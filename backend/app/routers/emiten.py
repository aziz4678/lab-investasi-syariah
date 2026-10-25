from fastapi import APIRouter, HTTPException

from backend.app.services import berita as brt
from backend.app.services import emiten as em
from backend.app.services import indeks as idk
from backend.app.services import orang_dalam as odl
from backend.app.services import pengumuman as pgm
from backend.app.services import profil as pf
from backend.app.services import valuasi as vl

router = APIRouter(prefix="/api")


@router.get("/emiten")
def daftar_emiten():
    return em.daftar()


@router.get("/profil/{kode}")
def profil_emiten_info(kode: str):
    return pf.profil(kode)


@router.get("/orang_dalam/{kode}")
def orang_dalam(kode: str, hari: int = 90):
    return odl.detail(kode, min(max(hari, 7), 400))


@router.get("/berita/{kode}")
def berita(kode: str):
    return brt.daftar(kode)


@router.get("/indeks/{kode}")
def indeks_emiten(kode: str):
    return idk.anggota(kode)


@router.get("/pengumuman")
def pengumuman_daftar(kode: str | None = None, kategori: str | None = "penting", halaman: int = 0, ukuran: int = 25):
    return pgm.daftar(kode, kategori, max(0, halaman), min(max(ukuran, 5), 100))


@router.get("/valuasi/{kode}")
def valuasi_emiten(kode: str):
    return vl.hitung(kode)


@router.get("/emiten/{kode}")
def profil_emiten(kode: str):
    p = em.profil(kode)
    if p is None:
        raise HTTPException(404, f"Data harga {kode.upper()} tidak ada")
    return p
