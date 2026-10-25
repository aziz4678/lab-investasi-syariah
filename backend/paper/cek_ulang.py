import os
import subprocess
import sys
from datetime import datetime

import pandas as pd
from pymongo import MongoClient

from backend.core.config import ROOT
from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.paper.tren_harian import koreksi_tanpa_transaksi, tutup_resmi_tanpa_transaksi

DB_CEK = "swing_cek"
KUNCI = {
    "paper_transaksi": ["tgl", "ticker", "aksi"],
    "paper_ekuitas": ["tgl"],
    "paper_sinyal": ["tgl"],
    "paper_posisi": ["ticker"],
}
MAKS_BEDA = 20
TOLERANSI_IDX = 0.0001


def ticker_paper(prod):
    t = {p["ticker"] for p in prod.paper_posisi.find({}, {"ticker": 1})}
    t |= {x["ticker"] for x in prod.paper_transaksi.find({}, {"ticker": 1})}
    for s in prod.paper_sinyal.find({}, {"kandidat": 1, "terpilih": 1}):
        t |= set(s.get("kandidat") or []) | set(s.get("terpilih") or [])
    return t


def cek_idx(prod, mulai, sampai):
    m, s = pd.Timestamp(mulai), pd.Timestamp(sampai)
    if not dt.ada("idx_harian"):
        return {"cocok": None, "pesan": "data idx_harian belum ada"}
    idx = dt.baca("idx_harian", kolom=["tgl", "StockCode", "OpenPrice", "Close", "Volume"])
    idx = idx[(idx["tgl"] >= m) & (idx["tgl"] <= s)]
    kal = pd.DatetimeIndex(sorted({pd.Timestamp(e["tgl"]) for e in prod.paper_ekuitas.find({}, {"tgl": 1})}))
    kal = kal[(kal >= m) & (kal <= s)]
    ada = set(idx["tgl"].unique())
    belum = [str(t.date()) for t in kal if t not in ada]
    if idx.empty:
        return {"cocok": None, "hari": 0, "belum_dicek": belum, "pesan": "idx_harian belum mencakup periode paper; jalankan 'Ambil otomatis' ringkasan perdagangan IDX"}
    dipakai = ticker_paper(prod)
    kode = [k for k in dt.daftar("harian") if not k.startswith("_")]
    harga = dt.baca_banyak("harian", kode, ["open", "close", "adj_close", "volume"])
    resmi = tutup_resmi_tanpa_transaksi(m)
    beda, tanpa_transaksi, dicek = [], 0, 0
    for k, g in idx.groupby("StockCode"):
        y0 = harga.get(k)
        if y0 is None:
            continue
        y = koreksi_tanpa_transaksi(y0, resmi.get(k))
        mentah_beda = (y0["close"] - y["close"]).abs() > 1e-9
        tanpa_transaksi += int(mentah_beda[(mentah_beda.index >= m) & (mentah_beda.index <= s)].sum())
        for r in g.itertuples():
            dicek += 1
            pakai = k in dipakai
            if r.tgl not in y.index:
                if r.Volume > 0:
                    beda.append({"ticker": k, "tgl": str(r.tgl.date()), "jenis": "hilang di data paper", "idx": float(r.Close), "paper": None, "dipakai": pakai})
                continue
            b = y.loc[r.tgl]
            for kol, angka in (("close", r.Close), ("open", r.OpenPrice)):
                if kol == "open" and (not pakai or r.Volume == 0):
                    continue
                if angka > 0 and abs(float(b[kol]) / float(angka) - 1) > TOLERANSI_IDX:
                    beda.append({"ticker": k, "tgl": str(r.tgl.date()), "jenis": kol, "idx": float(angka), "paper": float(b[kol]), "dipakai": pakai})
    beda.sort(key=lambda x: (not x["dipakai"], x["tgl"], x["ticker"]))
    return {"cocok": not beda, "sampai_idx": str(idx["tgl"].max().date()), "hari": int(idx["tgl"].nunique()), "baris": dicek,
            "jumlah_beda": len(beda), "beda_dipakai": sum(x["dipakai"] for x in beda), "beda": beda[:MAKS_BEDA],
            "tanpa_transaksi_dikoreksi": tanpa_transaksi, "belum_dicek": belum}


def rapikan(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, list):
        return [rapikan(x) for x in v]
    if isinstance(v, dict):
        return {k: rapikan(x) for k, x in v.items()}
    return v


def susun(db, koleksi):
    hasil = {}
    for dok in map(rapikan, db[koleksi].find({}, {"_id": 0})):
        k = tuple(str(dok.get(x)) for x in KUNCI[koleksi])
        hasil.setdefault(k, []).append(dok)
    return hasil


