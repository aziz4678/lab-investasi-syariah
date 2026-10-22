import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

UMUR_YAHOO = timedelta(days=30)
URL_TERJEMAH = "https://api.mymemory.translated.net/get"
COBA_LAGI = timedelta(days=1)
JABATAN = [
    ("Chief Executive Officer", "Direktur Utama (CEO)"), ("Chief Financial Officer", "Direktur Keuangan (CFO)"), ("Chief Operating Officer", "Direktur Operasional (COO)"),
    ("President Director", "Presiden Direktur"), ("President Commissioner", "Presiden Komisaris"), ("Vice President Director", "Wakil Presiden Direktur"),
    ("Corporate Secretary", "Sekretaris Perusahaan"), ("Independent Director", "Direktur Independen"), ("Commissioner", "Komisaris"),
    ("Director", "Direktur"), ("Head of", "Kepala"), ("Manager", "Manajer"), ("General", "Umum"), ("Finance", "Keuangan"), ("Accounting", "Akuntansi"),
    ("Investor Relations", "Hubungan Investor"), ("Human Capital", "SDM"), ("Human Resources", "SDM"), ("Operations", "Operasional"), ("Business", "Bisnis"),
    ("and ", "dan "),
]


def jabatan_id(t):
    if not t:
        return t
    for a, b in JABATAN:
        t = re.sub(rf"\b{re.escape(a)}", b, t)
    return t


def potong(teks, batas=450):
    kalimat = re.split(r"(?<=[.!?])\s+", teks.strip())
    hasil, kini = [], ""
    for k in kalimat:
        if len(kini) + len(k) + 1 > batas and kini:
            hasil.append(kini)
            kini = k
        else:
            kini = f"{kini} {k}".strip()
    if kini:
        hasil.append(kini)
    return hasil


def terjemah(teks):
    import requests
    hasil = []
    for bagian in potong(teks):
        try:
            r = requests.get(URL_TERJEMAH, params={"q": bagian, "langpair": "en|id"}, timeout=30)
            j = r.json()
        except Exception:
            return None
        t = (j.get("responseData") or {}).get("translatedText")
        if j.get("responseStatus") != 200 or not t or j.get("quotaFinished") or "MYMEMORY WARNING" in t:
            return None
        hasil.append(t)
    return " ".join(hasil)


def terjemah_jabatan(pejabat):
    daftar = [p.get("jabatan") or "" for p in pejabat]
    if not any(daftar):
        return None
    t = terjemah(" | ".join(daftar))
    if not t:
        return None
    hasil = [x.strip() for x in t.split("|")]
    return hasil if len(hasil) == len(daftar) else None


def pastikan_terjemahan(y):
    if not y or not y.get("deskripsi") or (y.get("deskripsi_id") and (y.get("jabatan_id") or not y.get("pejabat"))):
        return y
    gagal = y.get("terjemah_gagal")
    if gagal and datetime.now() - gagal < COBA_LAGI:
        return y
    t = y.get("deskripsi_id") or terjemah(y["deskripsi"])
    jb = y.get("jabatan_id") or terjemah_jabatan(y.get("pejabat") or [])
    perubahan = {"deskripsi_id": t, "jabatan_id": jb} if t else {"terjemah_gagal": datetime.now()}
    d.koneksi().profil_yahoo.update_one({"kode": y["kode"]}, {"$set": perubahan})
    return {**y, **perubahan}


def ambil_yahoo(kode):
    import logging
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    try:
        i = yf.Ticker(f"{kode}.JK").info or {}
    except Exception:
        return None
    if not i.get("longName") and not i.get("shortName"):
        return None
    pertama = i.get("firstTradeDateMilliseconds")
    return {
        "kode": kode, "diambil": datetime.now(), "nama": i.get("longName") or i.get("shortName"),
        "deskripsi": i.get("longBusinessSummary"), "sektor": i.get("sector"), "industri": i.get("industry"),
        "website": i.get("website"), "alamat": ", ".join(x for x in [i.get("address1"), i.get("address2"), i.get("city")] if x),
        "telepon": i.get("phone"), "karyawan": i.get("fullTimeEmployees"),
        "pejabat": [{"nama": o.get("name"), "jabatan": o.get("title")} for o in (i.get("companyOfficers") or [])[:6]],
        "orang_dalam": i.get("heldPercentInsiders"), "institusi": i.get("heldPercentInstitutions"),
        "mulai_diperdagangkan": datetime.fromtimestamp(pertama / 1000) if pertama else None,
    }


