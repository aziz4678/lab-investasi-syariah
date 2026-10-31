import pandas as pd

from backend.app.services import etf, penyebab
from backend.db import data as dt
from backend.db import koneksi as d

KRISIS = [("Krisis keuangan 2008", "2007-10-09", "2009-03-09"), ("Covid 2020", "2020-02-19", "2020-03-23"), ("Suku bunga naik 2022", "2022-01-03", "2022-10-12")]
JENDELA = {1: 252, 3: 756, 5: 1260, 10: 2520}
MIN_TAHUN_PROKSI = 15
MIN_KORELASI = 0.8
MIN_TURUN = -10


def total(h):
    return etf.total(h)


def kurs(mu):
    mu = {"GBp": "GBP", "GBX": "GBP"}.get(mu, mu or "USD")
    k = dt.baca(f"kurs/{mu}")
    if k is not None:
        return k["close"].dropna()
    return dt.baca("pasar")["usdidr"].dropna() if mu == "USD" else None


def seri(kode, mu):
    h = etf.baca_luar(kode)
    if h is None or h.empty:
        return None, None, None
    s = total(h)
    s = s[~s.index.duplicated()]
    k = kurs(mu)
    rp = (s * k.reindex(s.index, method="ffill")).dropna() if k is not None else pd.Series(dtype=float)
    return h, s, rp


def per_tahun(s, rp):
    akhir = s.resample("YE").last()
    akhir_rp = rp.resample("YE").last() if len(rp) else pd.Series(dtype=float)
    hasil = []
    for i, (t, v) in enumerate(akhir.items()):
        if i == 0:
            if s.index[0] > pd.Timestamp(year=t.year, month=1, day=15):
                continue
            awal, awal_rp = s.iloc[0], (rp.iloc[0] if len(rp) else None)
        else:
            awal, awal_rp = akhir.iloc[i - 1], (akhir_rp.get(akhir.index[i - 1]) if len(akhir_rp) else None)
        v_rp = akhir_rp.get(t) if len(akhir_rp) else None
        hasil.append({"tahun": int(t.year), "usd": float((v / awal - 1) * 100),
                      "rp": float((v_rp / awal_rp - 1) * 100) if v_rp is not None and awal_rp else None,
                      "berjalan": bool(t > s.index[-1])})
    return hasil


def jendela(s):
    hasil = []
    for th, n in JENDELA.items():
        if len(s) <= n + 20:
            continue
        r = (s / s.shift(n) - 1).dropna()
        tahunan = ((1 + r) ** (1 / th) - 1) * 100
        hasil.append({"tahun": th, "n": int(len(r)), "untung": float((r > 0).mean() * 100), "median": float(tahunan.median()),
                      "terburuk": float(tahunan.min()), "terbaik": float(tahunan.max())})
    return hasil


def penurunan(s, n=3):
    puncak = s.cummax()
    dd = s / puncak - 1
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
        dasar = bagian.idxmin()
        dalam = float(bagian.min() * 100)
        if dalam > MIN_TURUN:
            continue
        awal = s[s.index < a].index[-1] if (s.index < a).any() else a
        hasil.append({"puncak": awal.strftime("%Y-%m-%d"), "dasar": dasar.strftime("%Y-%m-%d"), "turun": dalam,
                      "pulih": b.strftime("%Y-%m-%d") if b is not None else None,
                      "bulan_turun": round((dasar - awal).days / 30.44, 1),
                      "bulan_pulih": round((b - dasar).days / 30.44, 1) if b is not None else None})
    return sorted(hasil, key=lambda x: x["turun"])[:n]


def krisis(s):
    hasil = []
    for nama, a, b in KRISIS:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if s.index[0] > a or s.index[-1] < b:
            hasil.append({"nama": nama, "turun": None})
            continue
        hasil.append({"nama": nama, "turun": float((s.asof(b) / s.asof(a) - 1) * 100)})
    return hasil


def cagr(s):
    th = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / th) - 1) * 100 if th >= 1 and len(s) > 1 else None


