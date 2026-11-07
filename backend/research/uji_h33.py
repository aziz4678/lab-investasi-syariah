import argparse
import json
import time

import numpy as np
import pandas as pd

from audit import h22_ulang as au
from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi as kn
from backend.research import screener as sc
from backend.research import swing_target3 as s
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

MODAL_IDR = 100e6
BOBOT = 0.10
POSISI = 10
SEEDS = range(1, 101)
CONTOH = 7
PUTUS = 0.5
MULAI_DATA = "2005-01-01"
AKHIR = pd.Timestamp("2026-11-06")
AMBANG = {"nilai": 5e9, "harga": 50, "nilai_s2": 20e9, "harga_s3": 200}

PASAR = {
    "my": {"mulai": pd.Timestamp("2007-01-02"), "kurs": "myridr", "indeks": ("my_titans25", "adj_close"), "indeks_mulai": pd.Timestamp("2008-02-01"),
           "broker": 0.0010, "min_broker": 8.0, "lain_beli": 0.0013, "lain_jual": 0.0013, "pajak_div": 0.0, "vonis": True},
    "idx": {"mulai": pd.Timestamp("2010-01-01"), "kurs": None, "indeks": None, "indeks_mulai": None,
            "broker": 0.0, "min_broker": 0.0, "lain_beli": sc.FEE_BELI / 100, "lain_jual": sc.FEE_JUAL / 100, "pajak_div": 0.10, "vonis": False},
    "us": {"mulai": pd.Timestamp("2006-01-02"), "kurs": "usdidr", "indeks": ("us_djim", "close"), "indeks_mulai": pd.Timestamp("2006-01-02"),
           "broker": 0.0, "min_broker": 0.0, "lain_beli": 0.0, "lain_jual": 0.00003, "pajak_div": 0.15, "vonis": False},
}


def tick(pasar, p):
    p = np.asarray(p, dtype=float)
    if pasar == "idx":
        return sc.fraksi(p)
    if pasar == "my":
        return np.select([p < 1, p < 10, p < 100], [0.005, 0.01, 0.02], 0.10)
    return np.where(p < 1, 0.0001, 0.01)


def kurs(pasar):
    k = hg.indeks_luar(PASAR[pasar]["kurs"])["close"]
    return k[k > 0]


