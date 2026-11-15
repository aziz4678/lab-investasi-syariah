import numpy as np
import pandas as pd

from backend.db import data as dt

AMBANG_NAIK = 5.0
AMBANG_TURUN = -5.0
AMBANG_TAK_BIASA = -1.0
MIN_TAHUN_PRODUK = 5
AWAL_PROKSI = pd.Period("2010-01", "M")
DIV_JII = 0.025
PAJAK_DIV_SPUS = 0.30
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

PERAN = {
    "lokal": "Ikut pertumbuhan perusahaan Indonesia, untuk uang yang tidak dipakai minimal 5 tahun.",
    "global": "Ikut pertumbuhan perusahaan besar dunia (AS), penyeimbang saat pasar Indonesia lemah.",
    "emas": "Peredam saat saham jatuh.",
    "pu": "Dana siap pakai, nilainya stabil.",
    "darurat": "Dana siap pakai, nilainya stabil.",
    "pt": "Sedikit lebih tinggi dari pasar uang, tetap bisa dicairkan kapan saja.",
}
PASAR = {"lokal": "pasar saham Indonesia", "global": "pasar saham syariah dunia", "emas": "harga emas"}
TOLOK = {"lokal": "JII", "global": "MSCI World Islamic", "emas": "harga emas dalam rupiah"}


def pr(v, desimal=1):
    return f"{v:+.{desimal}f}%".replace(".", ",").replace("+", "")


def bulan_teks(p):
    return f"{BULAN[p.month - 1]} {p.year}"


def kondisi(ret):
    if ret is None:
        return {"kode": "tidak_ada", "teks": "Belum ada data", "warna": "abu"}
    if ret < AMBANG_TURUN:
        return {"kode": "turun", "teks": "Lagi turun", "warna": "merah"}
    if ret > AMBANG_NAIK:
        return {"kode": "naik", "teks": "Lagi naik", "warna": "hijau"}
    return {"kode": "datar", "teks": "Datar", "warna": "abu"}


def _harian(nama, kolom="close"):
    x = dt.baca(nama)
    if x is None or len(x) == 0:
        return pd.Series(dtype=float)
    s = x[kolom].dropna().sort_index()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    return s


def _bulanan(s):
    m = s.dropna().resample("ME").last()
    m.index = m.index.to_period("M")
    return m


def _ret_1th(s):
    if s is None or len(s) < 2:
        return None
    akhir = s.index[-1]
    awal = s[s.index <= akhir - pd.Timedelta(days=365)]
    if not len(awal):
        return None
    return float((s.iloc[-1] / awal.iloc[-1] - 1) * 100)


def _kurs_harian():
    return _harian("pasar", "usdidr")


def seri_jii():
    s = _harian("indeks/JKII")
    return s


def seri_msci_idr():
    usd = _harian("indeks_luar/gl_msci_world_islamic", "adj_close")
    k = _kurs_harian()
    return (usd * k.reindex(usd.index, method="ffill")).dropna()


def seri_emas_idr():
    e = _harian("pasar", "emas")
    k = _kurs_harian()
    return (e * k.reindex(e.index, method="ffill")).dropna()


def seri_spus_idr():
    x = dt.baca("etf_luar/SPUS")
    if x is None or len(x) == 0:
        return pd.Series(dtype=float)
    x = x.sort_index()
    x.index = pd.DatetimeIndex(x.index).tz_localize(None)
    c, dv = x["close"], x["dividends"].fillna(0)
    r = ((c + (1 - PAJAK_DIV_SPUS) * dv) / c.shift(1) - 1).dropna()
    usd = (1 + r).cumprod()
    k = _kurs_harian()
    return (usd * k.reindex(usd.index, method="ffill")).dropna()


def tolok_1th(kaki):
    if kaki == "lokal":
        j = seri_jii()
        r = _ret_1th(j)
        return None if r is None else ((1 + r / 100) * (1 + DIV_JII) - 1) * 100
    if kaki == "global":
        return _ret_1th(seri_msci_idr())
    if kaki == "emas":
        return _ret_1th(seri_emas_idr())
    return None


