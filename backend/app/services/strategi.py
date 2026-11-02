from backend.paper import tren_harian as th
from backend.research import screener as sc


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
        {"judul": "Cut loss", "jenis": "cl", "teks": "Batas jual dipasang ±10% di bawah harga beli. Kalau harga penutupan jatuh di bawahnya sebelum sempat naik, dijual besok pagi. Terjadi di ±2 dari 3 trade."},
        {"judul": "Take profit", "jenis": "tp", "teks": "Tanpa target angka. Batas jual ikut naik mengikuti harga tertinggi, tidak pernah turun. Dijual saat harga turun ±10% dari puncak. Contoh: beli 1.000, puncak 1.500 → jual ±1.380 (+38%)."},
    ],
    "harapan": "Lebih sering rugi kecil daripada untung (cuma ±1 dari 3 trade yang untung, rugi rata-rata ±10%), tapi trade yang untung rata-rata naik ±35% dan sesekali sampai ratusan persen. Backtest 2020-2026 ±20,9% per tahun (median 100 simulasi Monte Carlo, sesudah koreksi data harga 2026-11-02; dulu 22,8%), tapi setelah memperhitungkan ARA/ARB terkunci dan saham delisting yang tidak ada di data, angka realistis 2020-2026 ±15-20% per tahun. Ke depan bisa satu digit sampai belasan per tahun: hampir semua untung datang dari ±10 lonjakan besar, dan 2010-2019 hanya ±9% (di atas bobot sama syariah 7,2% dan JII 5,3%, tapi kalah dari IHSG 9,2%). Pernah turun hampir 40% dari puncak.",
    "detail": {"sub": "backtest", "teks": "Cara kerja beli, hold, TP & CL dengan data asli di Backtest →"},
    "tab": [["paper", "Paper trade"], ["backtest", "Backtest"], ["aturan", "Aturan & variabel"]],
    "paper": "h11a",
    "fitur": {"zona_paper": True, "tautan_blend": True, "biaya_rebalance": False},
    "hipotesis": {
        "kode": "H11a", "judul": "Hipotesis H11a: Follow Tren", "ket": "Apa yang diuji di backtest ini, dan sampai mana sekarang",
        "kalimat": "Saham syariah likuid yang harganya mencetak **rekor tertinggi setahun** cenderung melanjutkan kenaikan. Dengan **memotong rugi cepat** dan **membiarkan untung berjalan** lewat batas jual yang ikut naik, hasil totalnya mengalahkan memegang semua saham syariah secara rata, walau lebih sering rugi daripada untung.",
    },
    "perjalanan": [
        {"waktu": "Okt 2026", "judul": "Uji data lama 2010-2019", "isi": "Gagal tipis 6/7 (tahun positif 67% < 70%). CAGR 9,0% (median 100 simulasi, cara paper) di atas bobot sama syariah 7,2% dan JII 5,3%, tapi kalah dari IHSG 9,2%. Uji awal (laporan bulanan, 1 simulasi): 12,1% vs 8,1%.", "status": "selesai"},
        {"waktu": "Okt 2026", "judul": "Uji data baru 2020-2026", "isi": "Dibuka sekali sebagai pengecualian, aturan sama persis. Lulus 7 dari 7 kriteria.", "status": "selesai"},
        {"waktu": "21 Okt 2026", "judul": "Paper trade dimulai", "isi": "Uang pura-pura Rp100 jt, aturan dikunci, dijalankan tiap hari bursa.", "status": "jalan"},
        {"waktu": "1 Nov 2026", "judul": "Audit standar seragam", "isi": "Gagal standar seragam di dev, lulus 2020+. Kapasitas kecil: di saham likuid ≥ Rp20 M CAGR ±separuh (S2).", "status": "selesai"},
        {"waktu": "Jan 2027", "judul": "Cek eksekusi", "isi": "Hari ke-63: batas GAGAL mulai berlaku.", "status": "nanti"},
        {"waktu": "Apr 2027", "judul": "Cek tengah", "isi": "Bandingkan dengan zona wajar backtest.", "status": "nanti"},
        {"waktu": "Okt 2027", "judul": "Keputusan utama", "isi": "Tidak pernah WASPADA/GAGAL → uang nyata kecil 10-20%. Ditambah 1 Nov 2026: gagal juga kalau turun lebih dalam dari -45% atau ada bug eksekusi.", "status": "nanti"},
    ],
    "backtest": {"jenis": "versi", "cara_kerja": "tren", "olah": [["impor_fundamental", "Impor fundamental"], ["isi_backtest", "Hitung ulang backtest"]], "versi": {
        "h11a_2020": {"pendek": "2020-2026", "isi": "Uji utama: saham syariah menurut DES OJK pada tanggal itu.", "jii": -10.8},
        "h11a_2020_konservatif": {"pendek": "2020-2026 konservatif ARA/ARB", "isi": "Beli dibatalkan saat ARA terkunci, jual menunggu kalau ARB terkunci. Lebih realistis, tapi belum memperhitungkan saham delisting (survivorship).", "jii": -10.8},
        "h11a_dev": {"pendek": "2010-2019", "isi": "Data pengembangan (daftar 217 saham, ada bias survivorship). Dipakai menyusun aturan.", "jii": 5.3},
    }},
    "aturan_langkah": [
        {"judul": "Cari sinyal", "isi": "Setiap sore, cari saham syariah likuid yang harga penutupannya menembus titik tertinggi 250 hari bursa terakhir (±1 tahun)."},
        {"judul": "Beli di open besok", "isi": "Beli di harga pembukaan hari berikutnya. Maksimal 10 saham, masing-masing ±10% modal. Kalau sinyal lebih banyak dari slot kosong, dipilih acak."},
        {"judul": "Jual saat tren patah", "isi": "Stop = close tertinggi sejak beli − 3×ATR. Stop ikut naik, tidak pernah turun. Kalau close di bawah stop, jual di open besok. Tidak ada target untung."},
    ],
    "contoh_stop": {
        "judul": "Contoh trailing stop", "ket": "Beli di Rp1.000, ATR Rp30, jadi jarak stop 3 × 30 = Rp90 dari close tertinggi",
        "baris": [["Hari 1", "1.000", "1.000", "910", "Rugi maks -9%", ""], ["Hari 10", "1.150", "1.150", "1.060", "Untung +6% terkunci", "naik"],
                  ["Hari 20", "1.400", "1.400", "1.310", "Untung +31% terkunci", "naik"], ["Hari 25", "1.350", "1.400", "1.310 (tetap)", "–", ""],
                  ["Hari 30", "1.290", "1.400", "1.310, tembus", "Jual di open besok", "turun"], ["Hari 31", "Open 1.285", "", "", "Hasil ±28%", "naik"]],
        "catatan": "Selama harga naik, posisi dipegang tanpa batas atas. Penjualan terjadi sedikit di bawah puncak; itu ongkos supaya tidak keluar karena goyangan biasa.",
    },
    "risiko": [
        "Win rate cuma 30-40%. Rugi beruntun 10-16 kali pernah terjadi.",
        "Penurunan modal 30-40% dari puncak pernah terjadi, dan modal pernah hampir 3 tahun di bawah puncaknya (2021-2024).",
        "Untung datang dari sedikit trade yang naik puluhan sampai ratusan persen. Kalau trade besar itu terlewat, hasil setahun bisa negatif.",
        "Rugi per trade bisa -15% sampai -25% di saham volatil, terutama kalau jatuh tajam semalam atau kena ARB.",
        "Dihitung seperti paper (median 100 simulasi Monte Carlo), backtest 2020-2026 memberi ±20,9% per tahun dengan penurunan terdalam ±-42% (konservatif ARA/ARB ±20,3%) dan 2010-2019 hanya ±9,1%: di atas bobot sama syariah (7,1%) dan JII (5,3%), tapi kalah dari IHSG (9,2%). Angka sesudah koreksi data harga 2026-11-02 (dulu 22,8% / -38%): bar basi Yahoo menyembunyikan penurunan. Realistis untuk 2020-2026 ±15-20% per tahun; ke depan bisa satu digit sampai belasan.",
        "Kapasitas kecil: di saham yang lebih likuid (nilai transaksi ≥ Rp20 M) hasilnya kira-kira separuh. Cocok untuk modal pribadi kecil, tidak bisa diperbesar.",
        "Jangan ubah aturan di tengah jalan: melonggarkan stop, memasang target untung, atau memilih saham sendiri.",
    ],
    "panel_daftar": [],
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
        "Reset paper ini ikut memutus Momentum Blend (H29), karena bagian Follow Tren di H29 memakai paper ini.",
    ],
    "angka": {"cagr": 20.9, "cagr_konservatif": 20.3, "dd": -41.9, "win_rate": 33, "periode": "2020-2026"},
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

