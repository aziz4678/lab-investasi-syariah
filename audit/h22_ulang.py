import argparse
import math
import time

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import isi_backtest as ib
from backend.paper.tren_harian import BOBOT, PAJAK_DIVIDEN, biaya_beli, hasil_jual
from backend.research import eksplorasi_2020 as ek
from backend.research import screener as sc
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

FRAKSI_ASLI = sc.fraksi
IHSG = None


def ihsg():
    global IHSG
    if IHSG is None:
        IHSG = dt.baca("pasar")["ihsg"].dropna()
    return IHSG


def rf_bulanan():
    b = dt.baca("makro/bunga_antarbank")["nilai"].dropna()
    b.index = pd.to_datetime(b.index).to_period("M")
    return (1 + b / 100) ** (1 / 12) - 1


def cagr_bln(r):
    return ((1 + r).prod() ** (12 / len(r)) - 1) * 100 if len(r) else np.nan


def dd_bln(r):
    e = np.concatenate([[1.0], (1 + r).cumprod().to_numpy()])
    return (e / np.maximum.accumulate(e) - 1).min() * 100


def sharpe(r, rf):
    x = (r - rf.reindex(r.index).ffill().bfill()).dropna()
    return x.mean() / x.std() * math.sqrt(12)


def tanpa_tahun_terbaik(r):
    th = (1 + r).groupby(r.index.year).prod()
    terbaik = int(th.idxmax())
    return cagr_bln(r[r.index.year != terbaik]), terbaik, (th.max() - 1) * 100


def buang(r, e0, pnl, ids):
    r2 = r.copy()
    for (i, b), v in pnl.items():
        if i in ids and b in r2.index:
            r2[b] -= v / e0[b]
    return r2


def h22_log(S, min_nilai=5e9, min_harga=100, tick=1, keluar=frozenset()):
    P, tgl = S["P"], S["tgl"]
    rb = m.jadwal(S)
    mulai = rb[0][1]
    hari = tgl[tgl >= mulai]
    rb_map = {d: t for t, d in rb}
    kas, pegang, tunda_jual, tunda_beli = 1.0, {}, set(), {}
    aktif, ep = {}, []
    nilai_kemarin, pnl, isi, ekuitas = {}, {}, {}, []
    cn = P["c_nilai"]

    def jual_semua(k, d, aliran):
        nonlocal kas
        e = aktif.pop(k)
        terima = pegang[k] * P["o"].at[d, k] * (1 - m.FEE_JUAL - m.biaya_tick(P, k, d, tick))
        kas += terima
        aliran[e] = aliran.get(e, 0) + terima
        ep[e]["terima"] += terima
        ep[e]["jual"] = d
        del pegang[k]

    for d in hari:
        aliran = {}
        if d in rb_map:
            t = rb_map[d]
            for k, a in tunda_beli.items():
                kas += a
            tunda_beli = {}
            calon = [k for k in m.lolos(S, t, min_nilai, min_harga) if k not in keluar]
            urut = m.peringkat(S, t, "h22", calon)
            n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
            rank = {k: i + 1 for i, k in enumerate(urut)}
            harga_o = {k: (P["o"].at[d, k] if P["o"].at[d, k] > 0 else cn.at[d, k]) for k in pegang}
            eq_o = kas + sum(pegang[k] * (harga_o[k] if harga_o[k] == harga_o[k] else 0) for k in pegang)
            tetap = sorted([k for k in pegang if rank.get(k, 10 ** 9) <= 2 * n], key=lambda k: rank[k])
            jual = [k for k in pegang if k not in tetap]
            if len(tetap) > n:
                jual += tetap[n:]
                tetap = tetap[:n]
            baru = [k for k in urut if k not in pegang][: max(0, n - len(tetap))]
            tunda_jual.update(jual)
            for k in tetap:
                w = pegang[k] * harga_o[k] / eq_o if eq_o > 0 else 0
                if w > 2 / n and m.bisa(P, k, d, "jual"):
                    lembar = pegang[k] - (eq_o / n) / harga_o[k]
                    terima = lembar * P["o"].at[d, k] * (1 - m.FEE_JUAL - m.biaya_tick(P, k, d, tick))
                    pegang[k] -= lembar
                    kas += terima
                    e = aktif[k]
                    aliran[e] = aliran.get(e, 0) + terima
                    ep[e]["terima"] += terima
            for k in list(tunda_jual):
                if k in pegang and m.bisa(P, k, d, "jual"):
                    jual_semua(k, d, aliran)
                    tunda_jual.discard(k)
                elif k not in pegang:
                    tunda_jual.discard(k)
            if baru:
                anggaran = min(eq_o / n, kas / len(baru))
                for k in baru:
                    tunda_beli[k] = anggaran
                    kas -= anggaran
        else:
            for k in list(tunda_jual):
                if k in pegang and m.bisa(P, k, d, "jual"):
                    jual_semua(k, d, aliran)
                    tunda_jual.discard(k)
        for k in list(tunda_beli):
            if m.bisa(P, k, d, "beli"):
                a = tunda_beli.pop(k)
                pegang[k] = pegang.get(k, 0) + a / (P["o"].at[d, k] * (1 + m.FEE_BELI + m.biaya_tick(P, k, d, tick)))
                if k not in aktif:
                    aktif[k] = len(ep)
                    ep.append({"ticker": k, "beli": d, "jual": None, "modal": 0.0, "terima": 0.0, "akhir": 0.0})
                e = aktif[k]
                ep[e]["modal"] += a
                aliran[e] = aliran.get(e, 0) - a
        nilai = {aktif[k]: pegang[k] * (cn.at[d, k] if cn.at[d, k] == cn.at[d, k] else 0) for k in pegang}
        ekuitas.append((d, kas + sum(tunda_beli.values()) + sum(nilai.values())))
        bln = d.to_period("M")
        for e in set(nilai) | set(aliran) | set(nilai_kemarin):
            pnl[(e, bln)] = pnl.get((e, bln), 0.0) + nilai.get(e, 0) - nilai_kemarin.get(e, 0) + aliran.get(e, 0)
        nilai_kemarin = nilai
        isi[bln] = set(pegang)
    for e, v in nilai_kemarin.items():
        ep[e]["akhir"] = v
    eq = pd.Series(dict(ekuitas))
    return selesai(eq, pnl, ep, isi, hari[-1])


