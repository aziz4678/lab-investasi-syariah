from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.jobs import pekerjaan as pk
from backend.app.routers import backtest, dividen, emiten, etf, logo, paper, pasar, reksadana, riset, sistem, sumber_data
from backend.core.config import FRONTEND_DIST as DIST

app = FastAPI(title="Lab Syariah API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])
pk.bersihkan_yatim()

for modul in [backtest, paper, sistem, sumber_data, logo, riset, emiten, dividen, etf, reksadana, pasar]:
    app.include_router(modul.router)

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{jalur:path}")
    def spa(jalur: str):
        f = (DIST / jalur).resolve()
        aman = f.is_relative_to(DIST.resolve())
        if jalur and aman and f.is_file() and f.name != "index.html":
            return FileResponse(f)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
