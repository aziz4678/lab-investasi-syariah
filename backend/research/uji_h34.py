import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi
from backend.research import analisis_likuiditas as al
from backend.research import analisis_profil as ap
from backend.research.screener import fraksi

MULAI = pd.Timestamp("2020-01-01")
AKHIR = pd.Timestamp("2023-12-31")
SETORAN = 5_000_000
PORSI_CADANGAN = 0.20
N = 10
ROE_MIN, ROE_MIN_KEU = 0.12, 0.10
DER_MAKS = 1.0
TURUN = 0.15
MAKS_SAHAM = 0.15
LIKUID, HARGA_MIN = 5e9, 50
FEE_BELI, FEE_JUAL = 0.0015, 0.0025
PAJAK_DIV = 0.10
DIV_JII = 0.025
LOT = 100
PLASEBO = 500
JENDELA_LAP, BASI_LAP = 730, 300
FY2018_TERBIT = pd.Timestamp("2019-04-30")
AKHIR_PERIODE = {"TW1": (3, 31), "TW2": (6, 30), "TW3": (9, 30), "AUDIT": (12, 31)}


class Data:
    def __init__(self):
        raw = hg.bersih_banyak(kolom=["open", "close", "close_mentah", "faktor", "nilai", "tanpa_transaksi", "beku", "dividen", "saham_tercatat"])
        raw = {k: v[(v.index >= MULAI) & (v.index <= AKHIR)] for k, v in raw.items()}
        raw = {k: v for k, v in raw.items() if len(v)}
        self.kode = sorted(raw)
        self.ki = {k: i for i, k in enumerate(self.kode)}
        hari = sorted(set().union(*[set(v.index) for v in raw.values()]))
        self.T = pd.DatetimeIndex(hari)
        self.ti = {t: i for i, t in enumerate(self.T)}

        def lebar(kol, isi=np.nan):
            return pd.DataFrame({k: raw[k][kol] for k in self.kode}).reindex(self.T).astype(float).fillna(isi) if isi == isi else pd.DataFrame({k: raw[k][kol] for k in self.kode}).reindex(self.T).astype(float)

        self.O = lebar("open").values
        self.C = lebar("close").values
        self.CM = lebar("close_mentah").values
        self.F = lebar("faktor").values
        self.V = pd.DataFrame({k: raw[k]["nilai"] for k in self.kode}).reindex(self.T).astype(float)
        self.TT = pd.DataFrame({k: raw[k]["tanpa_transaksi"] for k in self.kode}).reindex(self.T).fillna(True).astype(bool).values
        self.BK = pd.DataFrame({k: raw[k]["beku"] for k in self.kode}).reindex(self.T).fillna(False).astype(bool).values
        self.D = lebar("dividen", 0.0).values
        self.SH = lebar("saham_tercatat").values
        self.ada = ~np.isnan(self.C)
        self.terakhir = {k: raw[k].index[-1] for k in self.kode}
        self.delisting = {k for k, t in self.terakhir.items() if t < self.T[-1]}
        self.likuid = self.V.rolling(60, min_periods=60).median().values
        self.ndata = pd.DataFrame(self.ada, index=self.T).cumsum().values
        bulan = pd.Series(self.T, index=self.T).groupby(self.T.to_period("M"))
        self.awal_bulan = list(bulan.first())
        self.akhir_bulan = list(bulan.last())
        self.des = {}
        for d in koneksi.koneksi()["des"].find({}, {"kode": 1, "mulai": 1, "akhir": 1}):
            self.des.setdefault(d["kode"], []).append((pd.Timestamp(d["mulai"]), pd.Timestamp(d["akhir"])))
        prof = {d["kode"]: d.get("sektor") for d in koneksi.koneksi()["profil_idx"].find({}, {"kode": 1, "sektor": 1})}
        self.keuangan = {k for k, s in prof.items() if s == "Keuangan"}
        kurs = dt.baca("kurs/USD")["close"]
        kurs.index = pd.to_datetime(kurs.index)
        self.kurs = kurs.sort_index()
        self.lap = self._fundamental()
        L = al.semua_indeks()["L"]
        self.pu = L["PU"].dropna()
        self.rd_saham = ap.indeks_baru(cetak=False)[0]["SH"][0].dropna()
        j = hg.indeks("indeks/JKII")
        j = j["close"] if isinstance(j, pd.DataFrame) else j
        j.index = pd.to_datetime(j.index)
        self.jii = j.sort_index()
        self._pbv_titik = {}
        self._kual = {}
        self._uni = {}

    def _fundamental(self):
        rows = list(koneksi.koneksi()["fundamental"].find({"ada_angka": True, "tgl_publikasi": {"$ne": None}},
                                                          {"_id": 0, "kode": 1, "tahun": 1, "periode": 1, "tgl_publikasi": 1, "laba": 1, "laba_lalu": 1, "ekuitas": 1,
                                                           "ekuitas_total": 1, "liabilitas": 1, "arus_kas_operasi": 1, "arus_kas_operasi_lalu": 1, "unit": 1}))
        f = pd.DataFrame(rows)
        f["tgl_publikasi"] = pd.to_datetime(f["tgl_publikasi"])
        fy = {}
        for r in f[f["periode"] == "AUDIT"].itertuples():
            fy[(r.kode, r.tahun)] = (r.laba, r.arus_kas_operasi, r.tgl_publikasi)
            if r.tahun == 2019 and (r.kode, 2018) not in fy:
                fy[(r.kode, 2018)] = (r.laba_lalu, r.arus_kas_operasi_lalu, FY2018_TERBIT)
        hasil = {}
        for r in f.itertuples():
            if r.periode not in AKHIR_PERIODE:
                continue
            m, d = AKHIR_PERIODE[r.periode]
            akhir = pd.Timestamp(r.tahun, m, d)
            if r.periode == "AUDIT":
                laba, cfo, tersedia = r.laba, r.arus_kas_operasi, r.tgl_publikasi
            else:
                p = fy.get((r.kode, r.tahun - 1))
                if p is None:
                    continue
                laba = r.laba + p[0] - r.laba_lalu
                cfo = r.arus_kas_operasi + p[1] - r.arus_kas_operasi_lalu
                tersedia = max(r.tgl_publikasi, p[2])
            ek = r.ekuitas
            roe = laba / ek if ek == ek and ek > 0 and laba == laba else np.nan
            der = r.liabilitas / r.ekuitas_total if r.ekuitas_total == r.ekuitas_total and r.ekuitas_total > 0 else np.nan
            hasil.setdefault(r.kode, []).append({"akhir": akhir, "tersedia": tersedia, "terbit": r.tgl_publikasi, "roe": roe, "cfo": cfo, "der": der,
                                                 "ekuitas": ek, "usd": r.unit == "USD"})
        for k in hasil:
            hasil[k].sort(key=lambda x: (x["akhir"], x["tersedia"]))
        return hasil

    def ekuitas(self, k, t):
        c = [x for x in self.lap.get(k, []) if x["terbit"] < t and x["ekuitas"] == x["ekuitas"]]
        if not c:
            return None
        x = max(c, key=lambda x: (x["akhir"], x["terbit"]))
        if x["ekuitas"] <= 0:
            return None
        e = x["ekuitas"]
        if x["usd"]:
            kr = self.kurs[self.kurs.index <= t]
            if not len(kr):
                return None
            e *= float(kr.iloc[-1])
        return e

    def kualitas(self, k, t):
        kunci = (k, t)
        if kunci in self._kual:
            return self._kual[kunci]
        c = {}
        for x in self.lap.get(k, []):
            if x["tersedia"] < t and x["akhir"] > t - pd.Timedelta(days=JENDELA_LAP) and x["roe"] == x["roe"]:
                c[x["akhir"]] = x
        c = [c[a] for a in sorted(c)][-8:]
        hasil = (False, None)
        if len(c) >= 4 and c[-1]["akhir"] >= t - pd.Timedelta(days=BASI_LAP):
            rmin = min(x["roe"] for x in c)
            ok = rmin >= (ROE_MIN_KEU if k in self.keuangan else ROE_MIN)
            if ok and k not in self.keuangan:
                ok = c[-1]["cfo"] == c[-1]["cfo"] and c[-1]["cfo"] > 0 and c[-1]["der"] == c[-1]["der"] and c[-1]["der"] <= DER_MAKS
            hasil = (bool(ok), rmin)
        self._kual[kunci] = hasil
        return hasil

    def di_des(self, k, t):
        return any(a <= t <= b for a, b in self.des.get(k, []))

    def universe(self, i, likuid, hmin, buang):
        kunci = (i, likuid, hmin, buang)
        if kunci in self._uni:
            return self._uni[kunci]
        t = self.T[i]
        j = i - 1
        hasil = []
        if j >= 0:
            for k, c in self.ki.items():
                if k in buang or not self.ada[j, c] or self.BK[j, c] or self.ndata[j, c] < 60:
                    continue
                if not (self.likuid[j, c] >= likuid) or not (self.CM[j, c] >= hmin):
                    continue
                if self.di_des(k, t):
                    hasil.append(k)
        self._uni[kunci] = hasil
        return hasil

    def pbv_median(self, k, t):
        if k not in self._pbv_titik:
            c = self.ki[k]
            sh0 = self.SH[np.argmax(self.ada[:, c]), c] if self.ada[:, c].any() else np.nan
            titik = []
            y = None
            for q in pd.date_range("2019-03-31", AKHIR, freq="QE"):
                if q < MULAI:
                    if y is None:
                        try:
                            y = hg.saham(k)
                            y.index = pd.to_datetime(y.index)
                        except Exception:
                            y = pd.DataFrame()
                    if y is None or y.empty or "close" not in y:
                        continue
                    s = y["close"][y.index <= q]
                    if not len(s) or not (sh0 == sh0):
                        continue
                    mcap = float(s.iloc[-1]) * sh0
                else:
                    idx = np.searchsorted(self.T.values, np.datetime64(q), side="right") - 1
                    if idx < 0 or not self.ada[idx, c]:
                        continue
                    mcap = self.C[idx, c] * self.SH[idx, c]
                e = self.ekuitas(k, q + pd.Timedelta(days=1))
                if e is None or not (mcap == mcap):
                    continue
                titik.append((q, mcap / e))
            self._pbv_titik[k] = titik
        v = [p for q, p in self._pbv_titik[k] if q <= t]
        return float(np.median(v)) if len(v) >= 4 else None

    def pu_level(self, t):
        p = t.to_period("M") - 1
        s = self.pu[self.pu.index <= p]
        return float(s.iloc[-1])


