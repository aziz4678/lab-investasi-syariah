STATUS = [
    {"id": "gagal", "label": "Gagal", "warna": "turun",
     "arti": "Tidak memenuhi semua kriteria lulus yang dikunci sebelum uji. Ditutup tanpa variasi parameter."},
    {"id": "tidak_diadopsi", "label": "Tidak diadopsi", "warna": "abu",
     "arti": "Usulan perbaikan/filter untuk strategi lain. Aturan adopsinya tidak terpenuhi, jadi strategi induk tetap apa adanya."},
    {"id": "paper", "label": "Paper", "warna": "naik",
     "arti": "Dijalankan maju dengan uang virtual, aturan dikunci. Belum terbukti; dinilai dengan zona normal yang dikunci."},
    {"id": "uji_maju", "label": "Uji maju", "warna": "aksen",
     "arti": "Aturan dikunci dan dijalankan maju pada data yang belum ada (mulai tanggal tertentu)."},
    {"id": "dikunci", "label": "Dikunci", "warna": "kuning",
     "arti": "Hipotesis, aturan, dan kriteria sudah ditulis, tapi uji belum dijalankan."},
    {"id": "belum_dikunci", "label": "Belum dikunci", "warna": "garis",
     "arti": "Masih rencana. Aturan dan kriteria belum final, jadi belum boleh diuji."},
]

KATEGORI = [
    {"id": "screener", "label": "Screener ML"},
    {"id": "swing", "label": "Swing teknikal"},
    {"id": "kalender", "label": "Kalender & event"},
    {"id": "aliran", "label": "Aliran dana"},
    {"id": "tren", "label": "Tren & momentum"},
    {"id": "fundamental", "label": "Fundamental & valuasi"},
    {"id": "dividen", "label": "Dividen"},
    {"id": "indikator", "label": "Indikator klasik"},
    {"id": "rezim", "label": "Rezim pasar"},
    {"id": "faktor", "label": "Faktor & risiko"},
    {"id": "reksadana", "label": "Reksa dana"},
]

LENCANA = {
    "dev_gagal": "Dev gagal",
    "holdout_pengecualian": "Holdout pengecualian",
    "pasca_hasil": "Dibuat setelah lihat hasil",
}

BIAYA = "Fee beli 0,15% + jual 0,25% + selisih 1 tick per sisi (±1,2% pulang-pergi)."
LIKUID = "Lolos likuiditas di hari sinyal: nilai transaksi rata-rata 20 hari ≥ Rp5 M, ATR% 1,5-5, harga ≥ Rp50, tanpa hari volume nol dalam 5 hari."
U217 = "217 saham syariah dari daftar saat ini (syariah_tickers.txt): bias survivorship dan status syariah diketahui dari masa depan."
UDES = "Saham syariah menurut DES OJK pada tanggal sinyal (point-in-time)."
K6 = ["Expectancy bersih > 0", "Di atas pembanding (tahanan acak sama lama)", "Bootstrap 90% batas bawah > 0",
      "Tahun positif ≥ 70%", "Tanpa 10 trade terbaik tetap > 0", "Tanpa 5 ticker terbaik tetap > 0"]
TT = "tidak tercatat"


def k(teks, dev=None, holdout=None):
    isi = {"teks": teks}
    if dev is not None:
        isi["dev"] = {"nilai": dev[0], "ok": dev[1]}
    if holdout is not None:
        isi["holdout"] = {"nilai": holdout[0], "ok": holdout[1]}
    return isi


def k6(dev, holdout=None, teks=K6):
    return [k(t, dev[i], holdout[i] if holdout else None) for i, t in enumerate(teks)]


def a(periode, cagr=None, dd=None, trade=None, wr=None, net=None, net_ket="/trade", kotor=None, pemb=None,
      bh=None, bh_dd=None, bh_nama=None, ket=None, utama=False, ekstra=None, dd_label=None, tile=None, monte_carlo=None, info=None):
    return {"periode": periode, "cagr": cagr, "dd": dd, "trade": trade, "wr": wr, "net": net, "net_ket": net_ket,
            "kotor": kotor, "pemb": pemb, "bh": bh, "bh_dd": bh_dd, "bh_nama": bh_nama, "ket": ket, "utama": utama,
            "ekstra": ekstra or [], "dd_label": dd_label, "tile": tile, "monte_carlo": monte_carlo, "info": info}


def p(nama, rentang, universe, dibuka, hasil=None, skor=None, ket=None):
    return {"nama": nama, "rentang": rentang, "universe": universe, "dibuka": dibuka, "hasil": hasil, "skor": skor, "ket": ket}


CATATAN_MONTE_CARLO = 'Simulasi Monte Carlo: Follow Tren memegang maksimal 10 saham. Kalau sinyal beli lebih banyak dari slot kosong, saham dipilih acak karena aturan tidak memberi prioritas. Pilihan acak ini ikut menentukan hasil, jadi backtest diulang 100 kali dengan seed berbeda (seed = angka awal pengacak; seed sama menghasilkan pilihan yang sama, jadi bisa diulang persis). Median = hasil tengah dari 100 simulasi. p5–p95 = rentang tempat 90 dari 100 simulasi berada. Kurva dan tabel memakai satu simulasi (seed 7) sebagai contoh. Paper trade juga memilih acak (seed = tanggal), jadi hasil nyata bisa jatuh di mana saja di rentang ini, atau di luarnya.'
LAP_BULANAN = "CAGR & DD dari laporan bulanan: simulasi 5 posisi @20%, untung/rugi dicatat di bulan jual."
TAHAP1_KUNCI = "2026-10-20"

