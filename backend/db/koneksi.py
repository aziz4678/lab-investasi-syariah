import os
from datetime import datetime

import numpy as np
import pandas as pd
from pymongo import ASCENDING, MongoClient

URI = os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017")
NAMA_DB = os.environ.get("SWING_MONGO_DB", "swing")
_DB = None


def koneksi():
    global _DB
    if _DB is None:
        _DB = MongoClient(URI, serverSelectionTimeoutMS=5000)[NAMA_DB]
    return _DB


def siapkan_indeks(db=None):
    db = koneksi() if db is None else db
    db.backtest_trade.create_index([("versi", ASCENDING), ("tgl_sinyal", ASCENDING)])
    db.backtest_trade.create_index([("versi", ASCENDING), ("ticker", ASCENDING)])
    db.backtest_ekuitas.create_index([("versi", ASCENDING), ("bulan", ASCENDING)], unique=True)
    db.backtest_ringkasan.create_index("versi", unique=True)
    db.des.create_index([("kode", ASCENDING), ("mulai", ASCENDING)], unique=True)
    db.lapkeu.create_index([("kode", ASCENDING), ("tahun", ASCENDING), ("periode", ASCENDING)], unique=True)
    db.fundamental.create_index([("kode", ASCENDING), ("tahun", ASCENDING), ("periode", ASCENDING)], unique=True)
    db.fundamental.create_index([("kode", ASCENDING), ("tgl_publikasi", ASCENDING)])
    db.info_saham.create_index("ticker", unique=True)
    db.rekomendasi_log.create_index([("tgl", ASCENDING), ("konfig", ASCENDING), ("ticker", ASCENDING)], unique=True)
    db.paper_posisi.create_index("ticker", unique=True)
    db.paper_transaksi.create_index([("tgl", ASCENDING)])
    db.paper_ekuitas.create_index("tgl", unique=True)
    db.paper_sinyal.create_index("tgl", unique=True)


def ganti_versi(db, koleksi, versi, dokumen):
    db[koleksi].delete_many({"versi": versi})
    if dokumen:
        db[koleksi].insert_many(dokumen)


def ke_bson(v):
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return None if pd.isna(v) else pd.Timestamp(v).to_pydatetime()
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and np.isnan(v):
        return None
    if v is pd.NaT:
        return None
    return v


def ke_dokumen(df):
    return [{k: ke_bson(v) for k, v in r.items()} for r in df.to_dict("records")]


def simpan_df(koleksi, df, filter_hapus=None):
    db = koneksi()
    db[koleksi].delete_many(filter_hapus or {})
    dok = ke_dokumen(df)
    if dok:
        db[koleksi].insert_many(dok)
    return len(dok)


def baca_df(koleksi, query=None, kolom=None):
    proyeksi = {"_id": 0}
    if kolom:
        proyeksi.update({k: 1 for k in kolom})
    return pd.DataFrame(list(koneksi()[koleksi].find(query or {}, proyeksi)))


class Penanda:
    def __init__(self, nama):
        self.nama = nama

    def exists(self):
        return koneksi().penanda.count_documents({"_id": self.nama}) > 0

    def read_text(self):
        dok = koneksi().penanda.find_one({"_id": self.nama})
        return dok["isi"] if dok else ""

    def write_text(self, isi):
        koneksi().penanda.replace_one({"_id": self.nama}, {"_id": self.nama, "isi": isi, "diubah": datetime.now()}, upsert=True)

    def __str__(self):
        return f"penanda:{self.nama}"


def penanda(nama):
    return Penanda(nama)
