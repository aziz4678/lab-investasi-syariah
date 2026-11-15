import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.research import uji_h35 as h35
from backend.research import uji_h37 as h37

DEV_AKHIR = h37.DEV_AKHIR
HOLDOUT_AWAL = h37.HOLDOUT_AWAL
STRUKTUR = {
    "A": {"baseline": "50%", "varian": {"50%": 0.5, "25%": 0.25, "0%": 0.0}},
    "B": {"baseline": "50:50", "varian": {"50:50": (0.4, 0.4, 0.2), "25:75": (0.2, 0.6, 0.2), "0:100": (0.0, 0.8, 0.2)}},
}
JENDELA5 = [("2001-2005", 2001, 2005), ("2006-2010", 2006, 2010), ("2011-2015", 2011, 2015), ("2016-2020", 2016, 2020), ("2021-Okt 2026", 2021, 2026)]


def periode(R, nama):
    if nama == "dev":
        return R.loc[h35.AWAL + 1:DEV_AKHIR]
    if nama == "holdout":
        return R.loc[HOLDOUT_AWAL:h35.AKHIR]
    return R


def nilai(R, st, bobot):
    if st == "A":
        return h35.porto(R, bobot)[0]
    return h37.porto3(R, bobot, h37.SPREAD)[0]


def metrik(V):
    r = V.pct_change().dropna()
    j12 = h35.jendela(V, 12)
    t = h35.turun(V)
    vol = float(r.std() * np.sqrt(12))
    return {"cagr": h35.cagr(V), "dd": t["dd"], "vol": vol, "sharpe": float(r.mean() * 12 / vol), "j12": float(j12.min()), "j12_akhir": str(j12.idxmin()),
            "mar": h35.cagr(V) / abs(t["dd"]), "j10": float(h35.jendela(V, 120).min()) if len(V) > 121 else None}


def vonis_struktur(m, base, kecil_dulu):
    lulus = {}
    for v, x in m.items():
        if v == base:
            continue
        ok = {}
        for per in ("dev", "holdout"):
            ok[per] = [x[per]["cagr"] >= m[base][per]["cagr"], x[per]["dd"] >= m[base][per]["dd"] - 0.03]
        lulus[v] = {"detail": ok, "lolos": all(all(a) for a in ok.values())}
    lolos = [v for v in kecil_dulu if v in lulus and lulus[v]["lolos"]]
    pilihan = lolos[0] if lolos else base
    return lulus, pilihan


def info_seragam(m, base):
    out = {}
    for v, x in m.items():
        if v == base:
            continue
        out[v] = {}
        for per in ("dev", "holdout"):
            b, y = m[base][per], x[per]
            k1 = (y["j10"] is not None and b["j10"] is not None and y["j10"] > b["j10"])
            k2 = y["mar"] >= b["mar"]
            k3 = y["cagr"] >= b["cagr"] - 0.02
            out[v][per] = [bool(k1), bool(k2), bool(k3)]
    return out


