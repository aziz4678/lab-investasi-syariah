import json
import re
import sys
from collections import Counter
from datetime import datetime

from pymongo import UpdateOne

from backend.db import data as dt

KATEGORI = [
    ("ksei_5", "Pemegang saham di atas 5% (KSEI)", r"Pemegang Saham di atas 5\s*%"),
    ("ksei_1", "Pemegang saham di atas 1% (KSEI)", r"Pemegang Saham di atas 1\s*%"),
    ("kepemilikan", "Laporan kepemilikan saham", r"LAPORAN KEPEMILIKAN|Perubahan Kepemilikan|Struktur Pemegang Saham|Keterbukaan Informasi Pemegang Saham Tertentu"),
    ("pemantauan", "Papan pemantauan khusus", r"Pemantauan Khusus"),
    ("delisting", "Delisting / go private", r"Delisting|Penghapusan Pencatatan|Go Private|Perusahaan Tertutup"),
    ("suspensi", "Suspensi & pembukaan", r"Suspensi|Penghentian Sementara|Pembukaan Kembali Perdagangan|Pencabutan Penghentian"),
    ("tender", "Tender offer", r"Tender Offer|Penawaran Tender"),
    ("uma", "Unusual Market Activity", r"Unusual Market|\bUMA\b"),
    ("penjelasan", "Penjelasan ke bursa", r"Permintaan Penjelasan|Penjelasan atas|Volatilitas"),
    ("dividen", "Dividen", r"Dividen"),
    ("hmetd", "Right issue / penambahan modal", r"HMETD|Hak Memesan Efek|Penawaran Umum Terbatas|Penambahan Modal"),
    ("buyback", "Buyback", r"Pembelian Kembali|Buy ?back"),
    ("split", "Pemecahan / penggabungan saham", r"Pemecahan|Stock Split|Penggabungan Nilai Nominal|Reverse Stock"),
    ("rups", "RUPS", r"RUPS|Rapat Umum"),
    ("aksi", "Transaksi material & afiliasi", r"Transaksi Material|Transaksi Afiliasi|Benturan Kepentingan|Akuisisi|Penggabungan Usaha|Peleburan|Merger|Divestasi|Pelepasan|Kegiatan Usaha|kontrak penting|aset yang sifatnya penting"),
    ("fakta", "Fakta material & siaran pers", r"Fakta Material|Siaran Pers|Press Release|Perlu Diketahui Publik|Perubahan Nama"),
    ("laporan", "Laporan keuangan & tahunan", r"Laporan Keuangan|Laporan Tahunan|Laporan Keberlanjutan"),
    ("paparan", "Paparan publik", r"Paparan Publik|Public Expose"),
    ("direksi", "Manajemen & tata kelola", r"Direksi|Direktur|Komisaris|Sekretaris Perusahaan|Corporate Secretary|Komite|Internal Audit|Pengurus|Akuntan Publik"),
    ("utang", "Obligasi, sukuk & pinjaman", r"Obligasi|Sukuk|\bMTN\b|Medium Term|Pinjaman|Fasilitas Kredit|Pembayaran Bunga|Imbalan Efek|Kupon|Ijarah|Pelunasan|Jatuh Tempo|Pemeringkatan"),
    ("rutin", "Laporan rutin", r"Registrasi Pemegang Efek|Laporan Bulanan|Laporan Harian|Peredaran Unit|Structured Warrant|Waran Terstruktur|Liquidity Provider|Penggunaan Dana|Perubahan Alamat|Saham Hilang|Konfirmasi Emiten"),
    ("pencatatan", "Pencatatan efek", r"Pencatatan|Penawaran Umum Perdana|\bIPO\b"),
]
LABEL = {k: l for k, l, _ in KATEGORI} | {"lain": "Lainnya"}
POLA = [(k, re.compile(p, re.I)) for k, _, p in KATEGORI]
KOLEKSI = "pengumuman"
INFO = "pengumuman_info"


def kategori(judul):
    for k, p in POLA:
        if p.search(judul or ""):
            return k
    return "lain"


def kode_valid(k):
    k = (k or "").strip().upper()
    return k if re.fullmatch(r"[A-Z0-9]{4}", k) else None


