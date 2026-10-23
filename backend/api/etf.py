import numpy as np
import pandas as pd

from backend.api import etf_info as info
from backend.api import reksadana as rdn
from backend.db import data as dt
from backend.db import koneksi as d

BATAS_LONJAKAN = 0.20


def bersihkan(h):
    c = h["close"]
    median = c.rolling(5, center=True, min_periods=3).median()
    buang = (c / median - 1).abs() > BATAS_LONJAKAN
    return h[~buang], int(buang.sum())


JENIS = {"saham": "Saham Indonesia", "emas": "Emas", "global": "Global (dolar AS)"}


def cagr(s, tahun):
    if s.empty:
        return None
    t = s.index[-1] - pd.DateOffset(years=tahun)
    awal = s[s.index <= t]
    if awal.empty:
        return None
    return ((s.iloc[-1] / awal.iloc[-1]) ** (1 / tahun) - 1) * 100


def metrik_bursa(kode):
    h = dt.baca(f"etf/{kode}")
    if h is None or h.empty:
        return {}
    h, dibuang = bersihkan(h)
    c = h["close"]
    nilai = (h["close"] * h["volume"]).tail(20)
    tahun = (c.index[-1] - c.index[0]).days / 365.25
    hari_dagang = (h["volume"].tail(60) > 0).mean() * 100 if len(h) >= 5 else None
    return {
        "bursa_mulai": c.index[0].strftime("%Y-%m-%d"), "bursa_sampai": c.index[-1].strftime("%Y-%m-%d"), "harga": float(c.iloc[-1]),
        "cagr_3th": cagr(c, 3), "cagr_5th": cagr(c, 5), "cagr_semua": ((c.iloc[-1] / c.iloc[0]) ** (1 / tahun) - 1) * 100 if tahun >= 1 else None,
        "dd_semua": float((c / c.cummax() - 1).min() * 100), "nilai_transaksi": float(nilai.mean()) if len(nilai) else None,
        "hari_dagang": float(hari_dagang) if hari_dagang is not None else None, "tahun_data": round(tahun, 1), "lonjakan_dibuang": dibuang,
    }


def daftar():
    db = d.koneksi()
    peta = {x["_id"]: x for x in db.rd_etf.find({})}
    data = [x for x in rdn.daftar()["data"] if x["id"] in peta or x["kategori"] == "etf"]
    hasil = []
    for x in data:
        m = peta.get(x["id"], {})
        kode = m.get("kode")
        jenis = m.get("jenis") or ("emas" if "EMAS" in x["nama"].upper() or "GOLD" in x["nama"].upper() else "global" if x["mata_uang"] == "USD" else "saham")
        isi = info.KETERANGAN.get(kode) if kode else None
        if not isi:
            isi = {"emas": "Isinya emas. Harganya mengikuti harga emas dalam rupiah.", "global": "Saham syariah luar negeri, dalam dolar AS, tapi dibeli di BEI.",
                   "saham": "Saham syariah Indonesia, meniru sebuah indeks."}.get(jenis)
        hasil.append({**x, "kode": kode, "jenis": jenis, "jenis_label": JENIS.get(jenis, jenis), "cocok": m.get("cocok"), "isi": isi, **(metrik_bursa(kode) if kode else {})})
    hasil.sort(key=lambda r: (list(JENIS).index(r["jenis"]) if r["jenis"] in JENIS else 9, -(r.get("aum") or 0)))
    return rdn.bersih({"data": hasil, "jenis": JENIS})


def grafik(kode):
    h = dt.baca(f"etf/{kode}")
    if h is None:
        return None
    h, _ = bersihkan(h)
    ih = None
    try:
        from backend.api.emiten import baca_ihsg
        i = baca_ihsg().reindex(h.index, method="ffill")
        ih = (i / i.dropna().iloc[0] * h["close"].iloc[0]).round(2).tolist() if i.notna().any() else None
    except Exception:
        ih = None
    return rdn.bersih({"tgl": [t.strftime("%Y-%m-%d") for t in h.index], "close": h["close"].round(2).tolist(),
                       "volume": h["volume"].fillna(0).astype(float).tolist(), "ihsg": ih})


AWAL_BANDING = pd.Timestamp("2020-01-02")


def cagr_sejak(s, mulai):
    x = s[s.index >= mulai]
    if len(x) < 2 or x.index[0] > mulai + pd.Timedelta(days=31):
        return None
    tahun = (x.index[-1] - x.index[0]).days / 365.25
    return ((x.iloc[-1] / x.iloc[0]) ** (1 / tahun) - 1) * 100 if tahun >= 1 else None


def total(h):
    return (h["adj_close"] if "adj_close" in h and h["adj_close"].notna().any() else h["close"]).dropna()