def pc(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def tahunan(V):
    out = {}
    for y in range(2001, 2027):
        a = pd.Period(f"{y - 1}-12", "M") if y > 2001 else V.index[0]
        b = min(pd.Period(f"{y}-12", "M"), V.index[-1])
        out[y] = float(V.loc[b] / V.loc[a] - 1)
    return out


def jendela5(V):
    out = {}
    for nm, y1, y2 in JENDELA5:
        a = pd.Period(f"{y1 - 1}-12", "M") if y1 > 2001 else V.index[0]
        b = min(pd.Period(f"{y2}-12", "M"), V.index[-1])
        n = b - a
        n = n.n
        out[nm] = float((V.loc[b] / V.loc[a]) ** (12 / n) - 1)
    return out


def utama():
    R0 = h37.seri_h37()
    hasil, vonis, seri = {}, {}, {}
    for st, cfg in STRUKTUR.items():
        m = {v: {} for v in cfg["varian"]}
        seri[st] = {}
        for per in ("dev", "holdout", "penuh"):
            R = periode(R0, per)
            for v, bobot in cfg["varian"].items():
                V = nilai(R, st, bobot)
                m[v][per] = metrik(V)
                if per == "penuh":
                    seri[st][v] = V
        urut = [v for v in cfg["varian"] if v != cfg["baseline"]]
        lulus, pilihan = vonis_struktur(m, cfg["baseline"], urut)
        hasil[st] = {"metrik": m, "lulus": lulus, "pilihan": pilihan, "info_seragam": info_seragam(m, cfg["baseline"])}
        vonis[st] = pilihan
    print(f"H38: {len(R0)} bulan {R0.index[0]} s/d {R0.index[-1]}; dev s/d {DEV_AKHIR}, holdout dari {HOLDOUT_AWAL}")
    for st, cfg in STRUKTUR.items():
        print(f"\n=== Struktur {st} (baseline {cfg['baseline']}) ===")
        print(f"{'varian':<8}{'periode':<9}{'CAGR':>8}{'maxDD':>9}{'vol':>8}{'Sharpe':>8}{'12bln terburuk':>16}")
        for v in cfg["varian"]:
            for per in ("dev", "holdout", "penuh"):
                x = hasil[st]["metrik"][v][per]
                print(f"{v:<8}{per:<9}{pc(x['cagr']):>8}{pc(x['dd']):>9}{pc(x['vol']):>8}{x['sharpe']:>8.2f}{pc(x['j12']):>10} ({x['j12_akhir']})")
    print("\n=== Return per tahun kalender, struktur A (lokal 50 / 25 / 0) ===")
    ta = {v: tahunan(seri["A"][v]) for v in STRUKTUR["A"]["varian"]}
    for y in range(2001, 2027):
        print(f"{y}  " + "  ".join(f"{pc(ta[v][y]):>8}" for v in ta))
    print("\n=== INFO: jendela 5 tahun tidak tumpang tindih (CAGR, pemenang) ===")
    j5 = {}
    for st, cfg in STRUKTUR.items():
        j5[st] = {v: jendela5(seri[st][v]) for v in cfg["varian"]}
        print(f"Struktur {st}: " + " | ".join(cfg["varian"]))
        for nm, _, _ in JENDELA5:
            vals = {v: j5[st][v][nm] for v in cfg["varian"]}
            mnang = max(vals, key=vals.get)
            print(f"  {nm:<14}" + "  ".join(f"{pc(vals[v]):>8}" for v in vals) + f"   menang: {mnang}")
        menang = {v: sum(1 for nm, _, _ in JENDELA5 if max(j5[st], key=lambda z: j5[st][z][nm]) == v) for v in cfg["varian"]}
        print(f"  jumlah jendela menang: {menang}")
    print("\n=== VERDICT ===")
    for st, cfg in STRUKTUR.items():
        for v, x in hasil[st]["lulus"].items():
            d, h = x["detail"]["dev"], x["detail"]["holdout"]
            print(f"Struktur {st} {v}: {'LULUS' if x['lolos'] else 'GAGAL'} (dev CAGR {'v' if d[0] else 'x'} DD {'v' if d[1] else 'x'} | holdout CAGR {'v' if h[0] else 'x'} DD {'v' if h[1] else 'x'})")
        print(f"  => Struktur {st}: {'baseline ' + cfg['baseline'] + ' tetap' if vonis[st] == cfg['baseline'] else 'ganti ke ' + vonis[st]}")
        for v, x in hasil[st]["info_seragam"].items():
            print(f"  INFO standar seragam (analog K1 J10 terburuk, K2 MAR, K3 CAGR-2 poin) {v}: dev {x['dev']} holdout {x['holdout']}")
    dt.simpan_hasil("h38_hasil", json.loads(json.dumps({"versi": datetime.now().strftime("%Y-%m-%d %H:%M"), "hasil": hasil, "vonis": vonis, "jendela5": j5,
                                                        "tahunan_A": ta}, default=str)))
    print("SELESAI")


if __name__ == "__main__":
    utama()
