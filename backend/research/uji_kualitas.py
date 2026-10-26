import argparse
import math
import time
import types
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.ingest import des_ojk
from backend.research import uji_h21_h22 as fw

VARIAN = ("K1", "K2", "K3")
TAHUN = {"dev": range(2011, 2020), "holdout": range(2020, 2027)}
BASI_BULAN = 15
MIN_LOLOS = 10
N_ACAK = 1000
SEED = 20261025
BULAN = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
PENANDA = kdb.penanda("holdout_dibuka_kualitas")


def keuangan():
    k = dt.baca("keuangan_idx")
    k = k[~k["curiga"].astype(bool) & k["kode"].notna()].copy()
    for kol in ("assets", "liabilities", "equity", "sales", "profit_owner", "bv"):
        k[kol] = pd.to_numeric(k[kol], errors="coerce").astype(float)
    k["terbit"] = pd.to_datetime(k["terbit"])
    k["fs_date"] = pd.to_datetime(k["fs_date"])
    fye = k["fye"].fillna("Dec").astype(str).str[:3].str.lower().map(BULAN).fillna(12).astype(int)
    m = ((k["fs_date"].dt.month - fye - 1) % 12) + 1
    k["laba_th"] = k["profit_owner"] * 12 / m
    k["roe"] = k["laba_th"] / k["equity"]
    k["roa"] = k["laba_th"] / k["assets"]
    k["npm"] = (k["profit_owner"] / k["sales"]).where(k["sales"] > 0)
    k["der"] = k["liabilities"] / k["equity"]
    return k[k["equity"] > 0]


def potret(k, t):
    x = k[(k["terbit"] <= t) & (k["fs_date"] >= t - pd.DateOffset(months=BASI_BULAN))]
    x = x.sort_values(["kode", "terbit", "bulan"]).drop_duplicates("kode", keep="last")
    return x.set_index("kode")


def tanggal_sinyal(S, periode):
    ab = S["akhir_bulan"]
    return [ab[pd.Period(f"{y}-06", "M")] for y in TAHUN[periode] if pd.Period(f"{y}-06", "M") in ab.index]


def lolos_dasar(S, t):
    P = S["P"]
    ok = (P["med60"].loc[t] >= 5e9) & (P["c_raw_ff"].loc[t] >= 100) & (P["jml_data"].loc[t] >= 250) & (P["aktif250"].loc[t] >= 0.9) & ~P["konversi"].loc[t]
    return set(ok[ok].index)


def siapkan(periode):
    k = keuangan()
    syariah_pernah = set(k.loc[k["syariah"].astype(bool), "kode"])
    des = des_ojk.baca()
    asli = fw.des_ojk
    fw.des_ojk = types.SimpleNamespace(baca=lambda: pd.DataFrame({"kode": sorted(set(des["kode"]) | syariah_pernah)}), syariah_pada=asli.syariah_pada)
    try:
        S = fw.susun(periode)
    finally:
        fw.des_ojk = asli
    sinyal = {}
    for t in tanggal_sinyal(S, periode):
        p = potret(k, t)
        p = p[p["syariah"].astype(bool)]
        dasar = sorted(lolos_dasar(S, t) & set(p.index))
        p = p.loc[dasar].copy()
        p["pbv"] = (S["P"]["c_raw_ff"].loc[t, dasar] / p["bv"]).where(p["bv"] > 0)
        sinyal[t] = p
    S["sinyal"] = sinyal
    return S


def calon(p, varian):
    if varian == "B":
        return p
    if varian == "K1":
        return p.dropna(subset=["roe", "der", "pbv"])
    if varian == "K2":
        return p.dropna(subset=["roe", "roa", "npm", "der"])
    return p[(p["der"] <= 2)].dropna(subset=["roe"])


def skor(p, varian):
    r = lambda s, naik: s.rank(pct=True, ascending=naik)
    if varian == "K1":
        return (r(p["roe"], True) + r(p["der"], False) + r(p["pbv"], False)) / 3
    if varian == "K2":
        return (r(p["roe"], True) + r(p["roa"], True) + r(p["npm"], True) + r(p["der"], False)) / 4
    return p["roe"]


def jadwal_varian(S, varian):
    tgl = S["tgl"]
    out = []
    for t, p in S["sinyal"].items():
        if len(calon(p, varian)) < MIN_LOLOS:
            continue
        nxt = tgl[tgl > t]
        if len(nxt):
            out.append((t, nxt[0]))
    return out


def pasang(S, varian, acak=None):
    jd = jadwal_varian(S, varian)
    fw.jadwal = lambda S_: jd

    def lolos(S_, t, min_nilai, min_harga):
        return pd.Index(sorted(calon(S["sinyal"][t], varian).index))

    def peringkat(S_, t, jenis, cl):
        p = calon(S["sinyal"][t], varian).loc[list(cl)]
        if acak is not None:
            rng = np.random.default_rng([acak, int(t.strftime("%Y%m%d"))])
            return list(rng.permutation(sorted(p.index)))
        s = skor(p, varian)
        return list(s.sort_values(ascending=False, kind="mergesort").index)

    fw.lolos = lolos
    fw.peringkat = peringkat