def selesai(eq, pnl, ep, isi, akhir, bln=None):
    if bln is None:
        bln = eq.groupby(eq.index.to_period("M")).last()
    e0 = bln.shift(1).fillna(1.0)
    r = bln / e0 - 1
    pos = pd.DataFrame(ep)
    pos["jual"] = pos["jual"].fillna(akhir)
    pos["pnl"] = pos["terima"] + pos.get("div", 0) + pos["akhir"] - pos["modal"]
    pos["ret"] = pos["pnl"] / pos["modal"] * 100
    return {"eq": eq, "r": r, "e0": e0, "pnl": pnl, "pos": pos, "isi": isi}


def h11a_log(dok, mulai, akhir, mentah):
    tr = pd.DataFrame([x for x in dok if x["dipilih"]])
    tr["tgl_beli"] = pd.to_datetime(tr["tgl_beli"])
    tr["tgl_jual"] = pd.to_datetime(tr["tgl_jual"]).where(tr["status"] != "terbuka")
    tr = tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    hari = ihsg().index[(ihsg().index >= mulai) & (ihsg().index <= akhir)]
    tabel, dv = {}, {}
    for t in tr["ticker"].unique():
        mm = mentah[t]
        s = mm["close"][mm.index.isin(hari)].astype(float)
        tabel[t] = s[np.isfinite(s.to_numpy())].reindex(hari).ffill().to_numpy()
        d_ = mm["dividends"].fillna(0) if "dividends" in mm else pd.Series(dtype=float)
        d_ = d_[d_.index.isin(hari) & (d_ > 0)]
        dv[t] = {k: float(v) for k, v in d_.items()}
    ticker = tr["ticker"].to_numpy()
    hb = tr["harga_beli"].to_numpy(float)
    beli = {k: v for k, v in tr.groupby("tgl_beli")}
    jual = {k: v for k, v in tr[tr["tgl_jual"].notna()].groupby("tgl_jual")}
    ep = [{"ticker": ticker[i], "beli": tr["tgl_beli"].iloc[i], "jual": tr["tgl_jual"].iloc[i], "modal": 0.0, "terima": 0.0, "div": 0.0, "akhir": 0.0}
          for i in range(len(tr))]
    kas, posisi, nilai_kemarin, pnl, isi, out = 1.0, {}, {}, {}, {}, []

    def nilai_pos(j):
        return {i: l * (tabel[ticker[i]][j] if tabel[ticker[i]][j] == tabel[ticker[i]][j] else hb[i]) for i, l in posisi.items()}

    for j, tgl in enumerate(hari):
        aliran = {}
        for i, l in posisi.items():
            d_ = dv[ticker[i]].get(tgl)
            if d_:
                x = l * d_ * (1 - PAJAK_DIVIDEN)
                kas += x
                aliran[i] = aliran.get(i, 0) + x
                ep[i]["div"] += x
        if tgl in jual:
            for r in jual[tgl].itertuples():
                lembar = posisi.pop(r.Index, 0.0)
                x = lembar * hasil_jual(r.harga_jual)
                kas += x
                if lembar:
                    aliran[r.Index] = aliran.get(r.Index, 0) + x
                    ep[r.Index]["terima"] += x
        ekuitas = out[-1] if out else 1.0
        if tgl in beli:
            for r in beli[tgl].itertuples():
                dana = min(BOBOT * ekuitas, kas)
                if dana <= 0:
                    continue
                posisi[r.Index] = dana / biaya_beli(r.harga_beli)
                kas -= dana
                aliran[r.Index] = aliran.get(r.Index, 0) - dana
                ep[r.Index]["modal"] += dana
        nilai = nilai_pos(j)
        out.append(kas + sum(nilai.values()))
        b = tgl.to_period("M")
        for i in set(nilai) | set(aliran) | set(nilai_kemarin):
            pnl[(i, b)] = pnl.get((i, b), 0.0) + nilai.get(i, 0) - nilai_kemarin.get(i, 0) + aliran.get(i, 0)
        nilai_kemarin = nilai
        isi[b] = {ticker[i] for i in posisi}
    for i, v in nilai_kemarin.items():
        ep[i]["akhir"] = v
    harian = pd.Series(out, index=hari)
    bln = harian.resample("ME").last()
    bln.index = bln.index.to_period("M")
    bln = bln.reindex(pd.period_range(mulai.to_period("M"), akhir.to_period("M"), freq="M")).ffill().fillna(1.0)
    hasil = selesai(harian, pnl, ep, isi, hari[-1], bln)
    hasil["pos"] = hasil["pos"][hasil["pos"]["modal"] > 0]
    return hasil