def ubah(x):
    tgl = datetime.fromisoformat(x["tgl"][:19]) if x.get("tgl") else None
    kode = kode_valid(x.get("kode"))
    return {
        "_id": x["id"], "tgl": tgl, "kode": kode, "kode_asli": None if kode else (x.get("kode") or "").strip() or None,
        "no": x.get("no"), "judul": (x.get("judul") or "").strip(), "jenis": x.get("jenis"), "kategori": kategori(x.get("judul")),
        "lampiran": [{"url": a.get("url"), "nama": a.get("nama"), "utama": bool(a.get("utama"))} for a in x.get("lampiran") or [] if a.get("url")],
    }


def ringkasan():
    c = dt.db()[KOLEKSI]
    awal = c.find_one(sort=[("tgl", 1)])
    akhir = c.find_one(sort=[("tgl", -1)])
    per = {x["_id"]: x["n"] for x in c.aggregate([{"$group": {"_id": "$kategori", "n": {"$sum": 1}}}])}
    return {"total": c.estimated_document_count(), "dari": awal["tgl"] if awal else None, "sampai": akhir["tgl"] if akhir else None,
            "emiten": len(c.distinct("kode")), "per_kategori": per}


def impor():
    from backend.ingest.impor_browser import cari
    berkas = [f for f in cari("idx_pengumuman_*.json")]
    if not berkas:
        print("Tidak ada file idx_pengumuman_*.json di Downloads / folder proyek. Jalankan dulu script pengumuman IDX di Console.")
        return
    c = dt.db()[KOLEKSI]
    sebelum = c.estimated_document_count()
    dibaca = 0
    baru = 0
    for f in sorted(berkas, key=lambda f: f.name):
        nama = re.sub(r" \(\d+\)(?=\.json$)", "", f.name)
        if dt.waktu_arsip(f"pengumuman/{nama}") >= f.stat().st_mtime:
            continue
        baru += 1
        try:
            isi = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"LEWATI {f.name}: bukan JSON yang utuh (unduhan terputus?)")
            continue
        if not isinstance(isi, list):
            print(f"LEWATI {f.name}: format tidak dikenal")
            continue
        ops = [UpdateOne({"_id": d["_id"]}, {"$set": d}, upsert=True) for d in (ubah(x) for x in isi if x.get("id"))]
        for i in range(0, len(ops), 5000):
            c.bulk_write(ops[i:i + 5000], ordered=False)
        dt.simpan_arsip(f"pengumuman/{nama}", f.read_bytes(), "pengumuman")
        dibaca += len(isi)
        print(f"{f.name}: {len(isi)} pengumuman dibaca")
    if not baru:
        print("Semua file idx_pengumuman_*.json di Downloads sudah pernah diimpor. Jalankan script pengumuman IDX lagi untuk data baru.")
    c.create_index([("kode", 1), ("tgl", -1)])
    c.create_index([("kategori", 1), ("tgl", -1)])
    c.create_index([("tgl", -1)])
    r = ringkasan()
    dt.db()[INFO].replace_one({"_id": "ringkas"}, {"_id": "ringkas", "diimpor": datetime.now(), **r}, upsert=True)
    print(f"\nTotal di database: {r['total']} pengumuman (bertambah {r['total'] - sebelum}), {r['emiten']} emiten, "
          f"{r['dari']:%Y-%m-%d} s/d {r['sampai']:%Y-%m-%d}")
    print("Per kategori:")
    for k, n in sorted(r["per_kategori"].items(), key=lambda z: -z[1]):
        print(f"  {LABEL.get(k, k):40s} {n:7d}")
    lain = Counter(x["judul"][:60] for x in c.find({"kategori": "lain"}, {"judul": 1}).limit(20000))
    print("Contoh judul kategori Lainnya:", "; ".join(j for j, _ in lain.most_common(8)))


def bulan_terakhir():
    akhir = dt.db()[KOLEKSI].find_one(sort=[("tgl", -1)])
    return akhir["tgl"].strftime("%Y%m") if akhir else None


if __name__ == "__main__":
    {"impor": impor}[sys.argv[1] if len(sys.argv) > 1 else "impor"]()
