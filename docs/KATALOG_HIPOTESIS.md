# Katalog hipotesis (sumber utama)

Sumber kebenaran daftar hipotesis. CLAUDE.md dan README hanya meringkas dan menautkan ke sini. Isi baris di bawah dibangkitkan dari `HIPOTESIS` di `backend/app/services/hipotesis.py` (yang juga membentuk menu Hipotesis); kriteria, tabel, dan penjelasan lengkap tiap hipotesis ada di [RENCANA_SCREENER.md](RENCANA_SCREENER.md) dan di menu Hipotesis. Kalau hipotesis ditambah atau status berubah, ubah `hipotesis.py` lebih dulu lalu perbarui tabel ini.

## Aturan hitung

- **Satuan hitung = entri katalog (sub-ID)**, sama dengan menu Hipotesis: H7a dan H7b dihitung dua, H19a-g tujuh, dan seterusnya. Angka resmi di semua dokumen = **53 hipotesis**.
- **Satuan alternatif = ID induk** (H7a/H7b = H7): **37 ID**, yaitu H0-H37 tanpa H24 (H24 Ramadan sengaja dihapus atas permintaan user 2026-10-28, tidak diuji ulang).
- Selisih 53 - 37 = 16 sub-ID tambahan: H7 +1, H11 +1, H12 +1, H14 +1, H15 +1, H16 +2, H17 +3, H19 +6.
- **H31** (H20 dengan kas RD pasar uang) berkeluarga H20 tetapi punya ID sendiri, dihitung satu.
- **Seri K (K1-K3, kualitas)** jalur terpisah atas permintaan user, **tidak dihitung** (lihat [RISET_KUALITAS.md](RISET_KUALITAS.md), semua gagal di dev).
- Eksplorasi 2020+ dan analisis pendukung bukan hipotesis dan tidak dihitung.

## Ringkasan status (53 entri)

| Status | Jumlah |
|---|---|
| Gagal | 42 |
| Tidak diadopsi | 6 |
| Paper trade | 2 |
| Uji maju | 2 |
| Belum dikunci | 1 |
| **Total** | **53** |

Catatan: H35 dan H37 berstatus Uji maju (mulai 1 Des 2026) sekaligus lolos pasca hasil (arah umum data sudah diketahui sebelum uji). H29 Paper sejak 1 Nov 2026, H11a Paper sejak 21 Okt 2026.

## Daftar