def ew(O, CN, lolos_fn, reb, akhir, keluar=frozenset()):
    eq, r, e0, pnl, ep = 1.0, {}, {}, {}, []
    for w, (t, d) in enumerate(reb):
        d1 = reb[w + 1][1] if w + 1 < len(reb) else akhir
        calon = [k for k in lolos_fn(t) if k not in keluar]
        rets = {}
        for k in calon:
            p0 = O.at[d, k] if O.at[d, k] > 0 else CN.at[d, k]
            if not (p0 > 0):
                continue
            if w + 1 < len(reb):
                p1 = O.at[d1, k] if O.at[d1, k] > 0 else CN.at[d1, k]
            else:
                p1 = CN.at[d1, k]
            rets[k] = (p1 / p0 - 1) if p1 == p1 else -1.0
        b = d.to_period("M")
        if not rets:
            r[b], e0[b] = 0.0, eq
            continue
        n = len(rets)
        e0[b] = eq
        for k, x in rets.items():
            i = len(ep)
            ep.append({"ticker": k, "ret": x * 100, "pnl": eq * x / n, "jual": d1})
            pnl[(i, b)] = eq * x / n
        r[b] = sum(rets.values()) / n
        eq *= 1 + r[b]
    pos = pd.DataFrame(ep)
    return {"r": pd.Series(r), "e0": pd.Series(e0), "pnl": pnl, "pos": pos}


def top_ticker(pos, k):
    return list(pos.groupby("ticker")["pnl"].sum().nlargest(k).index)


