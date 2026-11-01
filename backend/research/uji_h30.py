import argparse
import json
import time

import numpy as np
import pandas as pd

from audit import h22_ulang as au
from backend.db import data as dt
from backend.research import uji_h21_h22 as m

SINYAL_AWAL = {"dev": "2014-01-01"}
BULAN = 36
DES_MULAI = pd.Timestamp("2019-12-01")
SENS = [("dasar", {}), ("S1 biaya 2 tick", {"tick": 2}), ("S2 likuiditas ≥ Rp20 M", {"min_nilai": 20e9}), ("S3 harga ≥ Rp200", {"min_harga": 200})]


def lolos_rm(S, t):
    if S["periode"] == "holdout" and t < DES_MULAI:
        return m.lolos(dict(S, periode="dev"), t, 5e9, 100)
    return m.lolos(S, t, 5e9, 100)


def panel(S):
    if "h30_panel" in S:
        return S["h30_panel"]
    ab = S["akhir_bulan"]
    C = S["P"]["c_nilai"].loc[ab.values]
    C.index = ab.index
    sebelum = C.shift(1)
    R_m = (C / sebelum - 1).where(sebelum > 0)
    R = R_m.where((C > 0) & (sebelum > 0))
    rm = pd.Series(np.nan, index=ab.index)
    for i in range(1, len(ab)):
        calon = list(lolos_rm(S, ab.iloc[i - 1]))
        if calon:
            rm.iloc[i] = R_m.iloc[i][calon].mean()
    rf_asli = au.rf_bulanan()
    rf = rf_asli.reindex(pd.period_range(rf_asli.index.min(), ab.index.max(), freq="M")).ffill().reindex(ab.index)
    S["h30_panel"] = {"C": C, "R": R, "rm": rm, "rf": rf, "idx": ab.index}
    return S["h30_panel"]


def skor(S, t):
    cache = S.setdefault("h30_skor", {})
    if t in cache:
        return cache[t]
    pn = panel(S)
    i = pn["idx"].get_loc(t.to_period("M"))
    kosong = pd.Series(dtype=float)
    if i < BULAN:
        cache[t] = kosong
        return kosong
    jendela = pn["idx"][i - BULAN + 1:i + 1]
    rf = pn["rf"].loc[jendela]
    x = pn["rm"].loc[jendela] - rf
    if x.isna().any() or rf.isna().any():
        cache[t] = kosong
        return kosong
    C = pn["C"].iloc[i - BULAN:i + 1]
    ok = (C > 0).all()
    Y = pn["R"].loc[jendela, ok[ok].index].sub(rf, axis=0)
    Y = Y.loc[:, Y.notna().all()]
    if Y.shape[1] == 0:
        cache[t] = kosong
        return kosong
    X = np.column_stack([np.ones(BULAN), x.to_numpy()])
    B = np.linalg.lstsq(X, Y.to_numpy(), rcond=None)[0]
    E = Y.to_numpy() - X @ B
    e = E[BULAN - 12:BULAN - 1]
    sd = e.std(axis=0, ddof=1)
    s = pd.Series(np.where(sd > 0, e.sum(axis=0) / np.where(sd > 0, sd, 1), np.nan), index=Y.columns).dropna()
    cache[t] = s
    return s


def susun(periode):
    S = m.susun(periode)
    S["cfg"] = dict(S["cfg"], sinyal_awal=SINYAL_AWAL[periode])
    return S


def kontribusi(pos):
    per = pos.groupby("ticker")["pnl"].sum().sort_values(ascending=False)
    tot = pos["pnl"].sum()
    return {"top5": [(k, round(float(v) * 100, 1)) for k, v in per.head(5).items()],
            "top10": [(k, round(float(v) * 100, 1)) for k, v in per.head(10).items()],
            "porsi_top5": round(float(per.head(5).sum() / tot * 100), 1) if tot > 0 else None,
            "porsi_top10": round(float(per.head(10).sum() / tot * 100), 1) if tot > 0 else None,
            "laba_total": round(float(tot) * 100, 1), "posisi": len(pos), "saham": int(pos["ticker"].nunique())}


def satu(S, jenis, rj, kj, min_nilai=5e9, min_harga=100, tick=1):
    P = S["P"]
    h = au.h22_log(S, min_nilai, min_harga, tick, jenis=jenis)
    e = au.ew(P["o"], P["c_nilai"], lambda t: list(m.lolos(S, t, min_nilai, min_harga)), m.jadwal(S), S["tgl"][-1])
    ks = au.uji_konsentrasi(h, None)
    kb = au.uji_konsentrasi(e, None)
    f = lambda v: round(float(v), 2)
    krit = [
        ("a1 CAGR > bobot sama", f"{f(ks['CAGR'])}% vs {f(kb['CAGR'])}%", ks["CAGR"] > kb["CAGR"]),
        ("a2 CAGR > JII (+ dividen 2,5%/th)", f"{f(ks['CAGR'])}% vs {f(kj['CAGR'])}%", ks["CAGR"] > kj["CAGR"]),
        ("b1 tanpa 5 saham terbesar > bobot sama tanpa 5", f"{f(ks['-5 saham (kas)'])}% vs {f(kb['-5 saham (kas)'])}%", ks["-5 saham (kas)"] > kb["-5 saham (kas)"]),
        ("b2 tanpa 10 saham terbesar > bobot sama tanpa 10", f"{f(ks['-10 saham (kas)'])}% vs {f(kb['-10 saham (kas)'])}%", ks["-10 saham (kas)"] > kb["-10 saham (kas)"]),
        ("b3 tanpa tahun terbaik > bobot sama & JII tanpa tahun terbaik",
         f"{f(ks['-tahun terbaik'])}% ({ks['tahun terbaik']}) vs bobot sama {f(kb['-tahun terbaik'])}% ({kb['tahun terbaik']}), JII {f(kj['-tahun terbaik'])}% ({kj['tahun terbaik']})",
         ks["-tahun terbaik"] > kb["-tahun terbaik"] and ks["-tahun terbaik"] > kj["-tahun terbaik"]),
    ]
    return h, e, ks, kb, krit


