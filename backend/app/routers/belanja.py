from fastapi import APIRouter

from backend.app.services import belanja as bl

router = APIRouter(prefix="/api/belanja")


@router.get("/pertumbuhan")
def pertumbuhan(setoran: float = 1_000_000, modal_awal: float = 0, apps: str = "bibit,ajaib,makmur,stockbit", gaya: str = "saham"):
    return bl.pertumbuhan(apps, setoran, modal_awal, gaya)


@router.get("/konservatif")
def konservatif(modal: float = 1_000_000_000, pengeluaran: float = 10_000_000, darurat: int = 6, opsi: str = "sbn50", apps: str = "bibit,ajaib,makmur,stockbit"):
    return bl.konservatif(apps, modal, pengeluaran, darurat, opsi)
