import io
import json
import math
import os
from datetime import datetime, timezone
from functools import lru_cache

import gridfs
import numpy as np
import pandas as pd
from pymongo import MongoClient

URI = os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017")
NAMA_DB = os.environ.get("SWING_DATA_DB", "lab_data")
BARIS_PER_BAGIAN = 10000
_DB = None


def db():
    global _DB
    if _DB is None:
        _DB = MongoClient(URI, serverSelectionTimeoutMS=5000)[NAMA_DB]
    return _DB


def pecah(nama):
    koleksi, _, kunci = nama.partition("/")
    return koleksi, kunci or koleksi


def _ke_list(s):
    if pd.api.types.is_datetime64_any_dtype(s.dtype):
        return [None if pd.isna(v) else v.to_pydatetime() for v in s]
    if pd.api.types.is_bool_dtype(s.dtype):
        return [bool(v) for v in s]
    if pd.api.types.is_integer_dtype(s.dtype):
        return [int(v) for v in s]
    if pd.api.types.is_float_dtype(s.dtype):
        return s.astype(float).tolist()
    return [v.item() if isinstance(v, np.generic) else v for v in s]


def _dari_list(nilai, jenis):
    if jenis.startswith("datetime64"):
        return pd.Series(pd.to_datetime(nilai)).astype(jenis)
    if jenis == "object":
        return pd.Series(nilai, dtype=object)
    if jenis in ("string", "str"):
        return pd.Series(nilai, dtype=object).astype(jenis)
    return pd.Series(nilai).astype(jenis)


def tulis(nama, df):
    koleksi, kunci = pecah(nama)
    c = db()[koleksi]
    indeks = None if isinstance(df.index, pd.RangeIndex) and df.index.start == 0 and df.index.step == 1 else df.index
    kolom = [str(k) for k in df.columns]
    jenis = {str(k): str(df[k].dtype) for k in df.columns}
    n = len(df)
    bagian = max(1, math.ceil(n / BARIS_PER_BAGIAN))
    sekarang = datetime.now()
    dok = []
    for i in range(bagian):
        sl = df.iloc[i * BARIS_PER_BAGIAN:(i + 1) * BARIS_PER_BAGIAN]
        d = {"_id": kunci if bagian == 1 else f"{kunci}#{i:04d}", "nama": kunci, "bagian": i, "jumlah_bagian": bagian, "baris": len(sl),
             "kolom": kolom, "jenis": jenis, "diperbarui": sekarang}
        if indeks is not None:
            d["indeks_nama"] = df.index.name
            d["indeks_jenis"] = str(df.index.dtype)
            d["indeks"] = _ke_list(pd.Series(sl.index))
        for k in df.columns:
            d[str(k)] = _ke_list(sl[k])
        dok.append(d)
    c.delete_many({"nama": kunci})
    c.insert_many(dok)
    c.create_index([("nama", 1), ("bagian", 1)])
    _cache.cache_clear()


def ada(nama):
    koleksi, kunci = pecah(nama)
    return db()[koleksi].count_documents({"nama": kunci}, limit=1) > 0


def versi(nama):
    koleksi, kunci = pecah(nama)
    d = db()[koleksi].find_one({"nama": kunci}, {"diperbarui": 1}, sort=[("diperbarui", -1)])
    return d["diperbarui"].timestamp() if d else 0.0


def daftar(koleksi):
    return sorted(db()[koleksi].distinct("nama"))


def _bangun(dok, kolom_pilih=None):
    if not dok:
        return None
    dok = sorted(dok, key=lambda x: x["bagian"])
    kolom = [k for k in dok[0]["kolom"] if kolom_pilih is None or k in kolom_pilih]
    jenis = dok[0]["jenis"]
    bagian = []
    for d in dok:
        data = {k: _dari_list(d[k], jenis[k]) for k in kolom}
        f = pd.DataFrame(data, columns=kolom)
        if "indeks" in d:
            ix = _dari_list(d["indeks"], d["indeks_jenis"])
            f.index = pd.Index(ix, name=d.get("indeks_nama"))
        bagian.append(f)
    hasil = pd.concat(bagian) if len(bagian) > 1 else bagian[0]
    if "indeks" not in dok[0]:
        hasil = hasil.reset_index(drop=True)
    return hasil


@lru_cache(maxsize=64)
def _cache(koleksi, kunci, kolom, ver):
    proyeksi = None if kolom is None else {k: 1 for k in ("bagian", "kolom", "jenis", "indeks", "indeks_nama", "indeks_jenis", *kolom)}
    return _bangun(list(db()[koleksi].find({"nama": kunci}, proyeksi)), kolom)


def baca(nama, kolom=None, salin=True):
    koleksi, kunci = pecah(nama)
    kolom = tuple(kolom) if kolom else None
    hasil = _cache(koleksi, kunci, kolom, versi(nama))
    if hasil is None:
        return None
    return hasil.copy() if salin else hasil


