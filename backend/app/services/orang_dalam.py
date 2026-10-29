from datetime import datetime, timedelta

from backend.db import data as dt

ARAH = {"pembelian": 1, "penjualan": -1}


def arah(jenis):
    j = (jenis or "").lower()
    return next((v for k, v in ARAH.items() if j.startswith(k)), 0)


def peran(x):
    if x.get("orang_dalam"):
        j = (x.get("jabatan") or "").lower()
        return "Komisaris" if "komisaris" in j else "Direksi" if "direksi" in j or "direktur" in j else "Direksi/Komisaris"
    if x.get("pengendali"):
        return "Pengendali"
    if (x.get("persen_sebelum") or 0) >= 5 or (x.get("persen_sesudah") or 0) >= 5:
        return "Pemegang ≥5%"
    return "Pemegang saham"


def ringkas_laporan(x):
    beli = jual = nilai_beli = nilai_jual = lain = 0
    harga = []
    for t in x.get("transaksi") or []:
        a = arah(t.get("jenis"))
        n = t.get("jumlah") or 0
        h = t.get("harga")
        if a > 0:
            beli += n
            nilai_beli += n * (h or 0)
        elif a < 0:
            jual += n
            nilai_jual += n * (h or 0)
        else:
            lain += n
        if h:
            harga.append(h)
    jenis = sorted({t.get("jenis") for t in x.get("transaksi") or [] if t.get("jenis")})
    tgl = [t["tanggal"] for t in x.get("transaksi") or [] if t.get("tanggal")]
    return {
        "id": x["_id"], "tgl_lapor": x.get("tgl_lapor").isoformat() if x.get("tgl_lapor") else None,
        "tgl_transaksi": max(tgl).isoformat() if tgl else None, "nama": x.get("nama"), "peran": peran(x), "jabatan": x.get("jabatan"),
        "orang_dalam": bool(x.get("orang_dalam")), "persen_sebelum": x.get("persen_sebelum"), "persen_sesudah": x.get("persen_sesudah"),
        "saham_sebelum": x.get("saham_sebelum"), "saham_sesudah": x.get("saham_sesudah"),
        "beli": beli, "jual": jual, "lain": lain, "nilai_beli": nilai_beli, "nilai_jual": nilai_jual,
        "harga_min": min(harga) if harga else None, "harga_maks": max(harga) if harga else None, "jenis": jenis,
        "tujuan": next((t.get("tujuan") for t in x.get("transaksi") or [] if t.get("tujuan")), None),
        "jumlah_transaksi": len(x.get("transaksi") or []), "url": x.get("url"),
    }


def detail(kode, hari=90):
    db = dt.db()
    kode = kode.upper()
    lap = [ringkas_laporan(x) for x in db.kepemilikan_lapor.find({"kode": kode}).sort([("tgl_lapor", -1), ("_id", -1)]).limit(80)]
    batas = (datetime.now() - timedelta(days=hari)).isoformat()
    baru = [x for x in lap if (x["tgl_lapor"] or "") >= batas]
    total = lambda f, syarat: sum(x[f] for x in baru if syarat(x))
    ringkas = {
        "hari": hari, "laporan": len(baru),
        "dalam_beli": total("nilai_beli", lambda x: x["orang_dalam"]), "dalam_jual": total("nilai_jual", lambda x: x["orang_dalam"]),
        "besar_beli": total("nilai_beli", lambda x: not x["orang_dalam"]), "besar_jual": total("nilai_jual", lambda x: not x["orang_dalam"]),
    }
    tanggal = sorted(db.kepemilikan_besar.distinct("tgl", {"kode": kode}), reverse=True)
    pemegang = []
    if tanggal:
        kini = list(db.kepemilikan_besar.find({"kode": kode, "tgl": tanggal[0]}, {"_id": 0}).sort("persen", -1))
        lalu = {x["investor"]: x for x in db.kepemilikan_besar.find({"kode": kode, "tgl": tanggal[1]}, {"_id": 0})} if len(tanggal) > 1 else {}
        for x in kini:
            sebelum = lalu.get(x["investor"])
            pemegang.append({"investor": x["investor"], "klasifikasi": x.get("klasifikasi"), "lokal_asing": x.get("lokal_asing"),
                             "asal": x.get("asal"), "saham": x.get("saham"), "persen": x.get("persen"),
                             "ubah": None if not lalu else (x["persen"] or 0) - ((sebelum or {}).get("persen") or 0), "baru": bool(lalu) and sebelum is None})
        keluar = [{"investor": k, "persen": v.get("persen")} for k, v in lalu.items() if k not in {x["investor"] for x in kini}]
    else:
        keluar = []
    info = db.kepemilikan_info.find_one({"_id": "ringkas"}) or {}
    return {
        "kode": kode, "laporan": lap, "ringkas": ringkas, "pemegang": pemegang, "keluar": keluar,
        "pemegang_tgl": tanggal[0].isoformat() if tanggal else None, "pemegang_tgl_lalu": tanggal[1].isoformat() if len(tanggal) > 1 else None,
        "mulai_data": "2023-07-03", "diimpor": info.get("diimpor").isoformat(timespec="minutes") if info.get("diimpor") else None,
    }
