import argparse
import logging
import time

import numpy as np
import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import koreksi_harga as kh
from backend.ingest.final import buang_belum_final
from backend.research.swing_target3 import rapikan_index

PASAR = {
    "ihsg": "^JKSE",
    "usdidr": "IDR=X",
    "minyak": "CL=F",
    "emas": "GC=F",
    "sp500": "^GSPC",
    "vix": "^VIX",
    "em": "EEM",
}
MULAI = "2010-01-01"
TIMPA_HARI = 21
BATCH = 40
TOLERANSI = 1e-4


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
        df = buang_belum_final(rapikan_index(df), t)
        if not df.empty:
            hasil[t] = df
    return hasil


def unduh_harga(daftar, mulai, ukuran=BATCH, aturan=None):
    aturan = kh.aturan() if aturan is None else aturan
    sisa = list(daftar)
    for coba in range(3):
        gagal = []
        for i in range(0, len(sisa), ukuran):
            potong = sisa[i:i + ukuran]
            hasil = ambil_batch(potong, mulai)
            for t in potong:
                if t in hasil:
                    kode = t.replace(".JK", "")
                    df, catatan = kh.terapkan(hasil[t], kode, aturan)
                    for c in catatan:
                        print(f"  koreksi: {c}", flush=True)
                    dt.tulis(f"harga/{kode}", df)
                else:
                    gagal.append(t)
            print(f"  batch {i // ukuran + 1}: {len(hasil)}/{len(potong)}", flush=True)
        if not gagal:
            break
        print(f"percobaan {coba + 1}: {len(gagal)} tidak ada data, ulang", flush=True)
        sisa = gagal
        time.sleep(5)
    return gagal


def faktor_berubah(lama, baru, kolom_adj, kolom_dasar):
    sama = lama.index.intersection(baru.index)
    if not len(sama):
        return True
    t = sama[0]
    fl = lama.at[t, kolom_adj] / lama.at[t, kolom_dasar] if kolom_dasar else lama.at[t, kolom_adj]
    fb = baru.at[t, kolom_adj] / baru.at[t, kolom_dasar] if kolom_dasar else baru.at[t, kolom_adj]
    return not (np.isfinite(fl) and np.isfinite(fb)) or abs(fb / fl - 1) > TOLERANSI


def close_berubah(lama, baru):
    sama = lama.index.intersection(baru.index)
    if not len(sama):
        return False
    a, b = lama.loc[sama, "close"], baru.loc[sama, "close"]
    ok = (a > 0) & (b > 0)
    beda = np.abs(np.log(b[ok] / a[ok])) > 0.02
    return int(beda.sum()) >= 2


def gabung(lama, baru):
    return pd.concat([lama[lama.index < baru.index.min()], baru.reindex(columns=lama.columns)]).sort_index()


def mulai_timpa():
    return (pd.Timestamp.today().normalize() - pd.Timedelta(days=TIMPA_HARI)).strftime("%Y-%m-%d")


def perbarui_harga(penuh=False):
    kode = dt.daftar("harga")
    simbol = [k + ".JK" for k in kode]
    if penuh:
        print(f"unduh ulang penuh harga {len(simbol)} saham sejak {MULAI}", flush=True)
        gagal = unduh_harga(simbol, MULAI)
        print(f"selesai: {len(simbol) - len(gagal)} diperbarui, {len(gagal)} tidak ada di Yahoo (data lama dipertahankan)")
        return
    mulai = mulai_timpa()
    aturan = kh.aturan()
    print(f"perbarui harga {len(simbol)} saham: timpa ulang data sejak {mulai}, {len(aturan)} aturan koreksi aktif", flush=True)
    ditimpa, kosong, lengkap = 0, 0, []
    for i in range(0, len(simbol), BATCH):
        potong = simbol[i:i + BATCH]
        hasil = ambil_batch(potong, mulai)
        for t in potong:
            if t not in hasil:
                kosong += 1
                continue
            lama = dt.baca(f"harga/{t[:-3]}")
            lama.index = pd.to_datetime(lama.index)
            baru, catatan = kh.terapkan(hasil[t], t[:-3], aturan)
            for c in catatan:
                print(f"  koreksi: {c}", flush=True)
            batas = kh.batas_terbaru(t[:-3], aturan)
            if (batas is not None and batas > pd.Timestamp(mulai)) or faktor_berubah(lama, baru, "adj_close", "close") or close_berubah(lama, baru):
                lengkap.append(t)
                continue
            dt.tulis(f"harga/{t[:-3]}", gabung(lama, baru))
            ditimpa += 1
        print(f"  batch {i // BATCH + 1}: {len(hasil)}/{len(potong)} ada data", flush=True)
    if lengkap:
        print(f"{len(lengkap)} saham ada dividen/split/penyesuaian harga baru atau data terputus, unduh penuh: {', '.join(t[:-3] for t in lengkap[:20])}", flush=True)
        unduh_harga(lengkap, MULAI, aturan=aturan)
    print(f"selesai: {ditimpa} ditimpa ulang, {len(lengkap)} diunduh penuh, {kosong} tanpa data baru (delisting/suspensi, data lama dipertahankan)")


