import numpy as np
import pandas as pd

from backend.paper import mesin_pertumbuhan as mp

PRODUK = {"lokal": [{"id": 1, "nama": "RD Lokal A", "mu": "IDR"}, {"id": 2, "nama": "RD Lokal B", "mu": "IDR"}],
          "global": [{"id": 3, "nama": "RD Global C", "mu": "IDR"}]}


class DataSintetis:
    def __init__(self, hari, rd, etf, aum=None):
        self.hari = [pd.Timestamp(h) for h in hari]
        self.rd_seri = rd
        self.etf_df = etf
        self.aum_nilai = aum or {}
        self.nama = {k: k for k in etf}

    def rd(self, fid, mu, D):
        s = self.rd_seri.get(fid)
        if s is None or D not in s.index:
            return None
        v = s.loc[D]
        return None if pd.isna(v) else float(v)

    def etf(self, kode, D):
        df = self.etf_df.get(kode)
        if df is None or D not in df.index:
            return None
        r = df.loc[D]
        g = lambda k: None if pd.isna(r[k]) else float(r[k])
        return {"close": g("close"), "volume": g("volume"), "nilai": g("nilai"), "nav": g("nav"), "premium": g("premium")}

    def aum(self, kode, D):
        return self.aum_nilai.get(kode)

    def frames(self):
        return self.etf_df


def hari_kerja(awal, akhir, libur=()):
    h = pd.bdate_range(awal, akhir)
    return [x for x in h if x not in set(pd.to_datetime(list(libur)))]


def seri_etf(hari, close=240.0, premium=0.0, nilai=30e6, volume=None):
    idx = pd.DatetimeIndex(hari)
    p = premium(idx) if callable(premium) else np.full(len(idx), premium, dtype=float)
    c = np.full(len(idx), close, dtype=float)
    v = np.full(len(idx), nilai / close) if volume is None else np.asarray(volume(idx) if callable(volume) else volume, dtype=float)
    nav_asli = pd.Series(c / (1 + p), index=idx)
    nav = nav_asli.shift(1).fillna(nav_asli)
    df = pd.DataFrame({"close": c, "volume": v, "nilai": c * v, "nav": nav, "premium": c / nav - 1}, index=idx)
    return df


def seri_rd(hari, awal=1000.0, naik=0.0001):
    return pd.Series([awal * (1 + naik) ** i for i in range(len(hari))], index=pd.DatetimeIndex(hari))


def bangun(hari, etf=None, aum=None, rd_naik=0.0001):
    naik = rd_naik if isinstance(rd_naik, dict) else {i: rd_naik for i in (1, 2, 3)}
    rd = {i: seri_rd(hari, 1000.0 + 100 * i, naik[i]) for i in (1, 2, 3)}
    return DataSintetis(hari, rd, etf if etf is not None else {"AAA": seri_etf(hari)}, aum if aum is not None else {"AAA": 20e9})


def mesin(strategi, data, mulai, **kw):
    m = mp.Mesin(strategi, data, mulai=mulai, **kw)
    m.st["produk"] = PRODUK
    m.st["pilih_awal"] = None
    return m
