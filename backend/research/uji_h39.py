import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.research import uji_h35 as h35
from backend.research import uji_h37 as h37

AWAL = pd.Period("2014-09", "M")
AKHIR = h35.AKHIR
DEV_AKHIR = pd.Period("2020-12", "M")
HOLDOUT_AWAL = pd.Period("2021-01", "M")
BIAYA_BTC = 0.005
SPREAD = h37.SPREAD
STRUKTUR = {"A": (0.5, 0.5, 0.0), "B": (0.4, 0.4, 0.2)}
PORSI = [0.0, 0.025, 0.05]
BULAN_TAHUNAN = (12,)
BULAN_KUARTAL = (3, 6, 9, 12)
DILEWATI = [
    ("Tanpa 5/10 saham penyumbang terbesar", "kaki portofolio adalah indeks/RD/emas/BTC, tidak ada saham tunggal untuk dibuang"),
    ("S1 spread 2 tick", "tidak ada ticker saham; biaya BTC 0,5% dan spread emas 3% sudah asumsi eksplisit"),
    ("S2 kapasitas Rp20 M", "bukan saham IDX; kapasitas BTC/RD/ETF jauh di atas modal pribadi"),
    ("S3 harga saham >= Rp200", "tidak ada saham; syarat harga minimum tidak relevan"),
]


def bulanan_kripto(nama):
    d = harga.indeks_luar(nama)["close"].dropna().sort_index()
    s = h35.bulanan(d)
    hilang = [b for b in pd.period_range(AWAL, AKHIR, freq="M") if b not in s.index]
    if hilang and nama == "btc_usd":
        raise harga.DataTidakAda(f"{nama} bolong: {hilang[:5]}")
    return s


def seri_h39():
    R = h37.seri_h37().loc[AWAL + 1:AKHIR].copy()
    fx = h35.kurs()
    for nama, kol in (("btc_usd", "btc"), ("eth_usd", "eth")):
        s = bulanan_kripto(nama)
        r_usd = (s / s.shift(1)).reindex(R.index)
        r_fx = (fx / fx.shift(1)).reindex(R.index)
        R[kol] = r_usd * r_fx - 1
        if kol == "btc" and (R[kol].isna().any() or r_fx.isna().any()):
            raise harga.DataTidakAda("ada bulan BTC tanpa return")
    return R


def target(struktur, porsi_btc, kaki=("btc",), pecah=None):
    a, b, c = STRUKTUR[struktur]
    sisa = 1 - porsi_btc
    t = {"idx": a * sisa, "gl": b * sisa, "emas": c * sisa}
    if pecah is None:
        t["btc"] = porsi_btc
    else:
        t["btc"] = porsi_btc * pecah[0]
        t["eth"] = porsi_btc * pecah[1]
    return {k: v for k, v in t.items() if v > 0}


def porto(R, t, bulan_rebal=BULAN_TAHUNAN):
    awal_biaya = t.get("emas", 0) * SPREAD / 2 + sum(t.get(x, 0) * BIAYA_BTC for x in ("btc", "eth"))
    w = {x: t[x] * (1 - awal_biaya) for x in t}
    nilai, maks_btc = [1.0], 0.0
    for b, r in R.iterrows():
        for x in w:
            w[x] *= 1 + r[x]
        tot = sum(w.values())
        maks_btc = max(maks_btc, sum(w.get(x, 0) for x in ("btc", "eth")) / tot)
        if b.month in bulan_rebal:
            c = 0.0
            for x in w:
                selisih = w[x] - t[x] * tot
                if x in ("idx", "gl"):
                    c += h35.BIAYA_REBAL * max(0.0, selisih)
                elif x == "emas":
                    c += SPREAD / 2 * abs(selisih)
                else:
                    c += BIAYA_BTC * abs(selisih)
            tot -= c
            w = {x: t[x] * tot for x in t}
        nilai.append(tot)
    return pd.Series(nilai, index=[R.index[0] - 1] + list(R.index)), maks_btc


def periode(R, nama):
    if nama == "dev":
        return R.loc[:DEV_AKHIR]
    if nama == "holdout":
        return R.loc[HOLDOUT_AWAL:]
    return R


