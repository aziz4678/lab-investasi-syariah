import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

PERIODE = {"dev": ("h11a_dev", "2011-01", "2019-12", "2011-2019 (dev)"),
           "2020": ("h11a_2020", "2020-01", None, "2020-2026")}
PORSI = list(range(0, 101, 10))
_CACHE = {}


def _versi():
    r = d.koneksi().backtest_ringkasan.find_one({}, {"_id": 0, "dibuat": 1, "waktu": 1}, sort=[("_id", -1)]) or {}
    return (str(r), dt.versi("makro/bunga_antarbank"), dt.versi("indeks/JKII"), dt.versi("makro/inflasi"))


def _tren(versi, mulai, akhir):
    rows = list(d.koneksi().backtest_ekuitas.find({"versi": versi}, {"_id": 0, "bulan": 1, "return": 1}).sort("bulan", 1))
    s = pd.Series({pd.Period(r["bulan"], "M"): r["return"] / 100 for r in rows})
    s = s[s.index >= pd.Period(mulai, "M")]
    return s[s.index <= pd.Period(akhir, "M")] if akhir else s


def _inti(bulan):
    b = dt.baca("makro/bunga_antarbank")["nilai"]
    b.index = b.index.to_period("M")
    b = b.reindex(pd.period_range(min(b.index.min(), bulan[0]), bulan[-1], freq="M")).ffill()
    return pd.Series([(1 + (b[m] - 1.5) / 100) ** (1 / 12) - 1 for m in bulan], index=bulan)


def _jii(bulan):
    c = dt.baca("indeks/JKII")["close"]
    akhir = c.groupby(c.index.to_period("M")).last()
    r = akhir / akhir.shift(1) - 1 + 0.005 / 12
    return r.reindex(bulan).fillna(0.0)


def _inflasi(bulan):
    s = dt.baca("makro/inflasi")["nilai"]
    s.index = s.index.to_period("M")
    s = s.reindex(bulan).dropna()
    return float(s.mean()) if len(s) else None


def _campur(rt, ri, p):
    w = p / 100
    a, b = w, 1 - w
    ek, tahun = [], None
    for m in rt.index:
        if tahun is not None and m.year != tahun:
            tot = a + b
            a, b = tot * w, tot * (1 - w)
        tahun = m.year
        a *= 1 + rt[m]
        b *= 1 + ri[m]
        ek.append(a + b)
    return pd.Series(ek, index=rt.index)


def _metrik(e):
    awal = pd.concat([pd.Series([1.0]), pd.Series(e.to_numpy())])
    th = len(e) / 12
    cagr = (awal.iloc[-1] ** (1 / th) - 1) * 100
    dd = float((awal / awal.cummax() - 1).min() * 100)
    th_akhir = e.groupby(e.index.year).last()
    th_awal = th_akhir.shift(1)
    th_awal.iloc[0] = 1.0
    per_th = (th_akhir / th_awal - 1) * 100
    penuh = [(e.index.year == y).sum() == 12 for y in per_th.index]
    lengkap = per_th[penuh]
    th_min = int(per_th.idxmin())
    return {"cagr": round(cagr, 2), "dd": round(dd, 1), "terburuk": round(float(per_th.min()), 1),
            "th_terburuk": str(th_min) + ("" if penuh[list(per_th.index).index(th_min)] else "*"), "th_negatif": int((lengkap < 0).sum()), "th_lengkap": int(len(lengkap)),
            "per_tahun": {str(k): round(float(v), 1) for k, v in per_th.items()}}


def _hitung(kunci):
    hasil = {}
    for id_, (versi, mulai, akhir, label) in PERIODE.items():
        rt = _tren(versi, mulai, akhir)
        if rt.empty:
            continue
        ri = _inti(rt.index)
        rj = _jii(rt.index)
        baris = []
        kurva = {}
        for p in PORSI:
            e = _campur(rt, ri, p)
            baris.append({"porsi": p, **_metrik(e)})
            kurva[p] = [round(float(x) * 100, 1) for x in e]
        ej = (1 + rj).cumprod()
        inf = _inflasi(rt.index)
        hasil[id_] = {"label": label, "dari": str(rt.index[0]), "sampai": str(rt.index[-1]), "baris": baris,
                      "bulan": [str(m) for m in rt.index], "kurva": kurva,
                      "jii": {**_metrik(ej), "kurva": [round(float(x) * 100, 1) for x in ej]},
                      "inflasi": round(inf, 2) if inf is not None else None,
                      "patokan_inti": round(inf + 1.5, 2) if inf is not None else None}
    return hasil


def hitung():
    kunci = _versi()
    if kunci not in _CACHE:
        _CACHE.clear()
        _CACHE[kunci] = _hitung(kunci)
    return {"periode": _CACHE[kunci], "porsi": PORSI}
