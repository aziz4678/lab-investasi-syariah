import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi
from backend.research import screener as sc

MULAI = pd.Timestamp("2020-01-01")
AKHIR_DEV = pd.Timestamp("2023-12-31")
DATA_SAMPAI = pd.Timestamp("2024-01-02")
AKHIR_HOLDOUT = pd.Timestamp("2026-10-31")
PERIODE = {
    "dev": {"akhir": AKHIR_DEV, "dari": MULAI, "sampai": DATA_SAMPAI, "mulai_sim": pd.Timestamp("2020-01-02")},
    "holdout": {"akhir": AKHIR_HOLDOUT, "dari": pd.Timestamp("2024-01-01"), "sampai": None, "mulai_sim": pd.Timestamp("2024-01-01")},
    "uji_kode": {"akhir": AKHIR_DEV, "dari": pd.Timestamp("2022-01-01"), "sampai": DATA_SAMPAI, "mulai_sim": pd.Timestamp("2022-01-03")},
}
KELUAR_SATUAN = frozenset("ANJT CUAN DEWA ESTI KOBX MBSS RIGS SGER SMMT TUGU".split())
POSISI = 10
BOBOT = 0.10
TAHAN = 60
PERSENTIL = 80
KOLAM_MIN = 100
HIST_MIN, HIST_MAKS = 4, 8
LIKUID, HARGA_MIN = 5e9, 50
FEE_BELI, FEE_JUAL = 0.0015, 0.0025
PAJAK_DIV = 0.10
DIV_JII = 0.025
BIAYA_EW = 0.006
MODAL = 1e8
URUT = {"TW1": 0, "TW2": 1, "TW3": 2, "AUDIT": 3}
PENANDA = koneksi.penanda("holdout_disegel_h36")
PENANDA_BUKA = koneksi.penanda("holdout_dibuka_h36")
KOLOM = ["open", "high", "low", "close", "volume", "close_mentah", "faktor", "tanpa_transaksi", "beku", "dividen"]


def baca_event(akhir=AKHIR_DEV):
    f = koneksi.baca_df("fundamental")
    l = koneksi.baca_df("lapkeu", kolom=["kode", "tahun", "periode", "tgl_publikasi"]).rename(columns={"tgl_publikasi": "tgl_l"})
    l["tgl_l"] = pd.to_datetime(l["tgl_l"])
    l = l.sort_values("tgl_l").drop_duplicates(["kode", "tahun", "periode"])
    f = f.merge(l, on=["kode", "tahun", "periode"], how="left")
    f["tgl_f"] = pd.to_datetime(f["tgl_publikasi"])
    f["tgl"] = f["tgl_l"].fillna(f["tgl_f"])
    f["sumber_tgl"] = np.where(f["tgl_l"].notna(), "lapkeu", np.where(f["tgl_f"].notna(), "fundamental", "kosong"))
    f["n"] = f["periode"].map(URUT)
    f["q"] = f["tahun"] * 4 + f["n"]
    f = f[f["n"].notna() & f["tahun"].between(2019, akhir.year)]
    f = f[~(f["tgl"] > akhir)]
    f["valid"] = f["ada_angka"].astype(bool) & f["laba"].notna() & f["laba_lalu"].notna()
    return f


def kode_desember(kode):
    d = dt.baca("keuangan_idx", kolom=["kode", "fye"])
    d["fye"] = d["fye"].astype(str).str.strip().str.lower()
    d = d[~d["fye"].isin(["-", "", "nan", "none"])]
    bukan = set(d[d["fye"] != "dec"]["kode"])
    ada = set(d["kode"])
    return bukan, set(kode) - ada


