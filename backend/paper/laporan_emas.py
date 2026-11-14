from datetime import datetime

import pandas as pd

from backend.db import koneksi as d

KOLEKSI = "laporan_emas_h37"


def nav_sejajar(df, hari, t):
    t = pd.Timestamp(t)
    sesudah = [h for h in hari if h > t]
    if sesudah and sesudah[0] in df.index and pd.notna(df.at[sesudah[0], "nav"]):
        return float(df.at[sesudah[0], "nav"]), False
    s = df.loc[:t, "nav"].dropna()
    return (float(s.iloc[-1]), True) if len(s) else (None, True)


def hitung(transaksi, ekuitas, etf_df, hari):
    hari = sorted(pd.Timestamp(h) for h in hari)
    emas = sorted((t for t in transaksi if t.get("kaki") == "emas"), key=lambda t: (t["tgl"], t["_id"]))
    pembelian = []
    for t in emas:
        kode = t["kunci"][4:]
        df = etf_df.get(kode)
        nav, perkiraan = (None, True) if df is None else nav_sejajar(df, hari, t["tgl"])
        prem = t["harga"] / nav - 1 if nav else None
        if t["sisi"] == "beli":
            pembelian.append({"tgl": t["tgl"], "kode": kode, "harga": t["harga"], "unit": t["unit"], "nilai": t["nilai"], "nav_sejajar_keputusan": t.get("nav_sejajar"),
                              "premium_keputusan": t.get("premium_keputusan"), "nav_sejajar_eksekusi": nav, "nav_eksekusi_perkiraan": perkiraan,
                              "premium_dibayar": prem, "lewat_rem": bool(t.get("lewat_rem")), "hari_order": t.get("hari_order"), "lewati_sebelumnya": t.get("lewati_sebelumnya")})
    seri = []
    unit_nav = 0.0
    kode_nav = None
    for e in sorted(ekuitas, key=lambda x: x["tgl"]):
        for t in emas:
            if t["tgl"] == e["tgl"]:
                kode = t["kunci"][4:]
                df = etf_df.get(kode)
                nav, _ = (None, True) if df is None else nav_sejajar(df, hari, t["tgl"])
                if nav:
                    biaya = t["nilai"] + t["fee"] if t["sisi"] == "beli" else -(t["nilai"] - t["fee"])
                    unit_nav += biaya / nav
                    kode_nav = kode
        nilai_nav = None
        if kode_nav and unit_nav:
            nav, perkiraan = nav_sejajar(etf_df[kode_nav], hari, e["tgl"])
            nilai_nav = unit_nav * nav if nav else None
        pasar = e.get("emas") or 0.0
        pembanding = e["nilai"] - pasar + nilai_nav if nilai_nav is not None else e["nilai"]
        seri.append({"tgl": e["tgl"], "ekuitas": e["nilai"], "ekuitas_kaki_emas_nav": pembanding, "selisih": e["nilai"] - pembanding, "emas_pasar": pasar, "emas_nav": nilai_nav})
    nilai_total = sum(p["nilai"] for p in pembelian)
    berpremium = [p for p in pembelian if p["premium_dibayar"] is not None]
    nilai_b = sum(p["nilai"] for p in berpremium)
    ringkas = {"pembelian": len(pembelian), "lewat_rem": sum(1 for p in pembelian if p["lewat_rem"]), "nilai_dibeli": nilai_total,
               "premium_dibayar_tertimbang": sum(p["premium_dibayar"] * p["nilai"] for p in berpremium) / nilai_b if nilai_b else None,
               "selisih_terakhir": seri[-1]["selisih"] if seri else None}
    return {"pembelian": pembelian, "seri": seri, "ringkasan": ringkas}


def simpan(db, data):
    transaksi = list(db.paper_h37_transaksi.find({}))
    ekuitas = list(db.paper_h37_ekuitas.find({}))
    hasil = hitung(transaksi, ekuitas, data.etf_df, data.hari)
    hasil.update({"dibuat": datetime.now(), "catatan": "Laporan eksekusi emas H37, bukan aturan. Premium dibayar = harga beli / NAV berlabel hari bursa berikutnya (sejajar dengan harga hari itu); NAV hari terakhir belum terbit sehingga memakai NAV terbaru (perkiraan). ekuitas_kaki_emas_nav = ekuitas H37 bila kaki emas dibeli dan dinilai pada NAV, supaya hasil strategi terpisah dari biaya eksekusi."})
    db[KOLEKSI].replace_one({"_id": "terbaru"}, {"_id": "terbaru", **hasil}, upsert=True)
    return hasil["ringkasan"]
