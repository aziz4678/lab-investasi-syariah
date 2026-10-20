import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

from backend.db import data as dt

URL_DEFAULT = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"

HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.idx.co.id/id/data-pasar/laporan-statistik/ringkasan-perdagangan/",
}

KOLOM = ["tgl", "ticker", "volume", "asing_beli", "asing_jual"]


def baca_ticker(path):
    if not path:
        return None
    sumber = Path(path).read_text().splitlines() if Path(path).exists() else dt.baca_daftar(Path(path).stem)
    if not sumber:
        return None
    hasil = set()
    for baris in sumber:
        t = baris.strip().upper()
        if not t or t.startswith("#"):
            continue
        hasil.add(t if t.endswith(".JK") else t + ".JK")
    return hasil


def cari_kolom(df, calon):
    peta = {c.lower(): c for c in df.columns}
    for x in calon:
        if x.lower() in peta:
            return peta[x.lower()]
    return None


def parse(isi, tanggal):
    baris = isi.get("data") if isinstance(isi, dict) else isi
    if not baris:
        return pd.DataFrame(columns=KOLOM)
    df = pd.DataFrame(baris)
    kode = cari_kolom(df, ["StockCode", "Code", "KodeSaham"])
    vol = cari_kolom(df, ["Volume"])
    beli = cari_kolom(df, ["ForeignBuy"])
    jual = cari_kolom(df, ["ForeignSell"])
    if None in (kode, vol, beli, jual):
        raise RuntimeError("nama kolom nggak cocok, kolom yang ada: " + ", ".join(map(str, df.columns)))
    out = pd.DataFrame({
        "tgl": tanggal.strftime("%Y-%m-%d"),
        "ticker": df[kode].astype(str).str.strip().str.upper() + ".JK",
        "volume": pd.to_numeric(df[vol], errors="coerce"),
        "asing_beli": pd.to_numeric(df[beli], errors="coerce"),
        "asing_jual": pd.to_numeric(df[jual], errors="coerce"),
    })
    return out.dropna()


def ambil_satu_hari(sesi, tanggal, url, batas_waktu):
    r = sesi.get(url, params={"length": 9999, "start": 0, "date": tanggal.strftime("%Y%m%d")}, timeout=batas_waktu)
    if r.status_code == 403:
        raise RuntimeError("403 diblokir proteksi situs, pakai jalur browser (idx_asing_browser.js lalu mode impor)")
    if r.status_code != 200:
        raise RuntimeError(f"status HTTP {r.status_code}")
    try:
        isi = r.json()
    except ValueError:
        raise RuntimeError("respons bukan JSON, kemungkinan diblokir CAPTCHA atau Cloudflare")
    return parse(isi, tanggal)


def buat_sesi(cookie):
    sesi = requests.Session()
    sesi.headers.update(HEADER)
    if cookie:
        sesi.headers["Cookie"] = cookie
    return sesi


def uji(a):
    sesi = buat_sesi(a.cookie)
    hari = pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=8)[::-1]
    for d in hari:
        try:
            df = ambil_satu_hari(sesi, d, a.url, a.batas_waktu)
        except Exception as e:
            print(f"{d.date()} gagal: {e}")
            continue
        if df.empty:
            print(f"{d.date()} kosong (mungkin libur)")
            continue
        df["net"] = df["asing_beli"] - df["asing_jual"]
        print(f"{d.date()} berhasil: {len(df)} saham")
        print(df.sort_values("net", ascending=False).head(5).to_string(index=False))
        print("\nCek manual: bandingkan net asing 1-2 saham di atas dengan tampilan di situs IDX atau aplikasi sekuritas lo.")
        print("Kalau cocok, lanjut ke perintah 'unduh'.")
        return
    print("\nsemua percobaan gagal. Kalau 403, pakai jalur browser: jalankan idx_asing_browser.js di konsol halaman IDX, lalu mode impor.")


