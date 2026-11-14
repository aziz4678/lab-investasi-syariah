import logging
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import etf as etf_mod

UTAMA = ["XTRA", "XGLD", "XMES", "XDES", "XSGO"]
TAMBAHAN = ["XKGS", "XBGS"]
KODE_MANUAL = {5980: "XMES", 5983: "XBGS"}
BATAS_PREMIUM = 0.02
MIN_AUM = 10e9
MIN_NILAI = 10e6
HARI_PILIH = 60
KOLEKSI = "etf_emas"


def daftar(db):
    out = {}
    for r in db.rd_etf.find({"jenis": "emas"}):
        kode = r.get("kode") or KODE_MANUAL.get(r["_id"])
        if kode:
            out[kode] = {"id": r["_id"], "nama": r["nama"], "manual": not r.get("kode")}
    return out


def produk(db, fid):
    return db.rd_produk.find_one({"_id": {"$in": [fid, str(fid)]}}) or {}


def nav_seri(db, fid):
    x = pd.DataFrame(list(db.rd_nav.find({"fund": {"$in": [fid, str(fid)]}}, {"_id": 0})))
    if x.empty:
        return pd.Series(dtype=float)
    x["tgl"] = pd.to_datetime(x["tgl"])
    return x.set_index("tgl")["nav"].astype(float).sort_index()


def bangun(db, kode, info):
    h = etf_mod.unduh(f"{kode}.JK")
    if h is None or h.empty:
        return None
    baru = pd.DataFrame({"close": h["close"].astype(float), "volume": h["volume"].astype(float)})
    baru["nilai"] = baru["close"] * baru["volume"]
    nav = nav_seri(db, info["id"])
    baru["nav"] = nav.reindex(baru.index)
    baru["premium"] = baru["close"] / baru["nav"] - 1
    p = produk(db, info["id"])
    baru["aum"] = np.nan
    baru["aum_tgl"] = None
    if len(baru) and p.get("AssetUnderManagement") is not None:
        baru.loc[baru.index[-1], "aum"] = float(p["AssetUnderManagement"])
        baru.loc[baru.index[-1], "aum_tgl"] = str(p.get("AumPublishedDate") or "")[:10]
    baru["diambil"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if dt.ada(f"{KOLEKSI}/{kode}"):
        lama = dt.baca(f"{KOLEKSI}/{kode}")
        keep = lama.loc[~lama.index.isin(baru.index)]
        sama = lama.loc[lama.index.isin(baru.index)]
        for kol in ("aum", "aum_tgl"):
            if kol in sama:
                baru[kol] = baru[kol].combine_first(sama[kol].reindex(baru.index))
        baru = pd.concat([keep, baru]).sort_index()
    return baru


def ringkas(df):
    prem = df["premium"].dropna()
    ada_nav = int(df["nav"].notna().sum())
    trans = df["nilai"][df["volume"] > 0]
    aum = df["aum"].dropna()
    return {"hari": int(len(df)), "hari_ada_nav": ada_nav, "hari_tanpa_transaksi": int((df["volume"] <= 0).sum()),
            "mulai": str(df.index.min().date()), "sampai": str(df.index.max().date()),
            "premium_median": float(prem.median()) if len(prem) else None, "premium_min": float(prem.min()) if len(prem) else None,
            "premium_maks": float(prem.max()) if len(prem) else None, "premium_terakhir": float(prem.iloc[-1]) if len(prem) else None,
            "mutlak_median": float(prem.abs().median()) if len(prem) else None,
            "nilai_median_harian": float(df["nilai"].median()), "nilai_median_hari_transaksi": float(trans.median()) if len(trans) else None,
            "aum": float(aum.iloc[-1]) if len(aum) else None, "aum_tgl": str(df["aum_tgl"].dropna().iloc[-1]) if df["aum_tgl"].notna().any() else None}


def jalan():
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    db = d.koneksi()
    semua = daftar(db)
    hasil = {}
    for kode in UTAMA + TAMBAHAN:
        info = semua.get(kode)
        if not info:
            print(f"  {kode}: tidak ada di rd_etf, dilewati")
            continue
        df = bangun(db, kode, info)
        if df is None:
            print(f"  {kode}: tidak ada data bursa, dilewati")
            continue
        dt.tulis(f"{KOLEKSI}/{kode}", df)
        r = ringkas(df)
        r["nama"] = info["nama"]
        r["pencocokan_manual"] = info["manual"]
        r["utama"] = kode in UTAMA
        hasil[kode] = r
    dt.simpan_hasil("etf_emas_ringkas", {"dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"), "etf": hasil,
                                           "catatan": ["Nilai transaksi = close x volume Yahoo (ETF tidak ada di ringkasan perdagangan IDX).",
                                                       "Premium = close / NAV Pasardana hari yang sama; NAV hari T terbit malam, hari tanpa NAV = kosong.",
                                                       "AUM = AssetUnderManagement Pasardana pada tanggal terbit AUM (bukan harian)."]})
    tampil(hasil)
    print("SELESAI")


def seleksi(frames, aum, nama=None, sampai=None, hari=HARI_PILIH, kecuali=()):
    kandidat = []
    for kode, df in frames.items():
        if kode in kecuali:
            continue
        ekor = df if sampai is None else df.loc[:sampai]
        ekor = ekor.tail(hari)
        if not len(ekor):
            continue
        prem = ekor["premium"].dropna().abs()
        a = aum.get(kode)
        nilai = float(ekor["nilai"].median())
        med = float(prem.median()) if len(prem) else None
        alasan = []
        if a is None or a < MIN_AUM:
            alasan.append("AUM < Rp10 M")
        if nilai < MIN_NILAI:
            alasan.append("median nilai transaksi 60 hari < Rp10 jt")
        if med is None:
            alasan.append("tidak ada premium")
        kandidat.append({"kode": kode, "nama": (nama or {}).get(kode, kode), "aum": a, "nilai_median": nilai, "premium_mutlak_median": med, "hari_data": int(len(ekor)),
                         "hari_premium": int(len(prem)), "lolos": not alasan, "alasan": alasan})
    lolos = sorted([k for k in kandidat if k["lolos"]], key=lambda k: (k["premium_mutlak_median"], -(k["aum"] or 0)))
    return {"terpilih": lolos[0]["kode"] if lolos else None, "kandidat": kandidat, "hari": hari}