def tick(harga, n):
    return float(fraksi(harga)) * n


def keranjang(D, i, likuid, hmin, buang):
    t = D.T[i]
    lolos = []
    for k in D.universe(i, likuid, hmin, buang):
        ok, rmin = D.kualitas(k, t)
        if ok:
            lolos.append((rmin, k))
    lolos.sort(key=lambda x: (-x[0], x[1]))
    return [k for _, k in lolos[:N]], len(lolos)


def xirr(tgl, arus):
    t0 = tgl[0]
    th = np.array([(t - t0).days / 365.25 for t in tgl])
    a = np.array(arus, dtype=float)
    f = lambda r: float(np.sum(a / (1 + r) ** th))
    try:
        return brentq(f, -0.99, 10)
    except ValueError:
        return np.nan


def turun_terdalam(rasio):
    r = np.asarray(rasio, dtype=float)
    puncak = np.maximum.accumulate(r)
    return float(np.min(r / puncak - 1))


def twr_tahun(T, nilai, arus, setor_pagi=True):
    r = pd.Series(0.0, index=T)
    for i in range(1, len(T)):
        dasar = nilai[i - 1] + arus[i] if setor_pagi else nilai[i - 1]
        atas = nilai[i] if setor_pagi else nilai[i] - arus[i]
        if dasar > 0:
            r.iloc[i] = atas / dasar - 1
    return (1 + r).groupby(T.year).prod() - 1