def simulasi(S, varian, acak=None, tick=1):
    pasang(S, varian, acak)
    return fw.simulasi(S, varian, tick=tick)


def pembanding(S):
    pasang(S, "B")
    return fw.pembanding_sama(S)


def potong(e, mulai):
    e = e[e.index >= mulai]
    return e / e.iloc[0]


def tanpa_top(sim, e_b, n=3):
    eq = sim["ekuitas"]
    mb = eq.groupby(eq.index.to_period("M")).last()
    awal_bln = mb.shift(1)
    awal_bln.iloc[0] = 1.0
    r = mb / awal_bln - 1
    rb = fw.bulanan(e_b).reindex(r.index).fillna(0)
    kontrib = {}
    for (k, b), v in sim["pnl"].items():
        if b in awal_bln.index:
            kontrib[k] = kontrib.get(k, 0) + v / awal_bln[b]
    top = [k for k, _ in sorted(kontrib.items(), key=lambda x: -x[1])[:n]]
    r2 = r.copy()
    for (k, b), v in sim["pnl"].items():
        if k in top and b in awal_bln.index:
            w = sim["bobot_awal"].get((k, b), 0) / awal_bln[b]
            r2[b] += -v / awal_bln[b] + w * rb[b]
    tahun = len(r2) / 12
    return ((1 + r2).prod() ** (1 / tahun) - 1) * 100, top


def ringkas(sim, eb, ej):
    e = sim["ekuitas"]
    mulai = e.index[0]
    eb, ej = potong(eb, mulai), potong(ej, mulai)
    return {"cagr": fw.cagr(e), "dd": fw.max_dd(e), "cagr_b1": fw.cagr(eb), "dd_b1": fw.max_dd(eb), "cagr_b2": fw.cagr(ej),
            "selisih": fw.cagr(e) - fw.cagr(eb), "posisi": float(sim["posisi"].mean()),
            "turnover": sim["dagang"] / ((e.index[-1] - e.index[0]).days / 365.25) / e.mean() * 100}


def cek(S):
    print("Potret per tanggal sinyal (syariah + likuid + data valid):")
    for t, p in S["sinyal"].items():
        jml = {v: len(calon(p, v)) for v in VARIAN}
        umur = ((t - p["fs_date"]).dt.days / 30.4).median() if len(p) else float("nan")
        print(f"  {t:%Y-%m-%d}: dasar {len(p):3d} | K1 {jml['K1']:3d} K2 {jml['K2']:3d} K3 {jml['K3']:3d} | umur laporan median {umur:4.1f} bln"
              f"{'' if len(p) >= MIN_LOLOS else '  <- dilewati (portofolio dipegang)'}")


def jalankan_dev():
    t0 = time.time()
    S = siapkan("dev")
    cek(S)
    eb = pembanding(S)
    ej = fw.pembanding_jii(S, eb.index[0])
    hasil, sims = {}, {}
    for v in VARIAN:
        sims[v] = simulasi(S, v)
        hasil[v] = ringkas(sims[v], eb, ej)
    print(f"\n{'varian':7s} {'CAGR':>7s} {'DD':>7s} {'B1':>7s} {'DD B1':>7s} {'JII':>7s} {'selisih':>8s} {'posisi':>6s} {'turnover':>8s}")
    for v, h in hasil.items():
        print(f"{v:7s} {h['cagr']:6.2f}% {h['dd']:6.1f}% {h['cagr_b1']:6.2f}% {h['dd_b1']:6.1f}% {h['cagr_b2']:6.2f}% {h['selisih']:7.2f}  {h['posisi']:6.1f} {h['turnover']:7.0f}%")
    menang = max(VARIAN, key=lambda v: hasil[v]["selisih"])
    h = hasil[menang]
    print(f"\nPemenang dev: {menang} (selisih {h['selisih']:.2f} poin)")
    print(f"Uji anti-kebetulan: {N_ACAK} x 3 portofolio acak ...", flush=True)
    terbaik = []
    for i in range(N_ACAK):
        sel = []
        for j, v in enumerate(VARIAN):
            sim = simulasi(S, v, acak=SEED + i * 10 + j)
            sel.append(fw.cagr(sim["ekuitas"]) - fw.cagr(potong(eb, sim["ekuitas"].index[0])))
        terbaik.append(max(sel))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{N_ACAK} ulangan, p95 sementara {np.percentile(terbaik, 95):.2f} ({time.time() - t0:.0f} dtk)", flush=True)
    p95 = float(np.percentile(terbaik, 95))
    peringkat_p = float((np.array(terbaik) < h["selisih"]).mean() * 100)
    k1 = h["cagr"] > h["cagr_b1"] and h["cagr"] > h["cagr_b2"]
    k2 = h["dd"] >= h["dd_b1"]
    k3 = h["selisih"] > p95
    print(f"\nKriteria dev ({menang}):")
    print(f"  [{'LULUS' if k1 else 'GAGAL'}] 1. CAGR {h['cagr']:.2f}% > B1 {h['cagr_b1']:.2f}% dan > JII {h['cagr_b2']:.2f}%")
    print(f"  [{'LULUS' if k2 else 'GAGAL'}] 2. max DD {h['dd']:.1f}% tidak lebih dalam dari B1 {h['dd_b1']:.1f}%")
    print(f"  [{'LULUS' if k3 else 'GAGAL'}] 3. selisih {h['selisih']:.2f} > p95 acak-terbaik {p95:.2f} (mengalahkan {peringkat_p:.1f}% ulangan)")
    lulus = k1 and k2 and k3
    print(f"\nHASIL DEV SERI K: {'LULUS' if lulus else 'GAGAL'}")
    lap = laporan(S, sims, menang, eb, "h11a_dev")
    tahun = pd.DataFrame({v: fw.per_tahun(sims[v]["ekuitas"]) for v in VARIAN} | {"B1": fw.per_tahun(potong(eb, sims[VARIAN[0]]["ekuitas"].index[0]))})
    print("\nPer tahun (%):\n" + tahun.round(1).T.to_string())
    dt.simpan_hasil("kualitas_dev", pd.DataFrame(hasil).T.reset_index(names="varian"))
    dt.simpan_hasil("kualitas_dev_acak", pd.DataFrame({"acak_terbaik": terbaik}))
    dt.simpan_hasil("kualitas_dev_tahun", tahun.reset_index(names="tahun"))
    dt.simpan_hasil("kualitas_dev_putusan", pd.DataFrame([{"pemenang": menang, "p95": p95, "persentil": peringkat_p, "k1": k1, "k2": k2, "k3": k3, "lulus": lulus, **lap}]))
    dt.hasil_teks("status_kualitas").write_text(f"{'LULUS' if lulus else 'GAGAL'} {menang}", encoding="utf-8")
    print(f"\nWaktu total {time.time() - t0:.0f} dtk")
    return lulus