BLEND = {
    "id": "blend",
    "nama": "Momentum Blend",
    "kode": "H29",
    "kelas": "Saham syariah IDX",
    "status": "paper",
    "status_label": "Paper trade",
    "ringkas": "Modal dibagi dua. Separuh mengikuti aturan Follow Tren: beli saham syariah yang menembus rekor tertinggi setahun dan jual saat harga turun cukup jauh dari puncaknya. Separuh lagi mengikuti RS 12-1: tiap bulan memegang saham syariah yang paling naik dalam 12 bulan terakhir, tanpa menghitung bulan terakhir. Tiap akhir bulan porsinya dikembalikan ke 50/50.",
    "gaya": "Breakout 52W + RS 12-1 · dua cara momentum dalam satu modal · dikembalikan ke 50/50 tiap akhir bulan · RS 12-1 = H22",
    "langkah": [
        {"judul": "Bagi modal", "teks": "50% modal untuk bagian Follow Tren, 50% untuk bagian RS 12-1."},
        {"judul": "Follow Tren", "teks": "Beli saham syariah yang menembus rekor tertinggi 52 minggu, 10% dari bagiannya, maksimal 10 saham. Jual saat close turun 3×ATR dari puncak."},
        {"judul": "RS 12-1", "teks": "Tiap akhir bulan urutkan saham syariah likuid menurut kenaikan 12 bulan tanpa bulan terakhir, pegang ±20% teratas (minimal 10 saham). Dijual kalau peringkatnya jatuh ke luar 2× batas."},
        {"judul": "Kembali ke 50/50", "teks": "Tiap akhir bulan porsi kedua bagian disamakan lagi. Tidak ada target untung; bagian RS 12-1 tidak memakai stop."},
    ],
    "harapan": "Dibuat setelah melihat hasil: simulasi gabungan ±15% per tahun di kedua periode (2011-2019 14,8%, 2020-2026 14,7%) dan lebih stabil dari masing-masing bagian, tapi itu bukan bukti karena idenya muncul setelah data itu terlihat. RS 12-1 gagal di universe likuid ≥ Rp20 M (S2) dan Follow Tren tinggal ±separuh di sana, jadi kapasitasnya tetap kecil: hanya cocok untuk modal pribadi kecil. Di simulasi 2020-2026 pernah turun ±42% dari puncak. Satu-satunya bukti adalah paper trade sampai Nov 2027.",
    "detail": {"sub": "aturan", "teks": "Semua aturan yang dikunci & selisih paper vs simulasi di Aturan →"},
    "tab": [["paper", "Paper trade"], ["backtest", "Backtest"], ["aturan", "Aturan & variabel"]],
    "paper": "h29",
    "fitur": {"zona_paper": False, "tautan_blend": False, "biaya_rebalance": True},
    "hipotesis": {
        "kode": "H29", "judul": "Hipotesis H29: Momentum Blend", "ket": "Dibuat setelah melihat hasil · satu-satunya bukti adalah paper trade",
        "kalimat": "Menggabungkan **dua cara momentum yang berbeda** (breakout 52 minggu dengan stop, dan peringkat kenaikan 12 bulan tanpa stop) dengan **porsi tetap 50/50** membuat hasilnya **lebih stabil antar periode** daripada masing-masing sendiri. Hipotesis ini dibuat setelah data 2010-2026 terlihat, jadi angka lamanya bukan bukti.",
    },
    "perjalanan": [
        {"waktu": "1 Nov 2026", "judul": "Dibuat & dikunci", "isi": "Ide dari audit H11a & H22 setelah data 2010-2026 terlihat. Aturan dikunci tanpa penyetelan; angka historis bukan bukti.", "status": "selesai"},
        {"waktu": "2 Nov 2026", "judul": "Paper trade dimulai", "isi": "Bagian RS 12-1 membeli 22 saham di open 2 Nov; bagian Follow Tren = paper H11a yang sudah berjalan. Modal setara Rp100 jt.", "status": "jalan"},
        {"waktu": "Nov 2027", "judul": "Evaluasi 12 bulan", "isi": "1 Nov 2027: gagal kalau turun lebih dalam dari -45% atau ada bug eksekusi. Dibandingkan dengan Follow Tren, bobot sama, dan JII.", "status": "nanti"},
    ],
    "backtest": {
        "jenis": "versi",
        "versi": {
            "h29_2020": {"pendek": "2020-2026", "isi": "Simulasi gabungan di saham syariah menurut DES OJK pada tanggal itu. Bagian RS 12-1 di periode ini = eksplorasi.", "periode": "2020-2026"},
            "h29_dev": {"pendek": "2011-2019", "isi": "Simulasi gabungan di data lama (Follow Tren 217 saham, RS 12-1 kode DES 2019-2026, ada bias survivorship).", "periode": "2011-2019"},
        },
        "peringatan": "Dibuat setelah lihat hasil: ide Momentum Blend muncul setelah data 2010-2026 terlihat, jadi semua angka di tab ini bukan bukti. Gunanya hanya untuk memahami cara kerjanya dan seberapa naik-turunnya. Bukti hanya dari paper trade sampai Nov 2027.",
        "cara_kerja": "blend",
        "cara_ket": "dua bagian dalam satu modal, dikembalikan ke 50/50 tiap akhir bulan",
        "mc_catatan": "Di Momentum Blend hanya bagian Follow Tren yang memilih saham secara acak saat sinyal lebih banyak dari slot kosong. Bagian RS 12-1 selalu mengambil peringkat teratas, jadi tidak ikut diacak.",
        "kurva_ket": "Modal awal = 1x · 50% Follow Tren + 50% RS 12-1, dikembalikan ke 50/50 tiap akhir bulan tanpa biaya · harga pasar akhir bulan",
        "kurva_info": "Garis tebal = Momentum Blend. Garis lain = kalau seluruh modal hanya dipakai satu bagian saja, atau dibandingkan dengan membeli semua saham syariah likuid sama banyak (bobot sama), JII, dan IHSG.",
        "seri": [
            {"label": "Momentum Blend", "kunci": "ekuitas", "var": "--series-1", "lebar": 2.5, "putus": [], "isi": True},
            {"label": "Follow Tren saja", "kunci": "h11a", "var": "--series-2", "lebar": 1.5, "putus": [], "isi": False},
            {"label": "RS 12-1 saja", "kunci": "h22", "var": "--series-4", "lebar": 1.5, "putus": [], "isi": False},
            {"label": "Bobot sama syariah", "kunci": "beli_tahan", "var": "--series-3", "lebar": 1.5, "putus": [5, 4], "isi": False},
            {"label": "JII", "kunci": "jii", "var": "--series-5", "lebar": 1.5, "putus": [2, 3], "isi": False},
            {"label": "IHSG", "kunci": "ihsg", "var": "--series-3", "lebar": 1, "putus": [1, 3], "isi": False},
        ],
        "olah": [["isi_backtest_h29", "Hitung ulang simulasi"]],
        "olah_ket": "Pakai setelah data harga diperbarui · menghitung ulang 100 simulasi kedua periode, ±5-10 menit",
    },
    "istilah": [
        ["Momentum Blend", "Gabungan dua strategi momentum dalam satu modal: 50% Follow Tren dan 50% RS 12-1."],
        ["RS 12-1 (momentum 12-1)", "Peringkat saham menurut kenaikan harga 12 bulan terakhir, tanpa menghitung bulan terakhir. RS = relative strength, kekuatan relatif dibanding saham lain."],
        ["Kenapa bulan terakhir dilewati", "Saham yang naik tajam bulan lalu sering turun sedikit bulan berikutnya. Melewati 1 bulan terakhir menghindari efek balik ini."],
        ["Peringkat", "Urutan saham syariah likuid dari yang naik paling tinggi dalam 12 bulan (peringkat 1) ke yang paling rendah."],
        ["N (jumlah saham RS 12-1)", "Banyaknya saham yang dipegang bagian RS 12-1: 20% dari saham yang lolos syarat, minimal 10. Saat paper dimulai ±22 saham."],
        ["Batas 2N", "Saham yang sudah dipegang tetap dipegang selama peringkatnya masih di 2N teratas, supaya tidak bolak-balik jual beli dan bayar biaya."],
        ["Rebalance bulanan", "Pemeriksaan tiap akhir bulan: saham yang peringkatnya jatuh dijual, slot kosong diisi saham peringkat teratas, dieksekusi besok paginya di harga pembukaan."],
        ["Kembali ke 50/50", "Tiap akhir bulan nilai bagian Follow Tren dan RS 12-1 disamakan lagi. Bagian yang naik lebih banyak menyumbang ke bagian yang tertinggal."],
        ["Pangkas", "Menjual sebagian saham RS 12-1 yang bobotnya sudah lebih dari 2 kali jatah, kembali ke 1 jatah."],
        ["Bobot sama syariah", "Pembanding: semua saham syariah likuid dibeli sama banyak, diperbarui tiap bulan, tanpa biaya."],
        ["JII", "Jakarta Islamic Index: 30 saham syariah terbesar dan terlikuid. Di sini indeks harga, tanpa dividen."],
        ["Korelasi", "Seberapa sering dua bagian naik-turun bersamaan (1 = selalu bersama, 0 = tidak berhubungan). Makin rendah, makin berguna digabung."],
        ["Dibuat setelah lihat hasil", "Ide diuji di data yang sudah pernah dilihat, jadi hasil bagusnya bisa kebetulan. Bukti hanya dari data baru (paper trade)."],
    ],
    "aturan_langkah": [
        {"judul": "Bagi 50/50", "isi": "Modal dibagi dua bagian sama besar: Follow Tren (H11a) dan RS 12-1 (H22). Tiap bagian menjalankan aturannya sendiri dengan uangnya sendiri."},
        {"judul": "Jalankan dua aturan", "isi": "Follow Tren dicek tiap sore (breakout 52 minggu, stop 3×ATR). RS 12-1 dicek tiap akhir bulan (peringkat kenaikan 12 bulan tanpa bulan terakhir)."},
        {"judul": "Kembali ke 50/50", "isi": "Tiap akhir bulan nilai kedua bagian disamakan lagi. Return bulanan = 0,5 × return Follow Tren + 0,5 × return RS 12-1."},
    ],
    "variabel": [
        {"grup": "Porsi & pengembalian ke 50/50", "isi": [
            {"nama": "Porsi modal", "nilai": "50% Follow Tren, 50% RS 12-1", "ket": "Tetap, tidak disetel. Dihitung dari nilai H29 di akhir bulan sebelumnya.", "pembaruan": TETAP},
            {"nama": "Kembali ke 50/50", "nilai": "Tiap akhir bulan kalender (close hari bursa terakhir)", "ket": "Return bulanan H29 = 0,5 × return bagian Follow Tren + 0,5 × return bagian RS 12-1.", "pembaruan": "Otomatis tiap akhir bulan"},
            {"nama": "Biaya pemindahan", "nilai": "Angka utama tanpa biaya; angka kedua dipotong 1,34% dari nilai yang dipindah", "ket": "Fee jual 0,25% + fee beli 0,15% + 2 × tick rata-rata 0,47% (rata-rata trade backtest Follow Tren 2020+).", "pembaruan": TETAP},
        ]},
        {"grup": "Bagian Follow Tren (H11a)", "isi": [
            {"nama": "Aturan", "nilai": "Persis Follow Tren: breakout 52 minggu, 10% bagian, maks 10 saham, stop 3×ATR14 trailing", "ket": "Lihat menu Follow Tren → Aturan & variabel untuk rinciannya.", "pembaruan": TETAP},
            {"nama": "Paper", "nilai": "Paper Follow Tren yang sudah berjalan sejak 21 Okt 2026", "ket": "Lot 100, beli batal di candle ARA terkunci, jual ditunda di candle terkunci, ukuran posisi dari ekuitas close kemarin.", "pembaruan": HARIAN},
        ]},
        {"grup": "Bagian RS 12-1 (H22)", "isi": [
            {"nama": "Status syariah", "nilai": "Masuk DES OJK pada tanggal sinyal", "ket": "Saham yang keluar DES dijual di rebalance berikutnya.", "pembaruan": "Otomatis: DES dicek jadwal (20 Mei-Jun, 20 Nov-Des) atau tombol Cek DES baru"},
            {"nama": "Likuiditas", "nilai": "Median nilai transaksi 60 hari ≥ Rp5 miliar, harga ≥ Rp100", "ket": "Plus ≥ 250 hari data dan ada transaksi di ≥ 90% dari 250 hari terakhir.", "pembaruan": "Otomatis tiap akhir bulan"},
            {"nama": "Sinyal", "nilai": "Return close (disesuaikan dividen) akhir bulan t−12 → akhir bulan t−1", "ket": "Bulan terakhir dilewati karena sering berbalik. Peringkat 1 = naik paling tinggi.", "pembaruan": "Otomatis tiap akhir bulan"},
            {"nama": "Jadwal", "nilai": "Sinyal di close hari bursa terakhir bulan, eksekusi di open hari bursa pertama bulan berikutnya", "ket": "Tidak ada transaksi di tengah bulan kecuali transaksi yang tertunda.", "pembaruan": TETAP},
            {"nama": "Jumlah saham", "nilai": "N = maks(10, bulat(20% × saham lolos))", "ket": "Saat dikunci ±110 saham lolos → N = 22.", "pembaruan": "Otomatis tiap akhir bulan"},
            {"nama": "Tetap dipegang", "nilai": "Selama peringkat ≤ 2N dan masih lolos", "ket": "Penyangga supaya tidak bolak-balik jual beli. Slot kosong diisi peringkat teratas yang belum dipegang.", "pembaruan": TETAP},
            {"nama": "Bobot", "nilai": "Saham baru 1/N ekuitas bagian; dipangkas ke 1/N kalau bobot > 2/N", "ket": "Saham lama tidak diseimbangkan ulang kecuali terlalu besar.", "pembaruan": TETAP},
            {"nama": "Transaksi tertunda", "nilai": "Volume 0, atau candle satu harga dengan return ≥ +6,5% (beli) / ≤ -6,5% (jual)", "ket": "Dicoba lagi tiap hari bursa; beli tertunda dibatalkan di rebalance berikutnya.", "pembaruan": HARIAN},
            {"nama": "Stop / target", "nilai": "Tidak ada", "ket": "Keluar hanya karena peringkat turun atau keluar DES.", "pembaruan": TETAP},
        ]},
        {"grup": "Biaya & eksekusi", "isi": [
            {"nama": "Biaya", "nilai": f"Fee beli {sc.FEE_BELI:g}% + jual {sc.FEE_JUAL:g}% + selisih 1 tick per sisi".replace(".", ","), "ket": "Di kedua bagian, termasuk pemangkasan.", "pembaruan": "Tetap. Hanya diubah kalau fee broker berubah, sebagai hipotesis baru"},
            {"nama": "Lot", "nilai": "Kelipatan 100 lembar", "ket": "Sisa kas kecil tiap pembelian; saham mahal bisa batal kalau 1 lot melebihi jatah.", "pembaruan": TETAP},
            {"nama": "Dividen", "nilai": "Tunai, dipotong pajak 10%", "ket": "Bagian RS 12-1 paper memakai harga mentah + dividen tunai.", "pembaruan": "Otomatis dari data harga Yahoo (tanggal ex-dividen)"},
        ]},
        {"grup": "Syarat gagal & evaluasi (dikunci 2026-11-01)", "isi": [
            {"nama": "Evaluasi", "nilai": "1 Nov 2027 (12 bulan)", "ket": "Dibandingkan dengan Follow Tren, bobot sama universe syariah likuid, dan JII pada periode yang sama.", "pembaruan": TETAP},
            {"nama": "GAGAL", "nilai": "Drawdown lebih dalam dari -45%, atau bug eksekusi", "ket": "Drawdown dari angka utama (tanpa biaya pemindahan).", "pembaruan": "Dicek otomatis tiap hari bursa"},
            {"nama": "Bukan gagal", "nilai": "Hasil biasa-biasa saja atau rugi kecil", "ket": "Audit 2026-11-01: tahun tanpa lonjakan besar itu normal untuk strategi momentum.", "pembaruan": TETAP},
        ]},
    ],
    "panel_daftar": [
        {"judul": "Selisih metode paper vs simulasi", "ket": "Disengaja, bukan bug: angka paper tidak akan sama persis dengan simulasi",
         "isi": [
             "Bagian RS 12-1 paper memakai harga mentah + dividen tunai dipotong pajak 10%; simulasi memakai harga disesuaikan Yahoo (dividen masuk tanpa pajak).",
             "Lot 100 lembar di kedua bagian paper; simulasi memakai lembar pecahan.",
             "Bagian Follow Tren paper membatalkan beli di candle ARA terkunci dan menunda jual di candle terkunci (versi konservatif ARA/ARB); simulasi memakai versi dasar.",
             "Ukuran posisi dari ekuitas close hari sebelumnya (Follow Tren sejak 2 Nov 2026, RS 12-1 dari ekuitas close hari sinyal); simulasi RS 12-1 memakai ekuitas di harga open hari rebalance.",
             "Bagian RS 12-1 paper menyesuaikan jumlah lembar saat split dan mengunduh harga saham yang dipegang tapi sudah keluar DES; simulasi memakai data historis yang sudah disesuaikan.",
             "Paper Follow Tren memakai koreksi hari tanpa transaksi (close resmi IDX); simulasi tidak.",
             "Pemilihan acak sinyal Follow Tren di paper memakai seed = tanggal; simulasi memakai median 30/100 seed.",
         ]},
        {"judul": "Cek ulang & reset", "ket": "Supaya paper bisa dipercaya",
         "isi": [
             "Bagian RS 12-1 dijalankan ulang dari nol tiap hari bursa (job Cek ulang paper H29) dan dibandingkan dengan yang tersimpan.",
             "Pengecekan awal di data Agu-Okt 2026: keputusan rebalance sama persis dengan simulasi, selisih ekuitas paling besar 0,09%.",
             "Momentum Blend tidak punya tombol reset sendiri. Reset paper Follow Tren ikut memutus H29.",
         ]},
    ],
    "risiko": [
        "Dibuat setelah melihat hasil: stabilnya angka gabungan (14,8% vs 14,7%) bisa kebetulan.",
        "RS 12-1 sendirian runtuh di 2020-2026 (5,3% per tahun, pernah turun lebih dari 50% dari puncak), dan 8 dari 10 pemenang terbesarnya datang dari 2025 saja.",
        "Kapasitas kecil: RS 12-1 gagal di universe likuid ≥ Rp20 M dan Follow Tren tinggal ±separuh di sana.",
        "Pengembalian ke 50/50 hanya di atas kertas dan tanpa biaya di angka utama; di uang nyata perlu memindahkan dana antar dua bagian tiap bulan.",
        "Di simulasi 2020-2026 (dihitung harian) Momentum Blend pernah turun ±42% dari puncak (rentang 100 simulasi -40% s/d -44%), dekat batas gagal -45%. Penurunan sedalam itu bisa terulang.",
        "Jangan ubah porsi atau aturan di tengah jalan; perubahan = hipotesis baru.",
    ],
    "angka": {"cagr": 14.7, "dd": -32.7, "periode": "2020-2026 (simulasi, bukan bukti)"},
}

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
     "data": "Dari hasil section lain. Menunggu paper Follow Tren berjalan cukup lama.",
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
    return {"aktif": [TREN52, BLEND], "rencana": RENCANA}
