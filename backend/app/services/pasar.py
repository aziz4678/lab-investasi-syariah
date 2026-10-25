import time

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as kdb

PERIODE = {"1H": 1, "1M": 5, "1B": 21, "3B": 63}
MIN_NILAI = 1e9
MIN_HARGA = 50
GLOBAL = [("usdidr", "Dolar AS", "Rp"), ("emas", "Emas", "US$"), ("minyak", "Minyak", "US$"), ("sp500", "S&P 500", ""),
          ("em", "Negara berkembang", "US$"), ("vix", "VIX (rasa takut)", "")]
SESI = {"biasa": [[540, 720], [810, 960]], "jumat": [[540, 690], [840, 960]]}
_cache = {}


def _ihsg():
    a = dt.baca("pasar")["ihsg"].dropna()
    b = dt.baca("harian/_ihsg")["ihsg"].dropna()
    s = pd.concat([a, b])
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]


def _saham():
    mentah = {k: v for k, v in dt.baca_banyak("harian", kolom=["close", "adj_close", "volume"]).items() if not k.startswith("_")}
    tutup = pd.DataFrame({k: v["close"] for k, v in mentah.items()})
    adj = pd.DataFrame({k: v["adj_close"] for k, v in mentah.items()})
    vol = pd.DataFrame({k: v["volume"] for k, v in mentah.items()})
    ada = tutup.notna().sum(axis=1)
    hari = ada[ada >= max(10, 0.3 * tutup.shape[1])].index
    return tutup.loc[hari], adj.loc[hari], vol.loc[hari]


def _profil():
    return {d["kode"]: d for d in kdb.koneksi().profil_idx.find({}, {"_id": 0, "kode": 1, "nama": 1, "sektor": 1})}


def _bulat(v, n=2):
    return None if v is None or pd.isna(v) else round(float(v), n)


def hitung():
    tutup, adj, vol = _saham()
    profil = _profil()
    nilai = (tutup * vol).fillna(0)
    tgl = tutup.index[-1]
    rata20 = nilai.iloc[-20:].mean()
    likuid = (rata20 >= MIN_NILAI) & (tutup.iloc[-1] >= MIN_HARGA)

    def baris(k, ret):
        p = profil.get(k, {})
        return {"kode": k, "nama": p.get("nama"), "sektor": p.get("sektor"), "close": _bulat(tutup[k].iloc[-1], 0), "ret": _bulat(ret * 100),
                "nilai": _bulat(nilai[k].iloc[-1], 0)}

    top = {}
    sektor = {}
    for kunci, n in PERIODE.items():
        ret = (adj.iloc[-1] / adj.iloc[-1 - n] - 1).replace([np.inf, -np.inf], np.nan)
        r = ret[likuid].dropna()
        top[kunci] = {"naik": [baris(k, r[k]) for k in r.nlargest(10).index], "turun": [baris(k, r[k]) for k in r.nsmallest(10).index]}
        ss = pd.Series({k: profil.get(k, {}).get("sektor") for k in r.index}).dropna()
        g = r.loc[ss.index].groupby(ss)
        sektor[kunci] = sorted([{"sektor": s, "ret": _bulat(v.median() * 100), "naik": int((v > 0).sum()), "n": int(len(v))} for s, v in g],
                               key=lambda x: -x["ret"])

    kemarin = adj.iloc[-2]
    hari_ini = adj.iloc[-1]
    beda = (hari_ini / kemarin - 1)[hari_ini.notna() & kemarin.notna()]
    total = nilai.sum(axis=1)

    ih = _ihsg()
    ma200 = ih.rolling(200).mean()
    awal_tahun = ih[ih.index < pd.Timestamp(ih.index[-1].year, 1, 1)]
    setahun = ih[ih.index > ih.index[-1] - pd.Timedelta(days=365)]

    ret_ih = ih.pct_change().reindex(total.index[-120:])
    ret_med = adj.pct_change(fill_method=None).median(axis=1).reindex(total.index[-120:])
    arah = [int(np.sign(a if pd.notna(a) else b)) if pd.notna(a) or pd.notna(b) else 0 for a, b in zip(ret_ih, ret_med)]

    glob = []
    ps = dt.baca("pasar")
    for kol, label, satuan in GLOBAL:
        s = ps[kol].dropna()
        if len(s) < 22:
            continue
        glob.append({"kode": kol, "label": label, "satuan": satuan, "nilai": _bulat(s.iloc[-1]), "tgl": s.index[-1].strftime("%Y-%m-%d"),
                     "ret_1h": _bulat((s.iloc[-1] / s.iloc[-2] - 1) * 100), "ret_1b": _bulat((s.iloc[-1] / s.iloc[-22] - 1) * 100)})

    return {
        "tgl": tgl.strftime("%Y-%m-%d"),
        "jumlah_saham": int(tutup.shape[1]),
        "jumlah_likuid": int(likuid.sum()),
        "ihsg": {
            "tgl": [d.strftime("%Y-%m-%d") for d in ih.index], "nilai": [round(float(v), 2) for v in ih.values],
            "terakhir": _bulat(ih.iloc[-1]), "tgl_terakhir": ih.index[-1].strftime("%Y-%m-%d"),
            "ret_1h": _bulat((ih.iloc[-1] / ih.iloc[-2] - 1) * 100),
            "ytd": _bulat((ih.iloc[-1] / awal_tahun.iloc[-1] - 1) * 100) if len(awal_tahun) else None,
            "tinggi_52": _bulat(setahun.max()), "rendah_52": _bulat(setahun.min()),
            "dari_puncak_52": _bulat((ih.iloc[-1] / setahun.max() - 1) * 100),
            "ma200": _bulat(ma200.iloc[-1]), "vs_ma200": _bulat((ih.iloc[-1] / ma200.iloc[-1] - 1) * 100),
        },
        "luas": {"naik": int((beda > 0.0005).sum()), "turun": int((beda < -0.0005).sum()), "tetap": int((beda.abs() <= 0.0005).sum()),
                 "ara_kira": int((beda >= 0.2).sum()), "arb_kira": int((beda <= -0.15).sum())},
        "nilai": {"tgl": [d.strftime("%Y-%m-%d") for d in total.index[-120:]], "nilai": [round(float(v)) for v in total.iloc[-120:]],
                  "arah": arah,
                  "hari_ini": round(float(total.iloc[-1])), "rata20": round(float(total.iloc[-21:-1].mean())),
                  "teraktif": [baris(k, beda.get(k, np.nan)) for k in nilai.iloc[-1].nlargest(10).index]},
        "top": top,
        "sektor": sektor,
        "global": glob,
    }