def segmen(df):
    df = df[(df.index >= MULAI_DATA) & (df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
    r = df["adj_close"].pct_change().abs()
    putus = list(np.flatnonzero((r > PUTUS).to_numpy()))
    batas = [0] + putus + [len(df)]
    return [df.iloc[batas[i]:batas[i + 1]] for i in range(len(batas) - 1)], [df.index[i] for i in putus]


def fitur(df, kr, syr):
    f = df["adj_close"] / df["close"]
    o, h, l, c = df["open"] * f, df["high"] * f, df["low"] * f, df["adj_close"]
    d = pd.DataFrame({"open": o, "high": pd.concat([o, h, l, c], axis=1).max(axis=1), "low": pd.concat([o, h, l, c], axis=1).min(axis=1),
                      "close": c, "volume": df["volume"], "close_mentah": df["close"]}, index=df.index)
    x = s.hitung_indikator(d)
    x["value_mentah"] = (d["close_mentah"] * d["volume"]).rolling(20).mean()
    k = kr.reindex(x.index, method="ffill").bfill()
    x["nilai_idr"] = x["value_mentah"] * k
    x["harga_idr"] = d["close_mentah"] * k
    syariah = pd.Series(False, index=x.index)
    for r in syr.itertuples():
        syariah |= (x.index >= r.mulai) & (x.index <= r.akhir)
    vol_nol = (d["volume"] == 0).rolling(5).sum()
    x["lolos_dasar"] = x["atr_pct"].between(sc.ATR_MIN, sc.ATR_MAKS) & (vol_nol == 0) & syariah
    x["lolos"] = x["lolos_dasar"] & (x["nilai_idr"] >= AMBANG["nilai"]) & (x["harga_idr"] >= AMBANG["harga"])
    return ut.tambah_fitur(x)


def siapkan(pasar):
    syr = hg.syariah_luar(pasar)
    data = hg.luar_banyak(pasar, set(syr["kode"]))
    kr = kurs(pasar)
    siap, mentah, kode_seg, kejadian, ujung = {}, {}, {}, [], set()
    for kode, df in sorted(data.items()):
        bagian, putus = segmen(df)
        for tg in putus:
            kejadian.append({"kode": kode, "tgl": tg})
        sy = syr[syr["kode"] == kode]
        for i, b in enumerate(bagian):
            if len(b) < 250:
                continue
            nama = kode if i == 0 else f"{kode}~{i}"
            x = fitur(b, kr, sy)
            siap[nama] = x
            mentah[nama] = b
            kode_seg[nama] = kode
            if i < len(bagian) - 1:
                ujung.add(nama)
    kj = pd.DataFrame(kejadian)
    if len(kj):
        lolos_sebelum = []
        for r in kj.itertuples():
            df = data[r.kode]
            df = df[(df.index >= MULAI_DATA) & (df.index < r.tgl)]
            seg = [n for n, k in kode_seg.items() if k == r.kode and siap[n].index.max() < r.tgl and siap[n].index.max() >= (df.index.max() if len(df) else r.tgl)]
            lolos_sebelum.append(bool(seg and siap[seg[0]]["lolos"].iloc[-1]))
        kj["lolos_sebelum"] = lolos_sebelum
    kal = pd.DatetimeIndex(sorted(set().union(*[x.index for x in siap.values()])))
    return {"siap": siap, "mentah": mentah, "kode": kode_seg, "putus": kj, "kurs": kr, "ujung": ujung, "kalender": kal}


def varian(S, nama):
    if nama in ("dasar", "s1"):
        return S["siap"]
    kol = "nilai_idr" if nama == "s2" else "harga_idr"
    ambang = AMBANG["nilai_s2"] if nama == "s2" else AMBANG["harga_s3"]
    return {k: x.assign(lolos=x["lolos"] & (x[kol] >= ambang)) for k, x in S["siap"].items()}


def trade(siap, mulai, ujung=frozenset()):
    tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= AKHIR)].reset_index(drop=True)
    dok = []
    for r in tr.itertuples():
        x = siap[r.ticker]
        i = x.index.get_loc(r.tgl)
        f_b = x["close_mentah"].iloc[i + 1] / x["close"].iloc[i + 1]
        beli = float(x["open"].iloc[i + 1] * f_b)
        k = x.index.get_loc(r.tgl_exit)
        if r.alasan == "stop":
            jual = float(x["open"].iloc[k] * x["close_mentah"].iloc[k] / x["close"].iloc[k])
        else:
            jual = float(x["close_mentah"].iloc[k])
        putus = r.alasan == "terbuka" and r.ticker in ujung
        dok.append({"ticker": r.ticker, "tgl": r.tgl, "tgl_exit": r.tgl_exit, "tgl_beli": x.index[i + 1], "harga_beli": beli,
                    "tgl_jual": r.tgl_exit, "harga_jual": jual, "hari": int(r.hari), "kotor": float(r.kotor),
                    "status": "terbuka" if r.alasan == "terbuka" and not putus else "selesai", "putus": bool(putus), "net": 0.0})
    return pd.DataFrame(dok)


def biaya(pasar, nilai, sisi):
    c = PASAR[pasar]
    return max(c["broker"] * nilai, c["min_broker"]) + (c["lain_beli"] if sisi == "beli" else c["lain_jual"]) * nilai


def kotor_dari_dana(pasar, dana):
    c = PASAR[pasar]
    v = dana / (1 + c["broker"] + c["lain_beli"])
    if c["broker"] * v < c["min_broker"]:
        v = (dana - c["min_broker"]) / (1 + c["lain_beli"])
    return v


