# Lab Investasi Syariah

Aplikasi pribadi untuk meriset dan menguji strategi investasi **syariah** di pasar Indonesia: saham syariah IDX, reksa dana & sukuk syariah, dan ETF. Semua ide strategi diperlakukan sebagai hipotesis yang ditulis dulu, diuji dengan biaya transaksi realistis, lalu dicatat apa adanya, termasuk yang gagal.

> Proyek riset dan uji coba, belum memakai uang asli. **Bukan nasihat keuangan.**

## Tujuan

Mencari cara mendapat penghasilan rutin dari investasi syariah, dengan target berlapis:

| Lapisan | Isi | Patokan |
|---|---|---|
| Likuiditas | Sukuk negara + reksa dana pasar uang syariah (tempat parkir kas) | Imbal hasil bersih ≥ inflasi + 1,5%/th, penurunan maks -10% |
| Pendapatan | Saham dividen syariah | Kosong: strategi dividen gagal diuji |
| Apresiasi modal | Strategi saham yang lulus uji (Follow Tren) | Total return > beli-tahan JII, penurunan sampai -40% |

Fokus riset: saham syariah IDX. Paper trade Follow Tren dinilai 12 bulan (keputusan manual Okt 2027, porsi awal maks 10%, bukan bukti edge) sebelum uang nyata, dimulai kecil dan bertahap.

## Fase saat ini: eksekusi dan menunggu

Tidak ada hipotesis baru di data 2010-2026 sampai evaluasi Okt/Nov 2027, kecuali memakai data baru dan kriteria ditulis sebelum melihat data. Yang berjalan: paper H11a dan H29, dan uji maju H35 dan H37 (mulai 1 Des 2026).

Hanya instrumen syariah. Saham disaring dengan Daftar Efek Syariah (DES) OJK yang berlaku **pada tanggal itu**, bukan daftar hari ini.

## Status strategi

| Strategi | Status | Ringkasan |
|---|---|---|
| **Follow Tren** (H11a) | Paper trade sejak 21 Okt 2026, modal Rp100 jt | Beli saham syariah likuid yang menembus harga tertinggi 250 hari, maks 10 posisi @10%, stop 3×ATR14. Backtest 2020-2026 (median 100 simulasi Monte Carlo, sesudah koreksi data harga 2 Nov 2026): CAGR +20,9%, penurunan maks -41,9%. Audit 2026-11-01: gagal standar seragam di dev, kapasitas kecil (universe Rp20 M ±separuh). Belum terbukti di uang nyata. |
| **Momentum Blend** (H29) | Paper trade sejak 1 Nov 2026, modal Rp100 jt | Breakout 52W + RS 12-1: 50% Follow Tren + 50% RS 12-1 (momentum 12-1, H22), dikembalikan ke 50/50 tiap akhir bulan. Ditemukan setelah melihat data, jadi angka historisnya bukan bukti; evaluasi 1 Nov 2027. |
| **Syariah Global** (H35) | Lolos pasca hasil (K1-K4 4/4); **uji maju mulai 1 Des 2026**, modal paper Rp100 jt | 50% JII + 50% saham syariah global, rupiah, rebalance Desember. Indeks Jun 2001-Okt 2026: CAGR +9,5%, DD -42,6%, jendela 10 th terburuk +2,8% (100% IDX: +8,3%, -61,4%, -7,2%). Arah umum data sudah diketahui sebelum uji (kontaminasi tercatat). |
| **Syariah Global + Emas** (H37) | Lolos dev dan holdout (pasca hasil); **uji maju mulai 1 Des 2026**, aturan dikunci 12 Nov 2026, evaluasi pertama Jan 2028 | 40% JII / 40% global syariah / 20% emas (ETF emas syariah), rebalance Desember. Dev 2001-2013: CAGR 14,6%, DD -34,2% (H35 14,1%, -42,6%). Holdout 2014-Okt 2026: 6,7%, -13,4% (H35 5,1%, -19,0%); margin DD holdout 5,6 poin (batas 5) dan sebagian besar keunggulan dari emas 2024-2025. Sensitivitas: bobot 45/45/10 gagal K1 (2/3) di dev dan holdout, 35/35/30 juga gagal K1 di holdout; spread emas 1% dan 6% lolos 3/3. Uji maju menilai pelaksanaan produk nyata, bukan bukti edge. |
| PEAD / kejutan laba (H36) | Gagal di holdout | Dev 2020-2023 lulus (CAGR 17,1%) hanya karena strategi berada di kas saat jatuhnya pasar 2020 dan satu trade BYAN. Holdout 2024-2026: CAGR 3,0% vs bobot sama 7,8%; excess per event -0,76%; tanpa saham batu bara 1,4% vs 5,3%. |
| Pemburu Dividen (H17) | Gagal | 10 yield tertinggi yang rutin bayar 3 tahun: penghasilan tinggi hanya saat boom batu bara. Uji maju 2027 dihentikan 25 Okt 2026 (keputusan user). |
| Swing pendek, indikator klasik, fundamental/valuasi, aliran dana asing/KSEI | Gagal | Biaya ±1,2% pulang-pergi memakan keuntungan kecil. |
| Filter rezim JII, low volatility, momentum bulanan, dual momentum JII/emas/kas | Gagal | Lihat halaman Hipotesis. |
| Screener swing "bottom reversal" di saham bertren naik (H27) | Gagal di dev 2010-2019 | Sebelum biaya pun hasilnya nol, kalah dari beli saham acak. |
| Gap up yang celahnya belum ditutup (H28) | Gagal di dev 2010-2019 | Jarang terjadi (29 kali dalam 10 tahun) dan setelahnya harga rata-rata turun. |
| Ikut pembelian saham oleh direksi/komisaris (H25) | Gagal di dev 2023-2024 | Rata-rata terlihat bagus, tapi separuh lebih trade kalah dari pasar; hasil ditarik beberapa saham yang melonjak di 2024. |
| Faktor kualitas ala Buffett (ROE, utang, harga wajar), seri K | Gagal di dev 2011-2019 | Semua varian kalah dari memegang semua saham syariah likuid secara rata. Kolam saham syariah likuid terlalu kecil (28-62 saham) untuk membedakan keunggulan faktor dari kebetulan. Lihat [docs/RISET_KUALITAS.md](docs/RISET_KUALITAS.md). |