def top_pos(pos, k):
    return set(pos["pnl"].nlargest(k).index)


def ids_ticker(pos, tk):
    return set(pos.index[pos["ticker"].isin(tk)])


def distribusi(pos, pnl, label):
    p = pos.copy()
    th_pnl = pd.Series({(i, b.year): 0.0 for (i, b) in pnl})
    for (i, b), v in pnl.items():
        th_pnl[(i, b.year)] += v
    th_pnl = th_pnl[th_pnl.index.get_level_values(0).isin(p.index)]
    p["tahun"] = th_pnl.groupby(level=0).idxmax().map(lambda x: x[1]).reindex(p.index)
    laba_th = th_pnl.groupby(level=1).sum()
    baris = []
    for th, g in p.groupby("tahun"):
        a, b = g[g["ret"] > 50], g[g["ret"] > 100]
        di_th = th_pnl.xs(th, level=1)
        tot = laba_th.get(th, 0)
        t5, t10 = di_th.nlargest(5).sum(), di_th.nlargest(10).sum()
        baris.append({"strategi": label, "tahun": th, "laba tahun": round(tot * 100, 1), ">50%": len(a), "saham >50%": a["ticker"].nunique(),
                      ">100%": len(b), "saham >100%": b["ticker"].nunique(),
                      "top5 % laba th": round(t5 / tot * 100) if tot > 0 else None, "top10 % laba th": round(t10 / tot * 100) if tot > 0 else None})
    tot = p["pnl"].sum()
    t5, t10 = p["pnl"].nlargest(5), p["pnl"].nlargest(10)
    ring = {"strategi": label, "posisi": len(p), ">50%": int((p["ret"] > 50).sum()), "saham >50%": p.loc[p["ret"] > 50, "ticker"].nunique(),
            ">100%": int((p["ret"] > 100).sum()), "saham >100%": p.loc[p["ret"] > 100, "ticker"].nunique(),
            "tahun >50% muncul": p.loc[p["ret"] > 50, "tahun"].nunique(),
            "top5 % laba": round(t5.sum() / tot * 100, 1), "top10 % laba": round(t10.sum() / tot * 100, 1),
            "tahun top10": p.loc[t10.index, "tahun"].value_counts().sort_index().to_dict(),
            "top10": ", ".join(f"{p.at[i, 'ticker']} {p.at[i, 'ret']:.0f}%" for i in t10.index)}
    return pd.DataFrame(baris), ring


def uji_konsentrasi(h, ulang):
    r, e0, pnl, pos = h["r"], h["e0"], h["pnl"], h["pos"]
    out = {"CAGR": cagr_bln(r), "DD": dd_bln(r)}
    for k in (5, 10):
        out[f"-{k} posisi (kas)"] = cagr_bln(buang(r, e0, pnl, top_pos(pos, k)))
        out[f"-{k} saham (kas)"] = cagr_bln(buang(r, e0, pnl, ids_ticker(pos, top_ticker(pos, k))))
        if ulang:
            out[f"-{k} saham (tidak ada)"] = cagr_bln(ulang(top_ticker(pos, k))["r"])
    c, th, v = tanpa_tahun_terbaik(r)
    out["-tahun terbaik"] = c
    out["tahun terbaik"] = f"{th} ({v:+.0f}%)"
    return out


def kalender_sinyal(hari, mulai_sinyal):
    ab = pd.Series(hari, index=hari).groupby(hari.to_period("M")).max()
    reb = []
    for t in ab[ab >= mulai_sinyal]:
        nxt = hari[hari > t]
        if len(nxt):
            reb.append((t, nxt[0]))
    return reb


def matriks(siap, hari):
    O = pd.DataFrame({k: x["open"] for k, x in siap.items()}).reindex(hari)
    CN = pd.DataFrame({k: x["close"] for k, x in siap.items()}).reindex(hari).ffill()
    L = pd.DataFrame({k: x["lolos"] for k, x in siap.items()}).reindex(hari).fillna(False).astype(bool)
    return O, CN, L


