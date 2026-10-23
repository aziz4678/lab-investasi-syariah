import logging
import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.db import koneksi as d
from backend.riset.swing_target3 import rapikan_index

BATAS_RASIO = 0.10
MIN_KORELASI = 0.7
BATAS_SIMPANG_P90 = 0.08
MIN_TITIK = 5


def jenis_dari(nama):
    n = nama.upper()
    if re.search(r"EMAS|GOLD", n):
        return "emas"
    if re.search(r"GLOBAL|DOLLAR|USD", n):
        return "global"
    return "saham"


def calon_produk(db):
    return list(db.rd_produk.find({"$or": [{"kategori": "etf"}, {"nama": {"$regex": r"\bETF\b", "$options": "i"}}], "tidak_aktif": {"$ne": True}},
                                  {"nama": 1, "InvestmentManagerName": 1, "kategori": 1}))


def kata_kunci(p):
    nama = p["nama"]
    mi = re.sub(r"\b(PT|Tbk|Asset|Management|Manajemen|Investasi|Investment|Indonesia|Aset)\b|,|\.", " ", p.get("InvestmentManagerName") or "")
    mi = " ".join(mi.split()[:2])
    return list(dict.fromkeys([nama, re.sub(r"(?i)syariah|sharia", "", nama).strip(), f"{mi} ETF".strip()]))


def cari_simbol(q):
    try:
        hasil = yf.Search(q, max_results=10).quotes
    except Exception:
        return []
    return [x["symbol"] for x in hasil if str(x.get("symbol", "")).endswith(".JK") and re.fullmatch(r"X[A-Z0-9]{2,4}\.JK", x["symbol"])]


