import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urljoin

from curl_cffi import requests

from backend.db import data as dt
from backend.db import koneksi as d

UMUR_HARI = 90
MIN_BYTE = 300
MIN_BYTE_TAJAM = 3000
MI_DOMAIN = {
    "bahana": "bahanatcw.com", "syailendra": "syailendracapital.com", "trimegah": "trimegah-am.com", "batavia": "bpam.co.id",
    "manulife": "manulifeim.co.id", "eastspring": "eastspring.co.id", "sinarmas": "sinarmas-am.co.id", "sucorinvest": "sucorinvestam.com",
    "avrist": "avrist-am.com", "henan putihrai": "hpam.co.id", "bnp paribas": "bnpparibas-am.co.id", "principal": "principal.co.id",
    "panin": "panin-am.co.id", "maybank": "maybank-am.co.id", "majoris": "majoris-am.com", "ashmore": "ashmoregroup.com",
    "ciptadana": "ciptadana.com", "schroder": "schroders.com", "indo premier": "indopremier.com", "allianz": "allianzgi.com",
    "samuel": "samuel.co.id", "insight": "insightinvestments.co.id", "uob": "uobam.co.id", "phillip": "phillip.co.id",
    "pinnacle": "pinnacleinvestment.co.id", "danareksa": "danareksa.co.id",
}
PENERBIT_DOMAIN = {
    "ishares": "ishares.com", "blackrock": "ishares.com", "vanguard": "vanguard.com", "state street": "ssga.com", "sp funds": "spfunds.com",
    "vaneck": "vaneck.com", "wahed": "wahedinvest.com", "invesco": "invesco.com", "hsbc": "hsbc.com", "schwab": "schwab.com",
    "ark": "ark-invest.com", "kraneshares": "kraneshares.com",
}


def kunci_mi(nama):
    return re.sub(r"[^a-z0-9]", "", (nama or "").lower())


def domain(url):
    if not url or url.strip() in ("-", ""):
        return None
    u = re.sub(r"^https?:?/*", "", url.strip().lower()).lstrip("./")
    u = u.split("/")[0].split("?")[0].strip()
    u = re.sub(r"^www\d?\.", "", u)
    return u if "." in u else None


def ambil(url):
    try:
        r = requests.get(url, impersonate="chrome", timeout=20)
        if r.status_code == 200 and len(r.content) >= MIN_BYTE and (r.headers.get("content-type", "").startswith("image") or r.content[:4] in (b"\x89PNG", b"\x00\x00\x01\x00") or r.content[:2] == b"\xff\xd8"):
            return r.content, r.headers.get("content-type") or "image/png"
    except Exception:
        return None
    return None


def dari_html(dom):
    try:
        r = requests.get(f"https://www.{dom}", impersonate="chrome", timeout=20)
    except Exception:
        try:
            r = requests.get(f"https://{dom}", impersonate="chrome", timeout=20)
        except Exception:
            return None
    calon = []
    for tag in re.findall(r"<link[^>]+>", r.text, re.I):
        rel = re.search(r'rel=["\']?([^"\'>]+)', tag, re.I)
        href = re.search(r'href=["\']([^"\']+)', tag, re.I)
        if rel and href and "icon" in rel.group(1).lower():
            ukuran = re.search(r"sizes=[\"']?(\d+)", tag)
            nilai = (2 if "apple" in rel.group(1).lower() else 1, int(ukuran.group(1)) if ukuran else 0)
            calon.append((nilai, urljoin(r.url, href.group(1))))
    for _, u in sorted(calon, reverse=True):
        x = ambil(u)
        if x:
            return x
    return None


def cari_logo(dom):
    x = dari_html(dom)
    if x and len(x[0]) >= MIN_BYTE_TAJAM:
        return x + ("situs",)
    for u in (f"https://www.google.com/s2/favicons?domain={dom}&sz=128", f"https://www.google.com/s2/favicons?domain=www.{dom}&sz=128"):
        y = ambil(u)
        if y:
            return y + ("google",)
    if x:
        return x + ("situs",)
    x = ambil(f"https://icons.duckduckgo.com/ip3/{dom}.ico")
    return x + ("duckduckgo",) if x else None


def target():
    db = d.koneksi()
    hasil = {}
    for p in db.profil_yahoo.find({}, {"kode": 1, "website": 1}):
        if domain(p.get("website")):
            hasil[f"emiten/{p['kode']}"] = domain(p["website"])
    for p in db.profil_idx.find({}, {"kode": 1, "website": 1}):
        if domain(p.get("website")):
            hasil[f"emiten/{p['kode']}"] = domain(p["website"])
    for nama in db.rd_produk.distinct("InvestmentManagerName"):
        n = (nama or "").lower()
        dom = next((v for k, v in MI_DOMAIN.items() if k in n), None)
        if dom:
            hasil[f"mi/{kunci_mi(nama)}"] = dom
    for e in db.etf_luar.find({}, {"kode": 1, "penerbit": 1, "nama": 1}):
        n = f"{e.get('penerbit') or ''} {e.get('nama') or ''}".lower()
        dom = next((v for k, v in PENERBIT_DOMAIN.items() if k in n), None)
        if dom:
            hasil[f"etf/{e['kode']}"] = dom
    hasil["negara/kemenkeu"] = "kemenkeu.go.id"
    return hasil


def jalan(paksa=False):
    db = dt.db()
    semua = target()
    batas = datetime.now() - timedelta(days=UMUR_HARI)
    sudah = {x["_id"]: x for x in db.logo_info.find({})}
    antre = [(k, v) for k, v in semua.items() if (sudah.get(k) or {}).get("sumber") != "idx" and (paksa or k not in sudah or sudah[k].get("domain") != v or not sudah[k].get("ada") or sudah[k].get("dicek", datetime.min) < batas)]
    print(f"{len(semua)} logo dikenal, {len(antre)} perlu diambil (emiten dari situs resmi, manajer investasi & penerbit ETF dari peta domain)")
    cache = {}

    def kerja(item):
        k, dom = item
        if dom not in cache:
            cache[dom] = cari_logo(dom)
        return k, dom, cache[dom]

    ok = gagal = 0
    with ThreadPoolExecutor(4) as ex:
        for i, (k, dom, x) in enumerate(ex.map(kerja, antre)):
            if x:
                isi, jenis, sumber = x
                dt.simpan_arsip(f"logo/{k}", isi, "logo")
                db.logo_info.replace_one({"_id": k}, {"_id": k, "domain": dom, "ada": True, "jenis": jenis, "sumber": sumber, "dicek": datetime.now()}, upsert=True)
                ok += 1
            else:
                db.logo_info.replace_one({"_id": k}, {"_id": k, "domain": dom, "ada": False, "dicek": datetime.now()}, upsert=True)
                gagal += 1
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(antre)} diproses ({ok} ada, {gagal} tanpa logo)")
    total = db.logo_info.count_documents({"ada": True})
    print(f"SELESAI: {ok} logo baru, {gagal} tidak ketemu (pakai inisial). Total logo tersimpan: {total}")


if __name__ == "__main__":
    jalan(paksa="--paksa" in sys.argv)