def info(S, jenis, h, rf):
    sim = m.simulasi(S, jenis)
    eq = sim["ekuitas"]
    selisih = float((eq - h["eq"].reindex(eq.index)).abs().max())
    tahun = (eq.index[-1] - eq.index[0]).days / 365.25
    return sim, {"cek_log_vs_simulasi": selisih, "mulai": str(sim["mulai"].date()), "akhir": str(eq.index[-1].date()),
                 "cagr_harian": round(m.cagr(eq), 2), "dd_harian": round(m.max_dd(eq), 2), "vol": round(m.vol_tahunan(eq), 2),
                 "sharpe": round(float(au.sharpe(h["r"], rf)), 2),
                 "turnover_th": round(sim["dagang"] / 2 / eq.mean() / tahun * 100, 1), "kas_rata": round(sim["kas"].mean() * 100, 1),
                 "n_rata": round(sim["rekap"]["n"].mean(), 1), "lolos_rata": round(sim["rekap"]["lolos"].mean(), 1),
                 "rebalance": len(sim["rekap"]), "korelasi_follow_tren": m.korelasi_follow_tren(eq, "h11a_dev"),
                 "kontribusi": kontribusi(h["pos"])}


def per_tahun(r):
    return ((1 + r).groupby(r.index.year).prod() - 1) * 100


def jalankan(periode):
    t0 = time.time()
    S = susun(periode)
    rf = au.rf_bulanan()
    jadwal = m.jadwal(S)
    print(f"H30 {periode}: {len(S['kode'])} kode, sinyal pertama {jadwal[0][0].date()} eksekusi {jadwal[0][1].date()}, sinyal terakhir {jadwal[-1][0].date()}, {len(jadwal)} rebalance", flush=True)
    jml = []
    for t, _ in jadwal:
        calon = list(m.lolos(S, t, 5e9, 100))
        jml.append((len(calon), len(skor(S, t).reindex(calon).dropna())))
    jml = pd.DataFrame(jml, columns=["lolos", "diranking"])
    print(f"  saham lolos rata-rata {jml['lolos'].mean():.1f}, bisa diranking {jml['diranking'].mean():.1f} (min {jml['diranking'].min()}, maks {jml['diranking'].max()}) ({time.time() - t0:.0f} dtk)", flush=True)
    mulai = jadwal[0][1]
    jii = m.pembanding_jii(S, mulai)
    rj = m.bulanan(jii.loc[mulai:])
    cj, thj, vj = au.tanpa_tahun_terbaik(rj)
    kj = {"CAGR": au.cagr_bln(rj), "DD": au.dd_bln(rj), "-tahun terbaik": cj, "tahun terbaik": f"{thj} ({vj:+.0f}%)"}
    hasil = {"periode": periode, "jumlah_saham": {"lolos_rata": round(jml["lolos"].mean(), 1), "diranking_rata": round(jml["diranking"].mean(), 1),
                                                   "diranking_min": int(jml["diranking"].min()), "diranking_maks": int(jml["diranking"].max())},
             "jii": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in kj.items()}}
    seri = {}
    for jenis in ["h30", "h22"]:
        out = {"skenario": {}}
        for nama, ps in SENS:
            h, e, ks, kb, krit = satu(S, jenis, rj, kj, **ps)
            out["skenario"][nama] = {"kriteria": [(a, v, bool(o)) for a, v, o in krit], "lulus": all(o for _, _, o in krit),
                                    "strategi": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in ks.items()},
                                    "bobot_sama": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in kb.items()}}
            if nama == "dasar":
                sim, inf = info(S, jenis, h, rf)
                out["info"] = inf
                out["per_tahun"] = pd.DataFrame({"strategi": per_tahun(h["r"]), "bobot_sama": per_tahun(e["r"]), "jii": per_tahun(rj)}).round(1).reset_index().rename(columns={"index": "tahun"}).to_dict("records")
                out["kontribusi_bobot_sama"] = kontribusi(e["pos"])
                seri[jenis] = h
            print(f"  {jenis} {nama} selesai ({time.time() - t0:.0f} dtk)", flush=True)
        out["lulus_semua"] = all(v["lulus"] for v in out["skenario"].values())
        hasil[jenis] = out
    j = pd.concat([seri["h30"]["r"].rename("a"), seri["h22"]["r"].rename("b")], axis=1, join="inner").dropna()
    irisan = [len(seri["h30"]["isi"].get(b, set()) & seri["h22"]["isi"].get(b, set())) / len(seri["h30"]["isi"][b])
              for b in j.index if seri["h30"]["isi"].get(b)]
    hasil["h30_vs_h22"] = {"korelasi_bulanan": round(float(j["a"].corr(j["b"])), 2), "irisan_pegangan_pct": round(float(np.mean(irisan)) * 100, 1)}
    hasil["lulus_dev"] = hasil["h30"]["lulus_semua"]
    hasil = json.loads(json.dumps(hasil, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    dt.simpan_hasil(f"h30_{periode}", hasil)
    print(json.dumps(hasil, ensure_ascii=False, indent=1))
    print(f"SELESAI {time.time() - t0:.0f} dtk", flush=True)
    return hasil


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev"], default="dev")
    a = ap.parse_args()
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