class H11a:
    def __init__(self, siap, mulai, akhir, seeds):
        self.siap, self.mulai, self.seeds = siap, mulai, seeds
        tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
        self.tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= (akhir if akhir is not None else tr["tgl"].max()))].reset_index(drop=True)
        self.akhir = akhir if akhir is not None else self.tr["tgl_exit"].max()
        self.mentah = {t: baca_mentah(t) for t in self.tr["ticker"].unique()}
        self.dok = ib.dokumen_trade("audit", self.tr, set(), siap)

    def jalan(self, seed, keluar=frozenset()):
        tr = self.tr[~self.tr["ticker"].isin(keluar)]
        pilih = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        dok = [dict(x, dipilih=i in pilih) for i, x in zip(self.tr.index, self.dok)]
        return h11a_log(dok, self.mulai, self.akhir, self.mentah)

    def ew(self, keluar=frozenset()):
        hari = ihsg().index[(ihsg().index >= self.mulai - pd.Timedelta(days=40)) & (ihsg().index <= self.akhir)]
        O, CN, L = matriks(self.siap, hari)
        reb = [x for x in kalender_sinyal(hari, hari[0]) if x[1] >= self.mulai]
        return ew(O, CN, lambda t: list(L.columns[L.loc[t].to_numpy()]), reb, hari[-1], keluar)


def ringkas_seed(daftar):
    df = pd.DataFrame(daftar)
    return df.median(numeric_only=True)


def h11a_semua(obj, label, rf, cek=False):
    t0 = time.time()
    hasil, dist, ring, isi7, r_seed = [], [], None, None, {}
    for seed in obj.seeds:
        h = obj.jalan(seed)
        if cek and seed == obj.seeds[0]:
            pilih = set(simulasi_portofolio(obj.tr, ib.POSISI, seed).index)
            ret, _ = ib.kurva_paper([dict(x, dipilih=i in pilih) for i, x in zip(obj.tr.index, obj.dok)], obj.mulai, obj.akhir, obj.mentah)
            selisih = float((ret - h["r"]).abs().max())
            print(f"  cek salinan kurva H11a vs framework (seed {seed}): selisih maks return bulanan {selisih:.2e}", flush=True)
            assert selisih < 1e-9
        u = uji_konsentrasi(h, lambda tk: obj.jalan(seed, set(tk)))
        u["Sharpe"] = sharpe(h["r"], rf)
        u["tahun terbaik"] = int(str(u["tahun terbaik"])[:4])
        hasil.append(u)
        r_seed[seed] = h
        if seed == 7:
            dist, ring = distribusi(h["pos"], h["pnl"], label)
            u["tahun terbaik"] = tanpa_tahun_terbaik(h["r"])[1]
    print(f"  {label}: {len(obj.seeds)} seed selesai {time.time() - t0:.0f} dtk", flush=True)
    return hasil, dist, ring, r_seed


def h11a_sens(siap, mulai, akhir, seeds, label):
    baris = []
    varian = [("dasar", siap, False),
              ("S1 biaya 2 tick", siap, True),
              ("S2 nilai transaksi ≥ Rp20 M", {k: x.assign(lolos=x["lolos"] & (x["value_mentah"] >= 20e9)) for k, x in siap.items()}, False),
              ("S3 harga ≥ Rp200", {k: x.assign(lolos=x["lolos"] & (x["close_mentah"] >= 200)) for k, x in siap.items()}, False)]
    for nama, s, dua in varian:
        if dua:
            sc.fraksi = lambda h: 2 * FRAKSI_ASLI(h)
        try:
            obj = H11a(s, mulai, akhir, seeds)
            e = obj.ew()
            c, c5 = [], []
            for seed in seeds:
                h = obj.jalan(seed)
                c.append(cagr_bln(h["r"]))
                c5.append(cagr_bln(obj.jalan(seed, set(top_ticker(h["pos"], 5)))["r"]))
            cb = cagr_bln(e["r"])
            baris.append({"periode": label, "varian": nama, "CAGR": np.median(c), "EW": cb, "k1 CAGR > EW": np.median(c) > cb,
                          "CAGR -5 saham": np.median(c5), "k5 -5 saham > EW": np.median(c5) > cb})
        finally:
            sc.fraksi = FRAKSI_ASLI
        print(f"  sensitivitas H11a {label} {nama} selesai", flush=True)
    return pd.DataFrame(baris)


