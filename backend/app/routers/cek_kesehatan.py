from datetime import date, datetime, timedelta

from fastapi import APIRouter

from backend.core import libur_bursa as lb
from backend.db import koneksi as d
from backend.paper.cek_kesehatan import KOLEKSI

router = APIRouter(prefix="/api")

URUT = {"gagal": 0, "peringatan": 1, "info": 2, "ok": 3}


def bersih(x):
    return {"tanggal": x["tanggal"], "nama_cek": x["nama_cek"], "status": x["status"], "pesan": x["pesan"]}


def pemasangan(db):
    c = db[KOLEKSI]
    awal = c.find_one({}, {"dibuat": 1}, sort=[("dibuat", 1)])
    m = db["cek_kesehatan_meta"]
    tersimpan = m.find_one({"_id": "pemasangan"})
    if tersimpan:
        return tersimpan["waktu"]
    waktu = (awal or {}).get("dibuat") or datetime.now()
    m.insert_one({"_id": "pemasangan", "waktu": waktu})
    return waktu


def libur_daftar():
    return sorted(t for per in lb.LIBUR.values() for t in per)


def susun(semua, terakhir_dibuat=None):
    dasar = {"libur": libur_daftar(), "waktu_cek_terakhir": terakhir_dibuat.isoformat(timespec="seconds") if terakhir_dibuat else None}
    if not semua:
        return {**dasar, "tanggal": None, "terbaru": [], "riwayat": [], "harian": [], "tertinggi": "ok"}
    semua = sorted(semua, key=lambda x: x["tanggal"], reverse=True)
    terakhir = semua[0]["tanggal"]
    terbaru = sorted((bersih(x) for x in semua if x["tanggal"] == terakhir), key=lambda x: (URUT.get(x["status"], 9), x["nama_cek"]))
    riwayat = [bersih(x) for x in semua if x["status"] != "ok"]
    per = {}
    for x in semua:
        h = per.setdefault(x["tanggal"], {"tanggal": x["tanggal"], "gagal": 0, "peringatan": 0, "info": 0, "ok": 0})
        h[x["status"]] = h.get(x["status"], 0) + 1
    tertinggi = min((x["status"] for x in terbaru), key=lambda s: URUT.get(s, 9), default="ok")
    return {**dasar, "tanggal": terakhir, "terbaru": terbaru, "riwayat": riwayat, "harian": list(per.values()), "tertinggi": tertinggi}


@router.get("/cek-kesehatan")
def cek_kesehatan():
    db = d.koneksi()
    c = db[KOLEKSI]
    awal = str(date.today() - timedelta(days=30))
    semua = list(c.find({"tanggal": {"$gte": awal}}))
    terakhir = c.find_one({"sumber": "jadwal"}, {"dibuat": 1}, sort=[("dibuat", -1)])
    hasil = susun(semua, (terakhir or {}).get("dibuat"))
    hasil["pemasangan"] = pemasangan(db).isoformat(timespec="seconds")
    return hasil