def tanpa_terbaik(th):
    th = th.dropna()
    if len(th) < 2:
        return np.nan
    sisa = th.drop(th.idxmax())
    return float((1 + sisa).prod() ** (1 / len(sisa)) - 1)


def simulasi(D, setoran=SETORAN, cadangan_porsi=PORSI_CADANGAN, tambah="aturan", jadwal=None, n_tick=1, likuid=LIKUID, hmin=HARGA_MIN,
             buang=frozenset(), delisting="nol", beku="harga", rng=None):
    T = D.T
    awal = set(D.awal_bulan)
    akhir = set(D.akhir_bulan)
    pegang = {}
    kas = 0.0
    unit_pu = 0.0
    total_setor = 0.0
    keranjang_kini = []
    keranjang_log = []
    juni_pertama = True
    tambahan_log = []
    tunda = []
    tak_terbeli = 0
    kontrib = {}
    nilai = np.zeros(len(T))
    setor_kum = np.zeros(len(T))
    kas_seri = np.zeros(len(T))
    cad_seri = np.zeros(len(T))
    arus = np.zeros(len(T))
    tgl_arus, nilai_arus = [], []
    keluar_delist = set()

    def kon(k):
        return kontrib.setdefault(k, {"beli": 0.0, "jual": 0.0, "div": 0.0})

    def total_nilai(i):
        s = 0.0
        for k, h in pegang.items():
            c = D.ki[k]
            p = D.C[i, c]
            if p != p:
                continue
            if beku == "nol" and D.BK[i, c]:
                continue
            s += h["lembar"] * p
        return s + kas + unit_pu * D.pu_level(T[i])

    def beli(i, k, uang, batas_total):
        nonlocal tak_terbeli
        c = D.ki[k]
        if not D.ada[i, c] or D.TT[i, c] or not (D.O[i, c] > 0):
            return 0.0
        f = D.F[i, c]
        o_raw = D.O[i, c] / f
        harga_raw = o_raw + tick(o_raw, n_tick)
        per_lot = LOT * harga_raw * (1 + FEE_BELI)
        h = pegang.get(k)
        sudah = (h["lembar"] * D.C[i - 1, c] if h and i > 0 and D.C[i - 1, c] == D.C[i - 1, c] else 0.0)
        ruang = MAKS_SAHAM * batas_total - sudah
        if uang < per_lot:
            return -1.0
        uang = min(uang, max(ruang, 0.0))
        lot = int(uang // per_lot)
        if lot <= 0:
            return -2.0
        biaya = lot * per_lot
        lembar = lot * LOT / f
        if h is None:
            pegang[k] = {"lembar": lembar, "biaya": biaya}
        else:
            h["lembar"] += lembar
            h["biaya"] += biaya
        kon(k)["beli"] += biaya
        return biaya

    def jual(i, k):
        nonlocal kas
        c = D.ki[k]
        if not D.ada[i, c] or D.TT[i, c] or not (D.O[i, c] > 0):
            return False
        f = D.F[i, c]
        o_raw = D.O[i, c] / f
        harga_raw = max(o_raw - tick(o_raw, n_tick), 1.0)
        hasil = pegang[k]["lembar"] * f * harga_raw * (1 - FEE_JUAL)
        kas += hasil
        kon(k)["jual"] += hasil
        del pegang[k]
        return True

    for i, t in enumerate(T):
        for k in list(pegang):
            if k in D.delisting and t > D.terakhir[k]:
                c = D.ki[k]
                if delisting == "beku":
                    terakhir_i = D.ti[D.terakhir[k]]
                    hasil = pegang[k]["lembar"] * D.C[terakhir_i, c]
                    kas += hasil
                    kon(k)["jual"] += hasil
                keluar_delist.add(k)
                del pegang[k]
        for k, h in pegang.items():
            c = D.ki[k]
            dv = D.D[i, c]
            if dv > 0:
                uang = h["lembar"] * dv * (1 - PAJAK_DIV)
                kas += uang
                kon(k)["div"] += uang
        if t in awal:
            dasar = (total_nilai(i - 1) if i > 0 else 0.0) + setoran
            kas += setoran * (1 - cadangan_porsi)
            unit_pu += setoran * cadangan_porsi / D.pu_level(t)
            total_setor += setoran
            arus[i] = setoran
            tgl_arus.append(t)
            nilai_arus.append(-setoran)
            for k in list(pegang):
                if not D.di_des(k, t):
                    jual(i, k)
            if tunda:
                for k, uang in tunda:
                    if k not in pegang:
                        continue
                    cad = unit_pu * D.pu_level(t)
                    uang = min(uang, cad)
                    if uang <= 0:
                        continue
                    b = beli(i, k, uang, dasar)
                    if b > 0:
                        unit_pu -= b / D.pu_level(t)
                        tambahan_log.append({"tgl": str(t.date()), "kode": k, "rupiah": round(b)})
                tunda = []
            juni = t.month == 6
            if (not keranjang_kini and juni_pertama) or (juni and juni_pertama is False) or (juni and juni_pertama):
                bk, nl = keranjang(D, i, likuid, hmin, buang)
                bentuk = juni or nl >= N
                if bentuk:
                    if juni:
                        for k in list(pegang):
                            ok, _ = D.kualitas(k, t)
                            if not ok:
                                jual(i, k)
                        juni_pertama = False
                    keranjang_kini = bk
                    keranjang_log.append({"tgl": str(t.date()), "keranjang": bk, "lolos": nl})
            bisa = [k for k in keranjang_kini if D.ada[i, D.ki[k]] and not D.TT[i, D.ki[k]] and D.di_des(k, t)]
            if bisa and kas > 0:
                jatah = kas / len(bisa)
                for k in bisa:
                    b = beli(i, k, jatah, dasar)
                    if b > 0:
                        kas -= b
                    elif b == -1.0:
                        tak_terbeli += 1
        if t in akhir and i < len(T) - 1:
            cad = unit_pu * D.pu_level(T[i + 1])
            if tambah == "aturan" and pegang:
                calon = []
                for k, h in pegang.items():
                    c = D.ki[k]
                    p = D.C[i, c]
                    if p != p or not D.di_des(k, t):
                        continue
                    rata = h["biaya"] / h["lembar"]
                    if p > rata * (1 - TURUN):
                        continue
                    e = D.ekuitas(k, t)
                    med = D.pbv_median(k, t)
                    if e is None or med is None:
                        continue
                    if not (p * D.SH[i, c] / e < med):
                        continue
                    if not D.kualitas(k, t)[0]:
                        continue
                    calon.append((p / rata, k))
                calon.sort()
                for _, k in calon:
                    uang = min(cad, setoran)
                    if uang <= 0:
                        break
                    tunda.append((k, uang))
                    cad -= uang
            elif tambah == "plasebo" and jadwal and t in jadwal and pegang:
                for uang in jadwal[t]:
                    k = rng.choice(sorted(pegang))
                    tunda.append((k, min(uang, cad)))
                    cad -= min(uang, cad)
        nilai[i] = total_nilai(i)
        setor_kum[i] = total_setor
        kas_seri[i] = kas
        cad_seri[i] = unit_pu * D.pu_level(t)
    tgl_arus.append(T[-1])
    nilai_arus.append(nilai[-1])
    akhir_i = len(T) - 1
    for k, h in pegang.items():
        c = D.ki[k]
        p = D.C[akhir_i, c]
        if p == p and not (beku == "nol" and D.BK[akhir_i, c]):
            kon(k)["akhir"] = h["lembar"] * p
    laba = {k: v["jual"] + v["div"] + v.get("akhir", 0.0) - v["beli"] for k, v in kontrib.items()}
    mulai = np.argmax(setor_kum > 0)
    rasio = nilai[mulai:] / setor_kum[mulai:]
    return {"xirr": xirr(tgl_arus, nilai_arus), "dd": turun_terdalam(rasio), "nilai_akhir": float(nilai[-1]), "setor": float(total_setor),
            "kas_rata": float(np.mean(kas_seri[mulai:] / setor_kum[mulai:])), "kas_maks": float(np.max(kas_seri[mulai:] / setor_kum[mulai:])),
            "cad_rata": float(np.mean(cad_seri[mulai:] / setor_kum[mulai:])), "tak_terbeli": tak_terbeli, "tambahan": tambahan_log,
            "keranjang": keranjang_log, "laba": laba, "twr": twr_tahun(T, nilai, arus), "delist_dipegang": sorted(keluar_delist)}


def bobot_sama(D, setoran=SETORAN, likuid=LIKUID, hmin=HARGA_MIN, buang=frozenset()):
    T = D.T
    awal = set(D.awal_bulan)
    w = {}
    kas = 0.0
    nilai = np.zeros(len(T))
    arus = np.zeros(len(T))
    tgl, ar = [], []
    total = 0.0
    setor_kum = np.zeros(len(T))
    laba = {}
    for i, t in enumerate(T):
        if i > 0:
            for k in list(w):
                c = D.ki[k]
                if D.ada[i, c] and D.ada[i - 1, c] and D.C[i - 1, c] > 0:
                    lama = w[k]
                    w[k] = lama * (D.C[i, c] + D.D[i, c]) / D.C[i - 1, c]
                    laba[k] = laba.get(k, 0.0) + w[k] - lama
                elif not D.ada[i, c] and k in D.delisting and t > D.terakhir[k]:
                    laba[k] = laba.get(k, 0.0) - w[k]
                    del w[k]
        if t in awal:
            total += setoran
            arus[i] = setoran
            tgl.append(t)
            ar.append(-setoran)
            jml = sum(w.values()) + kas + setoran
            uni = D.universe(i, likuid, hmin, buang)
            if uni:
                w = {k: jml / len(uni) for k in uni}
                kas = 0.0
            else:
                w = {}
                kas = jml
        nilai[i] = sum(w.values()) + kas
        setor_kum[i] = total
    tgl.append(T[-1])
    ar.append(nilai[-1])
    mulai = np.argmax(setor_kum > 0)
    return {"xirr": xirr(tgl, ar), "dd": turun_terdalam(nilai[mulai:] / setor_kum[mulai:]), "laba": laba, "twr": twr_tahun(T, nilai, arus, setor_pagi=False),
            "nilai_akhir": float(nilai[-1])}


def cicil_jii(D, setoran=SETORAN):
    j = D.jii
    T = D.T
    awal = set(D.awal_bulan)
    lv = j.reindex(T).ffill()
    hari = np.array([(T[i] - T[i - 1]).days if i else 0 for i in range(len(T))])
    tot = lv.values * np.cumprod((1 + DIV_JII) ** (hari / 365.25))
    unit = 0.0
    nilai = np.zeros(len(T))
    arus = np.zeros(len(T))
    tgl, ar = [], []
    setor_kum = np.zeros(len(T))
    s = 0.0
    for i, t in enumerate(T):
        if t in awal:
            unit += setoran / tot[i]
            s += setoran
            arus[i] = setoran
            tgl.append(t)
            ar.append(-setoran)
        nilai[i] = unit * tot[i]
        setor_kum[i] = s
    tgl.append(T[-1])
    ar.append(nilai[-1])
    sr = pd.Series(tot, index=T)
    akhir_th = sr.groupby(T.year).last()
    th = akhir_th / pd.concat([pd.Series([sr.iloc[0]], index=[akhir_th.index[0] - 1]), akhir_th]).shift(1).reindex(akhir_th.index) - 1
    return {"xirr": xirr(tgl, ar), "dd": turun_terdalam(nilai / setor_kum), "twr": th, "nilai_akhir": float(nilai[-1])}


def cicil_rd_saham(D, setoran=SETORAN):
    L = D.rd_saham
    bulan = pd.period_range(MULAI.to_period("M"), AKHIR.to_period("M"), freq="M")
    unit, tgl, ar, nilai, setor = 0.0, [], [], [], []
    s = 0.0
    for b in bulan:
        lv = float(L[L.index <= b - 1].iloc[-1])
        unit += setoran / lv
        s += setoran
        tgl.append(b.start_time)
        ar.append(-setoran)
        nilai.append(unit * float(L[L.index <= b].iloc[-1]))
        setor.append(s)
    tgl.append(AKHIR)
    ar.append(nilai[-1])
    return {"xirr": xirr(tgl, ar), "dd": turun_terdalam(np.array(nilai) / np.array(setor)), "nilai_akhir": nilai[-1]}


def plasebo(D, h, n=PLASEBO):
    jumlah = [x["rupiah"] for x in h["tambahan"]]
    mulai_k = pd.Timestamp(h["keranjang"][0]["tgl"]) if h["keranjang"] else D.T[0]
    calon = [t for t in D.akhir_bulan[:-1] if t >= mulai_k]
    hasil = []
    for s in range(n):
        rng = np.random.default_rng(s)
        jadwal = {}
        for u in jumlah:
            t = calon[rng.integers(len(calon))]
            jadwal.setdefault(t, []).append(u)
        r = simulasi(D, tambah="plasebo", jadwal=jadwal, rng=rng)
        hasil.append(r["xirr"])
    return np.array(hasil)


def seragam(D, n_tick=1, likuid=LIKUID, hmin=HARGA_MIN, jii=None):
    h = simulasi(D, n_tick=n_tick, likuid=likuid, hmin=hmin)
    ew = bobot_sama(D, likuid=likuid, hmin=hmin)
    jii = jii or cicil_jii(D)
    top_h = sorted(h["laba"], key=lambda k: -h["laba"][k])
    top_e = sorted(ew["laba"], key=lambda k: -ew["laba"][k])
    hasil = {"h34": h, "ew": ew}
    for m in (5, 10):
        hasil[f"h34_tanpa{m}"] = simulasi(D, n_tick=n_tick, likuid=likuid, hmin=hmin, buang=frozenset(top_h[:m]))
        hasil[f"ew_tanpa{m}"] = bobot_sama(D, likuid=likuid, hmin=hmin, buang=frozenset(top_e[:m]))
        hasil[f"buang{m}"] = (top_h[:m], top_e[:m])
    k = {
        "1_vs_ew": (h["xirr"], ew["xirr"], h["xirr"] > ew["xirr"]),
        "2_vs_jii": (h["xirr"], jii["xirr"], h["xirr"] > jii["xirr"]),
        "3_tanpa5": (hasil["h34_tanpa5"]["xirr"], hasil["ew_tanpa5"]["xirr"], hasil["h34_tanpa5"]["xirr"] > hasil["ew_tanpa5"]["xirr"]),
        "4_tanpa10": (hasil["h34_tanpa10"]["xirr"], hasil["ew_tanpa10"]["xirr"], hasil["h34_tanpa10"]["xirr"] > hasil["ew_tanpa10"]["xirr"]),
    }
    a, b, c = tanpa_terbaik(h["twr"]), tanpa_terbaik(ew["twr"]), tanpa_terbaik(jii["twr"])
    k["5_tanpa_tahun"] = ((a, b, c), None, bool(a > b and a > c))
    hasil["kriteria"] = k
    hasil["lulus"] = all(v[2] for v in k.values())
    return hasil


def f(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x) * 100, 2)


