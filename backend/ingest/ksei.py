import calendar
import time
import zipfile

import pandas as pd

from backend.db import data as dt

URL = "https://web.ksei.co.id/Download/BalanceposEfek{}.zip"
MULAI = (2009, 12)
TIPE = ["IS", "CP", "PF", "IB", "ID", "MF", "SC", "FD", "OT"]
INSTITUSI_LOKAL = ["IS", "PF", "IB", "MF"]


def ambil(url):
    from curl_cffi import requests
    for coba in range(3):
        try:
            return requests.get(url, impersonate="chrome", timeout=90)
        except Exception:
            time.sleep(5 * (coba + 1))
    return None


def bulan_bulan(sampai):
    th, bl = MULAI
    while (th, bl) <= sampai:
        yield th, bl
        th, bl = (th + 1, 1) if bl == 12 else (th, bl + 1)


def unduh_bulan(th, bl):
    hari_akhir = calendar.monthrange(th, bl)[1]
    for h in range(hari_akhir, hari_akhir - 15, -1):
        tgl = f"{th}{bl:02d}{h:02d}"
        r = ambil(URL.format(tgl))
        if r is not None and r.status_code == 200 and r.content[:2] == b"PK":
            dt.simpan_arsip(f"BalanceposEfek{tgl}.zip", r.content, "ksei")
            return tgl
    return None


def unduh():
    from concurrent.futures import ThreadPoolExecutor
    hari_ini = pd.Timestamp.today()
    akhir = (hari_ini.year, hari_ini.month - 1) if hari_ini.month > 1 else (hari_ini.year - 1, 12)
    ada = {n[-12:-6] for n in dt.daftar_arsip(folder="ksei", awalan="BalanceposEfek")}
    perlu = [(th, bl) for th, bl in bulan_bulan(akhir) if f"{th}{bl:02d}" not in ada]
    print(f"{len(ada)} bulan sudah ada, {len(perlu)} perlu diunduh")
    with ThreadPoolExecutor(6) as ex:
        hasil = list(ex.map(lambda x: (x, unduh_bulan(*x)), perlu))
    hilang = [f"{th}-{bl:02d}" for (th, bl), tgl in hasil if tgl is None]
    print(f"selesai, {len(dt.daftar_arsip(folder='ksei', awalan='BalanceposEfek'))} file, tidak ditemukan: {hilang}")


def baca_zip(f):
    with zipfile.ZipFile(dt.bytes_io(dt.baca_arsip(f)) if isinstance(f, str) else f) as z:
        teks = z.read(z.namelist()[0]).decode("latin1")
    baris = [b.split("|") for b in teks.strip().splitlines()]
    kolom = ["tgl", "kode", "jenis", "saham", "harga"] + [f"L_{t}" for t in TIPE] + ["L_total"] + [f"F_{t}" for t in TIPE] + ["F_total"]
    df = pd.DataFrame([b[:len(kolom)] for b in baris[1:] if len(b) >= len(kolom)], columns=kolom)
    df = df[df["jenis"].str.strip().str.upper() == "EQUITY"].drop(columns="jenis")
    df["tgl"] = pd.to_datetime(df["tgl"].str.strip(), format="%d-%b-%Y")
    df["kode"] = df["kode"].str.strip().str.upper()
    for k in kolom[3:]:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    return df


def bangun():
    df = pd.concat([baca_zip(n) for n in dt.daftar_arsip(folder="ksei", awalan="BalanceposEfek")], ignore_index=True)
    df = df[df["saham"] > 0].drop_duplicates(["tgl", "kode"])
    df = df.reset_index(drop=True)
    dt.tulis("ksei", df)
    cek = (df[[f"L_{t}" for t in TIPE]].sum(axis=1) - df["L_total"]).abs() / df["saham"]
    print(f"{len(df):,} baris, {df['kode'].nunique()} kode, {df['tgl'].nunique()} bulan ({df['tgl'].min().date()} s/d {df['tgl'].max().date()})")
    print(f"jumlah tipe lokal = total lokal: {(cek < 1e-6).mean() * 100:.1f}% | rata-rata (lokal+asing)/saham beredar: "
          f"{((df['L_total'] + df['F_total']) / df['saham']).median() * 100:.1f}% (median)")
    return df


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "unduh":
        unduh()
    bangun()