def h22_sens(S, label):
    baris = []
    for nama, ps in [("dasar", {}), ("S1 biaya 2 tick", {"tick": 2}), ("S2 nilai transaksi ≥ Rp20 M", {"min_nilai": 20e9}), ("S3 harga ≥ Rp200", {"min_harga": 200})]:
        h = h22_log(S, **ps)
        pb = {k: v for k, v in ps.items() if k != "tick"}
        e = ew(S["P"]["o"], S["P"]["c_nilai"], lambda t: list(m.lolos(S, t, pb.get("min_nilai", 5e9), pb.get("min_harga", 100))), m.jadwal(S), S["tgl"][-1])
        t5 = top_ticker(h["pos"], 5)
        h5 = h22_log(S, **ps, keluar=frozenset(t5))
        cb = cagr_bln(e["r"])
        baris.append({"periode": label, "varian": nama, "CAGR": cagr_bln(h["r"]), "EW": cb, "k1 CAGR > EW": cagr_bln(h["r"]) > cb,
                      "CAGR -5 saham": cagr_bln(h5["r"]), "k5 -5 saham > EW": cagr_bln(h5["r"]) > cb, "-5 saham": ", ".join(t5)})
        print(f"  sensitivitas H22 {label} {nama} selesai", flush=True)
    return pd.DataFrame(baris)


def satu_periode(periode, seeds, rf, sens):
    print(f"\n######## {periode.upper()} ########", flush=True)
    t0 = time.time()
    S = m.susun(periode)
    h22 = h22_log(S)
    sim_asli = m.simulasi(S, "h22")
    asli = sim_asli["ekuitas"]
    selisih = float((asli - h22["eq"].reindex(asli.index)).abs().max())
    print(f"  cek salinan H22 vs framework: selisih maks ekuitas {selisih:.2e} ({time.time() - t0:.0f} dtk)", flush=True)
    assert selisih < 1e-9
    e22 = ew(S["P"]["o"], S["P"]["c_nilai"], lambda t: list(m.lolos(S, t, 5e9, 100)), m.jadwal(S), S["tgl"][-1])
    eb_asli = m.pembanding_sama(S)
    print(f"  cek pembanding bobot sama: framework CAGR {m.cagr(eb_asli):.2f}% vs ulang {cagr_bln(e22['r']):.2f}% (bulanan)", flush=True)
    jii = m.pembanding_jii(S, h22["eq"].index[0])
    rj = m.bulanan(jii.loc[h22["eq"].index[0]:])
    k22 = uji_konsentrasi(h22, lambda tk: h22_log(S, keluar=frozenset(tk)))
    k22["Sharpe"] = sharpe(h22["r"], rf)
    kew22 = uji_konsentrasi(e22, lambda tk: ew(S["P"]["o"], S["P"]["c_nilai"], lambda t: [k for k in m.lolos(S, t, 5e9, 100) if k not in tk],
                                                  m.jadwal(S), S["tgl"][-1]))
    kew22["Sharpe"] = sharpe(e22["r"], rf)
    cj, thj, vj = tanpa_tahun_terbaik(rj)
    kj = {"CAGR": cagr_bln(rj), "DD": dd_bln(rj), "-tahun terbaik": cj, "tahun terbaik": f"{thj} ({vj:+.0f}%)", "Sharpe": sharpe(rj, rf)}
    d22, g22 = distribusi(h22["pos"], h22["pnl"], "H22")
    s22 = h22_sens(S, periode) if sens else None
    rekap = sim_asli["rekap"]
    del S

    if periode == "dev":
        siap, mulai, akhir = ut.siapkan_dev(), pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31")
    else:
        siap, mulai, akhir = ut.siapkan_holdout(), pd.Timestamp("2020-01-01"), None
    obj = H11a(siap, mulai, akhir, seeds)
    hs, d11, g11, r_seed = h11a_semua(obj, f"H11a {periode}", rf, cek=True)
    e11 = obj.ew()
    kew11 = uji_konsentrasi(e11, lambda tk: obj.ew(set(tk)))
    kew11["Sharpe"] = sharpe(e11["r"], rf)
    s11 = h11a_sens(siap, mulai, akhir, seeds, periode) if sens else None

    kor, ov_a, ov_b, gab = [], [], [], []
    for seed, h in r_seed.items():
        j = pd.concat([h["r"].rename("a"), h22["r"].rename("b")], axis=1, join="inner").dropna()
        kor.append(j["a"].corr(j["b"]))
        c = 0.5 * j["a"] + 0.5 * j["b"]
        gab.append({"CAGR": cagr_bln(c), "DD": dd_bln(c), "Sharpe": sharpe(c, rf), "H11a CAGR": cagr_bln(j["a"]), "H11a DD": dd_bln(j["a"]),
                    "H11a Sharpe": sharpe(j["a"], rf), "H22 CAGR": cagr_bln(j["b"]), "H22 DD": dd_bln(j["b"]), "H22 Sharpe": sharpe(j["b"], rf)})
        a_, b_ = [], []
        for bl in j.index:
            A, B = h["isi"].get(bl, set()), h22["isi"].get(bl, set())
            if A:
                a_.append(len(A & B) / len(A))
            if B:
                b_.append(len(A & B) / len(B))
        ov_a.append(np.mean(a_))
        ov_b.append(np.mean(b_))
    print(f"  {periode} selesai {time.time() - t0:.0f} dtk", flush=True)
    return {"periode": periode, "k22": k22, "kew22": kew22, "kj": kj, "k11": ringkas_seed(hs).to_dict(), "kew11": kew11,
            "d": pd.concat([d11, d22]), "g": [g11, g22], "s22": s22, "s11": s11,
            "kor": (np.median(kor), np.min(kor), np.max(kor)), "ov": (np.median(ov_a) * 100, np.median(ov_b) * 100),
            "gab": pd.DataFrame(gab).median().to_dict(), "n22": (rekap["lolos"].mean(), rekap["n"].mean()),
            "periode_bln": (str(h22["r"].index[0]), str(h22["r"].index[-1]), str(r_seed[seeds[0]]["r"].index[0]), str(r_seed[seeds[0]]["r"].index[-1]))}


