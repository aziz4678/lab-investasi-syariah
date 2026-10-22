import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

from backend.db import koneksi as kdb

ROOT = Path(__file__).resolve().parents[2]
DB_CEK = "swing_cek"
KUNCI = {
    "paper_transaksi": ["tgl", "ticker", "aksi"],
    "paper_ekuitas": ["tgl"],
    "paper_sinyal": ["tgl"],
    "paper_posisi": ["ticker"],
}
MAKS_BEDA = 20


def rapikan(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, list):
        return [rapikan(x) for x in v]
    if isinstance(v, dict):
        return {k: rapikan(x) for k, x in v.items()}
    return v


def susun(db, koleksi):
    hasil = {}
    for dok in map(rapikan, db[koleksi].find({}, {"_id": 0})):
        k = tuple(str(dok.get(x)) for x in KUNCI[koleksi])
        hasil.setdefault(k, []).append(dok)
    return hasil


def bandingkan(prod, cek, sampai):
    beda = []
    for koleksi in KUNCI:
        a, b = susun(prod, koleksi), susun(cek, koleksi)
        if koleksi != "paper_posisi":
            a = {k: v for k, v in a.items() if k[0] <= str(sampai)}
            b = {k: v for k, v in b.items() if k[0] <= str(sampai)}
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                beda.append({"koleksi": koleksi, "kunci": " · ".join(k), "paper": str(a.get(k))[:300], "ulang": str(b.get(k))[:300]})
    sa = prod.paper_status.find_one({"_id": "status"}) or {}
    sb = cek.paper_status.find_one({"_id": "status"}) or {}
    for k in ["kas", "tgl_terakhir"]:
        if sa.get(k) != sb.get(k):
            beda.append({"koleksi": "paper_status", "kunci": k, "paper": str(sa.get(k)), "ulang": str(sb.get(k))})
    return beda


def utama():
    prod = kdb.koneksi()
    if prod.name == DB_CEK:
        raise SystemExit("jalankan dari db produksi, bukan db cek")
    status = prod.paper_status.find_one({"_id": "status"})
    pertama = prod.paper_ekuitas.find_one(sort=[("tgl", 1)])
    if not status or not pertama:
        print("Paper trade belum dimulai, tidak ada yang dicek.")
        return
    mulai = pertama["tgl"].date()
    sampai = status["tgl_terakhir"]
    klien = MongoClient(os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017"))
    klien.drop_database(DB_CEK)
    cek = klien[DB_CEK]
    cek.des.insert_many(list(prod.des.find({}, {"_id": 0})))
    print(f"Menjalankan ulang paper trade dari nol: {mulai} s/d {sampai}, modal Rp{status['modal_awal']:,.0f} (db {DB_CEK}, data harga lokal)")
    env = {**os.environ, "SWING_MONGO_DB": DB_CEK, "PYTHONIOENCODING": "utf-8"}
    hasil = subprocess.run([sys.executable, "-m", "backend.paper.tren_harian", "--tanpa-unduh", "--mulai", str(mulai),
                            "--modal", str(status["modal_awal"]), "--sampai", sampai],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if hasil.returncode != 0:
        print(hasil.stdout[-2000:], hasil.stderr[-2000:])
        raise SystemExit("jalankan ulang gagal")
    beda = bandingkan(prod, cek, sampai)
    hari = cek.paper_ekuitas.count_documents({})
    dok = {"waktu": datetime.now(), "mulai": str(mulai), "sampai": sampai, "hari": hari, "cocok": not beda,
           "jumlah_beda": len(beda), "beda": beda[:MAKS_BEDA], "sesi": status.get("sesi")}
    prod.paper_cek.insert_one(dok)
    klien.drop_database(DB_CEK)
    if beda:
        print(f"BEDA: {len(beda)} perbedaan antara paper tersimpan dan hasil jalankan ulang ({hari} hari).")
        for b in beda[:MAKS_BEDA]:
            print(f"  {b['koleksi']} {b['kunci']}\n    paper: {b['paper']}\n    ulang: {b['ulang']}")
        print("Kemungkinan: yfinance merevisi harga lama, data saham hilang, atau bug. Cek saham yang disebut.")
    else:
        print(f"COCOK: {hari} hari paper trade identik dengan hasil jalankan ulang (transaksi, posisi, ekuitas, sinyal).")


if __name__ == "__main__":
    utama()
