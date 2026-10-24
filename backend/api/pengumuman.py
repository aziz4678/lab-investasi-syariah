from backend.db import data as dt
from backend.riset.pengumuman_idx import KATEGORI, LABEL

PENTING = ["dividen", "rups", "hmetd", "buyback", "split", "tender", "suspensi", "delisting", "pemantauan", "kepemilikan", "aksi", "fakta", "uma",
           "penjelasan", "paparan", "direksi"]
URUT = [k for k, _, _ in KATEGORI] + ["lain"]


def _baris(x):
    return {"id": x["_id"], "tgl": x["tgl"].isoformat() if x.get("tgl") else None, "kode": x.get("kode"), "judul": x.get("judul"),
            "kategori": x.get("kategori"), "label": LABEL.get(x.get("kategori"), x.get("kategori")),
            "lampiran": [{"url": a["url"], "nama": a.get("nama"), "utama": a.get("utama")} for a in x.get("lampiran") or []]}


def daftar(kode=None, kategori=None, halaman=0, ukuran=25):
    c = dt.db().pengumuman
    dasar = {"kode": kode.upper()} if kode else {}
    hitung = {x["_id"]: x["n"] for x in c.aggregate([{"$match": dasar}, {"$group": {"_id": "$kategori", "n": {"$sum": 1}}}])}
    if kategori == "penting":
        syarat = {**dasar, "kategori": {"$in": PENTING}}
    elif kategori and kategori != "semua":
        syarat = {**dasar, "kategori": kategori}
    else:
        syarat = dasar
    total = c.count_documents(syarat)
    isi = c.find(syarat).sort("tgl", -1).skip(halaman * ukuran).limit(ukuran)
    info = dt.db().pengumuman_info.find_one({"_id": "ringkas"}) or {}
    return {
        "data": [_baris(x) for x in isi], "total": total, "halaman": halaman, "ukuran": ukuran,
        "kategori": [{"id": k, "label": LABEL[k], "n": hitung[k], "penting": k in PENTING} for k in URUT if hitung.get(k)],
        "penting": sum(n for k, n in hitung.items() if k in PENTING), "semua": sum(hitung.values()),
        "dari": info.get("dari").isoformat() if info.get("dari") else None, "sampai": info.get("sampai").isoformat() if info.get("sampai") else None,
        "diimpor": info.get("diimpor").isoformat(timespec="minutes") if info.get("diimpor") else None,
    }
