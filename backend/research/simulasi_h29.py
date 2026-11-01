import math
from datetime import datetime

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import isi_backtest as ib
from backend.db import koneksi as d
from backend.paper.h29 import BIAYA_PINDAH
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

JUMLAH_SIMULASI = 100
CONTOH_SEED = 7
PORSI = 0.5
VERSI = {
    "h29_dev": {"periode": "dev", "label": "Momentum Blend 2011-2019 (simulasi, dibuat setelah lihat hasil)"},
    "h29_2020": {"periode": "holdout", "label": "Momentum Blend 2020-2026 (simulasi, dibuat setelah lihat hasil)"},
}


def rs_simulasi(S):
    P, tgl = S["P"], S["tgl"]
    rb = m.jadwal(S)
    hari = tgl[tgl >= rb[0][1]]
    rb_map = {dd: t for t, dd in rb}
    kas, pegang, tunda_jual, tunda_beli = 1.0, {}, set(), {}
    aktif, ep, rekap, ekuitas = {}, [], [], []
    cn = P["c_nilai"]

    def tutup(k, dd, terima):
        e = aktif.pop(k)
        ep[e]["terima"] += terima
        ep[e]["jual"] = dd
        ep[e]["harga_jual"] = float(P["o_raw"].at[dd, k]) if P["o_raw"].at[dd, k] > 0 else float(P["c_raw_ff"].at[dd, k])

    for dd in hari:
        if dd in rb_map:
            t = rb_map[dd]
            for k, a in tunda_beli.items():
                kas += a
            tunda_beli = {}
            calon = m.lolos(S, t, 5e9, 100)
            mom = m.momentum(S, t)
            urut = m.peringkat(S, t, "h22", calon)
            n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
            rank = {k: i + 1 for i, k in enumerate(urut)}
            harga_o = {k: (P["o"].at[dd, k] if P["o"].at[dd, k] > 0 else cn.at[dd, k]) for k in pegang}
            eq_o = kas + sum(pegang[k] * (harga_o[k] if harga_o[k] == harga_o[k] else 0) for k in pegang)
            tetap = sorted([k for k in pegang if rank.get(k, 10 ** 9) <= 2 * n], key=lambda k: rank[k])
            jual = [k for k in pegang if k not in tetap]
            if len(tetap) > n:
                jual += tetap[n:]
                tetap = tetap[:n]
            baru = [k for k in urut if k not in pegang][: max(0, n - len(tetap))]
            for k in jual:
                tunda_jual.add(k)
            for k in tetap:
                w = pegang[k] * harga_o[k] / eq_o if eq_o > 0 else 0
                if w > 2 / n and m.bisa(P, k, dd, "jual"):
                    lembar = pegang[k] - (eq_o / n) / harga_o[k]
                    terima = lembar * P["o"].at[dd, k] * (1 - m.FEE_JUAL - m.biaya_tick(P, k, dd, 1))
                    pegang[k] -= lembar
                    kas += terima
                    ep[aktif[k]]["terima"] += terima
            for k in list(tunda_jual):
                if k in pegang and m.bisa(P, k, dd, "jual"):
                    terima = pegang[k] * P["o"].at[dd, k] * (1 - m.FEE_JUAL - m.biaya_tick(P, k, dd, 1))
                    kas += terima
                    tutup(k, dd, terima)
                    del pegang[k]
                    tunda_jual.discard(k)
                elif k not in pegang:
                    tunda_jual.discard(k)
            if baru:
                anggaran = min(eq_o / n, kas / len(baru))
                for k in baru:
                    tunda_beli[k] = anggaran
                    kas -= anggaran
            rekap.append({"sinyal": t, "eksekusi": dd, "lolos": int(len(calon)), "n": n, "beli": baru, "jual": jual, "tetap": tetap,
                          "peringkat": [[k, round(float(mom[k]) * 100, 1)] for k in urut[: 2 * n]]})
        else:
            for k in list(tunda_jual):
                if k in pegang and m.bisa(P, k, dd, "jual"):
                    terima = pegang[k] * P["o"].at[dd, k] * (1 - m.FEE_JUAL - m.biaya_tick(P, k, dd, 1))
                    kas += terima
                    tutup(k, dd, terima)
                    del pegang[k]
                    tunda_jual.discard(k)
        for k in list(tunda_beli):
            if m.bisa(P, k, dd, "beli"):
                a = tunda_beli.pop(k)
                pegang[k] = pegang.get(k, 0) + a / (P["o"].at[dd, k] * (1 + m.FEE_BELI + m.biaya_tick(P, k, dd, 1)))
                if k not in aktif:
                    aktif[k] = len(ep)
                    sinyal = max(t for t, x in rb if x <= dd)
                    ep.append({"ticker": k, "sinyal": sinyal, "beli": dd, "jual": None, "modal": 0.0, "terima": 0.0, "akhir": 0.0,
                               "harga_beli": float(P["o_raw"].at[dd, k]), "harga_jual": None})
                ep[aktif[k]]["modal"] += a
        nilai = {k: pegang[k] * (cn.at[dd, k] if cn.at[dd, k] == cn.at[dd, k] else 0) for k in pegang}
        ekuitas.append((dd, kas + sum(tunda_beli.values()) + sum(nilai.values())))
        for k, v in nilai.items():
            ep[aktif[k]]["akhir"] = v
            ep[aktif[k]]["harga_akhir"] = float(P["c_raw_ff"].at[dd, k])
    eq = pd.Series(dict(ekuitas))
    for e in ep:
        if e["jual"] is not None:
            e["akhir"] = 0.0
    return eq, ep, rekap


