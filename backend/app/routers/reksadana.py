from fastapi import APIRouter, HTTPException, Query

from backend.app.services import rd_banding as rdb
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


@router.get("/rd/racikan")
def rd_racikan(jangka: str = Query("menengah"), profil: str = Query("rendah")):
    return rdn.racikan(jangka, profil)


@router.get("/rd/mulai")
def rd_mulai():
    return rdn.mulai()


@router.get("/rd/platform")
def rd_platform():
    return rdn.platform_info()


@router.get("/rd/bandingkan/pilihan")
def rd_bandingkan_pilihan():
    return rdb.pilihan()


@router.get("/rd/bandingkan")
def rd_bandingkan(id: str = Query(...), periode: str = Query("5y"), rupiah: bool = Query(True)):
    return rdb.bandingkan([k.strip() for k in id.split(",") if k.strip()], periode, rupiah)


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