def hitung_sue(f, bukan_des):
    f = f[~f["kode"].isin(KELUAR_SATUAN) & ~f["kode"].isin(bukan_des)].copy()
    ytd = {}
    for r in f[f["valid"]].itertuples():
        ytd[(r.kode, r.tahun, r.n)] = (r.laba, r.laba_lalu)
    S = {}
    for (k, th, n), (a, b) in ytd.items():
        if n == 0:
            S[(k, th * 4)] = a - b
        elif (k, th, n - 1) in ytd:
            p = ytd[(k, th, n - 1)]
            S[(k, th * 4 + n)] = (a - p[0]) - (b - p[1])
    sue, alasan, jml_hist = [], [], []
    for r in f.itertuples():
        if pd.isna(r.tgl):
            sue.append(np.nan)
            alasan.append("tanpa_tgl_publikasi")
            jml_hist.append(0)
            continue
        if not r.valid or (r.n > 0 and (r.kode, r.tahun, r.n - 1) not in ytd):
            sue.append(np.nan)
            alasan.append("ytd_hilang")
            jml_hist.append(0)
            continue
        h = [S[(r.kode, r.q - j)] for j in range(1, HIST_MAKS + 1) if (r.kode, r.q - j) in S]
        jml_hist.append(len(h))
        if len(h) < HIST_MIN:
            sue.append(np.nan)
            alasan.append("histori_kurang")
            continue
        sd = float(np.std(h, ddof=1))
        if not sd > 0:
            sue.append(np.nan)
            alasan.append("stdev_nol")
            continue
        sue.append(S[(r.kode, r.q)] / sd)
        alasan.append("")
    f["S"] = [S.get((r.kode, r.q), np.nan) if r.valid else np.nan for r in f.itertuples()]
    f["sue"] = sue
    f["alasan"] = alasan
    f["hist"] = jml_hist
    d = f[f["sue"].notna()].sort_values("tgl")
    tgl = d["tgl"].values
    nilai = d["sue"].values
    pct = {}
    kolam = {}
    for i, r in enumerate(d.itertuples()):
        hi = np.searchsorted(tgl, np.datetime64(r.tgl), side="left")
        lo = np.searchsorted(tgl, np.datetime64(r.tgl - pd.Timedelta(days=365)), side="left")
        n = hi - lo
        kolam[r.Index] = n
        pct[r.Index] = float(np.mean(nilai[lo:hi] <= r.sue) * 100) if n >= KOLAM_MIN else np.nan
    f["kolam"] = pd.Series(kolam)
    f["pct"] = pd.Series(pct)
    f.loc[f["sue"].notna() & f["pct"].isna(), "alasan"] = "kolam_kecil"
    return f


class Harga:
    def __init__(self, sampai=DATA_SAMPAI, mulai_sim=None):
        raw = hg.bersih_banyak(kolom=KOLOM)
        raw = {k: v[(v.index >= MULAI) & ((v.index <= sampai) if sampai is not None else True)] for k, v in raw.items()}
        raw = {k: v for k, v in raw.items() if len(v)}
        self.kode = sorted(raw)
        self.ki = {k: i for i, k in enumerate(self.kode)}
        self.T = pd.DatetimeIndex(sorted(set().union(*[set(v.index) for v in raw.values()])))
        self.n = len(self.T)
        self.i0 = 0 if mulai_sim is None else int(np.searchsorted(self.T.values, np.datetime64(mulai_sim), side="left"))

        def lebar(kol, isi=None):
            x = pd.DataFrame({k: raw[k][kol] for k in self.kode}).reindex(self.T)
            return x.astype(float) if isi is None else x.fillna(isi).astype(float)

        self.O = lebar("open").values
        self.C = lebar("close").values
        self.CM = lebar("close_mentah").values
        self.F = lebar("faktor").values
        self.D = lebar("dividen", 0.0).values
        self.TT = pd.DataFrame({k: raw[k]["tanpa_transaksi"] for k in self.kode}).reindex(self.T).fillna(True).astype(bool).values
        self.BK = pd.DataFrame({k: raw[k]["beku"] for k in self.kode}).reindex(self.T).fillna(False).astype(bool).values
        self.ada = ~np.isnan(self.C)
        self.Cf = pd.DataFrame(self.C).ffill().values
        self.terakhir = {k: raw[k].index[-1] for k in self.kode}
        self.delisting = {k for k, t in self.terakhir.items() if t < self.T[-1]}
        pasar = pd.DataFrame({"ihsg_atas": 0.0, "ihsg_mom20": 0.0}, index=self.T)
        vm, atr, vn = {}, {}, {}
        for k in self.kode:
            v = raw[k]
            x = sc.fitur_ticker(v[["open", "high", "low", "close", "volume", "close_mentah"]], pasar.reindex(v.index))
            vm[k] = x["value_mentah"]
            atr[k] = x["atr_pct"]
            vn[k] = (v["volume"] == 0).rolling(5).sum()
        self.VM = pd.DataFrame(vm).reindex(self.T).values
        self.ATR = pd.DataFrame(atr).reindex(self.T).values
        self.VN = pd.DataFrame(vn).reindex(self.T).values
        self.des = {}
        for d in koneksi.koneksi()["des"].find({}, {"kode": 1, "mulai": 1, "akhir": 1}):
            self.des.setdefault(d["kode"], []).append((pd.Timestamp(d["mulai"]), pd.Timestamp(d["akhir"])))
        bulan = pd.Series(self.T, index=self.T).groupby(self.T.to_period("M"))
        self.awal_bulan = set(bulan.first())
        j = hg.indeks("indeks/JKII")
        j = j["close"] if isinstance(j, pd.DataFrame) else j
        j.index = pd.to_datetime(j.index)
        self.jii = j.sort_index()
        self._lolos = {}

    def di_des(self, k, t):
        return any(a <= t <= b for a, b in self.des.get(k, []))

    def lolos(self, likuid, hmin):
        kunci = (likuid, hmin)
        if kunci not in self._lolos:
            m = (self.VM >= likuid) & (self.ATR >= sc.ATR_MIN) & (self.ATR <= sc.ATR_MAKS) & (self.CM >= hmin) & (self.VN == 0) & self.ada & ~self.BK
            self._lolos[kunci] = m
        return self._lolos[kunci]