def unduh(simbol):
    df = yf.download(simbol, period="max", interval="1d", auto_adjust=False, actions=True, progress=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    df = rapikan_index(df).dropna(subset=["close"])
    return df[df["close"] > 0]


def nilai_cocok(harga, nav):
    gabung = pd.concat([harga.rename("h"), nav.rename("n")], axis=1, sort=True).dropna()
    if len(gabung) < MIN_TITIK:
        return None
    rasio = float((gabung["h"] / gabung["n"]).median())
    r = gabung.pct_change().dropna()
    kor = float(r["h"].corr(r["n"])) if len(r) >= MIN_TITIK and r["n"].std() > 0 else np.nan
    simpang = float((gabung["h"] / gabung["n"] - 1).abs().quantile(0.9))
    return {"rasio": round(rasio, 4), "korelasi": round(kor, 3) if np.isfinite(kor) else None, "simpang_p90": round(simpang, 4), "titik": len(gabung)}


def jalan():
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    db = d.koneksi()
    produk = calon_produk(db)
    print(f"{len(produk)} reksa dana syariah berbentuk ETF di katalog")
    nav_semua = pd.DataFrame(list(db.rd_nav.find({"fund": {"$in": [p["_id"] for p in produk]}}, {"_id": 0})))
    nav_semua["tgl"] = pd.to_datetime(nav_semua["tgl"])
    cache = {}
    hasil = []
    for p in produk:
        simbol = []
        for q in kata_kunci(p):
            simbol += cari_simbol(q)
            time.sleep(0.4)
        simbol = list(dict.fromkeys(simbol))
        nav = nav_semua[nav_semua["fund"] == p["_id"]].set_index("tgl")["nav"].sort_index()
        terbaik = None
        for s in simbol:
            if s not in cache:
                cache[s] = unduh(s)
                time.sleep(0.4)
            h = cache[s]
            if h is None or nav.empty:
                continue
            c = nilai_cocok(h["close"], nav)
            if c and abs(c["rasio"] - 1) <= BATAS_RASIO and ((c["korelasi"] or 0) >= MIN_KORELASI or c["simpang_p90"] <= BATAS_SIMPANG_P90):
                if terbaik is None or c["simpang_p90"] < terbaik[1]["simpang_p90"]:
                    terbaik = (s, c)
        jenis = jenis_dari(p["nama"])
        if terbaik:
            s, c = terbaik
            kode = s.removesuffix(".JK")
            h = cache[s]
            dt.tulis(f"etf/{kode}", h)
            db.rd_etf.replace_one({"_id": p["_id"]}, {"_id": p["_id"], "kode": kode, "nama": p["nama"], "jenis": jenis, "cocok": c,
                                                    "mulai": h.index.min().to_pydatetime(), "sampai": h.index.max().to_pydatetime(),
                                                    "diperbarui": datetime.now()}, upsert=True)
            hasil.append(p["nama"])
            print(f"  {kode:<5} {p['nama'][:48]:<48} cocok (harga/NAV {c['rasio']}, 90% hari selisih <= {c['simpang_p90'] * 100:.1f}%, {c['titik']} hari) · riwayat bursa sejak {h.index.min():%Y-%m-%d}")
        else:
            db.rd_etf.replace_one({"_id": p["_id"]}, {"_id": p["_id"], "kode": None, "nama": p["nama"], "jenis": jenis, "cocok": None,
                                                    "calon": simbol, "diperbarui": datetime.now()}, upsert=True)
            print(f"  ---   {p['nama'][:48]:<48} kode bursa tidak ditemukan / tidak cocok (calon: {', '.join(simbol) or '-'})")
    print(f"SELESAI: {len(hasil)} dari {len(produk)} ETF punya riwayat harga bursa dari Yahoo")





ETF_LUAR = {
    "SPUS": ("saham", "AS", True), "HLAL": ("saham", "AS", True), "ISDU.L": ("saham", "AS", True),
    "SPWO": ("saham", "Dunia", True), "UMMA": ("saham", "Dunia", True), "ISWD.L": ("saham", "Dunia", True), "HIWS.L": ("saham", "Dunia", True),
    "IGDA.L": ("saham", "Negara maju", True), "ISDE.L": ("saham", "Negara berkembang", True),
    "SPTE": ("saham", "Sektor teknologi", True), "SPRE": ("properti", "Dunia", True), "SPSK": ("sukuk", "Dunia", True),

    "SPY": ("saham", "AS", False), "VOO": ("saham", "AS", False), "IVV": ("saham", "AS", False), "VTI": ("saham", "AS", False),
    "QQQ": ("saham", "AS", False), "QQQM": ("saham", "AS", False), "DIA": ("saham", "AS", False), "IWM": ("saham", "AS", False),
    "SCHD": ("saham", "AS dividen", False), "VIG": ("saham", "AS dividen", False), "VYM": ("saham", "AS dividen", False),
    "XLK": ("saham", "Sektor teknologi", False), "VGT": ("saham", "Sektor teknologi", False), "SMH": ("saham", "Sektor teknologi", False),
    "SOXX": ("saham", "Sektor teknologi", False), "ARKK": ("saham", "Sektor teknologi", False),
    "XLF": ("saham", "Sektor lain", False), "XLE": ("saham", "Sektor lain", False), "XLV": ("saham", "Sektor lain", False),
    "VT": ("saham", "Dunia", False), "ACWI": ("saham", "Dunia", False),
    "VEA": ("saham", "Negara maju", False), "EFA": ("saham", "Negara maju", False),
    "VGK": ("saham", "Eropa", False), "EZU": ("saham", "Eropa", False), "FEZ": ("saham", "Eropa", False), "EWU": ("saham", "Eropa", False), "EWG": ("saham", "Eropa", False),
    "AAXJ": ("saham", "Asia", False), "EWJ": ("saham", "Asia", False), "MCHI": ("saham", "Asia", False), "FXI": ("saham", "Asia", False),
    "KWEB": ("saham", "Asia", False), "INDA": ("saham", "Asia", False), "EWY": ("saham", "Asia", False), "EWT": ("saham", "Asia", False),
    "EWS": ("saham", "Asia Tenggara", False), "EWM": ("saham", "Asia Tenggara", False), "EIDO": ("saham", "Asia Tenggara", False),
    "VNM": ("saham", "Asia Tenggara", False), "THD": ("saham", "Asia Tenggara", False),
    "VWO": ("saham", "Negara berkembang", False), "EEM": ("saham", "Negara berkembang", False),
    "ILF": ("saham", "Amerika Latin", False), "EWZ": ("saham", "Amerika Latin", False), "KSA": ("saham", "Timur Tengah", False),
    "VNQ": ("properti", "AS", False), "VNQI": ("properti", "Dunia", False),
    "AGG": ("obligasi", "AS", False), "BND": ("obligasi", "AS", False), "TLT": ("obligasi", "AS", False), "IEF": ("obligasi", "AS", False),
    "SHY": ("obligasi", "AS", False), "BNDX": ("obligasi", "Dunia", False), "EMB": ("obligasi", "Negara berkembang", False),
    "GLD": ("emas", "Dunia", False), "IAU": ("emas", "Dunia", False), "SLV": ("komoditas", "Dunia", False), "GDX": ("saham", "Sektor lain", False),
}


def kurs(mata_uang):
    mu = {"GBp": "GBP", "GBX": "GBP"}.get(mata_uang, mata_uang)
    if not mu or mu == "IDR":
        return None
    nama = f"kurs/{mu}"
    h = unduh(f"{mu}IDR=X")
    if h is not None and not h.empty:
        dt.tulis(nama, h[["close"]])
    return nama


def jalan_luar():
    db = d.koneksi()
    print(f"\nETF luar negeri ({len(ETF_LUAR)}):")
    mata_uang = set()
    ada = set()
    for i, (kode, (kelas, wilayah, syariah)) in enumerate(ETF_LUAR.items()):
        h = unduh(kode)
        if h is None:
            print(f"  {kode}: tidak ada data, dilewati")
            continue
        dt.tulis(f"etf_luar/{kode}", h)
        try:
            info = yf.Ticker(kode).info
        except Exception:
            info = {}
        mu = info.get("currency") or "USD"
        isi_top, sektor, aset = [], {}, {}
        try:
            fd = yf.Ticker(kode).funds_data
            th = fd.top_holdings
            if th is not None and len(th):
                isi_top = [{"kode": str(i), "nama": str(r.get("Name") or i), "bobot": round(float(r.get("Holding Percent") or 0) * 100, 2)} for i, r in th.head(10).iterrows()]
            sektor = {k: round(float(v) * 100, 2) for k, v in (fd.sector_weightings or {}).items() if v}
            aset = {k: round(float(v) * 100, 2) for k, v in (fd.asset_classes or {}).items() if v}
        except Exception:
            pass
        mata_uang.add(mu)
        db.etf_luar.replace_one({"_id": kode}, {
            "_id": kode, "kode": kode, "nama": info.get("longName") or info.get("shortName") or kode, "kelas": kelas, "wilayah": wilayah, "syariah": syariah,
            "mata_uang": mu, "bursa": "London" if kode.endswith(".L") else "AS",
            "biaya": info.get("netExpenseRatio") or info.get("annualReportExpenseRatio"), "aum": info.get("totalAssets"),
            "yield": info.get("yield") or info.get("dividendYield"), "penerbit": info.get("fundFamily"), "kategori": info.get("category"),
            "mulai": h.index.min().to_pydatetime(), "sampai": h.index.max().to_pydatetime(), "diperbarui": datetime.now(),
            "isi_top": isi_top, "sektor": sektor, "aset": aset, "ringkasan_en": (info.get("longBusinessSummary") or "")[:1500],
        }, upsert=True)
        ada.add(kode)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(ETF_LUAR)} ETF")
        time.sleep(0.3)
    hapus = db.etf_luar.delete_many({"_id": {"$nin": sorted(ada)}}).deleted_count
    for mu in sorted(mata_uang):
        kurs(mu)
    sy = sum(1 for k in ada if ETF_LUAR[k][2])
    print(f"SELESAI ETF luar negeri: {len(ada)} ETF ({sy} syariah, {len(ada) - sy} bukan syariah), kurs: {', '.join(sorted(mata_uang))}" + (f", {hapus} lama dihapus" if hapus else ""))


if __name__ == "__main__":
    jalan()
    jalan_luar()
