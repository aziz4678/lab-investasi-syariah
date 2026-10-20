import argparse
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.riset.swing_target3 import baca_ticker, rapikan_index
from backend.db import koneksi as d

PASAR = {
    "ihsg": "^JKSE",
    "usdidr": "IDR=X",
    "minyak": "CL=F",
    "emas": "GC=F",
    "sp500": "^GSPC",
    "vix": "^VIX",
    "em": "EEM",
}


def ambil_batch(daftar, mulai):
    mentah = yf.download(
        daftar, start=mulai, interval="1d", auto_adjust=False, actions=True,
        group_by="ticker", threads=True, progress=False,
    )
    hasil = {}
    for t in daftar:
        try:
            df = mentah[t].dropna(subset=["Open", "High", "Low", "Close"]).copy()
        except KeyError:
            continue
        if df.empty:
            continue
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        hasil[t] = rapikan_index(df)
    return hasil


def unduh_harga(daftar, mulai, ukuran):
    sisa = list(daftar)
    for coba in range(3):
        gagal = []
        for i in range(0, len(sisa), ukuran):
            potong = sisa[i:i + ukuran]
            hasil = ambil_batch(potong, mulai)
            for t in potong:
                if t in hasil:
                    dt.tulis(f"harga/{t.replace('.JK', '')}", hasil[t])
                else:
                    gagal.append(t)
            print(f"  batch {i // ukuran + 1}: {len(hasil)}/{len(potong)}")
        if not gagal:
            break
        print(f"percobaan {coba + 1}: {len(gagal)} gagal, ulang")
        sisa = gagal
        time.sleep(5)
    return gagal


def unduh_pasar(mulai):
    potongan = {}
    for nama, kode in PASAR.items():
        try:
            df = yf.download(kode, start=mulai, interval="1d", auto_adjust=True, progress=False)
        except Exception:
            df = None
        if df is None or df.empty:
            print(f"  {nama} ({kode}) gagal")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        potongan[nama] = rapikan_index(df)["Close"]
    pasar = pd.DataFrame(potongan)
    dt.tulis("pasar", pasar)
    print(f"pasar: {list(pasar.columns)}, {pasar.index.min().date()} s/d {pasar.index.max().date()}")


def unduh_info(daftar):
    kolom = ["sector", "industry", "marketCap", "sharesOutstanding", "floatShares",
             "heldPercentInsiders", "heldPercentInstitutions", "trailingPE", "priceToBook",
             "returnOnEquity", "debtToEquity", "dividendYield", "beta"]
    baris = []
    for i, t in enumerate(daftar, 1):
        try:
            info = yf.Ticker(t).info
        except Exception:
            info = {}
        baris.append({"ticker": t, **{k: info.get(k) for k in kolom}})
        if i % 25 == 0:
            print(f"  info {i}/{len(daftar)}")
            time.sleep(2)
    df = pd.DataFrame(baris).dropna(axis=1, how="all")
    d.simpan_df("info_saham", df)
    print(f"info: {df['sector'].notna().sum() if 'sector' in df else 0}/{len(df)} punya sektor")


def ringkas():
    baris = []
    for kode, df in sorted(dt.baca_banyak("harga").items()):
        baris.append({
            "ticker": kode, "mulai": df.index.min().date(), "akhir": df.index.max().date(),
            "baris": len(df), "vol_nol_pct": round((df["volume"] == 0).mean() * 100, 1),
            "dividen": int((df.get("dividends", pd.Series(dtype=float)) > 0).sum()),
            "split": int((df.get("stock_splits", pd.Series(dtype=float)) > 0).sum()),
        })
    r = pd.DataFrame(baris)
    dt.simpan_hasil("ringkasan_data", r)
    print(f"\n{len(r)} ticker | median baris {int(r['baris'].median())} | "
          f"mulai paling awal {r['mulai'].min()} | akhir terbaru {r['akhir'].max()}")
    print(f"ticker < 500 baris: {(r['baris'] < 500).sum()} | volume nol > 20%: {(r['vol_nol_pct'] > 20).sum()}")
    print(f"total kejadian dividen {r['dividen'].sum()}, split {r['split'].sum()}")


def utama():
    p = argparse.ArgumentParser()
    p.add_argument("--ticker-file", default="data/syariah_tickers.txt")
    p.add_argument("--mulai", default="2010-01-01")
    p.add_argument("--batch", type=int, default=40)
    p.add_argument("--tanpa-info", action="store_true")
    a = p.parse_args()

    daftar = baca_ticker(a.ticker_file)
    print(f"unduh harga {len(daftar)} ticker sejak {a.mulai}")
    gagal = unduh_harga(daftar, a.mulai, a.batch)
    if gagal:
        print(f"tetap gagal: {gagal}")
    unduh_pasar(a.mulai)
    if not a.tanpa_info:
        unduh_info(daftar)
    ringkas()


if __name__ == "__main__":
    utama()