def utama():
    D = Data()
    print(f"data: {len(D.kode)} kode, {D.T[0].date()} s/d {D.T[-1].date()}, delisting di dev {len(D.delisting)}", flush=True)
    jii = cicil_jii(D)
    rd = cicil_rd_saham(D)
    dasar = seragam(D, jii=jii)
    h = dasar["h34"]
    a = simulasi(D, cadangan_porsi=0.0, tambah=None)
    print("H34 dasar selesai, plasebo ...", flush=True)
    pl = plasebo(D, h)
    pers = float((pl < h["xirr"]).mean() * 100)
    p95 = float(np.nanpercentile(pl, 95))
    sens = {}
    for nama, kw in (("S1_2tick", {"n_tick": 2}), ("S2_rp20m", {"likuid": 20e9}), ("S3_rp200", {"hmin": 200})):
        sens[nama] = seragam(D, jii=jii, **kw)
        print(f"{nama} selesai", flush=True)
    lap = {"delisting_beku": simulasi(D, delisting="beku"), "beku_nol": simulasi(D, beku="nol"), "setoran_1jt": simulasi(D, setoran=1_000_000),
           "a_setoran_1jt": simulasi(D, setoran=1_000_000, cadangan_porsi=0.0, tambah=None)}
    khusus = {"9_vs_a": (h["xirr"], a["xirr"], h["xirr"] > a["xirr"]), "10_vs_plasebo_p95": (h["xirr"], p95, h["xirr"] > p95),
              "11_dd_vs_a": (h["dd"], a["dd"], h["dd"] >= a["dd"] - 0.02)}
    standar = {"dasar": dasar["lulus"], **{k: v["lulus"] for k, v in sens.items()}}
    lulus = all(standar.values()) and all(v[2] for v in khusus.values())
    per_tahun = {}
    for x in h["tambahan"]:
        per_tahun[x["tgl"][:4]] = per_tahun.get(x["tgl"][:4], 0) + 1

    def ring(r):
        return {"xirr": f(r["xirr"]), "dd": f(r["dd"]), "nilai_akhir": round(r["nilai_akhir"]), "kas_rata": f(r.get("kas_rata")), "kas_maks": f(r.get("kas_maks")),
                "cad_rata": f(r.get("cad_rata")), "tak_terbeli": r.get("tak_terbeli"), "tambahan": len(r.get("tambahan", []))}

    def krit(s):
        out = {}
        for k, v in s["kriteria"].items():
            if k == "5_tanpa_tahun":
                out[k] = {"h34": f(v[0][0]), "ew": f(v[0][1]), "jii": f(v[0][2]), "lulus": v[2]}
            else:
                out[k] = {"h34": f(v[0]), "pembanding": f(v[1]), "lulus": v[2]}
        return {"kriteria": out, "lulus": s["lulus"], "buang5": s["buang5"], "buang10": s["buang10"], "h34": ring(s["h34"]), "ew": ring(s["ew"])}

    top = sorted(h["laba"].items(), key=lambda x: -x[1])[:10]
    versi = hg.sidik(D.kode, mulai=MULAI, akhir=AKHIR, koleksi="harga_bersih_2020", kolom=("open", "close", "dividen", "saham_tercatat"))
    hasil = {
        "dibuat": datetime.now().isoformat(timespec="seconds"), "periode": "dev 2020-01-02 s/d 2023-12-29", "lulus": lulus,
        "keranjang": h["keranjang"], "tambahan_per_tahun": per_tahun, "tambahan": h["tambahan"],
        "ringkas": {"h34": ring(h), "a": ring(a), "jii": ring(jii), "rd_saham": ring(rd), "ew": ring(dasar["ew"])},
        "twr": {"h34": {str(k): f(v) for k, v in h["twr"].items()}, "ew": {str(k): f(v) for k, v in dasar["ew"]["twr"].items()}, "jii": {str(k): f(v) for k, v in jii["twr"].items()}},
        "plasebo": {"n": PLASEBO, "persentil_h34": round(pers, 1), "p5": f(np.nanpercentile(pl, 5)), "p50": f(np.nanpercentile(pl, 50)), "p95": f(p95)},
        "standar": {"dasar": krit(dasar), **{k: krit(v) for k, v in sens.items()}},
        "khusus": {k: {"h34": f(v[0]), "pembanding": f(v[1]), "lulus": v[2]} for k, v in khusus.items()},
        "laporan": {k: ring(v) for k, v in lap.items()}, "penyumbang10": [[k, round(v)] for k, v in top],
        "delisting_dipegang": h["delist_dipegang"],
        "versi_data": {**versi, "kualitas_data": "cek 2026-11-07: 0 temuan aktif (PPGL Okt 2026 ditahan, di luar dev)"},
    }
    dt.simpan_hasil("h34_dev", json.loads(json.dumps(hasil, default=str)))
    print(json.dumps(hasil["ringkas"], indent=1))
    print("SELESAI")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        utama()