def gabung(e11, e22, akhir):
    idx = e22.index.intersection(e11.index)
    idx = idx[idx <= akhir]
    a0 = e11[e11.index < idx[0]]
    a0 = float(a0.iloc[-1]) if len(a0) else 1.0
    j = {"v": 1.0, "vb": 1.0, "a": a0, "b": 1.0}
    v_list, vb_list, porsi = [], [], []
    for i, t in enumerate(idx):
        ra, rb = e11[t] / j["a"] - 1, e22[t] / j["b"] - 1
        f = 1 + PORSI * ra + PORSI * rb
        v, vb = j["v"] * f, j["vb"] * f
        akhir_bulan = i + 1 < len(idx) and idx[i + 1].to_period("M") != t.to_period("M")
        if akhir_bulan:
            bagian_a = j["vb"] * PORSI * (1 + ra)
            pindah = abs(bagian_a - vb * PORSI)
            porsi.append({"bulan": str(t.to_period("M")), "porsi_ft": round(bagian_a / vb * 100, 2), "pindah_pct": round(pindah / vb * 100, 2)})
            vb -= pindah * BIAYA_PINDAH
            j = {"v": v, "vb": vb, "a": float(e11[t]), "b": float(e22[t])}
        v_list.append(v)
        vb_list.append(vb)
    return pd.Series(v_list, index=idx), pd.Series(vb_list, index=idx), porsi


def bulanan(harian, dasar=1.0):
    b = harian.resample("ME").last()
    b.index = b.index.to_period("M")
    return b / pd.concat([pd.Series([dasar], index=[b.index[0] - 1]), b]).shift(1).iloc[1:] - 1


def cagr_bln(r):
    return float(((1 + r).prod() ** (12 / len(r)) - 1) * 100)


def dd_harian(h):
    return float((h / np.maximum(h.cummax(), 1.0) - 1).min() * 100)


def normal(seri, awal):
    s = seri.dropna()
    sebelum = s[s.index < awal]
    dasar = float(sebelum.iloc[-1]) if len(sebelum) else float(s.iloc[0])
    return s / dasar


def per_tahun(r):
    return {str(k): round(float(v), 1) for k, v in (((1 + r).groupby(r.index.year).prod() - 1) * 100).items()}


