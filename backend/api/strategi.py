from backend.paper import tren_harian as th
from backend.riset import screener as sc


def rp(v):
    return f"Rp{v / 1e9:,.0f} miliar".replace(",", ".")


TREN52 = {
    "id": "tren52",
    "nama": "Follow Tren",
    "kode": "H11a",
    "kelas": "Saham syariah IDX",
    "status": "paper",
    "status_label": "Paper trade",
    "ringkas": "Saham yang harganya baru mencetak rekor tertinggi dalam setahun biasanya sedang dalam tren naik. Strategi ini membeli saham syariah seperti itu, menahannya selama harga terus naik, dan menjualnya otomatis begitu harga turun cukup jauh dari puncaknya. Tidak ada tebak-tebakan dan tidak ada target untung.",
    "gaya": "Dulu bernama Ikut Tren / Tren 52 Minggu · trend following · rata-rata ditahan ±31 hari bursa · maksimal 10 saham",
    "langkah": [
        {"judul": "Cari", "teks": "Tiap sore dicari saham syariah yang ramai diperdagangkan dan harga penutupannya menembus rekor tertinggi 52 minggu."},
        {"judul": "Beli", "teks": "Besok pagi dibeli di harga pembukaan, masing-masing 10% dari modal, maksimal 10 saham sekaligus."},
        {"judul": "Jaga", "teks": "Pasang batas jual di bawah harga tertinggi sejak beli (±10%). Batas ini ikut naik saat harga naik, tidak pernah turun."},
        {"judul": "Jual", "teks": "Kalau harga penutupan jatuh di bawah batas itu, saham dijual besok pagi. Untung dikunci, rugi dibatasi."},
    ],
    "harapan": "Lebih sering rugi kecil daripada untung (cuma ±1 dari 3 trade yang untung, rugi rata-rata ±10%), tapi trade yang untung rata-rata naik ±35% dan sesekali sampai ratusan persen. Hasil backtest 2020-2026 ±23% per tahun, tapi itu terbantu reli saham kecil, jadi harapan realistis lebih rendah. Pernah turun hampir 40% dari puncak.",
    "variabel": [
        {"grup": "Universe (saham yang boleh dibeli)", "isi": [
            {"nama": "Status syariah", "nilai": "Masuk DES OJK pada hari sinyal", "ket": "Daftar Efek Syariah periode yang berlaku (1 Jun / 1 Des). Saham yang keluar DES tidak dibeli lagi."},
            {"nama": "Likuiditas", "nilai": f"Nilai transaksi rata-rata 20 hari ≥ {rp(sc.MIN_VALUE)}", "ket": "Supaya bisa beli dan jual tanpa menggeser harga."},
            {"nama": "Harga minimum", "nilai": f"≥ Rp{sc.HARGA_MIN}", "ket": "Menghindari saham gocap."},
            {"nama": "Volatilitas", "nilai": f"ATR 14 hari {sc.ATR_MIN:g}%–{sc.ATR_MAKS:g}% dari harga".replace(".", ","), "ket": "Terlalu tenang = tren lambat, terlalu liar = stop terlalu lebar."},
            {"nama": "Aktif diperdagangkan", "nilai": "Tidak ada hari volume 0 dalam 5 hari terakhir", "ket": "Menghindari saham suspensi / tidur."},
        ]},
        {"grup": "Sinyal beli", "isi": [
            {"nama": "Breakout 52 minggu", "nilai": "Close ≥ close tertinggi 250 hari bursa sebelumnya", "ket": "Harga disesuaikan dividen dan split. Dicek setiap sore setelah data penutupan final."},
            {"nama": "Pemilihan", "nilai": f"Maksimal {th.MAKS_POSISI} posisi; kalau sinyal lebih banyak dari slot kosong, dipilih acak", "ket": "Acak dengan seed tanggal, jadi bisa diulang persis. Tidak ada prioritas (prioritas momentum diuji di H13 dan tidak membantu)."},
        ]},
        {"grup": "Eksekusi", "isi": [
            {"nama": "Waktu beli", "nilai": "Harga open hari bursa berikutnya", "ket": "Batal kalau saham terkunci ARA (high = low dan open di atas close kemarin)."},
            {"nama": "Ukuran posisi", "nilai": f"{th.BOBOT * 100:.0f}% ekuitas saat beli, kelipatan {th.LOT} lembar, dibatasi kas", "ket": "Kalau 1 lot melebihi jatah, sinyal batal (makanya modal kecil sering batal)."},
            {"nama": "Biaya", "nilai": f"Fee beli {sc.FEE_BELI:g}% + jual {sc.FEE_JUAL:g}% + selisih 1 tick per sisi".replace(".", ","), "ket": "Rata-rata ±1,2% pulang-pergi. Ini yang membuat swing pendek gagal."},
        ]},
        {"grup": "Keluar (stop)", "isi": [
            {"nama": "Stop awal", "nilai": f"Harga beli − {th.MULT_ATR:g}×ATR14 hari sinyal", "ket": "Rata-rata ±10% di bawah harga beli."},
            {"nama": "Trailing stop", "nilai": f"Close tertinggi sejak beli − {th.MULT_ATR:g}×ATR14, tidak pernah turun", "ket": "Awalnya membatasi rugi, lalu mengunci untung saat harga naik."},
            {"nama": "Sinyal jual", "nilai": "Close < stop → jual di open hari berikutnya", "ket": "Kalau terkunci ARB (high = low), tunggu sampai bisa jual."},
            {"nama": "Target untung", "nilai": "Tidak ada", "ket": "Untung datang dari sedikit trade yang naik puluhan sampai ratusan persen; memotongnya merusak hasil."},
            {"nama": "Batas waktu", "nilai": f"{th.MAKS_HARI} hari bursa", "ket": "Hampir tidak pernah tercapai; pengaman saja."},
        ]},
        {"grup": "Lain-lain", "isi": [
            {"nama": "Dividen", "nilai": f"Dikreditkan ke kas, dipotong pajak {th.PAJAK_DIVIDEN * 100:.0f}%", "ket": "Di hari ex-date untuk posisi yang dipegang."},
            {"nama": "Data", "nilai": "Harga harian Yahoo Finance (2 tahun terakhir), DES dari OJK", "ket": "Hari bursa ditentukan dari tanggal data saham, bukan IHSG."},
        ]},
    ],
    "tidak_dipakai": [
        {"nama": "Fundamental (laba, pendapatan)", "uji": "H14", "hasil": "Membuang saham yang naik paling tinggi; MAR turun 0,80 → 0,57."},
        {"nama": "Filter pasar (IHSG di atas rata-rata 200 hari)", "uji": "H13", "hasil": "Tidak memperbaiki hasil di data independen."},
        {"nama": "Ukuran posisi berbasis risiko / prioritas momentum", "uji": "H13", "hasil": "Tidak memperbaiki hasil."},
        {"nama": "Buang saham volatil", "uji": "H12", "hasil": "Rugi mengecil tapi untung besar ikut hilang."},
        {"nama": "Kepemilikan ritel / institusi (KSEI)", "uji": "H15", "hasil": "Tidak konsisten; return turun."},
        {"nama": "Arus dana asing", "uji": "H7", "hasil": "Tidak berguna sendirian, rapuh sebagai tambahan."},
    ],
    "reset": [
        "Tombol Reset (ketik RESET) di halaman Paper trade. Hanya untuk paper trade strategi ini.",
        "Sebelum reset, seluruh database dibackup otomatis ke folder backup/.",
        "Posisi, transaksi, ekuitas, dan sinyal sesi lama dipindah ke arsip (bisa dilihat di 'Arsip sesi sebelumnya'), tidak dihapus.",
        "Setelah reset, isi modal baru lalu tekan Mulai. Paper mulai dari data penutupan terakhir; tidak ada posisi bawaan.",
        "Zona normal (batas wajar/gagal) TIDAK ikut direset: tetap h11a_v1 yang dikunci 22 Okt 2026, dan hari dihitung ulang dari awal sesi baru.",
        "Jangan reset hanya karena sedang rugi. Reset yang sah: ganti modal, salah setup, atau data rusak. Reset karena rugi = membuang bukti.",
    ],
    "angka": {"cagr": 23.1, "cagr_konservatif": 17.3, "dd": -39.7, "win_rate": 34, "periode": "2020-2026"},
}