def log_portofolio(pasar, S, tr, pilih, mulai, kali_tick=1):
    c = PASAR[pasar]
    tr = tr.loc[sorted(pilih)].sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    tr["tgl_jual"] = tr["tgl_jual"].where(tr["status"] != "terbuka")
    hari = S["hari"]
    tabel, dv = {}, {}
    for t in tr["ticker"].unique():
        m = S["mentah"][t]
        tabel[t] = m["close"].reindex(hari).ffill().to_numpy(float)
        d_ = m["dividends"].fillna(0) if "dividends" in m else pd.Series(dtype=float)
        d_ = d_[d_ > 0]
        dv[t] = {k: float(v) for k, v in d_.items()}
    ticker = tr["ticker"].to_numpy()
    hb = tr["harga_beli"].to_numpy(float)
    beli = {k: v for k, v in tr.groupby("tgl_beli")}
    jual = {k: v for k, v in tr[tr["tgl_jual"].notna()].groupby("tgl_jual")}
    ep = [{"ticker": S["kode"][ticker[i]], "beli": tr["tgl_beli"].iloc[i], "jual": tr["tgl_jual"].iloc[i], "modal": 0.0, "terima": 0.0, "div": 0.0,
           "akhir": 0.0} for i in range(len(tr))]
    modal = MODAL_IDR / float(S["kurs"].asof(mulai))
    kas, posisi, nilai_kemarin, pnl, isi, out, harga_akhir = modal, {}, {}, {}, {}, [], {}
    for j, tgl in enumerate(hari):
        aliran = {}
        for i, l in posisi.items():
            d_ = dv[ticker[i]].get(tgl)
            if d_:
                x = l * d_ * (1 - c["pajak_div"])
                kas += x
                aliran[i] = aliran.get(i, 0) + x
                ep[i]["div"] += x
        if tgl in jual:
            for r in jual[tgl].itertuples():
                lembar = posisi.pop(r.Index, 0.0)
                if not lembar:
                    continue
                v = lembar * (r.harga_jual - kali_tick * float(tick(pasar, r.harga_jual)))
                x = v - biaya(pasar, v, "jual")
                kas += x
                aliran[r.Index] = aliran.get(r.Index, 0) + x
                ep[r.Index]["terima"] += x
        ekuitas = out[-1] if out else modal
        if tgl in beli:
            for r in beli[tgl].itertuples():
                dana = min(BOBOT * ekuitas, kas)
                v = kotor_dari_dana(pasar, dana) if dana > 0 else 0
                if v <= 0:
                    continue
                posisi[r.Index] = v / (r.harga_beli + kali_tick * float(tick(pasar, r.harga_beli)))
                kas -= dana
                aliran[r.Index] = aliran.get(r.Index, 0) - dana
                ep[r.Index]["modal"] += dana
        nilai = {}
        for i, l in posisi.items():
            h = tabel[ticker[i]][j]
            if h == h:
                harga_akhir[i] = h
            nilai[i] = l * harga_akhir.get(i, hb[i])
        out.append(kas + sum(nilai.values()))
        b = tgl.to_period("M")
        for i in set(nilai) | set(aliran) | set(nilai_kemarin):
            pnl[(i, b)] = pnl.get((i, b), 0.0) + nilai.get(i, 0) - nilai_kemarin.get(i, 0) + aliran.get(i, 0)
        nilai_kemarin = nilai
        isi[b] = {ep[i]["ticker"] for i in posisi}
    for i, v in nilai_kemarin.items():
        ep[i]["akhir"] = v
    harian = pd.Series(out, index=hari) / modal
    pnl = {k: v / modal for k, v in pnl.items()}
    for e in ep:
        for kk in ("modal", "terima", "div", "akhir"):
            e[kk] /= modal
    bln = harian.resample("ME").last()
    bln.index = bln.index.to_period("M")
    bln = bln.reindex(pd.period_range(mulai.to_period("M"), AKHIR.to_period("M"), freq="M")).ffill().fillna(1.0)
    h = au.selesai(harian, pnl, ep, isi, hari[-1], bln)
    h["pos"] = h["pos"][h["pos"]["modal"] > 0]
    h["harian"] = harian
    return h


def kalender(S, mulai):
    return S["kalender"][(S["kalender"] >= mulai) & (S["kalender"] <= AKHIR)]


def pembanding_ew(S, siap, mulai):
    hari = S["kalender"][(S["kalender"] >= mulai - pd.Timedelta(days=40)) & (S["kalender"] <= AKHIR)]
    O = pd.DataFrame({k: x["open"] for k, x in siap.items()}).reindex(hari)
    CN = pd.DataFrame({k: x["close"] for k, x in siap.items()}).reindex(hari).ffill()
    L = pd.DataFrame({k: x["lolos"] for k, x in siap.items()}).reindex(hari).fillna(False).astype(bool)
    reb = [x for x in au.kalender_sinyal(hari, hari[0]) if x[1] >= mulai]
    e = au.ew(O, CN, lambda t: list(L.columns[L.loc[t].to_numpy()]), reb, hari[-1])
    e["pos"]["ticker"] = e["pos"]["ticker"].map(S["kode"])
    return e


