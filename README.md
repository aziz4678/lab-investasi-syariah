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

Fokus riset: saham syariah IDX. Paper trade Follow Tren dinilai 12 bulan (keputusan utama Okt 2027) sebelum uang nyata, dimulai kecil dan bertahap.

Hanya instrumen syariah. Saham disaring dengan Daftar Efek Syariah (DES) OJK yang berlaku **pada tanggal itu**, bukan daftar hari ini.

## Status strategi

| Strategi | Status | Ringkasan |
|---|---|---|
| **Follow Tren** (H11a) | Paper trade sejak 21 Okt 2026, modal Rp100 jt | Beli saham syariah likuid yang menembus harga tertinggi 250 hari, maks 10 posisi @10%, stop 3×ATR14. Backtest 2020-2026 (median 100 simulasi Monte Carlo): CAGR +23,6%, penurunan maks -37,5%. Belum terbukti di uang nyata. |
| Pemburu Dividen (H17) | Gagal | 10 yield tertinggi yang rutin bayar 3 tahun: penghasilan tinggi hanya saat boom batu bara. Uji maju 2027 dihentikan. |
| Swing pendek, indikator klasik, fundamental/valuasi, aliran dana asing/KSEI | Gagal | Biaya ±1,2% pulang-pergi memakan keuntungan kecil. |
| Filter rezim JII, low volatility, momentum bulanan, dual momentum JII/emas/kas | Gagal | Lihat halaman Hipotesis. |
| Ikut pembelian saham oleh direksi/komisaris (H25) | Gagal di dev 2023-2024 | Rata-rata terlihat bagus, tapi separuh lebih trade kalah dari pasar; hasil ditarik beberapa saham yang melonjak di 2024. |
| Faktor kualitas ala Buffett (ROE, utang, harga wajar), seri K | Gagal di dev 2011-2019 | Semua varian kalah dari memegang semua saham syariah likuid secara rata. Kolam saham syariah likuid terlalu kecil (28-62 saham) untuk membedakan keunggulan faktor dari kebetulan. Lihat [docs/RISET_KUALITAS.md](docs/RISET_KUALITAS.md). |

Katalog lengkap 41 hipotesis (H0-H25) beserta kriteria, hasil, dan grafiknya ada di menu **Hipotesis** dan di [docs/RENCANA_SCREENER.md](docs/RENCANA_SCREENER.md).

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