def yahoo(kode):
    db = d.koneksi()
    ada = db.profil_yahoo.find_one({"kode": kode}, {"_id": 0})
    if ada and datetime.now() - ada["diambil"] < UMUR_YAHOO:
        return ada
    baru = ambil_yahoo(kode)
    if baru:
        db.profil_yahoo.replace_one({"kode": kode}, baru, upsert=True)
        return baru
    return ada


def kepemilikan_ringkas(kode):
    df = dt.baca("ksei")
    if df is None:
        return None
    df = df[df["kode"] == kode]
    if df.empty:
        return None
    r = df.sort_values("tgl").iloc[-1]
    p = lambda kol: float(sum(r[k] for k in kol) / r["saham"] * 100)
    return {"tgl": r["tgl"].strftime("%Y-%m-%d"), "saham": float(r["saham"]),
            "ritel": round(p(["L_ID"]), 1), "institusi_lokal": round(p(["L_IS", "L_PF", "L_IB", "L_MF"]), 1),
            "korporasi_lokal": round(p(["L_CP"]), 1), "asing": round(p(["F_total"]), 1),
            "di_luar": round(100 - p(["L_total", "F_total"]), 1)}


def bersih(v):
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    return v


def profil(kode):
    kode = kode.upper()
    idx = d.koneksi().profil_idx.find_one({"kode": kode}, {"_id": 0})
    y = yahoo(kode)
    if not (idx and idx.get("kegiatan")):
        y = pastikan_terjemahan(y)
    if not idx and not y:
        return {"ada": False}
    hasil = {
        "ada": True, "kode": kode, "sumber": "IDX" if idx else "Yahoo Finance",
        "nama": (idx or {}).get("nama") or (y or {}).get("nama"),
        "deskripsi": (idx or {}).get("kegiatan") or (y or {}).get("deskripsi_id") or (y or {}).get("deskripsi"),
        "bahasa": "id" if idx and idx.get("kegiatan") else "mesin" if (y or {}).get("deskripsi_id") else "en",
        "deskripsi_en": (y or {}).get("deskripsi"),
        "klasifikasi_idx": [x for x in [(idx or {}).get(k) for k in ["sektor", "subsektor", "industri", "subindustri"]] if x],
        "sektor": (y or {}).get("sektor"), "industri": (y or {}).get("industri"),
        "website": (idx or {}).get("website") or (y or {}).get("website"),
        "alamat": (idx or {}).get("alamat") or (y or {}).get("alamat"),
        "telepon": (idx or {}).get("telepon") or (y or {}).get("telepon"),
        "karyawan": (y or {}).get("karyawan"),
        "tanggal_pencatatan": (idx or {}).get("tanggal_pencatatan") or (y or {}).get("mulai_diperdagangkan"),
        "papan": (idx or {}).get("papan"),
        "pemegang": (idx or {}).get("pemegang") or [],
        "direksi": (idx or {}).get("direksi") or [],
        "komisaris": (idx or {}).get("komisaris") or [],
        "pejabat": [{"nama": p.get("nama"), "jabatan": ((y or {}).get("jabatan_id") or [None] * 99)[i] or jabatan_id(p.get("jabatan"))}
                    for i, p in enumerate((y or {}).get("pejabat") or [])],
        "orang_dalam": (y or {}).get("orang_dalam"), "institusi": (y or {}).get("institusi"),
        "idx_diimpor": (idx or {}).get("diimpor"), "yahoo_diambil": (y or {}).get("diambil"),
        "ksei": kepemilikan_ringkas(kode),
    }
    return {k: bersih(v) for k, v in hasil.items()}