def indeks_bulanan(pasar):
    nama, kol = PASAR[pasar]["indeks"]
    x = hg.indeks_luar(nama)[kol].dropna()
    x = x[x > 0]
    b = x.resample("ME").last()
    b.index = b.index.to_period("M")
    return b.pct_change().dropna()


def jendela(r, mulai, akhir=None):
    m = r.index >= pd.Period(mulai, "M")
    if akhir is not None:
        m &= r.index <= pd.Period(akhir, "M")
    return r[m]


def konsentrasi(h):
    return au.uji_konsentrasi(h, None)


def h11a_idx_bulanan():
    db = kn.koneksi()
    r = []
    for v in ("h11a_dev", "h11a_2020"):
        r += [(x["bulan"], x["return"] / 100) for x in db.backtest_ekuitas.find({"versi": v}, {"_id": 0, "bulan": 1, "return": 1})]
    s_ = pd.Series(dict(r))
    s_.index = pd.PeriodIndex(s_.index, freq="M")
    return s_.sort_index()


def skenario(pasar, S, nama, rj, idx_bln):
    c = PASAR[pasar]
    mulai = c["mulai"]
    siap = varian(S, nama)
    t0 = time.time()
    tr = trade(siap, mulai, S["ujung"])
    e = pembanding_ew(S, siap, mulai)
    ke = konsentrasi(e)
    rj_w = jendela(rj, c["indeks_mulai"], AKHIR)
    cj, thj, vj = au.tanpa_tahun_terbaik(rj_w)
    hasil, simpan = [], {}
    for seed in SEEDS:
        pilih = set(simulasi_portofolio(tr, POSISI, seed).index)
        h = log_portofolio(pasar, S, tr, pilih, mulai, 2 if nama == "s1" else 1)
        k = konsentrasi(h)
        rw = jendela(h["r"], c["indeks_mulai"], AKHIR)
        cw, _, _ = au.tanpa_tahun_terbaik(rw)
        pos = h["pos"]
        tr_p = tr.loc[sorted(pilih)]
        x = {"CAGR": k["CAGR"], "DD_bln": k["DD"], "DD": (h["harian"] / h["harian"].cummax() - 1).min() * 100,
             "-5": k["-5 saham (kas)"], "-10": k["-10 saham (kas)"], "-th": k["-tahun terbaik"],
             "tahun_terbaik": int(str(k["tahun terbaik"])[:4]), "CAGR_jendela_indeks": au.cagr_bln(rw), "-th_jendela_indeks": cw,
             "trade": len(pos), "winrate": float((pos["pnl"] > 0).mean() * 100) if len(pos) else np.nan,
             "tahan": float(tr_p["hari"].median()) if len(tr_p) else np.nan, "trade_putus": int(tr_p["putus"].sum()),
             "s/d_2019": au.cagr_bln(jendela(h["r"], mulai, "2019-12")), "2020+": au.cagr_bln(jendela(h["r"], "2020-01")),
             "2008-2009": au.cagr_bln(jendela(h["r"], "2008-01", "2009-12")),
             "korelasi_h11a_idx": pd.concat([h["r"], idx_bln], axis=1, join="inner").corr().iloc[0, 1]}
        kr_b = S["kurs"].resample("ME").last()
        kr_b.index = kr_b.index.to_period("M")
        kb = kr_b.reindex(pd.period_range(h["r"].index[0] - 1, h["r"].index[-1], freq="M")).ffill().bfill()
        eq = (1 + h["r"]).cumprod() * kb.iloc[1:].to_numpy() / float(kb.iloc[0])
        x["CAGR_rupiah"] = (eq.iloc[-1] ** (12 / len(eq)) - 1) * 100
        hasil.append(x)
        if seed == CONTOH:
            simpan = h
    df = pd.DataFrame(hasil)
    med = df.median(numeric_only=True)
    ew_r = e["r"]
    ew_w = jendela(ew_r, mulai, AKHIR)
    kriteria = {
        "1 CAGR > bobot sama": (med["CAGR"], ke["CAGR"], bool(med["CAGR"] > ke["CAGR"])),
        "2 CAGR > indeks (jendela indeks)": (med["CAGR_jendela_indeks"], au.cagr_bln(rj_w), bool(med["CAGR_jendela_indeks"] > au.cagr_bln(rj_w))),
        "3 tanpa 5 saham > bobot sama tanpa 5": (med["-5"], ke["-5 saham (kas)"], bool(med["-5"] > ke["-5 saham (kas)"])),
        "4 tanpa 10 saham > bobot sama tanpa 10": (med["-10"], ke["-10 saham (kas)"], bool(med["-10"] > ke["-10 saham (kas)"])),
        "5a tanpa tahun terbaik > bobot sama tanpa tahun terbaik": (med["-th"], ke["-tahun terbaik"], bool(med["-th"] > ke["-tahun terbaik"])),
        "5b tanpa tahun terbaik > indeks tanpa tahun terbaik (jendela indeks)": (med["-th_jendela_indeks"], cj, bool(med["-th_jendela_indeks"] > cj)),
    }
    top_s = simpan["pos"].groupby("ticker")["pnl"].sum().nlargest(10)
    top_e = e["pos"].groupby("ticker")["pnl"].sum().nlargest(10)
    rk = {"skenario": nama, "sinyal": len(tr), "saham_universe": len({S["kode"][k] for k, x in siap.items() if x["lolos"].any()}),
          "lolos_per_hari": float(pd.DataFrame({k: x["lolos"] for k, x in siap.items()}).loc[mulai:AKHIR].sum(axis=1).mean()),
          "median": med.round(3).to_dict(), "p5": df.quantile(0.05, numeric_only=True).round(2).to_dict(), "p95": df.quantile(0.95, numeric_only=True).round(2).to_dict(),
          "tahun_terbaik_modus": int(df["tahun_terbaik"].mode().iloc[0]),
          "ew": {"CAGR": ke["CAGR"], "DD": ke["DD"], "-5": ke["-5 saham (kas)"], "-10": ke["-10 saham (kas)"], "-th": ke["-tahun terbaik"], "tahun_terbaik": ke["tahun terbaik"],
                 "s/d_2019": au.cagr_bln(jendela(ew_r, mulai, "2019-12")), "2020+": au.cagr_bln(jendela(ew_r, "2020-01")), "2008-2009": au.cagr_bln(jendela(ew_r, "2008-01", "2009-12"))},
          "indeks": {"CAGR": au.cagr_bln(rj_w), "DD": au.dd_bln(rj_w), "-th": cj, "tahun_terbaik": f"{thj} ({vj:+.0f}%)", "mulai": str(rj_w.index[0]),
                     "s/d_2019": au.cagr_bln(jendela(rj_w, rj_w.index[0], "2019-12")), "2020+": au.cagr_bln(jendela(rj_w, "2020-01")), "2008-2009": au.cagr_bln(jendela(rj_w, "2008-01", "2009-12"))},
          "kriteria": {k: [round(float(v[0]), 2), round(float(v[1]), 2), v[2]] for k, v in kriteria.items()},
          "lulus": int(sum(v[2] for v in kriteria.values())), "dari": len(kriteria),
          "top10_strategi_seed7": {k: round(float(v * 100), 1) for k, v in top_s.items()},
          "top10_strategi_porsi": round(float(top_s.sum() / simpan["pos"]["pnl"].sum() * 100), 1),
          "top10_ew": {k: round(float(v * 100), 1) for k, v in top_e.items()},
          "per_tahun_seed7": {str(k): round(float(v * 100), 1) for k, v in ((1 + simpan["r"]).groupby(simpan["r"].index.year).prod() - 1).items()},
          "per_tahun_ew": {str(k): round(float(v * 100), 1) for k, v in ((1 + ew_w).groupby(ew_w.index.year).prod() - 1).items()},
          "detik": round(time.time() - t0)}
    print(f"  {pasar} {nama}: CAGR {med['CAGR']:.2f}% vs EW {ke['CAGR']:.2f}%, lulus {rk['lulus']}/{rk['dari']} ({rk['detik']} dtk)", flush=True)
    return rk, df


