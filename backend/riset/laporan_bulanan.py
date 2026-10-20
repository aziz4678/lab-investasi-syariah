import numpy as np
import pandas as pd

MAKS_POSISI = 5


def simulasi_portofolio(tr, maks=MAKS_POSISI, seed=7):
    t = tr[["tgl", "tgl_exit", "net"] + (["skor"] if "skor" in tr else [])].copy()
    t["acak"] = np.random.default_rng(seed).random(len(t))
    urut = ["tgl", "skor"] if "skor" in t else ["tgl", "acak"]
    t = t.sort_values(urut, ascending=[True, False])
    buka = []
    ambil = []
    for r in t.itertuples():
        buka = [x for x in buka if x > r.tgl]
        if len(buka) >= maks:
            continue
        buka.append(r.tgl_exit)
        ambil.append(r.Index)
    return tr.loc[ambil]


def ringkas_bulanan(tr, maks=MAKS_POSISI):
    if tr.empty:
        print("laporan bulanan: tidak ada trade")
        return {}
    dipakai = simulasi_portofolio(tr, maks)
    faktor = 1 + dipakai["net"] / 100 / maks
    per_bulan = faktor.groupby(dipakai["tgl_exit"].dt.to_period("M")).prod()
    semua_bulan = pd.period_range(tr["tgl"].min().to_period("M"), tr["tgl_exit"].max().to_period("M"), freq="M")
    per_bulan = per_bulan.reindex(semua_bulan, fill_value=1.0)
    ret = (per_bulan - 1) * 100
    ekuitas = per_bulan.cumprod()
    dd = (ekuitas / ekuitas.cummax() - 1).min() * 100
    tahun = len(semua_bulan) / 12
    cagr = (ekuitas.iloc[-1] ** (1 / tahun) - 1) * 100 if tahun > 0 else np.nan
    kosong = (per_bulan == 1.0).mean() * 100
    print(f"portofolio {maks} posisi @ {100 / maks:.0f}%: {len(dipakai)}/{len(tr)} trade terambil | "
          f"bulanan rata2 {ret.mean():.2f}% median {ret.median():.2f}% | bulan positif {(ret > 0).mean() * 100:.0f}% | "
          f"terburuk {ret.min():.2f}% | DD maks {dd:.1f}% | CAGR {cagr:.1f}% | bulan tanpa trade {kosong:.0f}% | "
          f"ekuitas akhir {ekuitas.iloc[-1]:.2f}x")
    return {"cagr": cagr, "dd": dd, "bulan_positif": (ret > 0).mean() * 100, "ekuitas": ekuitas.iloc[-1]}