def daftar_luar():
    db = d.koneksi()
    cache_kurs = {}

    def kurs_dari(mu):
        mu = {"GBp": "GBP", "GBX": "GBP"}.get(mu, mu or "USD")
        if mu not in cache_kurs:
            k = dt.baca(f"kurs/{mu}")
            cache_kurs[mu] = k["close"].dropna() if k is not None else (dt.baca("pasar")["usdidr"].dropna() if mu == "USD" else None)
        return cache_kurs[mu]

    hasil = []
    for m in db.etf_luar.find({}, {"_id": 0}):
        h = dt.baca(f"etf_luar/{m['kode']}")
        if h is None or h.empty:
            continue
        s = total(h)
        kurs = kurs_dari(m.get("mata_uang"))
        rp = (s * kurs.reindex(s.index, method="ffill")).dropna() if kurs is not None else pd.Series(dtype=float)
        r = s.pct_change().dropna()
        tahun = (s.index[-1] - s.index[0]).days / 365.25
        hasil.append({**m, "isi": info.KETERANGAN.get(m["kode"]), "domisili": "Irlandia" if m["kode"].endswith(".L") else "Amerika Serikat",
                      **{k: v for k, v in dividen_info(h).items() if k != "dividen_riwayat"},
                      "harga": float(h["close"].iloc[-1]), "tgl": s.index[-1].strftime("%Y-%m-%d"),
                      "ret_1th": cagr(s, 1), "cagr_3th": cagr(s, 3), "cagr_5th": cagr(s, 5), "cagr_10th": cagr(s, 10),
                      "cagr_2020": cagr_sejak(s, AWAL_BANDING), "cagr_semua": ((s.iloc[-1] / s.iloc[0]) ** (1 / tahun) - 1) * 100 if tahun >= 1 else None,
                      "tahun_data": round(tahun, 1), "dd_semua": float((s / s.cummax() - 1).min() * 100),
                      "dd_2020": float((s[s.index >= AWAL_BANDING] / s[s.index >= AWAL_BANDING].cummax() - 1).min() * 100) if s.index[0] <= AWAL_BANDING + pd.Timedelta(days=31) else None,
                      "vol": float(r.tail(756).std() * np.sqrt(252) * 100), "ret_1th_rp": cagr(rp, 1), "cagr_2020_rp": cagr_sejak(rp, AWAL_BANDING),
                      "biaya": m["biaya"] * 1 if m.get("biaya") is not None else None, "yield": m["yield"] * 100 if m.get("yield") is not None else None,
                      "mulai": m["mulai"].strftime("%Y-%m-%d") if m.get("mulai") else None})
    hasil.sort(key=lambda x: (not x["syariah"], -(x.get("aum") or 0)))
    return rdn.bersih({"data": hasil, "awal_banding": AWAL_BANDING.strftime("%Y-%m-%d"), "wilayah_ket": info.WILAYAH_KET, "pajak": info.PAJAK})


def grafik_luar(kode, banding="SPY"):
    h = dt.baca(f"etf_luar/{kode}")
    if h is None:
        return None
    s = total(h)
    b = None
    if banding and banding != kode:
        hb = dt.baca(f"etf_luar/{banding}")
        if hb is not None:
            sb = total(hb).reindex(s.index, method="ffill")
            if sb.notna().any():
                i = sb.first_valid_index()
                b = (sb / sb[i] * s[i]).round(2).tolist()
    harga = h["close"].reindex(s.index).ffill()
    return rdn.bersih({"tgl": [t.strftime("%Y-%m-%d") for t in s.index], "nilai": s.round(2).tolist(), "harga": harga.round(2).tolist(),
                       "banding": b, "banding_kode": banding if b else None})


PERIODE = {"1y": 1, "3y": 3, "5y": 5, "10y": 10, "maks": None}


def dividen_info(h):
    if h is None or "dividends" not in h:
        return {}
    dv = h["dividends"].fillna(0)
    dv = dv[dv > 0]
    akhir = h.index[-1]
    d12 = dv[dv.index > akhir - pd.Timedelta(days=365)]
    harga = float(h["close"].iloc[-1])
    tahun = (akhir - h.index[0]).days / 365.25
    n = len(d12)
    label = info.frekuensi(n) if (n or tahun >= 1) else "Belum ada data"
    return {
        "dividen_frek": label, "dividen_n12": n, "dividen_12bln": float(d12.sum()) if n else 0.0,
        "dividen_yield12": float(d12.sum() / harga * 100) if n and harga else 0.0,
        "dividen_bulan": sorted({int(t.month) for t in d12.index}),
        "dividen_terakhir": dv.index[-1].strftime("%Y-%m-%d") if len(dv) else None,
        "dividen_riwayat": [{"tgl": t.strftime("%Y-%m-%d"), "nilai": round(float(v), 4)} for t, v in dv.tail(12).items()][::-1],
    }


def _seri_luar(kode):
    h = dt.baca(f"etf_luar/{kode}")
    return None if h is None or h.empty else h