def satu_pasar(pasar):
    t0 = time.time()
    S = siapkan(pasar)
    c = PASAR[pasar]
    S["hari"] = kalender(S, c["mulai"])
    rj = indeks_bulanan(pasar)
    idx_bln = h11a_idx_bulanan()
    kj = S["putus"]
    dalam = kj[(kj["tgl"] >= c["mulai"]) & (kj["tgl"] <= AKHIR)] if len(kj) else kj
    hasil = {"pasar": pasar, "vonis_berlaku": c["vonis"], "mulai": str(c["mulai"].date()), "akhir": str(AKHIR.date()),
             "putus": {"kejadian": int(len(dalam)), "saham": int(dalam["kode"].nunique()) if len(dalam) else 0,
                       "kejadian_saham_lolos": int(dalam["lolos_sebelum"].sum()) if len(dalam) else 0,
                       "saham_lolos": sorted(dalam.loc[dalam["lolos_sebelum"], "kode"].unique().tolist()) if len(dalam) else [],
                       "kejadian_sejak_2005": int(len(kj))},
             "seri": len(S["siap"]), "kode": len(set(S["kode"].values())),
             "versi_data": hg.sidik(sorted(set(S["kode"].values())), koleksi=hg.KOLEKSI_LUAR[pasar]),
             "skenario": {}}
    if pasar == "my":
        hasil["versi_data"]["daftar_sc"] = dt.db()["syariah_my"].count_documents({"jumlah": {"$gt": 0}})
    else:
        d = dt.db()["syariah_us"].find_one(sort=[("tanggal", -1)])
        hasil["versi_data"]["daftar_us"] = {"sumber": d["sumber"], "tanggal": str(d["tanggal"].date()), "jumlah": d["jumlah"]}
    top_dasar = None
    for nama in ("dasar", "s1", "s2", "s3"):
        rk, _ = skenario(pasar, S, nama, rj, idx_bln)
        if nama == "dasar":
            top_dasar = rk
        else:
            rk["top10_dasar_di_skenario"] = {k: (k in rk["top10_strategi_seed7"]) for k in top_dasar["top10_strategi_seed7"]}
            rk["top10_dasar_ada_di_universe"] = {k: any(S["kode"][n] == k and x["lolos"].any() for n, x in varian(S, nama).items())
                                                 for k in top_dasar["top10_strategi_seed7"]}
        hasil["skenario"][nama] = rk
    sk = hasil["skenario"]
    semua = all(x["lulus"] == x["dari"] for x in sk.values())
    hasil["lulus_semua"] = semua
    hasil["vonis"] = ("lolos" if semua else "gagal") if c["vonis"] else "laporan saja"
    hasil["detik"] = round(time.time() - t0)
    print(f"{pasar}: vonis {hasil['vonis']} ({hasil['detik']} dtk)", flush=True)
    return hasil


