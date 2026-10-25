import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.app.services import valuasi as vl
from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research.uji_h17 import kalender, muat_harga, nilai_pada

YIELD_MIN = 6.0
SIKLIKAL = {"Energy", "Basic Materials"}


def sektor_semua(kode):
    db = d.koneksi()
    info = {x["ticker"][:-3]: x.get("sector") for x in db.info_saham.find({}, {"ticker": 1, "sector": 1})}
    for x in db.profil_yahoo.find({}, {"kode": 1, "sektor": 1}):
        info.setdefault(x["kode"], x.get("sektor"))
    return info


def fitur_fundamental(k, m, t, dps12):
    lap = vl.laporan(k)
    sh = vl.saham(k)
    if lap.empty or sh.empty:
        return {}
    r = vl.pada(lap, t)
    if r is None:
        return {}
    n = vl.saham_pada(sh, t, vl.split_dari(m))
    fx = vl.nilai_kurs(r, t)
    if not np.isfinite(n) or not np.isfinite(r["laba_ttm"]):
        return {}
    eps = r["laba_ttm"] * fx / n
    g = vl.tumbuh(r["laba_ttm"], r["laba_ttm_1"])
    bank = np.isnan(r.get("pendapatan", np.nan)) and np.isnan(r.get("aset_lancar", np.nan))
    der = r["liabilitas"] / r["ekuitas_total"] if r["ekuitas_total"] and r["ekuitas_total"] > 0 else np.nan
    cfo = r["arus_kas_operasi_ttm"]
    return {"payout_lebih_100": bool(eps <= 0 or dps12 > eps), "laba_turun_30": bool(g is not None and g < -30),
            "arus_kas_kurang": bool(np.isfinite(cfo) and cfo * fx < dps12 * n), "der_tinggi": bool(not bank and np.isfinite(der) and der > 2)}


