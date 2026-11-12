import os
import re
import subprocess
import sys
from datetime import datetime

import pandas as pd
from pymongo import MongoClient

from backend.core.config import ROOT
from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi as kdb
from backend.paper.tren_harian import koreksi_tanpa_transaksi, tutup_resmi_tanpa_transaksi

DB_CEK = "swing_cek"
KUNCI = {
    "paper_transaksi": ["tgl", "ticker", "aksi"],
    "paper_ekuitas": ["tgl"],
    "paper_sinyal": ["tgl"],
    "paper_posisi": ["ticker"],
}
MAKS_BEDA = 50
TOLERANSI_IDX = 0.0001
KONSTAN_MAKS = 0.001
JENDELA_SEBELUM, JENDELA_SESUDAH = 90, 14
POLA_AKSI = re.compile(r"bonus|pemecahan|stock split|reverse stock|penggabungan nilai|hmetd|hak memesan|penawaran umum terbatas", re.I)


def ticker_paper(prod):
    t = {p["ticker"] for p in prod.paper_posisi.find({}, {"ticker": 1})}
    t |= {x["ticker"] for x in prod.paper_transaksi.find({}, {"ticker": 1})}
    for s in prod.paper_sinyal.find({}, {"kandidat": 1, "terpilih": 1}):
        t |= set(s.get("kandidat") or []) | set(s.get("terpilih") or [])
    return t


def jenis_aksi(judul):
    j = judul.lower()
    if "bonus" in j:
        return "saham bonus"
    if "pemecahan" in j or "stock split" in j:
        return "pemecahan saham"
    if "reverse" in j or "penggabungan nilai" in j:
        return "penggabungan saham"
    return "HMETD / right issue"


def teks_rasio(r, jenis):
    if r > 1 and jenis == "saham bonus":
        n = 1 / (r - 1)
        if abs(n - round(n)) < 0.02 * n:
            return f"{round(n)}:1"
    return f"x{r:.4f}"


def pengumuman_aksi(kode, awal, akhir):
    dari, sampai = awal - pd.Timedelta(days=JENDELA_SEBELUM), akhir + pd.Timedelta(days=JENDELA_SESUDAH)
    hasil = []
    for x in dt.db()["pengumuman"].find({"kode": kode, "tgl": {"$gte": dari.to_pydatetime(), "$lte": sampai.to_pydatetime()}}, {"_id": 0, "judul": 1, "tgl": 1}):
        if POLA_AKSI.search(x.get("judul") or ""):
            hasil.append({"tgl": str(x["tgl"].date()), "judul": x["judul"][:120]})
    return sorted(hasil, key=lambda z: z["tgl"])


def tanggal_ex(kode, sejak):
    try:
        x = hg.harian(kode)
    except Exception:
        return None
    if x is None or "stock_splits" not in x:
        return None
    s = x["stock_splits"].fillna(0)
    s = s[(s != 0) & (s.index >= sejak)]
    return str(s.index[0].date()) if len(s) else None


def kelompok_beda(beda):
    g = {}
    for b in beda:
        g.setdefault(b["ticker"], []).append(b)
    hasil = []
    for kode, daftar in sorted(g.items()):
        r = [b["idx"] / b["paper"] for b in daftar if b.get("paper")]
        tgl = sorted(b["tgl"] for b in daftar)
        konstan = len(r) >= 2 and max(r) - min(r) < KONSTAN_MAKS
        aksi = None
        if konstan:
            peng = pengumuman_aksi(kode, pd.Timestamp(tgl[0]), pd.Timestamp(tgl[-1]))
            if peng:
                jenis = next((jenis_aksi(x["judul"]) for x in peng if "bonus" in x["judul"].lower()), jenis_aksi(peng[-1]["judul"]))
                aksi = {"jenis": jenis, "rasio": teks_rasio(sum(r) / len(r), jenis), "ex": tanggal_ex(kode, pd.Timestamp(tgl[-1])), "pengumuman": peng[-3:]}
        hasil.append({"kode": kode, "tgl_awal": tgl[0], "tgl_akhir": tgl[-1], "baris": len(daftar), "rasio_min": round(min(r), 4) if r else None,
                      "rasio_maks": round(max(r), 4) if r else None, "konstan": konstan, "kategori": "aksi_korporasi" if aksi else "harga_berbeda",
                      "dipakai": any(b["dipakai"] for b in daftar), "aksi": aksi})
    return hasil


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
    kode = [k for k in hg.harian_daftar() if not k.startswith("_")]
    harga = hg.harian_banyak(kode, ["open", "close", "adj_close", "volume"])
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
    per_kode = kelompok_beda(beda)
    kategori = {k["kode"]: k["kategori"] for k in per_kode}
    for b in beda:
        b["kategori"] = kategori[b["ticker"]]
    aksi_baris = sum(1 for b in beda if b["kategori"] == "aksi_korporasi")
    return {"per_kode": per_kode, "jumlah_aksi_korporasi": aksi_baris, "jumlah_acak": len(beda) - aksi_baris, "cocok_selain_aksi": len(beda) == aksi_baris,
            "cocok": not beda, "sampai_idx": str(idx["tgl"].max().date()), "hari": int(idx["tgl"].nunique()), "baris": dicek,
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
