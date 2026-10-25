from fastapi import APIRouter, HTTPException, Query

from backend.app.services import reksadana as rdn

router = APIRouter(prefix="/api")


@router.get("/rd/daftar")
def rd_daftar():
    return rdn.daftar()


@router.get("/rd/kategori")
def rd_kategori():
    return rdn.ringkas_kategori()


@router.get("/rd/produk/{fid}")
def rd_produk(fid: int):
    x = rdn.detail(fid)
    if x is None:
        raise HTTPException(404, "reksa dana tidak ditemukan")
    return x


@router.get("/rd/sukuk")
def rd_sukuk():
    return rdn.sukuk()


@router.get("/rd/sukuk/{kode}")
def rd_sukuk_riwayat(kode: str):
    x = rdn.sukuk_riwayat(kode.upper())
    if x is None:
        raise HTTPException(404, "Sukuk tidak ditemukan")
    return x


@router.get("/rd/banding")
def rd_banding():
    return rdn.banding()


@router.get("/rd/alokasi")
def rd_alokasi(profil: str = Query("moderat"), modal: float = Query(100_000_000, gt=0, le=1e13)):
    return rdn.alokasi(profil, modal)


@router.get("/rd/lapisan")
def rd_lapisan():
    from backend.app.services import lapisan
    return lapisan.hitung()