HIPOTESIS = [
    {"kode": "H0", "keluarga": "H0-H1", "nama": "Screener TP +3% / SL -3%", "kategori": "screener", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "1/7",
     "awam": "Komputer diberi 16 ciri harian saham lalu diminta menebak saham mana yang paling mungkin naik 3% sebelum turun 3%. Kalau tebakannya cukup tepat, saham dengan skor tertinggi dibeli.",
     "aturan": {"Universe": U217 + " " + LIKUID,
                "Model": "Regresi logistik walk-forward: dilatih ulang tiap awal tahun dengan semua data sebelumnya (minimal 4 tahun). Fitur dijadikan persentil cross-section harian (mom5/20/60, jarak EMA20/50, RSI, ATR%, kontraksi, rasio volume, jarak high 20, posisi close, RS vs IHSG, nilai transaksi + 3 fitur pasar).",
                "Sinyal masuk": "Desil skor teratas, sinyal di close, beli open besok.",
                "Keluar / stop": "TP +3% atau SL -3% (cek per candle; dua-duanya kena di candle sama = SL). Gap ikut dihitung. Batas 60 hari bursa.",
                "Ukuran posisi": "1 posisi per ticker (uji trade); laporan bulanan 5 posisi @20%.",
                "Biaya": BIAYA},
     "periode": [p("Dev", "Prediksi 2015-2021", "217 saham", True, "gagal", "1/7"),
                 p("Holdout", "2022 s/d sekarang", "217 saham", False)],
     "kriteria": [k("Desil teratas: hit rate ≥ base rate + 5 poin", ("49,2% vs perlu 50,5% (base 45,5%)", False)),
                  k("Spearman desil vs hit ≥ 0,7", ("0,93", True)),
                  k("Expectancy bersih > 0", ("-1,23%/trade", False)),
                  k("Bootstrap 90% batas bawah > 0", ("tidak tercatat (rata-rata negatif)", False)),
                  k("Tahun positif ≥ 70%", ("0/7 tahun", False)),
                  k("Tanpa 10 trade terbaik > 0", (TT, False)),
                  k("Tanpa 5 ticker terbaik > 0", (TT, False))],
     "angka": [a("Dev 2015-2021", cagr=-52, dd=-99.5, wr=49.2, net=-1.23, kotor=-0.09, utama=True,
                 ket="Winrate = hit TP duluan di desil teratas. " + LAP_BULANAN)],
     "kenapa": "Model memang bisa mengurutkan saham (Spearman 0,93), tapi hanya menaikkan peluang dari 45,5% ke 49,2%. Dengan biaya ±1,14% per trade, TP 3% butuh peluang ±60% supaya untung.",
     "kelemahan": ["Universe 217 saham syariah saat ini (bias survivorship).", "Fitur ditetapkan sendiri; tidak ada data order book/broker."],
     "pelajaran": "Target kecil (3%) habis dimakan biaya. Kemampuan mengurutkan saja tidak cukup.",
     "terkait": ["H1"], "sumber": "RENCANA_SCREENER.md:1"},

    {"kode": "H1", "keluarga": "H0-H1", "nama": "Screener TP +8% / SL -4%", "kategori": "screener", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "0/7",
     "awam": "Sama dengan H0, tapi targetnya dibuat lebih jauh (naik 8%, batas rugi 4%) supaya biaya terasa lebih kecil dibanding untungnya.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Model": "Sama dengan H0.", "Sinyal masuk": "Desil skor teratas, beli open besok.",
                "Keluar / stop": "TP +8% atau SL -4% (RR 2:1, impas di hit ±43%). Batas 60 hari bursa.",
                "Ukuran posisi": "Sama dengan H0.", "Biaya": BIAYA},
     "periode": [p("Dev", "Prediksi 2015-2021", "217 saham", True, "gagal", "0/7"), p("Holdout", "2022 s/d sekarang", "217 saham", False)],
     "kriteria": [k("Desil teratas: hit rate ≥ base rate + 5 poin", ("34,3% vs base 31,6%", False)),
                  k("Spearman desil vs hit ≥ 0,7", ("0,39", False)),
                  k("Expectancy bersih > 0", ("-1,14%/trade", False)),
                  k("Bootstrap 90% batas bawah > 0", (TT, False)), k("Tahun positif ≥ 70%", (TT, False)),
                  k("Tanpa 10 trade terbaik > 0", (TT, False)), k("Tanpa 5 ticker terbaik > 0", (TT, False))],
     "angka": [a("Dev 2015-2021", cagr=-20, dd=-80, wr=34.3, net=-1.14, utama=True, ket="Winrate = hit TP duluan di desil teratas. " + LAP_BULANAN)],
     "kenapa": "Makin jauh targetnya, makin hilang kemampuan model mengurutkan saham (Spearman turun ke 0,39).",
     "kelemahan": ["Hanya satu konfigurasi TP/SL boleh dicoba (dikunci)."],
     "pelajaran": "Memperlebar target tidak menyelamatkan sinyal yang lemah.",
     "terkait": ["H0"], "sumber": "RENCANA_SCREENER.md:51"},

    {"kode": "H2", "keluarga": "H2", "nama": "Naik menjelang cum date dividen", "kategori": "kalender", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Banyak orang membeli saham menjelang tanggal terakhir berhak dividen (cum date). Idenya: ikut beli beberapa hari sebelumnya, lalu jual tepat di cum date.",
     "aturan": {"Universe": U217 + " Likuid di hari sinyal (ATR tidak difilter).",
                "Sinyal masuk": "Beli open hari bursa ex-5 (ex-date dari yfinance). Sekunder (ditetapkan sebelum uji): yield dividen ≥ 3%.",
                "Keluar / stop": "Jual close cum date (ex-1), tahan 4 hari. Tanpa stop.",
                "Ukuran posisi": "Uji per event; laporan bulanan 5 posisi @20%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2021", "217 saham", True, "gagal", "1/6"), p("Holdout", "2022 s/d sekarang", "217 saham", False)],
     "kriteria": k6([("-0,77%", False), ("kotor +0,40% vs +0,03%", True), (TT, False), ("17% tahun", False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2010-2021 (utama)", cagr=-5, dd=-55, trade=396, net=-0.77, kotor=0.40, pemb=0.03, utama=True, ket=LAP_BULANAN),
               a("Dev 2010-2021 (yield ≥ 3%)", cagr=-0.2, dd=-15, trade=100, net=-0.09, kotor=1.10, pemb=0.03, ket="Kelompok sekunder, ditetapkan sebelum uji. Bootstrap [-0,94; 0,84], tahun positif 50%.")],
     "tabel": {"judul": "Kelompok utama vs sekunder", "kolom": ["Kelompok", "Event", "Kotor", "Bersih", "Bootstrap 90%", "Tahun +", "CAGR (5 posisi)"],
               "baris": [["Semua event", "396", "+0,40%", "-0,77%", TT, "17%", "-5%"],
                         ["Yield ≥ 3%", "100", "+1,10%", "-0,09%", "[-0,94; 0,84]", "50%", "-0,2%"]]},
     "kenapa": "Efek run-up ada (kotor di atas pembanding, lebih kuat di yield ≥ 3%), tapi lebih kecil dari biaya.",
     "kelemahan": ["Universe 217 (bias survivorship).", "Ex-date dari yfinance, bukan jadwal resmi IDX."],
     "pelajaran": "Pola struktural kecil tetap kalah oleh biaya transaksi.",
     "terkait": ["H17a"], "sumber": "RENCANA_SCREENER.md:57"},

    {"kode": "H3", "keluarga": "H3-H6", "nama": "Pullback dalam tren naik", "kategori": "swing", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Beli saham yang trennya naik tapi baru saja turun tajam beberapa hari, dengan harapan harganya memantul lagi.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "EMA20 > EMA50, close > EMA50, turun ≥ 5% dalam 3 hari. Beli open besok.",
                "Keluar / stop": "Jual close hari ke-10. Tanpa TP/SL.", "Ukuran posisi": "1 posisi per ticker; laporan bulanan 5 posisi @20%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2021", "217 saham", True, "gagal", "1/6"), p("Holdout", "2022+", "217 saham", False)],
     "kriteria": k6([("-0,45%", False), ("kotor +0,87% vs +0,28%", True), (TT, False), ("33% tahun", False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2010-2021", cagr=-4, dd=-48, trade=1114, net=-0.45, kotor=0.87, pemb=0.28, utama=True, ket=LAP_BULANAN)],
     "kenapa": "Kotor +0,87% di atas acak, tapi tidak menutup biaya ±1,2%; hanya 33% tahun positif.",
     "kelemahan": ["Empat hipotesis (H3-H6) diuji sekaligus, peluang lulus kebetulan naik.", "Universe 217."],
     "pelajaran": "Pantulan jangka pendek ada, tapi kecil.", "terkait": ["H4", "H19d"], "sumber": "RENCANA_SCREENER.md:76"},

    {"kode": "H4", "keluarga": "H3-H6", "nama": "Breakout konsolidasi + volume", "kategori": "swing", "status": "gagal",
     "lencana": ["holdout_pengecualian"], "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "dev 4/6 · 2024+ 0/6",
     "awam": "Beli saham yang lama bergerak sempit lalu tiba-tiba menembus ke atas dengan volume dua kali lipat, lalu tahan 2 minggu.",
     "aturan": {"Universe": U217 + " " + LIKUID,
                "Sinyal masuk": "Rasio ATR / rata-rata 60 hari < 0,8 kemarin, close > high 20 hari sebelumnya, volume ≥ 2× rata-rata 20 hari. Beli open besok.",
                "Keluar / stop": "Jual close hari ke-10. Tanpa TP/SL.", "Ukuran posisi": "1 posisi per ticker; laporan bulanan 5 posisi @20%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2021", "217 saham", True, "gagal", "4/6"),
                 p("Holdout asli", "2022+", "217 saham", False, ket="2022-2023 bocor saat smoke test H7 (H4 +2,46% di 2020-2023)."),
                 p("Holdout pengecualian", "2024-01 s/d data terakhir", "217 saham", True, "gagal", "0/6", "Dibuka atas keputusan user walau dev gagal.")],
     "kriteria": k6([("+1,23%", True), ("kotor +2,60% vs +0,28%", True), ("-0,05", False), ("67% (8/12)", False), ("positif", True), ("positif", True)],
                    [("-1,46%", False), ("kotor -0,04% vs +0,30%", False), ("negatif", False), ("0/3 tahun", False), ("negatif", False), ("negatif", False)]),
     "angka": [a("Dev 2010-2021", cagr=7.0, dd=-23, trade=425, net=1.23, kotor=2.60, pemb=0.28, ket=LAP_BULANAN),
               a("Holdout pengecualian 2024+", cagr=-18.9, dd=-47, trade=192, net=-1.46, kotor=-0.04, pemb=0.30, utama=True,
                 ket="Semua tahun negatif (2024 -1,65%, 2025 -0,68%, 2026 -1,98%), median trade -2,10%. Dengan biaya setengah spread tetap -0,44%.")],
     "kenapa": "Satu-satunya pola yang positif di 2010-2021 dan 2020-2023, tapi di data yang benar-benar baru (2024+) rugi di semua tahun dan lebih buruk dari acak.",
     "kelemahan": ["Holdout dibuka sebagai pengecualian walau dev gagal (melanggar aturan 'gagal dev, berhenti').",
                   "Holdout 2022-2023 bocor lewat smoke test H7.", "Hasil 2020-2023 bergantung pada sedikit trade besar."],
     "pelajaran": "Bagus di data lama tidak menjamin apa pun. Inilah alasan holdout wajib.",
     "terkait": ["H7b", "H19e"], "sumber": "RENCANA_SCREENER.md:118"},

    {"kode": "H5", "keluarga": "H3-H6", "nama": "Efek pergantian bulan", "kategori": "kalender", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Konon harga saham cenderung naik di sekitar pergantian bulan (dana gaji/pensiun masuk). Beli di akhir bulan, jual awal bulan berikutnya.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "Sinyal hari bursa kedua terakhir, beli open hari bursa terakhir bulan.",
                "Keluar / stop": "Jual close hari bursa ke-3 bulan berikutnya.", "Ukuran posisi": "Semua saham lolos; laporan bulanan 5 posisi @20%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2021", "217 saham", True, "gagal", "1/6"), p("Holdout", "2022+", "217 saham", False)],
     "kriteria": k6([("-1,03%", False), ("kotor +0,23% vs +0,03%", True), (TT, False), (TT, False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2010-2021", cagr=-9, dd=-74, trade=5249, net=-1.03, kotor=0.23, pemb=0.03, utama=True, ket=LAP_BULANAN)],
     "kenapa": "Efeknya ada tapi hanya +0,2% sebelum biaya.", "kelemahan": ["Empat hipotesis sekaligus.", "Universe 217."],
     "pelajaran": "Efek kalender terlalu kecil untuk biaya IDX.", "terkait": ["H6"], "sumber": "RENCANA_SCREENER.md:86"},

    {"kode": "H6", "keluarga": "H3-H6", "nama": "Menjelang libur Lebaran", "kategori": "kalender", "status": "gagal",
     "tgl_kunci": TAHAP1_KUNCI, "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Beli saham beberapa hari sebelum libur Lebaran, dengan anggapan pasar biasanya optimis menjelang libur panjang.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "L = hari bursa terakhir sebelum Idul Fitri. Beli open L-4.",
                "Keluar / stop": "Jual close L (tahan 5 hari).", "Ukuran posisi": "Semua saham lolos; laporan bulanan 5 posisi @20%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2021", "217 saham", True, "gagal", "1/6"), p("Holdout", "2022+", "217 saham", False)],
     "kriteria": k6([("-0,81%", False), ("kotor +0,47% vs +0,07%", True), (TT, False), (TT, False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2010-2021", cagr=-0.8, dd=-13, trade=388, net=-0.81, kotor=0.47, pemb=0.07, utama=True, ket=LAP_BULANAN + " 92% bulan tanpa trade.")],
     "kenapa": "Cuma satu kejadian per tahun; efek kotor +0,47% kalah dari biaya.", "kelemahan": ["Hanya 12 kejadian Lebaran di dev."],
     "pelajaran": "Sampel kalender sangat kecil, tidak bisa diandalkan.", "terkait": ["H5"], "sumber": "RENCANA_SCREENER.md:87"},

    {"kode": "H7a", "keluarga": "H7", "nama": "Akumulasi asing 5 hari", "kategori": "aliran", "status": "gagal",
     "tgl_kunci": "2026-10-20", "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Beli saham yang paling banyak diborong investor asing dalam seminggu terakhir.",
     "aturan": {"Universe": U217 + " " + LIKUID + " Data asing IDX (GetStockSummary) 2020+.",
                "Sinyal masuk": "Desil teratas akumulasi asing 5 hari = Σ(ForeignBuy − ForeignSell) × Close / rata-rata nilai 20 hari. Beli open besok.",
                "Keluar / stop": "Tahan 10 hari.", "Ukuran posisi": "1 posisi per ticker.", "Biaya": BIAYA},
     "periode": [p("Dev", "2020-2023", "217 saham", True, "gagal", "1/6"), p("Holdout", "2024+", "217 saham", False)],
     "kriteria": k6([("-1,16%", False), ("kotor +0,08% vs +0,09%", False), (TT, None), (TT, None), (TT, None), (TT, None)]),
     "angka": [a("Dev 2020-2023", net=-1.16, kotor=0.08, pemb=0.09, utama=True, ket="Skor 1/6 tercatat, rincian kriteria lain tidak tercatat.")],
     "kenapa": "Saham yang diakumulasi asing tidak lebih baik dari saham acak, bahkan sebelum biaya.",
     "kelemahan": ["Data asing hanya 2020+, dev cuma 4 tahun."], "pelajaran": "Aliran asing harian gratis tidak punya daya prediksi.",
     "terkait": ["H7b", "H15a"], "sumber": "RENCANA_SCREENER.md:98"},

    {"kode": "H7b", "keluarga": "H7", "nama": "Breakout H4 + asing masuk", "kategori": "aliran", "status": "gagal",
     "tgl_kunci": "2026-10-20", "tgl_uji": "2026-10-20", "skor": "4/6 + 1",
     "awam": "Sinyal breakout H4, tapi hanya diambil kalau investor asing juga sedang membeli.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "Sinyal H4 dan akumulasi asing 5 hari > 0. Beli open besok.",
                "Keluar / stop": "Tahan 10 hari.", "Ukuran posisi": "1 posisi per ticker.", "Biaya": BIAYA},
     "periode": [p("Dev", "2020-2023", "217 saham", True, "gagal", "4/6 + kriteria tambahan lulus"), p("Holdout", "2024+", "217 saham", False)],
     "kriteria": k6([("+2,56%", True), ("di atas", True), ("[0,05; 5,00]", True), ("4/4 tahun", True), ("-0,68%", False), ("-0,06%", False)])
                 + [k("Tambahan: expectancy > H4 periode sama", ("+2,56% vs +2,46%", True))],
     "angka": [a("Dev 2020-2023", net=2.56, utama=True, ket="Jumlah trade tidak tercatat (aturan: < 50 trade = bukti tidak cukup).")],
     "kenapa": "Hanya 0,1 poin di atas H4 biasa dan hasilnya bergantung pada sedikit trade besar.",
     "kelemahan": ["Mewarisi H4; smoke test dengan data asing acak pun terlihat bagus.", "Sampel kecil."],
     "pelajaran": "Filter asing tidak menambah nilai di atas breakout.", "terkait": ["H4", "H7a"], "sumber": "RENCANA_SCREENER.md:102"},

    {"kode": "H8", "keluarga": "H8-H10", "nama": "Reaksi laporan keuangan", "kategori": "kalender", "status": "gagal",
     "tgl_kunci": "2026-10-20", "tgl_uji": "2026-10-21", "skor": "2/6",
     "awam": "Kalau harga saham melonjak jauh di atas IHSG setelah laporan keuangan terbit, biasanya kenaikannya berlanjut beberapa hari. Beli setelah lonjakan itu.",
     "aturan": {"Universe": UDES + " Likuid seperti H0 (yfinance adjusted).",
                "Sinyal masuk": "t0 = hari bursa pertama pada/setelah publikasi laporan (IDX). Return close(t0-1)→close(t0+1) dikurangi IHSG ≥ +4%. Sinyal di close t0+1.",
                "Keluar / stop": "Tahan 10 hari.", "Ukuran posisi": "1 posisi per ticker.", "Biaya": BIAYA},
     "periode": [p("Dev", "2020-2023", "DES historis", True, "gagal", "2/6"), p("Holdout", "2024+", "DES historis", False)],
     "kriteria": k6([("-0,02%", False), ("kotor +1,32% vs -0,08%", True), ("[-1,40; 1,19]", False), ("3/4 tahun", True), ("-1,49%", False), (TT, False)]),
     "angka": [a("Dev 2020-2023", cagr=-1.1, dd=-14, trade=168, net=-0.02, kotor=1.32, pemb=-0.08, utama=True, ket="Per tahun 2020 +1,76%, 2021 +0,55%, 2022 +0,03%, 2023 -1,57% (makin turun).")],
     "kenapa": "Efek terkuat sebelum biaya (+1,4 poin di atas acak), tapi setelah biaya hanya impas dan melemah tiap tahun.",
     "kelemahan": ["55 kode DES delisting tidak ada di yfinance.", "Tanggal publikasi = File_Modified terawal (proksi)."],
     "pelajaran": "Drift setelah laporan nyata, tapi tidak cukup besar untuk biaya.", "terkait": ["H14a"], "sumber": "RENCANA_SCREENER.md:134"},

    {"kode": "H9", "keluarga": "H8-H10", "nama": "Blok negosiasi berpremi", "kategori": "aliran", "status": "gagal",
     "tgl_kunci": "2026-10-20", "tgl_uji": "2026-10-20", "skor": "0/6",
     "awam": "Kalau ada transaksi besar di pasar negosiasi dengan harga di atas pasar, mungkin ada pihak yang tahu sesuatu. Ikut beli.",
     "aturan": {"Universe": UDES + " Likuid seperti H0.",
                "Sinyal masuk": "NonRegularValue ≥ 50% rata-rata nilai reguler 20 hari dan harga negosiasi ≥ close × 1,02. Beli open besok.",
                "Keluar / stop": "Tahan 10 hari.", "Ukuran posisi": "1 posisi per ticker.", "Biaya": BIAYA},
     "periode": [p("Dev", "2020-2023", "DES historis", True, "gagal", "0/6"), p("Holdout", "2024+", "DES historis", False)],
     "kriteria": k6([("-3,08%", False), ("kotor -1,67% vs -0,08%", False), (TT, False), (TT, False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2020-2023", trade=289, net=-3.08, kotor=-1.67, pemb=-0.08, utama=True)],
     "kenapa": "Arahnya terbalik: lebih buruk dari saham acak.",
     "kelemahan": ["Tidak boleh dibalik jadi sinyal 'hindari' tanpa hipotesis baru."],
     "pelajaran": "Transaksi negosiasi bukan sinyal beli.", "terkait": ["H10"], "sumber": "RENCANA_SCREENER.md:135"},

    {"kode": "H10", "keluarga": "H8-H10", "nama": "Antrian beli dominan saat tutup", "kategori": "aliran", "status": "gagal",
     "tgl_kunci": "2026-10-20", "tgl_uji": "2026-10-20", "skor": "1/6",
     "awam": "Kalau antrian beli jauh lebih tebal dari antrian jual saat penutupan, mungkin besok harganya naik.",
     "aturan": {"Universe": UDES + " Likuid seperti H0.",
                "Sinyal masuk": "Imbalance = (Bid − Offer) / (Bid + Offer) volume penutupan; desil teratas cross-section harian.",
                "Keluar / stop": "Tahan 5 hari.", "Ukuran posisi": "1 posisi per ticker.", "Biaya": BIAYA},
     "periode": [p("Dev", "2020-2023", "DES historis", True, "gagal", "1/6"), p("Holdout", "2024+", "DES historis", False)],
     "kriteria": k6([("-0,97%", False), ("kotor +0,30% vs -0,11%", True), (TT, False), ("0/4 tahun", False), (TT, False), (TT, False)]),
     "angka": [a("Dev 2020-2023", trade=4236, net=-0.97, kotor=0.30, pemb=-0.11, utama=True)],
     "kenapa": "Sinyal kecil (+0,4 poin di atas acak), habis dimakan biaya; tidak ada tahun positif.",
     "kelemahan": ["Hanya snapshot penutupan, bukan order book penuh."], "pelajaran": "Antrian penutupan bukan edge setelah biaya.",
     "terkait": ["H9", "H19g"], "sumber": "RENCANA_SCREENER.md:136"},

    {"kode": "H11a", "keluarga": "H11", "nama": "Follow Tren (tertinggi 52 minggu)", "kategori": "tren", "status": "paper",
     "lencana": ["dev_gagal", "holdout_pengecualian"], "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-21", "skor": "dev 6/7 · holdout 7/7",
     "awam": "Beli saham yang harganya mencetak rekor tertinggi setahun, lalu ikuti terus selama trennya naik. Jual kalau harga turun cukup jauh dari puncaknya. Sering rugi kecil, sesekali untung sangat besar.",
     "aturan": {"Universe": "Dev: " + U217 + " Holdout: " + UDES + " " + LIKUID,
                "Sinyal masuk": "Close ≥ close tertinggi 250 hari sebelumnya. Beli open besok.",
                "Keluar / stop": "Stop awal entry − 3×ATR14; trailing = max(stop, close tertinggi sejak entry − 3×ATR14). Close < stop → jual open besok (gap dihitung). Batas 500 hari.",
                "Ukuran posisi": "Maks 10 posisi @10% ekuitas; sinyal ditolak kalau penuh, sinyal di hari sama dipilih acak (seed 7).",
                "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2019", "217 saham", True, "gagal", "6/7", "Gagal di tahun positif (6/9 = 67%)."),
                 p("Holdout pengecualian", "2020-01 s/d data terakhir", "DES historis", True, "lulus", "7/7", "Dibuka atas keputusan user walau dev gagal tipis."),
                 p("Paper trade", "Sejak 21 Okt 2026, Rp100 jt", "DES harian", True, None, None, "Dinilai dengan zona normal batas_paper h11a_v1.")],
     "kriteria": k6([("+2,10%", True), ("kotor +3,43% vs -0,65%", True), ("[0,36; 4,00]", True), ("6/9 = 67%", False), ("+0,14%", True), ("+0,58%", True)],
                    [("+6,21%", True), ("kotor +7,70% vs -1,02%", True), ("[3,05; 9,87]", True), ("5/7 = 71%", True), ("+2,39%", True), ("+3,63%", True)])
                 + [k("CAGR 10 posisi > beli-tahan bobot sama", ("12,1% vs 8,1%", True), ("30,3% vs 6,5%", True))],
     "angka": [a("Cara paper 2020-2026 · median 100 simulasi Monte Carlo", monte_carlo="h11a_2020", utama=True, info=CATATAN_MONTE_CARLO,
                 ket="Cara paper: kurva harian, 10% ekuitas saat beli, harga pasar, dividen dipotong pajak. Median dari 100 simulasi Monte Carlo pemilihan saham saat sinyal melebihi slot kosong (aturan sama). Harapan realistis lebih rendah."),
               a("Cara paper 2010-2019 · median 100 simulasi Monte Carlo", monte_carlo="h11a_dev", info=CATATAN_MONTE_CARLO, ket="Universe dev 217 saham (bias survivorship)."),
               a("Uji dev 2010-2019 (laporan bulanan)", cagr=12.1, dd=-20.4, trade=495, wr=40, net=2.10, kotor=3.43, pemb=-0.65, bh=8.1, bh_nama="Bobot sama, rebalance harian (bulanan 7,6%)",
                 ket="CAGR & DD dari 1 simulasi (seed 7), metode laporan bulanan yang dipakai kriteria uji. Median trade -3,31%, rata-rata tahan 33 hari, bulan positif 46%."),
               a("Uji holdout 2020-2026 (laporan bulanan)", cagr=30.3, dd=-37.7, trade=692, wr=34, net=6.21, kotor=7.70, pemb=-1.02, bh=6.5, bh_nama="Bobot sama, rebalance harian (bulanan 0,5%)",
                 ket="CAGR & DD dari 1 simulasi (seed 7), metode laporan bulanan yang dipakai kriteria uji (melebih-lebihkan dibanding cara paper). Median trade -5,7%, bulan positif 40%. 30 seed acak: CAGR 24,7-34,6%.")],
     "kenapa": "Dev gagal tipis (tahun positif 67% < 70%). Holdout dibuka sebagai pengecualian dan lulus 7/7, jadi dilanjutkan ke paper trade, bukan dinyatakan terbukti.",
     "kelemahan": ["Dev gagal dengan aturan kita; holdout dibuka sebagai pengecualian.",
                   "2020-2026 mencakup reli besar saham kecil/konglomerasi (2020-2021, 2025).",
                   "Hasil bergantung pada sedikit trade besar; median trade negatif, bulan positif ±40%.",
                   "Di saham non-syariah (Set A, H13) CAGR 1,9% < beli-tahan 5,0%.",
                   "55 kode delisting tidak ada di data; laporan bulanan melebih-lebihkan dibanding cara paper (21,3% vs 17,3%)."],
     "pelajaran": "Satu-satunya yang lanjut ke paper trade. Edge-nya datang dari saham volatil yang naik berkali lipat, bukan dari winrate.",
     "terkait": ["H11b", "H12a", "H13", "H14a", "H15b"], "sumber": "RENCANA_SCREENER.md:151"},

    {"kode": "H11b", "keluarga": "H11", "nama": "Momentum 6 bulan + EMA200", "kategori": "tren", "status": "gagal",
     "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-21", "skor": "4/7",
     "awam": "Beli saham yang naik paling tinggi dalam 6 bulan terakhir (10% teratas) selama masih di atas rata-rata 200 hari, dengan stop yang sama seperti H11a.",
     "aturan": {"Universe": U217 + " " + LIKUID,
                "Sinyal masuk": "Return 120 hari di desil teratas cross-section dan close > EMA200. Beli open besok.",
                "Keluar / stop": "Sama dengan H11a (trailing 3×ATR14).", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2019", "217 saham", True, "gagal", "4/7"), p("Holdout", "2020+", "DES historis", False)],
     "kriteria": k6([("+1,66%", True), (TT + " (lulus)", True), ("[-0,20; 3,71]", False), (TT + " (lulus)", True), ("-0,15%", False), (TT + " (lulus)", True)])
                 + [k("CAGR 10 posisi > beli-tahan", ("4,8% vs 8,1%", False))],
     "angka": [a("Dev 2010-2019", cagr=4.8, net=1.66, bh=8.1, bh_nama="Beli-tahan bobot sama", utama=True)],
     "kenapa": "Expectancy positif tapi rapuh (tanpa 10 trade terbaik negatif) dan CAGR kalah dari beli-tahan.",
     "kelemahan": ["Universe 217.", "Rincian kriteria yang lulus disimpulkan dari skor 4/7."],
     "pelajaran": "Momentum relatif dengan stop ketat kalah dari breakout 52 minggu di data yang sama.", "terkait": ["H11a"], "sumber": "RENCANA_SCREENER.md:164"},

    {"kode": "H12a", "keluarga": "H12", "nama": "H11a tanpa saham volatil (ATR ≤ 3,5%)", "kategori": "tren", "status": "gagal",
     "lencana": ["pasca_hasil"], "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-21", "skor": "—",
     "awam": "Aturan Follow Tren yang sama, tapi saham yang terlalu liar (pergerakan harian besar) dibuang supaya rugi per trade lebih kecil.",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "Sinyal H11a dan ATR14% ≤ 3,5% di hari sinyal (stop awal paling jauh ±-10,5%).",
                "Keluar / stop": "Sama dengan H11a.", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2019", "217 saham", True, "gagal"), p("Info", "2020-2026", "DES historis", True, None, None, "Hanya informasi; periode sudah dipakai menilai H11a.")],
     "kriteria": [k("Expectancy bersih > 0", ("+1,21%", True)), k("Tanpa 10 trade terbaik > 0", ("negatif", False)),
                  k("CAGR > beli-tahan", ("5,0% vs 8,1%", False)), k("Kriteria H11a lainnya", (TT, None))],
     "angka": [a("Dev 2010-2019", cagr=5.0, dd=-9, net=1.21, bh=8.1, bh_nama="Beli-tahan bobot sama", utama=True,
                 ket="DD ±-9% (dicatat bersama H12b). Rata-rata menang 14,0% vs H11a 17,3%. Info 2020-2026: CAGR 4,1%.")],
     "kenapa": "Rugi memang mengecil, tapi kemenangan besar ikut hilang.",
     "kelemahan": ["Ide muncul setelah melihat trade paper 2026 (pasca-hasil)."],
     "pelajaran": "Edge H11a justru datang dari saham volatil.", "terkait": ["H11a", "H12b"], "sumber": "RENCANA_SCREENER.md:195"},

    {"kode": "H12b", "keluarga": "H12", "nama": "H12a + harga ≥ Rp200", "kategori": "tren", "status": "gagal",
     "lencana": ["pasca_hasil"], "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-21", "skor": "—",
     "awam": "Seperti H12a, ditambah membuang saham harga di bawah Rp200 (biaya tick-nya mahal).",
     "aturan": {"Universe": U217 + " " + LIKUID, "Sinyal masuk": "Sinyal H12a dan harga ≥ Rp200 (tick ≤ 0,5%).",
                "Keluar / stop": "Sama dengan H11a.", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Dev", "2010-2019", "217 saham", True, "gagal"), p("Info", "2020-2026", "DES historis", True, None, None, "Hanya informasi.")],
     "kriteria": [k("Expectancy bersih > 0", ("+1,26%", True)), k("Tanpa 10 trade terbaik > 0", ("negatif", False)),
                  k("CAGR > beli-tahan", ("5,2% vs 8,1%", False)), k("Kriteria H11a lainnya", (TT, None))],
     "angka": [a("Dev 2010-2019", cagr=5.2, dd=-9, net=1.26, bh=8.1, bh_nama="Beli-tahan bobot sama", utama=True, ket="DD ±-9% (dicatat bersama H12a). Info 2020-2026: CAGR 3,0%.")],
     "kenapa": "Sama dengan H12a; saham murah/volatil adalah sumber kemenangan besar.",
     "kelemahan": ["Pasca-hasil."], "pelajaran": "Jangan membuang ekor kanan distribusi demi rugi yang lebih kecil.",
     "terkait": ["H12a", "H11a"], "sumber": "RENCANA_SCREENER.md:198"},

    {"kode": "H13", "keluarga": "H13", "nama": "Perbaikan portofolio H11a (S/R/P)", "kategori": "tren", "status": "tidak_diadopsi",
     "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-21", "skor": "0/4 konfigurasi",
     "awam": "Mencoba tiga perbaikan cara masuk Follow Tren: ukuran posisi berdasar risiko, hanya beli saat IHSG sedang naik, dan memprioritaskan tren terkuat. Diuji di data yang belum pernah dipakai.",
     "aturan": {"Universe": "Set A: 182 saham non-syariah (hanya untuk uji, tidak dibeli), 2010-sekarang. Set B: saham DES di luar 217, 2010-2019. " + LIKUID,
                "S (ukuran posisi)": "Bobot = 1% ekuitas / jarak stop awal, maks 20%, total maks 100%, maks 10 posisi.",
                "R (rezim)": "Sinyal baru hanya kalau close IHSG > EMA200 IHSG.",
                "P (prioritas)": "Sinyal hari sama diurutkan dari return 120 hari tertinggi (bukan acak).",
                "Sinyal & stop": "Sama dengan H11a.", "Biaya": BIAYA},
     "periode": [p("Set A", "2010-2026 non-syariah", "144 saham", True, "tidak diadopsi"), p("Set B", "2010-2019 DES di luar 217", "306 saham", True, "tidak diadopsi")],
     "kriteria": [k("Komponen diadopsi kalau MAR > H11a di Set A dan Set B", ("tidak ada komponen yang menaikkan MAR di keduanya", False)),
                  k("Paket S+R+P: MAR > H11a di kedua set dan CAGR > beli-tahan", ("MAR turun", False)),
                  k("Cek H11a: CAGR > beli-tahan di Set A dan B (peringatan)", ("Set A 1,9% < 5,0%; Set B 12,5% vs 12,1%", False))],
     "angka": [],
     "tabel": {"judul": "4 konfigurasi vs H11a (CAGR / DD, MAR = CAGR / |DD|)",
               "kolom": ["Set", "H11a", "S", "R", "P", "S+R+P"],
               "baris": [["A non-syariah 2010-2026", "1,9% / -28% (0,07)", "1,5% / -26% (0,06)", "-0,2% / -25% (<0)", "sama H11a", "0,7% / -23% (0,03)"],
                         ["B DES di luar 217, 2010-2019", "12,5% / -18% (0,69)", "11,1% / -21% (0,53)", "9,5% / -14% (0,68)", "sama H11a", "7,4% / -17% (0,44)"],
                         ["Info: 217, 2010-2019", "10,8% / -20%", "9,6% / -15%", "7,1% / -19%", "10,2% / -20%", "6,4% / -16%"],
                         ["Info: DES 2020+", "29,5% / -38%", "32,3% / -28%", "30,2% / -16%", "32,4% / -32%", "19,1% / -12%"]]},
     "kenapa": "Tidak ada komponen yang menaikkan MAR di kedua set independen. R dan S terlihat bagus di DES 2020+, tapi periode itu sudah terpakai.",
     "kelemahan": ["29 saham Set A delisting hilang.", "P sama dengan H11a karena slot jarang penuh di set kecil."],
     "pelajaran": "Perbaikan yang terlihat bagus di periode yang sudah dipakai tidak bertahan di data independen. Juga: beli-tahan rebalance harian menggelembungkan pembanding.",
     "terkait": ["H11a", "H20"], "sumber": "RENCANA_SCREENER.md:203"},

    {"kode": "H14a", "keluarga": "H14", "nama": "H11a + laba tumbuh", "kategori": "fundamental", "status": "tidak_diadopsi",
     "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-22", "skor": "tidak diadopsi",
     "awam": "Sinyal Follow Tren hanya diambil kalau perusahaannya untung dan labanya tumbuh dibanding tahun lalu.",
     "aturan": {"Universe": "Set A non-syariah likuid 2020-2026 (penilaian utama) dan syariah DES 2020-2026 (pendukung). " + LIKUID,
                "Sinyal masuk": "Sinyal H11a dan laba YTD > 0 dan > laba YTD periode sama tahun lalu (laporan IDX yang terbit sebelum sinyal).",
                "Keluar / stop": "Sama dengan H11a.", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Set A", "2020-2026", "non-syariah", True, "tidak diadopsi"), p("Syariah DES", "2020-2026", "DES historis", True, "tidak diadopsi")],
     "kriteria": [k("Net/trade > H11a di Set A dan syariah", ("A 2,52% > 2,05%; syariah 5,85% < 6,21%", False)),
                  k("MAR > H11a di Set A dan syariah", ("A 0,21 > 0,14; syariah 0,57 < 0,80", False))],
     "angka": [a("Set A 2020-2026", cagr=4.4, dd=-21.3, trade=127, wr=39, net=2.52, utama=True),
               a("Syariah DES 2020-2026", cagr=14.7, dd=-25.9, trade=335, wr=33, net=5.85)],
     "tabel": {"judul": "H11a vs H14a vs H14b", "kolom": ["Set", "Konfig", "Trade", "WR", "Net/trade", "CAGR", "DD", "MAR"],
               "baris": [["A non-syariah", "H11a", "164", "36%", "+2,05%", "4,0%", "-28,1%", "0,14"],
                         ["A non-syariah", "H14a", "127", "39%", "+2,52%", "4,4%", "-21,3%", "0,21"],
                         ["A non-syariah", "H14b", "28", "57%", "+10,25%", "4,1%", "-3,4%", "1,21"],
                         ["Syariah DES", "H11a", "375", "34%", "+6,21%", "30,3%", "-37,7%", "0,80"],
                         ["Syariah DES", "H14a", "335", "33%", "+5,85%", "14,7%", "-25,9%", "0,57"],
                         ["Syariah DES", "H14b", "289", "34%", "+6,32%", "12,7%", "-19,9%", "0,64"]]},
     "kenapa": "Membantu di non-syariah, tapi di syariah menurunkan net/trade dan MAR: filter membuang beberapa saham yang naik paling tinggi.",
     "kelemahan": ["Data fundamental hanya 2019+.", "Syariah 2020+ sudah dipakai menilai H11a."],
     "pelajaran": "Laba tumbuh tidak memperbaiki Follow Tren di saham syariah.", "terkait": ["H11a", "H14b"], "sumber": "RENCANA_SCREENER.md:237"},

    {"kode": "H14b", "keluarga": "H14", "nama": "H14a + pendapatan tumbuh", "kategori": "fundamental", "status": "tidak_diadopsi",
     "tgl_kunci": "2026-10-21", "tgl_uji": "2026-10-22", "skor": "tidak diadopsi",
     "awam": "Seperti H14a, ditambah syarat pendapatan juga tumbuh.",
     "aturan": {"Universe": "Sama dengan H14a.", "Sinyal masuk": "H14a dan pendapatan YTD > tahun lalu. Emiten tanpa SalesAndRevenue (bank) tidak lolos.",
                "Keluar / stop": "Sama dengan H11a.", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Set A", "2020-2026", "non-syariah", True, "tidak diadopsi"), p("Syariah DES", "2020-2026", "DES historis", True, "tidak diadopsi")],
     "kriteria": [k("Net/trade > H11a di Set A dan syariah", ("A 10,25% > 2,05%; syariah 6,32% > 6,21%", True)),
                  k("MAR > H11a di Set A dan syariah", ("A 1,21 > 0,14; syariah 0,64 < 0,80", False))],
     "angka": [a("Set A 2020-2026", cagr=4.1, dd=-3.4, trade=28, wr=57, net=10.25, utama=True), a("Syariah DES 2020-2026", cagr=12.7, dd=-19.9, trade=289, wr=34, net=6.32)],
     "kenapa": "Net/trade naik di kedua set, tapi MAR syariah lebih rendah (0,64 vs 0,80). Set A hanya 28 trade.",
     "kelemahan": ["Bank otomatis tidak lolos.", "Sampel Set A sangat kecil."],
     "pelajaran": "Filter ketat memperkecil drawdown tapi memotong return lebih banyak.", "terkait": ["H14a"], "sumber": "RENCANA_SCREENER.md:244"},

    {"kode": "H15a", "keluarga": "H15", "nama": "Saham yang dikumpulkan institusi (KSEI)", "kategori": "aliran", "status": "gagal",
     "tgl_kunci": "2026-10-22", "tgl_uji": "2026-10-22", "skor": "1/5",
     "awam": "Tiap bulan beli saham yang porsi kepemilikan institusinya (reksa dana, dana pensiun, asuransi, asing) paling banyak naik dalam 3 bulan.",
     "aturan": {"Universe": "Dev: 217 saham; holdout: DES. Nilai transaksi 20 hari ≥ Rp5 M, harga ≥ Rp50, tanpa volume nol 5 hari.",
                "Sinyal masuk": "Akhir bulan: urutkan perubahan porsi institusi 3 bulan (file KSEI dengan jeda publikasi 30 hari). Beli desil teratas (min 5 saham) sama bobot, open hari berikutnya.",
                "Keluar / stop": "Tahan sampai rebalance bulan berikutnya.", "Ukuran posisi": "Sama bobot.", "Biaya": BIAYA + " Hanya untuk saham yang berganti."},
     "periode": [p("Dev", "2011-2019", "217 saham", True, "gagal", "1/5"), p("Holdout", "2020-2026", "DES historis", False)],
     "kriteria": [k("Rata-rata selisih bulanan bersih vs pembanding > 0", ("-0,77%/bln", False)),
                  k("Bootstrap 90% batas bawah > 0", ("-1,57%", False)), k("Selisih positif ≥ 70% tahun", ("2/9 tahun", False)),
                  k("Kotor desil atas > desil bawah", ("+0,29% < +0,45%/bln", False)), k("Liputan KSEI ≥ 80%", ("99%", True))],
     "angka": [a("Dev 2011-2019", cagr=-8.3, dd=-72.9, net=-0.77, net_ket="/bln vs pasar", kotor=0.29, pemb=0.40, bh=3.2, bh_dd=-36.3, bh_nama="Sama bobot universe, tanpa biaya", utama=True,
                 ket="Kotor & pembanding per bulan. CAGR/DD dihitung dari return bulanan tersimpan (hasil_riset). Biaya 0,67%/bulan, universe rata-rata 45 saham.")],
     "kenapa": "Saham yang dikumpulkan institusi justru naik lebih kecil dari yang dilepas, bahkan sebelum biaya.",
     "kelemahan": ["Universe dev kecil (±45 saham, desil 5 saham).", "Universe 217."],
     "pelajaran": "Data kepemilikan bulanan gratis tidak memberi keunggulan.", "terkait": ["H15b", "H7a"], "sumber": "RENCANA_SCREENER.md:274"},

    {"kode": "H15b", "keluarga": "H15", "nama": "H11a saat ritel tidak bertambah", "kategori": "aliran", "status": "tidak_diadopsi",
     "tgl_kunci": "2026-10-22", "tgl_uji": "2026-10-22", "skor": "tidak diadopsi",
     "awam": "Sinyal Follow Tren hanya diambil kalau porsi investor individu (ritel) tidak naik dalam 3 bulan, dengan anggapan saham yang ramai ritel cenderung sudah kemahalan.",
     "aturan": {"Universe": "Dev 217 (2010-2019), Set A non-syariah 2020-2026, syariah DES 2020-2026. " + LIKUID,
                "Sinyal masuk": "Sinyal H11a dan perubahan porsi ritel 3 bulan ≤ 0. Tanpa data KSEI = tidak diambil.",
                "Keluar / stop": "Sama dengan H11a.", "Ukuran posisi": "Maks 10 posisi @10%.", "Biaya": BIAYA},
     "periode": [p("Dev 217", "2010-2019", "217 saham", True, "tidak diadopsi"), p("Set A", "2020-2026", "non-syariah", True, "tidak diadopsi"),
                 p("Syariah DES", "2020-2026", "DES historis", True, "tidak diadopsi")],
     "kriteria": [k("Net/trade > H11a di ketiga set", ("dev 2,37 > 2,10; A 1,94 < 2,05; DES 5,27 < 6,21", False)),
                  k("MAR > H11a di ketiga set", ("dev 0,35 < 0,45; A sama 0,17; DES 0,82 > 0,75", False))],
     "angka": [a("Dev 217 2010-2019", cagr=7.0, dd=-20.3, trade=274, wr=40, net=2.37, utama=True),
               a("Syariah DES 2020-2026", cagr=18.2, dd=-22.1, trade=294, wr=35, net=5.27)],
     "tabel": {"judul": "H11a vs H15b", "kolom": ["Set", "Konfig", "Trade", "WR", "Net/trade", "CAGR", "DD", "MAR"],
               "baris": [["Dev 217 2010-2019", "H11a", "358", "40%", "+2,10%", "9,0%", "-20,0%", "0,45"],
                         ["Dev 217 2010-2019", "H15b", "274", "40%", "+2,37%", "7,0%", "-20,3%", "0,35"],
                         ["A non-syariah 2020-2026", "H11a", "164", "37%", "+2,05%", "4,9%", "-28,1%", "0,17"],
                         ["A non-syariah 2020-2026", "H15b", "80", "39%", "+1,94%", "2,1%", "-12,1%", "0,17"],
                         ["Syariah DES 2020-2026", "H11a", "365", "35%", "+6,21%", "27,1%", "-36,3%", "0,75"],
                         ["Syariah DES 2020-2026", "H15b", "294", "35%", "+5,27%", "18,2%", "-22,1%", "0,82"]]},
     "kenapa": "Drawdown turun, tapi return juga turun dan tidak konsisten di ketiga set.",
     "kelemahan": ["Syariah 2020+ sudah dipakai menilai H11a."], "pelajaran": "Filter ritel bukan perbaikan yang konsisten.",
     "terkait": ["H11a", "H15a"], "sumber": "RENCANA_SCREENER.md:277"},

    {"kode": "H16a", "keluarga": "H16", "nama": "Beli saham Undervalue", "kategori": "fundamental", "status": "gagal",
     "tgl_kunci": "2026-10-22", "tgl_uji": "2026-10-22", "skor": "2/5",
     "awam": "Tiap bulan beli semua saham yang menurut panel Valuasi dashboard harganya jauh di bawah nilai wajar (diskon ≥ 20%).",
     "aturan": {"Universe": UDES + " Nilai transaksi 20 hari ≥ Rp5 M, harga ≥ Rp50, ada valuasi.",
                "Sinyal masuk": "Akhir bulan, point-in-time: MoS ≥ 20% (nilai wajar = median PER/PBV historis & industri, Graham, DDM). Beli sama bobot open hari berikutnya.",
                "Keluar / stop": "Tahan sampai rebalance berikutnya.", "Ukuran posisi": "Sama bobot.", "Biaya": BIAYA + " Hanya saham yang berganti."},
     "periode": [p("Dev", "2021-04 s/d 2023-12", "DES historis", True, "gagal", "2/5"),
                 p("Holdout", "2024-01 s/d 2026-09", "DES historis", False, ket="Tidak lagi bersih: data 2024-2026 dibuka untuk analisis konvergensi.")],
     "kriteria": [k("Rata-rata selisih bulanan bersih > 0", ("-0,35%/bln", False)), k("Bootstrap 90% batas bawah > 0", ("-1,20%", False)),
                  k("Selisih tahunan positif ≥ 2 dari 3 tahun", ("1/3 (2022 +13,1%)", False)), k("Kotor > kelompok Overvalue", ("+0,37% > +0,05%", True)),
                  k("Rata-rata isi ≥ 5 saham", ("23,6", True))],
     "angka": [a("Dev 2021-04..2023-12", cagr=-2.3, dd=-27.9, net=-0.35, net_ket="/bln vs pasar", kotor=0.37, pemb=0.28, bh=2.3, bh_dd=-26.4, bh_nama="Sama bobot universe, tanpa biaya", utama=True,
                 ket="Kotor & pembanding per bulan. CAGR/DD dari return bulanan tersimpan (33 bulan).")],
     "kenapa": "Saham murah sedikit lebih baik dari saham mahal, tapi tidak mengalahkan rata-rata pasar setelah biaya; per tahun bolak-balik.",
     "kelemahan": ["Periode pendek (33 bulan).", "Survivorship: delisting tidak ada di Yahoo.", "Sektor Yahoo statis."],
     "pelajaran": "Valuasi murah bukan sinyal beli.", "terkait": ["H16b", "H16c"], "sumber": "RENCANA_SCREENER.md:298"},

    {"kode": "H16b", "keluarga": "H16", "nama": "Beli saham 'Layak dipertimbangkan'", "kategori": "fundamental", "status": "gagal",
     "tgl_kunci": "2026-10-22", "tgl_uji": "2026-10-22", "skor": "1/5",
     "awam": "Seperti H16a, tapi hanya saham yang murah, berkualitas, dan harganya di atas rata-rata 200 hari.",
     "aturan": {"Universe": "Sama dengan H16a.", "Sinyal masuk": "Sikap 'Layak': MoS ≥ 20%, skor kualitas ≥ maks-1, harga ≥ MA200.",
                "Keluar / stop": "Rebalance bulanan.", "Ukuran posisi": "Sama bobot.", "Biaya": BIAYA},
     "periode": [p("Dev", "2021-04 s/d 2023-12", "DES historis", True, "gagal", "1/5"), p("Holdout", "2024-01 s/d 2026-09", "DES historis", False)],
     "kriteria": [k("Rata-rata selisih bulanan bersih > 0", ("-0,47%/bln", False)), k("Bootstrap 90% batas bawah > 0", (TT, False)),
                  k("Selisih tahunan positif ≥ 2 dari 3 tahun", ("1/3 (2021 +2,3%)", False)), k("Kotor > kelompok Overvalue", (TT, None)),
                  k("Rata-rata isi ≥ 5 saham", ("2,5 (12% bulan kosong)", False))],
     "angka": [a("Dev 2021-04..2023-12", cagr=-5.2, dd=-41.5, net=-0.47, net_ket="/bln vs pasar", bh=2.3, bh_dd=-26.4, bh_nama="Sama bobot universe, tanpa biaya", utama=True,
                 ket="CAGR/DD dari return bulanan tersimpan.")],
     "kenapa": "Terlalu jarang muncul (2-3 saham) dan kalah dari pasar, terutama 2022 (-18,8%).",
     "kelemahan": ["Sama dengan H16a."], "pelajaran": "Saringan berlapis membuat portofolio terlalu kecil.", "terkait": ["H16a"], "sumber": "RENCANA_SCREENER.md:308"},

    {"kode": "H16c", "keluarga": "H16", "nama": "Undervalue yang bukan 'Hindari'", "kategori": "fundamental", "status": "gagal",
     "lencana": ["pasca_hasil"], "tgl_kunci": "2026-10-22", "tgl_uji": "2026-10-22", "skor": "3/6",
     "awam": "Saham Undervalue yang juga lolos lebih dari separuh cek kualitas. Ide user setelah H16a/H16b gagal.",
     "aturan": {"Universe": "Sama dengan H16.", "Sinyal masuk": "MoS ≥ 20% dan skor kualitas > setengah cek yang berlaku (Pantau atau Layak).",
                "Keluar / stop": "Rebalance bulanan.", "Ukuran posisi": "Sama bobot.", "Biaya": BIAYA},
     "periode": [p("Dev", "2021-04 s/d 2023-12", "DES historis", True, "gagal", "3/6"), p("Holdout", "2024-01 s/d 2026-09", "DES historis", False)],
     "kriteria": [k("Rata-rata selisih bulanan bersih > 0", ("-0,00%/bln", False)), k("Bootstrap 90% batas bawah > 0", ("-0,88%", False)),
                  k("Selisih tahunan positif ≥ 2 dari 3 tahun", ("1/3 (2022 +20,7%)", False)), k("Kotor > kelompok Overvalue", ("+0,72% > +0,05%", True)),
                  k("Rata-rata isi ≥ 5 saham", ("19,2", True)), k("Selisih > H16a pada bulan yang sama", ("0,00% > -0,35%", True))],
     "angka": [a("Dev 2021-04..2023-12", cagr=1.8, dd=-23.4, net=0.0, net_ket="/bln vs pasar", kotor=0.72, pemb=0.28, bh=2.3, bh_dd=-26.4, bh_nama="Sama bobot universe, tanpa biaya", utama=True,
                 ket="CAGR/DD dari return bulanan tersimpan.")],
     "kenapa": "Filter kualitas memperbaiki H16a, tapi hanya menyamai rata-rata pasar dan bergantung pada satu tahun (2022).",
     "kelemahan": ["Varian pasca-hasil.", "Holdout tidak lagi bersih."], "pelajaran": "Memperbaiki strategi yang gagal biasanya hanya mendekatkan ke rata-rata pasar.",
     "terkait": ["H16a"], "sumber": "RENCANA_SCREENER.md:322"},

    {"kode": "H17a", "keluarga": "H17", "nama": "Pemburu Dividen: 10 yield tertinggi konsisten", "kategori": "dividen", "status": "gagal",
     "tgl_kunci": "2026-10-23", "tgl_uji": "2026-10-23", "skor": "dev 2/4",
     "awam": "Tiap awal tahun beli 10 saham syariah dengan dividen tertinggi yang rutin membayar 3 tahun berturut-turut, lalu tahan setahun dan nikmati dividennya.",
     "aturan": {"Universe": "2014-2019: " + U217 + " 2020+: " + UDES + " Nilai transaksi 20 hari ≥ Rp5 M, harga ≥ Rp50.",
                "Sinyal masuk": "Hari bursa terakhir Desember: bayar dividen di tiap 3 tahun kalender sebelumnya, urut yield 12 bulan, ambil 10 teratas. Beli open hari bursa pertama Januari.",
                "Keluar / stop": "Tahan setahun; yang keluar dari daftar dijual saat rebalance. Tanpa stop.",
                "Ukuran posisi": "Sama bobot. Dividen tunai dipotong pajak 10%, tidak diinvestasikan ulang.",
                "Uji maju (dividen_v1)": "Rencana mulai Januari 2027 (maks 3 saham per sektor). DIHENTIKAN 25 Okt 2026 atas keputusan user setelah aturan yang sama gagal di H17c (non-syariah) dan H17d (syariah 2014-2026). Data diarsip di arsip_paper_dividen.",
                "Biaya": BIAYA},
     "periode": [p("Dev", "Portofolio 2014-2019", "217 saham", True, "gagal", "2/4"),
                 p("Holdout", "2020-2026", "DES historis", False, ket="Tidak dibuka resmi; hasil 2021-2026 terlihat sebagai pembanding H17b."),
                 p("Uji maju", "Rencana mulai 1 Jan 2027", "DES", False, ket="Dihentikan 25 Okt 2026 sebelum mulai (H17c & H17d gagal).")],
     "kriteria": [k("CAGR bersih ≥ pembanding", ("5,9% vs 7,0%", False)), k("Rata-rata yield penghasilan ≥ 4%/th", ("4,3% vs 2,0%", True)),
                  k("Penghasilan ≥ 3% di ≥ 80% tahun", ("5/6 tahun", True)), k("Tahun terburuk ≥ terburuk pembanding − 5 poin", ("2015 -38,7% vs -24,9%", False))],
     "angka": [a("Dev 2014-2019", cagr=5.9, dd=-38.7, bh=7.0, bh_dd=-24.9, bh_nama="Sama bobot universe likuid (dividen kena pajak, tanpa biaya)", utama=True,
                 ket="Data tahunan, jadi yang tersedia tahun terburuk (2015), bukan drawdown harian.", ekstra=[["Penghasilan dividen", "4,3%/th vs 2,0%"]], dd_label="Tahun terburuk"),
               a("Terlihat 2021-2026 (bukan bukti)", cagr=14.9, bh=0.7, bh_nama="Semua saham", ket="Bertepatan dengan boom batu bara.", ekstra=[["Penghasilan dividen", "9,9%/th"]])],
     "kenapa": "Penghasilan dividen tinggi dan stabil (lulus), tapi total return kalah pasar dan 2015 rugi -39% karena didominasi batu bara/tambang.",
     "kelemahan": ["Dev gagal; sempat direncanakan sebagai uji maju, lalu dihentikan setelah H17c/H17d gagal.", "Universe dev 217.",
                   "Portofolio terkonsentrasi di komoditas (ITMG, PTBA, ADRO, HRUM).", "Hasil 2021-2026 sudah terlihat."],
     "pelajaran": "Dividen tertinggi di IDX = taruhan siklus komoditas.", "terkait": ["H17b", "H2"], "sumber": "RENCANA_SCREENER.md:356"},

    {"kode": "H17b", "keluarga": "H17", "nama": "Pemburu Dividen + saringan anti-trap", "kategori": "dividen", "status": "tidak_diadopsi",
     "tgl_kunci": "2026-10-23", "tgl_uji": "2026-10-23", "skor": "tidak diadopsi",
     "awam": "Seperti H17a, tapi membuang saham yang dividennya berisiko dipotong (payout terlalu tinggi, laba anjlok, utang besar).",
     "aturan": {"Universe": UDES + " (2021-2026, butuh fundamental TTM).",
                "Sinyal masuk": "Calon H17a yang lolos: payout TTM ≤ 100%, laba TTM tidak turun > 30%, dividen tahun lalu ≥ 70% tahun sebelumnya, DER ≤ 2 (bukan bank), arus kas operasi ≥ dividen. 10 yield tertinggi.",
                "Keluar / stop": "Sama dengan H17a.", "Ukuran posisi": "Sama bobot.", "Biaya": BIAYA},
     "periode": [p("Uji tunggal", "Portofolio 2021-2026", "DES historis", True, "tidak diadopsi")],
     "kriteria": [k("CAGR bersih > H17a periode sama", ("4,9% vs 14,9%", False)),
                  k("Tahun penghasilan turun > 30% lebih sedikit dari H17a", ("1 vs 0", False)),
                  k("Rata-rata yield penghasilan ≥ 4%", ("7,6%", True))],
     "angka": [a("2021-2026", cagr=4.9, bh=14.9, bh_nama="H17a periode sama", utama=True, ekstra=[["Penghasilan dividen", "7,6%/th vs H17a 9,9%"]])],
     "kenapa": "Saringan membuang terutama 'dividen dipotong' (47) dan 'payout > 100%' (39), termasuk batu bara yang menang besar 2021-2025.",
     "kelemahan": ["Tanpa periode dev terpisah (data fundamental 2019+)."], "pelajaran": "Dividend trap sulit disaring dengan aturan sederhana.",
     "terkait": ["H17a"], "sumber": "RENCANA_SCREENER.md:364"},

    {"kode": "H17c", "keluarga": "H17", "nama": "Uji silang dividen_v1 di saham non-syariah", "kategori": "dividen", "status": "gagal",
     "tgl_kunci": "2026-10-25", "tgl_uji": "2026-10-25", "skor": "1/4",
     "awam": "Aturan uji maju Dividen (dividen_v1) dijalankan di saham yang tidak pernah syariah (bank, asuransi, dll.) 2014-2026. Aturannya tidak pernah dibentuk dari data ini, jadi kalau tetap bekerja, polanya umum dan bukan kebetulan batu bara.",
     "aturan": {"Aturan": "Persis dividen_v1 (fungsi simulasi uji maju dipakai apa adanya): 10 yield tertinggi yang bayar dividen 3 tahun berturut-turut, maks 3 per sektor, rebalance tiap Januari, pajak dividen 10%.",
                "Universe": "153 kode di data harga yang tidak pernah masuk DES OJK dan tidak ada di daftar 217 syariah. Nilai transaksi 20 hari ≥ Rp5 M, harga ≥ Rp50.",
                "Pembanding": "IHSG (harga) dan bobot sama semua saham likuid universe sama (dividen kena pajak, tanpa biaya).",
                "Catatan": "Non-syariah tidak bisa dibeli; hanya menguji apakah polanya umum.", "Biaya": BIAYA},
     "periode": [p("Uji silang", "Jan 2014 s/d 23 Okt 2026", "153 kode non-syariah (11-41 likuid)", True, "gagal", "1/4")],
     "kriteria": [k("1. Penghasilan rata-rata ≥ 4%/th dan ≥ 3% di ≥ 80% tahun penuh", ("2,35%/th; ≥ 3% di 17% tahun", False)),
                  k("2. CAGR ≥ IHSG dan ≥ pembanding bobot sama", ("1,07% vs IHSG 1,90% / bobot sama 0,35%", False)),
                  k("3. Max DD harian tidak lebih buruk dari IHSG − 10 poin", ("-48,4% vs batas -55,3%", True)),
                  k("4. Tahun terburuk ≥ terburuk pembanding − 5 poin", ("2024 -21,6% vs batas -19,5%", False))],
     "angka": [a("2014 - Okt 2026", cagr=1.07, dd=-48.4, bh=1.90, bh_dd=-45.3, bh_nama="IHSG (harga)", utama=True,
                 tile=[["Penghasilan dividen", "2,35%/th", "per ekuitas awal tahun, setelah pajak"], ["Saham dipegang", "6,9", "rata-rata; batas 3 per sektor"],
                       ["Kas menganggur", "24,9%", "rata-rata ekuitas"]],
                 ket="Bobot sama universe sama: CAGR 0,35%. Universe didominasi bank, rokok, menara.")],
     "tabel": {"judul": "Per tahun (%)", "kolom": ["Tahun", "Penghasilan", "Total", "Bobot sama", "IHSG"], "baris": [['2014', '1,4', '+10,9', '+30,5', '+22,3'], ['2015', '1,4', '-4,8', '-14,5', '-12,1'], ['2016', '2,2', '+42,1', '+43,1', '+15,3'], ['2017', '2,2', '+4,5', '+30,3', '+20,0'], ['2018', '1,8', '-4,2', '-8,3', '-2,5'], ['2019', '2,2', '-9,9', '-2,6', '+1,7'], ['2020', '2,6', '+7,7', '-1,0', '-5,1'], ['2021', '2,7', '+12,8', '+22,1', '+10,1'], ['2022', '2,6', '+13,1', '-13,8', '+4,1'], ['2023', '2,7', '+7,1', '-5,4', '+6,2'], ['2024', '3,2', '-21,6', '-11,8', '-2,7'], ['2025', '3,3', '+6,3', '-0,3', '+22,1'], ['2026*', '3,2', '-30,8', '-35,0', '-37,1']]},
     "kenapa": "Saham non-syariah likuid yang rutin bayar dividen sedikit (bank, rokok, menara). Batas 3 per sektor membuat portofolio rata-rata 6,9 saham dan seperempat modal menganggur, sehingga penghasilan hanya 1,4-3,3% dan return di bawah IHSG.",
     "kelemahan": ["Survivorship (data Yahoo hanya saham yang masih ada).", "Universe kecil, didominasi bank; batas sektor membuat < 10 saham.",
                   "Bank besar naik kuat 2014-2022 (diketahui umum).", "Uji ke ±39-40."],
     "pelajaran": "Aturan dividen_v1 tidak terbukti umum di luar saham syariah.", "terkait": ["H17a", "H17d"], "sumber": "RENCANA_SCREENER.md:682"},

    {"kode": "H17d", "keluarga": "H17", "nama": "dividen_v1 di saham syariah 2014-2026", "kategori": "dividen", "status": "gagal",
     "lencana": ["pasca_hasil"], "tgl_kunci": "2026-10-25", "tgl_uji": "2026-10-25", "skor": "2/4",
     "awam": "Aturan uji maju Dividen dijalankan mundur di saham syariah 2014-2026. Pelengkap H17c: datanya sudah pernah terlihat dan batas sektor dibuat setelah melihat dominasi batu bara, jadi buktinya lemah.",
     "aturan": {"Aturan": "Persis dividen_v1, sama dengan H17c.",
                "Universe": "2014-2019: " + U217 + " 2020+: " + UDES + " Nilai transaksi 20 hari ≥ Rp5 M, harga ≥ Rp50.",
                "Pembanding": "IHSG (harga) dan bobot sama semua saham likuid universe sama.", "Biaya": BIAYA},
     "periode": [p("Historis", "Jan 2014 s/d 23 Okt 2026", "syariah (217 lalu DES)", True, "gagal", "2/4")],
     "kriteria": [k("1. Penghasilan rata-rata ≥ 4%/th dan ≥ 3% di ≥ 80% tahun penuh", ("5,63%/th; ≥ 3% di 75% tahun", False)),
                  k("2. CAGR ≥ IHSG dan ≥ pembanding bobot sama", ("6,37% vs IHSG 1,90% / bobot sama 4,26%", True)),
                  k("3. Max DD harian tidak lebih buruk dari IHSG − 10 poin", ("-52,7% vs batas -55,3%", True)),
                  k("4. Tahun terburuk ≥ terburuk pembanding − 5 poin", ("2015 -32,9% vs batas -29,9%", False))],
     "angka": [a("2014 - Okt 2026", cagr=6.37, dd=-52.7, bh=1.90, bh_dd=-45.3, bh_nama="IHSG (harga)", utama=True,
                 tile=[["Penghasilan dividen", "5,63%/th", "2015-2017 hanya 2,4-2,8%"], ["Saham dipegang", "10,0", "rata-rata"],
                       ["Bobot sama", "4,26%", "universe syariah likuid"]],
                 ket="Penghasilan 2019-2025 tinggi (4,6-11,6%) didorong batu bara. Pasca hasil, bukan bukti.")],
     "tabel": {"judul": "Per tahun (%)", "kolom": ["Tahun", "Penghasilan", "Total", "Bobot sama", "IHSG"], "baris": [['2014', '3,9', '+20,3', '+15,8', '+22,3'], ['2015', '2,4', '-32,9', '-24,9', '-12,1'], ['2016', '2,5', '+26,2', '+28,1', '+15,3'], ['2017', '2,8', '+7,7', '+11,2', '+20,0'], ['2018', '3,5', '-10,3', '+9,7', '-2,5'], ['2019', '5,4', '+9,8', '+10,3', '+1,7'], ['2020', '4,7', '+1,5', '+6,3', '-5,1'], ['2021', '4,6', '+9,5', '+9,6', '+10,1'], ['2022', '6,9', '+27,5', '-11,1', '+4,1'], ['2023', '10,4', '-6,3', '-12,5', '+6,2'], ['2024', '11,6', '+4,0', '+5,9', '-2,7'], ['2025', '8,9', '+34,1', '+63,6', '+22,1'], ['2026*', '5,2', '+10,0', '-27,5', '-37,1']]},
     "kenapa": "Total return mengalahkan IHSG, tapi penghasilan hanya tinggi saat boom batu bara; 2015-2017 di bawah 3%, dan 2015 rugi -32,9%.",
     "kelemahan": ["Pasca hasil: 2014-2019 dipakai H17a, 2021-2026 terlihat lewat H17b, batas sektor dibuat setelah lihat data.",
                   "2014-2019 status syariah dari masa kini.", "Survivorship."],
     "pelajaran": "Dividen syariah tertinggi = taruhan siklus batu bara, juga dengan batas 3 per sektor.", "terkait": ["H17a", "H17c"], "sumber": "RENCANA_SCREENER.md:682"},

    {"kode": "H18", "keluarga": "H18", "nama": "Persistensi reksa dana syariah", "kategori": "reksadana", "status": "belum_dikunci",
     "tgl_kunci": None, "tgl_uji": None, "skor": "—",
     "awam": "Apakah reksa dana syariah yang bagus tahun ini cenderung tetap bagus tahun depan? Kalau ya, memilih berdasarkan skor masuk akal.",
     "aturan": {"Rencana": "Reksa dana dengan skor kuartil teratas di tahun T, apakah tetap di atas median kategori di tahun T+1 lebih sering dari 50%?",
                "Syarat jalan": "Riwayat NAV ≥ 3 tahun (pengumpulan harian mulai 23 Okt 2026, atau sumber riwayat panjang)."},
     "periode": [], "kriteria": [], "angka": [],
     "kenapa": "Belum diuji: data NAV baru ±1 tahun.", "kelemahan": [], "pelajaran": "",
     "terkait": [], "sumber": "RENCANA_SCREENER.md:433"},
]

H19_KUNCI = "2026-10-24"
H19_KRIT = K6 + ["CAGR 10 posisi > beli-tahan bobot sama (8,1%)", "Bootstrap bulanan 98% batas bawah > 0"]
H19_UMUM = {"Universe": U217 + " " + LIKUID + " Data dipotong 2019-12-31.",
            "Stop pelindung": "Stop awal entry − 3×ATR14, trailing seperti H11a; close < stop → jual open besok.",
            "Ukuran posisi": "Maks 10 posisi @10%, sinyal hari sama dipilih acak (seed 7). 1 posisi per ticker.", "Biaya": BIAYA}


def h19(kode, nama, awam, masuk, keluar, trade, wr, untung, rugi, exp, kotor, pf, cagr, dd, bulan, skor, lulus, kenapa, stop=True):
    aturan = {"Universe": H19_UMUM["Universe"], "Sinyal masuk": masuk, "Keluar": keluar}
    if stop:
        aturan["Stop pelindung"] = H19_UMUM["Stop pelindung"]
    aturan["Ukuran posisi"] = H19_UMUM["Ukuran posisi"]
    aturan["Biaya"] = BIAYA
    return {"kode": kode, "keluarga": "H19", "nama": nama, "kategori": "indikator", "status": "gagal",
            "tgl_kunci": H19_KUNCI, "tgl_uji": H19_KUNCI, "skor": skor, "awam": awam, "aturan": aturan,
            "periode": [p("Dev", "2010-2019", "217 saham", True, "gagal", skor), p("Holdout", "2020+", "DES historis", False)],
            "kriteria": [k(t, lulus[i]) for i, t in enumerate(H19_KRIT)],
            "angka": [a("Dev 2010-2019", cagr=cagr, dd=dd, trade=trade, wr=wr, net=exp, kotor=kotor, bh=8.1, bh_nama="Beli-tahan bobot sama 217", utama=True,
                        ket=f"Rata-rata untung +{untung}% vs rugi {rugi}%, profit factor {pf}, bulan positif {bulan}%.")],
            "kenapa": kenapa,
            "kelemahan": ["Tujuh hipotesis sekaligus (uji ke ±18-24): risiko lulus kebetulan tinggi, karena itu ada kriteria ke-8.", "Universe 217 (bias survivorship)."],
            "pelajaran": "Indikator klasik di saham individual IDX tidak menutup biaya ±1,2%.",
            "terkait": [x for x in ["H19a", "H19b", "H19c", "H19d", "H19e", "H19f", "H19g"] if x != kode],
            "sumber": "RENCANA_SCREENER.md:435"}


def _gagal_semua(exp_ok=False, pemb_ok=False, cagr_ok=False, nilai_exp="", nilai_cagr=""):
    return [(nilai_exp, exp_ok), (TT, pemb_ok), (TT, False), (TT, False), (TT, False), (TT, False), (nilai_cagr, cagr_ok), (TT, False)]


HIPOTESIS += [
    h19("H19a", "Golden cross MA50/MA200", "Beli saat rata-rata 50 hari memotong ke atas rata-rata 200 hari, jual saat memotong ke bawah.",
        "MA50 memotong ke atas MA200.", "MA50 < MA200, atau batas 500 hari.", 234, 29.9, 11.6, -7.2, -1.57, -0.31, 0.69, -3.8, -37.7, 23, "0/8",
        _gagal_semua(nilai_exp="-1,57%", nilai_cagr="-3,8%"), "Kotor pun negatif; 90% trade kena stop pelindung sebelum death cross."),
    h19("H19b", "MACD cross di atas nol + MA200", "Beli saat garis MACD memotong ke atas garis sinyalnya di area positif dan harga di atas rata-rata 200 hari.",
        "MACD memotong ke atas signal, MACD > 0, close > MA200.", "MACD < signal, atau batas 500 hari.", 1154, 26.3, 8.3, -4.3, -0.96, 0.25, 0.69, -10.5, -64.2, 25, "0/8",
        _gagal_semua(nilai_exp="-0,96%", nilai_cagr="-10,5%"), "Kotor +0,25% jauh di bawah biaya; winrate 26%."),
    h19("H19c", "Stochastic dari < 20 + MA200", "Beli saat Stochastic memantul dari area jenuh jual dalam tren naik, jual saat jenuh beli.",
        "%K memotong ke atas %D, %D kemarin < 20, close > MA200.", "%K > 80, atau batas 20 hari.", 832, 48.9, 4.9, -7.3, -1.33, -0.07, 0.65, -9.9, -63.0, 42, "0/8",
        _gagal_semua(nilai_exp="-1,33%", nilai_cagr="-9,9%"), "Winrate ±49%, tapi rugi rata-rata lebih besar dari untung."),
    h19("H19d", "RSI(2) < 10 + MA200 (Connors)", "Beli saham tren naik yang baru turun tajam 1-2 hari (RSI 2 hari sangat rendah), jual setelah memantul.",
        "RSI2 < 10 dan close > MA200.", "RSI2 > 70, atau batas 10 hari.", 1983, 50.8, 3.0, -4.4, -0.64, 0.61, 0.70, -11.6, -68.9, 44, "1/8",
        [("-0,64%", False), ("di atas", True), (TT, False), (TT, False), (TT, False), (TT, False), ("-11,6%", False), (TT, False)],
        "Kotor +0,61% (winrate sebelum biaya 63%), tapi biaya ±1,25% membalik jadi rugi. Dengan fee saja +0,21% (laporan, putusan tidak berubah)."),
    h19("H19e", "Bollinger squeeze breakout", "Beli saat pita Bollinger paling sempit dalam 6 bulan lalu harga menembus pita atas dengan volume besar.",
        "Lebar band kemarin = terendah 120 hari, close > band atas, volume ≥ 1,5× rata-rata.", "Close < MA20, atau batas 500 hari.", 115, 37.4, 12.1, -5.3, 1.21, 2.61, 1.37, 1.4, -11.9, 21, "2/8",
        [("+1,21%", True), (TT, None), (TT, None), ("50% tahun", False), ("-1,93%", False), (TT, None), ("1,4% < 8,1%", False), (TT, None)],
        "Satu-satunya expectancy positif, tapi hanya 115 trade, bergantung pada 10 trade terbaik, tahun positif 50%, CAGR jauh di bawah beli-tahan."),
    h19("H19f", "Engulfing/hammer di low 20 hari", "Beli saat muncul pola candle pembalikan (bullish engulfing atau hammer) di dekat harga terendah 20 hari.",
        "Bullish engulfing atau hammer, low ≤ low terendah 20 hari × 1,02, volume ≥ rata-rata.", "Tanpa exit aturan; batas 5 hari.", 764, 34.0, 4.0, -3.8, -1.15, 0.07, 0.54, -8.6, -61.4, 32, "1/8",
        [("-1,15%", False), (TT, None), (TT, None), (TT, None), (TT, None), (TT, None), ("-8,6%", False), (TT, None)],
        "Kotor hampir nol; pola candle tidak menambah informasi."),
    h19("H19g", "BSJP (beli sore jual pagi)", "Beli di penutupan saham yang ditutup di harga tertinggi hari itu dengan volume besar, jual besok pagi saat pembukaan.",
        "Close ≥ 95% range hari itu, volume ≥ 2× rata-rata, close > kemarin. Beli di close hari itu.", "Jual open besok. Tanpa stop.", 1041, 18.6, 2.2, -1.8, -1.08, 0.21, 0.27, -10.8, -67.3, 4, "1/8",
        [("-1,08%", False), (TT, None), (TT, None), (TT, None), (TT, None), (TT, None), ("-10,8%", False), (TT, None)],
        "Gap pagi rata-rata +0,21%, jauh di bawah biaya; winrate turun dari 48% ke 19% setelah biaya.", stop=False),
]

HIPOTESIS.append({
    "kode": "H20", "keluarga": "H20", "nama": "Filter rezim JII (rata-rata 10 bulan)", "kategori": "rezim", "status": "gagal",
    "tgl_kunci": "2026-10-24", "tgl_uji": "2026-10-24", "skor": "4/4 dasar · sensitivitas gagal",
    "awam": "Pegang indeks saham syariah JII selama harganya di atas rata-rata 10 bulan; kalau di bawah, pindah ke kas. Tujuannya menghindari penurunan besar seperti 2008.",
    "aturan": {"Instrumen": "Indeks JII (^JKII, close) + asumsi dividen 2,5%/th − expense 2,0%/th. Kas = bunga antarbank FRED − 1,5%/th (BI-Rate bila kosong).",
               "Sinyal": "Close hari bursa terakhir bulan: JII < rata-rata 10 close akhir bulan → KAS; ≥ → PASAR. Bertindak hanya kalau berubah.",
               "Keluar": "Jual close hari bursa ke-1, biaya 0,70%; hari ke-2 s/d 4 return 0, kas berbunga mulai hari ke-5.",
               "Masuk": "Pencairan kas hari ke-1, beli close hari bursa ke-4, biaya 0,60%.",
               "Pembanding": "Beli-tahan JII (dividen & expense sama), satu kali biaya masuk 0,60%."},
    "periode": [p("Dev", "Mei 2001 s/d Des 2014", "JII", True, "gagal", "dasar 4/4, kriteria 5 gagal"),
                p("Holdout", "Jan 2015 s/d 23 Okt 2026", "JII", False)],
    "kriteria": [k("1. Max DD ≤ 2/3 × DD beli-tahan", ("-29,7% vs -66,5%", True)),
                 k("2. CAGR ≥ beli-tahan − 2%/th", ("20,67% vs batas 19,41%", True)),
                 k("3. Perpindahan ≤ 3 per tahun", ("1,24 (17×)", True)),
                 k("4. Menang di ≥ 60% jendela 5 tahun", ("74% dari 105", True)),
                 k("5. Kas 0%: kriteria 1-2 tetap lulus", ("CAGR 18,81% < 19,41%", False)),
                 k("6a. Dividen 4%: kriteria 1-2 tetap lulus", ("22,03% vs 23,16%; DD -29,0%", True)),
                 k("6b. Expense 1,6%: kriteria 1-2 tetap lulus", ("21,04% vs 21,88%; DD -29,5%", True))],
    "angka": [a("Dev 2001-2014", cagr=20.67, dd=-29.7, bh=21.41, bh_dd=-66.5, bh_nama="Beli-tahan JII", utama=True,
                ket="22% waktu di kas. Krisis 2008: -8,0% vs -55,9%. Tertinggal di 2009 (+43,6% vs +93,9%) dan whipsaw 2011 (-18,4% vs +1,3%).")],
    "tabel": {"judul": "Skenario dasar dan sensitivitas", "kolom": ["Skenario", "CAGR H20", "DD H20", "CAGR beli-tahan", "DD beli-tahan", "Hasil"],
              "baris": [["Dasar", "20,67%", "-29,7%", "21,41%", "-66,5%", "lulus 1-4"],
                        ["5. Kas 0%", "18,81%", "-30,3%", "21,41%", "-66,5%", "gagal k2"],
                        ["6a. Dividen 4%", "22,03%", "-29,0%", "23,16%", "-66,2%", "lulus"],
                        ["6b. Expense 1,6%", "21,04%", "-29,5%", "21,88%", "-66,5%", "lulus"],
                        ["Gabungan terburuk (laporan)", "20,51%", "-29,4%", "23,63%", "-66,1%", "—"]]},
    "kenapa": "Drawdown turun besar dan konsisten, tapi saat bunga kas dianggap 0%, CAGR jatuh di bawah batas: kemampuan menyamai beli-tahan bergantung pada bunga kas tinggi awal 2000-an.",
    "kelemahan": ["JII = indeks harga; dividen hanya asumsi.", "Eksekusi di close (open ^JKII tidak andal).",
                  "Kendaraan nyata (reksa dana indeks) punya biaya & jeda pencairan lebih besar.", "Holdout 2015+ sudah diketahui umum."],
    "pelajaran": "Filter rezim bisa memangkas drawdown, tapi hasil relatifnya rapuh terhadap asumsi kas.",
    "terkait": ["H13"], "sumber": "RENCANA_SCREENER.md:485",
})

H2122_KUNCI = "2026-10-24"
H2122_UMUM = {
    "Universe": "Dev: 766 kode yang pernah masuk DES 2019-2026 (dianggap syariah sepanjang dev). Holdout: DES OJK pada tanggal sinyal + 10 kode dari data resmi IDX (TECH, ENVY, DUCK, HKMU, JSKY, PURE, CBMF, FREN, META, WBSA).",
    "Filter": "Median nilai transaksi 60 hari ≥ Rp5 M, harga ≥ Rp100, data ≥ 250 hari, aktif ≥ 90% hari. Kalender IHSG.",
    "Rebalance": "Sinyal close hari bursa terakhir tiap bulan, eksekusi open hari bursa pertama bulan berikutnya (ditunda kalau tidak bisa ditransaksikan).",
    "Ukuran & buffer": "N = maks(10, 20% saham lolos). Beli peringkat ≤ N, pegang selama peringkat ≤ 2N. Saham baru 1/N ekuitas, pangkas kalau > 2/N.",
    "Saham hilang": "Mati = 0 sejak hari terakhir aktif; FREN → EXCL; META dibekukan Rp238 (META = 0 hanya laporan).",
    "Pembanding": "Bobot sama semua saham lolos tanpa biaya; JII + dividen 2,5%/th.",
    "Biaya": BIAYA + " Dihitung dari turnover nyata.",
}
def h2122_periode(skor):
    return [p("Dev", "Feb 2011 s/d Des 2019", "766 kode DES-ever, rata2 58 saham lolos", True, "gagal", skor, "Kriteria dasar 6/6 lulus, gagal di sensitivitas."),
            p("Holdout", "Jan 2020 s/d 23 Okt 2026", "DES historis + 10 kode IDX", False, ket="Tidak dibuka (dev gagal).")]


H2122_EW = "Bobot sama semua saham lolos, tanpa biaya"
TABEL_SENS_KOLOM = ["Skenario", "CAGR", "Max DD", "Pembanding bobot sama", "Syarat wajib", "Hasil"]
H2122_KELEMAHAN = ["Dev bukan point-in-time (status syariah dan survivorship).", "Pembanding bobot sama tanpa biaya (konservatif, disengaja).",
                   "Open 2011-2019 tidak bisa diverifikasi ke data IDX.", "META dinilai di close terakhir Rp238, bukan harga tender offer (tidak tercatat di data).",
                   "FREN → EXCL diasumsikan bernilai sama.", "Uji ke ±36-37."]

HIPOTESIS += [
    {"kode": "H21", "keluarga": "H21-H22", "nama": "Low volatility bulanan", "kategori": "faktor", "status": "gagal",
     "tgl_kunci": H2122_KUNCI, "tgl_uji": "2026-10-24", "skor": "6/6 · sensitivitas 1/4",
     "awam": "Tiap bulan pegang saham syariah yang paling tenang setahun terakhir. Tujuannya penurunan modal lebih dangkal dari pasar, dengan hasil yang tidak jauh tertinggal.",
     "aturan": {"Sinyal": "Standar deviasi return harian 250 hari bursa, peringkat 1 = terendah.", **H2122_UMUM,
                "Sensitivitas (merugikan)": "S1 biaya 2 tick · S2 likuiditas ≥ Rp20 M · S3 tanpa 5 ticker terbaik · S4 harga ≥ Rp200. Kriteria 1 dan 3 harus tetap lulus."},
     "periode": h2122_periode("6/6 + sensitivitas 1/4"),
     "kriteria": [k("1. Max DD ≤ 0,75 × max DD bobot sama", ("-23,95% vs batas -26,36%", True)), k("2. Max DD tidak lebih dalam dari JII", ("-23,95% vs -25,21%", True)),
                  k("3. CAGR bersih ≥ bobot sama − 2%/th", ("6,25% vs batas 5,80%", True)), k("4. CAGR bersih ≥ JII − 2%/th", ("6,25% vs batas 4,96%", True)),
                  k("5. Volatilitas tahunan ≤ 0,85 × bobot sama", ("13,05% vs batas 16,42%", True)),
                  k("6. Menang di ≥ 60% jendela 36 bulan (DD lebih dangkal dan CAGR ≥ bobot sama − 2%)", ("44/72 = 61,1%", True)),
                  k("S1 biaya 2 tick: kriteria 1 & 3 tetap lulus", ("CAGR 5,93% · DD -24,23%", True)),
                  k("S2 likuiditas ≥ Rp20 M: kriteria 1 & 3 tetap lulus", ("DD -27,79% vs batas -25,33%", False)),
                  k("S3 tanpa 5 ticker terbaik: kriteria 1 & 3 tetap lulus", ("CAGR 3,53% vs 5,80%; DD -30,25%", False)),
                  k("S4 harga ≥ Rp200: kriteria 1 & 3 tetap lulus", ("CAGR 5,30% vs batas 6,15%", False))],
     "angka": [a("Dev Feb 2011 - Des 2019", cagr=6.25, dd=-23.95, net=None, bh=7.80, bh_dd=-35.14, bh_nama=H2122_EW, utama=True,
                 ket="Kas rata-rata 5,2%. JII + 2,5%: CAGR 6,96%, DD -25,21%, vol 12,97%.",
                 tile=[["Volatilitas", "13,05%", "bobot sama 19,32%"], ["Turnover", "43,7%/th", "biaya dari turnover nyata"], ["Saham dipegang", "11,9", "rata-rata N dari ±58 lolos"]],
                 ekstra=[["Korelasi bulanan dengan Follow Tren", "0,34"]])],
     "tabel": {"judul": "Sensitivitas merugikan (kriteria 1 dan 3 harus tetap lulus)", "kolom": TABEL_SENS_KOLOM,
               "baris": [["Dasar", "6,25%", "-23,95%", "7,80% / -35,14%", "DD ≤ -26,36% · CAGR ≥ 5,80%", "lulus"],
                         ["S1 biaya 2 tick", "5,93%", "-24,23%", "7,80% / -35,14%", "DD ≤ -26,36% · CAGR ≥ 5,80%", "lulus"],
                         ["S2 likuiditas ≥ Rp20 M", "3,81%", "-27,79%", "3,57% / -33,77%", "DD ≤ -25,33% · CAGR ≥ 1,57%", "gagal (DD)"],
                         ["S3 tanpa TLKM, ICBP, JSMR, UNVR, KLBF", "3,53%", "-30,25% (bln)", "7,80% / -32,01% (bln)", "DD ≤ -24,01% · CAGR ≥ 5,80%", "gagal"],
                         ["S4 harga ≥ Rp200", "5,30%", "-24,02%", "8,15% / -34,31%", "DD ≤ -25,73% · CAGR ≥ 6,15%", "gagal (CAGR)"]]},
     "kenapa": "Drawdown memang lebih dangkal (-24% vs -35%) dan volatilitas jauh lebih rendah, tapi hasilnya bergantung pada lima saham besar defensif (TLKM, ICBP, JSMR, UNVR, KLBF). Tanpa mereka CAGR jatuh ke 3,5% dan drawdown malah lebih dalam; di universe Rp20 M dan harga ≥ Rp200 juga gagal.",
     "kelemahan": H2122_KELEMAHAN, "pelajaran": "Low volatility di IDX 2011-2019 = segelintir saham defensif besar, bukan efek yang menyebar. Tertinggal di tahun pasar naik (2016, 2018).",
     "terkait": ["H22", "H20", "H12a"], "sumber": "RENCANA_SCREENER.md:599"},
    {"kode": "H22", "keluarga": "H21-H22", "nama": "Momentum 12-1 bulanan", "kategori": "tren", "status": "gagal",
     "tgl_kunci": H2122_KUNCI, "tgl_uji": "2026-10-24", "skor": "6/6 · sensitivitas 1/3",
     "awam": "Tiap bulan pegang saham syariah yang naik paling kuat dalam 12 bulan, tanpa menghitung bulan terakhir (yang sering berbalik). Tujuannya total return di atas pasar setelah biaya.",
     "aturan": {"Sinyal": "Return dari akhir bulan t−12 ke akhir bulan t−1, peringkat 1 = tertinggi. Tanpa filter tren, tanpa stop.", **H2122_UMUM,
                "Beda dengan H11b & Follow Tren": "Peringkat relatif bulanan, keluar saat peringkat > 2N, selalu ±N saham (H11b/H11a: sinyal harian + trailing stop, sering kas).",
                "Sensitivitas (merugikan)": "S1 biaya 2 tick · S2 likuiditas ≥ Rp20 M · S3 harga ≥ Rp200. Kriteria 1 dan 5 harus tetap lulus."},
     "periode": h2122_periode("6/6 + sensitivitas 1/3"),
     "kriteria": [k("1. CAGR bersih > bobot sama", ("18,79% vs 7,80%", True)), k("2. CAGR bersih > JII + 2,5%", ("18,79% vs batas 9,46%", True)),
                  k("3. Bootstrap blok 3 bulan selisih bulanan vs bobot sama: batas bawah 90% > 0", ("+0,192%/bln", True)),
                  k("4. Selisih tahunan positif di ≥ 60% tahun (tahun parsial ikut: dev ≥ 6/9, holdout ≥ 5/7)", ("7/9 tahun", True)),
                  k("5. Tanpa 5 ticker terbaik: CAGR tetap > bobot sama", ("9,11% vs 7,80%", True)),
                  k("6. Max DD tidak lebih dalam dari bobot sama − 10 poin", ("-37,37% vs batas -45,14%", True)),
                  k("S1 biaya 2 tick: kriteria 1 & 5 tetap lulus", ("tanpa 5 terbaik 7,73% vs 7,80%", False)),
                  k("S2 likuiditas ≥ Rp20 M: kriteria 1 & 5 tetap lulus", ("tanpa 5 terbaik -1,37% vs 3,57%", False)),
                  k("S3 harga ≥ Rp200: kriteria 1 & 5 tetap lulus", ("22,92% · tanpa 5 terbaik 13,54% vs 8,15%", True))],
     "angka": [a("Dev Feb 2011 - Des 2019", cagr=18.79, dd=-37.37, bh=7.80, bh_dd=-35.14, bh_nama=H2122_EW, utama=True,
                 ket="Kas rata-rata 4,8%. JII + 2,5%: CAGR 6,96%. Lima penyumbang terbesar: NIKL, BRPT, SMBR, TKIM, AKRA.",
                 tile=[["Volatilitas", "24,52%", "bobot sama 19,32%"], ["Turnover", "131,6%/th", "biaya dari turnover nyata"], ["Saham dipegang", "11,9", "rata-rata N dari ±58 lolos"]],
                 ekstra=[["Korelasi bulanan dengan Follow Tren", "0,65"]])],
     "tabel": {"judul": "Sensitivitas merugikan (kriteria 1 dan 5 harus tetap lulus)", "kolom": TABEL_SENS_KOLOM,
               "baris": [["Dasar", "18,79%", "-37,37%", "7,80% / -35,14%", "CAGR > 7,80% · tanpa 5 terbaik 9,11% > 7,80%", "lulus"],
                         ["S1 biaya 2 tick", "17,15%", "-39,13%", "7,80% / -35,14%", "tanpa 5 terbaik 7,73% vs 7,80%", "gagal (tipis)"],
                         ["S2 likuiditas ≥ Rp20 M", "7,25%", "-47,37%", "3,57% / -33,77%", "tanpa BRPT, AKRA, PTPP, INKP, CPIN -1,37% vs 3,57%", "gagal"],
                         ["S3 harga ≥ Rp200", "22,92%", "-33,86%", "8,15% / -34,31%", "tanpa 5 terbaik 13,54% vs 8,15%", "lulus"]]},
     "kenapa": "Angka dasar kuat (18,8% vs 7,8%, lulus 6/6), tapi rapuh: dengan biaya 2 tick, tanpa 5 pemenang terbesar hasilnya sudah di bawah bobot sama; di universe likuid Rp20 M tanpa 5 pemenang hasilnya negatif.",
     "kelemahan": H2122_KELEMAHAN + ["Holdout tidak buta: H11a (tren) sudah lulus di 2020+ dan berkorelasi dengan momentum."],
     "pelajaran": "Momentum di IDX = segelintir saham yang naik besar, sama seperti Follow Tren (korelasi 0,65). Kalaupun lulus, tidak banyak menambah diversifikasi.",
     "terkait": ["H21", "H11b", "H11a"], "sumber": "RENCANA_SCREENER.md:599"},
]

H23_KRIT = ["1. Max DD ≤ 2/3 × DD beli-tahan JII", "2. CAGR ≥ beli-tahan JII − 2%/th",
            "3. CAGR ≥ campuran 50/50 dan CAGR/|DD| ≥ campuran 50/50", "4. Perpindahan ≤ 4 per tahun",
            "5. Menang di ≥ 60% jendela 5 tahun vs beli-tahan JII", "6. Kas 0%: kriteria 1-3 tetap lulus",
            "7. Biaya emas 4% pulang-pergi: kriteria 1-3 tetap lulus", "8. Dividen JII 4%: kriteria 1-3 tetap lulus"]
HIPOTESIS.append({
    "kode": "H23", "keluarga": "H23", "nama": "Dual momentum JII / emas / kas", "kategori": "rezim", "status": "gagal",
    "lencana": ["pasca_hasil"], "tgl_kunci": "2026-10-25", "tgl_uji": "2026-10-25", "skor": "2/5 dasar · sensitivitas gagal",
    "awam": "Tiap akhir bulan, lihat mana yang paling naik dalam 12 bulan terakhir: saham syariah (JII), emas, atau kas. Pegang yang paling kuat. Idenya dari penelitian tren lintas aset (Antonacci; Hurst, Ooi & Pedersen).",
    "aturan": {"Aset": "JII (close + dividen 2,5%/th − expense 2,0%/th, sama dengan H20); emas rupiah = GC=F × kurs USD/IDR (kurs dibersihkan, celah diisi titik akhir bulan FRED); kas = antarbank − 1,5%/th.",
               "Sinyal": "Close hari bursa terakhir bulan: return 12 bulan tiap aset (indeks total return model). Pegang yang tertinggi; bertindak hanya kalau berubah.",
               "Pindah": "Hari bursa ke-1: jual aset lama di close (kas: bunga berhenti). Hari ke-2 s/d 4 return 0. Close hari ke-4: beli aset baru (kas: bunga mulai hari ke-5).",
               "Biaya": "JII masuk 0,60% / keluar 0,70%; emas 1% beli + 1% jual.",
               "Pembanding": "Beli-tahan JII; campuran tetap 50% JII + 50% emas diseimbangkan tiap Januari."},
    "periode": [p("Dev", "Jul 2002 s/d Des 2014", "JII, emas, kas", True, "gagal", "dasar 2/5"),
                p("Holdout", "Jan 2015 s/d 23 Okt 2026", "JII, emas, kas", False, ket="Tidak dibuka (dev gagal).")],
    "kriteria": [k(H23_KRIT[0], ("-27,2% vs batas -44,4%", True)),
                 k(H23_KRIT[1], ("13,51% vs batas 17,80%", False)),
                 k(H23_KRIT[2], ("13,51% vs 18,86%; rasio 0,50 vs 0,47", False)),
                 k(H23_KRIT[3], ("1,44 (18×)", True)),
                 k(H23_KRIT[4], ("37% dari 91", False)),
                 k(H23_KRIT[5], ("CAGR 9,42% < 17,80%", False)),
                 k(H23_KRIT[6], ("CAGR 12,23% < 17,80%", False)),
                 k(H23_KRIT[7], ("CAGR 14,81% < 19,52%", False))],
    "angka": [a("Dev 2002-2014", cagr=13.51, dd=-27.2, bh=19.80, bh_dd=-66.5, bh_nama="Beli-tahan JII", utama=True,
                tile=[["Perpindahan", "1,44/th", "18 kali dalam 12,5 tahun"], ["Waktu di aset", "54 / 28 / 12%", "JII / emas / kas (6% pindah)"],
                      ["Campuran 50/50", "18,86%", "DD -40,2%"]],
                ket="Campuran tetap 50% JII + 50% emas (pembanding) lebih baik dari H23 di CAGR, dengan DD -40,2%.")],
    "tabel": {"judul": "Skenario dasar dan sensitivitas", "kolom": ["Skenario", "CAGR H23", "DD H23", "Beli-tahan JII", "Campuran 50/50", "Hasil"],
              "baris": [["Dasar", "13,51%", "-27,2%", "19,80% / -66,5%", "18,86% / -40,2%", "gagal k2, k3, k5"],
                        ["6. Kas 0%", "9,42%", "-34,5%", "19,80% / -66,5%", "18,86% / -40,2%", "gagal"],
                        ["7. Emas 4%", "12,23%", "-28,6%", "19,80% / -66,5%", "18,73% / -40,2%", "gagal"],
                        ["8. Dividen 4%", "14,81%", "-27,1%", "21,52% / -66,2%", "19,74% / -40,1%", "gagal"],
                        ["Gabungan terburuk (laporan)", "8,17%", "-38,1%", "21,52% / -66,2%", "19,61% / -40,1%", "—"]]},
    "kenapa": "Drawdown memang lebih dangkal, tapi CAGR tertinggal ±6%/th dari beli-tahan dan ±5%/th dari campuran 50/50 yang tidak pernah pindah. Return 12 bulan terlambat masuk lagi setelah kejatuhan (2009: -1,6% vs JII +93,9%).",
    "kelemahan": ["Pasca hasil: dekat dengan H20 yang gagal; data JII 2001-2014 sudah terlihat di H20, 2020+ di eksplorasi.",
                  "Holdout tidak buta (emas naik besar 2019-2026, JII melemah sejak ±2018).",
                  "Emas = futures AS × kurs, bukan harga emas digital/Antam sebenarnya.",
                  "Kurs Jun-Des 2003 dan Agt 2008 hasil interpolasi.", "Uji ke ±38."],
    "pelajaran": "Pindah-pindah aset mengikuti tren kalah dari sekadar memegang campuran tetap. Di dev, diversifikasi sederhana JII + emas memberi hampir semua manfaat (DD -40% vs -66%) tanpa kehilangan return.",
    "terkait": ["H20"], "sumber": "RENCANA_SCREENER.md:619",
})

PELAJARAN = [
    {"judul": "Biaya ±1,2% memakan edge kecil",
     "isi": "Banyak pola punya return kotor di atas acak, tapi lebih kecil dari biaya pulang-pergi. Contoh: H2 kotor +0,40% → bersih -0,77%; H8 +1,32% → -0,02%; H19 kotor 0 s/d +0,6% per trade.",
     "bukti": ["H0", "H2", "H3", "H5", "H6", "H8", "H10", "H19d", "H19g"]},
    {"judul": "Bagus di data lama tidak menjamin apa pun",
     "isi": "H4 positif di 2010-2021 dan 2020-2023 (+1,23% / trade), lalu rugi di semua tahun 2024+ (-1,46%). Holdout yang benar-benar baru adalah hakim terakhir.",
     "bukti": ["H4"]},
    {"judul": "Tidak ada yang lulus bersih; satu yang lanjut ke paper",
     "isi": "Follow Tren (H11a) gagal tipis di dev (6/7), holdout dibuka sebagai pengecualian lalu lulus 7/7, jadi dilanjutkan ke paper trade. Edge-nya dari sedikit trade besar di saham volatil: median trade negatif, bulan positif ±40%.",
     "bukti": ["H11a", "H12a", "H12b", "H22"]},
    {"judul": "Data 2010-2019 bias survivorship",
     "isi": "Daftar 217 saham adalah saham syariah yang masih ada hari ini. DES historis baru ada sejak Des 2019, jadi dev sebelum 2020 cenderung terlalu bagus.",
     "bukti": ["H11a", "H13", "H19a"]},
    {"judul": "Menambah filter ke Follow Tren tidak membantu konsisten",
     "isi": "Ukuran posisi, filter IHSG, prioritas, laba tumbuh, ritel: tidak ada yang menaikkan MAR di semua set independen. Momentum 12-1 bulanan (H22) juga hanya mengulang sumber untung yang sama (korelasi 0,65) dan rapuh tanpa 5 pemenangnya.",
     "bukti": ["H12a", "H13", "H14a", "H14b", "H15b"]},
    {"judul": "Data aliran dana gratis tidak prediktif",
     "isi": "Akumulasi asing, transaksi negosiasi, antrian penutupan, dan perubahan kepemilikan KSEI tidak lebih baik dari saham acak.",
     "bukti": ["H7a", "H7b", "H9", "H10", "H15a"]},
    {"judul": "Valuasi murah tidak mengalahkan rata-rata pasar",
     "isi": "Saham Undervalue tidak menang setelah biaya, dan peluangnya mencapai nilai wajar tidak berbeda dari saham biasa dengan target naik sama.",
     "bukti": ["H16a", "H16b", "H16c"]},
    {"judul": "Dividen tertinggi = taruhan siklus komoditas",
     "isi": "Penghasilan dividen lulus (4,3%/th), tapi total return kalah pasar dan 2015 rugi -39%. Saringan anti-trap malah membuang pemenang batu bara.",
     "bukti": ["H17a", "H17b"]},
    {"judul": "Drawdown bisa dipangkas, tapi hasilnya rapuh",
     "isi": "H20 memotong DD dari -66% ke -30%, tapi gagal saat bunga kas dianggap 0%. H21 low vol memotong DD dari -35% ke -24%, tapi bergantung pada lima saham defensif besar dan gagal di universe yang lebih likuid.",
     "bukti": ["H20", "H21"]},
    {"judul": "Alat ukur bisa menipu",
     "isi": "Beli-tahan dengan rebalance harian menggelembungkan pembanding (DES 2020+: 6,5% vs bulanan 0,5%), dan laporan bulanan Follow Tren melebih-lebihkan dibanding cara paper (21,3% vs 17,3%).",
     "bukti": ["H13", "H11a"]},
    {"judul": "Hasil bergantung periode", "jenis": "eksplorasi",
     "isi": "Temuan eksplorasi, bukan bukti. Follow Tren cara paper median +9% di 2010-2019 tapi sekitar +24% di 2020-2026; H11b dan H17a gagal di data lama tapi lulus di 2020+, H21/H22 sebaliknya. Strategi jangka pendek tetap kalah biaya di kedua periode. Pasar ramai setelah COVID bisa saja tidak berulang.",
     "bukti": ["H11a", "H11b", "H17a", "H22"]},
]

ANALISIS = [
    {"id": "konvergensi", "nama": "Konvergensi ke nilai wajar", "tgl": "2026-10-22",
     "isi": "Peluang saham Undervalue mencapai nilai wajar dalam 1 tahun 21% (2021-2023) dan 29% (2021-2026), tidak berbeda dari saham Wajar dengan target naik sama. Yang sampai sempat turun median -9% s/d -14% dulu.",
     "terkait": ["H16a", "H16c"], "sumber": "RENCANA_SCREENER.md:331"},
    {"id": "trap", "nama": "Dividend trap", "tgl": "2026-10-23",
     "isi": "89 kejadian yield ≥ 6% (2012-2024): 65% trap (rugi atau dividen dipotong). Tanda yang lebih sering trap: dividen spesial, laba turun > 30%, arus kas < dividen. Sampel kecil.",
     "terkait": ["H17a", "H17b"], "sumber": "RENCANA_SCREENER.md:376"},
    {"id": "batas_paper", "nama": "Zona normal paper H11a", "tgl": "2026-10-22",
     "isi": "Bootstrap 5000 jalur dari kurva cara paper 2020-2026 (CAGR 17,3%, DD -40,5%). Waspada di bawah persentil 5, gagal di bawah persentil 1. Dikunci di batas_paper h11a_v1.",
     "terkait": ["H11a"], "sumber": "RENCANA_SCREENER.md:379"},
    {"id": "spread", "nama": "Spread nyata IDX", "tgl": "2026-10-20",
     "isi": "Spread penutupan median ±1,1-1,2 tick. Model 1 tick per sisi ±2× setengah spread; semua putusan tetap memakai model 1 tick.",
     "terkait": ["H7a", "H19d"], "sumber": "RENCANA_SCREENER.md:391"},
]


def batang(judul, label, seri, ket=None, satuan="%"):
    return {"jenis": "batang", "judul": judul, "label": label, "seri": [{"nama": n, "data": d} for n, d in seri], "ket": ket, "satuan": satuan}


def kurva_hasil(judul, nama, kolom, ket):
    return {"jenis": "kurva", "judul": judul, "sumber": {"hasil": nama, "x": "bulan", "kolom": kolom}, "ket": ket}


GRAFIK = {
    "H4": [batang("Bersih per trade per tahun, holdout 2024+", ["2024", "2025", "2026*"], [("Bersih/trade", [-1.65, -0.68, -1.98])], "Semua tahun negatif di data yang benar-benar baru. *2026 sebagian.")],
    "H8": [batang("Bersih per trade per tahun, dev", ["2020", "2021", "2022", "2023"], [("Bersih/trade", [1.76, 0.55, 0.03, -1.57])], "Efeknya melemah tiap tahun.")],
    "H11a": [
        {"jenis": "kurva", "judul": "Kurva modal holdout 2020-2026 (cara paper) · contoh 1 simulasi", "sumber": {"backtest": "h11a_2020"}, "ket": "Contoh 1 simulasi Monte Carlo (seed 7); angka utama memakai median 100 simulasi. Modal awal = 100. 10% ekuitas saat beli, harga pasar, dividen dipotong pajak."},
        {"jenis": "batang", "judul": "Return portofolio per tahun (cara paper) · contoh 1 simulasi", "sumber": {"backtest_tahun": ["h11a_dev", "h11a_2020"]}, "ket": "Contoh 1 simulasi Monte Carlo (seed 7). 2011-2019 = dev 217 saham, 2020+ = DES historis. 2021 menyumbang sebagian besar hasil.", "satuan": "%"},
        {"jenis": "kurva", "judul": "Kurva modal dev 2010-2019 (217 saham) · contoh 1 simulasi", "sumber": {"backtest": "h11a_dev"}, "ket": "Contoh 1 simulasi Monte Carlo (seed 7). Modal awal = 100. Universe 217 (bias survivorship)."},
    ],
    "H12a": [batang("CAGR dev 2010-2019", ["H11a", "H12a", "H12b", "Beli-tahan"], [("CAGR", [12.1, 5.0, 5.2, 8.1])], "Membuang saham volatil memotong CAGR lebih dari separuh.")],
    "H12b": [batang("CAGR dev 2010-2019", ["H11a", "H12a", "H12b", "Beli-tahan"], [("CAGR", [12.1, 5.0, 5.2, 8.1])], "Sama dengan H12a.")],
    "H13": [batang("MAR (CAGR / |DD|) per konfigurasi", ["H11a", "S", "R", "P", "S+R+P"],
                   [("Set A non-syariah", [0.07, 0.06, -0.01, 0.07, 0.03]), ("Set B DES di luar 217", [0.69, 0.53, 0.68, 0.69, 0.44])],
                   "Diadopsi hanya kalau MAR naik di kedua set. Tidak ada yang lolos.", satuan="")],
    "H14a": [batang("MAR per konfigurasi", ["H11a", "H14a", "H14b"], [("Set A non-syariah", [0.14, 0.21, 1.21]), ("Syariah DES 2020+", [0.80, 0.57, 0.64])],
                    "Membantu di non-syariah, menurunkan MAR di syariah.", satuan="")],
    "H14b": [batang("CAGR per konfigurasi", ["H11a", "H14a", "H14b"], [("Set A non-syariah", [4.0, 4.4, 4.1]), ("Syariah DES 2020+", [30.3, 14.7, 12.7])],
                    "Di syariah, filter fundamental memotong CAGR lebih dari separuh.")],
    "H15a": [kurva_hasil("Kurva modal dev 2011-2019", "hasil_h15a_dev", [["Desil atas (bersih)", "atas_bersih"], ["Pembanding (tanpa biaya)", "pembanding"]],
                         "Modal awal = 100, dihitung dari return bulanan tersimpan.")],
    "H15b": [batang("MAR per set", ["Dev 217", "Set A", "Syariah DES"], [("H11a", [0.45, 0.17, 0.75]), ("H15b", [0.35, 0.17, 0.82])], "Tidak konsisten di ketiga set.", satuan="")],
    "H16a": [kurva_hasil("Kurva modal dev 2021-04..2023-12", "hasil_h16_dev", [["Undervalue (bersih)", "undervalue_bersih"], ["Pembanding", "pembanding"], ["Overvalue (bersih)", "overvalue_bersih"]],
                         "Modal awal = 100, dari return bulanan tersimpan."),
             batang("Selisih vs pembanding per tahun", ["2021*", "2022", "2023"], [("Selisih", [-13.8, 13.1, -9.8])], "*2021 sebagian (mulai April).")],
    "H16b": [kurva_hasil("Kurva modal dev 2021-04..2023-12", "hasil_h16_dev", [["Layak (bersih)", "layak_bersih"], ["Pembanding", "pembanding"]], "Bulan tanpa saham dihitung 0."),
             batang("Selisih vs pembanding per tahun", ["2021*", "2022", "2023"], [("Selisih", [2.3, -18.8, -2.5])], "*2021 sebagian.")],
    "H16c": [kurva_hasil("Kurva modal dev 2021-04..2023-12", "hasil_h16c_dev", [["Undervalue berkualitas (bersih)", "berkualitas_bersih"], ["Pembanding", "pembanding"], ["Undervalue H16a (bersih)", "undervalue_bersih"]],
                         "Modal awal = 100."),
             batang("Selisih vs pembanding per tahun", ["2021*", "2022", "2023"], [("Selisih", [-11.9, 20.7, -7.2])], "Untungnya datang dari satu tahun (2022).")],
    "H17a": [{"jenis": "batang", "judul": "Total return per tahun, dev 2014-2019", "sumber": {"hasil_tahun": ["hasil_h17a_dev"], "kolom": [["H17a", "total", 0], ["Pembanding", "pembanding_total", 0]]}, "ket": "Dividen setelah pajak 10% sudah termasuk.", "satuan": "%"},
             {"jenis": "batang", "judul": "Penghasilan dividen per tahun, dev", "sumber": {"hasil_tahun": ["hasil_h17a_dev"], "kolom": [["H17a", "penghasilan", 0], ["Pembanding", "pembanding_penghasilan", 0]]}, "ket": "Dividen diterima setelah pajak / nilai beli.", "satuan": "%"}],
    "H17b": [{"jenis": "batang", "judul": "Total return per tahun 2021-2026", "sumber": {"hasil_tahun": ["hasil_h17b", "hasil_h17a_2021"], "kolom": [["H17b", "total", 0], ["H17a", "total", 1]]}, "ket": "*2026 sebagian. Hasil H17a 2021-2026 bukan bukti (dev gagal).", "satuan": "%"}],
    "H21": [{"jenis": "kurva", "judul": "Kurva modal dev Feb 2011 - Des 2019", "sumber": {"h2122": "h21"}, "ket": "Modal awal = 100. Bersih setelah biaya; pembanding tanpa biaya."},
            {"jenis": "batang", "judul": "Return per tahun, dev", "sumber": {"h2122_tahun": "h21"}, "ket": "2011 mulai Februari.", "satuan": "%"}],
    "H22": [{"jenis": "kurva", "judul": "Kurva modal dev Feb 2011 - Des 2019", "sumber": {"h2122": "h22"}, "ket": "Modal awal = 100. Bersih setelah biaya; pembanding tanpa biaya."},
            {"jenis": "batang", "judul": "Return per tahun, dev", "sumber": {"h2122_tahun": "h22"}, "ket": "2011 mulai Februari. Kalah dari bobot sama di 2015 dan 2019.", "satuan": "%"}],
    "H17c": [batang("Penghasilan dividen per tahun, non-syariah", ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'],
                    [("H17c", [1.4, 1.4, 2.2, 2.2, 1.8, 2.2, 2.6, 2.7, 2.6, 2.7, 3.2, 3.3])], "Batas lulus: rata-rata ≥ 4% dan ≥ 3% di ≥ 80% tahun."),
             batang("Return total per tahun", ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'],
                    [("H17c", [10.9, -4.8, 42.1, 4.5, -4.2, -9.9, 7.7, 12.8, 13.1, 7.1, -21.6, 6.3]), ("Bobot sama", [30.5, -14.5, 43.1, 30.3, -8.3, -2.6, -1.0, 22.1, -13.8, -5.4, -11.8, -0.3]), ("IHSG", [22.3, -12.1, 15.3, 20.0, -2.5, 1.7, -5.1, 10.1, 4.1, 6.2, -2.7, 22.1])],
                    "Tahun penuh saja; 2026 (s/d Okt): -30,8% vs IHSG -37,1%.")],
    "H17d": [batang("Penghasilan dividen per tahun, syariah", ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'],
                    [("H17d", [3.9, 2.4, 2.5, 2.8, 3.5, 5.4, 4.7, 4.6, 6.9, 10.4, 11.6, 8.9])], "Batas lulus: rata-rata ≥ 4% dan ≥ 3% di ≥ 80% tahun."),
             batang("Return total per tahun", ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'],
                    [("H17d", [20.3, -32.9, 26.2, 7.7, -10.3, 9.8, 1.5, 9.5, 27.5, -6.3, 4.0, 34.1]), ("Bobot sama", [15.8, -24.9, 28.1, 11.2, 9.7, 10.3, 6.3, 9.6, -11.1, -12.5, 5.9, 63.6]), ("IHSG", [22.3, -12.1, 15.3, 20.0, -2.5, 1.7, -5.1, 10.1, 4.1, 6.2, -2.7, 22.1])],
                    "Tahun penuh saja; 2026 (s/d Okt): +10,0% vs IHSG -37,1%.")],
    "H23": [batang("CAGR per skenario, dev 2002-2014", ["Dasar", "Kas 0%", "Emas 4%", "Dividen 4%", "Terburuk"],
                   [("H23", [13.51, 9.42, 12.23, 14.81, 8.17]), ("Beli-tahan JII", [19.80, 19.80, 19.80, 21.52, 21.52]), ("Campuran 50/50", [18.86, 18.86, 18.73, 19.74, 19.61])],
                   "Batas lulus = beli-tahan − 2%/th dan ≥ campuran 50/50."),
            batang("Return per tahun, dev", [str(t) for t in range(2002, 2015)],
                   [("H23", [-4.1, 51.9, 35.7, 6.7, 6.1, 42.3, 11.5, -1.6, 23.6, -7.5, 18.9, 1.2, 1.4]),
                    ("Beli-tahan JII", [-12.0, 77.5, 38.6, 22.4, 56.6, 59.2, -55.9, 93.9, 28.4, 1.3, 11.3, -1.2, 18.7]),
                    ("Campuran 50/50", [0.2, 46.2, 27.1, 23.7, 34.1, 48.1, -16.1, 44.7, 26.0, 5.3, 13.1, -4.5, 8.9])],
                   "2002 = Jul-Des. H23 melindungi di 2008 tapi tertinggal jauh di 2005, 2006, 2009.")],
    "H20": [batang("CAGR per skenario, dev 2001-2014", ["Dasar", "Kas 0%", "Dividen 4%", "Expense 1,6%", "Terburuk"],
                   [("H20", [20.67, 18.81, 22.03, 21.04, 20.51]), ("Beli-tahan", [21.41, 21.41, 23.16, 21.88, 23.63])], "Batas lulus = beli-tahan − 2%/th. Kas 0%: 18,81% < 19,41%."),
            batang("Max drawdown per skenario", ["Dasar", "Kas 0%", "Dividen 4%", "Expense 1,6%", "Terburuk"],
                   [("H20", [-29.7, -30.3, -29.0, -29.5, -29.4]), ("Beli-tahan", [-66.5, -66.5, -66.2, -66.5, -66.1])], "Drawdown terpotong lebih dari separuh di semua skenario.")],
}

KELUARGA = {
    "H0-H1": {"judul": "Screener ML", "ket": "Tahap 1: model regresi logistik memilih saham yang kena TP sebelum SL. Data harga gratis, 217 saham."},
    "H3-H6": {"judul": "Setup teknikal & kalender", "ket": "Empat pola diuji sekaligus, tahan beberapa hari, tanpa TP/SL. Semua kotor di atas acak, tapi hanya H4 yang menutup biaya di dev."},
    "H7": {"judul": "Aliran dana asing", "ket": "Data asing harian IDX 2020+, dev 2020-2023."},
    "H8-H10": {"judul": "Data IDX + DES historis", "ket": "Universe syariah per tanggal (DES OJK), data IDX 2020-2026: laporan keuangan, negosiasi, antrian penutupan."},
    "H11": {"judul": "Trend following", "ket": "Tahap 3: lama tahan bebas, wajib stop loss. Target return sebesar-besarnya."},
    "H12": {"judul": "H11a tanpa saham liar", "ket": "Ide muncul setelah melihat trade paper; dinilai di dev saja."},
    "H14": {"judul": "H11a + filter fundamental", "ket": "Penilaian di Set A non-syariah (data independen) dan syariah DES 2020+."},
    "H15": {"judul": "Kepemilikan KSEI", "ket": "Data KSEI bulanan sejak Des 2009, jeda publikasi 30 hari."},
    "H16": {"judul": "Valuasi dashboard", "ket": "Apakah vonis panel Valuasi Emiten bisa jadi strategi? Data 2024-2026 kemudian dibuka untuk analisis, jadi holdout tidak lagi bersih."},
    "H17": {"judul": "Pemburu Dividen", "ket": "Portofolio dividen tahunan untuk penghasilan rutin. Uji maju dividen_v1 dihentikan 25 Okt 2026 setelah H17c & H17d gagal."},
    "H21-H22": {"judul": "Faktor bulanan", "ket": "Dua portofolio bulanan dengan kerangka sama (universe, buffer, biaya, pembanding), dinilai terpisah dengan kriteria masing-masing."},
    "H23": {"judul": "Tren lintas aset", "ket": "Pindah antara saham syariah (JII), emas, dan kas mengikuti return 12 bulan. Hasil brainstorming literatur 2026-10-25."},
    "H19": {"judul": "Indikator teknikal klasik", "ket": "Tujuh indikator populer dalam bentuk baku, tanpa penyetelan. Karena diuji sekaligus, ada kriteria ke-8 (bootstrap 98%)."},
}

_CACHE = {}


def _kurva_backtest(versi):
    from backend.db import koneksi as kdb
    rows = list(kdb.koneksi().backtest_ekuitas.find({"versi": versi}, {"_id": 0, "bulan": 1, "ekuitas": 1, "beli_tahan": 1, "ihsg": 1}).sort("bulan", 1))
    return {"label": [r["bulan"] for r in rows],
            "seri": [{"nama": "Follow Tren", "data": [round(r["ekuitas"] * 100, 1) for r in rows]},
                     {"nama": "Beli-tahan bobot sama", "data": [round(r["beli_tahan"] * 100, 1) for r in rows]},
                     {"nama": "IHSG", "data": [round(r["ihsg"] * 100, 1) for r in rows]}]}


def _tahun_backtest(daftar):
    from backend.db import koneksi as kdb
    label, data = [], []
    for v in daftar:
        r = kdb.koneksi().backtest_ringkasan.find_one({"versi": v}, {"per_tahun": 1}) or {}
        for t, x in sorted((r.get("per_tahun") or {}).items()):
            if v.endswith("dev") and t == "2010":
                continue
            label.append(t + ("*" if t == "2026" else ""))
            data.append(round(x, 1))
    return {"label": label, "seri": [{"nama": "Return portofolio", "data": data}]}


def _kurva_hasil(src):
    from backend.db import data as dt
    df = dt.baca_hasil(src["hasil"])
    seri = []
    for nama, kol in src["kolom"]:
        eq, out = 100.0, []
        for v in df[kol]:
            eq *= 1 + (0 if v != v else float(v)) / 100
            out.append(round(eq, 1))
        seri.append({"nama": nama, "data": out})
    return {"label": [str(x) for x in df[src["x"]]], "seri": seri}


def _tahun_hasil(src):
    from backend.db import data as dt
    dfs = [dt.baca_hasil(n) for n in src["hasil_tahun"]]
    label = [str(t) + ("*" if p else "") for t, p in zip(dfs[0]["tahun"], dfs[0]["parsial"])]
    return {"label": label, "seri": [{"nama": n, "data": [round(float(v), 1) for v in dfs[i][kol]]} for n, kol, i in src["kolom"]]}


def _h2122(jenis, tahunan):
    from backend.db import data as dt
    h = (dt.baca_hasil("h2122_dev") or {}).get(jenis)
    if not h:
        return None
    if tahunan:
        rows = h["per_tahun"]
        return {"label": [str(r["tahun"]) for r in rows], "seri": [{"nama": "Strategi", "data": [r["strategi"] for r in rows]}, {"nama": "Bobot sama (tanpa biaya)", "data": [r["bobot_sama"] for r in rows]}, {"nama": "JII + 2,5%", "data": [r["jii"] for r in rows]}]}
    kv = h["kurva"]
    nama = "H21 low vol" if jenis == "h21" else "H22 momentum"
    return {"label": [x[:7] for x in kv["tgl"]], "seri": [{"nama": nama, "data": [round(x * 100, 1) for x in kv["strategi"]]},
            {"nama": "Pembanding bobot sama", "data": [round(x * 100, 1) for x in kv["bobot_sama"]]}, {"nama": "JII + 2,5%", "data": [round(x * 100, 1) if x == x else None for x in kv["jii"]]}]}


def _isi(g):
    src = g.get("sumber")
    if not src:
        return g
    kunci = repr(src) + (str(_cap_backtest()) if any(k.startswith("backtest") for k in src) else "")
    if kunci not in _CACHE:
        try:
            if "backtest" in src:
                _CACHE[kunci] = _kurva_backtest(src["backtest"])
            elif "backtest_tahun" in src:
                _CACHE[kunci] = _tahun_backtest(src["backtest_tahun"])
            elif "hasil" in src:
                _CACHE[kunci] = _kurva_hasil(src)
            elif "h2122" in src:
                _CACHE[kunci] = _h2122(src["h2122"], False)
            elif "h2122_tahun" in src:
                _CACHE[kunci] = _h2122(src["h2122_tahun"], True)
            elif "hasil_tahun" in src:
                _CACHE[kunci] = _tahun_hasil(src)
        except Exception:
            _CACHE[kunci] = None
    isi = _CACHE.get(kunci)
    if not isi:
        return None
    return {k: v for k, v in g.items() if k != "sumber"} | {"satuan": g.get("satuan", "")} | isi


def _cap_backtest():
    from backend.db import koneksi as kdb
    r = kdb.koneksi().backtest_ringkasan.find_one({}, {"dibuat": 1}, sort=[("dibuat", -1)])
    return r["dibuat"].timestamp() if r else 0


def _pct(v, tanda=True):
    return (f"{v:+.1f}%" if tanda else f"{v:.1f}%").replace(".", ",")


def _rentang(a_, b_, tanda=True):
    return f"{_pct(a_, tanda)} s/d {_pct(b_, tanda)}"


def _isi_monte_carlo(angka):
    if not any(x.get("monte_carlo") for x in angka):
        return angka
    kunci = ("monte_carlo", _cap_backtest())
    if kunci not in _CACHE:
        from backend.db import koneksi as kdb
        _CACHE[kunci] = {r["versi"]: r for r in kdb.koneksi().backtest_ringkasan.find({}, {"_id": 0, "versi": 1, "monte_carlo": 1, "cagr_beli_tahan": 1})}
    rk = _CACHE[kunci]
    hasil = []
    for x in angka:
        r = rk.get(x["monte_carlo"]) if x.get("monte_carlo") else None
        u = (r or {}).get("monte_carlo")
        if not u:
            hasil.append(x)
            continue
        tile = [["CAGR p5–p95", _rentang(u["cagr"]["p5"], u["cagr"]["p95"]), f"{u['n']} simulasi"],
                ["Drawdown p5–p95", _rentang(u["dd"]["p5"], u["dd"]["p95"], False), f"{u['n']} simulasi"],
                [f"Contoh 1 simulasi (seed {u['contoh_seed']})", _pct(u["contoh"]["cagr"]), f"DD {_pct(u['contoh']['dd'], False)} · kurva di grafik"]]
        ekstra = []
        k = rk.get(x["monte_carlo"] + "_konservatif", {}).get("monte_carlo")
        if k:
            ekstra.append(["Konservatif (ARA/ARB terkunci)", f"CAGR median {_pct(k['cagr']['median'])} ({_rentang(k['cagr']['p5'], k['cagr']['p95'])}), "
                                                              f"DD median {_pct(k['dd']['median'], False)} ({_rentang(k['dd']['p5'], k['dd']['p95'], False)})"])
        hasil.append(x | {"cagr": u["cagr"]["median"], "dd": u["dd"]["median"], "cagr_rentang": [u["cagr"]["p5"], u["cagr"]["p95"]],
                          "dd_rentang": [u["dd"]["p5"], u["dd"]["p95"]], "tile": tile, "ekstra": x["ekstra"] + ekstra,
                          "bh": r.get("cagr_beli_tahan"), "bh_nama": "Beli-tahan bobot sama (bulanan, cara paper)", "dd_label": "Max drawdown (median)"})
    return hasil


def _eksplorasi():
    from backend.db import data as dt
    kunci = ("eksplorasi", dt.versi_hasil("eksplorasi_2020_ringkas"))
    if kunci not in _CACHE:
        try:
            _CACHE[kunci] = dt.baca_hasil("eksplorasi_2020_ringkas")
        except Exception:
            _CACHE[kunci] = None
    return _CACHE[kunci]


def semua():
    eks = _eksplorasi() or {}
    per_kode = eks.get("hasil") or {}
    hip = [h | {"angka": _isi_monte_carlo(h.get("angka") or []), "grafik": [x for x in (_isi(g) for g in GRAFIK.get(h["kode"], [])) if x],
                "eksplorasi": per_kode.get(h["kode"])} for h in HIPOTESIS]
    info = {k: v for k, v in eks.items() if k != "hasil"} if eks else None
    return {"status": STATUS, "kategori": KATEGORI, "lencana": LENCANA, "pelajaran": PELAJARAN,
            "analisis": ANALISIS, "keluarga": KELUARGA, "hipotesis": hip, "eksplorasi": info}
