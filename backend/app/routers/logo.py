from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.db import data as dt

router = APIRouter(prefix="/api")


@router.get("/logo/ada")
def logo_ada():
    return sorted(x["_id"] for x in dt.db().logo_info.find({"ada": True}, {"_id": 1}))


@router.get("/logo/{jenis}/{kunci}")
def logo(jenis: str, kunci: str):
    if jenis not in ("emiten", "mi", "etf", "negara"):
        raise HTTPException(404, "jenis logo tidak dikenal")
    isi, tipe = dt.baca_arsip_jenis(f"logo/{jenis}/{kunci}")
    if isi is None:
        raise HTTPException(404, "logo tidak ada")
    return Response(content=isi, media_type=tipe, headers={"Cache-Control": "public, max-age=604800"})