def detail_luar(kode):
    data = daftar_luar()["data"]
    x = next((r for r in data if r["kode"] == kode), None)
    if x is None:
        return None
    m = d.koneksi().etf_luar.find_one({"_id": kode}) or {}
    h = _seri_luar(kode)
    sektor = sorted(({"nama": info.SEKTOR_ID.get(k, k), "bobot": v} for k, v in (m.get("sektor") or {}).items() if v > 0.05), key=lambda z: -z["bobot"])
    aset = sorted(({"nama": info.ASET_ID.get(k, k), "bobot": v} for k, v in (m.get("aset") or {}).items() if v > 0.05), key=lambda z: -z["bobot"])
    pajak = info.PAJAK["London" if x["bursa"] == "London" else "AS"]
    hasil = {**x, **dividen_info(h), "isi_top": m.get("isi_top") or [], "sektor_bobot": sektor, "aset_bobot": aset,
             "cocok": info.COCOK.get(x["kelas"]), "wilayah_ket": info.WILAYAH_KET.get(x["wilayah"]),
             "pajak": {**pajak, "indonesia": info.PAJAK["indonesia"], "catatan": info.PAJAK["catatan"]}}
    from backend.api import kesimpulan
    hasil["kesimpulan"] = kesimpulan.etf_luar(hasil, data)
    return rdn.bersih(hasil)


def pilihan():
    db = d.koneksi()
    hasil = [{"kode": m["kode"], "nama": m["nama"], "syariah": m["syariah"], "sumber": "luar", "mata_uang": m.get("mata_uang", "USD"), "wilayah": m.get("wilayah")}
             for m in db.etf_luar.find({}, {"kode": 1, "nama": 1, "syariah": 1, "mata_uang": 1, "wilayah": 1})]
    for m in db.rd_etf.find({"kode": {"$ne": None}}, {"kode": 1, "nama": 1}):
        hasil.append({"kode": m["kode"], "nama": m["nama"], "syariah": True, "sumber": "idx", "mata_uang": "IDR", "wilayah": "Indonesia"})
    hasil.sort(key=lambda r: (not r["syariah"], r["sumber"] != "idx", r["kode"]))
    return hasil


def _seri_banding(kode, rupiah):
    h = _seri_luar(kode)
    if h is not None:
        s = total(h)
        if rupiah:
            mu = (d.koneksi().etf_luar.find_one({"_id": kode}, {"mata_uang": 1}) or {}).get("mata_uang") or "USD"
            mu = {"GBp": "GBP", "GBX": "GBP"}.get(mu, mu)
            k = dt.baca(f"kurs/{mu}")
            kurs = k["close"].dropna() if k is not None else dt.baca("pasar")["usdidr"].dropna()
            s = (s * kurs.reindex(s.index, method="ffill")).dropna()
        return s
    h = dt.baca(f"etf/{kode}")
    if h is None or h.empty:
        return None
    h, _ = bersihkan(h)
    return h["close"].dropna()


def banding(kode_list, periode="5y", rupiah=False):
    seri = {}
    for k in kode_list[:4]:
        s = _seri_banding(k, rupiah)
        if s is not None and len(s) > 20:
            seri[k] = s[~s.index.duplicated()]
    if len(seri) < 2:
        return {"error": "Pilih minimal 2 ETF yang punya data harga."}
    df = pd.concat(seri, axis=1).sort_index().ffill()
    mulai = max(s.index[0] for s in seri.values())
    akhir = df.index[-1]
    th = PERIODE.get(periode)
    if th:
        mulai = max(mulai, akhir - pd.DateOffset(years=th))
    df = df[df.index >= mulai].dropna()
    if len(df) < 10:
        return {"error": "Periode bersama terlalu pendek."}
    norm = df / df.iloc[0] * 100
    tampil = norm.resample("W").last().dropna() if len(norm) > 900 else norm
    mingguan = df.resample("W").last().pct_change().dropna()
    tahun = (df.index[-1] - df.index[0]).days / 365.25
    metrik = {}
    for k in df.columns:
        s = df[k]
        tahunan = s.resample("YE").last()
        per_tahun = (tahunan / tahunan.shift(1) - 1).dropna() * 100
        metrik[k] = {
            "total": float((s.iloc[-1] / s.iloc[0] - 1) * 100),
            "per_tahun": float(((s.iloc[-1] / s.iloc[0]) ** (1 / tahun) - 1) * 100) if tahun >= 1 else None,
            "dd": float((s / s.cummax() - 1).min() * 100),
            "vol": float(mingguan[k].std() * np.sqrt(52) * 100) if len(mingguan) > 5 else None,
            "tahun_terbaik": float(per_tahun.max()) if len(per_tahun) else None,
            "tahun_terburuk": float(per_tahun.min()) if len(per_tahun) else None,
            "tahun_naik": int((per_tahun > 0).sum()), "tahun_dihitung": int(len(per_tahun)),
        }
    kor = mingguan.corr().round(2)
    pil = {p["kode"]: p for p in pilihan()}
    return rdn.bersih({"tgl": [t.strftime("%Y-%m-%d") for t in tampil.index], "seri": {k: tampil[k].round(2).tolist() for k in df.columns},
                       "metrik": metrik, "korelasi": {a: {b: float(kor.loc[a, b]) for b in kor.columns} for a in kor.index},
                       "mulai": df.index[0].strftime("%Y-%m-%d"), "akhir": df.index[-1].strftime("%Y-%m-%d"), "tahun": round(tahun, 1),
                       "info": {k: pil.get(k, {"kode": k}) for k in df.columns}, "rupiah": rupiah})
