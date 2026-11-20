import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi
from backend.research import screener as sc
from backend.research import uji_h36 as h36

MODAL = h36.MODAL
AKHIR_DEV = pd.Timestamp("2023-12-31")
SAMPAI_DEV = pd.Timestamp("2024-01-02")
AKHIR_HOLDOUT = pd.Timestamp("2026-10-31")
WARM = 220
LIKUID, HARGA_MIN = 5e9, 50
BASE_MIN, BASE_MAKS, BASE_RANGE = 25, 60, 0.25
RS_HARI, RS_PCT, RS_MIN_N = 126, 0.8, 20
VOL_X, VOL_HARI = 1.5, 50
KEJAR = 1.05
STOP_HARI, STOP_MAKS = 10, 0.08
TAHAN = 60
RISIKO, SLOT = 0.01, 5
SLIP = 0.002
LOT = 100
FEE_BELI, FEE_JUAL, PAJAK_DIV = h36.FEE_BELI, h36.FEE_JUAL, h36.PAJAK_DIV
H11_POSISI, H11_BOBOT, H11_ATR, H11_HARI, H11_SEED = 10, 0.10, 3.0, 500, (1, 2, 3, 4, 5)
PENANDA_BUKA = koneksi.penanda("holdout_dibuka_h40")
ATURAN = {
    "regime": "JII close > MA200 JII", "stage2": "close > MA20 > MA50 > MA100 > MA200 dan MA200 > MA200 20 hari lalu",
    "rs": "return 126 hari persentil >= 80 di universe syariah likuid hari itu (min 20 saham)",
    "base": "jendela 25-60 hari bursa sebelum hari sinyal, (high-low)/high <= 25%, jendela terpanjang yang valid",
    "trigger": "close > base_high dan volume >= 1,5x rata-rata 50 hari sebelum hari sinyal",
    "entry": "open besok, skip bila open > base_high x 1,05", "stop": "low terendah 10 hari sebelum sinyal, skip bila jarak > 8%",
    "exit": "close < MA20 -> jual open besok; stop kena -> min(stop, open); maks 60 hari bursa (jual open)",
    "sizing": "risiko 1% ekuitas close kemarin / (entry - stop), lot 100, maks 5 posisi, dibatasi kas, prioritas RS tertinggi",
    "biaya": "fee 0,15% beli + 0,25% jual + 1 tick per sisi + slippage 0,2% per sisi",
    "universe": "DES point-in-time, median nilai 20 hari >= Rp5 M, harga >= Rp50, tidak beku, bersih_2020",
    "varian": "V-B target = entry + (base_high - base_low) + stop; V-C 50% di target V-B sisanya trailing MA20; V-D tanpa filter JII (info saja)",
    "periode": "dev 2020-2023 (indikator valid sejak hari ke-220), holdout 2024-Okt 2026 hanya bila dev lolos",
    "lolos": "standar seragam (EW, JII, tanpa 5/10, tanpa tahun terbaik, S1 2 tick, S2 Rp20 M, S3 harga >= 200) + trade dev >= 30 + expectancy bersih > 0R + (korelasi H11a < 0,5 atau Sharpe 50/50 > Sharpe H11a)",
}