def laporan(S, sims, menang, eb, versi_ft):
    sim = sims[menang]
    e = sim["ekuitas"]
    eb2 = potong(eb, e.index[0])
    pasang(S, menang)
    sim2 = fw.simulasi(S, menang, tick=2)
    tanpa, top = tanpa_top(sim, eb2, 3)
    kor, n = fw.korelasi_follow_tren(e, versi_ft)
    print(f"\nLaporan saja ({menang}): biaya 2 tick CAGR {fw.cagr(sim2['ekuitas']):.2f}% | tanpa 3 penyumbang terbesar {top}: CAGR {tanpa:.2f}% (B1 {fw.cagr(eb2):.2f}%) | "
          f"korelasi bulanan dengan Follow Tren {kor} ({n} bln)")
    return {"cagr_2tick": fw.cagr(sim2["ekuitas"]), "cagr_tanpa3": tanpa, "top3": " ".join(top), "korelasi_ft": kor}


def jalankan_holdout():
    status = dt.hasil_teks("status_kualitas")
    isi = status.read_text(encoding="utf-8").split() if status.exists() else []
    if not isi or isi[0] != "LULUS":
        raise SystemExit("Holdout seri K hanya dibuka kalau dev LULUS.")
    if PENANDA.exists():
        raise SystemExit(f"Holdout seri K sudah pernah dibuka ({PENANDA.read_text().strip()})")
    PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    menang = isi[1]
    S = siapkan("holdout")
    cek(S)
    eb = pembanding(S)
    ej = fw.pembanding_jii(S, eb.index[0])
    sim = simulasi(S, menang)
    h = ringkas(sim, eb, ej)
    k1 = h["cagr"] > h["cagr_b1"]
    k2 = h["dd"] >= h["dd_b1"] - 5
    print(f"\nHoldout {menang}: CAGR {h['cagr']:.2f}% vs B1 {h['cagr_b1']:.2f}% (JII {h['cagr_b2']:.2f}%), DD {h['dd']:.1f}% vs B1 {h['dd_b1']:.1f}%")
    print(f"  [{'LULUS' if k1 else 'GAGAL'}] 1. CAGR > B1")
    print(f"  [{'LULUS' if k2 else 'GAGAL'}] 2. DD >= DD B1 - 5 poin ({h['dd_b1'] - 5:.1f}%)")
    lulus = k1 and k2
    print(f"HASIL HOLDOUT {menang}: {'LULUS' if lulus else 'GAGAL'}")
    lap = laporan(S, {menang: sim}, menang, eb, "h11a_2020")
    tahun = pd.DataFrame({menang: fw.per_tahun(sim["ekuitas"]), "B1": fw.per_tahun(potong(eb, sim["ekuitas"].index[0]))})
    print("\nPer tahun (%):\n" + tahun.round(1).T.to_string())
    dt.simpan_hasil("kualitas_holdout", pd.DataFrame([{**h, "varian": menang, "k1": k1, "k2": k2, "lulus": lulus, **lap}]))
    return lulus


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("tahap", choices=["cek", "dev", "holdout"])
    a = ap.parse_args()
    if a.tahap == "cek":
        cek(siapkan("dev"))
    elif a.tahap == "dev":
        jalankan_dev()
    else:
        jalankan_holdout()


if __name__ == "__main__":
    utama()