Katalog lengkap **53 hipotesis** (per sub-ID, = 37 ID induk H0-H37 tanpa H24; status: Gagal 42, Tidak diadopsi 6, Paper 2, Uji maju 2, Belum dikunci 1) ada di [docs/KATALOG_HIPOTESIS.md](docs/KATALOG_HIPOTESIS.md), dengan aturan hitungnya. Kriteria, hasil, dan grafik ada di menu **Hipotesis** dan di [docs/RENCANA_SCREENER.md](docs/RENCANA_SCREENER.md).

## Cara riset

- Hipotesis dan kriteria lulus ditulis **sebelum** uji dijalankan; tidak ada varian baru setelah melihat hasil.
- Data dibagi **dev** (untuk menguji) dan **holdout** (dibuka sekali, hanya kalau dev lulus).
- Biaya transaksi model ±1,2% pulang-pergi (fee beli 0,15% + jual 0,25% + selisih 1 tick per sisi).
- Hasil backtest Follow Tren dilaporkan sebagai median dan rentang p5-p95 dari 100 simulasi Monte Carlo, karena pemilihan saham saat sinyal melebihi slot dilakukan acak.
- Uji yang dibuat setelah melihat data diberi lencana "dibuat setelah lihat hasil" dan tidak dihitung sebagai bukti.
- Saat beberapa varian diuji sekaligus, pemenang harus mengalahkan persentil 95 dari "terbaik di antara portofolio acak" dengan jumlah varian yang sama (uji anti-kebetulan).

## Menu aplikasi

- **Beranda**: pasar hari ini (IHSG, perputaran uang, naik/turun, sektor, pasar dunia, jadwal dividen), ringkasan strategi, produk, perawatan, dan sumber data.
- **Follow Tren**: paper trade + pantauan harga, backtest, aturan, riset.
- **Hipotesis**: katalog semua uji, pelajaran, dan eksplorasi 2020+ (bukan bukti).
- **Emiten**: profil, harga, valuasi, dividen, fundamental, kepemilikan KSEI, transaksi orang dalam, berita, pengumuman.
- **Dividen**: informasi dividen saham syariah (jadwal resmi IDX, daftar & kalender, kalkulator penghasilan, dividend trap), plus ringkasan hasil uji strategi dividen H17 yang gagal.
- **Reksa Dana & Sukuk** (dibuat untuk pemula):
  - *Mulai di sini*: pilih kapan uangnya dipakai (< 1 th / 1–3 th / 5 th+) dan profil risiko (rendah/sedang/tinggi), lalu dapat racikan sukuk negara, reksa dana pasar uang, pendapatan tetap, saham Indonesia, dan saham global (dalam rupiah), beserta perkiraan hasil dari data masa lalu.
  - *Reksa Dana*: katalog dengan **lencana** (Konsisten, Kalahkan inflasi, Tahan banting, Biaya murah) dan peringatan otomatis (data pendek, NAV terlalu mulus, satu efek > 15%, dana kelolaan naik/turun tajam). Skor 0–100 tidak dipakai lagi.
  - *Tersedia di*: logo Bibit, Ajaib, dan Makmur yang menautkan ke halaman produknya (diambil dari halaman/sitemap publik), plus daftar 93 aplikasi jual-beli reksa dana berizin OJK.
  - Detail produk: ringkasan 30 detik, NAV/AUM, isi portofolio, "Seberapa bisa dipercaya" (hasil per tahun vs median sejenis/patokan/inflasi, posisi sekarang dari puncak, kenapa turun di tahun tertentu, berapa lama sebaiknya ditahan), dan kesimpulan.
  - *Sukuk & SBN*, *Bandingkan* (2–5 produk, termasuk deposito/JII/emas), *Cara kerja & istilah* (panduan pemula).
