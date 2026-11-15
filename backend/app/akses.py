import hashlib
import hmac
import os
import time
from html import escape
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from backend.core.config import ROOT

FILE_SANDI = ROOT / "akses.txt"
NAMA_COOKIE = "lab_akses"
MASA_COOKIE = 30 * 24 * 3600
BATAS_GAGAL = 5
JEDA_GAGAL = 15 * 60
HEADER_PROXY = ("x-forwarded-for", "x-forwarded-host", "forwarded", "cf-connecting-ip", "tailscale-user-login")

BLOK_TAMU = ("/api/pekerjaan", "/api/cek-kesehatan", "/api/portofolio-saya", "/api/kualitas", "/api/chrome_lab", "/api/skrip", "/api/cadangan", "/api/jadwal", "/api/otomatis")

IZIN_TAMU = ("/api/kualitas/paper",)

_gagal: list[float] = []


def pemilik(request: Request) -> bool:
    lewat_proxy = any(h in request.headers for h in HEADER_PROXY)
    return not lewat_proxy and request.client is not None and request.client.host in ("127.0.0.1", "::1")


async def _teruskan(request: Request, lanjut):
    if not pemilik(request):
        jalur = request.url.path
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return JSONResponse({"detail": "Hanya untuk pemilik (lokal)"}, status_code=403)
        if jalur not in IZIN_TAMU and any(jalur == b or jalur.startswith(b + "/") for b in BLOK_TAMU):
            return JSONResponse({"detail": "Hanya untuk pemilik (lokal)"}, status_code=403)
    return await lanjut(request)


def sandi() -> str:
    dari_env = os.environ.get("LAB_SANDI", "").strip()
    if dari_env:
        return dari_env
    try:
        return FILE_SANDI.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _tanda(kunci: str, kedaluwarsa: int) -> str:
    return hmac.new(kunci.encode(), f"lab|{kedaluwarsa}".encode(), hashlib.sha256).hexdigest()


def buat_token(kunci: str) -> str:
    kedaluwarsa = int(time.time()) + MASA_COOKIE
    return f"{kedaluwarsa}.{_tanda(kunci, kedaluwarsa)}"


def token_sah(token: str | None, kunci: str) -> bool:
    if not token or "." not in token:
        return False
    awal, tanda = token.split(".", 1)
    try:
        kedaluwarsa = int(awal)
    except ValueError:
        return False
    return kedaluwarsa > time.time() and hmac.compare_digest(tanda, _tanda(kunci, kedaluwarsa))


def _terblokir() -> bool:
    sekarang = time.time()
    _gagal[:] = [t for t in _gagal if sekarang - t < JEDA_GAGAL]
    return len(_gagal) >= BATAS_GAGAL


def _halaman(pesan: str = "", status: int = 200) -> HTMLResponse:
    info = f'<p class="p">{escape(pesan)}</p>' if pesan else ""
    isi = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Masuk</title>
<style>:root{{color-scheme:light dark}}body{{font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:Canvas;color:CanvasText}}
form{{display:grid;gap:12px;width:min(320px,86vw);padding:24px;border:1px solid #8884;border-radius:16px}}
input,button{{font:inherit;padding:10px 14px;border-radius:999px;border:1px solid #8886}}button{{background:#00a35f;color:#fff;border:0;cursor:pointer}}.p{{margin:0;color:#d33;font-size:14px}}</style></head>
<body><form method="post" action="/login"><strong>Lab Investasi Syariah</strong>{info}<input type="password" name="sandi" placeholder="Sandi" autofocus required><button>Masuk</button></form></body></html>"""
    return HTMLResponse(isi, status_code=status, headers={"Cache-Control": "no-store"})


async def penjaga(request: Request, lanjut):
    kunci = sandi()
    lewat_proxy = any(h in request.headers for h in HEADER_PROXY)
    lokal_murni = not lewat_proxy and request.client is not None and request.client.host in ("127.0.0.1", "::1")
    if lokal_murni:
        return await lanjut(request)
    if not kunci:
        if lewat_proxy:
            return Response("Akses dari luar ditolak: sandi belum dipasang (akses.txt).", status_code=503)
        return await _teruskan(request, lanjut)

    jalur = request.url.path
    if jalur == "/login":
        if request.method == "POST":
            if _terblokir():
                return _halaman("Terlalu banyak percobaan. Coba lagi nanti.", 429)
            data = parse_qs((await request.body()).decode("utf-8", "ignore"))
            masuk = (data.get("sandi") or [""])[0]
            if hmac.compare_digest(masuk.encode(), kunci.encode()):
                jawab = RedirectResponse("/", status_code=303)
                aman = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
                jawab.set_cookie(NAMA_COOKIE, buat_token(kunci), max_age=MASA_COOKIE, httponly=True, samesite="lax", secure=aman)
                return jawab
            _gagal.append(time.time())
            return _halaman("Sandi salah.", 401)
        return _halaman()

    if token_sah(request.cookies.get(NAMA_COOKIE), kunci):
        return await _teruskan(request, lanjut)
    if jalur.startswith("/api"):
        return JSONResponse({"detail": "Belum masuk"}, status_code=401)
    return RedirectResponse("/login", status_code=303)
