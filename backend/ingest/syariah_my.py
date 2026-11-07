import argparse
import io
import json
import re
from datetime import datetime

import pandas as pd
import pdfplumber
import requests

from backend.db import data as dt

HALAMAN = "https://www.sc.com.my/development/icm/icm-publications/list-of-shariah-compliant-securities"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LabInvestasiSyariah"}
FOLDER = "syariah_my"
BULAN = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
         "september": 9, "october": 10, "november": 11, "december": 12}
AWAL_DAFTAR = re.compile(r"(MAIN\s+MARKET|MAIN\s+BOARD|PAPAN\s+UTAMA|PASARAN\s+UTAMA)", re.I)
BUTIR = re.compile(r"(?<![\d.])(\d{1,4})\.\s+(\d{4})(?:\s|$)")
TOTAL = re.compile(r"(\d{3,4})\s+(?:Shariah[- ]compliant\s+securities|sekuriti\s+patuh\s+Syariah)", re.I)


def daftar_dokumen():
    t = requests.get(HALAMAN, headers=UA, timeout=60).text
    hasil = []
    for m in re.finditer(r'\{[^{}]*"Page Address":"[^"]*"[^{}]*\}', t):
        d = json.loads(m.group(0))
        teks = d.get("Page Description", "")
        tg = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", teks)
        if not tg or tg.group(2).lower() not in BULAN:
            continue
        tanggal = datetime(int(tg.group(3)), BULAN[tg.group(2).lower()], int(tg.group(1)))
        alamat = d["Page Address"]
        if not alamat.startswith("http"):
            alamat = "https://www.sc.com.my/" + alamat.lstrip("/")
        hasil.append({"tanggal": tanggal, "url": alamat, "judul": teks})
    return sorted(hasil, key=lambda x: x["tanggal"])


def ambil_pdf(url):
    r = requests.get(url, headers=UA, timeout=120)
    return r.content if r.content[:4] == b"%PDF" else None


def urai(isi):
    kode, total, mulai = [], None, False
    with pdfplumber.open(io.BytesIO(isi)) as p:
        for hal in p.pages:
            teks = hal.extract_text() or ""
            if total is None:
                m = TOTAL.search(teks.replace("\n", " "))
                if m:
                    total = int(m.group(1))
            if not mulai and AWAL_DAFTAR.search(teks) and len(BUTIR.findall(teks)) >= 10:
                mulai = True
            if mulai:
                kode += [k for _, k in BUTIR.findall(teks)]
    return kode, total


def perbarui(paksa=False):
    ada = {d["_id"]: d for d in dt.db()["syariah_my"].find()}
    for dok in daftar_dokumen():
        kunci = dok["tanggal"].strftime("%Y-%m-%d")
        if kunci in ada and not paksa and ada[kunci].get("jumlah"):
            continue
        nama = f"{FOLDER}/{kunci}.pdf"
        isi = dt.baca_arsip(nama)
        if isi is None:
            isi = ambil_pdf(dok["url"])
            if isi is None:
                print(f"{kunci}: PDF tidak bisa diambil", flush=True)
                continue
            dt.simpan_arsip(nama, isi, folder=FOLDER)
        kode, total = urai(isi)
        unik = sorted(set(kode))
        dt.db()["syariah_my"].replace_one({"_id": kunci}, {
            "_id": kunci, "tanggal": dok["tanggal"], "url": dok["url"], "judul": dok["judul"], "kode": unik,
            "jumlah": len(unik), "butir": len(kode), "total_tertulis": total, "diperbarui": datetime.now()}, upsert=True)
        print(f"{kunci}: {len(unik)} kode (butir {len(kode)}, tertulis {total})", flush=True)


def riwayat():
    d = pd.DataFrame(list(dt.db()["syariah_my"].find({"jumlah": {"$gt": 0}}, {"_id": 0, "tanggal": 1, "kode": 1})))
    d = d.sort_values("tanggal").reset_index(drop=True)
    d["akhir"] = d["tanggal"].shift(-1) - pd.Timedelta(days=1)
    baris = [{"kode": k, "mulai": r.tanggal, "akhir": r.akhir if pd.notna(r.akhir) else pd.Timestamp("2100-01-01")}
             for r in d.itertuples() for k in r.kode]
    return pd.DataFrame(baris)


def utama():
    a = argparse.ArgumentParser()
    a.add_argument("perintah", choices=["perbarui", "ringkas"])
    a.add_argument("--paksa", action="store_true")
    x = a.parse_args()
    if x.perintah == "perbarui":
        perbarui(x.paksa)
    for d in dt.db()["syariah_my"].find({}, {"_id": 1, "jumlah": 1, "butir": 1, "total_tertulis": 1}).sort("_id"):
        print(d["_id"], d.get("jumlah"), d.get("butir"), d.get("total_tertulis"))


if __name__ == "__main__":
    utama()