def ambil_pasar(kode, mulai):
    try:
        df = yf.download(kode, start=mulai, interval="1d", auto_adjust=True, progress=False)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    s = buang_belum_final(rapikan_index(df)["Close"].dropna(), kode)
    return s if len(s) else None


def perbarui_pasar(penuh=False):
    lama = None if penuh or not dt.ada("pasar") else dt.baca("pasar")
    mulai = MULAI if lama is None else mulai_timpa()
    kolom = {}
    for nama, kode in PASAR.items():
        s = ambil_pasar(kode, mulai)
        if s is None:
            print(f"  {nama} ({kode}) gagal, data lama dipertahankan", flush=True)
            if lama is not None and nama in lama:
                kolom[nama] = lama[nama].dropna()
            continue
        if lama is not None and nama in lama:
            l = lama[nama].dropna()
            if faktor_berubah(l.to_frame("x"), s.to_frame("x"), "x", None):
                print(f"  {nama}: riwayat berubah (penyesuaian), unduh penuh", flush=True)
                s = ambil_pasar(kode, MULAI)
                if s is None:
                    kolom[nama] = l
                    continue
            else:
                s = pd.concat([l[l.index < s.index.min()], s])
        kolom[nama] = s
        print(f"  {nama}: s/d {s.index.max().date()} ({s.iloc[-1]:.2f})", flush=True)
    pasar = pd.DataFrame(kolom).sort_index()
    pasar.index.name = "Date"
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
            "ticker": kode, "mulai": df.index.min(), "akhir": df.index.max(),
            "baris": len(df), "vol_nol_pct": round((df["volume"] == 0).mean() * 100, 1),
            "dividen": int((df.get("dividends", pd.Series(dtype=float)) > 0).sum()),
            "split": int((df.get("stock_splits", pd.Series(dtype=float)) > 0).sum()),
        })
    r = pd.DataFrame(baris)
    dt.simpan_hasil("ringkasan_data", r)
    print(f"\n{len(r)} ticker | median baris {int(r['baris'].median())} | "
          f"mulai paling awal {r['mulai'].min().date()} | akhir terbaru {r['akhir'].max().date()}")
    print(f"ticker < 500 baris: {(r['baris'] < 500).sum()} | volume nol > 20%: {(r['vol_nol_pct'] > 20).sum()}")
    print(f"total kejadian dividen {r['dividen'].sum()}, split {r['split'].sum()}")


def indeks_panjang():
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    h = yf.Ticker("^JKII").history(period="max", auto_adjust=False)
    h.index = h.index.tz_localize(None).normalize()
    jkii = h[["Close"]].rename(columns={"Close": "close"}).dropna()
    if len(jkii):
        dt.tulis("indeks/JKII", jkii)
        print(f"indeks/JKII: {len(jkii)} hari s/d {jkii.index.max().date()}")
    g = yf.Ticker("GC=F").history(period="max", auto_adjust=False)
    g.index = g.index.tz_localize(None).normalize()
    emas = buang_belum_final(g[["Close"]].rename(columns={"Close": "close"}).dropna(), "GC=F")
    if len(emas):
        dt.tulis("pasar_panjang/emas_usd", emas)
        print(f"pasar_panjang/emas_usd: {len(emas)} hari s/d {emas.index.max().date()}")


def utama():
    p = argparse.ArgumentParser()
    p.add_argument("perintah", choices=["harga", "pasar", "penuh", "info", "indeks_panjang"])
    a = p.parse_args()
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    if a.perintah == "indeks_panjang":
        indeks_panjang()
    elif a.perintah == "harga":
        perbarui_harga()
    elif a.perintah == "pasar":
        perbarui_pasar()
    elif a.perintah == "penuh":
        perbarui_harga(penuh=True)
        perbarui_pasar(penuh=True)
        ringkas()
    else:
        unduh_info([k + ".JK" for k in dt.daftar("harga")])


if __name__ == "__main__":
    utama()
