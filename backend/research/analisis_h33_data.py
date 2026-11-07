import argparse
import json

import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research import swing_target3 as s

KURS = {"my": "myridr", "us": "usdidr"}
AMBANG_IDR = {"nilai": 5e9, "nilai_s2": 2e10, "harga": 50, "harga_s3": 200}
MULAI_DATA = "2005-01-01"


def siapkan(df):
    df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)].copy()
    if len(df) < 60:
        return None
    f = df["adj_close"] / df["close"]
    o, h, l, c = df["open"] * f, df["high"] * f, df["low"] * f, df["adj_close"]
    d = pd.DataFrame({"open": o, "high": pd.concat([o, h, l, c], axis=1).max(axis=1),
                      "low": pd.concat([o, h, l, c], axis=1).min(axis=1), "close": c, "volume": df["volume"]}, index=df.index)
    x = s.hitung_indikator(d)
    return pd.DataFrame({
        "nilai": (df["close"] * df["volume"]).rolling(20).mean(),
        "atr_pct": x["atr_pct"],
        "harga": df["close"],
        "vol_nol": (df["volume"] == 0).rolling(5).sum(),
        "maks250": x["close"].rolling(250).max().shift(1),
        "close_adj": x["close"],
    }, index=df.index)


def masker(index, rentang):
    m = pd.Series(False, index=index)
    for r in rentang.itertuples():
        m |= (index >= r.mulai) & (index <= r.akhir)
    return m


def panel_luar(pasar):
    syr = hg.syariah_luar(pasar)
    data = hg.luar_banyak(pasar, set(syr["kode"]))
    potong = []
    for kode, df in data.items():
        df = df[df.index >= MULAI_DATA]
        x = siapkan(df)
        if x is None:
            continue
        x["syariah"] = masker(x.index, syr[syr["kode"] == kode])
        x["kode"] = kode
        potong.append(x[x["syariah"]])
    p = pd.concat(potong)
    p.index.name = "tgl"
    kurs = hg.indeks_luar(KURS[pasar])["close"]
    kurs = kurs[kurs > 0].reindex(p.index.unique().sort_values()).ffill().bfill()
    p["kurs"] = kurs.reindex(p.index).to_numpy()
    p["nilai_idr"] = p["nilai"] * p["kurs"]
    p["harga_idr"] = p["harga"] * p["kurs"]
    return p.reset_index(), syr, data


def panel_idx():
    daftar = sc.daftar_syariah()
    des = des_ojk.baca()
    data = hg.banyak(daftar | set(des["kode"]))
    potong = []
    for kode, df in data.items():
        x = siapkan(df)
        if x is None:
            continue
        dev = pd.Series(kode in daftar, index=x.index) & (x.index <= "2019-12-31")
        hol = masker(x.index, des[des["kode"] == kode]) & (x.index >= "2020-01-01")
        x["syariah"] = dev | hol
        x["kode"] = kode
        potong.append(x[x["syariah"] & (x.index >= "2010-01-01")])
    p = pd.concat(potong)
    p.index.name = "tgl"
    p = p.reset_index()
    p["nilai_idr"] = p["nilai"]
    p["harga_idr"] = p["harga"]
    return p


def kuantil_idx(p):
    g = p.dropna(subset=["nilai"]).groupby("tgl")
    q = pd.DataFrame({
        "nilai": g["nilai"].apply(lambda v: (v < AMBANG_IDR["nilai"]).mean()),
        "nilai_s2": g["nilai"].apply(lambda v: (v < AMBANG_IDR["nilai_s2"]).mean()),
        "harga": g["harga"].apply(lambda v: (v < AMBANG_IDR["harga"]).mean()),
        "harga_s3": g["harga"].apply(lambda v: (v < AMBANG_IDR["harga_s3"]).mean()),
        "n": g.size(),
    })
    return q


def lolos(p, cara, q=None):
    atr = p["atr_pct"].between(sc.ATR_MIN, sc.ATR_MAKS) & (p["vol_nol"] == 0)
    if cara == "kurs":
        return atr & (p["nilai_idr"] >= AMBANG_IDR["nilai"]) & (p["harga_idr"] >= AMBANG_IDR["harga"])
    g = p.groupby("tgl")
    bn = g["nilai"].transform(lambda v: v.quantile(q["nilai"]))
    bh = g["harga"].transform(lambda v: v.quantile(q["harga"]))
    return atr & (p["nilai"] >= bn) & (p["harga"] >= bh)


def per_tahun(p, kolom):
    x = p.assign(th=p["tgl"].dt.year)
    return x.groupby(["th", "tgl"])[kolom].sum().groupby("th").mean().round(1)


def kualitas_open(data, mulai=MULAI_DATA):
    baris = []
    for kode, df in data.items():
        df = df[(df.index >= mulai) & (df["volume"] > 0)]
        if df.empty:
            continue
        baris.append(pd.DataFrame({"th": df.index.year, "sama": (df["open"] == df["close"]).to_numpy(),
                                   "datar": ((df["high"] == df["low"])).to_numpy(),
                                   "lonjak": (df["close"].pct_change().abs() > 0.5).to_numpy()}))
    x = pd.concat(baris)
    return x.groupby("th").agg(open_sama_close=("sama", "mean"), high_sama_low=("datar", "mean"), lonjak_50=("lonjak", "sum")).round(3)


