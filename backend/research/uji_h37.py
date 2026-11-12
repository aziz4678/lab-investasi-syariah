import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.db import koneksi
from backend.research import uji_h35 as h35

AWAL = h35.AWAL
AKHIR = h35.AKHIR
DEV_AKHIR = pd.Period("2013-12", "M")
HOLDOUT_AWAL = pd.Period("2014-01", "M")
BIAYA_EMAS_TAHUN = 0.005
SPREAD = 0.03
BOBOT_UTAMA = (0.4, 0.4, 0.2)
VARIAN = [("45/45/10, spread 3%", (0.45, 0.45, 0.10), 0.005, 0.03), ("35/35/30, spread 3%", (0.35, 0.35, 0.30), 0.005, 0.03),
          ("40/40/20, spread 1%", (0.4, 0.4, 0.2), 0.005, 0.01), ("40/40/20, spread 6%", (0.4, 0.4, 0.2), 0.005, 0.06)]
PENANDA = koneksi.penanda("holdout_disegel_h37")
PENANDA_BUKA = koneksi.penanda("holdout_dibuka_h37")


def emas_usd_bulanan():
    s = h35.bulanan(harga.indeks("pasar_panjang/emas_usd")["close"])
    hilang = [b for b in pd.period_range(AWAL, AKHIR, freq="M") if b not in s.index]
    if hilang:
        raise harga.DataTidakAda(f"emas bolong: {hilang[:5]}")
    return s.loc[AWAL:AKHIR]


def seri_h37(biaya_emas=BIAYA_EMAS_TAHUN):
    R = h35.seri(h35.DASAR)
    g = emas_usd_bulanan()
    fx = h35.kurs()
    bulan = R.index
    r_g = (g / g.shift(1)).reindex(bulan)
    r_fx = (fx / fx.shift(1)).reindex(bulan)
    if r_g.isna().any() or r_fx.isna().any():
        raise harga.DataTidakAda("ada bulan emas tanpa return")
    R = R.copy()
    R["emas_usd"] = r_g - 1
    R["emas"] = r_g * r_fx * (1 - biaya_emas) ** (1 / 12) - 1
    return R


def porto3(R, bobot, spread, biaya_rebal=h35.BIAYA_REBAL):
    t = {"idx": bobot[0], "gl": bobot[1], "emas": bobot[2]}
    awal = t["emas"] * spread / 2
    w = {x: t[x] * (1 - awal) for x in t}
    nilai, b_total = [1.0], awal
    for b, r in R.iterrows():
        for x in w:
            w[x] *= 1 + r[x]
        tot = sum(w.values())
        if b.month == 12:
            jual = sum(max(0.0, w[x] - t[x] * tot) for x in ("idx", "gl"))
            c = biaya_rebal * jual + spread / 2 * abs(w["emas"] - t["emas"] * tot)
            b_total += c
            tot -= c
            w = {x: t[x] * tot for x in t}
        nilai.append(tot)
    return pd.Series(nilai, index=[R.index[0] - 1] + list(R.index)), b_total


def metrik(V):
    t = h35.turun(V)
    j = h35.jendela(V, h35.JENDELA)
    r = V.pct_change().dropna()
    return {"cagr": h35.cagr(V), "dd": t["dd"], "dd_lembah": t["lembah"], "dd_puncak": t["puncak"], "pulih": t["pulih"],
            "j10_buruk": float(j.min()) if len(j) else None, "j10_akhir": str(j.idxmin()) if len(j) else None, "n_jendela": len(j),
            "vol": float(r.std() * np.sqrt(12)), "bulan": len(r)}


def kriteria(h37, h35m):
    k1 = h37["dd"] - h35m["dd"] >= 0.05
    k2 = h37["j10_buruk"] is not None and h35m["j10_buruk"] is not None and h37["j10_buruk"] > h35m["j10_buruk"]
    k3 = h37["cagr"] >= h35m["cagr"] - 0.01
    return {"K1": [bool(k1), h37["dd"], h35m["dd"]], "K2": [bool(k2), h37["j10_buruk"], h35m["j10_buruk"]], "K3": [bool(k3), h37["cagr"], h35m["cagr"]]}


def per_tahun(V, R, tahun):
    out = {}
    for y in tahun:
        a = pd.Period(f"{y - 1}-12", "M") if y > 2001 else AWAL
        b = min(pd.Period(f"{y}-12", "M"), V.index[-1])
        out[y] = {"v": float(V.loc[b] / V.loc[a] - 1)}
    return out


def tahunan_seri(r, tahun):
    out = {}
    for y in tahun:
        x = r.loc[pd.Period(f"{y}-01", "M"):pd.Period(f"{y}-12", "M")]
        out[y] = float((1 + x).prod() - 1)
    return out


