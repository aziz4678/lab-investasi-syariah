import argparse
import io
import time
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

from backend.db import data as dt
from backend.ingest.final import buang_belum_final
from backend.research.swing_target3 import rapikan_index

MULAI = "2005-01-01"
BATCH = 40
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LabInvestasiSyariah"}
SPUS = "https://www.sp-funds.com/wp-content/uploads/data/TidalFG_Holdings_SPUS.csv"
PASAR = {"my": {"koleksi": "harga_my", "akhiran": ".KL"}, "us": {"koleksi": "harga_us", "akhiran": ""}}
INDEKS = {"my_titans25": "0821EA.KL", "my_klci_etf": "0820EA.KL", "my_klci": "^KLSE", "us_djim": "^IMUS",
          "us_spus": "SPUS", "us_hlal": "HLAL", "us_sp500": "^GSPC", "myridr": "MYRIDR=X", "usdidr": "IDR=X",
          "gl_djim_titans": "^IMXL", "gl_msci_world_islamic": "ISDW.L"}


def kode_my():
    s = set()
    for d in dt.db()["syariah_my"].find({"jumlah": {"$gt": 0}}, {"kode": 1}):
        s |= set(d["kode"])
    return sorted(s)


def perbarui_spus():
    teks = requests.get(SPUS, headers=UA, timeout=60).text
    d = pd.read_csv(io.StringIO(teks), dtype={"CUSIP": str})
    d = d[d["StockTicker"].notna() & d["CUSIP"].notna()]
    kode = sorted({str(k).strip().replace(".", "-").replace("/", "-") for k in d["StockTicker"] if str(k).strip() and str(k).strip().upper() != "CASH"})
    tanggal = pd.to_datetime(d["Date"].iloc[0]).to_pydatetime()
    dt.simpan_arsip(f"syariah_us/spus_{tanggal:%Y-%m-%d}.csv", teks, folder="syariah_us")
    dt.db()["syariah_us"].replace_one({"_id": f"spus_{tanggal:%Y-%m-%d}"}, {
        "_id": f"spus_{tanggal:%Y-%m-%d}", "sumber": "SPUS holdings (sp-funds.com)", "tanggal": tanggal, "kode": kode,
        "jumlah": len(kode), "diperbarui": datetime.now()}, upsert=True)
    return kode


def kode_us():
    d = dt.db()["syariah_us"].find_one(sort=[("tanggal", -1)])
    return d["kode"] if d else perbarui_spus()


def ambil(daftar, mulai):
    mentah = yf.download(daftar, start=mulai, interval="1d", auto_adjust=False, actions=True,
                         group_by="ticker", threads=True, progress=False)
    hasil = {}
    for t in daftar:
        try:
            df = mentah[t].dropna(subset=["Open", "High", "Low", "Close"]).copy()
        except KeyError:
            continue
        if df.empty:
            continue
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = buang_belum_final(rapikan_index(df), t)
        if not df.empty:
            hasil[t] = df
    return hasil


def unduh(pasar, mulai=MULAI):
    cfg = PASAR[pasar]
    kode = kode_my() if pasar == "my" else kode_us()
    simbol = [k + cfg["akhiran"] for k in kode]
    sisa, ok = simbol, 0
    for coba in range(3):
        gagal = []
        for i in range(0, len(sisa), BATCH):
            potong = sisa[i:i + BATCH]
            hasil = ambil(potong, mulai)
            for t in potong:
                if t in hasil:
                    dt.tulis(f"{cfg['koleksi']}/{t.removesuffix(cfg['akhiran']) if cfg['akhiran'] else t}", hasil[t])
                    ok += 1
                else:
                    gagal.append(t)
            print(f"  {pasar} batch {i // BATCH + 1}: {len(hasil)}/{len(potong)}", flush=True)
        if not gagal:
            break
        sisa = gagal
        time.sleep(5)
    dt.db()["pasar_luar_info"].replace_one({"_id": pasar}, {"_id": pasar, "kode": len(kode), "ada": ok, "tidak_ada": sorted(t.removesuffix(cfg["akhiran"]) if cfg["akhiran"] else t for t in sisa if gagal),
                                                           "mulai": mulai, "diperbarui": datetime.now()}, upsert=True)
    print(f"{pasar}: {ok}/{len(kode)} ada di Yahoo", flush=True)


def unduh_indeks(pilih=None):
    for nama, s in INDEKS.items():
        if pilih and nama not in pilih:
            continue
        h = yf.download(s, start="2000-01-01", interval="1d", auto_adjust=False, actions=True, progress=False, multi_level_index=False)
        if h is None or h.empty:
            print(f"{nama}: kosong", flush=True)
            continue
        h.columns = [c.lower().replace(" ", "_") for c in h.columns]
        h = buang_belum_final(rapikan_index(h), s)
        dt.tulis(f"indeks_luar/{nama}", h)
        print(f"{nama} ({s}): {len(h)} baris {h.index.min().date()} s/d {h.index.max().date()}", flush=True)


def utama():
    a = argparse.ArgumentParser()
    a.add_argument("perintah", choices=["my", "us", "spus", "indeks", "semua"])
    a.add_argument("--nama", nargs="*")
    x = a.parse_args()
    if x.perintah in ("spus", "semua"):
        print(f"SPUS: {len(perbarui_spus())} kode", flush=True)
    if x.perintah in ("indeks", "semua"):
        unduh_indeks(x.nama)
    if x.perintah in ("my", "semua"):
        unduh("my")
    if x.perintah in ("us", "semua"):
        unduh("us")


if __name__ == "__main__":
    utama()