def hitung_sinyal(Hd, Ld, Cd, Vd, CMd, dasar, jii_ok, likuid=LIKUID, hmin=HARGA_MIN, pakai_jii=True):
    ma = {n: Cd.rolling(n).mean() for n in (20, 50, 100, 200)}
    stage2 = (Cd > ma[20]) & (ma[20] > ma[50]) & (ma[50] > ma[100]) & (ma[100] > ma[200]) & (ma[200] > ma[200].shift(20))
    med = (CMd * Vd).rolling(20).median()
    univ = dasar & (med >= likuid) & (CMd >= hmin) & (Vd > 0)
    r = (Cd / Cd.shift(RS_HARI) - 1).where(univ)
    pct = r.rank(axis=1, pct=True)
    rs_ok = (pct >= RS_PCT) & (r.notna().sum(axis=1) >= RS_MIN_N).to_numpy()[:, None]
    bh = pd.DataFrame(np.nan, index=Cd.index, columns=Cd.columns)
    bl = bh.copy()
    for L in range(BASE_MIN, BASE_MAKS + 1):
        hi = Hd.rolling(L).max().shift(1)
        lo = Ld.rolling(L).min().shift(1)
        ok = ((hi - lo) / hi <= BASE_RANGE) & hi.notna()
        bh = bh.where(~ok, hi)
        bl = bl.where(~ok, lo)
    vol50 = Vd.rolling(VOL_HARI).mean().shift(1)
    trig = (Cd > bh) & (Vd >= VOL_X * vol50)
    stop0 = Ld.rolling(STOP_HARI).min().shift(1)
    sig = univ & stage2 & rs_ok & trig & stop0.notna()
    if pakai_jii:
        sig = sig & jii_ok.to_numpy()[:, None]
    return {"sig": sig.to_numpy(bool), "bh": bh.to_numpy(float), "bl": bl.to_numpy(float), "stop0": stop0.to_numpy(float),
            "pct": pct.to_numpy(float), "med": med, "ma20": ma[20].to_numpy(float), "univ": univ}


class P40(h36.Harga):
    def __init__(self, sampai, awal=WARM):
        super().__init__(sampai, None)
        raw = hg.bersih_banyak(kolom=["high", "low", "volume"])

        def lebar(kol):
            return pd.DataFrame({k: raw[k][kol] for k in self.kode}).reindex(self.T).astype(float)

        self.Hd, self.Ld, self.Vd = lebar("high"), lebar("low"), lebar("volume")
        self.H, self.Lw, self.V = self.Hd.values, self.Ld.values, self.Vd.values
        self.Cd = pd.DataFrame(self.Cf, index=self.T, columns=self.kode)
        self.CMd = pd.DataFrame(self.CM, index=self.T, columns=self.kode).ffill()
        des = np.zeros((self.n, len(self.kode)), bool)
        for k, rentang in self.des.items():
            if k in self.ki:
                for a, b in rentang:
                    des[:, self.ki[k]] |= (self.T >= a) & (self.T <= b)
        self.desm = pd.DataFrame(des, index=self.T, columns=self.kode)
        self.dasar = self.desm & pd.DataFrame(self.ada & ~self.BK, index=self.T, columns=self.kode)
        j = self.jii
        self.jii_ok = (j > j.rolling(200).mean()).reindex(self.T).ffill().fillna(False).astype(bool)
        self.i0 = awal
        self._h11 = {}
        self._mask = {}

    def lolos(self, likuid, hmin):
        kunci = (likuid, hmin)
        if kunci not in self._mask:
            med = (self.CMd * self.Vd).rolling(20).median()
            self._mask[kunci] = ((med >= likuid) & (self.CMd >= hmin) & pd.DataFrame(self.ada & ~self.BK, index=self.T, columns=self.kode)).to_numpy(bool)
        return self._mask[kunci]

    def sinyal(self, likuid=LIKUID, hmin=HARGA_MIN, pakai_jii=True):
        kunci = (likuid, hmin, pakai_jii)
        if kunci not in self._h11:
            self._h11[kunci] = hitung_sinyal(self.Hd, self.Ld, self.Cd, self.Vd, self.CMd, self.dasar, self.jii_ok, likuid, hmin, pakai_jii)
        return self._h11[kunci]


