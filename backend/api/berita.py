import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from backend.db import data as dt
from backend.db import koneksi as d

UMUR_CACHE = timedelta(hours=1)
HARI = 30
BUANG = re.compile(r"\b(PT|Tbk|Persero|\(Persero\)|Tbk\.?)\b", re.I)


def nama_emiten(kode):
    db = d.koneksi()
    for sumber, kolom in ((db.profil_idx, "nama"), (db.info_saham, "nama"), (db.profil_yahoo, "nama")):
        x = sumber.find_one({"kode": kode}, {kolom: 1}) or sumber.find_one({"_id": kode}, {kolom: 1})
        if x and x.get(kolom):
            n = re.sub(r"[(),.]", " ", BUANG.sub(" ", x[kolom]))
            n = re.sub(r"\s+", " ", n).strip()
            if len(n) >= 4:
                return n
    return None


def ambil_rss(kode, nama):
    from curl_cffi import requests
    q = f'"{kode}" saham' + (f' OR "{nama}"' if nama else "") + f" when:{HARI}d"
    r = requests.get(f"https://news.google.com/rss/search?q={quote(q)}&hl=id&gl=ID&ceid=ID:id", impersonate="chrome", timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    pola_kode = re.compile(rf"\b{re.escape(kode)}\b")
    pola_nama = re.compile(re.escape(nama), re.I) if nama else None
    hasil, lihat = [], set()
    for it in root.findall(".//item"):
        judul = (it.findtext("title") or "").strip()
        sumber = (it.findtext("source") or "").strip()
        if sumber and judul.endswith(f" - {sumber}"):
            judul = judul[: -len(sumber) - 3].strip()
        if not (pola_kode.search(judul) or (pola_nama and pola_nama.search(judul))):
            continue
        kunci = judul.lower()[:80]
        if kunci in lihat:
            continue
        lihat.add(kunci)
        try:
            tgl = parsedate_to_datetime(it.findtext("pubDate")).astimezone().replace(tzinfo=None)
        except Exception:
            tgl = None
        hasil.append({"judul": judul, "sumber": sumber or None, "tgl": tgl, "url": it.findtext("link")})
    hasil.sort(key=lambda x: x["tgl"] or datetime.min, reverse=True)
    return hasil[:40]


def daftar(kode, paksa=False):
    kode = kode.upper()
    c = dt.db().berita
    simpan = c.find_one({"_id": kode})
    if simpan and not paksa and datetime.now() - simpan["diambil"] < UMUR_CACHE:
        isi, diambil, galat = simpan["item"], simpan["diambil"], None
    else:
        nama = nama_emiten(kode)
        try:
            isi = ambil_rss(kode, nama)
            diambil, galat = datetime.now(), None
            c.replace_one({"_id": kode}, {"_id": kode, "diambil": diambil, "nama": nama, "item": isi}, upsert=True)
        except Exception as e:
            isi = simpan["item"] if simpan else []
            diambil = simpan["diambil"] if simpan else None
            galat = f"Google News tidak bisa diakses ({e.__class__.__name__}); menampilkan data tersimpan"
    return {"kode": kode, "hari": HARI, "diambil": diambil.isoformat(timespec="minutes") if diambil else None, "galat": galat,
            "item": [{**x, "tgl": x["tgl"].isoformat() if x.get("tgl") else None} for x in isi]}
