# Kesimpulan uji coba swing saham syariah IDX dengan data gratis

Tanggal: 20 Oktober 2026. Status: **selesai untuk tahap data gratis.**
Bukan nasihat keuangan.

## Ringkasan
Tujuannya mencari metode swing di saham syariah IDX yang bisa jadi **penghasilan rutin**, dengan target awal minimal +3% per posisi.

Pembaruan 21 Okt 2026: setelah target diubah jadi "return sebesar-besarnya dengan SL, lama tahan bebas", **H11a (beli saat harga tertinggi 52 minggu, keluar dengan trailing stop 3xATR) lulus holdout 2020-2026**. Statusnya kandidat paper trade, lihat bagian Tahap 3 di bawah. Kesimpulan untuk swing pendek (≤ 2 minggu) tetap sama.

Hasil swing pendek: **dari 14 uji, tidak ada strategi yang lolos.** Beberapa sinyal memang ada sebelum biaya, tapi kecil, tidak stabil, dan habis dimakan biaya transaksi. Satu-satunya pola yang konsisten di masa lalu (breakout) gagal total di data 2024-2026 yang belum pernah dilihat.

Kesimpulan: **dengan data harian publik gratis, swing trading belum terbukti bisa jadi penghasilan rutin di saham syariah IDX.**

## Data yang dipakai
| Data | Sumber | Rentang |
|---|---|---|
| Harga harian (mentah dan disesuaikan), dividen, split | yfinance | 2010 s/d Okt 2026, 217 saham syariah |
| IHSG, USD/IDR, minyak, emas, S&P500, VIX, EEM | yfinance | 2010 s/d Okt 2026 |
| Sektor dan fundamental snapshot | yfinance `.info` | saat ini saja |
| Ringkasan saham harian: foreign buy/sell, bid/offer, free float, pasar negosiasi | IDX `GetStockSummary` (lewat browser) | 2020 s/d Okt 2026, semua saham (989 kode) |

Tidak ada sumber gratis untuk:
- broker summary historis
- laporan keuangan per kuartal yang lengkap (yfinance cuma 5-6 kuartal)
- riwayat daftar syariah (DES)

## Cara uji
- **Hipotesis dan kriteria ditulis sebelum uji** (`RENCANA_SCREENER.md`). Tidak ada penyesuaian setelah lihat hasil.
- **Dev dan holdout.** Holdout cuma dibuka kalau dev lulus. Pengecualian H4 diputuskan terbuka dan dicatat sebelum dijalankan.
- **Biaya**: fee beli 0.15% + jual 0.25% + slip 1 tick per sisi, pakai fraksi harga IDX. Rata-rata sekitar 1.2% per round trip.
- **Entry di open hari berikutnya.** Kalau TP dan SL sama-sama mungkin kena di satu candle, dianggap SL. Candle ARB terkunci tidak bisa jual.
- **Kriteria lulus** (semuanya wajib):
  - expectancy net > 0
  - di atas pembanding acak
  - bootstrap 90% di atas nol
  - tahun positif >= 70%
  - tetap positif tanpa 10 trade terbaik dan tanpa 5 ticker teratas
- **Laporan portofolio bulanan** (5 posisi @ 20%) supaya kelihatan apakah bisa jadi penghasilan rutin.

## Hasil semua uji
Angka net per trade sudah dikurangi biaya.