def unduh(a):
    sesi = buat_sesi(a.cookie)
    keluar = Path(a.keluar)
    catatan = Path(a.keluar + ".tgl")
    sudah = set(catatan.read_text().split()) if catatan.exists() else set()
    filter_ticker = baca_ticker(a.ticker_file)
    selesai = pd.Timestamp(a.selesai) if a.selesai else pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    hari = [d for d in pd.bdate_range(a.mulai, selesai) if d.strftime("%Y-%m-%d") not in sudah]
    print(f"{len(hari)} hari perlu diunduh, {len(sudah)} sudah ada")

    gagal_beruntun = 0
    for n, d in enumerate(hari, 1):
        try:
            df = ambil_satu_hari(sesi, d, a.url, a.batas_waktu)
        except Exception as e:
            gagal_beruntun += 1
            print(f"{d.date()} gagal: {e}", flush=True)
            if gagal_beruntun >= 5:
                print("5 kegagalan beruntun, berhenti. Jalankan lagi nanti, progres tersimpan.")
                break
            time.sleep(a.jeda * 3)
            continue
        gagal_beruntun = 0
        if filter_ticker is not None and not df.empty:
            df = df[df["ticker"].isin(filter_ticker)]
        if not df.empty:
            df.to_csv(keluar, mode="a", header=not keluar.exists(), index=False)
        with open(catatan, "a") as f:
            f.write(d.strftime("%Y-%m-%d") + "\n")
        if n % 50 == 0:
            print(f"{n}/{len(hari)} hari selesai ({d.date()})", flush=True)
        time.sleep(a.jeda)
    print(f"selesai, data di {keluar}")


def impor(a):
    filter_ticker = baca_ticker(a.ticker_file)
    potongan = []
    berkas = sorted(Path(".").glob(a.pola))
    if not berkas:
        print(f"nggak ada file yang cocok dengan {a.pola}")
        return
    for f in berkas:
        mentah = json.loads(f.read_text(encoding="utf-8"))
        for hari in mentah:
            if not hari.get("data"):
                continue
            df = pd.DataFrame(hari["data"], columns=hari["kolom"])
            df.insert(0, "tgl", hari["tgl"])
            potongan.append(df)
        print(f"{f.name}: {len(mentah)} hari dibaca")
    if not potongan:
        print("semua hari kosong, cek konsol browser")
        return
    semua = pd.concat(potongan, ignore_index=True)
    semua["tgl"] = pd.to_datetime(semua["tgl"])
    semua["StockCode"] = semua["StockCode"].astype(str).str.strip().str.upper()
    for kol in semua.columns.drop(["tgl", "StockCode", "Remarks"]):
        semua[kol] = pd.to_numeric(semua[kol], errors="coerce")
    semua = semua.drop_duplicates(["tgl", "StockCode"]).sort_values(["tgl", "StockCode"])
    dt.tulis("idx_harian", semua.reset_index(drop=True))
    print(f"semua saham: {len(semua)} baris, {semua['StockCode'].nunique()} kode, {semua['tgl'].nunique()} hari, "
          f"{semua['tgl'].min().date()} s/d {semua['tgl'].max().date()} -> MongoDB lab_data.idx_harian")

    asing = pd.DataFrame({
        "tgl": semua["tgl"].dt.strftime("%Y-%m-%d"),
        "ticker": semua["StockCode"] + ".JK",
        "volume": semua["Volume"],
        "asing_beli": semua["ForeignBuy"],
        "asing_jual": semua["ForeignSell"],
    }).dropna()
    if filter_ticker is not None:
        asing = asing[asing["ticker"].isin(filter_ticker)]
        hilang = sorted(filter_ticker - set(asing["ticker"]))
        print(f"syariah: {asing['ticker'].nunique()}/{len(filter_ticker)} ticker ada di data IDX"
              + (f", tidak ada: {', '.join(hilang[:20])}" if hilang else ""))
    dt.simpan_hasil("idx_asing", asing[KOLOM].reset_index(drop=True))
    print(f"{len(asing)} baris -> MongoDB lab_data.hasil_riset/idx_asing")


def utama():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["uji", "unduh", "impor"])
    p.add_argument("--url", default=URL_DEFAULT)
    p.add_argument("--cookie")
    p.add_argument("--mulai", default="2016-06-01")
    p.add_argument("--selesai")
    p.add_argument("--keluar", default="data/idx_asing.csv")
    p.add_argument("--ticker-file", default="data/syariah_tickers.txt")
    p.add_argument("--jeda", type=float, default=1.0)
    p.add_argument("--pola", default="idx_harian_*.json")
    p.add_argument("--batas-waktu", type=float, default=30.0)
    a = p.parse_args()
    if a.mode == "uji":
        uji(a)
    elif a.mode == "impor":
        impor(a)
    else:
        unduh(a)


if __name__ == "__main__":
    utama()
