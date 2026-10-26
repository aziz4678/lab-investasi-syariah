# Riset Kualitas (seri K) — jalur terpisah dari H0-H23

Dikunci 2026-10-25, sebelum kode uji dibuat dan sebelum melihat hasil apa pun. Atas permintaan user: pendekatan baru, terpisah dari tesis sebelumnya, "cari yang terbaik" di antara beberapa definisi kualitas, dengan perlindungan terhadap kemenangan karena kebetulan. Belum dimasukkan ke katalog Hipotesis sampai hasil final.

Latar: literatur (Asness-Frazzini-Pedersen "Quality Minus Junk"; Frazzini-Kabiller-Pedersen "Buffett's Alpha") menunjukkan saham berkualitas (laba tinggi, aman, tidak mahal) memberi return di atas pasar di banyak negara, lebih kuat di negara berkembang. Faktor kualitas belum pernah diuji di proyek ini (H14 = filter laba tumbuh untuk Follow Tren, H16 = valuasi murah, H17 = dividen).

## Pendekatan: seleksi di dev, konfirmasi di holdout

1. Tiga varian (K1-K3) dijalankan di dev. Dipilih SATU pemenang dengan ukuran yang ditetapkan di sini.
2. Pemenang harus lolos uji anti-kebetulan yang memperhitungkan bahwa ia dipilih dari tiga.
3. Holdout dibuka SEKALI, hanya untuk pemenang. Dua varian lain tidak pernah dijalankan di holdout.
4. Tanpa varian tambahan setelah melihat hasil: tidak ada perubahan definisi skor, ukuran portofolio, jadwal, filter, atau periode.

## Data

- Fundamental: `lab_data.keuangan_idx` (tabel "Financial Data & Ratios" IDX bulanan 2010-2018 dari PDF Wayback, 2020 dari PDF IDX, 2021+ dari API IDX). Baris `curiga` dibuang.
- Potret untuk tanggal sinyal t: per kode, baris dengan `terbit` ≤ t yang paling baru; dipakai hanya kalau `fs_date` ≥ t − 15 bulan.
- Status syariah: tanda [S] IDX pada baris potret yang dipakai (point-in-time). Tidak memakai DES hari ini.
- Harga: koleksi `harga` (Yahoo), kerangka harga sama dengan H21/H22 (`uji_h21_h22.susun`), universe kode = DES-ever ∪ semua kode yang pernah bertanda syariah di `keuangan_idx`.

## Metrik (dihitung ulang dari angka mentah, bukan rasio tabel)

- Bulan cakupan laba tahun berjalan m = ((bulan fs_date − bulan akhir tahun buku − 1) mod 12) + 1; akhir tahun buku dari kolom `fye` (kosong = Desember).
- Laba setahun = laba milik pemilik (`profit_owner`; tahun 2010-2011 = laba bersih) × 12 / m.
- ROE = laba setahun / ekuitas; ROA = laba setahun / aset; NPM = laba tahun berjalan / penjualan tahun berjalan; DER = liabilitas / ekuitas; PBV = close mentah di t / nilai buku per saham (`bv`).
- Syarat data semua varian: ekuitas > 0. NPM hanya kalau penjualan > 0; PBV hanya kalau `bv` > 0.

## Universe (di tanggal sinyal t)

Bertanda syariah pada potret, punya potret valid, dan lolos filter likuiditas H21/H22: median nilai transaksi (close mentah × volume) 60 hari ≥ Rp5 M, close mentah ≥ Rp100, ≥ 250 hari data, volume > 0 di ≥ 90% dari 250 hari terakhir. Saham yang nilai metrik wajib variannya kosong tidak ikut di varian itu.

## Tiga varian (skor = rata-rata peringkat persentil di antara saham yang lolos)

| Kode | Skor | Syarat tambahan |
|---|---|---|
| K1 kualitas + harga wajar | ROE (tinggi baik), DER (rendah baik), PBV (rendah baik) | ROE, DER, PBV tersedia |
| K2 kualitas murni | ROE, ROA, NPM (tinggi baik), DER (rendah baik) | keempatnya tersedia |
| K3 ROE saja | ROE (tinggi baik) | DER ≤ 2 |

## Portofolio (sama untuk ketiganya, mekanisme H21/H22)

- Sinyal di close hari bursa terakhir Juni tiap tahun; eksekusi open hari bursa pertama Juli. Saham yang tidak bisa ditransaksikan hari itu ditunda (aturan H21/H22).
- N = maks(10, bulat(20% × jumlah saham lolos varian itu)). Beli peringkat ≤ N; pegang selama peringkat ≤ 2N; slot kosong diisi peringkat teratas; bobot saham baru 1/N ekuitas; pangkas kalau > 2/N. Sisa kas tidak berbunga.
- Kalau di tanggal sinyal jumlah saham lolos < 10 (data basi), tidak ada rebalance tahun itu; portofolio dipegang.
- Biaya: fee beli 0,15% + jual 0,25% + 1 tick per sisi (harga mentah), untuk setiap transaksi.
- Saham hilang/mati: perlakuan sama dengan H21/H22.

## Pembanding

- B1: bobot sama semua saham di universe (syariah + potret valid + likuid), jadwal sama, tanpa biaya.
- B2: JII (close) + dividen 2,5%/th, tanpa biaya.

## Periode

- Dev: sinyal Jun 2011, Jun 2012, ..., Jun 2019; portofolio Jul 2011 s/d 31 Des 2019.
- Holdout: sinyal Jun 2020, ..., Jun 2026; portofolio baru mulai Jul 2020 s/d close 23 Okt 2026 (dipatok). Mulai Jul 2020 karena potret terakhir sebelum Jan 2020 (laporan Jun 2018) sudah lebih dari 15 bulan; Mar 2020 tidak termasuk.

