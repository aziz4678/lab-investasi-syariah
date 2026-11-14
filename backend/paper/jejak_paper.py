import hashlib
import sys
from datetime import datetime, timedelta

from bson import json_util

from backend.db import koneksi as d

RIWAYAT = "paper_riwayat"
SIDIK = "paper_sidik"
DISNAPSHOT = ("paper_posisi", "paper_h22_posisi", "paper_status", "paper_h22_status")
BUKAN_APPEND_ONLY = {"paper_posisi", "paper_h22_posisi", "paper_status", "paper_h22_status", "paper_h35_status", "paper_h37_status", "paper_h35_posisi", "paper_h37_posisi",
                     "paper_catatan", SIDIK}
HARI_RIWAYAT = 30


def hash_dok(x):
    return hashlib.sha256(json_util.dumps(x, sort_keys=True).encode()).hexdigest()[:16]


def koleksi_append_only(db):
    return sorted(c for c in db.list_collection_names() if c.startswith("paper_") and c not in BUKAN_APPEND_ONLY)


def tanggal_data(db):
    st = db.paper_status.find_one({"_id": "status"}) or {}
    st22 = db.paper_h22_status.find_one({"_id": "status"}) or {}
    t = max(str(st.get("tgl_terakhir") or ""), str(st22.get("tgl_terakhir") or ""))
    return t[:10] or None


def hash_koleksi(db):
    out = {}
    for c in koleksi_append_only(db):
        out[c] = sorted([str(x["_id"]), hash_dok(x)] for x in db[c].find({}))
    return out


def bandingkan(lama, baru):
    beda = []
    for c, daftar in (lama or {}).items():
        sekarang = {i: h for i, h in (baru or {}).get(c, [])}
        for i, h in daftar:
            if i not in sekarang:
                beda.append(f"{c}/{i} hilang")
            elif sekarang[i] != h:
                beda.append(f"{c}/{i} berubah")
    return beda


def simpan_riwayat(db, tgl):
    n = 0
    for c in DISNAPSHOT:
        isi = list(db[c].find({}))
        db[RIWAYAT].update_one({"_id": f"{tgl}|{c}"}, {"$setOnInsert": {"tanggal": tgl, "koleksi": c, "dicatat": datetime.now(), "isi": isi}}, upsert=True)
        n += len(isi)
    return n


def simpan_sidik(db, tgl):
    sebelumnya = db[SIDIK].find_one({"_id": {"$lt": tgl}}, sort=[("_id", -1)])
    sekarang = hash_koleksi(db)
    anomali = bandingkan((sebelumnya or {}).get("koleksi"), sekarang)
    db[SIDIK].update_one({"_id": tgl}, {"$setOnInsert": {"tanggal": tgl, "dicatat": datetime.now(), "koleksi": sekarang, "anomali": anomali,
                                                       "dibandingkan_dengan": (sebelumnya or {}).get("_id")}}, upsert=True)
    return anomali, sum(len(v) for v in sekarang.values())


def status(db, sekarang=None):
    terakhir = db[SIDIK].find_one({}, sort=[("_id", -1)])
    if not terakhir:
        return {"snapshot": None, "anomali": [], "live_beda": [], "dokumen": 0, "koleksi": 0}
    awal = str((sekarang or datetime.now()).date() - timedelta(days=HARI_RIWAYAT))
    anomali = []
    for x in db[SIDIK].find({"_id": {"$gte": awal}, "anomali.0": {"$exists": True}}):
        anomali.extend(f"{x['_id']}: {a}" for a in x["anomali"])
    live_beda = bandingkan(terakhir["koleksi"], hash_koleksi(db))
    return {"snapshot": terakhir["_id"], "anomali": anomali, "live_beda": live_beda, "dokumen": sum(len(v) for v in terakhir["koleksi"].values()), "koleksi": len(terakhir["koleksi"])}


def jalan():
    db = d.koneksi()
    tgl = tanggal_data(db)
    if not tgl:
        print("belum ada data paper, dilewati")
        return
    n = simpan_riwayat(db, tgl)
    anomali, dok = simpan_sidik(db, tgl)
    print(f"{tgl}: riwayat {n} dokumen posisi/status, sidik {dok} dokumen append-only")
    for a in anomali:
        print(f"ANOMALI: {a}")
    print("SELESAI")


if __name__ == "__main__":
    jalan()
