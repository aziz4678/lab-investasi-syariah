from fastapi import APIRouter

from backend.app.services import hipotesis as hps
from backend.app.services import riset as rs
from backend.app.services import strategi as st

router = APIRouter(prefix="/api")


@router.get("/strategi")
def daftar_strategi():
    return st.semua()


@router.get("/hipotesis")
def hipotesis():
    return hps.semua()


@router.get("/riset")
def riset():
    return {"tahap": rs.TAHAP, "hipotesis": rs.HIPOTESIS, "kriteria": rs.KRITERIA}