def survivorship_my(syr, data):
    ada = set(data)
    akhir = {k: df.index.max() for k, df in data.items()}
    hasil = {}
    d = syr.groupby("mulai")["kode"].apply(set)
    for tg, kode in d.items():
        hasil[str(tg.date())] = {"daftar": len(kode), "ada_yahoo": len(kode & ada),
                                 "data_berhenti_sebelum_2026": sum(1 for k in kode & ada if akhir[k] < pd.Timestamp("2026-06-01"))}
    return hasil


def jalankan():
    hasil = {}
    pi = panel_idx()
    q = kuantil_idx(pi)
    qd = q[q.index <= "2019-12-31"].median()
    qh = q[q.index >= "2020-01-01"].median()
    qa = q.median()
    hasil["idx_kuantil"] = {"dev": qd.round(3).to_dict(), "2020+": qh.round(3).to_dict(), "semua": qa.round(3).to_dict(),
                            "per_tahun": q.groupby(q.index.year).median().round(3).to_dict()}
    pi["atr_ok"] = pi["atr_pct"].between(sc.ATR_MIN, sc.ATR_MAKS) & (pi["vol_nol"] == 0)
    pi["lolos"] = lolos(pi, "kurs")
    hasil["idx"] = {"saham_syariah_per_hari": per_tahun(pi.assign(x=1), "x").to_dict(),
                    "atr_ok": per_tahun(pi, "atr_ok").to_dict(), "lolos_h11a": per_tahun(pi, "lolos").to_dict(),
                    "nilai_p": pi.groupby(pi["tgl"].dt.year)["nilai_idr"].quantile([.25, .5, .75]).unstack().div(1e9).round(2).to_dict()}
    for pasar in ("my", "us"):
        p, syr, data = panel_luar(pasar)
        p["atr_ok"] = p["atr_pct"].between(sc.ATR_MIN, sc.ATR_MAKS) & (p["vol_nol"] == 0)
        p["lolos_kurs"] = lolos(p, "kurs")
        p["lolos_persentil"] = lolos(p, "persentil", qa)
        p["lolos_kurs_s2"] = p["atr_ok"] & (p["nilai_idr"] >= AMBANG_IDR["nilai_s2"]) & (p["harga_idr"] >= AMBANG_IDR["harga"])
        p["lolos_kurs_s3"] = p["lolos_kurs"] & (p["harga_idr"] >= AMBANG_IDR["harga_s3"])
        kurs = hg.indeks_luar(KURS[pasar])["close"]
        r = {"rentang": [str(p["tgl"].min().date()), str(p["tgl"].max().date())],
             "kode_syariah": int(syr["kode"].nunique()), "kode_ada_yahoo": len(data),
             "saham_syariah_per_hari": per_tahun(p.assign(x=1), "x").to_dict(),
             "atr_ok": per_tahun(p, "atr_ok").to_dict(),
             "lolos_kurs": per_tahun(p, "lolos_kurs").to_dict(),
             "lolos_persentil": per_tahun(p, "lolos_persentil").to_dict(),
             "lolos_kurs_s2": per_tahun(p, "lolos_kurs_s2").to_dict(),
             "lolos_kurs_s3": per_tahun(p, "lolos_kurs_s3").to_dict(),
             "nilai_p_idr_miliar": p.groupby(p["tgl"].dt.year)["nilai_idr"].quantile([.25, .5, .75]).unstack().div(1e9).round(2).to_dict(),
             "ambang_kurs_lokal": {str(th): {"nilai_5M": round(5e9 / v, 0), "harga_50": round(50 / v, 4), "harga_200": round(200 / v, 4)}
                                   for th, v in kurs.groupby(kurs.index.year).median().items()},
             "ambang_persentil_lokal": p.groupby(p["tgl"].dt.year).apply(lambda g: pd.Series({
                 "nilai": g.groupby("tgl")["nilai"].quantile(qa["nilai"]).median(),
                 "harga": g.groupby("tgl")["harga"].quantile(qa["harga"]).median()})).round(4).to_dict(),
             "kualitas_open": kualitas_open(data).to_dict()}
        if pasar == "my":
            r["survivorship"] = survivorship_my(syr, data)
        hasil[pasar] = r
    hasil = json.loads(json.dumps(hasil, default=str))
    dt.simpan_hasil("h33_data", hasil)
    return hasil


def utama():
    a = argparse.ArgumentParser()
    a.add_argument("--tampil", action="store_true")
    x = a.parse_args()
    h = dt.baca_hasil("h33_data") if x.tampil else jalankan()
    print(json.dumps(h, indent=1, default=str)[:20000])


if __name__ == "__main__":
    utama()
