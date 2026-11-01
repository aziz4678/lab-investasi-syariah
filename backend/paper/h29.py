import numpy as np
import pandas as pd

from backend.db import koneksi as kdb
from backend.paper import h22_harian as h22
from backend.research import screener as sc

PORSI = 0.5
BATAS_GAGAL_DD = -45.0
EVALUASI = "2027-11-01"
TICK_ESTIMASI = 0.0047
BIAYA_PINDAH = sc.FEE_JUAL / 100 + sc.FEE_BELI / 100 + 2 * TICK_ESTIMASI
KRITERIA = [
    "Momentum Blend (H29): evaluasi 12 bulan pada 2027-11-01. GAGAL kalau drawdown lebih dalam dari -45% atau ada bug eksekusi.",
    "Follow Tren (H11a), jadwal yang dikunci 21 Okt 2026 tetap: keputusan utama Okt 2027, kalau tidak pernah WASPADA/GAGAL di zona h11a_v1 → uang nyata kecil 10-20%.",
    "H11a GAGAL kalau zona h11a_v1 (dikunci 2026-10-22) menyatakan GAGAL (return di bawah persentil 1 sejak hari ke-63, drawdown lebih dalam dari persentil 1, atau rugi beruntun di atas persentil 99). Ditambahkan 1 Nov 2026, bukan pengganti: juga GAGAL kalau drawdown lebih dalam dari -45% atau ada bug eksekusi.",
    "Hasil 12 bulan yang biasa-biasa saja atau rugi kecil tidak otomatis gagal (kecuali H11a jatuh ke zona GAGAL h11a_v1): audit 2026-11-01 menunjukkan tahun tanpa lonjakan besar itu normal.",
    "Saat evaluasi, H11a, H29, bobot sama universe syariah likuid, dan JII dibandingkan pada periode yang sama.",
]


def seri():
    db = kdb.koneksi()
    r22 = list(db[h22.K_EKUITAS].find({}, {"_id": 0}).sort("tgl", 1))
    if not r22:
        return None
    e11 = {x["tgl"]: float(x["ekuitas"]) for x in db.paper_ekuitas.find({}, {"_id": 0, "tgl": 1, "ekuitas": 1})}
    awal = r22[0]["tgl"]
    if awal not in e11:
        return None
    baris = [r for r in r22 if r["tgl"] in e11]
    modal = float(h22.MODAL)
    jii0 = next((r["jii"] for r in baris if r.get("jii")), None)
    jangkar = {"v": modal, "vb": modal, "a": e11[awal], "b": float(baris[0]["ekuitas"])}
    out, jii_terakhir, biaya_total = [], None, 0.0
    for i, r in enumerate(baris):
        t = r["tgl"]
        ra, rb = e11[t] / jangkar["a"] - 1, float(r["ekuitas"]) / jangkar["b"] - 1
        faktor = 1 + PORSI * ra + PORSI * rb
        v, vb = jangkar["v"] * faktor, jangkar["vb"] * faktor
        jii_terakhir = r.get("jii") or jii_terakhir
        akhir_bulan = i + 1 < len(baris) and pd.Timestamp(baris[i + 1]["tgl"]).to_period("M") != pd.Timestamp(t).to_period("M")
        pindah = biaya = 0.0
        if akhir_bulan:
            bagian_a = jangkar["vb"] * PORSI * (1 + ra)
            pindah = abs(bagian_a - vb * PORSI)
            biaya = pindah * BIAYA_PINDAH
            vb -= biaya
            biaya_total += biaya
            jangkar = {"v": v, "vb": vb, "a": e11[t], "b": float(r["ekuitas"])}
        out.append({"tgl": t, "h11a": e11[t] / e11[awal] * modal, "h22": float(r["ekuitas"]), "h29": v, "h29_biaya": vb,
                    "ew": float(r.get("ew") or modal), "jii": jii_terakhir / jii0 * modal if jii0 and jii_terakhir else None,
                    "pindah_rp": pindah, "biaya_rp": biaya, "biaya_total_rp": biaya_total})
    return out


def ringkas(data):
    hasil = {}
    for k in ["h11a", "h29", "h29_biaya", "h22", "ew", "jii"]:
        x = np.array([d[k] for d in data if d[k] is not None], float)
        if not len(x):
            hasil[k] = None
            continue
        puncak = np.maximum.accumulate(np.maximum(x, x[0]))
        dd = x / puncak - 1
        hasil[k] = {"return_pct": float((x[-1] / x[0] - 1) * 100), "dd_pct": float(dd[-1] * 100), "dd_maks_pct": float(dd.min() * 100)}
    hasil["biaya_rebalance_rp"] = float(data[-1]["biaya_total_rp"]) if data else 0.0
    hasil["kali_rebalance"] = int(sum(1 for d in data if d["pindah_rp"] > 0))
    return hasil


def evaluasi(rk, zona_h11a=None):
    out = {}
    for k in ["h11a", "h29"]:
        x = rk.get(k)
        alasan = []
        if x and x["dd_maks_pct"] < BATAS_GAGAL_DD:
            alasan.append(f"drawdown {x['dd_maks_pct']:.1f}% lebih dalam dari {BATAS_GAGAL_DD:.0f}%")
        if k == "h11a" and zona_h11a and zona_h11a.get("zona") == "gagal":
            alasan += [f"zona h11a_v1: {a}" for a in zona_h11a.get("alasan", [])]
        out[k] = {"gagal": bool(alasan), "alasan": alasan, "dd_maks_pct": x["dd_maks_pct"] if x else None,
                  "zona": zona_h11a.get("zona") if k == "h11a" and zona_h11a else None}
    return {"tanggal": EVALUASI, "batas_dd": BATAS_GAGAL_DD, "kriteria": KRITERIA, "status": out,
            "biaya_pindah_pct": round(BIAYA_PINDAH * 100, 2), "tick_estimasi_pct": round(TICK_ESTIMASI * 100, 2)}
