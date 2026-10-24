import json
import re
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PORT = 9222
ALAMAT = f"http://127.0.0.1:{PORT}"
CHROME = [Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
          Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
          Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"]
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LabInvestasiSyariah" / "chrome_lab"
UNDUHAN = Path.home() / "Downloads"
URL_IDX = "https://www.idx.co.id/id"


def hidup():
    try:
        with urllib.request.urlopen(f"{ALAMAT}/json/version", timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return None


def tab():
    try:
        with urllib.request.urlopen(f"{ALAMAT}/json/list", timeout=2) as r:
            return [t for t in json.loads(r.read()) if t.get("type") == "page"]
    except Exception:
        return []


def status():
    v = hidup()
    if not v:
        return {"jalan": False}
    t = tab()
    idx = [x for x in t if "idx.co.id" in x.get("url", "")]
    siap = [x for x in idx if "Just a moment" not in x.get("title", "") and "Tunggu" not in x.get("title", "")]
    return {"jalan": True, "versi": v.get("Browser"), "tab_idx": len(idx), "idx_siap": bool(siap),
            "judul": idx[0]["title"] if idx else None}


def buka(url=URL_IDX):
    if hidup():
        return "sudah"
    exe = next((p for p in CHROME if p.exists()), None)
    if not exe:
        raise RuntimeError("Google Chrome tidak ditemukan di komputer ini")
    PROFIL.mkdir(parents=True, exist_ok=True)
    bendera = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(exe), f"--remote-debugging-port={PORT}", "--remote-debugging-address=127.0.0.1", f"--user-data-dir={PROFIL}",
                      "--no-first-run", "--no-default-browser-check", url],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=bendera, close_fds=True)
    for _ in range(30):
        if hidup():
            return "dibuka"
        time.sleep(0.5)
    raise RuntimeError("Chrome Lab dibuka tapi tidak merespons di port 9222")


def jalankan(teks, url=URL_IDX, batas_menit=180, ambil_hasil=None):
    from playwright.sync_api import sync_playwright
    if not hidup():
        raise RuntimeError("Chrome Lab belum terbuka. Tekan 'Buka Chrome Lab' di Sumber data dulu.")
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(ALAMAT)
        ctx = b.contexts[0] if b.contexts else b.new_context()
        sesi = b.new_browser_cdp_session()
        sesi.send("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(UNDUHAN), "eventsEnabled": False})
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        halaman = next((pg for pg in ctx.pages if urlparse(pg.url).netloc == host), None)
        if halaman is None:
            halaman = ctx.new_page()
        if halaman.url.rstrip("/") != url.rstrip("/"):
            halaman.goto(url, wait_until="domcontentloaded", timeout=90000)
        halaman.bring_to_front()
        for _ in range(60):
            if "Just a moment" not in halaman.title():
                break
            print("Menunggu pemeriksaan Cloudflare di Chrome Lab... (kalau ada kotak centang, klik sekali)", flush=True)
            time.sleep(5)
        else:
            raise RuntimeError("Halaman masih tertahan pemeriksaan Cloudflare. Selesaikan pemeriksaannya di Chrome Lab lalu ulangi.")
        time.sleep(2)
        tanda = {"selesai": False, "galat": False}

        def catat(m):
            if m.type not in ("log", "warning", "error"):
                return
            print("  " + m.text[:300], flush=True)
            if re.search(r"(^|\] )(SEMUA )?SELESAI", m.text.strip()):
                tanda["selesai"] = True

        halaman.on("console", catat)
        halaman.on("pageerror", lambda e: print("  ERROR halaman: " + str(e)[:300], flush=True))
        halaman.evaluate("() => { if (window.__pantau) window.__pantau.hapus(); }")
        halaman.add_script_tag(content=teks)
        mulai = time.time()
        while True:
            isi = halaman.evaluate("() => { const k = document.body ? document.body.innerText : ''; return k.includes('SELESAI ✔') ? 'selesai' : k.includes('ADA ERROR') ? 'galat' : ''; }")
            if isi == "selesai" or tanda["selesai"]:
                break
            if isi == "galat":
                raise RuntimeError("Script di Chrome Lab melaporkan ERROR, lihat log di atas")
            if time.time() - mulai > batas_menit * 60:
                raise RuntimeError(f"Script belum selesai setelah {batas_menit} menit")
            time.sleep(2)
        hasil = halaman.evaluate(ambil_hasil) if ambil_hasil else None
        time.sleep(3)
        return hasil


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else "status"
    if perintah == "buka":
        print(buka())
    elif perintah == "status":
        print(status())
    elif perintah == "jalan_file":
        teks = Path(sys.argv[2]).read_text(encoding="utf-8")
        jalankan(teks)
        print("Selesai")