def tick(harga):
    return float(sc.fraksi(harga))


def sinyal_siap(P, f, persentil, likuid, hmin, ear=None, dari=MULAI):
    L = P.lolos(likuid, hmin)
    baris = []
    alasan = {}
    d = f[f["pct"].notna() & (f["pct"] >= persentil) & (f["tgl"] >= dari)]
    for r in d.itertuples():
        if r.kode not in P.ki:
            alasan["tanpa_harga"] = alasan.get("tanpa_harga", 0) + 1
            continue
        c = P.ki[r.kode]
        pos = int(np.searchsorted(P.T.values, np.datetime64(r.tgl), side="right"))
        j, e = pos - 1, pos + 1
        if j < 0 or e >= P.n - 1:
            alasan["di_luar_batas_data"] = alasan.get("di_luar_batas_data", 0) + 1
            continue
        if not P.di_des(r.kode, r.tgl):
            alasan["bukan_syariah_des"] = alasan.get("bukan_syariah_des", 0) + 1
            continue
        if not L[j, c]:
            alasan["tidak_lolos_likuiditas_h11a"] = alasan.get("tidak_lolos_likuiditas_h11a", 0) + 1
            continue
        if ear is not None and not (ear.get((r.kode, r.q), np.nan) > 0):
            alasan["ear_tidak_positif"] = alasan.get("ear_tidak_positif", 0) + 1
            continue
        baris.append((r.kode, e, r.sue, r.tgl, r.q))
    s = pd.DataFrame(baris, columns=["kode", "e", "sue", "tgl", "q"])
    return s, alasan


def strategi(P, sinyal, tahan=TAHAN, n_tick=1, buang=frozenset()):
    sinyal = sinyal[~sinyal["kode"].isin(buang)]
    per_hari = {}
    for r in sinyal.itertuples():
        per_hari.setdefault(r.e, []).append(r)
    kas = MODAL
    pegang = {}
    ekuitas = np.zeros(P.n)
    trades = []
    laba = {}
    hit = {"slot_penuh": 0, "sudah_dipegang": 0, "tak_bisa_beli": 0, "kas_kurang": 0, "dibeli": 0, "delisting_nol": 0}
    sinyal_hari = {}

    def jual(i, k, paksa=False):
        nonlocal kas
        c = P.ki[k]
        if not P.ada[i, c] or P.TT[i, c] or not (P.O[i, c] > 0):
            return False
        h = pegang[k]
        f = P.F[i, c]
        o_raw = P.O[i, c] / f
        harga_raw = max(o_raw - tick(o_raw) * n_tick, 1.0)
        hasil = h["lembar"] * f * harga_raw * (1 - FEE_JUAL)
        kas += hasil
        total = hasil + h["div"]
        trades.append({"kode": k, "tgl_beli": P.T[h["i"]], "tgl_jual": P.T[i], "net": (total / h["biaya"] - 1) * 100, "rp": total - h["biaya"], "q": h["q"], "sue": h["sue"]})
        laba[k] = laba.get(k, 0.0) + total - h["biaya"]
        del pegang[k]
        return True

    for i in range(P.i0, P.n):
        t = P.T[i]
        for k in list(pegang):
            if k in P.delisting and t > P.terakhir[k]:
                h = pegang[k]
                trades.append({"kode": k, "tgl_beli": P.T[h["i"]], "tgl_jual": t, "net": (h["div"] / h["biaya"] - 1) * 100, "rp": h["div"] - h["biaya"], "q": h["q"], "sue": h["sue"]})
                laba[k] = laba.get(k, 0.0) + h["div"] - h["biaya"]
                hit["delisting_nol"] += 1
                del pegang[k]
        for k, h in pegang.items():
            dv = P.D[i, P.ki[k]]
            if dv > 0:
                u = h["lembar"] * dv * (1 - PAJAK_DIV)
                kas += u
                h["div"] += u
        akhir = i == P.n - 1
        for k in sorted(pegang, key=lambda z: pegang[z]["i"]):
            if akhir or i >= pegang[k]["i"] + tahan:
                if not jual(i, k) and akhir:
                    h = pegang[k]
                    val = h["lembar"] * P.Cf[i, P.ki[k]]
                    kas += val
                    h["div"] += val
                    trades.append({"kode": k, "tgl_beli": P.T[h["i"]], "tgl_jual": t, "net": (h["div"] / h["biaya"] - 1) * 100, "rp": h["div"] - h["biaya"], "q": h["q"], "sue": h["sue"]})
                    laba[k] = laba.get(k, 0.0) + h["div"] - h["biaya"]
                    del pegang[k]
        if not akhir and i in per_hari:
            eq_kemarin = ekuitas[i - 1] if i > P.i0 else MODAL
            for r in sorted(per_hari[i], key=lambda z: -z.sue):
                k = r.kode
                c = P.ki[k]
                if k in pegang:
                    hit["sudah_dipegang"] += 1
                    continue
                if len(pegang) >= POSISI:
                    hit["slot_penuh"] += 1
                    continue
                if not P.ada[i, c] or P.TT[i, c] or not (P.O[i, c] > 0):
                    hit["tak_bisa_beli"] += 1
                    continue
                uang = min(BOBOT * eq_kemarin, kas)
                if uang < 0.01 * eq_kemarin:
                    hit["kas_kurang"] += 1
                    continue
                f = P.F[i, c]
                o_raw = P.O[i, c] / f
                harga_raw = o_raw + tick(o_raw) * n_tick
                lembar = uang / (harga_raw * (1 + FEE_BELI)) / f
                kas -= uang
                pegang[k] = {"lembar": lembar, "biaya": uang, "i": i, "div": 0.0, "q": r.q, "sue": r.sue}
                hit["dibeli"] += 1
                sinyal_hari[i] = sinyal_hari.get(i, 0) + 1
        ekuitas[i] = kas + sum(h["lembar"] * P.Cf[i, P.ki[k]] for k, h in pegang.items())
    return {"eq": ekuitas, "trades": pd.DataFrame(trades), "laba": laba, "hit": hit}


