import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.ingest import koreksi_harga as kh

KOLEKSI = "kualitas_data"
KATEGORI = {
    "K1": "Salah skala sementara (lompat lalu balik)",
    "K2": "Aksi korporasi IDX tidak/salah disesuaikan",
    "K3": "Bar basi / harga beku padahal IDX ada transaksi",
    "K4": "Lompatan di luar ARA/ARB tanpa aksi korporasi tercatat",
    "IDX5": "2020+: close beda > 5% dari IDX resmi",
    "CELAH": "Hari tanpa data padahal IDX ada transaksi",
    "DUPLIKAT": "Tanggal ganda",
    "NOL": "Harga ≤ 0",
    "OHLC": "High < low atau close di luar rentang high-low",
}


def tercatat():
    c = dt.db()[kh.KOLEKSI]
    ids = {d["_id"] for d in c.find({}, {"_id": 1})}
    label = {(d["kode"], d.get("tgl") or d.get("ex_date") or d.get("dari")) for d in c.find({}, {"kode": 1, "tgl": 1, "ex_date": 1, "dari": 1})}
    return ids, label


def lompat_k4(kode, df, label):
    c = df["close"]
    r = c / c.shift(1)
    sp = df["stock_splits"].fillna(0) if "stock_splits" in df else pd.Series(0.0, index=df.index)
    gap = pd.Series(df.index, index=df.index).diff().dt.days
    m = ((r > kh.NAIK) | (r < kh.TURUN)) & (c.shift(1) >= 50) & ~df.index.isin(sp[sp > 0].index) & (gap <= 10)
    out = []
    for t in df.index[m.fillna(False)]:
        if (kode, str(t.date())) in label:
            continue
        out.append({"kategori": "K4", "kode": kode, "tgl": str(t.date()), "rasio": round(float(r[t]), 4),
                    "sebelum": float(c.shift(1)[t]), "sesudah": float(c[t])})
    return out


def dasar(kode, df, g):
    out = []
    dup = df.index[df.index.duplicated()]
    for t in sorted(set(dup)):
        out.append({"kategori": "DUPLIKAT", "kode": kode, "tgl": str(pd.Timestamp(t).date())})
    nol = df[(df[["open", "high", "low", "close"]] <= 0).any(axis=1)]
    if len(nol):
        out.append({"kategori": "NOL", "kode": kode, "tgl": str(nol.index[0].date()), "jumlah": int(len(nol)), "sampai": str(nol.index[-1].date())})
    ok = (df[["open", "high", "low", "close"]] > 0).all(axis=1)
    x = df[ok]
    salah = x[(x["high"] < x["low"] * (1 - 1e-6)) | (x["close"] > x["high"] * (1 + 1e-3)) | (x["close"] < x["low"] * (1 - 1e-3))]
    if len(salah):
        out.append({"kategori": "OHLC", "kode": kode, "tgl": str(salah.index[0].date()), "jumlah": int(len(salah)), "sampai": str(salah.index[-1].date())})
    if g is not None and len(df):
        aktif = g[(g["Volume"] > 0) & (g.index >= max(df.index.min(), kh.IDX_MULAI)) & (g.index <= df.index.max())]
        hilang = aktif.index.difference(df.index)
        if len(hilang):
            out.append({"kategori": "CELAH", "kode": kode, "tgl": str(hilang[0].date()), "jumlah": int(len(hilang)), "sampai": str(hilang[-1].date())})
    return out