def metrik(V):
    r = V.pct_change().dropna()
    j12 = h35.jendela(V, 12)
    t = h35.turun(V)
    vol = float(r.std() * np.sqrt(12))
    j10 = h35.jendela(V, 120)
    return {"cagr": h35.cagr(V), "dd": t["dd"], "vol": vol, "sharpe": float(r.mean() * 12 / vol), "j12": float(j12.min()), "j12_akhir": str(j12.idxmin()),
            "mar": h35.cagr(V) / abs(t["dd"]), "j10": float(j10.min()) if len(j10) else None}


def tahunan(V):
    out = {}
    for y in range(2014, 2027):
        a = pd.Period(f"{y - 1}-12", "M") if y > 2014 else V.index[0]
        b = min(pd.Period(f"{y}-12", "M"), V.index[-1])
        out[y] = float(V.loc[b] / V.loc[a] - 1)
    return out


def pc(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def lulus(m, base):
    hasil = {}
    for v, x in m.items():
        if v == base:
            continue
        ok = {per: [x[per]["cagr"] >= m[base][per]["cagr"], x[per]["dd"] >= m[base][per]["dd"] - 0.03] for per in ("dev", "holdout")}
        hasil[v] = {"detail": ok, "lolos": all(all(a) for a in ok.values())}
    return hasil


def pilih(hs):
    if hs.get(0.05, {}).get("lolos"):
        return 0.05
    if hs.get(0.025, {}).get("lolos"):
        return 0.025
    return 0.0


def seragam(m, base):
    out = {}
    for v, x in m.items():
        if v == base:
            continue
        out[v] = {}
        for per in ("dev", "holdout", "penuh"):
            b, y = m[base][per], x[per]
            out[v][per] = {"K1": bool(y["j10"] is not None and b["j10"] is not None and y["j10"] > b["j10"]), "K2": bool(y["mar"] >= b["mar"]), "K3": bool(y["cagr"] >= b["cagr"] - 0.02)}
    return out


def utama():
    R0 = seri_h39()
    hasil, vonis, seri, maks = {}, {}, {}, {}
    for st in STRUKTUR:
        m = {p: {} for p in PORSI}
        seri[st], maks[st] = {}, {}
        for per in ("dev", "holdout", "penuh"):
            R = periode(R0, per)
            for p in PORSI:
                V, mk = porto(R, target(st, p))
                m[p][per] = metrik(V)
                if per == "penuh":
                    seri[st][p] = V
                    maks[st][p] = mk
        hs = lulus(m, 0.0)
        hasil[st] = {"metrik": m, "lulus": hs, "pilihan": pilih(hs), "seragam": seragam(m, 0.0)}
        vonis[st] = hasil[st]["pilihan"]
    ref = porto(R0, target("B", 0.0))[0]
    cek = h37.porto3(R0, (0.4, 0.4, 0.2), SPREAD)[0]
    cek_a = h35.porto(R0, 0.5)[0]
    sama = float(np.abs(ref / cek - 1).max()) < 1e-9 and float(np.abs(porto(R0, target("A", 0.0))[0] / cek_a - 1).max()) < 1e-9
    print(f"H39: {len(R0)} bulan {R0.index[0]} s/d {R0.index[-1]}; dev s/d {DEV_AKHIR}, holdout dari {HOLDOUT_AWAL}; baseline identik mesin H35/H37: {sama}")
    print("\n=== 1. Metrik per struktur, varian, periode ===")
    for st in STRUKTUR:
        print(f"\nStruktur {st}")
        print(f"{'BTC':<7}{'periode':<9}{'CAGR':>8}{'maxDD':>9}{'vol':>8}{'Sharpe':>8}{'12bln terburuk':>18}")
        for p in PORSI:
            for per in ("dev", "holdout", "penuh"):
                x = hasil[st]["metrik"][p][per]
                print(f"{p * 100:<7.1f}{per:<9}{pc(x['cagr']):>8}{pc(x['dd']):>9}{pc(x['vol']):>8}{x['sharpe']:>8.2f}{pc(x['j12']):>10} ({x['j12_akhir']})")
    print("\n=== 2. Return per tahun kalender, struktur B (2014 = Okt-Des) ===")
    tb = {p: tahunan(seri["B"][p]) for p in PORSI}
    print(f"{'tahun':<7}" + "".join(f"{p * 100:>8.1f}%" for p in PORSI))
    for y in range(2014, 2027):
        print(f"{y:<7}" + "".join(f"{pc(tb[p][y]):>9}" for p in PORSI))
    print("\n=== 3. Porsi BTC tertinggi antar-rebalance (akhir bulan, sebelum rebalance) ===")
    for st in STRUKTUR:
        print(f"Struktur {st}: " + " | ".join(f"target {p * 100:.1f}% -> maks {maks[st][p] * 100:.1f}%" for p in PORSI if p > 0))
    print("\n=== 4. INFO (bukan kriteria) ===")
    info = {}
    for st in STRUKTUR:
        info[st] = {}
        for p in (0.025, 0.05):
            info[st][f"kuartalan_{p}"] = {}
            for per in ("dev", "holdout", "penuh"):
                V, mk = porto(periode(R0, per), target(st, p), BULAN_KUARTAL)
                info[st][f"kuartalan_{p}"][per] = {**metrik(V), "maks_btc": mk}
        print(f"\nStruktur {st}: rebalance kuartalan vs tahunan (CAGR / maxDD)")
        print(f"{'varian':<22}{'dev':>20}{'holdout':>20}{'penuh':>20}")
        for p in (0.025, 0.05):
            for jenis, sumber in (("tahunan", lambda per: hasil[st]["metrik"][p][per]), ("kuartalan", lambda per: info[st][f"kuartalan_{p}"][per])):
                print(f"{p * 100:.1f}% {jenis:<15}" + "".join(f"{pc(sumber(per)['cagr']):>10} /{pc(sumber(per)['dd']):>8}" for per in ("dev", "holdout", "penuh")))
    R18 = R0.loc[pd.Period("2018-01", "M"):]
    info["btc_eth"] = {}
    print("\nBTC+ETH 50/50 untuk porsi 5%, Jan 2018 s/d Okt 2026 (CAGR / maxDD / vol)")
    for st in STRUKTUR:
        base = metrik(porto(R18, target(st, 0.0))[0])
        btc = metrik(porto(R18, target(st, 0.05))[0])
        be_t, mk_t = porto(R18, target(st, 0.05, pecah=(0.5, 0.5)))
        be_k, mk_k = porto(R18, target(st, 0.05, pecah=(0.5, 0.5)), BULAN_KUARTAL)
        be, bek = metrik(be_t), metrik(be_k)
        info["btc_eth"][st] = {"baseline": base, "btc5": btc, "btc_eth5": be, "btc_eth5_kuartalan": bek, "maks_tahunan": mk_t, "maks_kuartalan": mk_k}
        for nama, x in (("baseline 0%", base), ("BTC 5%", btc), ("BTC+ETH 5% tahunan", be), ("BTC+ETH 5% kuartalan", bek)):
            print(f"  {st} {nama:<22}{pc(x['cagr']):>8}{pc(x['dd']):>9}{pc(x['vol']):>8}")
    print("\nStandar seragam analog (K1 J10 terburuk 10 th [hanya periode penuh], K2 MAR, K3 CAGR-2 poin), v = lulus:")
    for st in STRUKTUR:
        for p, x in hasil[st]["seragam"].items():
            print(f"  {st} BTC {p * 100:.1f}%: " + " | ".join(f"{per} " + "".join(f"{k}{'v' if ok else 'x'} " for k, ok in x[per].items()) for per in ("dev", "holdout", "penuh")))
    print("\nTes standar seragam yang dilewati (tidak berlaku untuk portofolio indeks/BTC):")
    for nama, alasan in DILEWATI:
        print(f"  - {nama}: {alasan}")
    print("\n=== 5. VERDICT ===")
    for st in STRUKTUR:
        for p, x in hasil[st]["lulus"].items():
            d, h = x["detail"]["dev"], x["detail"]["holdout"]
            print(f"Struktur {st} BTC {p * 100:.1f}%: {'LULUS' if x['lolos'] else 'GAGAL'} (dev CAGR {'v' if d[0] else 'x'} DD {'v' if d[1] else 'x'} | holdout CAGR {'v' if h[0] else 'x'} DD {'v' if h[1] else 'x'})")
        print(f"  => Struktur {st}: " + ("BTC tidak masuk" if vonis[st] == 0 else f"BTC {vonis[st] * 100:.1f}% masuk"))
    dt.simpan_hasil("h39_hasil", json.loads(json.dumps({"versi": datetime.now().strftime("%Y-%m-%d %H:%M"), "hasil": hasil, "vonis": vonis, "maks_btc": maks, "info": info,
                                                        "tahunan_B": tb, "dilewati": DILEWATI}, default=str)))
    print("SELESAI")


def ketahanan():
    R0 = seri_h39()
    hasil = {}
    for st in STRUKTUR:
        hasil[st] = {}
        for m in range(1, 13):
            cel = {}
            for p in PORSI:
                cel[p] = {}
                for per in ("dev", "holdout", "penuh"):
                    V, mk = porto(periode(R0, per), target(st, p), (m,))
                    cel[p][per] = {"cagr": h35.cagr(V), "dd": h35.turun(V)["dd"], "maks_btc": mk}
            hasil[st][m] = cel
    ringkas, vonis = {}, {}
    print("=== Ketahanan bulan rebalance (holdout Jan 2021-Okt 2026) ===")
    print(f"{'struktur':<9}{'porsi':<7}{'m lulus':>8}{'CAGR min':>10}{'median':>9}{'maks':>8}{'DD terburuk':>13}{'BTC maks terburuk':>19}")
    for st in STRUKTUR:
        ringkas[st] = {}
        for p in (0.025, 0.05):
            lolos = [m for m in range(1, 13) if hasil[st][m][p]["holdout"]["cagr"] >= hasil[st][m][0.0]["holdout"]["cagr"]
                     and hasil[st][m][p]["holdout"]["dd"] >= hasil[st][m][0.0]["holdout"]["dd"] - 0.03]
            cg = [hasil[st][m][p]["holdout"]["cagr"] for m in range(1, 13)]
            ringkas[st][p] = {"lolos": lolos, "n": len(lolos), "cagr_min": min(cg), "cagr_median": float(np.median(cg)), "cagr_maks": max(cg),
                              "dd_terburuk": min(hasil[st][m][p]["holdout"]["dd"] for m in range(1, 13)),
                              "btc_maks_terburuk": max(hasil[st][m][p][per]["maks_btc"] for m in range(1, 13) for per in ("dev", "holdout", "penuh"))}
            x = ringkas[st][p]
            print(f"{st:<9}{p * 100:<7.1f}{x['n']:>5}/12{pc(x['cagr_min']):>10}{pc(x['cagr_median']):>9}{pc(x['cagr_maks']):>8}{pc(x['dd_terburuk']):>13}{x['btc_maks_terburuk'] * 100:>18.1f}%")
        vonis[st] = 0.05 if ringkas[st][0.05]["n"] >= 9 else (0.025 if ringkas[st][0.025]["n"] >= 9 else 0.0)
    print()
    print("Baseline holdout per m (CAGR / DD), struktur A | B:")
    for m in range(1, 13):
        print(f"  m={m:<3}" + " | ".join(f"{pc(hasil[st][m][0.0]['holdout']['cagr'])} / {pc(hasil[st][m][0.0]['holdout']['dd'])}" for st in STRUKTUR)
              + "   lulus 5%: " + " ".join(("v" if m in ringkas[st][0.05]["lolos"] else "x") for st in STRUKTUR)
              + "  2,5%: " + " ".join(("v" if m in ringkas[st][0.025]["lolos"] else "x") for st in STRUKTUR))
    print()
    print("Dev/penuh per m, porsi 5% (CAGR / DD):")
    for st in STRUKTUR:
        for per in ("dev", "penuh"):
            c = [hasil[st][m][0.05][per]["cagr"] for m in range(1, 13)]
            d = [hasil[st][m][0.05][per]["dd"] for m in range(1, 13)]
            print(f"  {st} {per:<7}CAGR {pc(min(c))}..{pc(max(c))} (median {pc(float(np.median(c)))}), DD terburuk {pc(min(d))}")
    print()
    print("=== VERDICT KETAHANAN ===")
    for st in STRUKTUR:
        print(f"Struktur {st}: " + ("BTC tidak masuk" if vonis[st] == 0 else f"BTC {vonis[st] * 100:.1f}% dipakai"))
    akhir = "LOLOS" if any(v > 0 for v in vonis.values()) else "GAGAL"
    print(f"Status H39: {akhir}")
    dt.simpan_hasil("h39_ketahanan", json.loads(json.dumps({"versi": datetime.now().strftime("%Y-%m-%d %H:%M"), "hasil": hasil, "ringkas": ringkas, "vonis": vonis, "status": akhir}, default=str)))
    print("SELESAI")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ketahanan":
        ketahanan()
    else:
        utama()