def pilih_awal(sel):
    kand = sel["kandidat"]
    lolos = [k for k in kand if k["lolos"]]
    cukup = [k for k in lolos if k["hari_premium"] >= sel["hari"]]
    if cukup:
        k = sorted(cukup, key=lambda x: (x["premium_mutlak_median"], -(x["aum"] or 0)))[0]
        tier = "normal"
        alasan = f"aturan normal: lolos AUM dan nilai transaksi, data premium {sel['hari']} hari, median |premium| terendah ({k['premium_mutlak_median'] * 100:.2f}%)"
    elif lolos:
        k = sorted(lolos, key=lambda x: (-x["hari_premium"], x["premium_mutlak_median"], -(x["aum"] or 0)))[0]
        tier = "riwayat_terpanjang"
        alasan = (f"amandemen a2: tidak ada kandidat lolos dengan data premium >= {sel['hari']} hari; dipilih riwayat data premium terpanjang di antara yang lolos "
                  f"AUM dan nilai transaksi ({k['hari_premium']} hari)")
    else:
        ada = [x for x in kand if x["hari_premium"] > 0]
        k = sorted(ada, key=lambda x: (-x["hari_premium"], -x["nilai_median"]))[0] if ada else None
        tier = "riwayat_terpanjang_tanpa_filter"
        alasan = ("amandemen a2: tidak ada kandidat lolos filter AUM/nilai transaksi; dipilih riwayat data premium terpanjang tanpa filter, kaki emas tidak boleh default ke kas"
                  if k else "tidak ada ETF emas dengan data premium")
    hasil = dict(sel)
    hasil["terpilih"] = k["kode"] if k else None
    hasil["tier"] = tier
    hasil["alasan_pilih"] = alasan
    return hasil


def pilih(hari=HARI_PILIH):
    ring = (dt.baca_hasil("etf_emas_ringkas") or {}).get("etf") or {}
    frames = {k: dt.baca(f"{KOLEKSI}/{k}") for k in ring if dt.ada(f"{KOLEKSI}/{k}")}
    return seleksi(frames, {k: r.get("aum") for k, r in ring.items()}, {k: r["nama"] for k, r in ring.items()}, hari=hari)


def verifikasi_kode():
    db = d.koneksi()
    peng = dt.db()["pengumuman"]
    hasil = {}
    semua = daftar(db)
    nav_akhir = {k: float(nav_seri(db, v["id"]).iloc[-1]) for k, v in semua.items() if len(nav_seri(db, v["id"]))}
    for kode, info in semua.items():
        nav = nav_seri(db, info["id"])
        awal = peng.find_one({"kode": kode, "judul": {"$regex": "Pencatatan Awal ETF"}}, sort=[("tgl", 1)])
        tgl_awal = str(awal["tgl"])[:10] if awal else None
        nav_awal = str(nav.index.min().date()) if len(nav) else None
        h = dt.baca(f"{KOLEKSI}/{kode}") if dt.ada(f"{KOLEKSI}/{kode}") else None
        skala = None
        if h is not None and len(h) and kode in nav_akhir:
            c = float(h["close"].iloc[-1])
            selisih = sorted((abs(c / v - 1), k) for k, v in nav_akhir.items())
            skala = {"close": c, "paling_dekat": selisih[0][1], "selisih_terdekat": round(selisih[0][0], 4), "selisih_berikut": round(selisih[1][0], 4) if len(selisih) > 1 else None,
                     "unik": selisih[0][1] == kode and (len(selisih) < 2 or selisih[1][0] > 3 * selisih[0][0])}
        hasil[kode] = {"produk": info["nama"], "skala_harga_vs_nav": skala, "pencatatan_awal_idx": tgl_awal, "nav_pertama_produk": nav_awal, "cocok": bool(tgl_awal and tgl_awal == nav_awal),
                       "pengumuman_ada": int(peng.count_documents({"kode": kode}))}
    return hasil

def rp(x):
    return "-" if x is None else f"{x / 1e6:,.1f} jt" if abs(x) < 1e9 else f"{x / 1e9:,.2f} M"


def pc(x):
    return "-" if x is None else f"{x * 100:+.1f}%"


def tampil(hasil):
    print(f"{'ETF':<6}{'sejak':<12}{'hari':>5}{'NAV':>5}{'prem med':>9}{'min':>8}{'maks':>8}{'|prem|med':>10}{'nilai med/hari':>16}{'tanpa trx':>10}{'AUM':>10}")
    for k, r in hasil.items():
        print(f"{k:<6}{r['mulai']:<12}{r['hari']:>5}{r['hari_ada_nav']:>5}{pc(r['premium_median']):>9}{pc(r['premium_min']):>8}{pc(r['premium_maks']):>8}"
              f"{pc(r['mutlak_median']):>10}{rp(r['nilai_median_harian']):>16}{r['hari_tanpa_transaksi']:>10}{rp(r['aum']):>10}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verifikasi":
        for k, v in verifikasi_kode().items():
            print(k, v)
    elif len(sys.argv) > 1 and sys.argv[1] == "tampil":
        tampil(dt.baca_hasil("etf_emas_ringkas")["etf"])
    else:
        jalan()
