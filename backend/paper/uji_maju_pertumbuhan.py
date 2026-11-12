import sys
from datetime import datetime

from backend.db import koneksi as d

MODAL = 100_000_000
ATURAN = 'ATURAN UJI MAJU H35 & H37 (dikunci 12 Nov 2026)\n\nUMUM\n- Mulai hari bursa pertama Jan 2027. Modal paper Rp100 jt masing-masing, sekali masuk.\n- Kaki lokal & global = produk yang sama dengan halaman Portofolio Pertumbuhan.\n- Rebalance tiap Desember ke target: H35 50/50, H37 40/40/20.\n- Biaya: komisi broker + pajak jual sesuai konvensi proyek, harga pasar (bukan NAV).\n\nKAKI EMAS (H37)\n1. Pemilihan ETF (per 31 Des 2026, dan setiap rebalance Desember):\n   dari ETF emas syariah dengan AUM >= Rp10 M DAN median nilai transaksi 60 hari >= Rp10 jt,\n   pilih median |premium| 60 hari terendah. Seri: AUM terbesar.\n   (Data sekarang: XGLD. Kode XMES & XBGS wajib diverifikasi sebelum 31 Des.)\n2. Aturan beli/jual emas:\n   - Order per hari maks 20% dari nilai transaksi ETF hari itu (dicicil).\n   - Beli hanya pada hari dengan premium <= +2%. Kalau lebih, hari itu dilewati.\n   - Batas 15 hari bursa: sisa yang belum terbeli dibeli di hari ke-15 di harga mana pun\n     (tetap maks 20% nilai transaksi; sisanya lagi dibeli hari-hari berikutnya), dicatat\n     sebagai kejadian.\n   - Jual saat rebalance: dicicil dengan batas 20% yang sama, tanpa syarat premium.\n   - Dana yang belum terbelanjakan menunggu sebagai kas (tanpa imbal hasil).\n3. Ganti ETF di luar Desember hanya kalau: delisting, AUM < Rp10 M, atau 5 hari bursa\n   berturut tanpa transaksi. Dicatat sebagai kejadian.\n\nYANG DINILAI (uji pelaksanaan, BUKAN bukti edge). Evaluasi pertama Jan 2028.\n1. Selisih return paper vs model backtest periode sama <= 1,5 poin/th (H35 & H37 masing-masing).\n2. Premium bersih emas (rata-rata premium saat beli - rata-rata premium saat jual, tertimbang\n   nilai) <= 1 poin. Selama belum ada jual, laporkan premium saat beli vs premium terkini.\n3. Biaya nyata total vs asumsi backtest (spread 3% pulang-pergi, 0,5%/th): laporkan angkanya.\n4. Laporkan juga: hari tertunda, jumlah kejadian, tracking ETF vs GC=F x kurs.\nGagal 1 atau 2 -> asumsi backtest H37 dinilai terlalu optimistis; H37 tidak dipakai untuk\nuang nyata sampai diuji ulang dengan biaya nyata.\n'
TGL_KUNCI = "2026-11-12"
KONFIG = {
    "h35": {"nama": "Syariah Global 50/50", "bobot": {"lokal": 0.5, "global": 0.5}},
    "h37": {"nama": "Syariah Global + Emas 40/40/20", "bobot": {"lokal": 0.4, "global": 0.4, "emas": 0.2}},
}
BAGIAN = ("posisi", "transaksi", "ekuitas", "kejadian")
INDEKS = {"posisi": [("kaki", 1)], "transaksi": [("tgl", 1), ("kaki", 1)], "ekuitas": [("tgl", 1)], "kejadian": [("tgl", 1)]}


