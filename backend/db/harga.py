import hashlib

import numpy as np
import pandas as pd

from backend.db import data as dt


class DataTidakAda(RuntimeError):
    pass


def saham(kode):
    return dt.baca(f"harga/{kode}")


def banyak(kode=None, kolom=None):
    return dt.baca_banyak("harga", None if kode is None else sorted(kode), kolom)


def daftar():
    return dt.daftar("harga")


def harian(kode):
    return dt.baca(f"harian/{kode}")


def harian_banyak(kode=None, kolom=None):
    return dt.baca_banyak("harian", None if kode is None else sorted(kode), kolom)


def harian_daftar():
    return dt.daftar("harian")


def mentah(kode):
    bagian = [x for x in (saham(kode), harian(kode)) if x is not None]
    if not bagian:
        return None
    df = pd.concat(bagian)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["open", "high", "low", "close"])


def ihsg():
    s = dt.baca("pasar")["ihsg"].dropna()
    h = dt.baca("harian/_ihsg")
    if h is not None:
        s = pd.concat([s, h["ihsg"].dropna()])
        s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def indeks(nama):
    x = dt.baca(nama)
    if x is None:
        raise DataTidakAda(f"{nama} belum ada di database; jalankan pengunduhnya dulu (backend.ingest.kumpul_data indeks_panjang)")
    return x


def paper(data_yahoo):
    from backend.paper import sumber_idx
    return sumber_idx.susun(data_yahoo)


def status_koreksi():
    c = dt.db()["koreksi_harga"]
    aktif = c.count_documents({"status": "aktif"})
    tahan = c.count_documents({"status": "tahan"})
    terakhir = c.find_one({"status": "aktif"}, sort=[("dibuat", -1)], projection={"dibuat": 1})
    cek = dt.db()["kualitas_data"].find_one(sort=[("waktu", -1)], projection={"_id": 0, "waktu": 1, "status": 1, "jumlah_temuan": 1})
    return {"koreksi_aktif": aktif, "koreksi_tahan": tahan, "koreksi_terakhir": terakhir["dibuat"] if terakhir else None, "cek_kualitas": cek}


def sidik(kode, mulai=None, akhir=None, koleksi="harga", kolom=("open", "high", "low", "close", "adj_close", "volume")):
    data = dt.baca_banyak(koleksi, sorted(kode))
    h = hashlib.sha256()
    baris = 0
    for k in sorted(data):
        df = data[k].sort_index()
        df.index = pd.to_datetime(df.index)
        if mulai is not None:
            df = df[df.index >= pd.Timestamp(mulai)]
        if akhir is not None:
            df = df[df.index <= pd.Timestamp(akhir)]
        x = df[[c for c in kolom if c in df]].astype(float).round(6)
        h.update(k.encode())
        h.update(np.ascontiguousarray(x.index.values.astype("int64")).tobytes())
        h.update(np.ascontiguousarray(np.nan_to_num(x.values, nan=-1.0)).tobytes())
        baris += len(x)
    return {"sidik": h.hexdigest()[:16], "koleksi": koleksi, "kode": len(data), "baris": baris,
            "mulai": None if mulai is None else str(pd.Timestamp(mulai).date()), "akhir": None if akhir is None else str(pd.Timestamp(akhir).date()),
            **status_koreksi()}
