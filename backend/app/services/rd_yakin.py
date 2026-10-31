from functools import lru_cache

import numpy as np
import pandas as pd

from backend.app.services import penyebab
from backend.app.services import reksadana as rd
from backend.db import data as dt
from backend.db import koneksi as d

KRISIS = [("Taper tantrum 2013", "2013-04-30", "2013-08-31"), ("Rupiah melemah 2018", "2018-01-31", "2018-10-31"),
          ("Covid 2020", "2020-01-31", "2020-03-31"), ("Suku bunga naik 2022", "2021-12-31", "2022-10-31")]
JENDELA = {1: 12, 3: 36, 5: 60}
MIN_TAHUN_PROKSI = 10
BATAS_PROKSI = 8
MIN_KORELASI = 0.7
MIN_BULAN_KORELASI = 24
MIN_TURUN = -2
MAKS_SELISIH_PROKSI = 2
PAJAK_DEPOSITO = 0.2
KATEGORI_BUNGA = {"pasar_uang", "pendapatan_tetap", "terproteksi"}
KATEGORI_SAHAM = {"saham", "indeks", "campuran", "etf"}


@lru_cache(maxsize=2)
def _bulanan(kunci):
    db = d.koneksi()
    oj = pd.DataFrame(list(db.rd_ojk.find({"fund": {"$ne": None}}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    n = rd.nav()
    kolom = {}
    if not oj.empty:
        oj["tgl"] = pd.to_datetime(oj["tgl"])
        for f, g in oj.groupby("fund"):
            kolom[int(f)] = g.set_index("tgl")["nav"].sort_index()
    for f in n.columns:
        s = n[f].dropna()
        if s.empty:
            continue
        a = kolom.get(int(f))
        kolom[int(f)] = pd.concat([a[a.index < s.index[0]], s]) if a is not None else s
    hasil = {f: s[s > 0].resample("ME").last().dropna() for f, s in kolom.items() if len(s)}
    return pd.DataFrame(hasil).sort_index()


def bulanan():
    return _bulanan(rd.versi())


def ret_tahun(m):
    akhir = m.groupby(m.index.year).last()
    return (akhir / akhir.shift(1) - 1) * 100


def inflasi():
    x = dt.baca("makro/inflasi")
    return x["nilai"].dropna().sort_index() if x is not None else pd.Series(dtype=float)


def patokan(kategori, mata_uang):
    if mata_uang == "USD" or kategori == "global":
        s = dt.baca("pasar")["sp500"].dropna()
        return "S&P 500", "harga indeks saham AS, bukan syariah, tanpa dividen", s, "harga"
    if kategori in KATEGORI_SAHAM:
        s = dt.baca("indeks/JKII")["close"].dropna()
        return "JII", "harga indeks saham syariah, tanpa dividen", s, "harga"
    if kategori in KATEGORI_BUNGA:
        s = dt.baca("makro/bunga_antarbank")["nilai"].dropna()
        return "Deposito (perkiraan)", f"bunga antarbank rata-rata setahun, dipotong pajak {PAJAK_DEPOSITO * 100:.0f}%", s, "bunga"
    return None, None, None, None


def nilai_patokan(s, jenis, th, sampai, berjalan):
    if s is None:
        return None
    if jenis == "harga":
        awal = s[s.index < pd.Timestamp(year=th, month=1, day=1)]
        akhir = s[s.index <= (sampai if berjalan else pd.Timestamp(year=th, month=12, day=31))]
        if awal.empty or akhir.empty or akhir.index[-1].year != th:
            return None
        return float((akhir.iloc[-1] / awal.iloc[-1] - 1) * 100)
    x = s[s.index.year == th]
    if x.empty:
        return None
    porsi = sampai.dayofyear / 365.25 if berjalan else 1
    return float(x.mean() * (1 - PAJAK_DEPOSITO) * porsi)


def nilai_inflasi(inf, th, sampai, berjalan):
    x = inf[inf.index.year == th]
    if x.empty:
        return None
    if berjalan:
        return float(x.iloc[-1] * sampai.dayofyear / 365.25)
    return float(x.iloc[-1]) if x.index[-1].month == 12 else None


def per_tahun(m, sampai, median_kat, inf, pat, jenis):
    r = ret_tahun(m).dropna()
    hasil = []
    for th, v in r.items():
        berjalan = bool(th == sampai.year and sampai.month < 12)
        hasil.append({"tahun": int(th), "ret": float(v), "berjalan": berjalan,
                      "kategori": float(median_kat[th]) if th in median_kat.index and pd.notna(median_kat[th]) else None,
                      "inflasi": nilai_inflasi(inf, th, sampai, berjalan),
                      "patokan": nilai_patokan(pat, jenis, th, sampai, berjalan)})
    return hasil


def jendela(m):
    hasil = []
    for th, n in JENDELA.items():
        if len(m) <= n + 3:
            continue
        r = (m / m.shift(n) - 1).dropna()
        tahunan = ((1 + r) ** (1 / th) - 1) * 100
        hasil.append({"tahun": th, "n": int(len(r)), "untung": float((r > 0).mean() * 100), "median": float(tahunan.median()),
                      "terburuk": float(tahunan.min()), "terbaik": float(tahunan.max())})
    return hasil


def penurunan(m, n=3):
    dd = m / m.cummax() - 1
    episode, mulai = [], None
    for t, v in dd.items():
        if v < 0 and mulai is None:
            mulai = t
        elif v >= 0 and mulai is not None:
            episode.append((mulai, t))
            mulai = None
    if mulai is not None:
        episode.append((mulai, None))
    hasil = []
    for a, b in episode:
        bagian = dd[(dd.index >= a) & ((dd.index < b) if b is not None else True)]
        dalam = float(bagian.min() * 100)
        if dalam > MIN_TURUN:
            continue
        dasar = bagian.idxmin()
        awal = m[m.index < a].index[-1] if (m.index < a).any() else a
        hasil.append({"puncak": awal.strftime("%Y-%m-%d"), "dasar": dasar.strftime("%Y-%m-%d"), "turun": dalam,
                      "pulih": b.strftime("%Y-%m-%d") if b is not None else None,
                      "bulan_turun": round((dasar - awal).days / 30.44, 1),
                      "bulan_pulih": round((b - dasar).days / 30.44, 1) if b is not None else None})
    return sorted(hasil, key=lambda x: x["turun"])[:n]


def krisis(m):
    hasil = []
    for nama, a, b in KRISIS:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if m.index[0] > a or m.index[-1] < b:
            hasil.append({"nama": nama, "turun": None})
            continue
        hasil.append({"nama": nama, "turun": float((m.asof(b) / m.asof(a) - 1) * 100)})
    return hasil


def cagr(m):
    th = (m.index[-1] - m.index[0]).days / 365.25
    return float(((m.iloc[-1] / m.iloc[0]) ** (1 / th) - 1) * 100) if th >= 1 else None


def tahun_data(m):
    return (m.index[-1] - m.index[0]).days / 365.25


def proksi(fid, m, sekelompok, nama):
    if tahun_data(m) >= BATAS_PROKSI:
        return None
    b = bulanan()
    r = m.pct_change().dropna()
    terbaik = None
    for f in sekelompok:
        if f == fid or f not in b.columns:
            continue
        s = b[f].dropna()
        if len(s) < 2 or tahun_data(s) < MIN_TAHUN_PROKSI:
            continue
        gabung = pd.concat([r, s.pct_change()], axis=1, join="inner").dropna()
        if len(gabung) < MIN_BULAN_KORELASI:
            continue
        k = float(gabung.iloc[:, 0].corr(gabung.iloc[:, 1]))
        th = len(gabung) / 12
        selisih = ((1 + gabung.iloc[:, 0]).prod() ** (1 / th) - (1 + gabung.iloc[:, 1]).prod() ** (1 / th)) * 100
        if abs(selisih) > MAKS_SELISIH_PROKSI:
            continue
        if np.isfinite(k) and (terbaik is None or k > terbaik[0]):
            terbaik = (k, f, s)
    if terbaik is None or terbaik[0] < MIN_KORELASI:
        return None
    k, f, s = terbaik
    tahunan = ret_tahun(s).dropna()
    lengkap = tahunan[tahunan.index < s.index[-1].year] if s.index[-1].month < 12 else tahunan
    return {"id": int(f), "nama": nama.get(f), "korelasi": k, "mulai": s.index[0].strftime("%Y-%m-%d"), "tahun": round(tahun_data(s), 1),
            "cagr": cagr(s), "dd": float((s / s.cummax() - 1).min() * 100),
            "tahun_terburuk": {"tahun": int(lengkap.idxmin()), "ret": float(lengkap.min())} if len(lengkap) else None,
            "tahun_naik": int((lengkap > 0).sum()), "tahun_dihitung": int(len(lengkap)),
            "jendela": jendela(s), "krisis": krisis(s)}


def keyakinan(fid, s, kategori, mata_uang):
    s = s[s > 0].dropna() if s is not None else None
    if s is None or len(s) < 2:
        return None
    m = s.resample("ME").last().dropna()
    if len(m) < 13:
        return None
    sampai = s.index[-1]
    db = d.koneksi()
    produk = list(db.rd_produk.find({"tidak_aktif": {"$ne": True}, "kategori": kategori, "mata_uang": mata_uang}, {"nama": 1}))
    bagi = {x["_id"] for x in db.rd_detail.find({"dividen.0": {"$exists": True}}, {"_id": 1})}
    nama = {p["_id"]: p["nama"] for p in produk if p["_id"] not in bagi or p["_id"] == fid}
    b = bulanan()
    ada = [f for f in nama if f in b.columns]
    tahunan = b[ada].groupby(b.index.year).last() if ada else pd.DataFrame()
    ret_kat = tahunan / tahunan.shift(1) - 1
    median_kat = (ret_kat.median(axis=1, skipna=True) * 100) if len(ret_kat) else pd.Series(dtype=float)
    jumlah_kat = ret_kat.notna().sum(axis=1) if len(ret_kat) else pd.Series(dtype=int)
    label, ket, pat, jenis = patokan(kategori, mata_uang)
    inf = inflasi()
    pt = per_tahun(m, sampai, median_kat, inf, pat, jenis)
    for x in pt:
        x["jumlah_kategori"] = int(jumlah_kat.get(x["tahun"], 0)) if len(jumlah_kat) else 0
    lengkap = [x for x in pt if not x["berjalan"]]
    return rd.bersih({
        "mulai": m.index[0].strftime("%Y-%m-%d"), "sampai": sampai.strftime("%Y-%m-%d"), "tahun": round(tahun_data(m), 1),
        "per_tahun": pt, "patokan": {"label": label, "ket": ket} if label else None,
        "di_atas_inflasi": sum(1 for x in lengkap if x["inflasi"] is not None and x["ret"] > x["inflasi"]),
        "di_atas_kategori": sum(1 for x in lengkap if x["kategori"] is not None and x["ret"] > x["kategori"]),
        "di_atas_patokan": sum(1 for x in lengkap if x["patokan"] is not None and x["ret"] > x["patokan"]),
        "tahun_inflasi": sum(1 for x in lengkap if x["inflasi"] is not None), "tahun_kategori": sum(1 for x in lengkap if x["kategori"] is not None),
        "tahun_patokan": sum(1 for x in lengkap if x["patokan"] is not None),
        "jendela": jendela(m), "penurunan": penurunan(m), "krisis": krisis(m), "cagr": cagr(m),
        "proksi": proksi(fid, m, list(nama), nama), "bagi_dividen": fid in bagi, "dikecualikan": len(produk) - len(nama),
        "posisi": penyebab.posisi(m),
        "penyebab": penyebab.analisis(pt, {"saham_global"} if mata_uang == "USD" and kategori in ("global", "indeks", "etf") else penyebab.FAKTOR_RD.get(kategori, {"saham_id"})),
    })