def siapkan():
    db = d.koneksi()
    ada = set(db.list_collection_names())
    hasil = {}
    for kode, k in KONFIG.items():
        for b in BAGIAN:
            nama = f"paper_{kode}_{b}"
            if nama not in ada:
                db.create_collection(nama)
            db[nama].create_index(INDEKS[b])
        status = f"paper_{kode}_status"
        if status not in ada:
            db.create_collection(status)
        if not db[status].find_one({"_id": "status"}):
            db[status].insert_one({"_id": "status", "kode": kode.upper(), "nama": k["nama"], "bobot": k["bobot"], "modal": MODAL,
                                   "aktif": False, "dikunci": False, "draf": True, "mulai_rencana": "hari bursa pertama Jan 2027",
                                   "evaluasi_pertama": "Jan 2028", "dibuat": datetime.now()})
        hasil[kode] = {c: db[c].count_documents({}) for c in [status] + [f"paper_{kode}_{b}" for b in BAGIAN]}
    return hasil


def kunci():
    db = d.koneksi()
    siapkan()
    for kode in KONFIG:
        st = db[f"paper_{kode}_status"]
        if st.find_one({"_id": "status"}).get("dikunci"):
            print(f"{kode.upper()} sudah dikunci, tidak ditimpa.")
            continue
        st.update_one({"_id": "status"}, {"$set": {"dikunci": True, "draf": False, "aktif": False, "tgl_kunci": TGL_KUNCI, "dikunci_pada": datetime.now(),
                                                   "aturan": ATURAN, "aktif_otomatis": "hari bursa pertama Jan 2027"}})
        print(f"{kode.upper()} dikunci {TGL_KUNCI}, aktif=False")
    print(ATURAN)


AMANDEMEN_1 = {"id": "a1", "tgl": "2026-11-12", "mulai": "2026-12-01",
               "teks": "Tanggal mulai diubah dari hari bursa pertama Jan 2027 menjadi hari bursa pertama Des 2026 (1 Des 2026). Alasan: produk nyata sudah tersedia, menambah data uji maju. "
                       "Dibuat sebelum ada transaksi atau hasil uji maju apa pun. Aturan lain tidak berubah. Rebalance Desember 2026 dilewati (baru masuk); rebalance pertama Desember 2027. "
                       "Pemilihan ETF emas pertama: per hari bursa terakhir Nov 2026 (bukan 31 Des). Evaluasi pertama tetap Jan 2028 (13 bulan data). "
                       "Setelah amandemen ini teks aturan tidak boleh diubah lagi; hasil uji kering (simulasi mulai 2 Nov) hanya untuk memperbaiki bug mesin, bukan mengubah aturan."}


def amandemen():
    db = d.koneksi()
    for kode in KONFIG:
        st = db[f"paper_{kode}_status"]
        dok = st.find_one({"_id": "status"})
        if any(a.get("id") == AMANDEMEN_1["id"] for a in dok.get("amandemen") or []):
            print(f"{kode.upper()} amandemen a1 sudah tercatat.")
            continue
        if db[f"paper_{kode}_transaksi"].count_documents({}) or db[f"paper_{kode}_posisi"].count_documents({}):
            raise SystemExit(f"{kode.upper()} sudah ada transaksi/posisi, amandemen pra-mulai ditolak")
        st.update_one({"_id": "status"}, {"$push": {"amandemen": {**AMANDEMEN_1, "dicatat": datetime.now()}},
                                           "$set": {"mulai_rencana": "hari bursa pertama Des 2026 (1 Des 2026)", "aktif_otomatis": "hari bursa pertama Des 2026 (1 Des 2026)",
                                                    "rebalance_pertama": "Desember 2027", "pilih_etf_pertama": "hari bursa terakhir Nov 2026"}})
        print(f"{kode.upper()} amandemen a1 dicatat")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "siapkan":
        for kode, isi in siapkan().items():
            print(kode, isi)
        print("SELESAI")
    elif len(sys.argv) > 1 and sys.argv[1] == "amandemen":
        amandemen()
        print("SELESAI")
    elif len(sys.argv) > 1 and sys.argv[1] == "kunci":
        kunci()
        print("SELESAI")
    else:
        raise SystemExit("pakai: siapkan | kunci")