def bandingkan(prod, cek, sampai):
    beda = []
    for koleksi in KUNCI:
        a, b = susun(prod, koleksi), susun(cek, koleksi)
        if koleksi != "paper_posisi":
            a = {k: v for k, v in a.items() if k[0] <= str(sampai)}
            b = {k: v for k, v in b.items() if k[0] <= str(sampai)}
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                beda.append({"koleksi": koleksi, "kunci": " · ".join(k), "paper": str(a.get(k))[:300], "ulang": str(b.get(k))[:300]})
    sa = prod.paper_status.find_one({"_id": "status"}) or {}
    sb = cek.paper_status.find_one({"_id": "status"}) or {}
    for k in ["kas", "tgl_terakhir"]:
        if sa.get(k) != sb.get(k):
            beda.append({"koleksi": "paper_status", "kunci": k, "paper": str(sa.get(k)), "ulang": str(sb.get(k))})
    return beda


def utama():
    prod = kdb.koneksi()
    if prod.name == DB_CEK:
        raise SystemExit("jalankan dari db produksi, bukan db cek")
    status = prod.paper_status.find_one({"_id": "status"})
    pertama = prod.paper_ekuitas.find_one(sort=[("tgl", 1)])
    if not status or not pertama:
        print("Paper trade belum dimulai, tidak ada yang dicek.")
        return
    mulai = pertama["tgl"].date()
    sampai = status["tgl_terakhir"]
    klien = MongoClient(os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017"))
    klien.drop_database(DB_CEK)
    cek = klien[DB_CEK]
    cek.des.insert_many(list(prod.des.find({}, {"_id": 0})))
    print(f"Menjalankan ulang paper trade dari nol: {mulai} s/d {sampai}, modal Rp{status['modal_awal']:,.0f} (db {DB_CEK}, data harga lokal)")
    env = {**os.environ, "SWING_MONGO_DB": DB_CEK, "PYTHONIOENCODING": "utf-8"}
    hasil = subprocess.run([sys.executable, "-m", "backend.paper.tren_harian", "--tanpa-unduh", "--mulai", str(mulai),
                            "--modal", str(status["modal_awal"]), "--sampai", sampai],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if hasil.returncode != 0:
        print(hasil.stdout[-2000:], hasil.stderr[-2000:])
        raise SystemExit("jalankan ulang gagal")
    beda = bandingkan(prod, cek, sampai)
    hari = cek.paper_ekuitas.count_documents({})
    idx = cek_idx(prod, mulai, sampai)
    dok = {"waktu": datetime.now(), "mulai": str(mulai), "sampai": sampai, "hari": hari, "cocok": not beda,
           "jumlah_beda": len(beda), "beda": beda[:MAKS_BEDA], "sesi": status.get("sesi"), "idx": idx}
    prod.paper_cek.insert_one(dok)
    klien.drop_database(DB_CEK)
    if beda:
        print(f"BEDA: {len(beda)} perbedaan antara paper tersimpan dan hasil jalankan ulang ({hari} hari).")
        for b in beda[:MAKS_BEDA]:
            print(f"  {b['koleksi']} {b['kunci']}\n    paper: {b['paper']}\n    ulang: {b['ulang']}")
        print("Kemungkinan: yfinance merevisi harga lama, data saham hilang, atau bug. Cek saham yang disebut.")
    else:
        print(f"COCOK: {hari} hari paper trade identik dengan hasil jalankan ulang (transaksi, posisi, ekuitas, sinyal).")
    if idx.get("cocok") is None:
        print(f"Cek silang IDX resmi: belum bisa ({idx.get('pesan')}).")
    elif idx["cocok"]:
        print(f"Cek silang IDX resmi: COCOK. {idx['baris']} harga ({idx['hari']} hari s/d {idx['sampai_idx']}) sama dengan ringkasan perdagangan IDX.")
    else:
        print(f"Cek silang IDX resmi: {idx['jumlah_beda']} BEDA ({idx['beda_dipakai']} di saham yang dipakai paper). Data paper tidak diubah otomatis.")
        for b in idx["beda"]:
            print(f"  {b['ticker']} {b['tgl']} {b['jenis']}: IDX {b['idx']} vs paper {b['paper']}{' (dipakai paper)' if b['dipakai'] else ''}")
    if idx.get("belum_dicek"):
        print(f"Belum ada data IDX untuk: {', '.join(idx['belum_dicek'])} (jalankan 'Ambil otomatis' ringkasan perdagangan IDX).")


if __name__ == "__main__":
    utama()
