from fastapi import APIRouter

from backend.app.services import hipotesis as hps
from backend.app.services import penjelasan as pj
from backend.app.services import riset as rs
from backend.app.services import strategi as st

router = APIRouter(prefix="/api")


@router.get("/strategi")
def daftar_strategi():
    return st.semua()


@router.get("/hipotesis")
def hipotesis():
    return hps.semua()


@router.get("/hipotesis/{kode}/penjelasan")
def penjelasan(kode: str):
    return pj.untuk(kode)


@router.get("/riset")
def riset():
    return {"tahap": rs.TAHAP, "hipotesis": rs.HIPOTESIS, "kriteria": rs.KRITERIA}