| # | Hipotesis | Periode | Kotor | Pembanding acak | Net | CAGR portofolio | Hasil |
|---|---|---|---|---|---|---|---|
| H0 | Skor walk-forward, TP +3% / SL -3% | 2015-2021 | -0.09% | (hit 45.5%) | -1.23% | -52% | Gagal 1/7 |
| H1 | Skor walk-forward, TP +8% / SL -4% | 2015-2021 | - | (hit 31.6%) | -1.14% | -20% | Gagal 0/7 |
| H2 | Run-up dividen (ex-5 s/d cum date) | 2010-2021 | +0.40% | +0.03% | -0.77% | -5% | Gagal |
| H2b | Sama, yield >= 3% | 2010-2021 | +1.10% | +0.03% | -0.09% | -0.2% | Gagal |
| H3 | Pullback dalam tren naik | 2010-2021 | +0.87% | +0.28% | -0.45% | -4% | Gagal |
| H4 | Breakout konsolidasi + volume | 2010-2021 | +2.60% | +0.28% | +1.23% | +7% | Gagal tipis (4/6) |
| H5 | Pergantian bulan | 2010-2021 | +0.23% | +0.03% | -1.03% | -9% | Gagal |
| H6 | Menjelang libur Lebaran | 2010-2021 | +0.47% | +0.07% | -0.81% | -0.8% | Gagal |
| H7a | Akumulasi asing 5 hari (desil teratas) | 2020-2023 | +0.08% | +0.09% | -1.16% | -28% | Gagal |
| H7b | Breakout + akumulasi asing | 2020-2023 | +4.04% | +0.09% | +2.56% | +11.5% | Gagal (4/6) |
| H4* | Breakout, uji sekali di data baru | **2024-2026** | **-0.04%** | +0.30% | **-1.46%** | **-18.9%** | **Gagal 0/6** |
| H8 | Reaksi laporan keuangan (>= +4% di atas IHSG), DES historis | 2020-2023 | +1.32% | -0.08% | -0.02% | -1.1% | Gagal 2/6 |
| H9 | Blok negosiasi dengan premi >= 2%, DES historis | 2020-2023 | -1.67% | -0.08% | -3.08% | -23% | Gagal 0/6 |
| H10 | Antrian bid dominan saat tutup, DES historis | 2020-2023 | +0.30% | -0.11% | -0.97% | -42% | Gagal 1/6 |

*Pengecualian atas keputusan user, dicatat sebelum dijalankan.
**Tahap 3 (21 Okt 2026), lama tahan bebas + trailing stop:** H11a (52-week high, stop 3xATR) dev 2010-2019 lulus 6/7, lalu diuji sekali di holdout 2020-2026 (DES historis) dan **lulus 7/7**: net +6.21%/trade, CAGR portofolio 30.3% (versi konservatif 21.3%) vs beli-tahan 6.5%, drawdown -37%, bulan positif sekitar 40%. Status **kandidat paper trade**, belum terbukti. Detail di `RENCANA_SCREENER.md`.

H8-H10 (tahap 2, 21 Okt 2026) memakai universe saham yang syariah menurut DES OJK **pada hari itu**, data IDX 2020+, dan tanggal publikasi laporan keuangan dari IDX.

Hasil lama `swing_target3.py` (sebelum tahap ini) sejalan: sinyal komposit lebih baik dari acak, tapi dengan slip 0.5% expectancy sekitar 0, dan 88% untung berasal dari 5 saham gorengan.

## Temuan penting
1. **Biaya adalah pembunuh utama.** Sinyal terbaik sebelum biaya cuma +0.4% s/d +1% per trade (kecuali breakout), sedangkan biaya sekitar 1.2%. Trading sering dengan target kecil secara matematis berat. TP3/SL3 butuh hit sekitar 60%, model cuma mencapai 49%.
2. **Ranking saham itu nyata tapi lemah.** Skor walk-forward konsisten menaikkan peluang kena TP dari 43% ke 49% (spearman 0.93). Tidak cukup untuk menutup biaya.
3. **Efek dividen nyata tapi kecil.** Kenaikan menjelang cum date di atas acak, dan lebih kuat kalau yield tinggi, tapi lebih kecil dari biaya.
4. **Foreign flow tidak punya daya prediksi.** Saham yang diakumulasi asing tidak lebih baik dari saham acak (+0.08% vs +0.09%). Digabung dengan breakout pun cuma beda 0.1%.
5. **Breakout adalah pelajaran terpenting.** Rata-ratanya positif di data lama (2010-2021: 8 dari 12 tahun positif; 2020-2023: 4 dari 4), lalu negatif di semua tahun 2024-2026. Untungnya juga selalu bergantung pada segelintir trade besar (median trade negatif). Pola yang terlihat kuat di backtest bisa berhenti bekerja. Holdout yang dijaga ketat mencegah kerugian nyata.
6. **Spread nyata** (dari bid/offer IDX) sekitar 1.1-1.2 tick. Model 1 tick per sisi sekitar 2x lebih mahal dari setengah spread. Tapi dengan biaya lebih murah pun breakout 2024+ tetap rugi (-0.44%).
7. **Reaksi laporan keuangan adalah efek terkuat yang "struktural".** Saham yang naik >= 4% di atas IHSG setelah laporan terbit, rata-rata naik lagi +1.3% dalam 10 hari (acak: -0.1%). Tapi setelah biaya hasilnya cuma impas, makin lemah tiap tahun, dan sampelnya kecil (168 trade).
8. **Tidak ada strategi yang konsisten per bulan.** Bahkan yang terbaik (H4 2010-2021): bulan positif cuma 36%, bulan terburuk -12%, drawdown -23%. Tidak cocok untuk kebutuhan penghasilan rutin.