def cetak(h):
    p = h["periode"]
    print(f"\n================ {p.upper()} ================")
    print(f"bulan H22 {h['periode_bln'][0]}..{h['periode_bln'][1]}, H11a {h['periode_bln'][2]}..{h['periode_bln'][3]}; H22 rata-rata saham lolos {h['n22'][0]:.1f}, N {h['n22'][1]:.1f}")
    print("\n-- distribusi pemenang besar per tahun keluar (H11a seed 7) --")
    print(h["d"].to_string(index=False))
    for g in h["g"]:
        print(g)
    print("\n-- konsentrasi (CAGR % dari return bulanan; H11a = median seed) --")
    print(pd.DataFrame({"H11a": h["k11"], "EW universe H11a": h["kew11"], "H22": h["k22"], "EW universe H22": h["kew22"], "JII+2,5%": h["kj"]}).to_string())
    print(f"\n-- korelasi bulanan H11a vs H22: median {h['kor'][0]:.2f} (min {h['kor'][1]:.2f}, maks {h['kor'][2]:.2f}); "
          f"overlap saham dipegang akhir bulan: {h['ov'][0]:.0f}% saham H11a juga dipegang H22, {h['ov'][1]:.0f}% saham H22 juga dipegang H11a")
    print("-- gabungan 50/50 rebalance bulanan (median seed, bulan bersama) --")
    print({k: round(v, 2) for k, v in h["gab"].items()})
    if h["s22"] is not None:
        print("\n-- sensitivitas standar H22 (k5 = tanpa 5 saham penyumbang terbesar, universe dijalankan ulang tanpa saham itu) --")
        print(pd.concat([h["s22"], h["s11"]]).round(2).to_string(index=False))


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=30)
    ap.add_argument("--tanpa-sens", action="store_true")
    a = ap.parse_args()
    rf = rf_bulanan()
    seeds = list(range(1, a.seed + 1))
    if 7 not in seeds:
        seeds.append(7)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    with ek.tanpa_simpan():
        for p in ("dev", "holdout"):
            cetak(satu_periode(p, seeds, rf, not a.tanpa_sens))


if __name__ == "__main__":
    utama()
