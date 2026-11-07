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
    "Aturan v2 (dikunci 2026-11-07 dari audit sifat aturan; v1 tetap dihitung berdampingan). Keputusan Okt/Nov 2027 = keputusan MANUAL user dengan porsi kecil (peringatan keras H33: maks 10%), BUKAN bukti edge: di 12 bulan strategi tanpa edge tetap lolos 32-88%.",
    "Momentum Blend (H29) GAGAL kalau: drawdown lebih dalam dari -45%, ATAU di hari bursa ke-250 return < -27,0% atau drawdown terdalam < -39,1% (h29_v2), ATAU bug eksekusi tak terjelaskan > 5 hari bursa. Zona h29_v1 = info.",
    "Follow Tren (H11a) GAGAL kalau: pita simultan h11a_v2 (q 0,34%: return mulai hari ke-63, drawdown, rugi beruntun) tertembus, ATAU drawdown lebih dalam dari -45%, ATAU bug eksekusi. WASPADA (pita q 0,70%) dan U2 = info saja.",
    "Horizon bukti dari audit: H11a ±32-51 bulan, H29 ±43 bulan atau lebih. Hasil 12 bulan biasa-biasa saja atau rugi kecil tidak otomatis gagal.",
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
    from backend.paper import aturan_v2
    db = kdb.koneksi()
    out = {}
    for k in ["h11a", "h29"]:
        x = rk.get(k)
        v2 = db[aturan_v2.K_ZONA_V2].find_one({"strategi": k}, sort=[("tgl", -1)])
        alasan = list(v2["gagal"]) if v2 else []
        if x and x["dd_maks_pct"] < BATAS_GAGAL_DD and not any("-45" in a for a in alasan):
            alasan.append(f"drawdown {x['dd_maks_pct']:.1f}% lebih dalam dari {BATAS_GAGAL_DD:.0f}%")
        out[k] = {"gagal": bool(alasan), "alasan": alasan, "dd_maks_pct": x["dd_maks_pct"] if x else None,
                  "status_v2": v2["status"] if v2 else None, "waspada_v2": v2["waspada"] if v2 else [],
                  "zona": zona_h11a.get("zona") if k == "h11a" and zona_h11a else None}
    return {"tanggal": EVALUASI, "batas_dd": BATAS_GAGAL_DD, "kriteria": KRITERIA, "status": out,
            "biaya_pindah_pct": round(BIAYA_PINDAH * 100, 2), "tick_estimasi_pct": round(TICK_ESTIMASI * 100, 2)}
