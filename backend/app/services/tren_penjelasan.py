import numpy as np
import pandas as pd

from backend.db import koneksi as d
from backend.research import screener as sc
from backend.research import uji_tren as ut

DB = d.koneksi()
SEBELUM = 70
SESUDAH = 12
_cache = {}


def _harga(ticker, versi):
    x = sc.baca_harga([ticker]).get(ticker)
    if x is None:
        return None
    if versi == "h11a_dev":
        x = x[x.index <= f"{ut.DEV[1]}-12-31"]
    else:
        x = x[x.index >= "2018-01-01"]
    pasar = pd.DataFrame({"ihsg_atas": 0.0, "ihsg_mom20": 0.0}, index=x.index)
    return ut.tambah_fitur(sc.fitur_ticker(x, pasar))


def _jalur(tr, versi):
    x = _harga(tr["ticker"], versi)
    if x is None or pd.Timestamp(tr["tgl_sinyal"]) not in x.index:
        return None
    i = x.index.get_loc(pd.Timestamp(tr["tgl_sinyal"]))
    o, c, atr = x["open"].to_numpy(float), x["close"].to_numpy(float), x["atr"].to_numpy(float)
    f = float(tr["harga_beli"] / o[i + 1])
    stop = o[i + 1] - ut.MULT_ATR * atr[i]
    stop_awal = stop
    tertinggi = c[i + 1]
    jalur_stop = {}
    j = i + 1
    while True:
        jalur_stop[j] = stop
        if c[j] < stop:
            k = j + 1
            break
        tertinggi = max(tertinggi, c[j])
        if np.isfinite(atr[j]):
            stop = max(stop, tertinggi - ut.MULT_ATR * atr[j])
        if j >= len(x) - 2:
            return None
        j += 1
    if x.index[k] != pd.Timestamp(tr["tgl_jual"]):
        return None
    a, b = max(0, i - SEBELUM), min(len(x) - 1, k + SESUDAH)
    r = lambda v: None if v is None or not np.isfinite(v) else round(float(v) * f, 1)
    puncak = max(range(i + 1, k), key=lambda q: c[q])
    return {
        "ticker": tr["ticker"], "net": tr["net"], "kotor": tr["kotor"], "hari": tr["hari"],
        "tgl": [t.strftime("%Y-%m-%d") for t in x.index[a:b + 1]],
        "close": [r(c[q]) for q in range(a, b + 1)],
        "maks250": [r(x["maks250"].iloc[q]) if q <= i else None for q in range(a, b + 1)],
        "stop": [r(jalur_stop[q]) if q in jalur_stop else None for q in range(a, b + 1)],
        "titik": {"sinyal": i - a, "beli": i + 1 - a, "jual_sinyal": j - a, "jual": k - a, "puncak": puncak - a},
        "nilai": {
            "close_sinyal": r(c[i]), "maks250_sinyal": r(x["maks250"].iloc[i]), "harga_beli": tr["harga_beli"],
            "stop_awal": r(stop_awal), "stop_awal_pct": round(float(1 - stop_awal / o[i + 1]) * 100, 1), "atr_sinyal": r(atr[i]),
            "puncak": r(c[puncak]), "stop_akhir": r(jalur_stop[j]), "close_jual": r(c[j]), "harga_jual": tr["harga_jual"],
        },
    }


def _pilih(trade, versi, syarat, target):
    calon = sorted((t for t in trade if syarat(t)), key=lambda t: abs(t["net"] - target))
    for t in calon[:15]:
        j = _jalur(t, versi)
        if j:
            return j
    return None


def contoh(versi):
    ring = DB.backtest_ringkasan.find_one({"versi": versi}, {"_id": 0, "dibuat": 1, "rata_menang": 1, "rata_kalah": 1})
    if not ring:
        return None
    kunci = (versi, str(ring.get("dibuat")))
    if kunci in _cache:
        return _cache[kunci]
    trade = list(DB.backtest_trade.find({"versi": versi, "dipilih": True, "status": "selesai"},
                                        {"_id": 0, "ticker": 1, "tgl_sinyal": 1, "tgl_jual": 1, "harga_beli": 1, "harga_jual": 1,
                                         "hari": 1, "net": 1, "kotor": 1}))
    isi = {
        "tp": _pilih(trade, versi, lambda t: 20 <= t["net"] <= 60 and 25 <= t["hari"] <= 80, ring.get("rata_menang") or 35),
        "cl": _pilih(trade, versi, lambda t: t["net"] < 0 and 5 <= t["hari"] <= 25, ring.get("rata_kalah") or -9),
    }
    _cache[kunci] = isi
    return isi
