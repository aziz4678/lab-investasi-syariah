from fastapi import APIRouter, HTTPException, Query

from backend.app.services import rd_banding as rdb
from backend.app.services import reksadana as rdn

router = APIRouter(prefix="/api")


@router.get("/rd/daftar")
def rd_daftar():
    return rdn.daftar()


@router.get("/rd/cek_platform")
def rd_cek_platform():
    from backend.db import koneksi as d
    return rdn.bersih(d.koneksi().rd_cek_platform.find_one({"_id": "hasil"}) or {})


@router.get("/rd/kategori")
def rd_kategori():
    return rdn.ringkas_kategori()


@router.get("/rd/produk/{fid}")
def rd_produk(fid: int):
    x = rdn.detail(fid)
    if x is None:
        raise HTTPException(404, "reksa dana tidak ditemukan")
    return x


@router.get("/rd/penarikan")
def rd_penarikan():
    from backend.app.services import penarikan
    return penarikan.hasil()


@router.get("/konservatif")
def konservatif():
    from backend.app.services import penarikan
    return penarikan.konservatif()


@router.get("/konservatif/simulasi")
def konservatif_simulasi(modal: float = 1_000_000_000, opsi: str = "sbn50", tarik: float | None = None, tahun: int = 10, aplikasi: str = "semua"):
    from backend.app.services import penarikan
    return penarikan.simulasi(modal, opsi, tarik, tahun, aplikasi)


@router.get("/konservatif/rencana")
def konservatif_rencana(modal: float = 1_000_000_000, pengeluaran: float = 10_000_000, darurat: int = 6, opsi: str = "sbn50", aplikasi: str = "semua"):
    from backend.app.services import penarikan
    return penarikan.rencana(modal, pengeluaran, darurat, opsi, aplikasi)


@router.get("/pertumbuhan")
def pertumbuhan():
    from backend.app.services import pertumbuhan as pt
    return pt.dasar()


@router.get("/pertumbuhan/rencana")
def pertumbuhan_rencana(setoran: float = 1_000_000, modal_awal: float = 0, aplikasi: str = "semua"):
    from backend.app.services import pertumbuhan as pt
    return pt.rencana(setoran, modal_awal, aplikasi)


@router.get("/pertumbuhan/uji_maju")
def pertumbuhan_uji_maju():
    from backend.app.services import pertumbuhan as pt
    return pt.uji_maju()


@router.get("/pertumbuhan/emas")
def pertumbuhan_emas():
    from backend.app.services import pertumbuhan as pt
    return pt.emas()


@router.get("/rd/pengingat_sbn")
def rd_pengingat_sbn():
    from backend.app.services import penarikan
    return penarikan.pengingat_sbn()


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