def _harapan(m, sumber, label):
    m = m.dropna()
    if len(m) < 13:
        return None
    n = len(m) - 1
    tahun = n / 12
    cagr = float((m.iloc[-1] / m.iloc[0]) ** (1 / tahun) - 1) * 100
    dd = float((m / m.cummax() - 1).min() * 100)
    return {"cagr": cagr, "dd": dd, "dari": bulan_teks(m.index[0]), "sampai": bulan_teks(m.index[-1]), "tahun": tahun, "sumber": sumber, "label_sumber": label}


def harapan_teks(h):
    if h is None:
        return "Rekam jejak: belum ada riwayat yang cukup."
    arah = "naik" if h["cagr"] >= 0 else "turun"
    awal = f"Rekam jejak (periode {h['dari']}–{h['sampai']}): rata-rata {arah} {pr(abs(h['cagr']))} per tahun"
    if h["dd"] > -0.1:
        return f"{awal}, hampir tidak pernah turun."
    return f"{awal}, pernah turun sampai {pr(abs(h['dd']))}."


def _proksi_jii():
    j = _bulanan(seri_jii())
    j = j.loc[AWAL_PROKSI:]
    faktor = (1 + DIV_JII) ** (np.arange(len(j)) / 12)
    return pd.Series(j.to_numpy() * faktor, index=j.index)


def _proksi_harga(s):
    return _bulanan(s).loc[AWAL_PROKSI:]


def harapan_proksi(kaki):
    if kaki == "lokal":
        return _harapan(_proksi_jii(), "proksi", "indeks JII ditambah asumsi dividen 2,5%/th, bukan produk ini")
    if kaki == "global":
        return _harapan(_proksi_harga(seri_msci_idr()), "proksi", "indeks MSCI World Islamic dalam rupiah, bukan produk ini")
    if kaki == "emas":
        return _harapan(_proksi_harga(seri_emas_idr()), "proksi", "harga emas dunia dalam rupiah, bukan ETF ini")
    return None


def harapan_produk(m, tahun_data, kaki, label):
    if m is not None and tahun_data is not None and tahun_data >= MIN_TAHUN_PRODUK:
        h = _harapan(m, "produk", label)
        if h:
            return h
    return harapan_proksi(kaki)


def _kalimat(kaki, ret, tolok, tak_biasa_konservatif=False):
    if kaki in ("pu", "pt", "darurat"):
        if ret is not None and ret < AMBANG_TAK_BIASA:
            return {"teks": f"Turun {pr(abs(ret))} setahun. Ini tidak biasa untuk jenis produk ini; akan dipantau dan dievaluasi ulang kalau berlanjut.", "peringatan": True}
        if ret is not None and ret < 0:
            return {"teks": "Hampir datar dan stabil, memang itu fungsinya: tempat uang yang bisa diambil kapan saja.", "peringatan": False}
        return {"teks": "Naik pelan dan stabil, memang itu fungsinya: tempat uang yang bisa diambil kapan saja.", "peringatan": False}
    k = kondisi(ret)["kode"]
    pasar, nama = PASAR[kaki], TOLOK[kaki]
    if k == "turun" and tolok is not None and ret >= tolok:
        return {"teks": f"Turun karena {pasar} sedang turun ({nama} {pr(tolok)} setahun), bukan karena produknya. Produk ini malah lebih tahan dari pasarnya. Beli rutin saat turun = dapat unit lebih murah.", "peringatan": False}
    if k == "turun":
        akhir = f" ({nama} {pr(tolok)} setahun, produk ini {pr(ret)})" if tolok is not None else ""
        return {"teks": f"Produk ini tertinggal dari pasarnya{akhir}. Akan dievaluasi ulang.", "peringatan": True}
    if k == "naik":
        return {"teks": "Lagi naik. Tetap beli sesuai porsi, jangan ditambah. Kalau porsinya kebesaran, kelebihannya dipindah ke bagian lain saat penyeimbangan Desember.", "peringatan": False}
    if k == "datar":
        return {"teks": "Bergerak datar. Tetap beli sesuai porsi.", "peringatan": False}
    return {"teks": "Belum ada data return setahun, jadi belum bisa dinilai.", "peringatan": False}