def statistik(net):
    net = np.asarray(net, float)
    if not len(net):
        return {}
    menang = net > 0
    return {"trade": int(len(net)), "win_rate": round(float(menang.mean() * 100), 1), "rata_menang": round(float(net[menang].mean()), 2) if menang.any() else None,
            "rata_kalah": round(float(net[~menang].mean()), 2) if (~menang).any() else None, "net_per_trade": round(float(net.mean()), 2),
            "median_trade": round(float(np.median(net)), 2)}


def jalankan(versi):
    cfg = VERSI[versi]
    S = m.susun(cfg["periode"])
    e22, ep22, rekap = rs_simulasi(S)
    asli = m.simulasi(S, "h22")["ekuitas"]
    assert float((asli - e22.reindex(asli.index)).abs().max()) < 1e-9
    ew = m.pembanding_sama(S)
    mulai = e22.index[0]
    akhir_22 = e22.index[-1]
    tgl = S["tgl"]
    del S

    if cfg["periode"] == "dev":
        siap, m11, a11 = ut.siapkan_dev(), pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31")
        tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
        tr = tr[(tr["tgl"] >= m11) & (tr["tgl"] <= a11)].reset_index(drop=True)
    else:
        siap, m11 = ut.siapkan_holdout(), pd.Timestamp("2020-01-01")
        tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
        tr = tr[tr["tgl"] >= m11].reset_index(drop=True)
        a11 = tr["tgl_exit"].max()
    akhir = min(akhir_22, a11)
    mentah = {t: baca_mentah(t) for t in tr["ticker"].unique()}
    dok = ib.dokumen_trade(versi, tr, set(), siap)
    del siap

    hasil, contoh = [], None
    for seed in range(1, JUMLAH_SIMULASI + 1):
        pilih = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        dok_s = [dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)]
        _, e11 = ib.kurva_paper(dok_s, m11, a11, mentah)
        v, vb, porsi = gabung(e11, e22, akhir)
        r, rb = bulanan(v), bulanan(vb)
        r11 = bulanan(e11[(e11.index >= mulai) & (e11.index <= akhir)], float(e11[e11.index < mulai].iloc[-1]) if (e11.index < mulai).any() else 1.0)
        hasil.append({"cagr": cagr_bln(r), "dd": dd_harian(v), "cagr_biaya": cagr_bln(rb), "cagr_h11a": cagr_bln(r11),
                      "dd_h11a": dd_harian(normal(e11[e11.index <= akhir], mulai)[lambda s: s.index >= mulai])})
        if seed == CONTOH_SEED:
            contoh = {"v": v, "vb": vb, "porsi": porsi, "e11": e11, "dok": dok_s}
        if seed % 20 == 0:
            print(f"  {versi}: {seed}/{JUMLAH_SIMULASI} simulasi", flush=True)
    hs = pd.DataFrame(hasil)

    v, e11 = contoh["v"], contoh["e11"]
    idx = v.index
    r = bulanan(v)
    ih = dt.baca("pasar")["ihsg"].dropna()
    jii = dt.baca("indeks/JKII")["close"].dropna()
    kur = {"ekuitas": v, "h11a": normal(e11.reindex(e11.index.union(idx)).ffill(), mulai).reindex(idx),
           "h22": e22.reindex(idx), "beli_tahan": normal(ew, mulai).reindex(idx).ffill(),
           "ihsg": normal(ih.reindex(ih.index.union(idx)).ffill(), mulai).reindex(idx),
           "jii": normal(jii.reindex(jii.index.union(idx)).ffill(), mulai).reindex(idx)}
    bln = {k: s.resample("ME").last() for k, s in kur.items()}
    for s in bln.values():
        s.index = s.index.to_period("M")
    ek = (1 + r).cumprod()
    dd_bln = ek / np.maximum(ek.cummax(), 1.0) - 1
    dok_ek = [{"versi": versi, "bulan": str(b), "return": round(float(r[b] * 100), 2), "ekuitas": round(float(ek[b]), 4),
               "drawdown": round(float(dd_bln[b] * 100), 2), **{k: (round(float(bln[k][b]), 4) if b in bln[k].index and bln[k][b] == bln[k][b] else None)
                                                                for k in ["beli_tahan", "ihsg", "h11a", "h22", "jii"]}} for b in r.index]

    def tahunan(k):
        s = bln[k].dropna()
        rr = s / pd.concat([pd.Series([1.0], index=[s.index[0] - 1]), s]).shift(1).iloc[1:] - 1
        return per_tahun(rr)

    pt = {k: tahunan(k) for k in ["h11a", "h22", "beli_tahan", "ihsg", "jii"]}
    pt["h29"] = per_tahun(r)
    tahun = sorted(pt["h29"])
    per_tahun_bagian = [{"tahun": t, **{k: pt[k].get(t) for k in pt}} for t in tahun]

    dok_tr = []
    for x in contoh["dok"]:
        if not x["dipilih"] or pd.Timestamp(x["tgl_jual"]) < mulai or pd.Timestamp(x["tgl_beli"]) > akhir:
            continue
        dok_tr.append({**x, "versi": versi, "bagian": "Follow Tren"})
    for e in ep22:
        if e["beli"] > akhir or e["modal"] <= 1e-9:
            continue
        selesai = e["jual"] is not None and e["jual"] <= akhir
        hasil_rp = e["terima"] + (0.0 if selesai else e["akhir"])
        jual = e["jual"] if selesai else akhir
        hj = e["harga_jual"] if selesai else e.get("harga_akhir")
        dok_tr.append({"versi": versi, "ticker": e["ticker"], "tgl_sinyal": e["sinyal"].to_pydatetime(), "tgl_beli": e["beli"].to_pydatetime(),
                       "harga_beli": round(e["harga_beli"]), "tgl_jual": jual.to_pydatetime(), "harga_jual": round(hj) if hj == hj and hj else None,
                       "hari": int(((tgl > e["beli"]) & (tgl <= jual)).sum()), "kotor": round((hj / e["harga_beli"] - 1) * 100, 2) if hj and e["harga_beli"] else None,
                       "net": round((hasil_rp / e["modal"] - 1) * 100, 2), "status": "selesai" if selesai else "terbuka", "stop_awal_pct": None,
                       "dipilih": True, "bagian": "RS 12-1"})
    net_ft = [x["net"] for x in dok_tr if x["bagian"] == "Follow Tren" and x["status"] != "terbuka"]
    net_rs = [x["net"] for x in dok_tr if x["bagian"] == "RS 12-1" and x["status"] != "terbuka"]
    hari_rata = np.mean([x["hari"] for x in dok_tr]) if dok_tr else 0

    r22 = bulanan(e22[e22.index <= akhir])
    rew = bulanan(normal(ew, mulai)[lambda s: (s.index >= mulai) & (s.index <= akhir)])
    rih = bulanan(normal(ih, mulai)[lambda s: (s.index >= mulai) & (s.index <= akhir)])
    rjii = bulanan(normal(jii, mulai)[lambda s: (s.index >= mulai) & (s.index <= akhir)])
    r11c = bulanan(kur["h11a"])
    j = pd.concat([r11c.rename("a"), r22.rename("b")], axis=1).dropna()
    ringkas = {
        "versi": versi, "label": cfg["label"], "dibuat": datetime.now(), "mulai": str(r.index[0]), "akhir": str(r.index[-1]),
        "sinyal": int(len(dok_tr)), "trade": int(len(net_ft) + len(net_rs)), **statistik(net_ft + net_rs), "rata_hari": round(float(hari_rata), 1),
        "cagr": round(cagr_bln(r), 1), "dd_maks": round(dd_harian(v), 1), "dd_harian": round(dd_harian(v), 1),
        "bulan_positif": round(float((r > 0).mean() * 100), 1), "bulan_terburuk": round(float(r.min() * 100), 1), "bulan_terbaik": round(float(r.max() * 100), 1),
        "cagr_beli_tahan": round(cagr_bln(rew), 1), "cagr_ihsg": round(cagr_bln(rih), 1), "cagr_jii": round(cagr_bln(rjii), 1),
        "per_tahun": pt["h29"], "per_tahun_bagian": per_tahun_bagian,
        "metode": "harian: 50% kurva paper Follow Tren + 50% kurva RS 12-1, dikembalikan ke 50/50 tiap akhir bulan tanpa biaya; dibuat setelah lihat hasil, bukan bukti",
        "monte_carlo": {"n": JUMLAH_SIMULASI, "seed": f"1-{JUMLAH_SIMULASI}", "contoh_seed": CONTOH_SEED, "cagr": ib.sebaran(hs["cagr"]), "dd": ib.sebaran(hs["dd"]),
                        "contoh": {"cagr": round(float(hs["cagr"][CONTOH_SEED - 1]), 1), "dd": round(float(hs["dd"][CONTOH_SEED - 1]), 1)}},
        "bagian": {
            "h11a": {"nama": "Follow Tren", "cagr": round(float(hs["cagr_h11a"].median()), 1), "dd": round(float(hs["dd_h11a"].median()), 1), **statistik(net_ft),
                     "hari": round(float(np.mean([x["hari"] for x in dok_tr if x["bagian"] == "Follow Tren"] or [0])), 1)},
            "h22": {"nama": "RS 12-1", "cagr": round(cagr_bln(r22), 1), "dd": round(dd_harian(e22[e22.index <= akhir]), 1), **statistik(net_rs),
                    "hari": round(float(np.mean([x["hari"] for x in dok_tr if x["bagian"] == "RS 12-1"] or [0])), 1)},
            "ew": {"nama": "Bobot sama syariah", "cagr": round(cagr_bln(rew), 1), "dd": round(dd_harian(normal(ew, mulai)[lambda s: (s.index >= mulai) & (s.index <= akhir)]), 1)},
            "jii": {"nama": "JII (indeks harga)", "cagr": round(cagr_bln(rjii), 1)},
            "ihsg": {"nama": "IHSG", "cagr": round(cagr_bln(rih), 1)},
        },
        "korelasi": round(float(j["a"].corr(j["b"])), 2),
        "biaya_rebalance": {"cagr_median": round(float(hs["cagr_biaya"].median()), 1), "persen_dipindah": round(BIAYA_PINDAH * 100, 2),
                            "rata_pindah_pct": round(float(np.mean([p["pindah_pct"] for p in contoh["porsi"]])), 2)},
        "porsi": contoh["porsi"],
        "rebalance": [{"sinyal": x["sinyal"].to_pydatetime(), "eksekusi": x["eksekusi"].to_pydatetime(), "lolos": x["lolos"], "n": x["n"],
                       "beli": x["beli"], "jual": x["jual"], "tetap": x["tetap"], "peringkat": x["peringkat"]} for x in rekap if x["eksekusi"] <= akhir],
    }
    db = d.koneksi()
    d.ganti_versi(db, "backtest_ekuitas", versi, dok_ek)
    d.ganti_versi(db, "backtest_trade", versi, dok_tr)
    db.backtest_ringkasan.replace_one({"versi": versi}, ringkas, upsert=True)
    u = ringkas["monte_carlo"]
    print(f"{versi}: CAGR median {u['cagr']['median']}% (p5-p95 {u['cagr']['p5']} s/d {u['cagr']['p95']}), DD median {u['dd']['median']}%, "
          f"setelah biaya rebalance {ringkas['biaya_rebalance']['cagr_median']}% | Follow Tren {ringkas['bagian']['h11a']['cagr']}% · RS 12-1 {ringkas['bagian']['h22']['cagr']}% · "
          f"bobot sama {ringkas['cagr_beli_tahan']}% · JII {ringkas['cagr_jii']}% · IHSG {ringkas['cagr_ihsg']}%", flush=True)


def utama():
    for v in VERSI:
        print(f"menghitung {v} ...", flush=True)
        jalankan(v)
    print("SELESAI")


if __name__ == "__main__":
    utama()