def bobot_sama(P, likuid=LIKUID, hmin=HARGA_MIN, buang=frozenset(), biaya=False):
    L = P.lolos(likuid, hmin)
    w = {}
    kas = MODAL
    ekuitas = np.zeros(P.n)
    laba = {}
    for i in range(P.i0, P.n):
        t = P.T[i]
        if i > 0:
            for k in list(w):
                c = P.ki[k]
                if P.ada[i, c] and P.ada[i - 1, c] and P.C[i - 1, c] > 0:
                    lama = w[k]
                    w[k] = lama * (P.C[i, c] + P.D[i, c]) / P.C[i - 1, c]
                    laba[k] = laba.get(k, 0.0) + w[k] - lama
                elif not P.ada[i, c] and k in P.delisting and t > P.terakhir[k]:
                    laba[k] = laba.get(k, 0.0) - w[k]
                    del w[k]
        if t in P.awal_bulan and i > 0:
            jml = sum(w.values()) + kas
            uni = [k for k in P.kode if k not in buang and L[i - 1, P.ki[k]] and P.di_des(k, t)]
            if uni:
                baru = {k: jml / len(uni) for k in uni}
                if biaya:
                    jml -= BIAYA_EW * sum(abs(baru.get(k, 0.0) - w.get(k, 0.0)) for k in set(baru) | set(w))
                    baru = {k: jml / len(uni) for k in uni}
                w, kas = baru, 0.0
            else:
                w, kas = {}, jml
        ekuitas[i] = sum(w.values()) + kas
    return {"eq": ekuitas, "laba": laba}


def jii_total(P):
    lv = P.jii.reindex(P.T).ffill()
    hari = np.array([(P.T[i] - P.T[i - 1]).days if i > P.i0 else 0 for i in range(P.n)])
    return {"eq": MODAL * lv.values / lv.values[P.i0] * np.cumprod((1 + DIV_JII) ** (hari / 365.25))}


def metrik(P, hasil):
    e = hasil["eq"][P.i0:]
    T = P.T[P.i0:]
    hari = (T[-1] - T[0]).days
    cagr = (e[-1] / MODAL) ** (365.25 / hari) - 1
    dd = float(np.min(e / np.maximum.accumulate(e) - 1))
    r = pd.Series(e, index=T).pct_change().fillna(0.0)
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
    twr = (1 + r).groupby(T.year).prod() - 1
    twr = twr[pd.Series(1, index=T).groupby(T.year).sum() >= 20]
    return {"cagr": float(cagr), "dd": dd, "sharpe": sharpe, "twr": twr}


def tanpa_terbaik(twr):
    sisa = twr.drop(twr.idxmax())
    return float((1 + sisa).prod() ** (1 / len(sisa)) - 1)


