from fastapi import APIRouter

from backend.app.services import makro as mkr
from backend.app.services import pasar as ps

router = APIRouter(prefix="/api")


@router.get("/makro")
def makro():
    return mkr.ringkas()


@router.get("/pasar")
def pasar_ringkasan():
    return ps.ringkasan()


@router.get("/pasar/intraday")
def pasar_intraday(kode: str | None = None):
    try:
        return ps.intraday(kode.upper().strip() if kode else None)
    except Exception:
        return None