def baca_banyak(koleksi, kunci=None, kolom=None):
    q = {} if kunci is None else {"nama": {"$in": list(kunci)}}
    proyeksi = None if kolom is None else {k: 1 for k in ("nama", "bagian", "kolom", "jenis", "indeks", "indeks_nama", "indeks_jenis", *kolom)}
    kelompok = {}
    for d in db()[koleksi].find(q, proyeksi):
        kelompok.setdefault(d["nama"], []).append(d)
    return {k: _bangun(v, kolom) for k, v in kelompok.items()}


def hapus(nama):
    koleksi, kunci = pecah(nama)
    db()[koleksi].delete_many({"nama": kunci})
    _cache.cache_clear()


def simpan_hasil(nama, isi):
    if isinstance(isi, pd.DataFrame):
        tulis(f"hasil_riset/{nama}", isi)
        return
    teks = isi if isinstance(isi, str) else None
    db()["hasil_riset"].replace_one({"_id": nama}, {"_id": nama, "nama": nama, "bagian": 0, "jenis_isi": "teks" if teks is not None else "json",
                                                    "isi": teks if teks is not None else isi, "diperbarui": datetime.now()}, upsert=True)


def baca_hasil(nama):
    d = db()["hasil_riset"].find_one({"nama": nama, "bagian": 0})
    if d is None:
        return None
    if d.get("jenis_isi") in ("teks", "json"):
        return d["isi"]
    return baca(f"hasil_riset/{nama}")


def versi_hasil(nama):
    d = db()["hasil_riset"].find_one({"nama": nama}, {"diperbarui": 1})
    return d["diperbarui"].timestamp() if d else 0.0


def simpan_daftar(nama, isi):
    db()["daftar"].replace_one({"_id": nama}, {"_id": nama, "isi": list(isi), "diperbarui": datetime.now()}, upsert=True)


def baca_daftar(nama):
    d = db()["daftar"].find_one({"_id": nama})
    return list(d["isi"]) if d else []


def _fs():
    return gridfs.GridFS(db(), collection="arsip")


def simpan_arsip(nama, isi, folder=""):
    fs = _fs()
    if isinstance(isi, str):
        isi = isi.encode("utf-8")
    for lama in fs.find({"filename": nama}):
        fs.delete(lama._id)
    fs.put(isi, filename=nama, folder=folder, diunggah=datetime.now())


def baca_arsip_jenis(nama):
    f = _fs().find_one({"filename": nama}, sort=[("uploadDate", -1)])
    if not f:
        return None, None
    isi = f.read()
    if isi[:4] == bytes([0x89, 0x50, 0x4E, 0x47]):
        jenis = "image/png"
    elif isi[:2] == bytes([0xFF, 0xD8]):
        jenis = "image/jpeg"
    elif isi[:4] == bytes([0, 0, 1, 0]):
        jenis = "image/x-icon"
    elif b"<svg" in isi[:300]:
        jenis = "image/svg+xml"
    elif isi[:3] == b"GIF":
        jenis = "image/gif"
    elif isi[8:12] == b"WEBP":
        jenis = "image/webp"
    else:
        jenis = "application/octet-stream"
    return isi, jenis


def baca_arsip(nama):
    f = _fs().find_one({"filename": nama}, sort=[("uploadDate", -1)])
    return f.read() if f else None


def baca_arsip_json(nama):
    b = baca_arsip(nama)
    return json.loads(b.decode("utf-8")) if b is not None else None


def ada_arsip(nama):
    return _fs().exists({"filename": nama})


def daftar_arsip(folder=None, awalan=None):
    q = {}
    if folder is not None:
        q["folder"] = folder
    if awalan:
        q["filename"] = {"$regex": "^" + awalan}
    return sorted(f.filename for f in _fs().find(q))


def waktu_arsip(nama):
    f = _fs().find_one({"filename": nama}, sort=[("uploadDate", -1)])
    if not f:
        return 0.0
    u = f.upload_date
    return (u if u.tzinfo else u.replace(tzinfo=timezone.utc)).timestamp()


def ringkas():
    hasil = {}
    for k in db().list_collection_names():
        s = db().command("collstats", k)
        hasil[k] = {"dokumen": s.get("count"), "mb": round(s.get("storageSize", 0) / 1e6, 1)}
    return hasil


def bytes_io(b):
    return io.BytesIO(b)


class HasilTeks:
    def __init__(self, nama):
        self.nama = nama

    def exists(self):
        return isinstance(baca_hasil(self.nama), str)

    def read_text(self, encoding=None):
        isi = baca_hasil(self.nama)
        if not isinstance(isi, str):
            raise FileNotFoundError(self.nama)
        return isi

    def write_text(self, isi, encoding=None):
        simpan_hasil(self.nama, isi)

    def __str__(self):
        return f"hasil_riset/{self.nama}"


def hasil_teks(nama):
    return HasilTeks(nama)
