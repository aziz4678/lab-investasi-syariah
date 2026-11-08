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


def bersih(kode):
    return dt.baca(f"harga_bersih_2020/{kode}")


def bersih_banyak(kode=None, kolom=None):
    return dt.baca_banyak("harga_bersih_2020", None if kode is None else sorted(kode), kolom)


def bersih_daftar():
    return dt.daftar("harga_bersih_2020")


def bersih_info(kode=None):
    c = dt.db()["harga_bersih_2020_info"]
    if kode is None:
        return c.find_one({"_id": "_ringkasan"})
    return c.find_one({"_id": kode})


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


KOLEKSI_LUAR = {"my": "harga_my", "us": "harga_us"}


def luar(pasar, kode):
    return dt.baca(f"{KOLEKSI_LUAR[pasar]}/{kode}")


def luar_banyak(pasar, kode=None, kolom=None):
    return dt.baca_banyak(KOLEKSI_LUAR[pasar], None if kode is None else sorted(kode), kolom)


def luar_daftar(pasar):
    return dt.daftar(KOLEKSI_LUAR[pasar])


def indeks_luar(nama):
    x = dt.baca(f"indeks_luar/{nama}")
    if x is None:
        raise DataTidakAda(f"indeks_luar/{nama} belum ada; jalankan backend.ingest.pasar_luar indeks")
    return x


def syariah_luar(pasar):
    if pasar == "my":
        from backend.ingest import syariah_my
        return syariah_my.riwayat()
    d = dt.db()["syariah_us"].find_one(sort=[("tanggal", -1)])
    if d is None:
        raise DataTidakAda("syariah_us belum ada; jalankan backend.ingest.pasar_luar spus")
    return pd.DataFrame({"kode": d["kode"], "mulai": pd.Timestamp("1900-01-01"), "akhir": pd.Timestamp("2100-01-01")})