def gabungan(h):
    bervonis = [x for x in h.values() if x["vonis"] in ("lolos", "gagal")]
    lolos = sum(x["vonis"] == "lolos" for x in bervonis)
    if not bervonis:
        return "tidak ada pasar bervonis"
    if lolos == 0:
        return "peringatan keras"
    if lolos >= 2:
        return "bukti replikasi kuat"
    return "campur"


def jalankan(daftar=("my", "us")):
    hasil = dt.baca_hasil("h33_hasil") or {}
    hasil = hasil.get("pasar", {}) if isinstance(hasil, dict) else {}
    for p in daftar:
        hasil[p] = satu_pasar(p)
        simpan = {"pasar": hasil, "gabungan": gabungan(hasil), "dijalankan": pd.Timestamp.now().isoformat(timespec="seconds"),
                  "pembanding_h13_set_a": {"cagr": 1.9, "beli_tahan": 5.0}}
        dt.simpan_hasil("h33_hasil", json.loads(json.dumps(simpan, default=lambda v: v.item() if hasattr(v, "item") else str(v))))
    return dt.baca_hasil("h33_hasil")


def utama():
    a = argparse.ArgumentParser()
    a.add_argument("--pasar", nargs="+", default=["my", "us"])
    a.add_argument("--tampil", action="store_true")
    x = a.parse_args()
    h = dt.baca_hasil("h33_hasil") if x.tampil else jalankan(x.pasar)
    print(json.dumps({"gabungan": h["gabungan"], **{p: {"vonis": v["vonis"], "kriteria": {n: s_["kriteria"] for n, s_ in v["skenario"].items()}}
                                                   for p, v in h["pasar"].items()}}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    utama()
