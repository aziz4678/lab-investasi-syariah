import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from curl_cffi import requests

from backend.db import koneksi as d

DASAR = "https://pasardana.id/api"
JEDA = 0.6
UMUR_DETAIL = 7
BATAS_WAKTU = 60
KATEGORI = {
    "Pasar Uang": "pasar_uang", "Pendapatan Tetap": "pendapatan_tetap", "Campuran": "campuran", "Saham": "saham",
    "Indeks": "indeks", "Exchange Traded Fund": "etf", "Reksadana Global": "global", "Terproteksi": "terproteksi",
    "Penyertaan Terbatas": "penyertaan_terbatas", "DIRE & DINFRA": "dire",
}
KOLOM_PRODUK = ["Name", "InvestmentManagerName", "InvestmentManagerFee", "MinimumSubscription", "IsinCode", "CustodianBankName",
                "Currency", "ExchangeTradedFund", "Index", "Dividend", "NetAssetValue", "DailyReturn", "WeeklyReturn", "MtdReturn",
                "MonthlyReturn", "QuarterlyReturn", "SemiAnnualReturn", "YtdReturn", "YearlyReturn", "ThreeYearReturn", "FiveYearReturn",
                "AssetUnderManagement", "TotalUnit", "AumPublishedDate", "LastUpdate", "ConservativeCategory", "LastFundFactSheet",
                "RiskClassificationValue", "ExpenseRatio", "OneYearStdev", "OneYearSharpeRatio"]


def sesi():
    s = requests.Session(impersonate="chrome")
    s.headers.update({"Accept": "application/json"})
    return s


def ambil(s, jalur, **param):
    for coba in range(4):
        try:
            r = s.get(f"{DASAR}/{jalur}", params=param, timeout=BATAS_WAKTU)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 503):
                time.sleep(20 * (coba + 1))
                continue
            raise RuntimeError(f"{jalur}: status {r.status_code}")
        except requests.RequestsError as e:
            if coba == 3:
                raise
            print(f"  koneksi gagal ({e.__class__.__name__}), coba lagi")
            time.sleep(5 * (coba + 1))
    raise RuntimeError(f"{jalur}: gagal setelah 4 kali")


def tgl(x):
    return pd.Timestamp(x[:10]).to_pydatetime() if x else None


def perbarui_produk(s, db):
    semua = ambil(s, "FundSearchResult/GetAll")
    syariah = [r for r in semua if r.get("Id") and r.get("Sharia")]
    sekarang = datetime.now()
    ops_nav = []
    for r in syariah:
        dok = {k: r.get(k) for k in KOLOM_PRODUK}
        dok.update({"_id": r["Id"], "nama": r["Name"], "kategori": KATEGORI.get(r.get("ConservativeCategory"), "lain"),
                    "kategori_label": r.get("ConservativeCategory"), "mata_uang": "USD" if r.get("Currency") == 1 else "IDR",
                    "nav_tgl": tgl(r.get("LastUpdate")), "diperbarui": sekarang})
        db.rd_produk.replace_one({"_id": r["Id"]}, dok, upsert=True)
        if r.get("NetAssetValue") and r.get("LastUpdate"):
            t = tgl(r["LastUpdate"])
            ops_nav.append({"_id": f"{r['Id']}_{t:%Y%m%d}", "fund": r["Id"], "tgl": t, "nav": float(r["NetAssetValue"])})
    for x in ops_nav:
        db.rd_nav.replace_one({"_id": x["_id"]}, x, upsert=True)
    aktif = {r["Id"] for r in syariah}
    lama = db.rd_produk.update_many({"_id": {"$nin": list(aktif)}}, {"$set": {"tidak_aktif": True}})
    print(f"{len(semua)} reksa dana di Pasardana, {len(syariah)} syariah disimpan, {len(ops_nav)} NAV hari ini"
          + (f", {lama.modified_count} produk lama ditandai tidak aktif" if lama.modified_count else ""))
    return syariah


def ringkas_aset(port):
    hasil, sudah = [], set()
    for a in (port or {}).get("Assets") or []:
        nama = a.get("Name") or a.get("AssetName") or a.get("SecurityName")
        bobot = a.get("Percentage") or a.get("Weight") or a.get("Value")
        kunci = (a.get("Type"), (nama or "").strip().lower())
        if nama and kunci not in sudah:
            sudah.add(kunci)
            hasil.append({"nama": nama, "bobot": bobot, "jenis": a.get("AssetType") or a.get("Type")})
    return hasil[:30]


def deret(xs):
    return [{"tgl": tgl(x["Date"]), "nilai": x["Value"]} for x in xs or [] if x.get("Date") and x.get("Value") is not None]