def cek_satu(kode, df, g, ids, label, koleksi):
    temuan = []
    df = df.sort_index().copy()
    df.index = pd.to_datetime(df.index)
    temuan += dasar(kode, df, g)
    df = df[~df.index.duplicated(keep="last")]
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    if len(df) < 5:
        return temuan
    kerja = df
    if g is not None:
        fk, kerja = kh.faktor_yahoo(kode, df, g)
        for r in fk:
            if r["jenis"] == "faktor" and f"faktor:{kode}:{r['ex_date']}" not in ids:
                temuan.append({"kategori": "K2", "kode": kode, "tgl": r["ex_date"], "faktor_idx": r["faktor_idx"], "faktor": r["faktor"], "luput": r.get("luput")})
    for r in kh.usulan_pra2020(kode, kerja):
        if f"{r['jenis']}:{kode}:{r['tgl']}" not in ids:
            temuan.append({"kategori": "K1", "kode": kode, "tgl": r["tgl"], "cara": r["cara"]})
    if g is not None:
        for r in kh.sel_idx(kode, df, kerja, g):
            if f"sel:{kode}:{r['tgl']}" not in ids:
                kat = "K3" if r["kategori"] == "K3" else "IDX5"
                temuan.append({"kategori": kat, "kode": kode, "tgl": r["tgl"], "yahoo_close": r["bukti"]["yahoo_close"], "idx_close": r["bukti"]["idx_close"]})
    temuan += lompat_k4(kode, kerja, label)
    for t in temuan:
        t["koleksi"] = koleksi
    return temuan


def jalankan(koleksi=("harga", "harian"), simpan=True):
    mulai = datetime.now()
    resmi = kh.idx_resmi()
    ids, label = tercatat()
    temuan = []
    jumlah = {}
    for kol in koleksi:
        semua = hg.banyak() if kol == "harga" else hg.harian_banyak()
        semua.pop("_ihsg", None)
        jumlah[kol] = len(semua)
        for k, df in semua.items():
            temuan += cek_satu(k, df, resmi.get(k), ids, label, kol)
    t = pd.DataFrame(temuan)
    per_kat = t.groupby(["kategori", "koleksi"]).size().unstack(fill_value=0).to_dict("index") if len(t) else {}
    terakhir_idx = max(g.index.max() for g in resmi.values())
    tahan = [{"_id": d["_id"], "kode": d["kode"], "jenis": d["jenis"], "tgl": d.get("tgl") or d.get("ex_date") or d.get("dari"), "keputusan": d.get("keputusan")}
             for d in dt.db()[kh.KOLEKSI].find({"status": "tahan"})]
    kode_tahan = {x["kode"] for x in tahan}
    dok = {"waktu": mulai, "selesai": datetime.now(), "status": "LULUS" if not len(t) and not tahan else "ADA TEMUAN", "jumlah_temuan": int(len(t)),
           "tahan": tahan[:500], "jumlah_tahan": len(tahan),
           "per_kategori": per_kat, "kode_temuan": sorted((set(t["kode"]) if len(t) else set()) | kode_tahan), "temuan": temuan[:2000], "jumlah_kode": jumlah,
           "cakupan": {"idx_mulai": str(kh.IDX_MULAI.date()), "idx_sampai": str(terakhir_idx.date()),
                       "catatan": "2020+ dicek terhadap data resmi IDX; sebelum 2020 hanya deteksi internal (K1/K4) dan bukti dokumen."}}
    if simpan:
        dt.db()[KOLEKSI].insert_one(dok)
    return dok


def harian_ikut(kode):
    aturan = kh.aturan()
    for k in sorted(kode):
        df = hg.harian(k)
        if df is None:
            continue
        df2, _ = kh.terapkan(df, k, aturan)
        dt.tulis(f"harian/{k}", df2)


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tanpa-otomatis", action="store_true")
    a = ap.parse_args()
    if not a.tanpa_otomatis:
        h = kh.perbarui_otomatis()
        print(f"aksi korporasi baru: {len(h['aktif'])} diterapkan otomatis, {len(h['tahan'])} ditahan (perlu keputusan user)")
        for x in h["aktif"]:
            print(f"  diterapkan: {x['_id']} ({x['keputusan']})")
        for x in h["tahan"]:
            print(f"  DITAHAN: {x['_id']} ({x['keputusan']})")
        if h["aktif"]:
            harian_ikut({x["kode"] for x in h["aktif"]})
    dok = jalankan()
    print(f"cek kualitas data: {dok['status']}, {dok['jumlah_temuan']} temuan baru, cakupan IDX s/d {dok['cakupan']['idx_sampai']}")
    for kat, v in dok["per_kategori"].items():
        print(f"  {kat} ({KATEGORI.get(kat, kat)}): {v}")
    print("SELESAI")


if __name__ == "__main__":
    utama()
