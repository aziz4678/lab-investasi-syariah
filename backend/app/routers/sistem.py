from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Query

from backend.app.jobs import jadwal as jd
from backend.app.jobs import pekerjaan as pk
from backend.app.services import sumber_data as sd
from backend.core.config import FRONTEND_DIST as DIST
from backend.db import cadangan as cd
from backend.db import data as dt
from backend.db import koneksi as d

router = APIRouter(prefix="/api")
DB = d.koneksi()


@router.post("/aksi/{jenis}")
def aksi(jenis: str):
    if jenis not in pk.PERINTAH:
        raise HTTPException(404, f"aksi {jenis} tidak dikenal")
    if jenis == "paper_harian" and not DB.paper_status.find_one({"_id": "status"}):
        raise HTTPException(409, "paper trade belum dimulai")
    if jenis == "pulihkan":
        raise HTTPException(422, "pakai /api/aksi_pulihkan")
    if jenis == "otomatis":
        raise HTTPException(422, "pakai /api/otomatis/{sumber}")
    try:
        id_, baru = pk.mulai(jenis)
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@router.post("/aksi_pulihkan")
def aksi_pulihkan(nama: str = Body(...), konfirmasi: str = Body(...)):
    if konfirmasi != "PULIHKAN":
        raise HTTPException(422, "ketik PULIHKAN untuk konfirmasi")
    if nama not in {b["nama"] for b in cd.daftar()}:
        raise HTTPException(404, "backup tidak ditemukan")
    try:
        id_, baru = pk.mulai("pulihkan", [nama])
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@router.get("/cadangan")
def daftar_cadangan():
    return cd.daftar()


@router.get("/jadwal")
def status_jadwal():
    return jd.status()


@router.post("/aksi_jadwal")
def aksi_jadwal(aktif: bool = Body(..., embed=True)):
    try:
        return jd.pasang() if aktif else jd.lepas()
    except RuntimeError as e:
        raise HTTPException(500, f"gagal mengatur Task Scheduler: {e}")


@router.get("/pekerjaan")
def daftar_pekerjaan(batas: int = Query(10, le=100)):
    return pk.terbaru(batas)


@router.get("/pekerjaan/{id_}")
def satu_pekerjaan(id_: str):
    p = pk.ambil(id_)
    if not p:
        raise HTTPException(404, "pekerjaan tidak ada")
    return p


@router.get("/status")
def status_data():
    sekarang = datetime.now()
    hasil = {"sekarang": sekarang, "bursa_buka": sekarang.weekday() < 5 and 9 <= sekarang.hour < 16,
             "data_final": not (sekarang.weekday() < 5 and sekarang.hour < 17)}
    h = dt.baca("harian/_ihsg")
    if h is not None:
        ih = h["ihsg"].dropna()
        hasil["harga_terakhir"] = ih.index[-1].to_pydatetime()
        hasil["ihsg"] = float(ih.iloc[-1])
        hasil["ihsg_20h"] = float((ih.iloc[-1] / ih.iloc[-21] - 1) * 100) if len(ih) > 21 else None
        hasil["ihsg_di_atas_ema200"] = bool(ih.iloc[-1] > ih.ewm(span=200, adjust=False).mean().iloc[-1])
    des = DB.des.find_one(sort=[("mulai", -1)])
    if des:
        hasil["des_periode"] = des["kep"]
        hasil["des_mulai"] = des["mulai"]
        hasil["des_saham"] = DB.des.count_documents({"mulai": des["mulai"]})
        hasil["des_perlu_update"] = (sekarang - des["mulai"]).days > 190 or jd.perlu_cek_des(sekarang.date())
    cek_des = DB.penanda.find_one({"_id": "des_cek"})
    hasil["des_dicek"] = cek_des["isi"] if cek_des else None
    cek = DB.paper_cek.find_one(sort=[("waktu", -1)])
    idx = (cek or {}).get("idx") or {}
    hasil["paper_cek"] = {"waktu": cek["waktu"], "cocok": cek["cocok"], "jumlah_beda": cek["jumlah_beda"], "sampai": cek["sampai"],
                          "idx": {k: idx.get(k) for k in ("cocok", "sampai_idx", "jumlah_beda", "beda_dipakai", "belum_dicek", "pesan")} | {"beda": (idx.get("beda") or [])[:5]} if idx else None} if cek else None
    cad = cd.daftar()
    hasil["backup_terakhir"] = cad[0]["waktu"] if cad else None
    try:
        hasil["data_perlu"] = sd.jumlah_perlu()
    except Exception:
        hasil["data_perlu"] = None
    tahun = sorted(DB.fundamental.distinct("tahun", {"ada_angka": True}))
    hasil["fundamental_tahun"] = tahun
    hasil["fundamental_laporan"] = DB.fundamental.count_documents({"ada_angka": True})
    hasil["fundamental_lengkap"] = all(t in tahun for t in range(2019, 2027))
    hasil["pekerjaan"] = pk.terbaru(5)
    p = DB.paper_status.find_one({"_id": "status"}, {"_id": 0})
    hasil["paper_tgl_terakhir"] = p["tgl_terakhir"] if p else None
    return hasil


@router.get("/sehat")
def sehat():
    return {"mongo": DB.client.server_info()["version"], "versi": DB.backtest_ringkasan.count_documents({})}


@router.get("/build")
def versi_build():
    f = DIST / "index.html"
    return {"build": int(f.stat().st_mtime) if f.exists() else None}