## Tahap 1: seleksi di dev

- Ukuran seleksi: selisih CAGR varian − CAGR B1 (dev). Pemenang = selisih terbesar.
- Pemenang LULUS dev kalau semua terpenuhi:
  1. CAGR pemenang > CAGR B1 dan > CAGR B2.
  2. Max drawdown harian pemenang tidak lebih dalam dari max drawdown B1.
  3. Uji anti-kebetulan: 1.000 ulangan; tiap ulangan membuat 3 portofolio acak (peringkat = urutan acak di tiap tanggal sinyal, mekanisme/biaya/universe sama dengan varian, N mengikuti K1, K2, K3 masing-masing); ambil selisih CAGR − B1 terbesar dari ketiganya. Selisih pemenang harus > persentil 95 distribusi "acak terbaik". Seed 20261025.
- Kalau syarat tidak terpenuhi: seri K GAGAL di dev, holdout tidak dibuka, tanpa varian.

## Tahap 2: konfirmasi di holdout (hanya pemenang, sekali)

LULUS kalau: CAGR pemenang > CAGR B1, dan max drawdown pemenang ≥ max drawdown B1 − 5 poin.
Lulus = kandidat paper trade baru (lapisan apresiasi modal), aturan dikunci ulang sebelum paper; bukan langsung uang asli.

## Laporan saja (bukan syarat)

Hasil ketiga varian di dev (CAGR, DD, per tahun, jumlah saham, turnover); pemenang dengan biaya 2 tick; pemenang tanpa 3 saham penyumbang terbesar; korelasi return bulanan dengan Follow Tren (`backtest_ekuitas` h11a_dev / h11a_2020).

## Kelemahan (dicatat sebelum uji)

- Data bolong: 2016 hanya potret Jan (laporan Sep 2015), 2017 tidak ada potret segar sebelum Juli → portofolio Jul 2016 dipegang sampai Jul 2018 (sinyal Jun 2017 kemungkinan < 10 saham lolos).
- Survivorship: data harga Yahoo hanya saham yang masih ada.
- Laba setahun dari laba kuartalan dikali (musiman diabaikan). Nilai buku per saham dari tabel IDX (bisa beda tanggal dengan harga).
- Tahun 2010-2011 memakai laba bersih (belum ada pemisahan laba milik pemilik).
- Holdout 2020+ sudah dilihat untuk strategi lain (tapi tidak untuk faktor kualitas). Uji ke ±41-43; uji anti-kebetulan hanya mengoreksi pemilihan dari 3 varian, bukan seluruh 40+ uji sebelumnya.

## Hasil dev Jul 2011 - Des 2019 (2026-10-25, dijalankan sekali, `backend/research/uji_kualitas.py dev`): GAGAL, holdout tidak dibuka

Cek data sebelum hasil (tanpa return): universe syariah + likuid + data valid 28-62 saham per tahun; umur laporan median 3-12 bulan; Jun 2017 tanpa potret (portofolio dipegang), sesuai spesifikasi.

| Varian | CAGR | Max DD | Selisih vs B1 | Posisi rata-rata | Turnover/th |
|---|---|---|---|---|---|
| K1 kualitas + harga wajar | 4,57% | -37,7% | -2,82 | 10,6 | 59% |
| K2 kualitas murni | 4,13% | -36,1% | -3,27 | 10,6 | 52% |
| **K3 ROE saja (pemenang)** | 6,43% | -33,5% | -0,96 | 10,2 | 56% |
| B1 bobot sama (tanpa biaya) | 7,39% | -34,9% | — | | |
| B2 JII + 2,5% | 5,62% | | | | |

Kriteria pemenang K3: (1) CAGR > B1 dan > JII: GAGAL (6,43% < 7,39%); (2) DD tidak lebih dalam dari B1: lulus (-33,5% vs -34,9%); (3) anti-kebetulan: GAGAL (selisih -0,96 vs p95 "acak terbaik dari 3" = +8,06; hanya mengalahkan 25,9% ulangan).

Laporan saja (K3): biaya 2 tick CAGR 6,16%; tanpa 3 penyumbang terbesar (CPIN, TLKM, SCMA) CAGR 3,34%; korelasi bulanan dengan Follow Tren 0,46 (102 bulan).

Per tahun (%): K1 1,4 / 22,1 / -1,8 / 31,8 / -23,8 / 9,0 / 1,7 / -3,4 / 11,9; K2 3,5 / 26,8 / -4,7 / 22,9 / -24,0 / 28,2 / 13,6 / -11,3 / -6,5; K3 4,2 / 24,8 / -9,8 / 40,8 / -14,0 / 9,1 / 5,2 / 11,7 / -6,8; B1 6,6 / 26,2 / 3,2 / 32,8 / -21,9 / 22,3 / 4,5 / -6,5 / 6,6 (2011 = Jul-Des).

Catatan:
- Tidak ada varian yang mengalahkan memegang semua saham syariah likuid secara rata. Faktor kualitas tidak terlihat memberi keunggulan di universe syariah likuid IDX 2011-2019.
- Sebaran portofolio acak sangat lebar: "acak terbaik dari 3" di persentil 95 unggul +8 poin/th atas B1. Dengan universe hanya 28-62 saham dan ±10 posisi, keunggulan faktor yang wajar (2-3 poin/th seperti di literatur) hampir mustahil dibedakan dari kebetulan dalam 8,5 tahun. Ini pelajaran penting untuk uji faktor berikutnya di IDX.
- Sesuai aturan: GAGAL = ditutup, tanpa varian skor, ukuran, jadwal, atau periode. Holdout 2020+ tidak dibuka.
