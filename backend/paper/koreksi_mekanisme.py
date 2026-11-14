from datetime import datetime

from backend.db import koneksi as d

KOLEKSI = "koreksi_mekanisme"
KEBIJAKAN = ("Amandemen aturan hanya sebelum transaksi pertama dan hanya untuk bug atau look-ahead; a2 sah atas dasar ini. "
             "Setelah 1 Des 2026 tidak ada amandemen aturan. Perbaikan kode yang tidak mengubah isi aturan dicatat di koleksi koreksi_mekanisme.")
CATATAN_AMANDEMEN = ("Teks 'aturan' di status ini ditulis 12 Nov 2026 sebelum amandemen dan sengaja tidak diubah. Frasa 'Mulai hari bursa pertama Jan 2027' digantikan a1 (mulai 1 Des 2026), "
                     "'pemilihan ETF per 31 Des 2026' digantikan a1 (hari bursa terakhir Nov 2026) dan a2 (urutan tingkat pemilihan, premium sejajar). "
                     "Yang berlaku = teks aturan + a1 + a2. " + KEBIJAKAN)

ENTRI = [
    {"_id": "2026-11-12|a77c0ff|h11a", "tanggal": "2026-11-12", "commit": "a77c0ff", "strategi": "H11a/H29",
     "isi": "Penanganan split/bonus di tren_harian: posisi aktif disesuaikan (lot, harga masuk, stop, tertinggi) dengan catatan paper_catatan, kolom modal_rp ditambah ke paper_posisi (diisi untuk posisi aktif yang sudah ada), kolom rasio di transaksi.",
     "dampak": "Nol: belum ada split pada posisi paper sampai 14 Nov 2026, paper_transaksi kosong, aturan Follow Tren dan batas_paper tidak berubah. Satu-satunya perubahan data adalah modal_rp pada paper_posisi (turunan dari harga masuk x lot, nilai sama dengan rumus lama)."},
    {"_id": "2026-11-14|ef46f57|b1", "tanggal": "2026-11-14", "commit": "ef46f57", "strategi": "H35/H37",
     "isi": "B1: premium keputusan beli emas dihitung dari close ETF T-2 dibanding NAV berlabel hari bursa T-1 menurut kalender, bukan dari pergeseran baris data. Baris yang tidak ada = premium kosong = hari itu tidak beli dan tetap dihitung ke rem 15 hari.",
     "dampak": "Perbaikan implementasi a2: pada data dengan hari bolong versi lama bisa memakai NAV berlabel sesudah T-1. Aturan (batas +2%, rem 15 hari, 20% nilai transaksi) tidak berubah. Belum ada transaksi."},
    {"_id": "2026-11-14|ef46f57|b2", "tanggal": "2026-11-14", "commit": "ef46f57", "strategi": "H35/H37",
     "isi": "B2: hari terakhir bulan (rebalance Desember) ditentukan dari kalender libur_bursa, bukan dari data IHSG yang sudah termuat. Desember 2026 dan 2027 jatuh di 30 Des (31 Des libur bursa).",
     "dampak": "Mencegah rebalance sehari lebih awal bila data hari terakhir belum masuk. Aturan 'rebalance tiap Desember' tidak berubah; rebalance pertama tetap Desember 2027."},
    {"_id": "2026-11-14|ef46f57|b3", "tanggal": "2026-11-14", "commit": "ef46f57", "strategi": "H35/H37",
     "isi": "B3: MULAI, REBALANCE_PERTAMA, tanggal pilih ETF, dan batas cek transaksi pertama dibaca dari status terkunci di DB (amandemen a1); bila nilai di kode berbeda, job uji maju berhenti dengan error dan pemeriksa mencatat gagal.",
     "dampak": "Nol: nilai di kode sama dengan DB (MULAI 2026-12-01, rebalance pertama 2027, pilih ETF 2026-11-30)."},
    {"_id": "2026-11-14|ef46f57|b4", "tanggal": "2026-11-14", "commit": "ef46f57", "strategi": "H35/H37",
     "isi": "B4: AUM untuk seleksi ETF dibaca per tanggal seleksi (hari bursa terakhir Nov 2026), tidak lagi memakai tanggal hari job atau AUM terbaru bila data historisnya ada.",
     "dampak": "Mencegah AUM masa depan masuk seleksi. Kriteria seleksi (AUM >= Rp10 M, nilai transaksi 60 hari >= Rp10 jt) tidak berubah."},
    {"_id": "2026-11-14|66f61b6|e4", "tanggal": "2026-11-14", "commit": "66f61b6", "strategi": "H11a/H29/H35/H37",
     "isi": "Batas kejar ketinggalan: job paper H11a, paper H22, dan uji maju H35/H37 menolak memproses otomatis bila tertinggal lebih dari 10 hari bursa (berhenti dengan error, tidak ada data yang ditulis); sampai 10 hari tetap diproses berurutan per tanggal seperti biasa. Pemeriksa mencatat gagal untuk kasus >10 hari.",
     "dampak": "Nol pada hasil: pemrosesan hari terlewat sudah berurutan per tanggal sebelumnya (paper_cek memutar ulang dari nol dan cocok tiap hari; tes simulasi 3 dan 10 hari terlewat identik dengan jalan harian). Hanya menambah penolakan di atas 10 hari."},
    {"_id": "2026-11-14|fef2101|d", "tanggal": "2026-11-14", "commit": "fef2101", "strategi": "H11a/H29/H35/H37",
     "isi": "Jejak paper: snapshot harian posisi/status ke paper_riwayat (append-only) dan sidik per dokumen koleksi paper append-only ke paper_sidik; pemeriksa gagal bila dokumen lama berubah atau hilang.",
     "dampak": "Nol: hanya menambah koleksi baru, tidak mengubah koleksi paper yang ada."},
]


def catat(db, entri):
    dok = {"dicatat": datetime.now(), **entri}
    db[KOLEKSI].update_one({"_id": entri["_id"]}, {"$setOnInsert": dok}, upsert=True)


def pastikan(db=None):
    db = d.koneksi() if db is None else db
    for x in ENTRI:
        catat(db, x)
    for kode in ("h35", "h37"):
        st = db[f"paper_{kode}_status"]
        st.update_one({"_id": "status", "catatan_amandemen": {"$exists": False}}, {"$set": {"catatan_amandemen": CATATAN_AMANDEMEN}})