def seragam(P, f, jii_m, cache_ew, cfg):
    s, _ = sinyal_siap(P, f, cfg["pct"], cfg["likuid"], cfg["hmin"], dari=cfg["dari"])
    h = strategi(P, s, cfg["tahan"], cfg["ntick"])
    mh = metrik(P, h)
    kunci = (cfg["likuid"], cfg["hmin"])
    ew = cache_ew(kunci, frozenset())
    me = metrik(P, ew)
    top_h = sorted(h["laba"], key=lambda k: -h["laba"][k])
    top_e = sorted(ew["laba"], key=lambda k: -ew["laba"][k])
    out = {"cagr": mh["cagr"], "dd": mh["dd"], "ew": me["cagr"], "jii": jii_m["cagr"], "trade": int(len(h["trades"])), "buang5": top_h[:5], "buang10": top_h[:10]}
    k = {"1_vs_ew": mh["cagr"] > me["cagr"], "2_vs_jii": mh["cagr"] > jii_m["cagr"]}
    for m in (5, 10):
        hm = metrik(P, strategi(P, s, cfg["tahan"], cfg["ntick"], frozenset(top_h[:m])))
        em = metrik(P, cache_ew(kunci, frozenset(top_e[:m])))
        out[f"tanpa{m}"] = (hm["cagr"], em["cagr"])
        k[("3" if m == 5 else "4") + f"_tanpa{m}"] = hm["cagr"] > em["cagr"]
    a, b, c = tanpa_terbaik(mh["twr"]), tanpa_terbaik(me["twr"]), tanpa_terbaik(jii_m["twr"])
    out["tanpa_tahun"] = (a, b, c)
    k["5_tanpa_tahun"] = bool(a > b and a > c)
    out["kriteria"] = {x: bool(v) for x, v in k.items()}
    out["lulus"] = all(k.values())
    return out, h, mh, s


def ear_event(P, f, likuid=LIKUID, hmin=HARGA_MIN, dari=MULAI):
    L = P.lolos(likuid, hmin)
    d = f[f["pct"].notna() & (f["pct"] >= PERSENTIL) & (f["tgl"] >= dari)]
    hasil = {}
    for r in d.itertuples():
        if r.kode not in P.ki:
            continue
        pos = int(np.searchsorted(P.T.values, np.datetime64(r.tgl), side="right"))
        j = pos - 1
        if j < 2 or pos >= P.n:
            continue
        c = P.ki[r.kode]
        a, b = P.C[pos, c], P.C[pos - 3, c]
        if not (a > 0 and b > 0):
            continue
        uni = [P.ki[k] for k in P.kode if L[j, P.ki[k]] and P.di_des(k, r.tgl)]
        ra = P.C[pos, uni] / P.C[pos - 3, uni] - 1
        ra = ra[np.isfinite(ra)]
        if len(ra) < 5:
            continue
        hasil[(r.kode, r.q)] = a / b - 1 - float(np.mean(ra))
    return hasil


def tingkat_event(P, s, tahan=TAHAN, likuid=LIKUID, hmin=HARGA_MIN, n_tick=1):
    L = P.lolos(likuid, hmin)
    baris = []
    for r in s.itertuples():
        i, x = r.e, r.e + tahan
        c = P.ki[r.kode]
        if x >= P.n or not (P.O[i, c] > 0 and P.O[x, c] > 0) or P.TT[i, c]:
            continue
        j = i - 2
        uni = [P.ki[k] for k in P.kode if L[j, P.ki[k]] and P.di_des(k, r.tgl)]
        ro = P.O[x, uni] / P.O[i, uni] - 1
        ro = ro[np.isfinite(ro)]
        if len(ro) < 5:
            continue
        oe, ox = P.O[i, c] / P.F[i, c], P.O[x, c] / P.F[x, c]
        beli = (1 + tick(oe) * n_tick / oe) * (1 + FEE_BELI)
        jual = (1 - tick(ox) * n_tick / ox) * (1 - FEE_JUAL)
        net = (P.O[x, c] / P.O[i, c]) * jual / beli - 1
        baris.append({"q": r.tgl.to_period("Q"), "net": net, "uni": float(np.mean(ro)), "exc": net - float(np.mean(ro))})
    d = pd.DataFrame(baris)
    pq = d.groupby("q")[["net", "uni", "exc"]].mean()
    n = len(pq)
    t = stats.ttest_1samp(pq["exc"], 0.0) if n >= 3 else None
    return {"event": int(len(d)), "kuartal": int(n), "net": float(d["net"].mean()), "uni": float(d["uni"].mean()), "excess": float(d["exc"].mean()),
            "excess_per_kuartal": [round(float(v) * 100, 2) for v in pq["exc"]], "t": None if t is None else float(t.statistic), "p": None if t is None else float(t.pvalue),
            "kuartal_positif": int((pq["exc"] > 0).sum())}