| Kode | Nama | Kategori | Status | Skor / hasil | Diuji |
|---|---|---|---|---|---|
| H0 | Screener TP +3% / SL -3% | screener | Gagal | 1/7 | 2026-10-20 |
| H1 | Screener TP +8% / SL -4% | screener | Gagal | 0/7 | 2026-10-20 |
| H2 | Naik menjelang cum date dividen | kalender | Gagal | 1/6 | 2026-10-20 |
| H3 | Pullback dalam tren naik | swing | Gagal | 1/6 | 2026-10-20 |
| H4 | Breakout konsolidasi + volume | swing | Gagal (holdout_pengecualian) | dev 4/6 · 2024+ 0/6 | 2026-10-20 |
| H5 | Efek pergantian bulan | kalender | Gagal | 1/6 | 2026-10-20 |
| H6 | Menjelang libur Lebaran | kalender | Gagal | 1/6 | 2026-10-20 |
| H7a | Akumulasi asing 5 hari | aliran | Gagal | 1/6 | 2026-10-20 |
| H7b | Breakout H4 + asing masuk | aliran | Gagal | 4/6 + 1 | 2026-10-20 |
| H8 | Reaksi laporan keuangan | kalender | Gagal | 2/6 | 2026-10-21 |
| H9 | Blok negosiasi berpremi | aliran | Gagal | 0/6 | 2026-10-20 |
| H10 | Antrian beli dominan saat tutup | aliran | Gagal | 1/6 | 2026-10-20 |
| H11a | Follow Tren (tertinggi 52 minggu) | tren | Paper trade (dev_gagal, holdout_pengecualian) | dev 6/7 · holdout 7/7 | 2026-10-21 |
| H11b | Momentum 6 bulan + EMA200 | tren | Gagal | 4/7 | 2026-10-21 |
| H12a | H11a tanpa saham volatil (ATR ≤ 3,5%) | tren | Gagal (pasca_hasil) | — | 2026-10-21 |
| H12b | H12a + harga ≥ Rp200 | tren | Gagal (pasca_hasil) | — | 2026-10-21 |
| H13 | Perbaikan portofolio H11a (S/R/P) | tren | Tidak diadopsi | 0/4 konfigurasi | 2026-10-21 |
| H14a | H11a + laba tumbuh | fundamental | Tidak diadopsi | tidak diadopsi | 2026-10-22 |
| H14b | H14a + pendapatan tumbuh | fundamental | Tidak diadopsi | tidak diadopsi | 2026-10-22 |
| H15a | Saham yang dikumpulkan institusi (KSEI) | aliran | Gagal | 1/5 | 2026-10-22 |
| H15b | H11a saat ritel tidak bertambah | aliran | Tidak diadopsi | tidak diadopsi | 2026-10-22 |
| H16a | Beli saham Undervalue | fundamental | Gagal | 2/5 | 2026-10-22 |
| H16b | Beli saham 'Layak dipertimbangkan' | fundamental | Gagal | 1/5 | 2026-10-22 |
| H16c | Undervalue yang bukan 'Hindari' | fundamental | Gagal (pasca_hasil) | 3/6 | 2026-10-22 |
| H17a | Pemburu Dividen: 10 yield tertinggi konsisten | dividen | Gagal | dev 2/4 | 2026-10-23 |
| H17b | Pemburu Dividen + saringan anti-trap | dividen | Tidak diadopsi | tidak diadopsi | 2026-10-23 |
| H17c | Uji silang dividen_v1 di saham non-syariah | dividen | Gagal | 1/4 | 2026-10-25 |
| H17d | dividen_v1 di saham syariah 2014-2026 | dividen | Gagal (pasca_hasil) | 2/4 | 2026-10-25 |
| H18 | Persistensi reksa dana syariah | reksadana | Belum dikunci | — | - |
| H19a | Golden cross MA50/MA200 | indikator | Gagal | 0/8 | 2026-10-24 |
| H19b | MACD cross di atas nol + MA200 | indikator | Gagal | 0/8 | 2026-10-24 |
| H19c | Stochastic dari < 20 + MA200 | indikator | Gagal | 0/8 | 2026-10-24 |
| H19d | RSI(2) < 10 + MA200 (Connors) | indikator | Gagal | 1/8 | 2026-10-24 |
| H19e | Bollinger squeeze breakout | indikator | Gagal | 2/8 | 2026-10-24 |
| H19f | Engulfing/hammer di low 20 hari | indikator | Gagal | 1/8 | 2026-10-24 |
| H19g | BSJP (beli sore jual pagi) | indikator | Gagal | 1/8 | 2026-10-24 |
| H20 | Filter rezim JII (rata-rata 10 bulan) | rezim | Gagal | 4/4 dasar · sensitivitas gagal | 2026-10-24 |
| H21 | Low volatility bulanan | faktor | Gagal | 6/6 · sensitivitas 2/4 | 2026-10-24 |
| H22 | Momentum 12-1 bulanan | tren | Gagal | 6/6 · sensitivitas 2/3 | 2026-10-24 |
| H23 | Dual momentum JII / emas / kas | rezim | Gagal (pasca_hasil) | 2/5 dasar · sensitivitas gagal | 2026-10-25 |
| H25 | Pembelian saham oleh orang dalam | aliran | Gagal | 5/8 | 2026-10-29 |
| H26 | Follow Tren, batas jual dirapatkan setelah untung +30% | tren | Tidak diadopsi (pasca_hasil) | 1/5 | 2026-11-01 |
| H27 | Bottom reversal di tren naik | swing | Gagal | 0/9 | 2026-11-01 |
| H28 | Gap up yang belum ditutup | swing | Gagal | 0/9 | 2026-11-01 |
| H29 | Momentum Blend | tren | Paper trade (pasca_hasil) | paper sejak 1 Nov 2026 | - |
| H30 | Residual Momentum | tren | Gagal | dasar 3/5 · sensitivitas 0/3 | 2026-11-01 |
| H31 | Filter rezim JII, kas = RD pasar uang syariah | rezim | Gagal (pasca_hasil) | dasar 2/5 · sensitivitas 0/5 | 2026-11-07 |
| H32 | Frog-in-the-Pan (FIP) momentum | tren | Gagal | dasar 5/5 · sensitivitas 2/3 | 2026-11-07 |
| H33 | Replikasi Follow Tren di Malaysia & US | tren | Gagal | Malaysia dasar 6/6 · S1 0/6 · S2 2/6 · S3 6/6 | 2026-11-07 |
| H34 | Warren Buffett: cicil saham berkualitas + tambah saat turun | fundamental | Gagal | dasar 0/5 · S1 0/5 · S2 1/5 · S3 0/5 · khusus 1/3 | 2026-11-08 |
| H35 | Syariah Global: campuran IDX + global untuk lapisan Apresiasi | rezim | Uji maju (pasca_hasil) | K1-K4 4/4 (pasca hasil) | 2026-11-08 |
| H36 | PEAD / Earnings Surprise syariah (SUE murni) | fundamental | Gagal | dev lulus (bergantung artefak 2020) · holdout gagal · syarat 2a & 2b gagal | 2026-11-12 |
| H37 | Syariah Global + Emas: 40% Indonesia + 40% global + 20% emas | rezim | Uji maju (pasca_hasil) | dev 3/3 + holdout 3/3, sensitivitas 4/4 di keduanya (label varian emas dibetulkan 2026-11-12: spread bukan biaya/th); aturan uji maju dikunci 2026-11-12 (mulai 1 Des 2026) | - |