def pc(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def pilih(R, periode):
    if periode == "dev":
        return R.loc[AWAL + 1:DEV_AKHIR]
    return R.loc[HOLDOUT_AWAL:AKHIR]


def utama(periode="dev", simpan=True):
    if not PENANDA.exists():
        PENANDA.write_text(f"disegel {datetime.now():%Y-%m-%d %H:%M} (H37 dikunci 2026-11-12)\n")
    R = pilih(seri_h37(), periode)
    V37, b37 = porto3(R, BOBOT_UTAMA, SPREAD)
    V35, b35 = h35.porto(R, 0.5)
    m37, m35 = metrik(V37), metrik(V35)
    kr = kriteria(m37, m35)
    lolos = all(v[0] for v in kr.values())
    varian = {}
    for nama, bobot, be, sp in VARIAN:
        Rv = pilih(seri_h37(be), periode)
        Vv, _ = porto3(Rv, bobot, sp)
        mv = metrik(Vv)
        kv = kriteria(mv, m35)
        varian[nama] = {"metrik": mv, "kriteria": kv, "lolos": sum(v[0] for v in kv.values())}
    lolos_varian = all(v["lolos"] >= 2 for v in varian.values())
    vonis = "LOLOS" if (lolos and lolos_varian) else "GAGAL"
    tahun = list(range(R.index[0].year, R.index[-1].year + 1))
    t37 = per_tahun(V37, R, tahun)
    t35 = per_tahun(V35, R, tahun)
    te = tahunan_seri(R["emas"], tahun)
    korel = {"emas_vs_jii": float(R["emas"].corr(R["idx"])), "emas_vs_global": float(R["emas"].corr(R["gl"])), "jii_vs_global": float(R["idx"].corr(R["gl"]))}
    keluaran = {"periode": periode, "versi": datetime.now().strftime("%Y-%m-%d %H:%M"), "bulan": len(R), "utama": m37, "h35": m35, "kriteria": kr, "varian": varian,
                "tahunan": {"h37": t37, "h35": t35, "emas": te}, "korelasi": korel, "biaya_transaksi_h37": b37, "biaya_rebal_h35": b35,
                "n_jendela_10th": m37["n_jendela"], "vonis": vonis, "lolos_utama": lolos, "lolos_varian": lolos_varian,
                "keterbatasan": ["Indeks/futures, bukan produk; emas = GC=F x kurs, bukan Antam.", "Dividen JII dan global pra-2008 diasumsikan (cara H35).",
                                 "Jendela 10 th dev saling tumpang tindih, efektif hanya ±2,7 th independen.", "Arah umum data sudah diketahui (kontaminasi H35 tercatat)."]}
    print(f"H37 {periode}: {len(R)} bulan, {R.index[0]} s/d {R.index[-1]}")
    print(f"{'':<22}{'H37 40/40/20':>14}{'H35 50/50':>12}")
    print(f"{'CAGR':<22}{pc(m37['cagr']):>14}{pc(m35['cagr']):>12}")
    print(f"{'Max DD':<22}{pc(m37['dd']):>14}{pc(m35['dd']):>12}   lembah {m37['dd_lembah']} / {m35['dd_lembah']}")
    print(f"{'CAGR 10th terburuk':<22}{pc(m37['j10_buruk']):>14}{pc(m35['j10_buruk']):>12}   berakhir {m37['j10_akhir']} / {m35['j10_akhir']}")
    print(f"{'Volatilitas':<22}{pc(m37['vol']):>14}{pc(m35['vol']):>12}")
    print(f"Korelasi bulanan: emas-JII {korel['emas_vs_jii']:.2f}, emas-global {korel['emas_vs_global']:.2f}, JII-global {korel['jii_vs_global']:.2f}")
    print("Tahun   H37    H35   emas")
    for y in tahun:
        print(f"{y}  {pc(t37[y]['v']):>7}{pc(t35[y]['v']):>7}{pc(te[y]):>7}")
    print("Kriteria utama: " + " | ".join(f"{k} {'LOLOS' if v[0] else 'GAGAL'}" for k, v in kr.items()))
    for nama, v in varian.items():
        print(f"  {nama}: {v['lolos']}/3 " + " ".join(f"{k}{'v' if x[0] else 'x'}" for k, x in v["kriteria"].items()) + f" CAGR {pc(v['metrik']['cagr'])} DD {pc(v['metrik']['dd'])} J10 {pc(v['metrik']['j10_buruk'])}")
    print(f"Jendela 10 th tersedia: {m37['n_jendela']} (bulanan, tumpang tindih; dev ±{m37['bulan'] / 12:.1f} th)")
    alasan = [k for k, v in kr.items() if not v[0]] + [n for n, v in varian.items() if v["lolos"] < 2]
    print(f"VONIS {periode}: {vonis}" + (f" (gagal: {', '.join(alasan)})" if alasan else " (utama 3/3, semua varian >= 2/3)"))
    if simpan:
        nama = "h37_dev" if periode == "dev" else "h37_holdout"
        dt.simpan_hasil(nama, json.loads(json.dumps(keluaran, default=str)))
    print("SELESAI")
    return keluaran


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "dev":
        utama("dev")
    elif arg == "holdout":
        if not PENANDA_BUKA.exists():
            raise SystemExit("holdout H37 disegel; menunggu konfirmasi user (tulis penanda holdout_dibuka_h37)")
        utama("holdout")
    else:
        raise SystemExit("pakai: dev | holdout")