- **ETF**: ETF syariah Indonesia (detail produk + harga bursa) dan ETF luar negeri (yang bukan syariah diberi label), dengan panel "Seberapa bisa dipercaya" yang sama.
- **Kualitas data**: status cek harian harga Yahoo terhadap data resmi IDX, koreksi per kategori (salah skala, aksi korporasi, bar basi, lompatan), cakupan yang terverifikasi, dan masalah yang masih terbuka. Semua koreksi tercatat dengan nilai asli, alasan, dan bukti.
- **Rencana** dan **Panduan**.

Semua aksi (memperbarui data, menjalankan job, backup) dijalankan lewat tombol di dashboard.

## Menjalankan

Prasyarat (Windows): Python 3.12, Node.js, MongoDB (service lokal), Google Chrome.

```powershell
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
cd frontend; npm install; npm run build; cd ..
```

Lalu dobel klik `jalankan.bat`: mengecek venv & MongoDB, membangun tampilan bila perlu, menjalankan server di `http://127.0.0.1:8765`, dan membuka browser.

Pengembangan:

- Backend: `venv\Scripts\python -m uvicorn backend.app.main:app --reload --port 8765`
- Frontend: `cd frontend; npm run dev` (port 5173, API diteruskan ke 8765)
- Modul Python selalu dijalankan dari root sebagai modul, misalnya `python -m backend.paper.tren_harian`.
- Tes Python (unittest, tanpa pytest): `venv\Scripts\python -m unittest discover -s tests -t .`; satu modul: `venv\Scripts\python -m unittest tests.test_mesin_pertumbuhan`. Tes frontend: `cd frontend; npm test`.

Jadwal otomatis (Task Scheduler, Senin-Jumat 17:30) dipasang lewat tombol di panel Perawatan.

## Data

Semua data disimpan di MongoDB lokal, tidak ada file data di folder proyek:

- `swing`: state aplikasi (paper trade, backtest, DES, fundamental, reksa dana, dll.).
- `lab_data`: data pasar (harga harian saham sejak 2010, indeks, kurs, emas, data resmi IDX, KSEI, pengumuman, makro BI/FRED), dan data keuangan & rasio emiten bulanan sejak 2010 (`keuangan_idx`: aset, liabilitas, ekuitas, penjualan, laba, rasio, status syariah pada bulan itu).

Data keuangan 2010-2020 dibaca dari tabel "Financial Data & Ratios" di PDF IDX Monthly Statistics (arsip Wayback Machine dan situs IDX; hanya angka hasil bacaan yang disimpan), 2021+ dari statistik digital IDX. Hasil bacaan PDF dicocokkan dengan API IDX: 97,5% angka sama.

Sumber: Yahoo Finance (harga, hanya bar harian yang sudah final), IDX, OJK (termasuk NAB bulanan reksa dana sejak 2013 dan daftar aplikasi berizin), KSEI, Bank Indonesia, FRED, Pasardana, serta katalog publik Bibit, Ajaib, dan Makmur (hanya halaman/sitemap publik, tanpa login). Data IDX/OJK yang dilindungi Cloudflare diambil lewat Chrome biasa dengan profil terpisah ("Chrome Lab"); pemeriksaan Cloudflare tetap dilewati manual.

## Struktur

```
backend/
  app/        FastAPI: routers, services (logika per menu), jobs (job latar belakang & jadwal)
  paper/      paper trade Follow Tren, cek ulang + cek silang data resmi IDX
  ingest/     pengumpul & impor data (Yahoo, IDX, OJK, KSEI, BI, reksa dana, ETF, logo)
  research/   semua uji hipotesis dan analisis
  db/         akses MongoDB, backtest + simulasi Monte Carlo, cadangan
browser/      script pengambilan data IDX/OJK yang dijalankan di browser
frontend/     Vue 3 + Vite + Tailwind 4 + Chart.js
docs/         rencana & hasil semua uji, catatan teknis lengkap
```