def utama():
    des = des_ojk.baca()
    daftar217 = sc.daftar_syariah()
    kode = sorted(set(des["kode"]) | set(daftar217))
    data = muat_harga(kode)
    kal = kalender(data)
    sektor = sektor_semua(kode)
    kejadian = []
    for th in range(2012, 2025):
        t = kal[kal <= pd.Timestamp(f"{th}-12-31")].max()
        t2 = kal[kal <= pd.Timestamp(f"{th + 1}-12-31")].max()
        if t2 < pd.Timestamp(f"{th + 1}-12-20"):
            continue
        univ = sorted(daftar217) if th < 2019 else sorted(des_ojk.syariah_pada(des, t))
        for k in univ:
            m = data.get(k)
            if m is None:
                continue
            c = m["close"]
            p = nilai_pada(c, t)
            if not np.isfinite(p) or p < sc.HARGA_MIN or not (nilai_pada(m["nilai20"], t) >= sc.MIN_VALUE):
                continue
            dv = m["dividends"]
            dps12 = float(dv[(dv.index > t - pd.Timedelta(days=365)) & (dv.index <= t)].sum())
            if dps12 / p * 100 < YIELD_MIN:
                continue
            nanti = float(dv[(dv.index > t) & (dv.index <= t2)].sum())
            p2 = nilai_pada(c, t2)
            total = ((p2 + nanti) / p - 1) * 100
            tahunan = [dv[dv.index.year == y].sum() for y in (th - 3, th - 2, th - 1)]
            med = float(np.median(tahunan))
            p_lalu = nilai_pada(c, t - pd.Timedelta(days=365))
            ma200 = float(c[c.index <= t].tail(200).mean())
            dok = {
                "kode": k, "tahun": th, "yield": dps12 / p * 100, "total_12b": total, "dividen_berikut_pct": nanti / dps12 * 100,
                "trap": bool(total < 0 or nanti < 0.7 * dps12), "rugi": bool(total < 0), "dipotong": bool(nanti < 0.7 * dps12),
                "spesial": bool(med > 0 and dps12 > 2 * med) or bool(med == 0),
                "harga_turun_20": bool(np.isfinite(p_lalu) and p / p_lalu - 1 < -0.2), "di_bawah_ma200": bool(p < ma200),
                "siklikal": sektor.get(k) in SIKLIKAL, "sektor": sektor.get(k) or "?",
            }
            if th >= 2020:
                dok.update(fitur_fundamental(k, m, t, dps12))
            kejadian.append(dok)
    df = pd.DataFrame(kejadian)
    dt.simpan_hasil(f"analisis_dividend_trap", df.reset_index(drop=True))
    print(f"\n===== Dividend trap: {len(df)} kejadian yield >= {YIELD_MIN:g}% ({df['kode'].nunique()} saham), akhir tahun 2012-2024, hasil 12 bulan berikutnya =====")
    print(f"Trap (total return < 0 ATAU dividen berikutnya < 70%): {df['trap'].mean() * 100:.0f}% | rugi: {df['rugi'].mean() * 100:.0f}% | "
          f"dividen dipotong: {df['dipotong'].mean() * 100:.0f}% | total return 12 bln median {df['total_12b'].median():+.1f}%")
    ringkas = {"dibuat": datetime.now().isoformat(timespec="minutes"), "n": len(df), "trap": df["trap"].mean() * 100,
               "rugi": df["rugi"].mean() * 100, "dipotong": df["dipotong"].mean() * 100, "total_median": df["total_12b"].median(), "fitur": {}}
    df["yield_grup"] = pd.cut(df["yield"], [6, 8, 12, 1000], labels=["6-8%", "8-12%", ">12%"], right=False)
    print("\nPeluang trap per ciri saat dibeli (ya vs tidak):")
    for kol, nama in [("spesial", "dividen spesial (12 bln > 2x biasanya)"), ("harga_turun_20", "harga turun > 20% setahun terakhir"),
                      ("di_bawah_ma200", "harga di bawah rata-rata 200 hari"), ("siklikal", "sektor komoditas (energi/tambang)"),
                      ("payout_lebih_100", "payout > 100% / rugi (2020+)"), ("laba_turun_30", "laba turun > 30% (2020+)"),
                      ("arus_kas_kurang", "arus kas operasi < dividen (2020+)"), ("der_tinggi", "DER > 2 (2020+)")]:
        if kol not in df:
            continue
        x = df[df[kol].notna()]
        ya, tidak = x[x[kol] == True], x[x[kol] == False]
        if len(ya) < 3:
            continue
        print(f"  {nama:<42} ya {ya['trap'].mean() * 100:4.0f}% (n={len(ya):3d}, median {ya['total_12b'].median():+5.1f}%) | "
              f"tidak {tidak['trap'].mean() * 100:4.0f}% (n={len(tidak):3d}, median {tidak['total_12b'].median():+5.1f}%)")
        ringkas["fitur"][kol] = {"nama": nama, "ya": ya["trap"].mean() * 100, "n_ya": len(ya), "tidak": tidak["trap"].mean() * 100, "n_tidak": len(tidak),
                                 "median_ya": ya["total_12b"].median(), "median_tidak": tidak["total_12b"].median()}
    print("\nPer tingkat yield:")
    ringkas["yield"] = {}
    for g, x in df.groupby("yield_grup", observed=True):
        print(f"  yield {g:<6} trap {x['trap'].mean() * 100:4.0f}% (n={len(x)}), median total 12 bln {x['total_12b'].median():+.1f}%")
        ringkas["yield"][str(g)] = {"trap": x["trap"].mean() * 100, "n": len(x), "median": x["total_12b"].median()}
    print("\nPer tahun:")
    print(df.groupby("tahun").agg(n=("trap", "size"), trap=("trap", "mean"), total=("total_12b", "median")).assign(trap=lambda z: (z["trap"] * 100).round(0)).round(1).T.to_string())
    df["jml_tanda"] = df[["spesial", "harga_turun_20", "di_bawah_ma200", "siklikal"]].sum(axis=1)
    print("\nJumlah tanda bahaya (spesial, harga turun, di bawah MA200, komoditas):")
    ringkas["tanda"] = {}
    for g, x in df.groupby("jml_tanda"):
        print(f"  {g} tanda: trap {x['trap'].mean() * 100:4.0f}% (n={len(x)}), median total {x['total_12b'].median():+.1f}%")
        ringkas["tanda"][str(int(g))] = {"trap": x["trap"].mean() * 100, "n": len(x), "median": x["total_12b"].median()}
    print("\nContoh trap terburuk:")
    print(df.sort_values("total_12b").head(10)[["kode", "tahun", "yield", "total_12b", "dividen_berikut_pct", "spesial", "harga_turun_20", "siklikal"]].round(1).to_string(index=False))
    dt.simpan_hasil("dividend_trap_ringkas", json.loads(json.dumps(ringkas, default=float)))


if __name__ == "__main__":
    utama()
