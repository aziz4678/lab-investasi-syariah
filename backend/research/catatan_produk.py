from datetime import datetime

import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import keranjang_pertumbuhan as kp

KOLEKSI = "catatan_produk_pertumbuhan"
HARI = 5
SPUS = kp.SPUS_KODE


def produk_terpantau():
    unik = {}
    for app in kp.APLIKASI:
        dok = kp.terbaru(app)
        if dok is None:
            continue
        for kaki, isi in dok["isi"].items():
            for c in isi:
                unik.setdefault(c["id"], {"id": c["id"], "nama": c["nama"], "kaki": "lokal" if kaki == "LK" else "global", "mata_uang": c["mata_uang"]})
    return list(unik.values())


def kurs_harian():
    k = dt.baca("pasar")["usdidr"].dropna().sort_index()
    k.index = pd.DatetimeIndex(k.index).tz_localize(None)
    return k


def baris_rd(db, p):
    hasil = []
    for x in db.rd_nav.find({"fund": p["id"]}, {"_id": 0, "tgl": 1, "nav": 1}).sort("tgl", -1).limit(HARI):
        hasil.append({"tgl": pd.Timestamp(x["tgl"]).strftime("%Y-%m-%d"), "harga": float(x["nav"]), "kurs": None, "harga_idr": float(x["nav"]), "dividen": None})
    return hasil


def baris_spus():
    x = dt.baca(f"etf_luar/{SPUS}")
    if x is None or len(x) == 0:
        return []
    x = x.sort_index().tail(HARI)
    k = kurs_harian()
    hasil = []
    for tgl, r in x.iterrows():
        t = pd.Timestamp(tgl).tz_localize(None) if pd.Timestamp(tgl).tzinfo else pd.Timestamp(tgl)
        kurs = k[k.index <= t]
        kurs = float(kurs.iloc[-1]) if len(kurs) else None
        hasil.append({"tgl": t.strftime("%Y-%m-%d"), "harga": float(r["close"]), "kurs": kurs, "harga_idr": float(r["close"]) * kurs if kurs else None,
                      "dividen": float(r["dividends"]) if pd.notna(r["dividends"]) else 0.0})
    return hasil


def catat(db=None, cetak=True):
    db = d.koneksi() if db is None else db
    baru = 0
    for p in produk_terpantau():
        baris = baris_spus() if p["id"] == SPUS else baris_rd(db, p) if isinstance(p["id"], int) else []
        for b in baris:
            dok = {"_id": f"{b['tgl']}|{p['id']}", "id": p["id"], "nama": p["nama"], "kaki": p["kaki"], "mata_uang": p["mata_uang"], **b, "aturan": kp.ATURAN_VERSI, "dicatat": datetime.now()}
            hasil = db[KOLEKSI].update_one({"_id": dok["_id"]}, {"$setOnInsert": dok}, upsert=True)
            baru += 1 if hasil.upserted_id is not None else 0
    if cetak:
        print(f"catatan produk asli: {baru} baris baru di {KOLEKSI}")
    return baru


if __name__ == "__main__":
    catat()