def pc(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x) * 100, 2)


def batu_bara():
    return {d["kode"] for d in koneksi.koneksi()["profil_idx"].find({"industri": "Batu Bara"}, {"kode": 1})}


def utama(periode="dev", simpan=True):
    kf = PERIODE[periode]
    dari = kf["dari"]
    f0 = baca_event(kf["akhir"])
    bukan, tanpa_fye = kode_desember(f0["kode"].unique())
    f = hitung_sue(f0, bukan)
    dev = f[(f["tgl"] >= dari)]
    print(f"[{periode}] emiten dikeluarkan: ganti satuan {len(KELUAR_SATUAN & set(f0['kode']))} | non-Desember (fye) {len(bukan & set(f0['kode']))} | tanpa data fye {len(tanpa_fye)} (dipertahankan)", flush=True)
    tanpa = int((dev["alasan"] == "tanpa_tgl_publikasi").sum())
    print(f"event periode ({len(dev)}): tanpa tgl_publikasi {tanpa}, sumber tgl: {dev['sumber_tgl'].value_counts().to_dict()}", flush=True)
    per_q = dev[dev["tgl"].notna()].groupby(dev["tgl"].dt.to_period("Q")).size()
    print("event per kuartal publikasi:", " ".join(f"{str(k)[2:]}:{v}" for k, v in per_q.items()), flush=True)
    al = dev["alasan"].value_counts()
    tot = len(dev)
    print("dilewati: " + ", ".join(f"{k or 'sue_valid'} {v} ({v / tot * 100:.0f}%)" for k, v in al.items()), flush=True)
    print(f"valid SUE+pool>=100: {int(dev['pct'].notna().sum())}, sinyal pct>={PERSENTIL}: {int((dev['pct'] >= PERSENTIL).sum())}", flush=True)
    P = Harga(kf["sampai"], kf["mulai_sim"])
    print(f"harga: {len(P.kode)} kode, sim {P.T[P.i0].date()} s/d {P.T[-1].date()}, delisting {len(P.delisting)}", flush=True)
    jii_m = metrik(P, jii_total(P))
    cache = {}

    def cache_ew(kunci, buang, biaya=False):
        kk = (kunci, buang, biaya)
        if kk not in cache:
            cache[kk] = bobot_sama(P, kunci[0], kunci[1], buang, biaya)
        return cache[kk]

    dasar_cfg = {"pct": PERSENTIL, "tahan": TAHAN, "ntick": 1, "likuid": LIKUID, "hmin": HARGA_MIN, "dari": dari}
    varian = {"dasar": {}, "S1_2tick": {"ntick": 2}, "S2_rp20m": {"likuid": 20e9}, "S3_rp200": {"hmin": 200},
              "H36_tahan40": {"tahan": 40}, "H36_tahan90": {"tahan": 90}, "H36_pct70": {"pct": 70}, "H36_pct90": {"pct": 90}}
    hasil = {}
    pertama = None
    for nama, ubah in varian.items():
        cfg = {**dasar_cfg, **ubah}
        r, h, mh, s = seragam(P, f, jii_m, cache_ew, cfg)
        hasil[nama] = r
        if nama == "dasar":
            pertama = (r, h, mh, s)
        print(f"{nama}: CAGR {pc(r['cagr'])}% vs EW {pc(r['ew'])}% JII {pc(r['jii'])}% | tanpa5 {pc(r['tanpa5'][0])} vs {pc(r['tanpa5'][1])} | tanpa10 {pc(r['tanpa10'][0])} vs {pc(r['tanpa10'][1])} | {r['kriteria']}", flush=True)
    r, h, mh, s = pertama
    ew = cache_ew((LIKUID, HARGA_MIN), frozenset())
    me = metrik(P, ew)
    me_b = metrik(P, cache_ew((LIKUID, HARGA_MIN), frozenset(), True))
    tr = h["trades"]
    menang = float((tr["net"] > 0).mean() * 100)
    top = sorted(h["laba"].items(), key=lambda x: -x[1])
    total_laba = sum(h["laba"].values())
    lima = sum(v for _, v in top[:5])
    standar_ok = all(hasil[k]["lulus"] for k in ("dasar", "S1_2tick", "S2_rp20m", "S3_rp200"))
    daftar_ok = all(hasil[k]["lulus"] for k in ("H36_tahan40", "H36_tahan90", "H36_pct70", "H36_pct90"))
    sinyal_q = s.groupby(s["tgl"].dt.to_period("Q")).size()
    print("sinyal (setelah DES+likuiditas) per kuartal:", " ".join(f"{str(k)[2:]}:{v}" for k, v in sinyal_q.items()), flush=True)
    s_all, alasan_s = sinyal_siap(P, f, PERSENTIL, LIKUID, HARGA_MIN, dari=dari)
    print("sinyal dibuang:", alasan_s, "| eksekusi:", h["hit"], flush=True)
    event = tingkat_event(P, s)
    ear = ear_event(P, f, dari=dari)
    s_ear, _ = sinyal_siap(P, f, PERSENTIL, LIKUID, HARGA_MIN, ear, dari=dari)
    h_ear = strategi(P, s_ear)
    m_ear = metrik(P, h_ear)
    coal = batu_bara()
    s_tc = s[~s["kode"].isin(coal)]
    m_tc = metrik(P, strategi(P, s_tc))
    ew_tc = metrik(P, cache_ew((LIKUID, HARGA_MIN), frozenset(coal & set(P.kode))))
    syarat_2a = bool(event["excess"] > 0)
    syarat_2b = bool(m_tc["cagr"] >= ew_tc["cagr"])
    th = {k: {str(y): pc(v) for y, v in m["twr"].items()} for k, m in (("h36", mh), ("ew", me), ("jii", jii_m))}
    versi = hg.sidik(P.kode, mulai=MULAI, akhir=P.T[-1], koleksi="harga_bersih_2020", kolom=("open", "close", "dividen", "saham_tercatat"))
    lulus_standar = bool(standar_ok and daftar_ok)
    keluaran = {
        "dibuat": datetime.now().isoformat(timespec="seconds"), "periode": f"{periode}: tgl_publikasi {dari.date()} s/d {kf['akhir'].date()}, simulasi {P.T[P.i0].date()} s/d {P.T[-1].date()}",
        "lulus": lulus_standar, "standar_lulus": bool(standar_ok), "terdaftar_lulus": bool(daftar_ok),
        "interpretasi": {"kolam_peringkat": "semua event ber-SUE valid (semua emiten Desember) dengan tgl_publikasi < tgl event dalam 365 hari",
                         "persentil": "100 x proporsi SUE kolam <= SUE event", "tahan": "keluar di open indeks masuk + 60 hari bursa",
                         "ew": "kriteria memakai bobot sama tanpa biaya (standar seragam); EW berbiaya hanya laporan"},
        "pra_cek": {"event": int(len(dev)), "tanpa_tgl": tanpa, "alasan": {k or "sue_valid": int(v) for k, v in al.items()},
                    "per_kuartal": {str(k): int(v) for k, v in per_q.items()}, "sinyal_per_kuartal": {str(k): int(v) for k, v in sinyal_q.items()},
                    "dikeluarkan_satuan": sorted(KELUAR_SATUAN & set(f0["kode"])), "dikeluarkan_non_desember": sorted(bukan & set(f0["kode"])), "tanpa_fye": len(tanpa_fye),
                    "sinyal_dibuang": alasan_s, "eksekusi": h["hit"]},
        "portofolio": {"cagr": pc(mh["cagr"]), "dd": pc(mh["dd"]), "sharpe": round(mh["sharpe"], 2), "trade": int(len(tr)), "winrate": round(menang, 1), "net_per_trade": round(float(tr["net"].mean()), 2),
                       "ew": {"cagr": pc(me["cagr"]), "dd": pc(me["dd"]), "sharpe": round(me["sharpe"], 2)}, "ew_berbiaya": {"cagr": pc(me_b["cagr"]), "dd": pc(me_b["dd"])},
                       "jii": {"cagr": pc(jii_m["cagr"]), "dd": pc(jii_m["dd"]), "sharpe": round(jii_m["sharpe"], 2)}, "twr": th},
        "konsentrasi": {"top5": [[k, round(v)] for k, v in top[:5]], "porsi_top5": None if total_laba <= 0 else round(lima / total_laba * 100, 1), "laba_total": round(total_laba),
                        "tanpa5": [pc(r["tanpa5"][0]), pc(r["tanpa5"][1])], "tanpa10": [pc(r["tanpa10"][0]), pc(r["tanpa10"][1])]},
        "event_level": event, "varian": {k: {"cagr": pc(v["cagr"]), "dd": pc(v["dd"]), "ew": pc(v["ew"]), "jii": pc(v["jii"]), "trade": v["trade"], "tanpa5": [pc(v["tanpa5"][0]), pc(v["tanpa5"][1])],
                                           "tanpa10": [pc(v["tanpa10"][0]), pc(v["tanpa10"][1])], "tanpa_tahun": [pc(x) for x in v["tanpa_tahun"]], "kriteria": v["kriteria"], "lulus": v["lulus"]}
                                       for k, v in hasil.items()},
        "laporan_ear": {"label": "LAPORAN SAJA, tidak dipakai untuk keputusan", "cagr": pc(m_ear["cagr"]), "dd": pc(m_ear["dd"]), "sharpe": round(m_ear["sharpe"], 2), "trade": int(len(h_ear["trades"])),
                        "sinyal": int(len(s_ear)), "ear_dihitung": len(ear)},
        "syarat_uji_maju": {"2a_excess_event": {"excess": pc(event["excess"]), "lulus": syarat_2a},
                            "2b_tanpa_batu_bara": {"h36": pc(m_tc["cagr"]), "bobot_sama_tanpa_batu_bara": pc(ew_tc["cagr"]), "bobot_sama_penuh": pc(me["cagr"]), "lulus": syarat_2b,
                                                   "kode_batu_bara_di_data": len(coal & set(P.kode)), "sinyal_batu_bara_dibuang": int(len(s) - len(s_tc)), "dd_h36": pc(m_tc["dd"])}},
        "versi_data": {**versi, "keterbatasan": "survivorship ditutup 2020+ (harga_bersih_2020); syariah point-in-time DES; fundamental sejak 2019; event tanpa tanggal rilis dilewati; angka laporan terbaru (2026 Q3) bisa belum lengkap di fundamental"},
    }
    vonis = "LOLOS holdout -> Uji maju" if (lulus_standar and syarat_2a and syarat_2b) else "GAGAL"
    keluaran["vonis"] = vonis
    print(f"\n=== H36 {periode} ===", flush=True)
    ringkas = keluaran["portofolio"]
    print(f"H36 CAGR {ringkas['cagr']}% DD {ringkas['dd']}% Sharpe {ringkas['sharpe']} | trade {ringkas['trade']} win {ringkas['winrate']}% net/trade {ringkas['net_per_trade']}%")
    print(f"EW tanpa biaya CAGR {ringkas['ew']['cagr']}% DD {ringkas['ew']['dd']}% Sharpe {ringkas['ew']['sharpe']} | EW berbiaya {ringkas['ew_berbiaya']['cagr']}% | JII {ringkas['jii']['cagr']}% DD {ringkas['jii']['dd']}%")
    print("per tahun H36/EW/JII:", {y: (th["h36"].get(y), th["ew"].get(y), th["jii"].get(y)) for y in th["h36"]})
    print(f"top5: {keluaran['konsentrasi']['top5']} porsi {keluaran['konsentrasi']['porsi_top5']}% | tanpa5 {keluaran['konsentrasi']['tanpa5']} tanpa10 {keluaran['konsentrasi']['tanpa10']}")
    print(f"event-level 60h: n {event['event']}, net {pc(event['net'])}%, universe {pc(event['uni'])}%, excess {pc(event['excess'])}%, t {event['t']}, kuartal+ {event['kuartal_positif']}/{event['kuartal']}")
    print(f"syarat 2a {syarat_2a} | 2b {syarat_2b}: H36 tanpa batu bara {pc(m_tc['cagr'])}% vs bobot sama tanpa batu bara {pc(ew_tc['cagr'])}% (penuh {pc(me['cagr'])}%)")
    print(f"[tidak dipakai untuk keputusan] SUE>=80 + EAR>0: CAGR {keluaran['laporan_ear']['cagr']}% DD {keluaran['laporan_ear']['dd']}% trade {keluaran['laporan_ear']['trade']}")
    print(f"standar seragam (dasar+S1-S3): {'LULUS' if standar_ok else 'GAGAL'} | terdaftar H36: {'LULUS' if daftar_ok else 'GAGAL'}")
    print(f"VONIS: {vonis}")
    if simpan and periode == "dev":
        dt.simpan_hasil("h36_dev", json.loads(json.dumps(keluaran, default=str)))
    if simpan and periode == "holdout":
        lama = dt.baca_hasil("h36_holdout") or {}
        lama.update(json.loads(json.dumps(keluaran, default=str)))
        dt.simpan_hasil("h36_holdout", lama)
    print("SELESAI")
    return keluaran


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "dev":
        utama("dev")
    elif arg == "uji_kode":
        utama("uji_kode", simpan=False)
    elif arg == "holdout":
        if PENANDA_BUKA.exists():
            raise SystemExit(f"holdout H36 sudah dibuka ({PENANDA_BUKA.read_text().strip()})")
        PENANDA_BUKA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
        PENANDA.write_text(f"dibuka {datetime.now():%Y-%m-%d %H:%M} atas konfirmasi user (disegel 2026-11-12)\n")
        utama("holdout")
    else:
        raise SystemExit("pakai: dev | uji_kode | holdout")