def ringkasan():
    kunci = (dt.versi("harian/_ihsg"), dt.versi("pasar"), int(time.time() // 900))
    if _cache.get("kunci") != kunci:
        _cache["isi"] = hitung()
        _cache["kunci"] = kunci
    return _cache["isi"]


def _tutup_harian(kode):
    if kode is None:
        return _ihsg()
    bagian = [x["close"] for x in (dt.baca(f"harga/{kode}"), dt.baca(f"harian/{kode}"), dt.baca(f"etf/{kode}")) if x is not None and "close" in x]
    if not bagian:
        return None
    s = pd.concat(bagian).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def _ambil_menit(simbol):
    import logging

    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    d = yf.Ticker(simbol).history(period="5d", interval="1m")
    if d.empty:
        return None
    d.index = d.index.tz_convert("Asia/Jakarta")
    return d


SESI_LUAR = {"AS": ("America/New_York", [[570, 960]], "waktu New York"), "London": ("Europe/London", [[480, 990]], "waktu London")}


def intraday_luar(kode):
    kunci = f"intra_luar_{kode}"
    simpan = _cache.get(kunci)
    if simpan and simpan[0] > time.time() - 60:
        return simpan[1]
    import logging

    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    zona, sesi_jam, ket = SESI_LUAR["London" if kode.endswith(".L") else "AS"]
    d = yf.Ticker(kode).history(period="5d", interval="1m")
    if d.empty:
        return None
    d.index = d.index.tz_convert(zona)
    c = d["Close"].dropna()
    sesi = c.index[-1].date()
    hari = d[d.index.date == sesi]
    hc = hari["Close"].dropna()
    lalu = c[c.index.date < sesi]
    hr = dt.baca(f"etf_luar/{kode}")
    hr = hr["close"].dropna() if hr is not None and "close" in hr else pd.Series(dtype=float)
    hr = hr[hr.index.date < sesi]
    tutup = float(hr.iloc[-1]) if len(hr) else float(lalu.iloc[-1]) if len(lalu) else float(hari["Open"].dropna().iloc[0])
    vol = hari["Volume"].fillna(0)
    isi = {"kode": kode, "sesi": f"{sesi} ({ket})", "zona": zona, "tgl": [t.isoformat() for t in hc.index], "nilai": [round(float(v), 4) for v in hc.values],
           "tutup_kemarin": round(tutup, 4), "sesi_jam": sesi_jam, "terakhir": round(float(hc.iloc[-1]), 4),
           "jam": hc.index[-1].strftime("%H:%M"), "ret": round((float(hc.iloc[-1]) / tutup - 1) * 100, 2),
           "buka": _bulat(hari["Open"].dropna().iloc[0], 4) if hari["Open"].notna().any() else None,
           "tertinggi": _bulat(hari["High"].max(), 4), "terendah": _bulat(hari["Low"].min(), 4),
           "volume": int(vol.sum()), "nilai_transaksi": round(float((hari["Close"] * vol).sum()))}
    _cache[kunci] = (time.time(), isi)
    return isi


def intraday(kode=None):
    kunci = f"intra_{kode or 'ihsg'}"
    simpan = _cache.get(kunci)
    if simpan and simpan[0] > time.time() - 60:
        return simpan[1]
    d = _ambil_menit(f"{kode}.JK" if kode else "^JKSE")
    if d is None:
        return None
    c = d["Close"].dropna()
    sesi = c.index[-1].date()
    hari = d[d.index.date == sesi]
    hc = hari["Close"].dropna()
    harian = _tutup_harian(kode)
    sebelum = harian[harian.index.date < sesi] if harian is not None else []
    tutup = float(sebelum.iloc[-1]) if len(sebelum) else float(c[c.index.date < sesi].iloc[-1])
    vol = hari["Volume"].fillna(0)
    isi = {"kode": kode, "sesi": str(sesi), "tgl": [t.isoformat() for t in hc.index], "nilai": [round(float(v), 2) for v in hc.values],
           "tutup_kemarin": round(tutup, 2), "sesi_jam": SESI["jumat" if sesi.weekday() == 4 else "biasa"], "terakhir": round(float(hc.iloc[-1]), 2),
           "jam": hc.index[-1].strftime("%H:%M"), "ret": round((float(hc.iloc[-1]) / tutup - 1) * 100, 2),
           "buka": _bulat(hari["Open"].dropna().iloc[0]) if hari["Open"].notna().any() else None,
           "tertinggi": _bulat(hari["High"].max()), "terendah": _bulat(hari["Low"].min()),
           "volume": int(vol.sum()) if kode else None, "nilai_transaksi": round(float((hari["Close"] * vol).sum())) if kode else None}
    _cache[kunci] = (time.time(), isi)
    return isi


def harga_kini(kode_list):
    kode_list = sorted({k for k in kode_list if k})
    if not kode_list:
        return {}
    kunci = "kini_" + ",".join(kode_list)
    simpan = _cache.get(kunci)
    if simpan and simpan[0] > time.time() - 60:
        return simpan[1]
    import logging

    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    mentah = yf.download([f"{k}.JK" for k in kode_list], period="5d", interval="1m", group_by="ticker", progress=False, threads=True)
    hasil = {}
    for k in kode_list:
        try:
            c = (mentah[f"{k}.JK"] if len(kode_list) > 1 or isinstance(mentah.columns, pd.MultiIndex) else mentah)["Close"].dropna()
        except KeyError:
            continue
        if c.empty:
            continue
        c.index = c.index.tz_convert("Asia/Jakarta")
        sesi = c.index[-1].date()
        harian = _tutup_harian(k)
        sebelum = harian[harian.index.date < sesi] if harian is not None else []
        tutup = float(sebelum.iloc[-1]) if len(sebelum) else None
        h = float(c.iloc[-1])
        hasil[k] = {"harga": h, "jam": c.index[-1].strftime("%H:%M"), "sesi": str(sesi), "tutup_kemarin": tutup,
                    "ret": round((h / tutup - 1) * 100, 2) if tutup else None}
    _cache[kunci] = (time.time(), hasil)
    return hasil
