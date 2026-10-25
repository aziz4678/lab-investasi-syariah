from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.app.jobs import pekerjaan as pk
from backend.app.services import sumber_data as sd

router = APIRouter(prefix="/api")


@router.get("/chrome_lab")
def chrome_lab_status():
    from backend.ingest import chrome_lab
    return chrome_lab.status()


@router.post("/chrome_lab/buka")
def chrome_lab_buka():
    from backend.ingest import chrome_lab
    try:
        return {"hasil": chrome_lab.buka(), **chrome_lab.status()}
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/otomatis/{sumber}")
def otomatis(sumber: str):
    s = next((x for x in sd.SUMBER if x["id"] == sumber and x.get("cara") == "browser"), None)
    if not s:
        raise HTTPException(404, "sumber tidak dikenal atau bukan lewat browser")
    try:
        id_, baru = pk.mulai("otomatis", [sumber])
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@router.get("/sumber_data")
def daftar_sumber_data():
    return sd.status()


@router.get("/skrip/{nama}", response_class=PlainTextResponse)
def skrip_browser(nama: str):
    isi = sd.skrip(nama)
    if isi is None:
        raise HTTPException(404, "skrip tidak dikenal")
    return isi
