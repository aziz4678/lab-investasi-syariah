from datetime import datetime

from backend.db import data as dt

ALIAS = {"IDX HIGH DIVIDEND 20": "IDXHIDIV20", "IDX GROWTH30": "IDXG30", "IDX VALUE30": "IDXV30", "IDX QUALITY30": "IDXQ30",
         "IDX SHARIA GROWTH": "IDXSHAGROW", "IDX SMC COMPOSITE": "IDXSMC-COM", "IDX SMC LIQUID": "IDXSMC-LIQ",
         "IDX LQ45 LOW CARBON LEADERS": "IDXLQ45LCL", "IIDX LQ45 LOW CARBON LEADERS": "IDXLQ45LCL", "IDXMESBUMN17": "IDXMESBUMN"}
URUT = ["JII", "JII70", "ISSI", "IDXSHAGROW", "IDXMESBUMN", "LQ45", "IDX30", "IDX80", "KOMPAS100", "IDXHIDIV20", "IDXBUMN20",
        "IDXV30", "IDXG30", "IDXQ30", "IDXSMC-LIQ", "IDXSMC-COM"]
SYARIAH = {"JII", "JII70", "ISSI", "IDXSHAGROW", "IDXMESBUMN"}
KET = {"JII": "30 saham syariah terbesar & paling likuid", "JII70": "70 saham syariah terbesar & paling likuid",
       "ISSI": "semua saham syariah di BEI", "IDXSHAGROW": "saham syariah dengan pertumbuhan tinggi",
       "IDXMESBUMN": "saham syariah BUMN", "LQ45": "45 saham paling likuid", "IDX30": "30 saham paling likuid", "IDX80": "80 saham likuid",
       "KOMPAS100": "100 saham pilihan Kompas", "IDXHIDIV20": "20 saham dividen tinggi", "IDXBUMN20": "20 saham BUMN",
       "IDXV30": "30 saham value", "IDXG30": "30 saham growth", "IDXQ30": "30 saham quality", "IDXSMC-LIQ": "saham kapitalisasi kecil-menengah likuid",
       "IDXSMC-COM": "saham kapitalisasi kecil-menengah"}


def nama(n):
    n = (n or "").upper().strip()
    return ALIAS.get(n, n)


def anggota(kode):
    db = dt.db()
    kode = kode.upper()
    kini = datetime.now()
    periode = {}
    for x in db.indeks_anggota.aggregate([{"$match": {"mulai": {"$lte": kini}}}, {"$group": {"_id": {"i": "$indeks", "m": "$mulai"}}}]):
        periode.setdefault(nama(x["_id"]["i"]), set()).add(x["_id"]["m"])
    milik = {}
    for x in db.indeks_anggota.find({"kode": kode, "mulai": {"$lte": kini}}, {"indeks": 1, "mulai": 1, "baru": 1, "bobot": 1}):
        milik.setdefault(nama(x["indeks"]), {})[x["mulai"]] = x
    hasil = []
    for i in sorted(set(milik) & set(URUT), key=URUT.index):
        urut = sorted(periode.get(i, []))
        if not urut:
            continue
        sekarang = urut[-1] in milik[i]
        sejak = None
        if sekarang:
            k = len(urut) - 1
            while k >= 0 and urut[k] in milik[i]:
                k -= 1
            sejak = urut[k + 1]
        terakhir = max(milik[i])
        hasil.append({"indeks": i, "syariah": i in SYARIAH, "ket": KET.get(i), "anggota": sekarang,
                      "sejak": sejak.strftime("%Y-%m-%d") if sejak else None, "sejak_awal_data": bool(sejak and sejak == urut[0]),
                      "terakhir_masuk": terakhir.strftime("%Y-%m-%d"), "bobot": milik[i][terakhir].get("bobot") if sekarang else None,
                      "periode": len(milik[i]), "dari_periode": len(urut)})
    keluar = [{"indeks": nama(x["indeks"]), "mulai": x["mulai"].strftime("%Y-%m-%d")}
              for x in db.indeks_keluar.find({"kode": kode}).sort("mulai", -1).limit(10) if nama(x["indeks"]) in URUT]
    awal = db.indeks_anggota.find_one(sort=[("mulai", 1)])
    return {"kode": kode, "indeks": hasil, "keluar": keluar, "data_mulai": awal["mulai"].strftime("%Y-%m-%d") if awal else None}