def susun(kaki, ret, tolok, harapan, nama_tolok=None, proksi_ret=False, porsi=None, biaya=None, ket_tolok=None):
    kond = kondisi(ret)
    kal = _kalimat(kaki, ret, tolok)
    return {"kaki": kaki, "kondisi": kond, "kalimat": kal["teks"], "peringatan": kal["peringatan"], "peran": PERAN[kaki], "harapan": harapan_teks(harapan),
            "harapan_sumber": None if harapan is None else harapan["label_sumber"], "harapan_jenis": None if harapan is None else harapan["sumber"],
            "ret_1th": ret, "tolok_1th": tolok, "nama_tolok": nama_tolok or TOLOK.get(kaki), "ret_dari_proksi": proksi_ret, "porsi": porsi, "biaya": biaya, "ket_tolok": ket_tolok,
            "pasar": PASAR.get(kaki)}


def ringkasan(daftar, konservatif=False):
    ada = [x for x in daftar if x and x["kondisi"]["kode"] != "tidak_ada"]
    m = len(ada)
    if not m:
        return None
    hitung = {k: sum(1 for x in ada if x["kondisi"]["kode"] == k) for k in ("turun", "naik", "datar")}
    if konservatif:
        tak = [x for x in ada if x["ret_1th"] is not None and x["ret_1th"] < AMBANG_TAK_BIASA]
        if tak:
            return {"teks": f"Bulan ini {len(tak)} dari {m} produk sedang turun, tidak biasa untuk jenis produk ini. Dipantau dulu sebelum menambah beli.", "kondisi": "turun"}
        if any(x["ret_1th"] is not None and x["ret_1th"] < 0 for x in ada):
            return {"teks": f"Bulan ini {m} produk naik pelan atau hampir datar, tetap stabil: memang itu fungsinya, tempat uang yang bisa diambil kapan saja.", "kondisi": "datar"}
        return {"teks": f"Bulan ini {m} produk naik pelan dan stabil, memang itu fungsinya: tempat uang yang bisa diambil kapan saja.", "kondisi": "datar"}
    dominan = max(("turun", "naik", "datar"), key=lambda k: (hitung[k], {"turun": 2, "naik": 1, "datar": 0}[k]))
    n = hitung[dominan]
    if dominan == "turun":
        pasar = [x["pasar"] for x in ada if x["kondisi"]["kode"] == "turun" and x.get("pasar")]
        pasar_dominan = max(set(pasar), key=pasar.count) if pasar else "pasar"
        return {"teks": f"Bulan ini {n} dari {m} produk sedang turun karena {pasar_dominan} lemah. Ini wajar untuk investasi jangka panjang, dan justru saat murah porsi ini dibeli.", "kondisi": "turun"}
    if dominan == "naik":
        return {"teks": f"Bulan ini {n} dari {m} produk sedang naik. Tetap beli sesuai porsi, jangan ditambah karena tergoda naik.", "kondisi": "naik"}
    return {"teks": f"Bulan ini {n} dari {m} produk bergerak datar. Tetap beli sesuai porsi.", "kondisi": "datar"}


def bulanan_rd():
    from backend.app.services import rd_yakin
    return rd_yakin.bulanan()


def seri_rd(b, fid):
    if b is None or fid not in b.columns:
        return None
    m = b[fid].dropna()
    m.index = pd.DatetimeIndex(m.index).to_period("M")
    return m[~m.index.duplicated(keep="last")]


