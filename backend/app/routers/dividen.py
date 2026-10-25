from fastapi import APIRouter, Query

from backend.app.services import dividen as dvn

router = APIRouter(prefix="/api")


@router.get("/dividen/daftar")
def dividen_daftar():
    return dvn.daftar()


@router.get("/dividen/paper")
def dividen_paper():
    return dvn.paper()


@router.get("/dividen/pengingat")
def dividen_pengingat(hari: int = Query(7, ge=1, le=60)):
    return dvn.pengingat(hari)


@router.get("/dividen/jadwal")
def dividen_jadwal():
    return dvn.jadwal()


@router.get("/dividen/ringkasan")
def dividen_ringkasan():
    return dvn.ringkasan()


@router.get("/dividen/kalkulator")
def dividen_kalkulator(kode: str = Query(...)):
    return dvn.kalkulator(kode.split(","))


@router.get("/dividen/emiten/{kode}")
def dividen_emiten(kode: str):
    return dvn.emiten(kode)
