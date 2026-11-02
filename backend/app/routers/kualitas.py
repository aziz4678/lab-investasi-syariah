from fastapi import APIRouter

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import cek_kualitas as ck

router = APIRouter(prefix="/api")

NAMA_KAT = {**ck.KATEGORI, "K1": "K1 salah skala sementara", "K2": "K2 aksi korporasi", "K3": "K3 bar basi / harga beku", "K4": "K4 lompatan / dokumen"}


def cek_terakhir(dengan_temuan=False):
    proj = {"_id": 0} if dengan_temuan else {"_id": 0, "temuan": 0, "tahan": 0}
    return dt.db()[ck.KOLEKSI].find_one({}, proj, sort=[("waktu", -1)])


@router.get("/kualitas")
def kualitas():
    c = dt.db()["koreksi_harga"]
    per = list(c.aggregate([{"$group": {"_id": {"jenis": "$jenis", "kategori": "$kategori", "status": "$status"}, "n": {"$sum": 1}, "kode": {"$addToSet": "$kode"}}}]))
    ringkas = [{"jenis": x["_id"].get("jenis"), "kategori": x["_id"].get("kategori"), "status": x["_id"].get("status"), "jumlah": x["n"], "saham": len(x["kode"])} for x in per]
    label = list(c.find({"jenis": "label"}, {"_id": 0, "kode": 1, "tgl": 1, "status_label": 1, "rasio": 1, "alasan": 1}).sort("tgl", 1))
    tahan = list(c.find({"status": "tahan"}, {"_id": 1, "kode": 1, "jenis": 1, "tgl": 1, "ex_date": 1, "keputusan": 1, "alasan": 1}))
    periksa = list(c.find({"status": "periksa"}, {"_id": 1, "kode": 1, "ex_date": 1, "faktor_idx": 1, "rasio_yahoo_idx": 1, "alasan": 1}))
    log = list(dt.db()["koreksi_harga_log"].find({}, {"_id": 0}).sort("waktu", -1).limit(10))
    db = d.koneksi()
    jadwal = db.jadwal_harian.find_one({}, {"_id": 0, "langkah": 0}, sort=[("mulai", -1)])
    cek = cek_terakhir(True)
    if cek:
        cek["temuan"] = cek.get("temuan", [])[:300]
    return {"cek": cek, "koreksi": ringkas, "label": label, "tahan": tahan, "periksa": periksa, "log_otomatis": log, "jadwal": jadwal,
            "kategori": NAMA_KAT,
            "cakupan": [{"periode": "Jan 2020 - kini", "cara": "Dicek tiap hari ke data resmi IDX (close, open, high/low, volume, aksi korporasi dari harga acuan)", "status": "terverifikasi"},
                        {"periode": "2010 - 2019", "cara": "Hanya deteksi internal (K1 salah skala, K4 lompatan di luar ARA/ARB) + bukti dokumen per kasus", "status": "sebagian"},
                        {"periode": "Saham delisting", "cara": "Tidak ada di Yahoo (survivorship), tidak bisa diperbaiki", "status": "tidak tersedia"}]}


def kode_paper(db):
    pegang = {p["ticker"] for p in db.paper_posisi.find({}, {"ticker": 1})} | {p["ticker"] for p in db.paper_h22_posisi.find({}, {"ticker": 1})}
    sinyal = db.paper_sinyal.find_one({}, sort=[("tgl", -1)]) or {}
    kandidat = set(sinyal.get("kandidat") or []) | set(sinyal.get("terpilih") or [])
    st = db.paper_h22_status.find_one({"_id": "status"}) or {}
    r = st.get("rencana") or {}
    kandidat |= set(r.get("beli") or []) | set(r.get("jual") or [])
    return pegang, kandidat


@router.get("/kualitas/paper")
def kualitas_paper():
    db = d.koneksi()
    cek = cek_terakhir(True) or {}
    pegang, kandidat = kode_paper(db)
    temuan = cek.get("temuan", []) + [dict(x, kategori="TAHAN") for x in cek.get("tahan", [])]
    sentuh = [x for x in temuan if x.get("kode") in pegang | kandidat]
    for x in sentuh:
        x["peran"] = "dipegang" if x["kode"] in pegang else "kandidat"
    sumber = {}
    for bagian in ["h11a", "h22"]:
        x = db.paper_sumber.find_one({"bagian": bagian}, {"_id": 0}, sort=[("tgl", -1)])
        if x:
            sumber[bagian] = x
    jadwal = db.jadwal_harian.find_one({}, {"_id": 0, "langkah": 0, "urutan": 0}, sort=[("mulai", -1)])
    return {"status": cek.get("status"), "waktu": cek.get("waktu"), "jumlah_temuan": cek.get("jumlah_temuan", 0), "jumlah_tahan": cek.get("jumlah_tahan", 0),
            "menonjol": bool(sentuh), "sentuh": sentuh[:50], "sumber": sumber, "jadwal": jadwal}