class Buku:
    def __init__(self, P, n_tick, slip):
        self.P, self.n_tick, self.slip = P, n_tick, slip
        self.kas = MODAL
        self.pegang = {}
        self.trades = []
        self.laba = {}
        self.eq = np.zeros(P.n)
        self.expo = np.zeros(P.n)

    def awal_hari(self, i):
        P = self.P
        t = P.T[i]
        for k in list(self.pegang):
            if k in P.delisting and t > P.terakhir[k]:
                h = self.pegang.pop(k)
                self.catat(h, k, t, 0.0, "delisting")
        for k, h in self.pegang.items():
            dv = P.D[i, P.ki[k]]
            if dv > 0:
                u = h["lembar"] * dv * (1 - PAJAK_DIV)
                self.kas += u
                h["terima"] += u

    def catat(self, h, k, t, sisa, alasan):
        rp = h["terima"] + sisa - h["biaya"]
        self.laba[k] = self.laba.get(k, 0.0) + rp
        self.trades.append({"kode": k, "beli": h["tgl"], "jual": t, "rp": rp, "R": rp / h["risiko"] if h["risiko"] > 0 else np.nan,
                            "net": (h["terima"] + sisa) / h["biaya"] * 100 - 100, "alasan": alasan, "hari": h["hari"], "pct": h["pct"]})

    def bisa(self, i, k):
        P = self.P
        c = P.ki[k]
        return bool(P.ada[i, c] and not P.TT[i, c] and P.O[i, c] > 0)

    def jual(self, i, k, p_adj, alasan, porsi=1.0, tick=True):
        P = self.P
        c = P.ki[k]
        h = self.pegang[k]
        f = P.F[i, c]
        raw = p_adj / f
        raw = max(raw - (h3_tick(raw) * self.n_tick if tick else 0.0), 1.0) * (1 - self.slip)
        lembar = h["lembar"] * porsi
        hasil = lembar * f * raw * (1 - FEE_JUAL)
        self.kas += hasil
        h["terima"] += hasil
        h["lembar"] -= lembar
        if porsi >= 1.0 - 1e-12 or h["lembar"] * f * raw < 1:
            h["lembar"] = 0.0
            self.pegang.pop(k)
            self.catat(h, k, P.T[i], 0.0, alasan)
        return True

    def beli(self, i, k, ukuran, stop=None, pct=np.nan, eq_ref=None):
        P = self.P
        c = P.ki[k]
        f = P.F[i, c]
        raw = P.O[i, c] / f
        px = (raw + h3_tick(raw) * self.n_tick) * (1 + self.slip)
        satuan = px * (1 + FEE_BELI)
        maks = int(self.kas / satuan // LOT) * LOT
        if ukuran == "risiko":
            stop_raw = stop / f
            per = satuan - stop_raw
            if per <= 0:
                return False
            lembar_raw = min(int(RISIKO * eq_ref / per // LOT) * LOT, maks)
            risiko = lembar_raw * per
        else:
            lembar_raw = min(int(ukuran * eq_ref / satuan // LOT) * LOT, maks)
            risiko = lembar_raw * satuan * 0.1
        if lembar_raw < LOT:
            return False
        uang = lembar_raw * satuan
        self.kas -= uang
        self.pegang[k] = {"lembar": lembar_raw / f, "biaya": uang, "i": i, "tgl": P.T[i], "terima": 0.0, "risiko": risiko, "pct": pct, "hari": 0, "stop": stop}
        return True

    def tutup_hari(self, i):
        P = self.P
        nilai = sum(h["lembar"] * P.Cf[i, P.ki[k]] for k, h in self.pegang.items())
        self.eq[i] = self.kas + nilai
        self.expo[i] = nilai / self.eq[i] if self.eq[i] > 0 else 0.0

    def akhir(self, i):
        P = self.P
        for k in list(self.pegang):
            h = self.pegang[k]
            if not (self.bisa(i, k) and self.jual(i, k, P.C[i, P.ki[k]], "akhir_data", tick=False)):
                val = h["lembar"] * P.Cf[i, P.ki[k]]
                self.pegang.pop(k)
                self.kas += val
                self.catat(h, k, P.T[i], val, "akhir_data")
        self.tutup_hari(i)


def h3_tick(harga):
    return float(sc.fraksi(harga))


def strategi(P, mode="utama", n_tick=1, likuid=LIKUID, hmin=HARGA_MIN, buang=frozenset(), pakai_jii=True):
    S = P.sinyal(likuid, hmin, pakai_jii)
    sig, bh, bl, stop0, pct, ma20 = S["sig"], S["bh"], S["bl"], S["stop0"], S["pct"], S["ma20"]
    kolom_buang = [P.ki[k] for k in buang if k in P.ki]
    if kolom_buang:
        sig = sig.copy()
        sig[:, kolom_buang] = False
    B = Buku(P, n_tick, SLIP)
    flag = set()
    target = {}
    hit = {"sinyal": 0, "kejar": 0, "stop_jauh": 0, "slot_penuh": 0, "tak_bisa": 0, "lot_kurang": 0, "dibeli": 0}
    for i in range(P.i0, P.n):
        B.awal_hari(i)
        akhir = i == P.n - 1
        for k in sorted(B.pegang, key=lambda z: B.pegang[z]["i"]):
            h = B.pegang[k]
            h["hari"] = i - h["i"]
            if k in flag or h["hari"] >= TAHAN:
                if B.bisa(i, k):
                    B.jual(i, k, P.O[i, P.ki[k]], "ma20" if k in flag else "waktu")
                    flag.discard(k)
        if not akhir and i > P.i0 and sig[i - 1].any():
            d = i - 1
            kand = np.flatnonzero(sig[d])
            kand = kand[np.argsort(-np.nan_to_num(pct[d, kand]))]
            eq_ref = B.eq[i - 1]
            for c in kand:
                k = P.kode[c]
                hit["sinyal"] += 1
                if k in B.pegang:
                    continue
                if len(B.pegang) >= SLOT:
                    hit["slot_penuh"] += 1
                    continue
                if not B.bisa(i, k):
                    hit["tak_bisa"] += 1
                    continue
                if P.O[i, c] > bh[d, c] * KEJAR:
                    hit["kejar"] += 1
                    continue
                e, s = P.O[i, c], stop0[d, c]
                if not (s < e) or (e - s) / e > STOP_MAKS:
                    hit["stop_jauh"] += 1
                    continue
                if B.beli(i, k, "risiko", stop=s, pct=pct[d, c], eq_ref=eq_ref):
                    hit["dibeli"] += 1
                    flag.discard(k)
                    B.pegang[k]["i"] = i
                    target[k] = e + (bh[d, c] - bl[d, c])
                    B.pegang[k]["sebagian"] = False
                else:
                    hit["lot_kurang"] += 1
        for k in sorted(B.pegang):
            c = P.ki[k]
            h = B.pegang[k]
            if not P.ada[i, c] or P.TT[i, c]:
                continue
            o, lo, hi = P.O[i, c], P.Lw[i, c], P.H[i, c]
            if mode in ("B", "C") and o >= target[k] and not h["sebagian"]:
                if mode == "B":
                    B.jual(i, k, o, "target", tick=False)
                    continue
                B.jual(i, k, o, "target50", 0.5, tick=False)
                h["sebagian"] = True
                if k not in B.pegang:
                    continue
            if lo <= h["stop"]:
                B.jual(i, k, min(h["stop"], o), "stop", tick=False)
                continue
            if mode in ("B", "C") and not h["sebagian"] and hi >= target[k]:
                if mode == "B":
                    B.jual(i, k, target[k], "target", tick=False)
                    continue
                B.jual(i, k, target[k], "target50", 0.5, tick=False)
                h["sebagian"] = True
        if not akhir:
            for k in B.pegang:
                c = P.ki[k]
                if mode != "B" and P.ada[i, c] and P.C[i, c] < ma20[i, c]:
                    flag.add(k)
            B.tutup_hari(i)
        else:
            B.akhir(i)
    return {"eq": B.eq, "trades": pd.DataFrame(B.trades), "laba": B.laba, "expo": B.expo, "hit": hit}


def h11a(P, seed):
    L = P.desm.to_numpy(bool) & Harga_lolos(P)
    mx = P.Cd.rolling(250).max().shift(1).to_numpy(float)
    sinyal = (P.Cf >= mx) & L
    B = Buku(P, 1, 0.0)
    stop, tinggi, flag = {}, {}, set()
    for i in range(P.i0, P.n):
        B.awal_hari(i)
        akhir = i == P.n - 1
        for k in sorted(B.pegang, key=lambda z: B.pegang[z]["i"]):
            h = B.pegang[k]
            h["hari"] = i - h["i"]
            if k in flag or h["hari"] >= H11_HARI:
                if B.bisa(i, k):
                    B.jual(i, k, P.O[i, P.ki[k]], "stop")
                    flag.discard(k)
        if not akhir and i > P.i0 and sinyal[i - 1].any():
            d = i - 1
            kand = np.flatnonzero(sinyal[d])
            np.random.default_rng(seed * 1000003 + i).shuffle(kand)
            for c in kand:
                k = P.kode[c]
                if k in B.pegang or len(B.pegang) >= H11_POSISI or not B.bisa(i, k) or not np.isfinite(P.ATR[d, c]):
                    continue
                if B.beli(i, k, H11_BOBOT, eq_ref=B.eq[i - 1]):
                    B.pegang[k]["i"] = i
                    stop[k] = P.O[i, c] - H11_ATR * P.ATR[d, c] / 100 * P.Cf[d, c]
                    tinggi[k] = P.C[i, c]
        for k in list(B.pegang):
            c = P.ki[k]
            if not P.ada[i, c]:
                continue
            if P.C[i, c] < stop[k]:
                flag.add(k)
            else:
                tinggi[k] = max(tinggi[k], P.C[i, c])
                if np.isfinite(P.ATR[i, c]):
                    stop[k] = max(stop[k], tinggi[k] - H11_ATR * P.ATR[i, c] / 100 * P.Cf[i, c])
        if not akhir:
            B.tutup_hari(i)
        else:
            B.akhir(i)
    return {"eq": B.eq, "trades": pd.DataFrame(B.trades), "laba": B.laba, "expo": B.expo}


def Harga_lolos(P):
    return h36.Harga.lolos(P, LIKUID, HARGA_MIN)


def harian(P, hasil):
    return pd.Series(hasil["eq"][P.i0:], index=P.T[P.i0:]).pct_change().fillna(0.0)


def rincian(P, h):
    tr = h["trades"]
    m = h36.metrik(P, h)
    if tr.empty:
        return {**m, "n": 0}
    R = tr["R"].dropna()
    menang, kalah = R[R > 0], R[R <= 0]
    urut = tr.sort_values("jual")["rp"].to_numpy() <= 0
    streak = best = 0
    for x in urut:
        streak = streak + 1 if x else 0
        best = max(best, streak)
    return {**m, "n": int(len(tr)), "win": float((R > 0).mean() * 100), "avg_win": float(menang.mean()) if len(menang) else np.nan,
            "avg_loss": float(kalah.mean()) if len(kalah) else np.nan, "expect": float(R.mean()), "streak": int(best),
            "expo": float(h["expo"][P.i0:].mean() * 100)}


def pc(x):
    return None if x is None or not np.isfinite(x) else round(float(x) * 100, 2)


def h11a_median(P):
    hasil = []
    for s in H11_SEED:
        h = h11a(P, s)
        hasil.append((h36.metrik(P, h)["cagr"], s, h))
    hasil.sort(key=lambda z: z[0])
    return hasil[len(hasil) // 2][2], [round(c * 100, 1) for c, _, _ in hasil]


def seragam(P, jii_m, ew_cache, cfg):
    h = strategi(P, "utama", cfg["ntick"], cfg["likuid"], cfg["hmin"])
    mh = h36.metrik(P, h)
    kunci = (cfg["likuid"], cfg["hmin"])
    ew = ew_cache(kunci, frozenset())
    me = h36.metrik(P, ew)
    top_h = sorted(h["laba"], key=lambda k: -h["laba"][k])
    top_e = sorted(ew["laba"], key=lambda k: -ew["laba"][k])
    k = {"1_vs_ew": mh["cagr"] > me["cagr"], "2_vs_jii": mh["cagr"] > jii_m["cagr"]}
    out = {"cagr": mh["cagr"], "dd": mh["dd"], "ew": me["cagr"], "jii": jii_m["cagr"], "trade": int(len(h["trades"]))}
    for m in (5, 10):
        hm = h36.metrik(P, strategi(P, "utama", cfg["ntick"], cfg["likuid"], cfg["hmin"], frozenset(top_h[:m])))
        em = h36.metrik(P, ew_cache(kunci, frozenset(top_e[:m])))
        out[f"tanpa{m}"] = (hm["cagr"], em["cagr"])
        k[f"{3 if m == 5 else 4}_tanpa{m}"] = hm["cagr"] > em["cagr"]
    a, b, c = h36.tanpa_terbaik(mh["twr"]), h36.tanpa_terbaik(me["twr"]), h36.tanpa_terbaik(jii_m["twr"])
    out["tanpa_tahun"] = (a, b, c)
    k["5_tanpa_tahun"] = bool(a > b and a > c)
    out["kriteria"] = {x: bool(v) for x, v in k.items()}
    out["lulus"] = all(k.values())
    return out, h, mh


def baris(nama, r, kor=None):
    f = lambda x, d=1: "-" if x is None or not np.isfinite(x) else f"{x:.{d}f}"
    return (f"{nama:<12} n {r['n']:>3} | win {f(r.get('win'))}% | avgW {f(r.get('avg_win'), 2)}R | avgL {f(r.get('avg_loss'), 2)}R | exp {f(r.get('expect'), 2)}R | "
            f"CAGR {pc(r['cagr'])}% | DD {pc(r['dd'])}% | Sharpe {f(r['sharpe'], 2)} | streak {r.get('streak', '-')} | expo {f(r.get('expo'))}% | kor H11a {f(kor, 2)}")


def utama(periode="dev"):
    akhir = AKHIR_DEV if periode == "dev" else AKHIR_HOLDOUT
    P = P40(SAMPAI_DEV if periode == "dev" else None, WARM if periode == "dev" else 0)
    if periode == "holdout":
        P.i0 = int(np.searchsorted(P.T.values, np.datetime64("2024-01-01"), side="left"))
    print(f"[{periode}] kode {len(P.kode)}, sim {P.T[P.i0].date()} s/d {P.T[-1].date()} ({P.n - P.i0} hari), delisting {len(P.delisting)}", flush=True)
    jii_m = h36.metrik(P, h36.jii_total(P))
    cache = {}

    def ew_cache(kunci, buang):
        if (kunci, buang) not in cache:
            cache[(kunci, buang)] = h36.bobot_sama(P, kunci[0], kunci[1], buang)
        return cache[(kunci, buang)]

    ew = ew_cache((LIKUID, HARGA_MIN), frozenset())
    me = h36.metrik(P, ew)
    h11, seeds = h11a_median(P)
    r11 = rincian(P, h11)
    rh11 = harian(P, h11)
    print(f"H11a (mesin sama, median 5 seed, CAGR seed {seeds}) selesai", flush=True)
    varian = {"utama": {}, "S1_2tick": {"ntick": 2}, "S2_rp20m": {"likuid": 20e9}, "S3_rp200": {"hmin": 200}}
    hasil = {}
    pertama = None
    for nama, ubah in varian.items():
        cfg = {"ntick": 1, "likuid": LIKUID, "hmin": HARGA_MIN, **ubah}
        r, h, mh = seragam(P, jii_m, ew_cache, cfg)
        hasil[nama] = r
        if nama == "utama":
            pertama = (r, h, mh)
        print(f"{nama}: CAGR {pc(r['cagr'])}% vs EW {pc(r['ew'])}% JII {pc(r['jii'])}% | trade {r['trade']} | tanpa5 {pc(r['tanpa5'][0])} vs {pc(r['tanpa5'][1])} | tanpa10 {pc(r['tanpa10'][0])} vs {pc(r['tanpa10'][1])} | tahun {[pc(x) for x in r['tanpa_tahun']]} | {r['kriteria']}", flush=True)
    r, h, mh = pertama
    ru = rincian(P, h)
    rhu = harian(P, h)
    kor = float(rhu.corr(rh11))
    comb = 0.5 * rhu + 0.5 * rh11
    sh_comb = float(comb.mean() / comb.std() * np.sqrt(252)) if comb.std() > 0 else np.nan
    info = {}
    for nama, kw in (("V-B", {"mode": "B"}), ("V-C", {"mode": "C"}), ("V-D", {"pakai_jii": False})):
        hv = strategi(P, **kw)
        info[nama] = (rincian(P, hv), float(harian(P, hv).corr(rh11)))
    print(f"\n===== H40 {periode} | {P.T[P.i0].date()} s/d {P.T[-1].date()} =====")
    print(baris("UTAMA", ru, kor))
    for nama, (rv, kv) in info.items():
        print(baris(nama + " (info)", rv, kv))
    print(baris("H11a (mesin)", r11, 1.0))
    print(f"pembanding: JII B&H CAGR {pc(jii_m['cagr'])}% DD {pc(jii_m['dd'])}% Sharpe {jii_m['sharpe']:.2f} | EW syariah CAGR {pc(me['cagr'])}% DD {pc(me['dd'])}% Sharpe {me['sharpe']:.2f}")
    print(f"Sharpe 50/50 (H40+H11a) {sh_comb:.2f} vs H11a {r11['sharpe']:.2f} | korelasi harian {kor:.2f}")
    print(f"eksekusi: {h['hit']}")
    print("alasan exit:", h["trades"]["alasan"].value_counts().to_dict() if len(h["trades"]) else {})
    print("per tahun H40/EW/JII:", {int(y): (pc(mh["twr"].get(y)), pc(me["twr"].get(y)), pc(jii_m["twr"].get(y))) for y in mh["twr"].index})
    top = sorted(h["laba"].items(), key=lambda x: -x[1])[:5]
    print("5 penyumbang laba:", [(k, round(v / 1e6, 1)) for k, v in top])
    standar = all(hasil[k]["lulus"] for k in varian)
    syarat = {"trade>=30": ru["n"] >= 30, "expectancy>0R": bool(ru.get("expect", -1) > 0), "tambah_nilai": bool(kor < 0.5 or sh_comb > r11["sharpe"])}
    lulus = bool(standar and all(syarat.values()))
    gagal = [k for k, v in hasil.items() if not v["lulus"]]
    alasan = []
    if not standar:
        alasan.append("standar seragam gagal di " + ",".join(gagal))
    alasan += [f"{k} gagal" for k, v in syarat.items() if not v]
    print(f"\nVONIS {periode.upper()}: {'LOLOS' if lulus else 'GAGAL'}" + (" | " + "; ".join(alasan) if alasan else ""))
    versi = hg.sidik(P.kode, mulai=h36.MULAI, akhir=P.T[-1], koleksi="harga_bersih_2020", kolom=("open", "close", "dividen", "saham_tercatat"))
    simpan = {"dibuat": datetime.now().isoformat(timespec="seconds"), "periode": periode, "lulus": lulus, "standar": bool(standar), "syarat": {k: bool(v) for k, v in syarat.items()},
              "utama": {k: (pc(v) if k in ("cagr", "dd") else v) for k, v in ru.items() if k not in ("twr",)}, "korelasi_h11a": kor, "sharpe_50_50": sh_comb,
              "h11a": {k: (pc(v) if k in ("cagr", "dd") else v) for k, v in r11.items() if k != "twr"},
              "varian_seragam": {k: {"cagr": pc(v["cagr"]), "ew": pc(v["ew"]), "jii": pc(v["jii"]), "trade": v["trade"], "kriteria": v["kriteria"], "lulus": v["lulus"]} for k, v in hasil.items()},
              "varian_info": {k: {x: (pc(y) if x in ("cagr", "dd") else y) for x, y in v[0].items() if x != "twr"} for k, v in info.items()},
              "versi_data": {**versi, "keterbatasan": "indikator MA200/RS baru valid sejak hari bursa ke-220 (harga_bersih mulai 2 Jan 2020); survivorship ditutup 2020+; DES point-in-time; H11a = mesin sama (lot, 5 seed median) bukan angka backtest resmi"}}
    dt.simpan_hasil(f"h40_{periode}", json.loads(json.dumps(simpan, default=str)))
    print("SELESAI")
    return lulus


def cek():
    ro = hg.banyak([x.replace(".JK", "") for x in dt.baca_daftar("syariah_tickers")], ["open", "high", "low", "close", "adj_close", "volume"])
    ro = {k: v for k, v in ro.items() if len(v) > 300}
    T = pd.DatetimeIndex(sorted(set().union(*[set(v.index) for v in ro.values()])))
    T = T[T >= "2014-06-01"]

    def lebar(kol, adj=False):
        d = {}
        for k, v in ro.items():
            x = v[kol]
            if adj:
                x = x * (v["adj_close"] / v["close"])
            d[k] = x
        return pd.DataFrame(d).reindex(T).astype(float)

    Cd, Hd, Ld, Vd, CMd = lebar("close", True), lebar("high", True), lebar("low", True), lebar("volume"), lebar("close")
    Cd = Cd.ffill(limit=5)
    dasar = Cd.notna()
    j = hg.indeks("indeks/JKII")
    j = j["close"] if isinstance(j, pd.DataFrame) else j
    j.index = pd.to_datetime(j.index)
    j = j.sort_index()
    jii_ok = (j > j.rolling(200).mean()).reindex(T).ffill().fillna(False).astype(bool)
    print(f"[cek] Yahoo koreksi, syariah_tickers hari ini (survivorship), {len(ro)} saham", flush=True)
    for nama, pj in (("utama", True), ("tanpa filter JII", False)):
        S = hitung_sinyal(Hd, Ld, Cd, Vd, CMd, dasar, jii_ok, pakai_jii=pj)
        s = pd.DataFrame(S["sig"], index=T)
        sd = s.copy()
        awal = s.shift(1, fill_value=False)
        baru = s & ~awal
        per = baru.sum(axis=1).groupby(T.year).sum()
        print(f"sinyal ({nama}) per tahun, hari-saham: ", {int(y): int(s.sum(axis=1).groupby(T.year).sum()[y]) for y in per.index if y >= 2016}, flush=True)
        print(f"sinyal ({nama}) per tahun, kejadian baru:", {int(y): int(v) for y, v in per.items() if y >= 2016}, flush=True)
    return


def cek_bersih():
    P = P40(SAMPAI_DEV, WARM)
    print(f"[cek_bersih] DES point-in-time, harga_bersih, dev {P.T[P.i0].date()} s/d {P.T[-1].date()}")
    for nama, pj in (("utama", True), ("tanpa filter JII", False)):
        S = P.sinyal(pakai_jii=pj)
        s = pd.DataFrame(S["sig"], index=P.T)
        s = s[s.index <= AKHIR_DEV]
        baru = (s & ~s.shift(1, fill_value=False)).sum(axis=1)
        post = pd.DataFrame(S["sig"], index=P.T).iloc[P.i0:]
        post = post[post.index <= AKHIR_DEV]
        pre = (post & ~post.shift(1, fill_value=False)).sum(axis=1)
        print(f"{nama}: kejadian baru dev per tahun {pre.groupby(pre.index.year).sum().to_dict()} total {int(pre.sum())} | hari-saham {int(post.sum().sum())}")
        if pj:
            ts = pd.DataFrame(S["sig"], index=P.T).iloc[P.i0:]
            ts = ts[ts.index <= AKHIR_DEV]
            print("   jii_ok hari dev:", int(P.jii_ok.iloc[P.i0:][P.T[P.i0:] <= AKHIR_DEV].sum()), "dari", int((P.T[P.i0:] <= AKHIR_DEV).sum()))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "kunci":
        lama = dt.baca_hasil("h40_aturan")
        if lama:
            raise SystemExit(f"aturan sudah dikunci {lama.get('dikunci')}")
        dt.simpan_hasil("h40_aturan", {"dikunci": datetime.now().isoformat(timespec="seconds"), **ATURAN})
        print("aturan dikunci")
    elif arg == "cek":
        cek()
        cek_bersih()
    elif arg == "dev":
        utama("dev")
    elif arg == "holdout":
        dev = dt.baca_hasil("h40_dev")
        if not dev or not dev.get("lulus"):
            raise SystemExit("holdout tidak dibuka: dev belum lolos")
        if PENANDA_BUKA.exists():
            raise SystemExit(f"holdout H40 sudah dibuka ({PENANDA_BUKA.read_text().strip()})")
        PENANDA_BUKA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
        utama("holdout")
    else:
        raise SystemExit("pakai: kunci | cek | dev | holdout")