def sumber(h, s, rp):
    harga = h["close"].reindex(s.index).ffill().dropna()
    c_harga, c_total, c_rp = cagr(harga), cagr(s), cagr(rp) if len(rp) else None
    if c_harga is None or c_total is None:
        return None
    return {"mulai": s.index[0].strftime("%Y-%m-%d"), "harga": c_harga, "dividen": c_total - c_harga, "total": c_total,
            "kurs": (c_rp - c_total) if c_rp is not None else None, "rupiah": c_rp}


def mingguan(s):
    return s.resample("W-FRI").last().pct_change().dropna()


def proksi(kode, s):
    th = (s.index[-1] - s.index[0]).days / 365.25
    if th >= MIN_TAHUN_PROKSI:
        return None
    w = mingguan(s)
    terbaik = None
    for m in d.koneksi().etf_luar.find({"_id": {"$ne": kode}}, {"kode": 1, "nama": 1, "syariah": 1, "mata_uang": 1}):
        h = etf.baca_luar(m['kode'])
        if h is None or h.empty or (h.index[-1] - h.index[0]).days / 365.25 < MIN_TAHUN_PROKSI:
            continue
        sp = total(h)
        sp = sp[~sp.index.duplicated()]
        gabung = pd.concat([w, mingguan(sp)], axis=1, join="inner").dropna()
        if len(gabung) < 104:
            continue
        k = float(gabung.iloc[:, 0].corr(gabung.iloc[:, 1]))
        if terbaik is None or k > terbaik[0]:
            terbaik = (k, m, sp)
    if terbaik is None or terbaik[0] < MIN_KORELASI:
        return None
    k, m, sp = terbaik
    tahunan = per_tahun(sp, pd.Series(dtype=float))
    lengkap = [x for x in tahunan if not x["berjalan"]]
    buruk = min(lengkap, key=lambda x: x["usd"]) if lengkap else None
    return {"kode": m["kode"], "nama": m["nama"], "syariah": bool(m.get("syariah")), "korelasi": k,
            "mulai": sp.index[0].strftime("%Y-%m-%d"), "tahun": round((sp.index[-1] - sp.index[0]).days / 365.25, 1),
            "cagr": cagr(sp), "dd": float((sp / sp.cummax() - 1).min() * 100),
            "tahun_terburuk": buruk, "tahun_naik": sum(x["usd"] > 0 for x in lengkap), "tahun_dihitung": len(lengkap),
            "jendela": jendela(sp), "krisis": krisis(sp)}


def keyakinan(kode, mu):
    h, s, rp = seri(kode, mu)
    if s is None or len(s) < 60:
        return None
    asli = dt.baca(f"etf_luar/{kode}")
    kelas = (d.koneksi().etf_luar.find_one({"_id": kode}, {"kelas": 1}) or {}).get("kelas")
    pt = per_tahun(s, rp)
    return {"dipotong_sejak": etf.DATA_ANDAL_SEJAK.get(kode), "data_asli_mulai": asli.index[0].strftime("%Y-%m-%d") if asli is not None and len(asli) else None,
            "lonjakan_dibuang": int(len(asli) - len(h) - (len(asli[asli.index < h.index[0]]) if len(h) else 0)) if asli is not None else 0,
            "mulai": s.index[0].strftime("%Y-%m-%d"), "sampai": s.index[-1].strftime("%Y-%m-%d"),
            "tahun": round((s.index[-1] - s.index[0]).days / 365.25, 1), "per_tahun": pt,
            "jendela": jendela(s), "jendela_rp": jendela(rp) if len(rp) else [], "penurunan": penurunan(s),
            "krisis": krisis(s), "sumber": sumber(h, s, rp), "proksi": proksi(kode, s),
            "posisi": penyebab.posisi(rp if len(rp) else s, -5.0), "posisi_rupiah": bool(len(rp)),
            "penyebab": penyebab.analisis(pt, penyebab.FAKTOR_ETF.get(kelas, {"saham_global", "kurs"}), "usd", "rp" if len(rp) else None)}
