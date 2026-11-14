from datetime import date, timedelta

from fastapi import APIRouter

from backend.db import koneksi as d
from backend.paper.cek_kesehatan import KOLEKSI

router = APIRouter(prefix="/api")

URUT = {"gagal": 0, "peringatan": 1, "info": 2, "ok": 3}


def bersih(x):
    return {"tanggal": x["tanggal"], "nama_cek": x["nama_cek"], "status": x["status"], "pesan": x["pesan"]}


@router.get("/cek-kesehatan")
def cek_kesehatan():
    c = d.koneksi()[KOLEKSI]
    awal = str(date.today() - timedelta(days=30))
    semua = list(c.find({"tanggal": {"$gte": awal}}).sort([("tanggal", -1)]))
    if not semua:
        return {"tanggal": None, "terbaru": [], "riwayat": [], "harian": [], "tertinggi": "ok"}
    terakhir = semua[0]["tanggal"]
    terbaru = sorted((bersih(x) for x in semua if x["tanggal"] == terakhir), key=lambda x: (URUT.get(x["status"], 9), x["nama_cek"]))
    riwayat = [bersih(x) for x in semua if x["status"] != "ok"]
    per = {}
    for x in semua:
        h = per.setdefault(x["tanggal"], {"tanggal": x["tanggal"], "gagal": 0, "peringatan": 0, "info": 0, "ok": 0})
        h[x["status"]] = h.get(x["status"], 0) + 1
    tertinggi = min((x["status"] for x in terbaru), key=lambda s: URUT.get(s, 9), default="ok")
    return {"tanggal": terakhir, "terbaru": terbaru, "riwayat": riwayat, "harian": list(per.values()), "tertinggi": tertinggi}
