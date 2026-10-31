import json
import re
import sys
from datetime import datetime
from urllib.parse import unquote

import requests

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest.ojk_nab import kelas, norm

UA = {"User-Agent": "LabInvestasiSyariah/1.0 (riset pribadi)"}
ABAIKAN = {"REKSA", "DANA", "RDS", "RDT", "RDPT", "SYARIAH", "SHARIA", "SYARI", "AH", "FUND", "KELAS", "MI", "AM"}
KATA_SYARIAH = re.compile(r"SYARIAH|SHARIA|SYARI.?AH|SUKUK|AMANAH|ISLAMIC|HAJJ|MUDHARABAH", re.I)
AMBANG = 0.85
PLATFORM = {
    "bibit": {"nama": "Bibit", "situs": "https://bibit.id", "pto": r"Bibit Tumbuh Bersama", "cara": "browser", "logo_alt": r"logo bibit"},
    "ajaib": {"nama": "Ajaib", "situs": "https://ajaib.co.id", "pto": r"Takjub Teknologi", "cara": "sitemap", "logo_alt": r"ajaib logo",
              "sitemap": "https://ajaib.co.id/sitemap-reksa-dana.xml"},
    "makmur": {"nama": "Makmur", "situs": "https://www.makmur.id", "pto": r"Inovasi Finansial Teknologi", "cara": "sitemap", "logo_alt": r"makmur-logo",
               "sitemap": "https://www.makmur.id/sitemap-all-reksadana.xml"},
}


def token(s):
    return {t for t in norm(s).replace("BNI AM ", "BNIAM ").split() if t not in ABAIKAN}


def varian(n):
    v = [n]
    m = re.match(r"(.*)\((.*)\)", n)
    if m:
        v += [m.group(1), m.group(2)]
    return v


def mirip(a, b):
    terbaik = 0
    for x in varian(a):
        for y in varian(b):
            tx, ty = token(x), token(y)
            if tx and ty:
                terbaik = max(terbaik, len(tx & ty) / len(tx | ty))
    return terbaik


def cocokkan(daftar, produk):
    hasil, ragu = {}, []
    for n, url in daftar:
        k = kelas(n)
        calon = []
        for p in produk:
            if (k or None) != (kelas(p["nama"]) or None):
                continue
            if KATA_SYARIAH.search(p["nama"]) and not KATA_SYARIAH.search(n):
                continue
            calon.append((mirip(n, p["nama"]), p["_id"], p["nama"]))
        calon.sort(reverse=True)
        if calon and calon[0][0] >= AMBANG and (len(calon) < 2 or calon[1][0] < calon[0][0]):
            j, fid, pn = calon[0]
            if fid not in hasil or j > hasil[fid]["skor"]:
                hasil[fid] = {"nama": n, "url": url, "skor": j}
        elif calon and calon[0][0] >= 0.6 and KATA_SYARIAH.search(n):
            ragu.append({"nama": n, "url": url, "kandidat": calon[0][2], "skor": round(calon[0][0], 2)})
    return hasil, ragu


def ambil_sitemap(kunci):
    teks = requests.get(PLATFORM[kunci]["sitemap"], headers=UA, timeout=60).text
    lok = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", teks)
    if kunci == "ajaib":
        return [(unquote(u.rsplit("/", 1)[1]).replace("_", " "), u) for u in lok if "/aset/" in u and "/kategori/" not in u]
    return [(re.sub(r"-[0-9a-f]{12}$", "", u.rstrip("/").rsplit("/", 1)[1]).replace("-", " "), u) for u in lok if "/reksadana/" in u]


def salin(cari):
    for awalan in ("bibit_rd_", "ojk_pto_"):
        for f in cari(f"{awalan}*.json")[:1]:
            nama = re.sub(r" \(\d+\)(?=\.json$)", "", f.name)
            if dt.waktu_arsip(nama) >= f.stat().st_mtime:
                continue
            try:
                json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"LEWATI {f.name}: bukan JSON utuh")
                continue
            dt.simpan_arsip(nama, f.read_bytes(), "rd_platform")
            print(f"Disimpan ke arsip: {nama}")


def terbaru(awalan):
    nama = sorted(dt.daftar_arsip(folder="rd_platform", awalan=awalan))
    return (nama[-1], dt.baca_arsip_json(nama[-1])) if nama else (None, None)


def bangun():
    db = d.koneksi()
    produk = list(db.rd_produk.find({"tidak_aktif": {"$ne": True}}, {"nama": 1}))
    sekarang = datetime.now()
    nama_pto, pto = terbaru("ojk_pto_")
    if pto:
        db.rd_pto.delete_many({})
        db.rd_pto.insert_many([{**s, "_id": s["no"]} for s in pto["sistem"]])
        print(f"Daftar Portal Transaksi Online OJK: {len(pto['sistem'])} sistem ({nama_pto})")
    else:
        print("PERINGATAN: daftar Portal Transaksi Online OJK belum pernah diambil")
    sistem = list(db.rd_pto.find({}, {"_id": 0}))
    for kunci, p in PLATFORM.items():
        try:
            if p["cara"] == "sitemap":
                daftar, sumber = ambil_sitemap(kunci), p["sitemap"]
            else:
                nama_file, isi = terbaru("bibit_rd_")
                if not isi:
                    print(f"{p['nama']}: belum ada data dari Chrome Lab, data lama dipertahankan")
                    continue
                daftar, sumber = [(x["nama"], x["url"]) for x in isi["produk"]], nama_file
        except Exception as e:
            print(f"{p['nama']}: GAGAL mengambil ({type(e).__name__}: {e}), data lama dipertahankan")
            continue
        cocok, ragu = cocokkan(daftar, produk)
        domain = p["situs"].split("//")[1].replace("www.", "")
        izin = sorted([s for s in sistem if re.search(p["pto"], s.get("pemilik") or "", re.I)], key=lambda s: domain not in (s.get("url") or ""))
        db.rd_platform.delete_many({"platform": kunci})
        if cocok:
            db.rd_platform.insert_many([{"_id": f"{kunci}|{fid}", "fund": fid, "platform": kunci, "nama": x["nama"], "url": x["url"],
                                         "skor": round(x["skor"], 3), "diambil": sekarang} for fid, x in cocok.items()])
        db.rd_platform_info.update_one({"_id": kunci}, {"$set": {
            "nama": p["nama"], "situs": p["situs"], "cara": p["cara"], "sumber": sumber, "diambil": sekarang, "daftar": len(daftar),
            "cocok": len(cocok), "ragu": ragu, "izin_ojk": [{"nama": s["nama"], "pemilik": s["pemilik"]} for s in izin]}}, upsert=True)
        print(f"{p['nama']}: {len(daftar)} produk di daftar, {len(cocok)} cocok dengan katalog RD syariah, {len(ragu)} ragu (tidak dipakai)"
              f", izin OJK: {'ya (' + izin[0]['nama'] + ')' if izin else 'TIDAK DITEMUKAN di daftar OJK'}")
        for r in ragu[:10]:
            print(f"   ragu: {r['nama']} ~ {r['kandidat']} ({r['skor']})")
    db.rd_platform.create_index("fund")
    total = len(db.rd_platform.distinct("fund"))
    print(f"\nTotal: {total} dari {len(produk)} RD syariah ditemukan di minimal satu platform")


def impor():
    from backend.ingest.impor_browser import cari
    salin(cari)
    bangun()


if __name__ == "__main__":
    impor() if len(sys.argv) < 2 or sys.argv[1] == "impor" else bangun()