HARIAN = "Otomatis tiap hari bursa: dihitung ulang dari harga harian saat Perbarui / jadwal 17:30"
TETAP = "Tetap (aturan dikunci)"
PEMBARUAN = {
    "Status syariah": "Otomatis: DES dicek jadwal (20 Mei-Jun, 20 Nov-Des) atau tombol Cek DES baru",
    "Likuiditas": HARIAN, "Harga minimum": HARIAN, "Volatilitas": HARIAN, "Aktif diperdagangkan": HARIAN, "Breakout 52 minggu": HARIAN,
    "Trailing stop": "Nilai stop dihitung ulang tiap hari; aturannya tetap",
    "Biaya": "Tetap. Hanya diubah kalau fee broker berubah, sebagai hipotesis baru",
    "Dividen": "Otomatis dari data harga Yahoo (tanggal ex-dividen)",
    "Data": "Lihat panel Sumber data di Beranda (paling bawah)",
}
for _g in TREN52["variabel"]:
    for _v in _g["isi"]:
        _v["pembaruan"] = PEMBARUAN.get(_v["nama"], TETAP)

RENCANA = [
    {"id": "etf_strategi", "nama": "Strategi ETF", "kelas": "ETF syariah Indonesia & luar negeri", "ikon": "layers", "status": "Data sudah ada",
     "ide": "Datanya sudah ada di menu ETF. Berikutnya menguji aturan di level ETF: beli-tahan vs Follow Tren pada SPUS, HLAL, XIJI, dan sejenisnya.",
     "beda": "Satu ETF = puluhan saham, jadi risiko satu emiten hilang. Biaya transaksi dan spread lebih kecil.",
     "data": "Sudah tersedia: harga ETF IDX dan ETF luar negeri dari Yahoo Finance, kurs USD/GBP.",
     "pertanyaan": "Apakah aturan tren pada ETF memberi hasil mirip dengan penurunan yang lebih dangkal?"},
    {"id": "emas", "nama": "Emas", "kelas": "Emas batangan / tabungan emas / ETF emas", "ikon": "gem", "status": "Data sebagian ada",
     "ide": "Pelindung saat saham turun dan rupiah melemah. Uji alokasi tetap (mis. 10-20%) + rebalance.",
     "beda": "Aset syariah yang jelas, korelasi rendah dengan saham IDX.",
     "data": "Sudah ada: harga emas dunia + kurs sejak 2010, ETF emas IDX (XTRA, XDES, XSGO, XKGS) sejak 2026. Harga Antam/buyback belum.",
     "pertanyaan": "Berapa porsi emas yang paling mengurangi penurunan portofolio tanpa banyak menurunkan hasil?"},
    {"id": "alokasi", "nama": "Alokasi Portofolio", "kelas": "Gabungan semua section", "ikon": "scale", "status": "Menunggu hasil",
     "ide": "Menggabungkan strategi yang lolos (mis. Follow Tren + dividen + sukuk + emas) dengan porsi tetap dan rebalance.",
     "beda": "Strategi yang korelasinya rendah membuat penurunan modal jauh lebih dangkal.",
     "data": "Dari hasil section lain. Menunggu paper Follow Tren dan uji maju Dividen berjalan cukup lama.",
     "pertanyaan": "Kombinasi mana yang memberi penghasilan paling stabil per bulan?"},
    {"id": "saham_as", "nama": "Saham AS", "kelas": "NYSE / NASDAQ", "ikon": "globe", "status": "Perlu keputusan",
     "ide": "Follow Tren pada saham AS likuid. Data jauh lebih panjang (1990-an) dan biaya lebih kecil, jadi uji lebih kuat.",
     "beda": "Perlu kurs USD/IDR, pajak dividen 15-30%, dan broker luar/aplikasi lokal.",
     "data": "Gratis: Yahoo Finance. Filter syariah: daftar konstituen indeks syariah (S&P 500 Shariah / Dow Jones Islamic) belum ditemukan gratis.",
     "pertanyaan": "Perlu keputusan: hanya saham yang lolos screening syariah, dan dari mana daftarnya?"},
    {"id": "kripto", "nama": "Kripto", "kelas": "BTC dan ETH saja", "ikon": "bitcoin", "status": "Perlu keputusan",
     "ide": "Tren / rata-rata bergerak dan alokasi kecil sebagai pelengkap portofolio. Pasar 24 jam, volatilitas sangat tinggi.",
     "beda": "Tidak ada dividen, penurunan historis -70% s/d -85%. Status syariah diperdebatkan: Ijtima Ulama MUI 2021 menyatakan haram sebagai mata uang, dan sebagai aset diperdagangkan hanya sah kalau memenuhi syarat sil'ah.",
     "data": "Gratis: Yahoo Finance / Binance API, harian sejak 2014 (BTC) dan 2017 (ETH).",
     "pertanyaan": "Perlu keputusan syariah dulu sebelum diuji."},
]


def semua():
    return {"aktif": [TREN52], "rencana": RENCANA}
