import logging
import time

import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.ingest import koreksi_harga as kh
from backend.ingest.final import buang_belum_final
from backend.research.swing_target3 import rapikan_index

JII = "harian_indeks/JII"


def unduh(daftar):
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    hasil = {}
    aturan = kh.aturan()
    for i in range(0, len(daftar), 60):
        potong = [t + ".JK" for t in daftar[i:i + 60]]
        mentah = yf.download(potong, period="2y", interval="1d", auto_adjust=False, actions=True,
                             group_by="ticker", threads=True, progress=False)
        for t in potong:
            try:
                df = mentah[t].dropna(subset=["Open", "High", "Low", "Close"]).copy()
            except KeyError:
                continue
            if df.empty:
                continue
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            df = buang_belum_final(rapikan_index(df), t)
            if df.empty:
                continue
            df, catatan = kh.terapkan(df, t[:-3], aturan)
            for x in catatan:
                print(f"  koreksi: {x}")
            dt.tulis(f"harian/{t[:-3]}", df)
            hasil[t[:-3]] = df
        time.sleep(1)
    hilang = sorted(set(daftar) - set(hasil))
    if hilang:
        print(f"{len(hilang)} kode tidak ada di Yahoo (delisting / ganti kode / tidak tercatat), dilewati: {', '.join(hilang)}")
    ihsg = yf.download("^JKSE", period="2y", interval="1d", auto_adjust=True, progress=False)
    if isinstance(ihsg.columns, pd.MultiIndex):
        ihsg.columns = ihsg.columns.get_level_values(0)
    ihsg = buang_belum_final(rapikan_index(ihsg)["Close"].dropna(), "^JKSE")
    dt.tulis("harian/_ihsg", ihsg.to_frame("ihsg"))
    return hasil, ihsg


def unduh_jii():
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    x = yf.download("^JKII", period="2y", interval="1d", auto_adjust=True, progress=False)
    if x is None or x.empty:
        return
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = x.columns.get_level_values(0)
    s = buang_belum_final(rapikan_index(x)["Close"].dropna(), "^JKII")
    if len(s):
        dt.tulis(JII, s.to_frame("jii"))