def perbarui_detail(s, db, produk, paksa=False):
    batas = datetime.now() - timedelta(days=UMUR_DETAIL)
    sudah = {x["_id"]: x.get("diambil") for x in db.rd_detail.find({}, {"diambil": 1})}
    antre = [r for r in produk if paksa or not sudah.get(r["Id"]) or sudah[r["Id"]] < batas]
    print(f"Mengambil detail + riwayat NAV {len(antre)} produk (detail lebih dari {UMUR_DETAIL} hari)...")
    n_nav = 0
    for i, r in enumerate(antre):
        try:
            x = ambil(s, "FundService/GetSnapshot", fundId=r["Id"])
        except Exception as e:
            print(f"  {r['Name']}: gagal ({e})")
            continue
        for v in x.get("NetAssetValues") or []:
            if v.get("Date") and v.get("Value"):
                t = tgl(v["Date"])
                db.rd_nav.replace_one({"_id": f"{r['Id']}_{t:%Y%m%d}"}, {"_id": f"{r['Id']}_{t:%Y%m%d}", "fund": r["Id"], "tgl": t, "nav": float(v["Value"])}, upsert=True)
                n_nav += 1
        bm = x.get("Benchmark") or {}
        det = x.get("Detail") or {}
        perf = (x.get("Performances") or [{}])[0]
        dok = {
            "_id": r["Id"], "diambil": datetime.now(), "deskripsi": det.get("Description"), "tgl_terbit": tgl(det.get("IpoDate")),
            "min_beli": det.get("MinimumSubscription"), "min_beli_lagi": det.get("MinimumNextSubscription"), "min_jual": det.get("MinimumRedemption"),
            "biaya": deret(x.get("ExpenseRatios")), "aum": deret(x.get("AssetUnderManagements")), "unit": deret(x.get("TotalUnits")),
            "aset": ringkas_aset(x.get("Portfolio")), "porsi_dalam_negeri": (x.get("Portfolio") or {}).get("DomesticAllocation"),
            "risiko": (x.get("Portfolio") or {}).get("RiskClassificationValue"), "catatan_risiko": (x.get("Portfolio") or {}).get("RiskClassificationNote"),
            "pembanding": bm.get("Name"), "pembanding_deret": deret(bm.get("Data"))[-260:],
            "kinerja_1th": {k: perf.get(k) for k in ("Return", "StandardDeviation", "SharpeRatio", "SortinoRatio", "MaxDrawdown", "Beta")},
            "kategori_1th": {k: ((x.get("CategoryPerformances") or [{}])[0]).get(k) for k in ("Return", "StandardDeviation", "SharpeRatio", "TotalFunds")},
            "dokumen": [{"nama": dd.get("Name"), "tgl": tgl(dd.get("Date")), "jenis": dd.get("DocumentType"), "id": dd.get("Id")} for dd in (x.get("Documents") or [])[:6]],
            "dividen": [{"tgl": tgl(v["Date"]), "nilai": v.get("Value")} for v in x.get("FundDividends") or [] if v.get("Date")],
        }
        db.rd_detail.replace_one({"_id": r["Id"]}, dok, upsert=True)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(antre)} produk")
        time.sleep(JEDA)
    print(f"Detail selesai, {n_nav} titik NAV historis disimpan/diperbarui")


def perbarui_sukuk(s, db):
    semua = ambil(s, "Bond/GetAll")
    hari = datetime.now()
    sy = [r for r in semua if r.get("IsSharia") and r.get("IsActive") and r.get("MatureDate") and tgl(r["MatureDate"]) > hari]
    db.rd_sukuk.delete_many({})
    dok = []
    for r in sy:
        b = r.get("BondLastData") or {}
        kode = r["SecurityCode"]
        jenis = "SR" if kode.startswith("SR0") else "PBS" if kode.startswith("PBS") else "SPNS" if kode.startswith("SPNS") else \
            "Negara lain" if r.get("Type") == "G" else "Korporasi"
        dok.append({"_id": kode, "nama": r.get("Name"), "jenis": jenis, "penerbit": r.get("Issuer"), "kupon": r.get("InterestRate"),
                    "jenis_kupon": r.get("InterestType"), "terbit": tgl(r.get("IssueDate")), "jatuh_tempo": tgl(r.get("MatureDate")),
                    "jumlah": r.get("CurrentAmount"), "rating": (r.get("Rating") or {}).get("Name") if isinstance(r.get("Rating"), dict) else r.get("Rating"),
                    "harga": b.get("LastPrice"), "ytm": b.get("Ytm"), "current_yield": b.get("CurrentYield"), "sisa_tahun": b.get("Ttm"),
                    "durasi": b.get("ModDur"), "frekuensi": b.get("Freq"), "data_tgl": tgl(b.get("DateModified")), "mata_uang": r.get("Currency")})
    if dok:
        db.rd_sukuk.insert_many(dok)
        n_riwayat = 0
        for x in dok:
            if x.get("harga") is None or x.get("data_tgl") is None:
                continue
            t = x["data_tgl"].replace(hour=0, minute=0, second=0, microsecond=0)
            db.rd_sukuk_harga.replace_one({"_id": f"{x['_id']}_{t:%Y%m%d}"}, {"kode": x["_id"], "tgl": t, "harga": x["harga"], "ytm": x.get("ytm")}, upsert=True)
            n_riwayat += 1
        db.rd_sukuk_harga.create_index([("kode", 1), ("tgl", 1)])
        print(f"Riwayat harga sukuk: {n_riwayat} seri dicatat untuk hari ini, total {db.rd_sukuk_harga.count_documents({})} titik")
    hitung = pd.Series([x["jenis"] for x in dok]).value_counts().to_dict() if dok else {}
    print(f"{len(semua)} obligasi/sukuk di Pasardana, {len(dok)} sukuk syariah aktif disimpan: " + ", ".join(f"{k} {v}" for k, v in hitung.items()))


def jalan(paksa=False):
    db = d.koneksi()
    db.rd_nav.create_index([("fund", 1), ("tgl", 1)])
    s = sesi()
    produk = perbarui_produk(s, db)
    perbarui_detail(s, db, produk, paksa)
    perbarui_sukuk(s, db)
    db.rd_info.update_one({"_id": "ringkas"}, {"$set": {"diperbarui": datetime.now(), "produk": len(produk),
                                                        "nav": db.rd_nav.count_documents({}), "sukuk": db.rd_sukuk.count_documents({})}}, upsert=True)
    print(f"Selesai: {len(produk)} reksa dana syariah, {db.rd_nav.count_documents({})} titik NAV, {db.rd_sukuk.count_documents({})} sukuk")


if __name__ == "__main__":
    jalan(paksa="--paksa" in sys.argv)
