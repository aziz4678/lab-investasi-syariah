import os
import subprocess
import sys
from datetime import datetime

from pymongo import MongoClient

from backend.core.config import ROOT
from backend.db import koneksi as kdb
from backend.paper import h22_harian as h22

DB_CEK = "swing_cek_h22"
KUNCI = {
    h22.K_TRANSAKSI: ["tgl", "ticker", "aksi"],
    h22.K_EKUITAS: ["tgl"],
    h22.K_REBALANCE: ["eksekusi"],
    h22.K_POSISI: ["ticker"],
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


TOLERANSI_JII = 0.001


def pisah_jii(x):
    jii = {k: [d.get("jii") for d in v] for k, v in x.items()}
    return {k: [{a: b for a, b in d.items() if a != "jii"} for d in v] for k, v in x.items()}, jii


def jii_beda(a, b):
    beda = []
    for k in sorted(set(a) & set(b)):
        for x, y in zip(a[k], b[k]):
            if (x is None) != (y is None) or (x and y and abs(x / y - 1) > TOLERANSI_JII):
                beda.append({"kunci": " · ".join(k), "paper": x, "ulang": y})
    return beda


def bandingkan(prod, cek, sampai, info=None):
    beda = []
    for koleksi in KUNCI:
        a, b = susun(prod, koleksi), susun(cek, koleksi)
        if koleksi != h22.K_POSISI:
            a = {k: v for k, v in a.items() if k[0][:10] <= sampai}
            b = {k: v for k, v in b.items() if k[0][:10] <= sampai}
        if koleksi == h22.K_EKUITAS:
            a, ja = pisah_jii(a)
            b, jb = pisah_jii(b)
            if info is not None:
                info["jii_beda"] = jii_beda(ja, jb)
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                beda.append({"koleksi": koleksi, "kunci": " · ".join(k), "paper": str(a.get(k))[:300], "ulang": str(b.get(k))[:300]})
    sa = rapikan(prod[h22.K_STATUS].find_one({"_id": "status"}) or {})
    sb = rapikan(cek[h22.K_STATUS].find_one({"_id": "status"}) or {})
    for k in ["kas", "tgl_terakhir", "tunda_beli", "tunda_jual"]:
        if sa.get(k) != sb.get(k):
            beda.append({"koleksi": h22.K_STATUS, "kunci": k, "paper": str(sa.get(k))[:300], "ulang": str(sb.get(k))[:300]})
    return beda


def utama():
    prod = kdb.koneksi()
    if prod.name == DB_CEK:
        raise SystemExit("jalankan dari db produksi, bukan db cek")
    status = prod[h22.K_STATUS].find_one({"_id": "status"})
    if not status:
        print("Paper H29 bagian H22 belum dimulai, tidak ada yang dicek.")
        print("SELESAI")
        return
    sampai = status["tgl_terakhir"]
    klien = MongoClient(os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017"))
    klien.drop_database(DB_CEK)
    cek = klien[DB_CEK]
    cek.des.insert_many(list(prod.des.find({}, {"_id": 0})))
    kor = list(prod[h22.K_KOREKSI].find({}))
    if kor:
        cek[h22.K_KOREKSI].insert_many(kor)
    print(f"Menjalankan ulang paper H22 dari nol: titik awal sebelum {status['mulai']} s/d {sampai} (db {DB_CEK}, data harga lokal)")
    env = {**os.environ, "SWING_MONGO_DB": DB_CEK, "PYTHONIOENCODING": "utf-8"}
    hasil = subprocess.run([sys.executable, "-m", "backend.paper.h22_harian", "--tanpa-unduh", "--sampai", sampai, "--mulai", status["mulai"]],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if hasil.returncode != 0:
        print(hasil.stdout[-2000:], hasil.stderr[-2000:])
        klien.drop_database(DB_CEK)
        raise SystemExit("jalankan ulang gagal")
    info = {}
    beda = bandingkan(prod, cek, sampai, info)
    hari = cek[h22.K_EKUITAS].count_documents({})
    prod.paper_h22_cek.insert_one({"waktu": datetime.now(), "sampai": sampai, "hari": hari, "cocok": not beda,
                                   "jumlah_beda": len(beda), "beda": beda[:MAKS_BEDA], "sesi": status.get("sesi"),
                                   "jii_beda": info.get("jii_beda", [])[:MAKS_BEDA], "toleransi_jii": TOLERANSI_JII})
    klien.drop_database(DB_CEK)
    if beda:
        print(f"BEDA: {len(beda)} perbedaan antara paper H22 tersimpan dan hasil jalankan ulang ({hari} hari).")
        for b in beda[:MAKS_BEDA]:
            print(f"  {b['koleksi']} {b['kunci']}\n    paper: {b['paper']}\n    ulang: {b['ulang']}")
        print("Kemungkinan: yfinance merevisi harga lama, data saham hilang, atau bug. Cek saham yang disebut.")
    else:
        print(f"COCOK: {hari} hari paper H22 identik dengan hasil jalankan ulang (transaksi, posisi, ekuitas, rebalance).")
    if info.get("jii_beda"):
        print(f"Info: nilai JII pembanding beda di {len(info['jii_beda'])} hari (lebih dari {TOLERANSI_JII * 100:.1f}%), tidak memengaruhi transaksi/ekuitas.")
    print("SELESAI")


if __name__ == "__main__":
    utama()