## Kelemahan uji ini
- **Bias survivorship**: daftar syariah yang dipakai adalah daftar saat ini, bukan riwayat. Biasanya ini membuat backtest terlihat **lebih bagus**, jadi kenyataannya kemungkinan lebih buruk.
- Status syariah historis (DES dari OJK) belum dipakai saat uji. Dicek sesudahnya (`des_ojk.py`): 11.1% hari-saham 2020+ di daftar kita ternyata tidak syariah pada saat itu, dan daftar kita cuma mencakup sekitar 2/3 saham syariah yang likuid. Uji berikutnya wajib pakai DES historis.
- Data IDX cuma ada sejak 2020, jadi uji foreign flow cuma 4 tahun dev.
- Harga yfinance disesuaikan split. Sekitar 9% close tidak cocok dengan IDX, kemungkinan karena itu.
- Ada 11+ uji, jadi peluang "lulus karena kebetulan" naik. Ini justru membuat hasil gagal makin meyakinkan.
- Kebocoran kecil yang sudah dicatat: smoke test membuka H4 2022-2023 sebelum waktunya.

## Yang belum diuji
- Broker summary historis (bandarmologi). Invezgo cuma punya data sejak 21 April 2025 (dicek dengan trial, angkanya cocok persis dengan IDX). Belum ada sumber dengan riwayat panjang.
- Rebalancing indeks syariah (JII/ISSI)
- 55 kode DES yang sudah dihapus yfinance (11 pernah likuid, sekitar 0.9% hari-saham likuid)

## Rekomendasi
1. **Jangan pakai strategi swing mana pun dari uji ini untuk uang sungguhan.**
2. Untuk **penghasilan rutin**, sumber yang memang konsisten: dividen saham syariah, sukuk ritel, reksa dana pasar uang syariah. Trading paling banter jadi sampingan, dan baru dihitung setelah terbukti di paper trade.
3. Kalau mau lanjut riset trading, langkah berikutnya **data berbayar** (broker summary historis atau laporan keuangan lengkap). Wajib tetap pakai disiplin yang sama: hipotesis dulu, holdout, biaya realistis.

## File dan cara mengulang
| File | Fungsi |
|---|---|
| `kumpul_data.py` | Unduh ulang data yfinance ke `data/` |
| `idx_asing_browser.js` + `idx_asing.py impor` | Ambil data IDX lewat Console Chrome, lalu impor ke `data/idx_harian.parquet` |
| `screener.py uji --tp 3 --sl 3` | H0/H1 (walk-forward). `pindai` untuk daftar harian (status: belum terbukti) |
| `uji_dividen.py`, `uji_setup.py`, `uji_asing.py` | H2, H3-H6, H7 |
| `des_ojk.py` | DES historis OJK (14 periode, 2019-2026) ke `data/des/des_historis.csv` |
| `idx_lapkeu_browser.js` + `idx_lapkeu.py` | Tanggal publikasi laporan keuangan IDX ke `data/idx_lapkeu.parquet` |
| `uji_tahap2.py` | H8-H10 dengan universe DES historis |
| `laporan_bulanan.py` | Simulasi portofolio bulanan |
| `RENCANA_SCREENER.md` | Semua hipotesis, kriteria, dan hasil detail, ditulis berurutan |
| `status_screener_*.txt`, `holdout_dibuka_*.txt` | Penanda status dan holdout yang sudah dibuka |
