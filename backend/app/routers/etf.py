from fastapi import APIRouter, HTTPException, Query

from backend.app.services import etf as etfn
from backend.app.services import pasar as ps

router = APIRouter(prefix="/api")


@router.get("/etf/daftar")
def etf_daftar():
    return etfn.daftar()


@router.get("/etf/luar")
def etf_luar():
    return etfn.daftar_luar()


@router.get("/etf/pilihan")
def etf_pilihan():
    return etfn.pilihan()


@router.get("/etf/banding")
def etf_banding(kode: str = Query(...), periode: str = Query("5y"), rupiah: bool = Query(False)):
    return etfn.banding([k.strip().upper() for k in kode.split(",") if k.strip()], periode, rupiah)


@router.get("/etf/luar/detail/{kode}")
def etf_luar_detail(kode: str):
    x = etfn.detail_luar(kode.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x


@router.get("/etf/luar/intraday/{kode}")
def etf_luar_intraday(kode: str):
    try:
        return ps.intraday_luar(kode.upper().strip())
    except Exception:
        return None


@router.get("/etf/luar/grafik/{kode}")
def etf_luar_grafik(kode: str, banding: str = Query("SPY")):
    x = etfn.grafik_luar(kode.upper(), banding.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x


@router.get("/etf/grafik/{kode}")
def etf_grafik(kode: str):
    x = etfn.grafik(kode.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x