def kinerja_spus():
    s = seri_spus_idr()
    if len(s) < 2:
        return None
    m = _bulanan(s)
    tahun = (s.index[-1] - s.index[0]).days / 365.25
    cagr = lambda t: None if tahun < t else float(((s.iloc[-1] / s[s.index <= s.index[-1] - pd.Timedelta(days=int(365.25 * t))].iloc[-1]) ** (1 / t) - 1) * 100)
    return {"ret_1th": _ret_1th(s), "cagr_3": cagr(3), "cagr_5": cagr(5), "turun_terburuk": float((m / m.cummax() - 1).min() * 100), "tahun_data": tahun, "untung_12bln": None}


def kartu_pertumbuhan(kaki, kartu, b, kin, porsi):
    tolok = tolok_1th(kaki)
    jenis = kartu.get("tipe")
    if jenis == "saham_as":
        s = seri_spus_idr()
        ret = _ret_1th(s)
        tahun = (s.index[-1] - s.index[0]).days / 365.25 if len(s) > 1 else None
        h = harapan_produk(_bulanan(s) if len(s) > 1 else None, tahun, "global", "SPUS asli dalam rupiah, dividen dipotong pajak 30%")
        return susun("global", ret, tolok, h, porsi=porsi, biaya=kartu.get("biaya"), ket_tolok="Tolok ukur dalam rupiah, termasuk dividen.")
    if jenis == "etf":
        h = harapan_proksi("emas")
        return susun("emas", tolok, tolok, h, proksi_ret=True, porsi=porsi, ket_tolok="ETF emas baru listing, angka setahun memakai harga emas dunia dalam rupiah.")
    k = (kin or {}).get(int(kartu["id"])) or {}
    ret = k.get("ret_1th")
    m = seri_rd(b, int(kartu["id"]))
    label = "NAV produk asli" + (" dalam rupiah" if kartu.get("mata_uang") == "USD" else "")
    h = harapan_produk(m, k.get("tahun_data"), kaki, label)
    return susun(kaki, ret, tolok, h, porsi=porsi, biaya=kartu.get("biaya"), ket_tolok="JII dihitung dengan asumsi dividen 2,5% per tahun." if kaki == "lokal" else None)


def tolok_kategori(data_rd, x):
    nilai = [r["ret_1th"] for r in data_rd if r.get("kategori") == x.get("kategori") and r.get("mata_uang") == x.get("mata_uang") and r.get("ret_1th") is not None]
    return float(np.median(nilai)) if len(nilai) >= 3 else None


def proksi_kategori(b, data_rd, x):
    ids = [int(r["id"]) for r in data_rd if r.get("kategori") == x.get("kategori") and r.get("mata_uang") == x.get("mata_uang") and int(r["id"]) in b.columns]
    if len(ids) < 3:
        return None
    m = b[ids].copy()
    m.index = pd.DatetimeIndex(m.index).to_period("M")
    m = m[~m.index.duplicated(keep="last")]
    r = m.pct_change(fill_method=None).mean(axis=1, skipna=True).dropna()
    r = r.loc[AWAL_PROKSI:]
    if len(r) < 13:
        return None
    return _harapan((1 + r).cumprod(), "proksi", "rata-rata produk sejenis, bukan produk ini")


def kartu_konservatif(wadah, kartu, b, info_rd, data_rd):
    x = info_rd.get(int(kartu["id"])) or {}
    ret = x.get("ret_1th")
    tolok = tolok_kategori(data_rd, x)
    m = seri_rd(b, int(kartu["id"]))
    h = None
    if m is not None and (x.get("tahun_data") or 0) >= MIN_TAHUN_PRODUK:
        h = _harapan(m, "produk", "NAV produk asli")
    if h is None:
        h = proksi_kategori(b, data_rd, x)
    return susun(wadah, ret, tolok, h, nama_tolok="rata-rata produk sejenis", porsi=kartu.get("porsi"), biaya=kartu.get("biaya"))
