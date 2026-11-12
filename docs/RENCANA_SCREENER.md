# Rencana screener TP +3% (dikunci 2026-10-20, sebelum ada hasil)

## Pertanyaan
Bisakah skor dari data harian memilih saham syariah yang **kena +3% sebelum -3%** lebih sering dari saham acak, dan tetap untung setelah fee + slip?

## Label (triple barrier)
- Sinyal di close hari t, entry di **open t+1**.
- TP = entry x 1.03, SL = entry x 0.97 (harga murni, tanpa fee).
- Dicek per candle mulai t+1:
  - open <= SL: keluar di open (rugi gap). open >= TP: keluar di open (untung gap).
  - low <= SL dan high >= TP di candle yang sama: **dianggap SL** (konservatif).
  - candle terkunci (high == low) dan turun: tidak bisa jual, lanjut ke candle berikutnya.
- Batas teknis 60 hari bursa: keluar di close, dicatat sebagai `waktu`. Kalau > 5% trade, dilaporkan.
- Hasil: `menang` (TP duluan) = 1, selain itu 0. Return per trade juga disimpan.

## Universe
- Saham di `syariah_tickers.txt` (bias survivorship belum ditutup, dicatat sebagai kelemahan).
- Lolos per hari: rata-rata nilai transaksi 20 hari >= Rp5 M, ATR% 1.5-5, harga mentah >= 50, tidak ada volume nol 5 hari terakhir.
- Data dari 2010, harga adjusted untuk sinyal, harga mentah untuk fraksi harga.

## Fitur (tetap, tidak ditambah setelah lihat hasil)
Per saham (diubah jadi persentil cross-section per hari): mom5, mom20, mom60, jarak_ema20, jarak_ema50, rsi, atr_pct, kontraksi, vol_rasio, jarak_high20, posisi_close, rs20 (mom20 - mom20 IHSG), log nilai transaksi.
Pasar (sama untuk semua saham di hari itu): IHSG di atas EMA50, mom20 IHSG, breadth (% syariah di atas EMA20).

## Model
Regresi logistik, **walk-forward**: tiap awal tahun dilatih ulang dengan semua data sebelumnya (minimal 4 tahun), prediksi tahun itu. Label baru dipakai untuk latih kalau tradenya sudah selesai sebelum tanggal latih (tidak bocor).
Skor = perkiraan peluang menang.

## Periode
- Pengembangan (dev): prediksi 2015-2021.
- Holdout: 2022 s/d sekarang. **Dilihat sekali** setelah semua keputusan dikunci.

## Biaya
Fee beli 0.15%, jual 0.25%, slip **1 tick per sisi** pakai fraksi harga IDX (harga mentah): <200: 1, 200-499: 2, 500-1999: 5, 2000-4999: 10, >=5000: 25.

## Kriteria lulus (semua, di dev **dan** holdout)
1. Desil skor teratas: hit rate >= base rate (semua saham lolos universe) **+5 poin**.
2. Hit rate naik seiring desil skor: Spearman desil vs hit >= 0.7.
3. Simulasi trade desil teratas (1 posisi per ticker sekaligus): expectancy setelah fee + slip > 0.
4. Bootstrap 90% (blok per bulan) expectancy di atas nol.
5. Tahun positif >= 70%.
6. Tetap positif tanpa 10 trade terbaik dan tanpa 5 ticker teratas.

Gagal di dev: berhenti, tidak lanjut ke holdout, screener diberi label "belum terbukti".
Lulus dev, gagal holdout: tidak ada edge, jangan dipakai.
Lulus semua: boleh paper trade (log rekomendasi dicek maju).

## Hasil H0 (TP 3 / SL 3)
Dev GAGAL (lihat catatan ringkas). Holdout tidak dibuka.

## H1: TP lebih besar (dikunci 2026-10-20, sebelum dijalankan)
- Alasan: biaya sekitar 1.1% per trade terlalu besar dibanding TP 3%.
- **Satu konfigurasi saja: TP +8%, SL -4%** (RR 2:1). Hit impas sekitar (4 + 1.1) / 12 = 43%.
- Semua yang lain sama dengan H0 (label, universe, fitur, model, periode, biaya, kriteria 1-6). Penanda holdout terpisah per konfigurasi.
- Tidak boleh mencoba TP/SL lain kalau gagal.

## H2: run-up menjelang cum date dividen (dikunci 2026-10-20, sebelum dijalankan)
- Alasan: investor beli menjelang cum date demi dividen. Polanya struktural.
- Event: ex-date dari yfinance. Cum date = hari bursa sebelum ex-date.
- Trade: **entry open hari bursa ex-5, exit close cum date (ex-1)**, tahan 4 hari. Dipilih 5 hari karena jadwal cum biasanya sudah diumumkan sekitar 8 hari bursa sebelumnya, jadi tidak bocor ke masa depan.
- Syarat: saham lolos filter likuiditas universe di hari sinyal (ex-6). ATR tidak difilter.
- Kelompok: **utama** = semua event. **Sekunder** (ditetapkan sekarang) = yield dividen >= 3% (dividen / close mentah hari sinyal).
- Pembanding: semua tahanan 4 hari (entry open t+1, exit close t+4) dari saham lolos universe di tahun yang sama.
- Periode: dev 2010-2021, holdout 2022 s/d sekarang.
- Biaya sama (fee + 1 tick per sisi).
- Kriteria lulus (dev **dan** holdout): exp net > 0, lebih tinggi dari pembanding, bootstrap 90% (blok per bulan) > 0, tahun positif >= 70%, tetap positif tanpa 10 trade terbaik dan tanpa 5 ticker teratas.
- Juga dilaporkan (tidak jadi kriteria): % trade dengan kenaikan kotor >= 3%.

## Hasil H1 dan H2 (2026-10-20)
- H1 TP8/SL4 dev: **GAGAL 0/7**. Base 31.6%, desil 10 hit 34.3%, spearman 0.39, exp net -1.14%. Holdout tidak dibuka.
- H2 dividen dev 2010-2021: **GAGAL**.
  - Utama: 396 event, kotor +0.40% vs pembanding +0.03%, net -0.77%, tahun positif 17%.
  - Yield >= 3%: 100 event, kotor +1.10%, net -0.09%, bootstrap [-0.94, 0.84], tahun positif 50%.
  - Efek run-up ada (kotor di atas pembanding) tapi lebih kecil dari biaya. Holdout tidak dibuka.

## H3-H6: setup teknikal dan kalender (dikunci 2026-10-20, sebelum dijalankan)
Kerangka bersama:
- Universe dan biaya sama dengan H0. Sinyal di close, entry open hari berikutnya, exit di close hari ke-N. Tidak ada TP/SL.
- Pembanding: semua tahanan N hari dari saham lolos universe di periode yang sama.
- Kriteria lulus sama dengan H2 (exp net > 0, di atas pembanding, bootstrap 90% > 0, tahun positif >= 70%, tahan tanpa 10 terbaik dan tanpa 5 ticker), di dev 2010-2021 **dan** holdout 2022+.
- Ada 4 hipotesis sekaligus, jadi peluang lulus karena kebetulan naik. Holdout tetap hakim terakhir.

Definisi:
- **H3 pullback dalam tren naik**: EMA20 > EMA50, close > EMA50, turun >= 5% dalam 3 hari. Tahan 10 hari. Satu posisi per ticker.
- **H4 breakout dari konsolidasi + volume**: rasio ATR/rata-rata 60 hari < 0.8 di hari sebelumnya, close > high 20 hari sebelumnya, volume >= 2x rata-rata 20 hari. Tahan 10 hari. Satu posisi per ticker.
- **H5 pergantian bulan**: sinyal di hari bursa kedua terakhir tiap bulan, entry open hari bursa terakhir, exit close hari bursa ke-3 bulan berikutnya. Semua saham lolos universe.
- **H6 menjelang libur Lebaran**: L = hari bursa terakhir sebelum Idul Fitri. Entry open L-4, exit close L (tahan 5 hari). Semua saham lolos universe. Tanggal Idul Fitri: 2010-09-10, 2011-08-30, 2012-08-19, 2013-08-08, 2014-07-28, 2015-07-17, 2016-07-06, 2017-06-25, 2018-06-15, 2019-06-05, 2020-05-24, 2021-05-13, 2022-05-02, 2023-04-22, 2024-04-10, 2025-03-31, 2026-03-20.

## Hasil H3-H6 dev 2010-2021 (2026-10-20)
| | n | kotor | pembanding | net | hasil |
|---|---|---|---|---|---|
| H3 pullback | 1114 | +0.87% | +0.28% | -0.45% | GAGAL (tahun + 33%) |
| H4 breakout | 425 | +2.60% | +0.28% | **+1.23%** | GAGAL tipis: bootstrap 5% -0.05, tahun + 67% (8/12). Lulus 4 dari 6 kriteria. |
| H5 pergantian bulan | 5249 | +0.23% | +0.03% | -1.03% | GAGAL |
| H6 Lebaran | 388 | +0.47% | +0.07% | -0.81% | GAGAL |
Semua kotor di atas pembanding, tapi cuma H4 yang lebih besar dari biaya. Sesuai aturan, holdout tidak dibuka dan H4 tidak diubah-ubah.

## H7: foreign flow (dikunci 2026-10-20, sebelum data IDX diunduh)
- Data: `data/idx_harian.parquet` dari `GetStockSummary?date=YYYYMMDD`. Liputan saham lolos universe harus >= 80%. Kalau di bawah itu, hasil tidak dipakai.
- Fitur: **akumulasi asing 5 hari** = jumlah (ForeignBuy - ForeignSell) x Close selama 5 hari / rata-rata nilai transaksi 20 hari.
- **H7a**: saham di desil teratas akumulasi asing (cross-section per hari, saham lolos universe). Entry open besok, tahan 10 hari. Satu posisi per ticker.
- **H7b** (sekunder, ditetapkan sekarang): sinyal H4 breakout **dan** akumulasi asing 5 hari > 0. Tahan 10 hari.
- Pembanding dan kriteria sama dengan H3-H6.
- Periode: kalau data mulai <= 2016, dev s/d 2021 dan holdout 2022+. Kalau lebih baru, dev = 60% awal tahun yang tersedia, holdout = sisanya.
- **Ditetapkan 2026-10-20 (data belum diimpor):** API IDX hanya punya data 2020 ke atas. Tujuh tahun (2020-2026), 60% = 4 tahun. **Dev 2020-2023, holdout 2024-01-01 s/d sekarang.** Tahun positif >= 70% di dev berarti minimal 3 dari 4 tahun.
- Catatan: sampelnya kecil (H4 cuma sekitar 35 trade/tahun, jadi H7b mungkin hanya puluhan trade). Hasil H7b dengan < 50 trade di dev dianggap tidak cukup bukti, apa pun hasilnya.
- **Kriteria tambahan H7b (2026-10-20, sebelum data asing asli ada):** exp net H7b harus > exp net H4 di periode yang sama, di dev dan holdout. Alasannya: smoke test dengan data asing acak menunjukkan H7b tetap terlihat bagus karena mewarisi H4.
- **Kebocoran yang dilaporkan:** smoke test `uji_asing.py` mencetak H4 dengan harga asli 2020-2023. Itu membuka sebagian holdout H4 (2022-2023). Hasil yang terlihat: n 218, exp net +2.46%, bootstrap [-0.06, 5.00], tanpa 10 terbaik -0.50%. Untuk H4, periode yang masih bersih **hanya 2024+**.

## Hasil H7 dev 2020-2023 (2026-10-20, data asli)
- Kualitas data: liputan asing 99.2%. Close IDX cocok dengan yfinance 91.2%. Yang tidak cocok kemungkinan saham yang pernah split (AKRA, BYAN, BRIS, dll), karena yfinance menyesuaikan split. Kalender IDX = IHSG (1636 hari).
- Spread nyata median sekitar 1.1-1.2 tick (<200: 1.16%, 500-1999: 0.56%, 5000+: 0.35%). Setengah spread per sisi = sekitar 0.55-0.6 tick, jadi model 1 tick per sisi sekitar 2x lebih mahal dari setengah spread.
- **H7a GAGAL total**: kotor +0.08% vs pembanding +0.09%. Akumulasi asing sendirian tidak punya daya prediksi.
- **H7b GAGAL**: net +2.56% (H4 +2.46%), bootstrap [0.05, 5.00], tahun positif 4/4. Gagal di tanpa 10 terbaik (-0.68%) dan tanpa 5 ticker (-0.06%). Filter asing hampir tidak menambah apa-apa di atas H4.
- Holdout H7 tidak dibuka.
- H4 di 2020-2023 (sudah terlihat waktu smoke test): +2.46%, tahun positif 4/4, tapi tanpa 10 terbaik -0.50%. Hasilnya bergantung pada sedikit trade besar (positive skew).

## PENGECUALIAN: uji H4 breakout di 2024+ (diputuskan user 2026-10-20, dikunci sebelum dijalankan)
- Melanggar aturan "gagal dev, berhenti". Alasan: H4 satu-satunya pola yang konsisten positif di 2010-2021 dan 2020-2023. 2024+ satu-satunya periode yang belum pernah dilihat.
- Definisi H4 **persis sama**, tidak ada yang diubah. Periode 2024-01-01 s/d data terakhir. Pembanding, biaya, dan 6 kriteria sama dengan H3-H6. Tahun positif >= 70% berarti 3 dari 3 tahun (2026 cuma sebagian).
- Hanya sekali jalan. Kalau lulus, statusnya **kandidat paper trade**, bukan terbukti. Kalau gagal, H4 ditutup dan tidak diubah-ubah.
- **Hasil (2026-10-20): GAGAL 0/6.** 192 trade, kotor -0.04% (pembanding +0.30%), net -1.46%, semua tahun negatif (2024 -1.65%, 2025 -0.68%, 2026 -1.98%), median -2.10%. Portofolio: CAGR -18.9%, DD -47%. Dengan biaya setengah spread pun tetap -0.44%. **H4 ditutup.**

## Tahap 2: H8-H10 dengan universe DES historis (dikunci 2026-10-20, sebelum data dan kode dibuat)
Konteks: broker summary ditinggalkan (Invezgo cuma punya data sejak 2025-04-21). Sudah ada 11 uji gagal, jadi peluang lulus kebetulan makin besar. Holdout tetap hakim terakhir.

Kerangka bersama:
- **Universe**: saham yang **syariah menurut DES OJK pada hari sinyal** (`des_ojk.syariah_pada`), bukan `syariah_tickers.txt`. Harga dari yfinance (adjusted) untuk semua kode DES. Filter likuiditas sama (nilai 20 hari >= Rp5 M, ATR% 1.5-5, harga >= 50, tidak ada volume nol 5 hari).
- Periode: **dev 2020-2023, holdout 2024+** (data IDX hanya 2020+). Biaya sama (fee + 1 tick per sisi). Entry open hari setelah sinyal.
- Pembanding: semua tahanan dengan lama sama dari universe yang sama dan periode yang sama.
- Kriteria sama dengan H3-H6 (6 kriteria) + laporan bulanan.

Definisi:
- **H8 reaksi laporan keuangan**: t0 = hari bursa pertama pada/setelah tanggal publikasi laporan keuangan (kuartalan/tahunan) di situs IDX. Reaksi abnormal = return close(t0-1) ke close(t0+1) dikurangi return IHSG di jendela yang sama. Sinyal di close t0+1 kalau reaksi abnormal >= +4%. Tahan 10 hari. Butuh data tanggal publikasi dari IDX (diunduh user lewat browser). Kalau tanggal publikasi tidak bisa didapat, H8 batal (tidak diganti proksi).
- **H9 blok negosiasi premium**: harga rata-rata negosiasi = NonRegularValue / NonRegularVolume. Sinyal kalau NonRegularValue >= 50% rata-rata nilai reguler 20 hari **dan** harga rata-rata negosiasi >= close reguler x 1.02. Tahan 10 hari. Satu posisi per ticker.
- **H10 antrian beli penutupan**: imbalance = (BidVolume - OfferVolume) / (BidVolume + OfferVolume) saat penutupan (Bid > 0 dan Offer > Bid). Sinyal: desil teratas imbalance cross-section per hari. Tahan 5 hari. Satu posisi per ticker.

### Data H8 (dikunci 2026-10-21, sebelum data lengkap diunduh)
- Sumber: `GetFinancialReport` IDX (reportType=rdf, EmitenType=s, periode tw1/tw2/tw3/audit, tahun laporan 2019-2026).
- Tanggal publikasi = `File_Modified` **paling awal** di antara record dan lampirannya.
- Dibuang kalau tanggal publikasi > 6 bulan setelah akhir periode laporan (TW1 = 31 Mar, TW2 = 30 Jun, TW3 = 30 Sep, Audit = 31 Des). Kemungkinan itu revisi, bukan publikasi pertama. Jumlah yang dibuang dilaporkan.
- Definisi sinyal H8 tidak berubah.

### Hasil tahap 2 dev 2020-2023 (2026-10-20)
- Universe: 766 ticker berdata harga, rata-rata 67 saham lolos per hari. 55 kode DES tidak ada di yfinance (delisting/ganti kode). 11 di antaranya pernah likuid (ENVY, HKMU, DUCK, TECH, JSKY, FREN, META, dll), sekitar 0.9% hari-saham likuid. Sisa bias survivorship ini kecil tapi membuat hasil sedikit terlalu bagus.
- **H9 blok negosiasi premium: GAGAL 0/6.** 289 trade, kotor -1.67% (pembanding -0.08%), net -3.08%. Arahnya terbalik (lebih buruk dari acak), tapi **tidak boleh dibalik jadi sinyal jual/hindari** tanpa hipotesis baru.
- **H10 imbalance bid penutupan: GAGAL 1/6.** 4236 trade, kotor +0.30% (pembanding -0.11%), net -0.97%, 0/4 tahun positif.
- Data H8 (2026-10-21): 22.898 record dari IDX, 565 dibuang (> 6 bulan, kemungkinan revisi), sisa 22.333. 791 dari 823 kode DES tercakup. Jeda publikasi median 36 hari. 47% terbit setelah 16:00. TW1 2024 cuma 677 di data mentah IDX (lebih sedikit dari tahun lain).
- **H8 reaksi laporan keuangan: GAGAL 2/6.** 168 trade, kotor **+1.32%** (pembanding -0.08%), net **-0.02%** (hampir impas), bootstrap [-1.40, 1.19], tahun positif 3/4 (2020 +1.76, 2021 +0.55, 2022 +0.03, 2023 -1.57, makin turun). Tanpa 10 terbaik -1.49%. Portofolio: CAGR -1.1%, DD -14%. Efek drift setelah laporan **nyata sebelum biaya** (+1.4 poin di atas acak), tapi tidak cukup setelah biaya. Holdout tidak dibuka.

## Tahap 3: trend following, lama tahan bebas (dikunci 2026-10-21, sebelum kode dibuat)
Target user berubah: **return sebesar-besarnya, wajib SL, tanpa minimal return dan tanpa batas hari.** Sudah ada 14 uji gagal, jadi peluang lulus kebetulan tinggi.

Exit (sama untuk semua hipotesis, tidak boleh diubah):
- Entry open hari setelah sinyal.
- Stop awal = entry - 3 x ATR14 (ATR di hari sinyal).
- Trailing stop = max(stop sebelumnya, close tertinggi sejak entry - 3 x ATR14 hari itu).
- Kalau close < stop: keluar di **open besoknya** (gap ikut dihitung).
- Batas teknis 500 hari bursa, keluar di close.
- Satu posisi per ticker. Biaya sama (fee + 1 tick per sisi).

Sinyal:
- **H11a 52-week high**: close >= close tertinggi 250 hari sebelumnya.
- **H11b momentum 6 bulan**: return 120 hari di desil teratas cross-section **dan** close > EMA200.

Periode dan universe:
- **Dev 2010-2019**: daftar 217 saham (`syariah_tickers.txt`). Bias survivorship dan status syariah diketahui, membuat dev terlihat lebih bagus.
- **Holdout 2020-01-01 s/d sekarang**: universe DES historis (benar). Sebagian data harga 2020+ sudah dipakai uji lain dengan aturan berbeda, dicatat sebagai kelemahan.
- Sinyal dihitung sampai akhir periode. Trade yang masih terbuka di akhir data ditutup di close terakhir.

Portofolio: maksimal **10 posisi @ 10%**. Sinyal ditolak kalau slot penuh. Sinyal di hari yang sama dipilih acak (seed 7).

Kriteria lulus (dev **dan** holdout):
1-6. Sama dengan H3-H6 (exp net > 0, di atas pembanding tahan 20 hari, bootstrap 90% > 0, tahun positif >= 70%, tanpa 10 terbaik > 0, tanpa 5 ticker > 0).
7. CAGR portofolio > CAGR **beli dan tahan semua saham universe** (bobot sama, tanpa biaya) di periode yang sama.

### Hasil tahap 3 dev 2010-2019 (2026-10-21)
Data dev dipotong di 2019-12-31 supaya trade dev tidak memakai harga holdout. Beli-tahan bobot sama: CAGR 8.1%.
- **H11a 52-week high: GAGAL tipis, 6 dari 7 kriteria.** 495 trade, net +2.10% (kotor +3.43%, pembanding -0.65%), bootstrap [0.36, 4.00], tanpa 10 terbaik +0.14%, tanpa 5 ticker +0.58%. Portofolio 10 posisi: CAGR **12.1%** vs 8.1%, DD -20.4%, bulan positif 46%. **Gagal di tahun positif: 6/9 = 67%** (2014 -1.69%, 2015 -3.95%, 2019 -0.24%; 2010 tidak ada trade karena butuh 250 hari pemanasan). Median trade -3.31%, rata-rata tahan 33 hari.
- **H11b momentum 6 bulan: GAGAL** (4/7). Net +1.66%, bootstrap [-0.20, 3.71], tanpa 10 terbaik -0.15%, CAGR 4.8% < 8.1%.
- Sesuai aturan, holdout tidak dibuka. Catatan: dev memakai daftar 217 (bias survivorship), jadi hasil dev cenderung terlalu bagus.

### PENGECUALIAN: holdout H11a (diputuskan user 2026-10-21, dikunci sebelum dijalankan)
- Hanya H11a, aturan **persis sama** (sinyal, exit 3xATR, 10 posisi, biaya, 7 kriteria). H11b tidak dibuka.
- Universe DES historis, sinyal 2020-01-01 s/d data terakhir. Tahun positif >= 70% dihitung dari 2020-2026 (2026 sebagian).
- Sekali jalan. Lulus = kandidat paper trade (bukan terbukti). Gagal = H11a ditutup permanen, tidak ada variasi.
- **Hasil (2026-10-21): LULUS 7/7.** 692 trade, 235 ticker. Net +6.21% (kotor +7.70%, pembanding -1.02%), bootstrap [3.05, 9.87], tahun positif 5/7 (2020 +15.4, 2021 +7.9, 2022 -2.1, 2023 +2.8, 2024 +5.7, 2025 +15.9, 2026 -2.5), tanpa 10 terbaik +2.39%, tanpa 5 ticker +3.63%. Portofolio 10 posisi: CAGR 30.3% vs beli-tahan 6.5%, DD -37.7%, bulan positif 40%, median trade -5.7%, rata-rata tahan 30 hari.
- **Pemeriksaan realisme (laporan, bukan perubahan aturan):**
  - Data: close entry/exit 10 trade terbaik cocok dengan IDX (selisih 5x di HRUM/MSIN/SMDR karena yfinance menyesuaikan split). Tidak ada lonjakan harian > 35%.
  - 30 seed acak pemilihan portofolio: CAGR 24.7%-34.6%, DD median -35%. Semuanya di atas beli-tahan.
  - **Konservatif** (buang 10 entry di candle ARA terkunci, exit di candle ARB terkunci menunggu open pertama yang tidak terkunci): 682 trade, net +5.67%, tanpa 10 terbaik +1.91%, **CAGR 21.3%**, DD -37.1%, bulan positif 37%.
  - Per kelas harga: < 200 +5.5%, 200-499 +17.5%, 500-1999 +5.6%, >= 2000 +2.0%. Semua positif, tapi saham kecil-menengah menyumbang paling banyak.
- **Status: KANDIDAT PAPER TRADE.** Kelemahan: periode 2020-2026 mencakup reli besar saham kecil/konglomerasi (2020-2021, 2025). 55 kode delisting tidak ada di data. Hasil sangat bergantung pada sedikit trade besar (median trade negatif). Drawdown ~37% dan cuma sekitar 40% bulan positif, jadi **bukan penghasilan bulanan yang konsisten**.

### H12: H11a tanpa saham "liar" (dikunci 2026-10-21, sebelum dijalankan; ide muncul SETELAH melihat trade 2026)
- Aturan H11a sama persis, ditambah filter di hari sinyal:
  - **H12a**: ATR14% <= 3.5% (jadi stop awal paling jauh sekitar -10.5%).
  - **H12b**: H12a **dan** harga >= Rp200 (tick tidak lebih dari 0.5%).
- **Penilaian hanya di dev 2010-2019** (217 saham), dengan 7 kriteria H11a. Hasil 2020-2026 cuma informasi, karena periode itu sudah dipakai menilai H11a dan ide filter ini muncul dari melihat trade 2026.
- Kalau H12 lulus dev, tetap tidak menggantikan H11a sampai ada bukti paper trade ke depan. Kalau ditambahkan, paper trade dijalankan berdampingan, bukan mengganti.
- **Hasil (2026-10-21): H12a dan H12b GAGAL di dev.** Dev 2010-2019: net/trade 1.21% / 1.26% (H11a 2.10%), CAGR 5.0% / 5.2%, di bawah beli-tahan 8.1% (H11a 12.1%). Tanpa 10 terbaik jadi negatif. DD lebih kecil (-9% vs -20%), rata-rata kalah sedikit mengecil (-6.9% vs -7.9%), tapi rata-rata menang turun lebih banyak (14.0% vs 17.3%). Informasi 2020-2026: CAGR 4.1% / 3.0% vs H11a 30.3%. **Kesimpulan: kemenangan besar H11a justru datang dari saham volatil. Filter volatilitas membuang sumber edge-nya. H11a tetap tanpa filter.**

## H13: perbaikan H11a, diuji di data independen (dikunci 2026-10-21, sebelum data dan kode dibuat)
Sinyal dan exit H11a tidak berubah. Yang diubah cuma cara masuk portofolio, dalam tiga komponen dengan alasan logis:
- **S (ukuran posisi berbasis risiko)**: bobot = 1% ekuitas / jarak stop awal (3 x ATR14 / harga entry), paling besar 20%. Total bobot posisi terbuka maksimal 100% (sinyal ditolak kalau melebihi). Maksimal tetap 10 posisi. Alasan: rugi per trade terhadap modal jadi seragam tanpa membuang saham volatil.
- **R (regime pasar)**: sinyal baru hanya diambil kalau close IHSG > EMA200 IHSG di hari sinyal. Posisi yang sudah ada tidak dipaksa keluar. Alasan: breakout saat pasar turun lebih sering gagal.
- **P (prioritas saat slot terbatas)**: sinyal di hari yang sama diurutkan dari return 120 hari tertinggi, bukan acak. Alasan: tren lebih kuat lebih mungkin berlanjut.
- Konfigurasi yang dibandingkan (hanya ini): **H11a** (bobot 10%, acak), **S**, **R**, **P**, **S+R+P**.

Data uji independen (belum pernah dipakai untuk menilai H11a):
- **Set A**: 182 saham IDX yang tidak pernah masuk DES 2019-2026 (non-syariah), 2010 s/d sekarang. Hanya untuk pengujian, tidak untuk dibeli.
- **Set B**: saham DES di luar daftar 217, harga 2010-2019 (data dipotong 2019-12-31).
- Filter likuiditas dan biaya sama dengan H11a.

Metrik utama: **MAR = CAGR / |drawdown maksimal|** (return per unit risiko), ditambah CAGR, drawdown, bulan positif.

Aturan keputusan:
- Komponen (S, R, P) diadopsi hanya kalau **menaikkan MAR dibanding H11a di Set A dan Set B**.
- Paket S+R+P diadopsi kalau MAR-nya > H11a di kedua set **dan** CAGR-nya tetap > beli-tahan di kedua set.
- H11a sendiri juga dicek: kalau CAGR H11a < beli-tahan di Set A atau Set B, dicatat sebagai **peringatan** soal H11a.
- Hasil di periode syariah lama (2010-2019 217 saham, 2020+ DES) ditampilkan sebagai informasi, bukan dasar keputusan.

### Hasil H13 (2026-10-21)
Set A: 153 dari 182 saham non-syariah terunduh (29 delisting hilang), 144 cukup data. Set B: 306 saham.

| Set | H11a net/trade | H11a CAGR | DD | S | R | P | S+R+P (CAGR/DD) |
|---|---|---|---|---|---|---|---|
| A non-syariah 2010-2026 | +0.88% (WR 37%) | 1.9% | -28% | 1.5% / -26% | -0.2% / -25% | sama H11a | 0.7% / -23% |
| B DES di luar 217, 2010-2019 | +4.61% (WR 39%) | 12.5% | -18% | 11.1% / -21% | 9.5% / -14% | sama H11a | 7.4% / -17% |
| info 217, 2010-2019 | +2.10% | 10.8% | -20% | 9.6% / -15% | 7.1% / -19% | 10.2% / -20% | 6.4% / -16% |
| info DES 2020+ | +6.21% | 29.5% | -38% | 32.3% / -28% | 30.2% / -16% | 32.4% / -32% | 19.1% / -12% |

- **Keputusan: S, R, P, dan S+R+P TIDAK diadopsi** (MAR tidak naik di Set A dan B). P sama dengan H11a di set kecil karena slot jarang penuh. R dan S terlihat bagus di DES 2020+, tapi itu periode yang sudah terpakai, jadi tidak dihitung.
- **Koreksi alat ukur:** beli-tahan di `uji_tren.benchmark` memakai rebalance harian, dan ini menggelembungkan return (bounce bid-offer saham kecil). Dengan rebalance bulanan: A 5.0% (harian 7.8%), B 12.1% (18.1%), 217 7.6% (8.1%), DES 2020+ 0.5% (6.5%). IHSG: A 4.3%, B 9.4%, 2010-2019 9.4%, 2020+ -2.6%. Kriteria 7 H11a di holdout tetap lulus, malah lebih jelas (29.5% vs 0.5%).
- **Peringatan H11a:** net/trade positif di keempat set (+0.88 / +4.61 / +2.10 / +6.21), tapi di Set A (non-syariah) CAGR 1.9% < beli-tahan bulanan 5.0%. Di Set B setara (12.5% vs 12.1%). Sinyal di set kecil jarang, jadi modal sering menganggur di kas, dan itu menekan CAGR. Hasil 2020+ syariah (CAGR ~30%) kemungkinan sebagian karena periodenya (reli saham kecil). **Harapan realistis lebih rendah dari 30%.**

## H14: H11a + filter fundamental (dikunci 2026-10-21, sebelum data fundamental diunduh penuh)
Sumber: inline XBRL laporan keuangan IDX (`idx_fundamental_browser.js`), 2019-2026, 619 kode syariah likuid + 118 non-syariah likuid. Angka TW bersifat kumulatif sejak awal tahun (YTD).

**Point-in-time**: di hari sinyal, hanya laporan dengan tanggal publikasi (`File_Modified` terawal, tanpa yang > 6 bulan) **sebelum** hari sinyal yang boleh dipakai. Diambil laporan terbaru.

Laba = `ProfitLossAttributableToParentEntity@CurrentYearDuration` (kalau tidak ada, `ProfitLoss@CurrentYearDuration`). Pembanding tahun lalu = konteks `PriorYearDuration` di laporan yang sama.
- **H14a**: sinyal H11a hanya diambil kalau laba YTD > 0 **dan** laba YTD > laba YTD periode yang sama tahun lalu.
- **H14b** (sekunder): H14a **dan** pendapatan YTD (`SalesAndRevenue`) > tahun lalu. Emiten tanpa `SalesAndRevenue` (bank, dll.) dianggap tidak lolos H14b.
- Mata uang tidak berpengaruh, karena hanya membandingkan tanda dan pertumbuhan di laporan yang sama.
- Sinyal tanpa laporan yang tersedia: tidak diambil di H14 (jumlahnya dilaporkan).

Periode: sinyal 2020-01-01 s/d sekarang (laporan 2019 sebagai bekal).
- **Penilaian utama: Set A (non-syariah likuid) 2020-2026**, data independen.
- Syariah DES 2020-2026: sudah dipakai menilai H11a, jadi pendukung saja.

Aturan keputusan: H14a/H14b diadopsi kalau, dibanding H11a di set yang sama, **net/trade lebih tinggi dan MAR portofolio (10 posisi @10%) lebih tinggi di Set A dan di syariah DES 2020+**. Selain itu dicatat saja.

### Hasil H14 (2026-10-22, dijalankan sekali setelah data 2019-2026 lengkap)
Data: 16.986 laporan berisi angka, 733 kode; tanggal publikasi 97.7%. Liputan sinyal: 100% punya laporan terbit sebelum sinyal, umur median 27-68 hari.

| set | konfig | trade | net/trade | CAGR | DD | MAR |
|---|---|---|---|---|---|---|
| A non-syariah | H11a | 164 | 2.05% | 4.0% | -28.1% | 0.14 |
| A non-syariah | H14a | 127 | 2.52% | 4.4% | -21.3% | 0.21 |
| A non-syariah | H14b | 28 | 10.25% | 4.1% | -3.4% | 1.21 |
| syariah DES | H11a | 375 | 6.21% | 30.3% | -37.7% | 0.80 |
| syariah DES | H14a | 335 | 5.85% | 14.7% | -25.9% | 0.57 |
| syariah DES | H14b | 289 | 6.32% | 12.7% | -19.9% | 0.64 |

**Keputusan: H14a dan H14b TIDAK diadopsi.** H14a kalah net/trade dan MAR di syariah. H14b menang net/trade di kedua set, tapi MAR syariah lebih rendah (0.64 vs 0.80). H14b di Set A hanya 28 trade (bank tidak punya SalesAndRevenue, jadi tidak lolos sesuai aturan). Catatan: CAGR dihitung dengan metode portofolio bulanan yang sama untuk semua konfigurasi (lihat temuan di bagian batas paper). H11a tetap dipakai apa adanya.

## H15: perubahan kepemilikan KSEI (dikunci 2026-10-22, sebelum data dihubungkan ke harga)
Data: KSEI `BalanceposEfek<tgl>.zip` bulanan sejak Des 2009 (gratis, `backend/ingest/ksei.py`). Per saham: jumlah lembar per tipe investor lokal/asing (IS asuransi, CP korporasi, PF dana pensiun, IB lembaga keuangan, ID individu, MF reksa dana, SC sekuritas, FD yayasan, OT lainnya).
- **Ritel** = lokal ID. **Institusi** = lokal IS + PF + IB + MF + asing total - asing ID. Dihitung sebagai persen dari jumlah saham (`Sec. Num`).
- **Sinyal** = perubahan 3 bulan: persen di file tanggal D dikurangi persen di file 3 bulan sebelumnya.
- **Jeda publikasi**: file tanggal D baru boleh dipakai pada hari t kalau D + 30 hari <= t. Dipakai file terbaru yang memenuhi.

**H15a (portofolio bulanan mandiri)**: tiap hari bursa terakhir bulan, universe = daftar (dev: 217 `syariah_tickers.txt`; holdout: DES pada hari itu) yang nilai transaksi 20 hari >= `sc.MIN_VALUE`, harga >= `sc.HARGA_MIN`, tanpa hari volume 0 dalam 5 hari. Urutkan perubahan institusi 3 bulan; beli desil teratas (minimal 5 saham) sama bobot di open hari berikutnya, tahan sampai rebalance berikutnya (open hari setelah akhir bulan berikutnya). Biaya dihitung dari pergantian saham (fee 0.15%/0.25% + 1 tick per sisi). Pembanding = rata-rata sama bobot seluruh universe, tanpa biaya.
- Lulus dev 2011-2019 kalau semua: (1) rata-rata selisih bulanan bersih vs pembanding > 0; (2) batas bawah bootstrap 90% selisih bulanan > 0; (3) selisih positif di >= 70% tahun; (4) return kotor desil teratas > desil terbawah; (5) liputan KSEI >= 80% universe. Holdout 2020-2026 dibuka sekali hanya kalau dev lulus, dengan syarat (1), (3), (4).

**H15b (filter H11a)**: sinyal H11a hanya diambil kalau perubahan ritel 3 bulan <= 0 (ritel tidak bertambah). Sinyal tanpa data KSEI tidak diambil (dilaporkan).
- Diadopsi kalau net/trade DAN MAR portofolio lebih tinggi dari H11a di: dev 2010-2019 (217 syariah), Set A non-syariah 2020-2026, dan syariah DES 2020-2026. Metode portofolio sama dengan H13/H14.

Hanya dua uji ini. Tidak ada variasi lain (periode 1/6 bulan, kuintil, tipe investor lain) setelah melihat hasil.

### Hasil H15 (2026-10-22)
Data KSEI: 202 bulan (Des 2009 - Sep 2026), 1.053 kode, jumlah tipe = total 100%. Uji mesin dengan sinyal acak: kotor setara pembanding, biaya ganti saham ±1%/bulan.

**H15a dev 2011-2019: GAGAL 1/5.** 99 bulan, universe rata-rata 45 saham, desil 5 saham, liputan 99%, biaya 0.67%/bulan. Desil atas kotor +0.29%/bulan < desil bawah +0.45% < pembanding +0.40%; selisih bersih -0.77%/bulan (bootstrap 5% -1.57%), tahun positif 2/9. Holdout tidak dibuka.

**H15b: TIDAK diadopsi.**
| set | konfig | trade | net/trade | CAGR | DD | MAR |
|---|---|---|---|---|---|---|
| dev 217 syariah 2010-2019 | H11a | 358 | 2.10% | 9.0% | -20.0% | 0.45 |
| dev 217 syariah 2010-2019 | H15b | 274 | 2.37% | 7.0% | -20.3% | 0.35 |
| A non-syariah 2020-2026 | H11a | 164 | 2.05% | 4.9% | -28.1% | 0.17 |
| A non-syariah 2020-2026 | H15b | 80 | 1.94% | 2.1% | -12.1% | 0.17 |
| syariah DES 2020-2026 | H11a | 365 | 6.21% | 27.1% | -36.3% | 0.75 |
| syariah DES 2020-2026 | H15b | 294 | 5.27% | 18.2% | -22.1% | 0.82 |
Filter ritel mengurangi drawdown tapi juga return; tidak konsisten di ketiga set. (CAGR H11a di sini sedikit beda dari H14 karena periode metrik sampai Des 2026; kedua konfigurasi diukur sama.)

## H16: valuasi dashboard Emiten sebagai strategi (dikunci 2026-10-22, sebelum kode uji dibuat dan sebelum melihat hubungannya dengan return)
Pertanyaan: apakah saham syariah yang dinilai "Undervalue" / "Layak dipertimbangkan" oleh panel Valuasi (`backend/app/services/valuasi.py`) memberi return lebih tinggi dari rata-rata saham syariah likuid?

Aturan valuasi = sama dengan dashboard, dihitung point-in-time tiap akhir bulan t:
- Laporan: hanya yang `tgl_publikasi` <= t. TTM = YTD + tahunan tahun lalu - YTD tahun lalu. Saham beredar = KSEI terakhir <= t. Laporan USD x kurs pada t. Harga = close mentah pada t. Dividen = 365 hari sebelum t.
- Metode: PER/PBV historis (median riwayat bulanan sampai 5 tahun ke belakang, minimal 24 bulan), PER/PBV industri (median saham syariah seindustri pada t, minimal 4; kalau kurang pakai sektor), Graham, DDM (dividen 3 tahun kalender berturut-turut, payout >= 40%, r 11%, g maks 5%). Bank: PER dan Graham tidak dipakai. Energy/Basic Materials: PER tidak dipakai. Nilai wajar = median metode yang dipakai; MoS = (wajar - harga) / wajar.
- Kualitas 7 cek dan sikap persis seperti dashboard (Layak = MoS >= 20%, kualitas >= maks-1, harga >= MA200; kualitas dihitung dari data yang berlaku).

Portofolio bulanan sama bobot, beli open hari bursa setelah t, tahan sampai rebalance berikutnya; biaya hanya untuk saham yang masuk/keluar (fee 0.15%/0.25% + 1 tick per sisi). Universe: DES pada t, nilai transaksi 20 hari >= `sc.MIN_VALUE` (Rp5 M), harga >= Rp50, ada valuasi. Pembanding = rata-rata sama bobot universe, tanpa biaya.
- **H16a** = semua saham dengan vonis Undervalue (MoS >= 20%).
- **H16b** = semua saham dengan sikap Layak dipertimbangkan.
- Kelompok pembanding: Overvalue (MoS < -15%).

Periode: band historis butuh 24 bulan data sejak 2019, jadi sinyal mulai akhir 2021. **Dev 2021-04 s/d 2023-12, holdout 2024-01 s/d 2026-09** (dibuka sekali, hanya kalau dev lulus).
Lulus dev (masing-masing H16a/H16b) kalau semua: (1) rata-rata selisih bulanan bersih vs pembanding > 0; (2) batas bawah bootstrap 90% > 0; (3) selisih tahunan positif di >= 2 dari 3 tahun (2021 sebagian, 2022, 2023); (4) return kotor kelompok > return kotor kelompok Overvalue; (5) rata-rata isi portofolio >= 5 saham. Holdout: syarat (1), (3) [>= 2 dari 3 tahun], (4).
Catatan yang diterima: periode pendek, saham delisting yang tidak ada di Yahoo hilang (survivorship), sektor dari Yahoo (statis).

### Hasil H16 dev 2021-04 s/d 2023-12 (2026-10-22)
Sebelum uji asli ditemukan dan diperbaiki bug data (bukan perubahan aturan): harga Yahoo sudah disesuaikan stock split, jumlah saham KSEI belum, sehingga EPS/BVPS sebelum split terlalu besar (mis. DSSA split 1:10 2024 dan 1:25 2026). Jumlah saham sekarang dikali faktor split setelah tanggal data KSEI (`valuasi.saham_pada`), juga di dashboard. Uji mesin dengan label acak: kotor setara pembanding.
- Panel 17.715 baris, 493 kode; universe rata-rata 79 saham/bulan.
- **H16a Undervalue: GAGAL 2/5.** Isi 23,6 saham. Kotor +0,37%/bulan, bersih -0,07%, pembanding +0,28%, Overvalue kotor +0,05%. Selisih -0,35%/bulan (bootstrap 5% -1,20%). Per tahun: 2021 -13,8%, 2022 +13,1%, 2023 -9,8%.
- **H16b Layak dipertimbangkan: GAGAL 1/5.** Isi 2,5 saham (12% bulan kosong). Selisih -0,47%/bulan. Per tahun: 2021 +2,3%, 2022 -18,8%, 2023 -2,5%.
- Holdout tidak dibuka. Panel Valuasi tetap sebagai alat riset, bukan sinyal.

## H16c: Undervalue yang bukan "Hindari" (dikunci 2026-10-22, SETELAH melihat hasil H16a/H16b; ide dari user)
Status: varian pasca-hasil. Hanya satu varian ini yang diuji; tidak ada potongan lain setelahnya.
- Seleksi tiap bulan: vonis Undervalue (MoS >= 20%) DAN sikap bukan "Hindari" = skor kualitas > setengah cek yang berlaku (sama dengan "Pantau" atau "Layak" di dashboard untuk saham Undervalue). Universe, biaya, pembanding, periode, dan mesin sama persis dengan H16.
- Lulus dev 2021-04..2023-12 kalau: syarat H16 (1)-(5) DAN (6) rata-rata selisih bulanan H16c > H16a pada bulan yang sama (filter harus menambah nilai).
- Karena pasca-hasil, lulus dev saja tidak cukup untuk dipakai. Holdout 2024-01..2026-09 dibuka sekali hanya kalau dev lulus; syarat holdout (1), (3) [>= 2 dari 3 tahun], (4), (6).

### Hasil H16c dev 2021-04 s/d 2023-12 (2026-10-22): GAGAL 3/6
Isi rata-rata 19,2 saham. Kotor +0,72%/bulan, bersih +0,28%, pembanding +0,28%: selisih -0,00%/bulan (bootstrap 5% -0,88%). Per tahun: 2021 -11,9%, 2022 +20,7%, 2023 -7,2%. Filter kualitas memperbaiki H16a (-0,35% -> 0,00%) dan lebih baik dari Overvalue, tapi hanya menyamai rata-rata pasar dan bergantung pada satu tahun (2022). Holdout tidak dibuka. Tidak ada varian H16 lain yang akan diuji.

## Analisis konvergensi ke nilai wajar (dikunci 2026-10-22 sebelum dijalankan; deskriptif, bukan uji strategi)
Pertanyaan user: apakah harga saham Undervalue naik sampai nilai wajarnya, berapa lama, dan apa beda yang sampai dan yang tidak.
- Kejadian: saham syariah likuid (universe H16) yang di akhir bulan t berstatus Undervalue (MoS >= 20%) dan tidak sedang dalam kejadian aktif. Target = nilai wajar pada t (tetap). Kejadian baru untuk saham yang sama hanya setelah kejadian sebelumnya mencapai target.
- Hasil: hari bursa sampai close >= target; penurunan terdalam sebelum mencapai target; kenaikan tertinggi kalau belum mencapai.
- Pembanding: semua saham berstatus Wajar (MoS -15%..5%) di bulan yang sama, target kenaikan sama besar (persentase kejadian).
- Data hanya dev 2021-04..2023-12; jalur harga dipotong 31 Des 2023 (sensor). Peluang mencapai per 21/63/126/252/504 hari dengan Kaplan-Meier.
- Perbandingan ciri yang sampai vs tidak (dalam 252 hari): MoS, sektor/siklikal, sikap (Layak/Pantau/Hindari), skor kualitas, pertumbuhan laba 3 th, IHSG > MA200.

### Hasil analisis konvergensi (2026-10-22, `backend/research/analisis_konvergensi.py`)
131 kejadian Undervalue (116 saham), kenaikan yang dibutuhkan median 52% (p25/p75 34%/87%). Peluang mencapai nilai wajar (Kaplan-Meier): 3 bln 7%, 6 bln 11%, 1 th 21%, 2 th 26%. Pembanding saham Wajar dengan target naik sama: 8%, 14%, 21%, 24% -> tidak berbeda.
Yang sampai (28): median 135 hari bursa (p25/p75 51/223), sempat turun median -9% dulu. Yang belum (103): kenaikan tertinggi median +12%, penurunan terdalam median -31%.
Per kebutuhan naik: 25-50% Undervalue 26% vs Wajar 34% (1 th); 50-100% 19% vs 17%; >100% 12% vs 2%. MoS 20-35% 26% vs MoS >50% 12%. Sikap Layak/Pantau/Hindari dan siklikal tidak membedakan.
Kesimpulan: nilai wajar metode dashboard bukan target yang sering tercapai; status Undervalue tidak menambah peluang dibanding saham biasa dengan kenaikan yang sama.

## Tesis Undervalue: data 2024-2026 DIBUKA (keputusan user 2026-10-22)
Tesis Undervalue (keluarga valuasi: H16a/b/c dan analisis konvergensi) dipisah dari Tren 52 Minggu. Data 2024-01..2026-10 untuk tesis ini dibuka untuk analisis deskriptif konvergensi ke nilai wajar (metode persis sama dengan bagian "Analisis konvergensi"). Akibatnya holdout H16/H16c tidak lagi bersih; uji aturan valuasi baru ke depan hanya lewat uji maju (forward). Tidak ada perubahan apa pun pada Tren 52 Minggu (H11a), paper trade, zona normal, maupun data ujinya.

### Hasil konvergensi 2021-04..2026-09 (data tesis Undervalue dibuka, jalur harga s/d 2026-10-20)
239 kejadian (185 saham), kenaikan dibutuhkan median 44%. Peluang mencapai nilai wajar: 1 bln 2,5%, 3 bln 11%, 6 bln 19%, 1 th 29%, 2 th 38%. Pembanding saham Wajar target sama: 4%, 11%, 18%, 26%, 35%.
- Kejadian 2021-2023: 1 th 20% vs pembanding 21%. Kejadian 2024-2026: 1 th 43% vs 34%, 2 th 55% vs 47%; yang sampai median 79 hari bursa.
- Yang sampai (104): median 194 hari bursa (p25/p75 62/456), sempat turun median -14%. Yang belum (135, diamati median 704 hari): kenaikan tertinggi median +21%, penurunan terdalam median -46%.
- MoS 20-35%: 1 th 38%, 2 th 50%; MoS 35-50%: 18%/28%; MoS > 50%: 16%/16%. IHSG < MA200 saat kejadian: 38% vs IHSG > MA200 25% (1 th).
- Dibanding saham Wajar dengan kebutuhan naik sama: 25-50% 39% vs 38%; 50-100% 18% vs 17%; > 100% 17% vs 4%.
Kesimpulan: status Undervalue hampir tidak menambah peluang mencapai target dibanding saham biasa dengan kenaikan sama (kecuali diskon sangat dalam, yang tetap jarang tercapai). Periode 2024-2026 lebih baik dari pembanding, 2021-2023 tidak.

## Tesis Pemburu Dividen (dikunci 2026-10-23, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Tujuan: penghasilan rutin dari dividen saham syariah, ditahan setahun. Data: dividen Yahoo (`dividends`, tanggal = ex-date, sudah disesuaikan split; 3.993 pembayaran 495 saham 2010-2026), harga `data/harga`, fundamental Mongo (2019+), DES historis (Des 2019+).
Aturan umum: rebalance setahun sekali di hari bursa terakhir Desember (t); beli open hari bursa pertama Januari, tahan sampai rebalance berikutnya. Dividen dihitung tunai dipotong pajak 10% (tidak diinvestasikan ulang di tengah tahun). Biaya fee 0,15%/0,25% + 1 tick per sisi hanya untuk saham yang masuk/keluar. Sama bobot. Universe: 2013-2019 = 217 `syariah_tickers.txt` (bias survivorship, sama seperti H11a dev); 2020+ = DES pada t. Likuid: nilai transaksi 20 hari >= `sc.MIN_VALUE` (Rp5 M), harga >= Rp50.

**H17a Dividen tinggi konsisten**: saham yang membayar dividen (ex-date) di masing-masing 3 tahun kalender sebelum t; urutkan yield 12 bulan (dividen ex-date dalam 365 hari sebelum t / close t); ambil 10 teratas (kalau kurang dari 5 calon, ambil semua).
- Pembanding: sama bobot seluruh universe likuid (dividen kena pajak sama, tanpa biaya), IHSG (harga saja, info), deposito 5%/tahun (asumsi tetap, info).
- Lulus dev 2014-2019 (portofolio tahun 2014..2019) kalau semua: (1) CAGR bersih >= pembanding; (2) rata-rata yield penghasilan bersih (dividen diterima setelah pajak / nilai beli) >= 4%/tahun; (3) yield penghasilan >= 3% di >= 80% tahun; (4) tahun terburuk tidak lebih buruk dari tahun terburuk pembanding dikurangi 5 poin. Holdout 2020-2026 dibuka sekali hanya kalau dev lulus, syarat (1)-(3).

**H17b Dividen + saringan anti-trap** (butuh TTM fundamental, jadi portofolio 2021-2026, satu uji terkunci tanpa periode dev terpisah): calon H17a yang juga lolos semua: payout TTM <= 100% (dividen 12 bln <= EPS TTM, EPS > 0); laba TTM tidak turun > 30% dibanding setahun lalu; dividen tahun kalender terakhir >= 70% tahun sebelumnya; DER <= 2 (bukan bank); arus kas operasi TTM >= total dividen 12 bulan. Ambil 10 yield tertinggi.
- Diadopsi kalau pada 2021-2026: CAGR bersih > H17a periode sama DAN tahun dengan penghasilan turun > 30% dari tahun sebelumnya lebih sedikit dari H17a DAN rata-rata yield penghasilan >= 4%.

**Analisis dividend trap (deskriptif, setelah uji)**: kejadian = saham universe likuid pada akhir tahun t (2012-2025) dengan yield 12 bulan >= 6%. Trap kalau dalam 12 bulan berikutnya total return (harga + dividen) < 0 ATAU dividen 12 bulan berikutnya < 70% dari 12 bulan sebelumnya. Dibandingkan: tingkat yield, dividen spesial (12 bln terakhir > 2x median 3 tahun sebelumnya), payout > 100%, laba turun, arus kas operasi < dividen, DER, siklikal, harga di bawah MA200, harga turun > 20% dalam 12 bulan sebelum t.

### Hasil tesis Pemburu Dividen (2026-10-23)
- Uji mesin dengan pilihan acak: wajar (UNVR 2017 dividen Jul+Nov tercatat, biaya ganti 0,4-1,1%/th).
- **H17a dev 2014-2019: GAGAL 2/4.** CAGR bersih 5,9% vs pembanding 7,0% (gagal); yield penghasilan rata-rata 4,3% vs 2,0% (lulus); penghasilan >= 3% di 5/6 tahun (lulus); tahun terburuk 2015 -38,7% vs pembanding -24,9% (gagal). Portofolio didominasi batu bara/tambang (ITMG, PTBA, ADRO, HRUM). Holdout tidak dibuka resmi.
- **H17b anti-trap 2021-2026: TIDAK diadopsi.** CAGR 4,9% vs H17a 14,9% (periode sama), penghasilan 7,6% vs 9,9%, 1 tahun penghasilan turun > 30% vs 0. Saringan membuang terutama "dividen dipotong" (47) dan "payout > 100%" (39), termasuk batu bara yang menang besar 2021-2025.
- Catatan kejujuran: hasil H17a 2021-2026 (+14,9%/th, penghasilan 9,9%/th, pembanding semua saham +0,7%) terlihat karena wajib dihitung sebagai pembanding H17b. Karena dev gagal, H17a tetap TIDAK lulus; hasil 2021-2026 bertepatan dengan boom batu bara dan tidak boleh dipakai sebagai bukti.
- Kesimpulan: strategi dividen tertinggi di IDX = taruhan siklus komoditas. Penghasilan dividen tinggi dan stabil di kedua periode (4-10%/th), tapi nilai modal ikut siklus.

### Hasil analisis dividend trap (2026-10-23, `backend/research/analisis_trap.py`)
89 kejadian yield >= 6% (40 saham), 2012-2024. Trap 65% (rugi 42%, dividen dipotong 47%), total return 12 bln median +13,2%. Trap jika ada vs tidak: dividen spesial 74% vs 55%; laba turun > 30% 73% vs 53%; arus kas < dividen 67% vs 56%; harga turun > 20% 69% vs 62%; komoditas 69% vs 61%; payout > 100% 58% vs 59%; yield > 12% 74% (median +5,8%) vs 6-8% 62%. Jumlah tanda (spesial, harga turun, < MA200, komoditas): 0: 50%, 1: 55%, 2: 65%, 3: 80%. Sampel kecil; ringkasan di `data/hasil/dividend_trap_ringkas.json` dipakai dashboard.

## Batas paper trade H11a (dikunci 2026-10-22, paper baru berjalan 1 hari tanpa trade)
**Catatan koreksi data (2026-11-02):** setelah koreksi data harga, backtest 2020+ cara paper (median 100 simulasi Monte Carlo) turun ke CAGR 20,9% (17,9..24,2%) dengan DD median -41,9% (dulu 22,8% / -38,0%); konservatif ARA/ARB 20,3% / -41,8%; dev 9,1% / -25,6%. Batas GAGAL paper -45% (ditambahkan 2026-11-01) makin dekat dengan penurunan normal. Kriteria dan zona `h11a_v1` tetap, karena dikunci sebelum koreksi. Penyebab: bar basi Yahoo yang menyembunyikan penurunan (PDPP 2024, MPMX 2022) dan aksi korporasi PACK 2026.
Tujuan: menentukan sebelum melihat hasil paper kapan H11a dianggap masih wajar, perlu diwaspadai, atau gagal.
- Sumber: trade `h11a_2020_konservatif` yang masuk portofolio (375 selesai + 4 terbuka). Kurva ekuitas harian dibangun ulang dengan cara paper: 10% ekuitas saat beli (dibatasi kas), harga pasar, biaya sama, dividen dikreditkan dipotong pajak 10%.
- Bootstrap blok 20 hari bursa dari return harian kurva itu, 5000 jalur x 500 hari, seed 20261022. Rugi beruntun: bootstrap urutan hasil trade, 5000 x 80 trade.
- Disimpan di Mongo `batas_paper` id `h11a_v1`; script `backend/paper/batas_paper.py` menolak menghitung ulang.
- WASPADA: return paper di bawah persentil 5 (mulai hari bursa ke-21), atau drawdown terdalam di bawah persentil 5, atau rugi beruntun di atas persentil 95.
- GAGAL: return di bawah persentil 1 (mulai hari ke-63), atau drawdown terdalam di bawah persentil 1, atau rugi beruntun di atas persentil 99.
- Konsekuensi GAGAL: H11a tidak dilanjutkan ke uang asli. Tidak boleh mengubah aturan lalu meneruskan paper yang sama; perubahan = hipotesis baru.
- Catatan: zona berasal dari backtest 2020-2026 yang optimis. Lolos zona tidak membuktikan edge.

Temuan saat membuat kurva harian (2026-10-22, bukan perubahan aturan): kurva gaya paper konservatif berakhir 2.95x (CAGR 17.3%, DD -40.5%), lebih rendah dari laporan bulanan 3.74x (CAGR 21.3%). Penyebab: laporan bulanan menghitung tiap trade sebagai 10% ekuitas di bulan jual, sedangkan paper memakai 10% ekuitas saat beli. Untuk trade yang ditahan lama saat ekuitas naik, cara bulanan melebih-lebihkan hasil. Selisih net per trade (rata-rata 4.05% vs 3.15% dari harga mentah) dijelaskan oleh dividen, bukan bug.

## Aturan pemakaian data spread (dikunci 2026-10-20)
- Bid/Offer penutupan dipakai untuk **mengukur** spread nyata: (Offer - Bid) / harga tengah, dicatat per kelas harga.
- Model biaya alternatif: slip per sisi = setengah spread median 20 hari per saham.
- Hasil lulus/gagal semua hipotesis lama **tetap pakai model 1 tick**. Hipotesis yang cuma lulus dengan biaya alternatif statusnya "kandidat", bukan lulus, dan wajib paper trade dulu.

## Laporan bulanan (ditambah 2026-10-20, hanya laporan, bukan kriteria)
Target user: penghasilan rutin dari trading. Jadi tiap uji juga melaporkan simulasi portofolio:
- Maksimal 5 posisi sekaligus, masing-masing 20% ekuitas. Sinyal ditolak kalau slot penuh. Kalau sinyal di hari yang sama lebih banyak dari slot, pilih skor tertinggi; kalau tidak ada skor, pilih acak (seed 7).
- Untung/rugi dicatat di bulan exit, dengan compounding.
- Dilaporkan: rata-rata dan median return bulanan, % bulan positif, bulan terburuk, drawdown maksimal (dari ekuitas akhir bulan, jadi drawdown di tengah bulan tidak terlihat), CAGR, % bulan tanpa trade.
- Ambang buat dibahas nanti (bukan kriteria lulus): bulan positif >= 65%, drawdown <= 15%.

Hasil dev (2026-10-20):
| | rata2/bulan | bulan + | bulan kosong | terburuk | DD maks | CAGR |
|---|---|---|---|---|---|---|
| H0 TP3/SL3 | -5.85% | 5% | 3% | -20.6% | -99.5% | -52% |
| H1 TP8/SL4 | -1.67% | 36% | 3% | -14.9% | -80% | -20% |
| H2 dividen | -0.43% | 30% | 32% | -9.2% | -55% | -5% |
| H2 yield>=3 | -0.01% | 16% | 65% | -3.7% | -15% | -0.2% |
| H3 pullback | -0.26% | 41% | 3% | -11.2% | -48% | -4% |
| **H4 breakout** | **+0.67%** | 36% | 31% | -12.1% | -23% | **+7.0%** |
| H5 pergantian bulan | -0.76% | 35% | 4% | -10.0% | -74% | -9% |
| H6 Lebaran | -0.06% | 3% | 92% | -3.5% | -13% | -0.8% |

## Output screener
`rekomendasi_<tanggal>.csv`, diurutkan dari peluang tertinggi: ticker, close, perkiraan entry, TP, SL, peluang, base rate hari itu, 3 fitur pendorong. Semua rekomendasi ditambahkan ke `log_rekomendasi.csv` untuk dicek maju.

## Uji maju Pemburu Dividen (dividen_v1), dikunci 2026-10-23 — DIHENTIKAN 2026-10-25 (lihat hasil H17c/H17d)

Dikunci sebelum data 2027 ada. Kode: `backend/paper/dividen_harian.py` (konstanta `ATURAN` disimpan di koleksi `batas_paper` id `dividen_v1`; modul menolak jalan kalau berubah). Tujuan: mengukur penghasilan rutin dari dividen saham syariah, bukan mengalahkan pasar.

- Mulai hari bursa pertama Januari 2027, modal Rp100 jt.
- Seleksi tiap Januari (acuan: hari bursa terakhir sebelumnya): saham DES saat itu, harga >= Rp50, nilai transaksi rata-rata 20 hari >= Rp5 M, membayar dividen di masing-masing 3 tahun kalender terakhir, urut yield 12 bulan tertinggi (sama dengan H17a), **maksimal 3 saham per sektor** (sektor Yahoo `info_saham`, kosong = sektor sendiri), 10 saham. Kalau calon < 5, ambil semua.
- Beli di open, 1/10 ekuitas per saham dibulatkan lot; yang masih terpilih tidak dijual; yang keluar dijual di open. Fee 0,15%/0,25% + 1 tick.
- Dividen tunai (Yahoo) x lot, pajak 10%, masuk kas di tanggal cair IDX (`dividen_idx`) atau ex + 18 hari. Tidak diinvestasikan ulang di tengah tahun.
- **Lulus** bila sampai 31 Des 2028: penghasilan bersih >= 4% modal awal tiap tahun, total return >= IHSG periode sama, dan drawdown maksimum tidak lebih buruk dari IHSG lebih dari 10 poin. Gagal salah satu = tidak lulus. Tidak ada varian lain.
- Catatan: simulasi diputar ulang dari awal tiap hari (deterministik); stock split hanya mengubah pembulatan lot.

## Reksa Dana & Sukuk (2026-10-23) — belum ada hipotesis yang dikunci

Section produk (bukan strategi). Data Pasardana: 269 reksa dana syariah (riwayat NAV ±1 tahun, mulai dikumpulkan harian 2026-10-23) dan 410 sukuk aktif. Skor katalog = peringkat persentil dalam kategori + mata uang yang sama, 1 tahun terakhir (pasar uang: return 60/biaya 20/AUM 20; lainnya: return 40/drawdown 25/volatilitas 15/biaya 10/AUM 10); produk < 200 hari data atau NAV beku (> 50% hari tidak berubah) tidak diberi skor. Skor ini deskriptif, BUKAN bukti produk akan tetap unggul.

Rencana uji (dikunci nanti, sebelum melihat hasilnya): **H18 persistensi** — apakah reksa dana syariah dengan skor kuartil teratas di tahun T tetap di atas median kategori di tahun T+1 (lebih sering dari 50%)? Baru boleh dijalankan setelah ada riwayat NAV >= 3 tahun (dari pengumpulan harian atau sumber riwayat panjang yang ditemukan kemudian).

## H19: paket indikator teknikal klasik (dikunci 2026-10-24 11:55, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Permintaan user: uji indikator yang umum dipakai trader IHSG dengan data yang kita punya. Sudah ada ±17 uji (H0-H18), jadi 7 hipotesis sekaligus ini sangat rawan "lulus karena kebetulan". Aturan diambil dari bentuk baku di literatur, **tanpa penyetelan parameter**, dan tidak boleh diubah setelah melihat hasil. Tidak ada varian tambahan.

Kerangka (sama dengan tahap 3 kecuali disebut lain):
- Sinyal di close hari t, saham harus `lolos` (likuid: nilai 20 hari >= Rp5 M, ATR% 1,5-5, harga >= 50, tidak ada hari volume 0 dalam 5 hari) pada hari t. Entry open t+1 (kecuali H19g).
- Stop pelindung semua hipotesis (kecuali H19g): stop awal entry - 3 x ATR14, trailing = max(stop, close tertinggi sejak entry - 3 x ATR14); close < stop -> keluar open besok.
- Exit aturan: kalau kondisi exit hipotesis terpenuhi di close hari j (j > hari entry), keluar open j+1. Batas waktu per hipotesis -> keluar di close hari ke-N setelah entry. Mana yang lebih dulu.
- Satu posisi per ticker (sinyal baru diabaikan selama posisi terbuka). Biaya sama (fee 0,15% beli + 0,25% jual + 1 tick per sisi).
- Portofolio maksimal 10 posisi @ 10%, sinyal ditolak kalau penuh, sinyal di hari yang sama dipilih acak (seed 7).
- Dev 2010-2019: daftar 217 saham (`syariah_tickers.txt`, bias survivorship; DES historis baru ada sejak Des 2019). Harga dipotong 2019-12-31.
- Holdout 2020-01-01 s/d data terakhir: universe DES historis. **Hanya dibuka untuk hipotesis yang lulus SEMUA kriteria di dev, sekali jalan.** Data 2020+ sudah pernah dipakai H11a (aturan berbeda), dicatat sebagai kelemahan.

Indikator (dihitung dari harga adjusted):
- MA50, MA200 = rata-rata sederhana close. MACD = EMA12 - EMA26, signal = EMA9 dari MACD. Stochastic %K(14) = (close - low terendah 14) / (high tertinggi 14 - low terendah 14) x 100, %D = MA3 dari %K. RSI2 = RSI Wilder periode 2. Bollinger = MA20 ± 2 x standar deviasi 20 hari, lebar = (atas - bawah) / MA20. Volume rata-rata = MA20 volume hari sebelumnya.

Sinyal (S), exit aturan (X), batas hari (N), pembanding (P = rata-rata semua tahanan open t+1 s/d close t+P dari saham lolos):
- **H19a golden cross**: S = MA50 memotong ke atas MA200 (MA50 > MA200 hari ini, <= kemarin). X = MA50 < MA200. N = 500. P = 20.
- **H19b MACD**: S = MACD memotong ke atas signal **dan** MACD > 0 **dan** close > MA200. X = MACD < signal. N = 500. P = 20.
- **H19c Stochastic**: S = %K memotong ke atas %D **dan** %D < 20 (kemarin) **dan** close > MA200. X = %K > 80. N = 20. P = 10.
- **H19d RSI(2) mean reversion (Connors)**: S = RSI2 < 10 **dan** close > MA200. X = RSI2 > 70. N = 10. P = 5.
- **H19e Bollinger squeeze breakout**: S = lebar band kemarin = terendah 120 hari **dan** close > band atas **dan** volume >= 1,5 x volume rata-rata. X = close < MA20. N = 500. P = 20.
- **H19f candlestick reversal**: S = (bullish engulfing: kemarin close < open, hari ini close > open, open <= close kemarin, close >= open kemarin; **atau** hammer: badan <= 1/3 range, ekor bawah >= 2 x badan, ekor atas <= badan, close di 1/3 atas range) **dan** low hari ini <= low terendah 20 hari sebelumnya x 1,02 **dan** volume >= volume rata-rata. Tanpa X. N = 5. P = 5.
- **H19g BSJP (beli sore jual pagi)**: S = posisi close >= 95% range hari itu (range > 0) **dan** volume >= 2 x volume rata-rata **dan** close > close kemarin. Entry **di close hari t**, exit **open t+1**, tanpa stop. P = semua tahanan close t -> open t+1 saham lolos.

Kriteria lulus (dev, lalu holdout bila dibuka), semua harus terpenuhi:
1-6. Sama dengan H3-H6/H11 (exp net > 0, di atas pembanding, bootstrap 90% batas bawah > 0, tahun positif >= 70%, tanpa 10 trade terbaik > 0, tanpa 5 ticker terbaik > 0).
7. CAGR portofolio 10 posisi > CAGR beli-tahan bobot sama semua saham universe (tanpa biaya) di periode yang sama.
8. **Tambahan karena uji ganda**: bootstrap bulanan 98% batas bawah (persentil 1) > 0.
Lulus dev + holdout = kandidat paper trade, **bukan** pengganti Follow Tren. Gagal = ditutup, tanpa variasi parameter.
Yang dilaporkan untuk semua: jumlah trade, winrate, rata-rata untung vs rugi, expectancy, profit factor, CAGR, max drawdown, bulan positif.

### Hasil H19 dev 2010-2019 (2026-10-24, dijalankan sekali, `backend/research/uji_h19.py --periode dev`): SEMUA GAGAL, holdout tidak dibuka
Beli-tahan bobot sama 217 saham: CAGR 8,1%/th. Bug RSI (naik terus = NaN, harusnya 100) diperbaiki SEBELUM uji dijalankan.
| Hipotesis | Trade | Winrate | Untung vs rugi rata2 | Exp net | Kotor | Profit factor | CAGR 10 posisi | DD | Kriteria lulus |
|---|---|---|---|---|---|---|---|---|---|
| H19a golden cross MA50/200 | 234 | 30% | +11,6% vs -7,2% | -1,57% | -0,31% | 0,69 | -3,8% | -38% | 0/8 |
| H19b MACD cross > 0 + MA200 | 1.154 | 26% | +8,3% vs -4,3% | -0,96% | +0,25% | 0,69 | -10,5% | -64% | 0/8 |
| H19c Stochastic dari < 20 + MA200 | 832 | 49% | +4,9% vs -7,3% | -1,33% | -0,07% | 0,65 | -9,9% | -63% | 0/8 |
| H19d RSI(2) < 10 + MA200 | 1.983 | 51% | +3,0% vs -4,4% | -0,64% | +0,61% | 0,70 | -11,6% | -69% | 1/8 (di atas pembanding) |
| H19e Bollinger squeeze breakout | 115 | 37% | +12,1% vs -5,3% | **+1,21%** | +2,61% | 1,37 | +1,4% | -12% | 2/8 |
| H19f engulfing/hammer di low 20 hari | 764 | 34% | +4,0% vs -3,8% | -1,15% | +0,07% | 0,54 | -8,6% | -61% | 1/8 |
| H19g BSJP | 1.041 | 19% | +2,2% vs -1,8% | -1,08% | +0,21% | 0,27 | -10,8% | -67% | 1/8 |
Catatan:
- Return kotor (sebelum biaya) hampir semuanya di sekitar 0 sampai +0,6% per trade, padahal biaya ±1,2%. Indikator klasik di saham individual IDX 2010-2019 tidak punya edge yang cukup untuk menutup biaya; sama dengan temuan H0-H6.
- Pola studi literatur terlihat: RSI/Stochastic winrate tinggi (~50%) tapi rugi rata-rata lebih besar dari untung (rasio 0,67-0,68); MACD/golden cross winrate rendah (26-30%). Bedanya, di saham individual dengan biaya nyata hasilnya negatif.
- H19a: 90% trade keluar oleh stop pelindung 3xATR sebelum death cross; ini bagian aturan yang dikunci. Versi tanpa stop / exit death cross saja = hipotesis baru pasca-hasil, tidak dijalankan.
- H19e satu-satunya expectancy positif (+1,21%), tapi hanya 115 trade, bergantung pada 10 trade terbaik (tanpa itu -1,93%), tahun positif 50%, CAGR 1,4% < 8,1%. Tidak lulus.
- Semua ditutup. Tidak ada variasi parameter.
- Cek sensitivitas biaya (2026-10-24, laporan saja, putusan TIDAK berubah): biaya nyata rata-rata per trade H19 = 1,25% (median 1,18%) = fee 0,40% + 1 tick per sisi (tick 0,31-0,67% per sisi untuk harga Rp300-8.000, 1,67% di Rp60). Kalau biaya hanya fee 0,40%: H19a -0,71%, H19b -0,15%, H19c -0,47%, H19d **+0,21%**, H19e +2,21%, H19f -0,33%, H19g -0,19%. Model 1 tick per sisi dipilih karena spread nyata terukur ±1,1-1,2 tick (data IDX, H7). Winrate sebelum biaya: H19d 63%, H19c 56%, H19g 48% (setelah biaya 51%, 49%, 19%).

## H20: filter rezim JII di atas beli-tahan (dikunci 2026-10-24, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Konteks: target baru menekankan drawdown kecil, bukan return maksimal. Uji ke-21+; hanya SATU hipotesis, tanpa varian. Draf direvisi user tiga kali sebelum dikunci.

Data & instrumen:
- Indeks JII (`^JKII`, Yahoo, sejak 3 Jul 2000) sebagai pengganti produk yang mengikuti JII. Return saat di pasar = return **close** JII harian + asumsi dividen 2,5%/th − expense ratio 2,0%/th (keduanya diakru harian).
- Harga open ^JKII TIDAK dipakai: dicek 2026-10-24, open = close kemarin di 24-31% hari (2000-2003), 21% (2009), 47% (2020), 27% (2022), 58% (2023). Close lengkap (tanpa kosong, tanpa bulan hilang).
- Return kas = bunga antarbank FRED `IRSTCI01IDM156N` (bulanan) − 1,5%/th, diakru harian. Kalau FRED belum tersedia untuk bulan tertentu, pakai BI-Rate (data BI) − 1,5%/th untuk bulan itu.

Aturan:
- Sinyal di close hari bursa terakhir tiap bulan: JII < rata-rata 10 close akhir bulan (termasuk bulan ini) → posisi berikutnya KAS; JII >= rata-rata → posisi berikutnya PASAR. Hanya bertindak kalau posisi berubah.
- Keluar (PASAR → KAS): jual di close hari bursa ke-1 bulan berikutnya, biaya **0,70%** (fee jual 0,25% + spread 1 tick 0,45%). Hari bursa ke-2 s.d. ke-4 return 0. Kas berbunga mulai hari bursa ke-5.
- Masuk (KAS → PASAR): pencairan kas mulai hari bursa ke-1 (bunga berhenti), hari bursa ke-1 s.d. ke-4 return 0, beli JII di close hari bursa ke-4, biaya **0,60%** (fee beli 0,15% + spread 1 tick 0,45%).
- Awal: sinyal pertama di akhir bulan ke-10 data (akhir Apr 2001). Sebelum sinyal pertama posisi = KAS untuk H20; beli-tahan masuk di close hari bursa pertama Mei 2001.
- Beli-tahan (pembanding): JII + dividen 2,5%/th − expense 2,0%/th, satu kali biaya masuk 0,60% di awal, tanpa perpindahan.

Periode:
- **Dev**: Mei 2001 s/d 31 Des 2014.
- **Holdout**: 1 Jan 2015 s/d **close 23 Okt 2026** (dipatok). Dibuka SEKALI, hanya kalau dev lulus semua kriteria. Posisi awal holdout = posisi H20 yang berlaku di akhir dev (sinyal tetap berjalan sejak 2001). **Penjelasan tertulis (2026-10-24, sebelum uji dijalankan):** (1) di awal holdout beli-tahan dianggap sudah memegang posisi, tanpa biaya masuk, supaya setara dengan H20 yang meneruskan posisi dari 2014; (2) CAGR, max drawdown, dan jendela bergulir holdout dihitung dari ekuitas awal Jan 2015 (puncak di-reset), bukan meneruskan dari dev. Detail lain yang disetujui user: sebelum sinyal pertama H20 di KAS; rata-rata 10 bulan termasuk close bulan berjalan; H20 hanya bertindak kalau posisi berubah.

Kriteria lulus dasar (dev dan holdout, semua harus terpenuhi):
1. Max drawdown H20 <= 2/3 x max drawdown beli-tahan.
2. CAGR H20 >= CAGR beli-tahan − 2%/th.
3. Rata-rata perpindahan <= 3 per tahun (**setiap keluar = 1 perpindahan, setiap masuk = 1 perpindahan**).
4. Jendela 5 tahun bergulir (geser per bulan): menang kalau DD H20 < DD beli-tahan **dan** CAGR H20 >= CAGR beli-tahan − 2%. Lulus kalau menang di >= 60% jendela.

Kriteria sensitivitas (masing-masing skenario **terpisah**; di tiap skenario kriteria 1-2 harus tetap lulus, dev dan holdout):
5. Return kas 0% (dividen 2,5%, expense 2,0%).
6a. Dividen 4%/th (kas dasar, expense 2,0%) — menguntungkan beli-tahan.
6b. Expense ratio 1,6%/th (kas dasar, dividen 2,5%) — menguntungkan beli-tahan.
Hanya DILAPORKAN, bukan syarat lulus: skenario gabungan terburuk (kas 0% + dividen 4% + expense 1,6%).

Hasil: lulus dev + holdout = kandidat uji maju (lapisan satelit/inti saham), bukan pengganti Follow Tren atau strategi lain. Gagal = ditutup, tanpa variasi jumlah bulan, jenis MA, jeda, atau instrumen.
Yang dilaporkan: CAGR, max DD, jumlah perpindahan per tahun, % waktu di kas, jendela menang, per tahun kalender, untuk dasar + semua skenario.

Kelemahan (dicatat sebelum uji):
- Holdout 2015+ sudah diketahui secara umum (JII melemah sejak ±2018, crash Covid Mar 2020, IHSG turun 12 bulan terakhir). Holdout tidak buta.
- JII = indeks harga; dividen hanya asumsi.
- Eksekusi di close (open tidak andal) sedikit lebih optimis daripada transaksi nyata.
- Kendaraan nyata kemungkinan **reksa dana indeks syariah** (ETF XIJI terlalu sepi, ±Rp10 jt/hari) yang punya biaya subscribe/redeem sendiri (sering 0-1%) dan pencairan T+3 s/d T+7, jadi biaya & jeda nyata bisa lebih besar dari model.
- Bunga antarbank awal 2000-an tinggi (diuji lewat kriteria 5).
- Uji ke-21+; risiko lulus karena kebetulan tetap ada.

### Hasil H20 dev Mei 2001 - Des 2014 (2026-10-24, dijalankan sekali, `backend/research/uji_h20.py --periode dev`): GAGAL (kriteria 5), holdout tidak dibuka
Sebelum uji dijalankan, dua bug kode diperbaiki tanpa melihat hasil: sinyal MA10 dihitung dari seluruh riwayat (bukan data yang sudah dipotong), dan penyaring "MA belum lengkap" (indeks tanggal vs periode). Mekanisme masuk/keluar dicek dengan data tiruan (biaya & jeda cocok hitungan manual).
| Skenario | CAGR H20 | DD H20 | CAGR beli-tahan | DD beli-tahan | Pindah/th | % tidak di pasar | Jendela menang | k1 | k2 | k3 | k4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Dasar | 20,67% | -29,7% | 21,41% | -66,5% | 1,24 (17x) | 22% | 74% (105 jendela) | ✔ | ✔ | ✔ | ✔ |
| 5. kas 0% | 18,81% | -30,3% | 21,41% | -66,5% | 1,24 | 22% | 57% | ✔ | **✘** (batas 19,41%) | | |
| 6a. dividen 4% | 22,03% | -29,0% | 23,16% | -66,2% | | | | ✔ | ✔ | | |
| 6b. expense 1,6% | 21,04% | -29,5% | 21,88% | -66,5% | | | | ✔ | ✔ | | |
| Gabungan terburuk (laporan) | 20,51% | -29,4% | 23,63% | -66,1% | | | 57% | | | | |
- Kriteria dasar 1-4 lulus semua; sensitivitas 6a dan 6b lulus; **kriteria 5 (kas 0%) gagal tipis: CAGR 18,81% vs batas 19,41% (kurang 0,60 poin)**. Artinya di dev, kemampuan H20 menyamai CAGR beli-tahan bergantung pada bunga kas tinggi awal 2000-an (antarbank Mei 2001 16,3%) — persis yang ingin dicegah kriteria 5.
- Penurunan drawdown besar dan konsisten: -29,7% vs -66,5% (krisis 2008: H20 -8,0% vs beli-tahan -55,9%). Biayanya: tertinggal di tahun pemulihan (2009 +43,6% vs +93,9%) dan whipsaw 2011-2012 (2011 -18,4% vs +1,3%; 7 perpindahan dalam 2011-2012).
- Sesuai aturan: GAGAL = ditutup, tanpa variasi jumlah bulan, jenis MA, jeda, atau instrumen. Holdout 2015+ tidak dibuka.

## H21 low volatility & H22 momentum 12-1 (dikunci 2026-10-24, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Uji ke ±36-37. Dua hipotesis dinilai **terpisah**, masing-masing dengan kriterianya sendiri. Gagal = ditutup tanpa variasi parameter. Holdout dibuka sekali, hanya untuk yang lulus semua kriteria dev, dan baru setelah user melihat hasil dev.

Cek sebelum dikunci (2026-10-24, hanya data, tanpa return strategi):
- Universe likuid (median nilai 60 hari ≥ Rp5 M, harga ≥ Rp100) akhir tahun: 2011-2017 42-61 saham, 2019 29, 2020-2026 72-129 (Rp20 M: 18-35 dev, 37-69 holdout). Karena itu ukuran portofolio proporsional, bukan angka tetap.
- Data Yahoo punya baris hari libur (31 Des 2018: 439 baris, volume 0 semua) → kalender wajib hari bursa IHSG.
- Kualitas open Yahoo: open = close kemarin 19-44% (2010-2019), 36-52% (2020-2026); open Yahoo cocok dengan OpenPrice resmi IDX di 99,6-100% hari likuid 2020-2026 (2025: Yahoo 40,6% vs IDX 40,7% open = close kemarin). Keputusan: eksekusi di open.
- Saham hilang: data Yahoo hanya berisi saham yang masih ada, jadi 0 kasus "berhenti di tengah". 10 kode DES yang pernah likuid + syariah di 2020+ tidak ada di Yahoo: TECH, ENVY, DUCK, HKMU, JSKY, PURE, CBMF (jatuh ke ±Rp50 lalu berhenti diperdagangkan 2020-2023), FREN (merger ke EXCL Apr 2025), META (suspensi 7 Nov 2023, tender offer sukarela Metro Pacific Tollways 2024), WBSA (tercatat Apr 2026). 19 kode DES lain tidak pernah ada transaksinya di data IDX (tidak relevan).

Kerangka bersama:
- Universe dev: semua kode yang pernah masuk DES 2019-2026 dan punya data Yahoo ≥ 250 hari (766 kode), dianggap syariah sepanjang dev. Holdout: DES OJK pada tanggal sinyal (`des_ojk.syariah_pada`).
- Filter di tanggal sinyal t: median nilai transaksi (close mentah × volume, 0 kalau volume 0) 60 hari bursa terakhir ≥ Rp5 M; close mentah ≥ Rp100; ≥ 250 hari data; volume > 0 di ≥ 90% dari 250 hari bursa terakhir. Tanpa filter ATR.
- Jadwal: sinyal di close hari bursa terakhir tiap bulan (kalender IHSG). Eksekusi di open hari bursa pertama bulan berikutnya. Saham yang tidak bisa ditransaksikan hari itu (volume 0, atau candle satu harga high = low dengan return ≤ -6,5% untuk jual / ≥ +6,5% untuk beli) ditunda ke open hari bisa berikutnya.
- Ukuran: N = maks(10, bulat(20% × jumlah saham lolos)). Beli peringkat ≤ N. Saham yang dipegang tetap dipegang selama peringkat ≤ 2N dan masih lolos filter + syariah; selain itu dijual. Slot kosong diisi peringkat teratas yang belum dipegang. Kalau pegangan > N (N mengecil), peringkat terburuk dijual sampai N.
- Bobot: saham baru dibeli 1/N ekuitas; kalau kas kurang, kas dibagi rata ke saham baru. Saham lama tidak diseimbangkan ulang kecuali bobot > 2/N → dipangkas ke 1/N. Sisa kas tidak berbunga.
- Biaya: fee beli 0,15% + jual 0,25% + 1 tick per sisi (fraksi IDX, harga mentah) untuk setiap transaksi nyata termasuk pemangkasan. Turnover dilaporkan.
- Harga: Yahoo adjusted (dividen masuk tanpa pajak). Holdout ditambah 10 kode di atas dari data harian resmi IDX (harga mentah; kalau OpenPrice kosong, eksekusi memakai close hari itu). Saham yang tidak pernah aktif lagi sampai akhir data dinilai 0 sejak hari terakhir aktif. FREN: nilai dibawa ke EXCL di close terakhir FREN (14 Apr 2025). META: dibekukan di Rp238 (close terakhir; harga tender tidak tercatat di data pengumuman) sejak suspensi, tidak bisa dijual di pasar reguler. Skenario META = 0 hanya dilaporkan.
- Pembanding 1: bobot sama semua saham lolos (universe dan filter sama), beli open hari rebalance, tahan sampai rebalance berikutnya, **tanpa biaya**. Pembanding 2: JII (`indeks/JKII`, close) + dividen 2,5%/th diakru harian, tanpa biaya.
- Periode: dev sinyal akhir Jan 2011, portofolio Feb 2011 s/d 31 Des 2019 (harga dipotong 2019-12-31). Holdout portofolio baru mulai rebalance Jan 2020 s/d close 23 Okt 2026 (dipatok).
- Metrik: CAGR dari ekuitas harian, max drawdown harian, volatilitas tahunan = std return bulanan × √12.
- Laporan saja: korelasi return bulanan dengan Follow Tren (dev `backtest_ekuitas` h11a_dev, holdout h11a_2020, cara paper), turnover, N rata-rata, % kas, per tahun.

**H21 low volatility.** Sinyal: standar deviasi return harian (close adjusted, kalender IHSG) 250 hari bursa terakhir; peringkat 1 = terendah.
Kriteria lulus (dev dan holdout, semua):
1. Max DD ≤ 0,75 × max DD pembanding bobot sama.
2. Max DD tidak lebih dalam dari JII.
3. CAGR bersih ≥ CAGR bobot sama − 2%/th.
4. CAGR bersih ≥ CAGR JII − 2%/th.
5. Volatilitas tahunan ≤ 0,85 × bobot sama.
6. Jendela 36 bulan bergulir (geser per bulan): menang kalau DD H21 lebih dangkal dari bobot sama **dan** CAGR H21 ≥ CAGR bobot sama − 2%. Lulus kalau menang di ≥ 60% jendela.
Sensitivitas merugikan (masing-masing terpisah; kriteria 1 dan 3 harus tetap lulus, dev dan holdout): S1 biaya 2 tick per sisi; S2 likuiditas median ≥ Rp20 M (pembanding ikut universe ini); S3 tanpa 5 ticker penyumbang terbesar (return bulanan mereka diganti return bobot sama bulan itu); S4 harga ≥ Rp200 (pembanding ikut).

**H22 momentum 12-1.** Sinyal: return close adjusted dari akhir bulan t−12 ke akhir bulan t−1 (bulan terakhir dilewati); peringkat 1 = tertinggi. Tanpa filter tren, tanpa stop.
Kriteria lulus (dev dan holdout, semua):
1. CAGR bersih > CAGR bobot sama.
2. CAGR bersih > CAGR JII + 2,5%.
3. Bootstrap blok 3 bulan (5000×, seed 7) rata-rata selisih bulanan bersih vs bobot sama: batas bawah 90% (persentil 5) > 0.
4. Selisih return tahunan vs bobot sama positif di ≥ 60% tahun kalender, **tahun parsial ikut dihitung**: dev 2011 (Feb-Des) s/d 2019 = 9 tahun, perlu ≥ 6; holdout 2020 s/d 2026 (Jan-23 Okt) = 7 tahun, perlu ≥ 5.
5. Tanpa 5 ticker penyumbang terbesar (diganti return bobot sama): CAGR tetap > bobot sama.
6. Max DD tidak lebih dalam dari max DD bobot sama − 10 poin.
Sensitivitas merugikan (terpisah; kriteria 1 dan 5 harus tetap lulus, dev dan holdout): S1 biaya 2 tick; S2 likuiditas ≥ Rp20 M; S3 harga ≥ Rp200.

Beda H22 dengan H11b (gagal) dan Follow Tren: H11b = return 120 hari desil teratas harian + close > EMA200 + trailing stop 3×ATR, maks 10 posisi, sering kas. Follow Tren = breakout absolut tertinggi 250 hari + trailing stop, maks 10 posisi, sering kas. H22 = peringkat relatif 12-1, hanya rebalance bulanan, keluar saat peringkat > 2N, selalu ±N saham.

Lulus dev + holdout = kandidat uji maju (bukan pengganti Follow Tren). Gagal = ditutup, tanpa variasi lookback, jumlah saham, buffer, atau filter.

Kelemahan (dicatat sebelum uji):
- Dev bukan point-in-time: status syariah diambil dari DES 2019-2026, saham yang delisting sebelum 2020 tidak ada di Yahoo (survivorship tidak bisa ditutup karena data IDX baru 2020+).
- Holdout H22 tidak buta: H11a (tren) sudah lulus di 2020+ dan berkorelasi dengan momentum. Holdout H21 lebih bersih, tapi kondisi pasar 2020+ umumnya diketahui.
- Pembanding bobot sama **tanpa biaya** = pilihan konservatif yang disengaja (merugikan strategi).
- Open 2011-2019 tidak bisa diverifikasi langsung ke data IDX, hanya dari polanya yang wajar.
- 10 kode tambahan holdout memakai harga mentah IDX (tanpa penyesuaian dividen); OpenPrice IDX sering kosong 2020-2024 → close dipakai untuk eksekusi kode-kode itu.
- Merger FREN → EXCL diasumsikan bernilai sama di close terakhir FREN (rasio konversi tidak ada di data).
- META dinilai di close terakhir Rp238, bukan harga tender offer (PDF tender tidak dibaca; hanya judul + link tersimpan).
- Harga adjusted Yahoo memasukkan dividen tanpa pajak 10%; JII hanya indeks harga + asumsi dividen.
- Kapasitas: saham Rp5 M/hari aman untuk modal ±Rp100 jt, tidak untuk modal besar.
- Korelasi dengan Follow Tren di dev memakai universe berbeda (217 vs 766).
- Uji ke ±36-37: risiko lulus karena kebetulan tetap ada.

### Hasil H21 & H22 dev Feb 2011 - Des 2019 (2026-10-24, dijalankan sekali, `backend/research/uji_h21_h22.py --periode dev`): KEDUANYA GAGAL (sensitivitas), holdout tidak dibuka
Sebelum uji: uji mesin dengan peringkat acak (5 seed) — tanpa biaya CAGR rata-rata 6,3% (0,4-12,2%) vs bobot sama 7,8%; dengan biaya turun ±9,4 poin, sesuai turnover acak ±710%/th × biaya. Penyusunan data holdout dicek tanpa menjalankan strategi (FREN → EXCL 14 Apr 2025, META beku 238, TECH = 0 setelah 4 Agu 2023). Rerun kedua hanya karena gagal simpan (tipe numpy), angka identik.
Universe rata-rata 58,4 saham lolos/bulan, N rata-rata 11,9, 107 rebalance. Pembanding: bobot sama CAGR 7,80%, DD -35,14%, vol 19,32%; JII + 2,5% CAGR 6,96%, DD -25,21%, vol 12,97%.

| | CAGR | Max DD | Vol | Turnover/th | Kas rata2 | Korelasi Follow Tren | Kriteria dasar | Sensitivitas |
|---|---|---|---|---|---|---|---|---|
| H21 low vol | 6,25% | -23,95% | 13,05% | 43,7% | 5,2% | 0,34 | 6/6 | S1 ✔, S2 ✘, S3 ✘, S4 ✘ |
| H22 momentum 12-1 | 18,79% | -37,37% | 24,52% | 131,6% | 4,8% | 0,65 | 6/6 | S1 ✘, S2 ✘, S3 ✔ |

H21 kriteria: (1) DD -23,95% vs batas -26,36% ✔; (2) vs JII -25,21% ✔; (3) CAGR 6,25% vs batas 5,80% ✔; (4) vs batas JII 4,96% ✔; (5) vol 13,05% vs batas 16,42% ✔; (6) 44/72 jendela = 61,1% ✔ (tipis).
H21 sensitivitas: S1 2 tick CAGR 5,93% / DD -24,23% ✔ (tipis, batas 5,80%); S2 Rp20 M DD -27,79% vs batas -25,33% ✘ (CAGR 3,81% vs 1,57% ✔); S3 tanpa TLKM, ICBP, JSMR, UNVR, KLBF: CAGR 3,53% vs batas 5,80% ✘, DD bulanan -30,25% vs -24,01% ✘; S4 harga ≥ Rp200 CAGR 5,30% vs batas 6,15% ✘.
H22 kriteria: (1) 18,79% vs 7,80% ✔; (2) vs batas 9,46% ✔; (3) bootstrap p5 +0,192%/bln ✔; (4) 7/9 tahun ✔ (kalah 2015 dan 2019); (5) tanpa NIKL, BRPT, SMBR, TKIM, AKRA 9,11% vs 7,80% ✔; (6) DD -37,37% vs batas -45,14% ✔.
H22 sensitivitas: S1 2 tick CAGR 17,15% ✔ tapi kriteria 5 tanpa 5 terbaik 7,73% vs 7,80% ✘ (kurang 0,07 poin); S2 Rp20 M CAGR 7,25% vs 3,57% ✔ tapi tanpa BRPT, AKRA, PTPP, INKP, CPIN -1,37% vs 3,57% ✘, DD -47,37%; S3 harga ≥ Rp200 CAGR 22,92% ✔, tanpa 5 terbaik 13,54% ✔.
Per tahun H21 / H22 / bobot sama: 2011 9,9 / 36,9 / 13,1; 2012 16,0 / 26,6 / 14,3; 2013 11,0 / 13,6 / -4,0; 2014 18,2 / 37,2 / 24,7; 2015 -11,3 / -25,9 / -22,6; 2016 10,4 / 59,7 / 31,2; 2017 8,5 / 33,5 / 10,0; 2018 -5,3 / 29,1 / 12,8; 2019 2,0 / -15,8 / 0,2.

Catatan:
- H21: drawdown memang lebih dangkal (-24% vs -35%) dan volatilitas jauh lebih rendah, tapi hasilnya bergantung pada lima saham besar defensif (TLKM, ICBP, JSMR, UNVR, KLBF). Tanpa mereka, CAGR jatuh ke 3,5% dan drawdown malah lebih dalam. Di universe Rp20 M drawdown-nya tidak cukup dangkal. Tertinggal di 2016 (+10% vs +31%) dan 2018 (-5% vs +13%).
- H22: angka dasar kuat (18,8% vs 7,8%, lulus semua 6 kriteria), tapi rapuh: dengan biaya 2 tick, tanpa 5 pemenang terbesar hasilnya sudah di bawah bobot sama, dan di universe likuid Rp20 M tanpa 5 pemenang hasilnya negatif. Korelasi dengan Follow Tren 0,65 → sumber keuntungannya mirip (sedikit saham yang naik besar), jadi kalaupun lulus tidak banyak menambah diversifikasi.
- Sesuai aturan: GAGAL = ditutup, tanpa variasi lookback, jumlah saham, buffer, atau filter. Holdout 2020-2026 tidak dibuka.
- **Pembaruan angka karena koreksi data harga 2026-11-02 (bukan perubahan aturan; vonis tetap GAGAL).** Bobot sama dev 7,80% → 6,28% (laba palsu MAPI Mei 2018 hilang). H21: CAGR 6,18%, kriteria dasar 6/6, sensitivitas 2/4 (S1 ✔, **S4 harga ≥ Rp200 berbalik lulus** 5,30% vs batas 4,60%; S2 ✘ DD -27,79% vs -25,33%; S3 ✘ tanpa 5 saham 2,77% vs batas 4,27%). H22: CAGR 18,79%, kriteria 5 tanpa 5 terbaik 8,60% vs 6,27%, sensitivitas 2/3 (**S1 biaya 2 tick berbalik lulus** 7,21% vs 6,27%; S2 ✘ -1,37% vs 3,57%; S3 ✔ 12,99% vs 6,60%). Hasil lama di `hasil_riset/h2122_dev_pra_koreksi_20261102`.

## H23: dual momentum JII / emas / kas (dikunci 2026-10-25, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Konteks: hasil brainstorming literatur 2026-10-25 (Antonacci "Global Equity Momentum"; Hurst, Ooi & Pedersen 2017 "A Century of Evidence on Trend-Following"). Satu hipotesis, tanpa varian. Disetujui user 2026-10-25 dengan lencana **pasca hasil**: H23 dekat dengan H20 (yang gagal dan ditutup "tanpa variasi instrumen"), data JII 2001-2014 sudah terlihat di H20 dev, dan 2020-2026 sudah terlihat di eksplorasi 2020+. Karena itu hasilnya bukti lemah; lulus = kandidat uji maju saja, bukan diadopsi. Biaya emas 2% pulang-pergi dipilih user sebelum uji.

Cek data sebelum dikunci (2026-10-25, hanya kelengkapan data, tanpa return strategi apa pun):
- Emas `GC=F` (Yahoo, USD/troy ons) lengkap sejak 2001 (tanpa celah > 5 hari).
- Kurs `IDR=X` (Yahoo, `kurs/USD`) kotor: 12 titik salah (×0,1 pada 1 Nov 2010 & 7 Feb 2012, nilai macet 9.612 Okt-Des 2013, 5 Nov 2008, 26 Des 2024) dan celah 214 hari (Jun-Des 2003), 26 hari (Agt 2008), 10 hari (Sep 2002). Setelah dibersihkan (aturan di bawah, median 21 hari), akhir bulan cocok dengan FRED `CCUSSP02IDM650N` (kurs akhir periode, sampai Des 2023): 245 dari 271 bulan beda ≤ 1%, 2 bulan > 3%, maks 3,3%.

Data & instrumen:
- **JII**: sama persis dengan H20 (close `indeks/JKII` + dividen 2,5%/th − expense 2,0%/th diakru harian; biaya masuk 0,60%, keluar 0,70%).
- **Emas (rupiah)**: close `GC=F` × kurs USD/IDR. Kurs: close `IDR=X` dibuang bila menyimpang > 5% dari median 21 hari bursa (berpusat; semula 11, diubah 2026-10-25 sebelum uji karena nilai macet 9.612 di Nov-Des 2013 muncul 6 dari 11 hari sehingga lolos); celah > 7 hari kalender diisi interpolasi log-linear lewat titik akhir bulan FRED di dalam celah. Biaya emas **1% beli + 1% jual** (2% pulang-pergi), tanpa biaya simpan.
- Tanggal emas: nilai emas untuk hari bursa IDX t = nilai emas-rupiah terakhir yang bertanggal **sebelum** t (emas AS & kurs ditutup setelah IDX tutup; mencegah melihat masa depan).
- **Kas**: sama dengan H20 (bunga antarbank FRED `IRSTCI01IDM156N` − 1,5%/th; BI-Rate bila FRED belum ada).
- Kalender: hari bursa JII.

Aturan:
- Sinyal di close hari bursa terakhir tiap bulan: hitung return 12 bulan (close akhir bulan ini / close akhir bulan yang sama tahun lalu) dari indeks total return model masing-masing: JII (dengan dividen − expense), emas-rupiah, kas (bunga − 1,5% berbunga majemuk). Pegang aset dengan return 12 bulan **tertinggi** (kalau kas tertinggi → kas). Hanya bertindak kalau aset berubah.
- Perpindahan A → B (mengikuti mekanisme H20): hari bursa ke-1 bulan berikutnya: kalau A berisiko, A ikut return hari itu lalu dijual di close (biaya jual A); kalau A kas, bunga berhenti dan return 0. Hari ke-2 s.d. ke-4 return 0. Close hari ke-4: beli B (biaya beli B) kalau B berisiko; kalau B kas, bunga mulai hari ke-5.
- Awal: emas-rupiah ada sejak 28 Jun 2001 → sinyal pertama akhir Jun 2002. Sebelum sinyal pertama = kas.
- **Pembanding 1, beli-tahan JII**: seperti H20 (masuk close hari bursa ke-1 Jul 2002, biaya 0,60%).
- **Pembanding 2, campuran tetap 50% JII + 50% emas**: masuk close hari bursa ke-1 Jul 2002 (biaya beli masing-masing), diseimbangkan ulang ke 50/50 di close hari bursa pertama tiap Januari, biaya per sisi sesuai aset atas nilai yang dipindah.

Periode:
- **Dev**: Jul 2002 s/d 31 Des 2014.
- **Holdout**: 1 Jan 2015 s/d close 23 Okt 2026 (dipatok). Dibuka SEKALI, hanya kalau dev lulus semua kriteria dan setelah user melihat hasil dev. Posisi H23 diteruskan dari akhir dev; kedua pembanding dianggap sudah memegang posisi tanpa biaya masuk; CAGR, DD, jendela dihitung dari ekuitas awal Jan 2015 (puncak di-reset).

Kriteria lulus dasar (dev dan holdout, semua harus terpenuhi):
1. Max drawdown H23 ≤ 2/3 × max drawdown beli-tahan JII.
2. CAGR H23 ≥ CAGR beli-tahan JII − 2%/th.
3. Bukan cuma diversifikasi: CAGR H23 ≥ CAGR campuran 50/50 **dan** CAGR/|max DD| H23 ≥ CAGR/|max DD| campuran 50/50.
4. Rata-rata perpindahan ≤ 4 per tahun (setiap pergantian aset = 1).
5. Jendela 5 tahun bergulir (geser per bulan) vs beli-tahan JII, definisi sama dengan H20 kriteria 4: menang di ≥ 60% jendela.

Kriteria sensitivitas (skenario terpisah; di tiap skenario kriteria 1, 2, 3 harus tetap lulus, dev dan holdout):
6. Return kas 0%.
7. Biaya emas 4% pulang-pergi (2% + 2%), juga untuk campuran 50/50.
8. Dividen JII 4%/th (menguntungkan beli-tahan dan campuran).
Hanya DILAPORKAN: gabungan terburuk (kas 0% + emas 4% + dividen 4%).
Klarifikasi (2026-10-25, ditulis saat menyusun kode, sebelum uji dijalankan): di tiap skenario, indeks total return untuk sinyal memakai asumsi skenario itu (kas 0% → return 12 bulan kas = 0; dividen 4% → indeks JII memakai dividen 4%). Biaya tidak masuk indeks sinyal.

Yang dilaporkan: CAGR, max DD harian, perpindahan/th, % waktu di tiap aset, jendela menang, per tahun kalender, daftar perpindahan.
Hasil: lulus dev + holdout = kandidat uji maju (lapisan satelit/inti), bukan diadopsi. Gagal = ditutup, tanpa variasi lookback, aset, biaya, atau aturan pindah.

Kelemahan (dicatat sebelum uji):
- Pasca hasil (lihat konteks). Holdout tidak buta: emas naik besar 2019-2026 dan JII melemah sejak ±2018 sudah diketahui umum, jadi holdout cenderung menguntungkan H23.
- Emas: harga futures AS × kurs, bukan harga emas digital/Antam sebenarnya; selisih jual-beli nyata bisa berubah-ubah.
- Kurs 2003 (6 bulan) dan Agt 2008 hasil interpolasi, volatilitas harian di celah itu hilang.
- JII = indeks harga; dividen asumsi; eksekusi di close sedikit optimis (sama dengan H20).
- Uji ke ±38; risiko lulus karena kebetulan tetap ada.

### Hasil H23 dev Jul 2002 - Des 2014 (2026-10-25, dijalankan sekali, `backend/research/uji_h23.py --periode dev`): GAGAL, holdout tidak dibuka
Sebelum uji dijalankan: mekanisme (biaya, jeda 4 hari, beli-tahan, campuran 50/50, penyeimbangan Januari) dicek dengan data tiruan dan cocok persis dengan hitungan manual; data kurs/emas dicek tanpa return strategi. Satu error kode (baris sinyal tanpa riwayat 12 bulan) diperbaiki sebelum hasil pertama keluar.
| Skenario | CAGR H23 | DD H23 | CAGR beli-tahan | DD beli-tahan | CAGR 50/50 | DD 50/50 | Pindah/th | % JII / emas / kas | Jendela menang | k1 | k2 | k3 | k4 | k5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dasar | 13,51% | -27,2% | 19,80% | -66,5% | 18,86% | -40,2% | 1,44 (18×) | 54 / 28 / 12 | 37% (91) | ✔ | ✘ | ✘ | ✔ | ✘ |
| 6. kas 0% | 9,42% | -34,5% | 19,80% | -66,5% | 18,86% | -40,2% | 2,00 | 57 / 32 / 4 | | ✔ | ✘ | ✘ | | |
| 7. emas 4% | 12,23% | -28,6% | 19,80% | -66,5% | 18,73% | -40,2% | 1,44 | | | ✔ | ✘ | ✘ | | |
| 8. dividen 4% | 14,81% | -27,1% | 21,52% | -66,2% | 19,74% | -40,1% | 1,60 | | | ✔ | ✘ | ✘ | | |
| Gabungan terburuk (laporan) | 8,17% | -38,1% | 21,52% | -66,2% | 19,61% | -40,1% | 2,16 | | 32% | | | | | |
- Lulus kriteria 1 (DD) dan 4 (perpindahan); gagal 2, 3, 5 dan semua sensitivitas. CAGR tertinggal ±6%/th dari beli-tahan JII dan ±5%/th dari campuran 50/50.
- Per tahun: H23 terlambat masuk lagi setelah kejatuhan (2009 -1,6% vs JII +93,9%; 2006 +6,1% vs +56,6%; 2005 +6,7% vs +22,4%). Return 12 bulan bereaksi lambat, dan pindah ke emas di 2008 masih rugi dibanding diam di emas.
- Campuran 50/50 (pembanding, bukan hipotesis): CAGR 18,86% dengan DD -40,2% vs beli-tahan JII 19,80% / -66,5%. **Catatan, bukan bukti**: ini hanya pembanding dev; tidak diuji sebagai hipotesis.
- Sesuai aturan: GAGAL = ditutup, tanpa variasi lookback, aset, biaya, atau aturan pindah. Holdout 2015+ tidak dibuka.

## H17c uji silang dividen_v1 di saham non-syariah & H17d dividen_v1 syariah historis (dikunci 2026-10-25, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Konteks: user tidak mau menunggu uji maju 2027-2028 (2026-10-25). Data syariah 2014-2026 sudah terpakai (H17a dev gagal 2014-2019; 2021-2026 terlihat lewat H17b; aturan `dividen_v1` "maks 3 per sektor" dibuat setelah melihat dominasi batu bara). Disepakati user: **H17c = bukti utama** (data yang tidak pernah dipakai membentuk aturan dividen), **H17d = pelengkap** berlencana pasca hasil. Uji maju `dividen_v1` tetap berjalan, tidak diubah (`paper_dividen_*` & `batas_paper` tidak disentuh; sidik dicocokkan sebelum/sesudah).

Aturan yang diuji: **persis `dividen_v1`** (`backend/paper/dividen_harian.py`: fungsi `simulasi` dipakai apa adanya, hanya tanggal mulai dan daftar universe yang diganti di dalam proses uji): seleksi tiap Januari (acuan hari bursa terakhir sebelumnya), harga ≥ Rp50, nilai transaksi rata-rata 20 hari ≥ Rp5 M, membayar dividen di masing-masing 3 tahun kalender terakhir, urut yield 12 bulan, maks 3 saham per sektor (sektor Yahoo; kosong = sektor sendiri), 10 saham (calon < 5 → semua); beli open 1/10 ekuitas dibulatkan lot; yang masih terpilih tidak dijual; dividen tunai × lot, pajak 10%, cair di tanggal bayar IDX atau ex + 18 hari; tidak diinvestasikan ulang di tengah tahun; fee 0,15%/0,25% + 1 tick. Modal Rp100 jt.

Universe:
- **H17c (non-syariah)**: 153 kode di koleksi `harga` yang tidak pernah masuk DES OJK (2019-2026) dan tidak ada di daftar 217 syariah (bank, asuransi, pembiayaan, dll.). 114 punya sektor Yahoo.
- **H17d (syariah)**: sama dengan H17a: 2014-2019 daftar 217 syariah (bias: status syariah dari masa kini), 2020+ DES OJK pada tanggal acuan.

Periode: hari bursa pertama Jan 2014 s/d 23 Okt 2026 (dipatok). Tahun penuh 2014-2025 (12 tahun); 2026 parsial (dilaporkan, tidak dihitung di kriteria per tahun, ikut di CAGR & DD).

Pembanding:
- IHSG (indeks harga, tanpa dividen), harian.
- Bobot sama semua saham lolos likuiditas di universe yang sama (cara H17a: beli open hari bursa pertama tiap tahun, tahan setahun, dividen setelah pajak, **tanpa biaya**).

Kriteria lulus (tiap uji dinilai terpisah, semua harus terpenuhi):
1. Penghasilan bersih (dividen setelah pajak, menurut tanggal ex / ekuitas awal tahun) rata-rata ≥ 4%/th **dan** ≥ 3% di ≥ 80% tahun penuh.
2. CAGR total bersih ≥ CAGR IHSG **dan** ≥ CAGR pembanding bobot sama.
3. Max drawdown harian tidak lebih buruk dari max drawdown IHSG lebih dari 10 poin.
4. Return tahun terburuk (tahun penuh) ≥ tahun terburuk pembanding bobot sama − 5 poin.
Laporan saja: per tahun (penghasilan %, total %, IHSG, pembanding, saham), jumlah saham rata-rata, % kas menganggur, kontribusi sektor.

Arti hasil:
- H17c lulus = aturan dividen_v1 bekerja juga di kelompok saham yang sama sekali berbeda → bukti bahwa polanya umum, bukan kebetulan batu bara. Bersama H17d lulus, lapisan Dividen boleh dipertimbangkan user untuk uang nyata kecil sebelum uji maju selesai (keputusan user, bukan otomatis).
- H17c gagal = aturan tidak terbukti umum; H17d (apa pun hasilnya) tidak cukup sendirian karena pasca hasil.
- Tanpa varian: tidak ada perubahan jumlah saham, batas sektor, syarat 3 tahun, atau universe setelah melihat hasil.

Kelemahan (dicatat sebelum uji):
- Non-syariah tidak bisa dibeli (bukan instrumen syariah); ini hanya uji apakah polanya umum.
- Survivorship: `harga` (Yahoo) hanya berisi saham yang masih ada.
- Universe non-syariah kecil dan didominasi bank; batas 3 per sektor bisa membuat portofolio < 10 saham (sisa jatah jadi kas tanpa bunga, sesuai aturan).
- H17d: 2014-2019 status syariah dari masa kini; 2021-2026 sudah terlihat; batas sektor dibuat setelah lihat data.
- Pengetahuan umum: bank besar Indonesia naik kuat 2014-2022 (diketahui sebelum uji).
- Uji ke ±39-40.

### Hasil H17c & H17d (2026-10-25, dijalankan sekali, `backend/research/uji_h17cd.py semua`): KEDUANYA GAGAL
Sidik `paper_*` & `batas_paper` sama sebelum/sesudah uji.
| | H17c non-syariah | H17d syariah (pasca hasil) |
|---|---|---|
| CAGR | 1,07% | 6,37% |
| IHSG / bobot sama | 1,90% / 0,35% | 1,90% / 4,26% |
| Max DD harian | -48,4% (IHSG -45,3%) | -52,7% (IHSG -45,3%) |
| Penghasilan rata-rata (tahun penuh) | 2,35%/th, ≥ 3% di 17% tahun | 5,63%/th, ≥ 3% di 75% tahun |
| Tahun terburuk | 2024 -21,6% (pembanding terburuk -14,5%) | 2015 -32,9% (pembanding -24,9%) |
| Saham rata-rata / kas rata-rata | 6,9 / 24,9% | 10,0 / 15,4% |
| Kriteria 1 / 2 / 3 / 4 | ✘ / ✘ / ✔ / ✘ (1/4) | ✘ / ✔ / ✔ / ✘ (2/4) |
- H17c: universe non-syariah likuid kecil (11-41 saham), didominasi bank + rokok + menara; batas 3 per sektor membuat portofolio rata-rata 6,9 saham dan ±25% ekuitas menganggur sebagai kas, sehingga penghasilan per ekuitas hanya 1,4-3,3%. Aturan dividen_v1 tidak terbukti umum.
- H17d: penghasilan tinggi di 2019-2025 (4,6-11,6%, didorong batu bara), tapi 2015-2017 hanya 2,4-2,8% (gagal syarat 80%); 2015 -32,9% dan DD -52,7%. Total return mengalahkan IHSG dan bobot sama, tapi itu pasca hasil (bukan bukti).
- Sesuai aturan: tanpa varian.
- **Keputusan user 2026-10-25: uji maju dividen_v1 DIHENTIKAN** karena H17c & H17d gagal. Data `paper_dividen_*` (status menunggu + pratinjau) dan `batas_paper/dividen_v1` diarsip ke `swing.arsip_paper_dividen` lalu dihapus; job `paper_dividen` dan jadwalnya dicabut; tab Uji maju dihapus. Kode simulasi dipindah ke `backend/research/dividen_v1.py` (dipakai `uji_h17cd.py`). Catatan kejujuran: H17c/H17d gagal tidak membuktikan dividen_v1 pasti gagal ke depan; penghentian adalah keputusan user berdasarkan bukti data lama.
- **Lapisan Pendapatan kosong** (catatan 2026-11-08): H17a/c/d gagal dan uji maju dihentikan 25 Okt 2026; lapisan ini tidak berisi strategi sampai ada yang lulus uji.

## H24: efek Ramadan pada JII — dihapus dari katalog (2026-10-28, permintaan user)
Pernah dikunci dan diuji sekali (2026-10-28): JII hanya selama Ramadan vs kas, dev Ramadan 2001-2014 GAGAL 4/6 (rata-rata bersih +0,74%/Ramadan, tapi tidak lebih baik dari jendela acak, p 0,30; tanpa 2007 negatif). Holdout tidak dibuka. Detail, kode, dan hasil dihapus atas permintaan user; baris ini disimpan supaya jumlah uji tetap tercatat dan ide ini tidak diuji ulang tanpa sadar.

## H25: pembelian saham oleh orang dalam (dikunci 2026-10-29, sebelum harga/return setelah sinyal dihitung)
Permintaan user (2026-10-28/29) setelah brainstorming literatur. Sumber ide: Cohen, Malloy & Pomorski (2012, *Journal of Finance*, "Decoding Inside Information"): pembelian direksi/komisaris yang **tidak rutin** diikuti return lebih tinggi beberapa bulan; juga Lakonishok & Lee (2001), Seyhun (1986). Bukti di negara berkembang campuran. Uji ke-42 (termasuk H24 yang dihapus); hanya SATU hipotesis, tanpa varian.

Pertanyaan: saham syariah likuid yang baru dibeli direksi/komisarisnya sendiri (atas inisiatif sendiri), apakah dalam 3 bulan berikutnya naik lebih tinggi daripada saham syariah likuid lain di periode yang sama, setelah biaya?

Data (sudah diambil 2026-10-28, sebelum hipotesis ini ditulis; yang sudah dilihat hanya jumlah laporan dan teks tujuan, BELUM ada harga/return):
- `lab_data.kepemilikan_lapor`: formulir elektronik IDX "Pemegang Saham Tertentu" (3 Jul 2023 - 27 Nov 2025, `format: erep`) + format standar KSEI (sejak 28 Nov 2025). Waktu terbit = `tgl` (jam pengumuman IDX).
- Harga `harga/<kode>` (Yahoo, harian final): open/close disesuaikan dividen & split untuk return, harga mentah untuk fraksi tick.
- Universe: saham syariah DES (`des_ojk.syariah_pada`) + likuid: nilai transaksi rata-rata 20 hari ≥ **Rp1 M**, harga ≥ Rp50, tanpa hari volume nol dalam 5 hari; **tanpa syarat ATR**. Dihitung di hari sinyal = hari bursa terakhir ≤ tanggal terbit laporan.
- **Perubahan draf sebelum dikunci (2026-10-29, keputusan user)**: draf memakai likuiditas ala H11a (Rp5 M + ATR 1,5-5%). Hitungan JUMLAH sinyal saja (tanpa harga sesudah sinyal/return) memberi dev 48 trade (< syarat 60) → syarat diganti Rp1 M tanpa ATR (dev 98, holdout ±179 sebelum dipotong jendela). ATR dipakai H11a untuk stop 3×ATR; H25 tanpa stop. Batas Rp100 jt, masa tahan, dan kriteria tidak berubah.

Kejadian (sinyal), semua harus terpenuhi:
1. Laporan dengan `orang_dalam = True` (Direksi atau Dewan Komisaris). Pemegang ≥5% yang bukan direksi/komisaris tidak dihitung.
2. Minimal satu baris transaksi berjenis "Pembelian" dengan harga > 0 dan jumlah > 0.
3. Pembeli bersih di laporan itu: nilai beli − nilai jual ≥ **Rp100 juta** (jumlah × harga).
4. **Bukan pembelian rutin/wajib**: teks tujuan semua baris pembelian TIDAK mengandung (huruf kecil): `pojk`, `peraturan`, `remunerasi`, `tantiem`, `bonus`, `mesop`, `esop`, `msop`, `lti`, `program`, `repo`, `repurchase`, `tabungan saham`, `menabung`, `hibah`, `waris`, `kewajiban`, `pemenuhan`, `hmetd`, `right`, `konversi`, `waran`, `dividen`, `tender`, `penjatahan`, `ipo`, `penawaran umum`, `jaminan`, `gadai`.
5. Kualitas: kalau saldo bisa dicek (semua baris beli/jual), saham sebelum + beli − jual harus = saham sesudah (selisih ≤ 0,1%); kalau tidak cocok, laporan dibuang.
6. Saham lolos universe di hari sinyal.

Transaksi:
- Masuk: **open hari bursa pertama SETELAH tanggal terbit laporan** (bukan tanggal transaksi orang dalam; tidak mengintip). Biaya beli 0,15% + 1 tick.
- Keluar: close hari bursa ke-63 sejak masuk (±3 bulan). Biaya jual 0,25% + 1 tick. Tanpa stop. Kalau tidak ada harga di hari keluar (suspensi), pakai close terakhir yang ada sebelumnya.
- Satu posisi per saham: laporan baru untuk saham yang posisinya masih terbuka diabaikan. Tidak ada batas jumlah posisi (uji per trade).

Ukuran per trade:
- Return kotor = close keluar / open masuk − 1 (harga disesuaikan). Return bersih = setelah biaya di atas.
- Pembanding = rata-rata return kotor semua saham universe di hari sinyal yang sama (masuk di open hari berikutnya), jendela sama (open masuk → close hari ke-63), tanpa biaya.
- Excess bersih = return bersih − pembanding.

Periode:
- **Dev**: laporan terbit 3 Jul 2023 s/d 31 Des 2024 (harga keluar bisa sampai ±Apr 2025).
- **Holdout**: laporan terbit 1 Jan 2025 s/d laporan terakhir yang jendela 63 harinya selesai sebelum data harga terakhir saat uji. Dibuka SEKALI, hanya kalau dev lulus semua kriteria.

Kriteria lulus (dev, lalu holdout bila dibuka; semua harus terpenuhi):
1. Jumlah trade ≥ 60 (kurang dari itu = GAGAL karena data tidak cukup).
2. Rata-rata return bersih per trade > 0.
3. Rata-rata excess bersih per trade > 0.
4. Uji acak: rata-rata return kotor > persentil 95 dari 10.000 set acak (tiap trade diganti saham acak lain dari universe hari sinyal yang sama, jendela sama; seed 25).
5. Bootstrap 90% (blok per bulan masuk, 10.000 kali): batas bawah rata-rata excess bersih > 0.
6. Tanpa 10 trade terbaik: rata-rata excess bersih tetap > 0.
7. Tanpa 5 emiten terbaik (menurut total excess): rata-rata excess bersih tetap > 0.
8. Kuartal masuk (yang punya ≥ 5 trade) dengan rata-rata excess bersih > 0 ≥ 60%.

Hanya dilaporkan (bukan syarat): tahan 21 dan 126 hari; tanpa batas Rp100 juta; batas ≥ Rp500 juta; termasuk pemegang ≥5% bukan direksi/komisaris; biaya 2 tick per sisi; hasil terpisah Direksi vs Komisaris; jumlah kejadian yang dibuang per aturan 2-6.

Hasil: lulus dev + holdout = kandidat uji maju (paper) sebagai strategi kedua di lapisan Apresiasi modal, bukan uang nyata langsung. Gagal = ditutup, tanpa variasi batas nilai, daftar kata, masa tahan, atau universe.

Kelemahan (dicatat sebelum uji):
- Periode pendek: dev 18 bulan, holdout ±18 bulan; satu kondisi pasar bisa mendominasi (IHSG/JII turun 2025-2026 sudah diketahui umum, sebagian dikendalikan oleh pembanding hari yang sama).
- Tidak bisa memakai definisi "rutin" Cohen dkk. (bertransaksi di bulan yang sama 3 tahun berturut-turut) karena data baru sejak Jul 2023; diganti daftar kata tujuan.
- Format laporan berganti di tengah holdout (28 Nov 2025).
- 3,5% laporan lama saldonya tidak cocok (salah isi emiten); dibuang lewat aturan 5.
- Data diambil sendiri dari PDF; salah baca kecil mungkin tersisa.
- Banyak pembelian orang dalam terjadi di saham kecil yang tidak lolos likuiditas; sinyal yang tersisa sedikit (dev ±98).
- Syarat likuiditas diubah setelah melihat jumlah sinyal (bukan return); dicatat di atas.
- Kalau saham tidak punya harga open di hari masuk (suspensi), kejadian dibuang dan jumlahnya dilaporkan.

### Hasil H25 dev laporan Jul 2023 - Des 2024 (2026-10-29, dijalankan sekali, `backend/research/uji_h25.py --periode dev`): GAGAL 5/8, holdout tidak dibuka
Sebelum data harga asli dipakai, mesin dicek dengan harga tiruan (tanggal kejadian asli): harga datar → bersih -1,391%/trade = hitungan biaya manual, semua kriteria gagal; efek palsu +0,15%/hari di saham orang dalam → terdeteksi, semua lulus.
Kejadian: 5.451 laporan direksi/komisaris → dibuang 2.119 tanpa pembelian, 454 rutin/wajib, 91 saldo tidak cocok; dari sisa kejadian dev 392 tidak lolos universe, 189 posisi masih terbuka → **98 trade, 64 emiten**.

| Kriteria | Hasil | |
|---|---|---|
| 1. Trade ≥ 60 | 98 | ✔ |
| 2. Bersih > 0 | +8,04%/trade | ✔ |
| 3. Excess bersih > 0 | +6,07% (pembanding +1,97%; **median excess -2,81%**, menang 47%) | ✔ |
| 4. Kotor > p95 acak | +9,79% vs +8,29% (median acak +1,50%, p 0,033) | ✔ |
| 5. Bootstrap 5% > 0 | -1,28% | **✘** |
| 6. Tanpa 10 trade terbaik > 0 | -6,27% | **✘** |
| 7. Tanpa 5 emiten terbaik > 0 | -3,46% (tanpa CUAN, PTRO, SSIA, RAJA, LABA) | **✘** |
| 8. Kuartal menang ≥ 60% | 4/6 | ✔ |

Per kuartal masuk (excess bersih): 2023Q3 -0,50 (19 trade), Q4 +14,90 (13), 2024Q1 +16,70 (11), Q2 +3,56 (18), Q3 -3,78 (17), Q4 +11,37 (20).
Laporan saja: tahan 21 hari excess +2,73% (131 trade); tahan 126 hari +4,06% (81); tanpa batas nilai +6,55% (119); batas ≥ Rp500 jt +7,81% (76); biaya 2 tick +4,78%; termasuk pemegang ≥5% +2,12% (154); **Direksi +0,27% (66) vs Dewan Komisaris +18,03% (32)**.
- Rata-rata bagus tapi tidak tahan uji: separuh lebih trade kalah dari pembanding (median -2,81%), dan hasil bergantung pada segelintir saham yang melonjak di 2024 (CUAN/PTRO grup Barito, RAJA, SSIA, LABA). Tanpa 10 trade terbaik rata-ratanya -6,27%.
- Selisih Komisaris vs Direksi menarik tapi BUKAN bukti (32 trade, diduga terpusat di saham grup yang sama, dan dilihat setelah hasil). Tidak boleh dijadikan varian baru tanpa hipotesis baru + data baru.
- Sesuai aturan: GAGAL = ditutup, tanpa variasi batas nilai, daftar kata, masa tahan, universe, atau jabatan. Holdout 2025-2026 tidak dibuka.

## H26: Follow Tren dengan batas jual dirapatkan setelah untung besar (dikunci 2026-11-01, sebelum kode uji dibuat dan sebelum hasil aturan ini dihitung)
Permintaan user 2026-11-01 setelah melihat eksplorasi MFE/MAE trade backtest H11a (bukan bukti): pemenang rata-rata hanya membawa pulang ±45% dari untung tertingginya (median 2020+: sempat +43%, dijual +19%). TP tetap (+5% s/d +50%) dan cut loss ketat (-3/-5/-7%) sudah terlihat kalah di semua data saat eksplorasi, jadi TIDAK diuji (sudah diketahui hasilnya). Satu hipotesis, tanpa varian pilihan. Lencana **pasca hasil**: idenya muncul dari data MFE, dan semua data 2010-2026 sudah pernah dibuka untuk H11a, jadi tidak ada holdout bersih. Lulus = paling jauh kandidat uji maju; paper H11a tetap berjalan dengan aturan lama, tidak diganti.

Pertanyaan: kalau batas jual (trailing stop) dirapatkan dari 3×ATR14 ke 2×ATR14 setelah posisi untung besar, apakah Follow Tren menyimpan lebih banyak untung dari puncak tanpa kehilangan trade besarnya, sehingga hasil portofolio lebih baik?

Aturan (semua sama dengan H11a kecuali butir keluar):
- Universe, sinyal (close ≥ close tertinggi 250 hari sebelumnya), masuk open besok, stop awal entry − 3×ATR14, maks 10 posisi @10% ekuitas, pemilihan acak bila sinyal > slot, batas 500 hari, biaya ±1,2% pulang-pergi: sama persis dengan H11a.
- Keluar: trailing = max(stop, close tertinggi sejak entry − M×ATR14 hari itu). M = 3 sampai close (harga disesuaikan) pernah ≥ **harga masuk × 1,30**; mulai hari itu dan seterusnya M = **2** (tidak kembali ke 3). Stop tidak pernah turun. Close < stop → jual open besok (gap dihitung).

Data & cara uji (mesin `isi_backtest`, cara paper: kurva harian, 10% ekuitas saat beli, harga pasar, dividen dipotong pajak):
- **Dev**: 2010-2019, universe 217 saham (sama dengan H11a dev).
- **Cek kedua**: 2020 s/d data terakhir, DES historis (sama dengan versi `h11a_2020`).
- Ukuran: median CAGR dan median max drawdown harian dari **100 simulasi Monte Carlo** (seed 1-100). H11a dihitung ulang dengan kode yang sama (pembanding; tersimpan dev 9,1% / -25,5%, 2020+ 23,6%).

Kriteria lulus (semua wajib):
1. Median CAGR H26 dev ≥ median CAGR H11a dev + 1 poin.
2. Median max DD H26 dev tidak lebih buruk dari H11a dev lebih dari 2 poin.
3. Median CAGR H26 2020+ ≥ median CAGR H11a 2020+.
4. Tanpa 5 trade terbesar (bersih) masing-masing strategi, dev: median CAGR H26 ≥ median CAGR H11a.
5. Sensitivitas dev (hanya cek ketahanan, bukan memilih varian): ambang {+20%, +40%} × M {1,5; 2,5} = 4 kombinasi; minimal 3 dari 4 punya median CAGR ≥ H11a dev.

Hanya dilaporkan (bukan syarat): win rate, rata-rata menang/kalah, rata-rata bersih per trade, lama tahan, porsi untung puncak yang dibawa pulang (kotor / MFE pemenang), jumlah trade yang mencapai ambang.

Hasil: lulus semua = kandidat uji maju (catatan pasca hasil), bukan pengganti H11a di paper. Gagal = status **tidak diadopsi**, ditutup tanpa variasi ambang/M lain.

Kelemahan (dicatat sebelum uji):
- Pasca hasil: ide dari data MFE yang sudah dilihat; tidak ada data bersih.
- Ambang +30% dipilih dekat median MFE pemenang (+29,5% dev, +43% 2020+).
- Dev memakai 217 saham daftar hari ini (survivorship), sama dengan H11a dev.
- Merapatkan stop menambah jumlah jual-beli ulang (sinyal baru bisa masuk lagi), biaya ikut naik.

### Hasil H26 (2026-11-01, dijalankan sekali, `backend/research/uji_h26.py`, hasil `hasil_riset/h26_hasil`): GAGAL 1/5 → tidak diadopsi
Cek mesin: tanpa ambang, simulasi H26 identik dengan `uji_tren.simulasi` (495 sinyal dev), dan H11a dev dihitung ulang = angka tersimpan (9,1% / -25,5%). H11a 2020+ dihitung ulang 22,7% (tersimpan 23,6%; data harga sudah bertambah).

| Kriteria | Hasil | |
|---|---|---|
| 1. Dev CAGR ≥ H11a + 1 | 6,1% vs 9,1% + 1 | ✘ |
| 2. Dev DD tidak lebih buruk > 2 poin | -25,5% vs -25,5% | ✔ |
| 3. 2020+ CAGR ≥ H11a | 20,2% vs 22,7% | ✘ |
| 4. Dev tanpa 5 terbesar | 3,1% vs 4,2% | ✘ |
| 5. Sensitivitas ≥ 3/4 | 0 dari 4 (5,1 / 7,8 / 6,2 / 7,2% vs 9,1%) | ✘ |

Laporan tambahan: sinyal dev 512 vs 495 (jual lebih awal → masuk lagi), bersih/trade +1,61% vs +2,10%, lama tahan 30,9 vs 32,8 hari, 80 trade menyentuh +30%, porsi untung puncak yang dibawa pulang pemenang 46% vs 44%. 2020+: bersih/trade +4,48% vs +6,22%, DD -36,7% vs -38,2%.

Kenapa: batas jual rapat menjual tren besar saat koreksi biasa di tengah jalan; untung yang "diselamatkan" kecil dibanding kenaikan lanjutan yang hilang. Ditutup tanpa variasi ambang/M lain. Pelajaran: untung yang dilepas dari puncak adalah ongkos memegang tren besar.

## H27: bottom reversal di tren naik (dikunci 2026-11-01 atas persetujuan user, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Asal ide: screener "Swing Bottom Reversal" IPOT yang dibagikan di X (contoh BLES, EMAS, GULA, VERN). Kriteria asli: Bottom Reversal = 1 (indikator IPOT, rumus tidak dibuka), Net Foreign Flow 1 minggu > 0, harga ≥ SMA100, SMA100 > SMA200, SMA50 > SMA100. Contoh yang dibagikan hanya yang naik, jadi bukan bukti. Satu versi saja, tanpa varian pilihan.

Pertanyaan: membeli pantulan setelah koreksi di saham syariah yang MA-nya tersusun naik, apakah untung setelah biaya, dan memberi sesuatu di atas Follow Tren?

Penyesuaian dari rumus asli (diputuskan sebelum melihat hasil):
- "Bottom Reversal" diganti definisi terbuka di bawah (rumus IPOT tidak diketahui).
- Syarat asing dibuang: H7/H15 sudah gagal, dan data asing per saham tidak ada untuk 2010-2019.
- Universe saham syariah saja, bukan semua IHSG.

Kerangka (sama dengan H19 kecuali disebut lain):
- Sinyal di close hari t, saham harus `lolos` (nilai 20 hari ≥ Rp5 M, ATR% 1,5-5, harga ≥ 50, tanpa hari volume 0 dalam 5 hari). Entry open t+1.
- Sinyal = semua terpenuhi di hari t:
  1. Tren: MA50 > MA100 > MA200 **dan** close ≥ MA100.
  2. Sempat koreksi: close kemarin ≤ MA20 kemarin.
  3. Pantulan: close hari ini > MA20 hari ini **dan** close hari ini > high kemarin.
- Keluar, mana yang lebih dulu: stop pelindung (stop awal entry − 3×ATR14, trailing = max(stop, close tertinggi sejak entry − 3×ATR14), close < stop → open besok); close < MA50 → open besok; batas 20 hari bursa → close hari ke-20.
- Satu posisi per ticker, maks 10 posisi @10% ekuitas, sinyal > slot dipilih acak. CAGR & DD = median 100 simulasi Monte Carlo (seed 1-100). Biaya ±1,2% pulang-pergi (fee 0,15% beli + 0,25% jual + 1 tick per sisi).
- Pembanding P = rata-rata semua tahanan open t+1 s/d close t+20 saham lolos.
- MA = rata-rata sederhana close disesuaikan.
- **Dev 2010-2019**: 217 saham (`syariah_tickers`, bias survivorship), harga dipotong 2019-12-31.
- **Holdout 2020 s/d data terakhir**: DES historis. Hanya dibuka bila lulus SEMUA kriteria dev, sekali jalan. Data 2020+ sudah dipakai H11a & eksplorasi 2020 (aturan berbeda), dicatat sebagai kelemahan.

Kriteria lulus (dev, lalu holdout bila dibuka), semua wajib:
1-6. Sama dengan H19 (exp net > 0, di atas pembanding, bootstrap 90% batas bawah > 0, tahun positif ≥ 70%, tanpa 10 trade terbaik > 0, tanpa 5 ticker terbaik > 0).
7. Median CAGR portofolio > CAGR beli-tahan bobot sama universe (tanpa biaya) di periode yang sama.
8. Bootstrap bulanan 98% batas bawah (persentil 1) > 0 (uji ke-43, rawan kebetulan).
9. Nilai tambah atas Follow Tren: median CAGR / |median max DD| > H11a di periode yang sama (dev H11a 9,1% / 25,5% = 0,36; dihitung ulang dengan kode yang sama).

Hanya dilaporkan (bukan syarat): jumlah trade, winrate, untung vs rugi rata-rata, return kotor, profit factor, lama tahan, porsi keluar per alasan (stop / MA50 / 20 hari), korelasi return bulanan dengan H11a, persen trade yang saat masuk juga dipegang H11a.

Hasil: lulus dev + holdout = kandidat paper kedua, bukan pengganti Follow Tren. Gagal = ditutup tanpa variasi MA, batas hari, atau aturan keluar.

Kelemahan (dicatat sebelum uji):
- Mirip H19c/H19d (pantulan + filter MA200) yang gagal karena biaya; peluang lulus rendah.
- Definisi reversal buatan sendiri, bukan rumus IPOT.
- Dev 217 saham daftar hari ini (survivorship); holdout 2020+ tidak buta.

### Hasil H27 dev 2010-2019 (2026-11-01, dijalankan sekali, `backend/research/uji_h27.py --periode dev`, hasil `hasil_riset/h27_dev`): GAGAL 0/9, holdout tidak dibuka
Cek mesin: H11a dev dihitung ulang dengan kode yang sama = 9,1% / -25,5% (sama dengan angka tersimpan). Beli-tahan bobot sama 217 saham 8,1%/th.

| Kriteria | Hasil | |
|---|---|---|
| 1. Exp net > 0 | -1,23% (kotor -0,02%, median -2,48%) | ✘ |
| 2. Di atas pembanding (tahan 20 hari) | -1,23% vs -0,65% (kotor +0,60%) | ✘ |
| 3. Bootstrap 90% batas bawah > 0 | -1,79% | ✘ |
| 4. Tahun positif ≥ 70% | 10% (hanya 2012, +0,17%) | ✘ |
| 5. Tanpa 10 trade terbaik > 0 | -1,53% | ✘ |
| 6. Tanpa 5 ticker terbaik > 0 | -1,47% (tanpa ASRI, SSIA, TINS, BMTR, ANTM) | ✘ |
| 7. Median CAGR > beli-tahan | -8,2% (p5-p95 -8,7 s/d -7,7%) vs 8,1% | ✘ |
| 8. Bootstrap bulanan persentil 1 > 0 | -2,00% | ✘ |
| 9. CAGR/|DD| > H11a | -8,2/59,9 = -0,14 vs 9,1/25,5 = 0,36 | ✘ |

Laporan: 1.005 trade, 76 ticker, winrate 30%, untung +6,74% vs rugi -4,58%, profit factor 0,62, tahan 10,4 hari; keluar MA50 65%, 20 hari 25%, stop 10%. Korelasi bulanan dengan H11a 0,62 (contoh 1 simulasi), 22% trade sahamnya sedang dipegang H11a. Per tahun (bersih/trade): 2010 -2,45, 2011 -1,80, 2012 +0,17, 2013 -1,56, 2014 -1,01, 2015 -2,80, 2016 -1,08, 2017 -0,18, 2018 -2,07, 2019 -1,55.

Kenapa: bahkan sebelum biaya hasilnya nol dan kalah dari saham acak dengan lama tahan sama. Pantulan di atas MA20 sering tidak berlanjut; 65% trade keluar karena close jatuh di bawah MA50. Ditutup tanpa variasi MA, batas hari, atau aturan keluar. Pelajaran: contoh screener di media sosial yang hanya menampilkan saham yang naik bukan bukti.

## H28: gap up yang belum ditutup (dikunci 2026-11-01 atas permintaan user, sebelum kode uji dibuat dan sebelum melihat hasil apa pun)
Asal ide: postingan X (@thesmallmoney) "cari saham yang gap-nya belum ditutup dan masih lebar, risknya masuk akal, hanya untuk short term", digabung dengan running trade, orderbook, dan tradebook. Bagian orderbook/running trade/tradebook TIDAK bisa diuji (data historis tidak ada); yang diuji hanya saringan gap. Kalau gagal, artinya gap saja tidak cukup; klaim orderbook tetap tidak terbukti maupun terbantah. Satu versi, tanpa varian pilihan. Gap belum pernah diuji di H0-H27.

Pertanyaan: saham syariah yang gap up dan celahnya tetap terbuka sampai penutupan, apakah lanjut naik dalam jangka pendek cukup untuk menutup biaya?

Aturan (angka dipilih sebelum melihat data apa pun):
- Hari g (sinyal, dilihat di close g), semua terpenuhi:
  1. Gap lebar dan belum ditutup: low g ≥ high (g−1) × 1,02 (celah ≥ 2% bertahan sepanjang hari).
  2. Risiko masuk akal: close g ≤ high (g−1) × 1,10 (jarak ke batas gap ≤ ±10%).
  3. Saham `lolos` (nilai 20 hari ≥ Rp5 M, ATR% 1,5-5, harga ≥ 50, tanpa hari volume 0 dalam 5 hari).
- Masuk open g+1. Kalau open g+1 ≤ high (g−1) (gap sudah tertutup sebelum masuk) → tidak masuk.
- Stop awal = high (g−1) (gap tertutup). Trailing = max(stop, close tertinggi sejak entry − 3×ATR14). Close < stop → jual open besok.
- Batas waktu 10 hari bursa setelah sinyal → jual di close hari ke-10. Mana yang lebih dulu.
- Satu posisi per ticker, maks 10 posisi @10% ekuitas, sinyal > slot dipilih acak; CAGR & DD = median 100 simulasi Monte Carlo. Biaya ±1,2% pulang-pergi.
- Pembanding P = rata-rata semua tahanan open t+1 s/d close t+10 saham lolos.
- **Dev 2010-2019**: 217 saham (survivorship), harga dipotong 2019-12-31. **Holdout 2020+**: DES historis, hanya dibuka bila lulus SEMUA kriteria dev, sekali jalan (data 2020+ sudah dipakai H11a & eksplorasi).

Kriteria lulus: sama persis dengan H27 (1-6 seperti H19, 7 median CAGR > beli-tahan bobot sama, 8 bootstrap bulanan persentil 1 > 0, 9 median CAGR/|median max DD| > H11a periode sama).

Hanya dilaporkan: jumlah trade, winrate, untung vs rugi, kotor, profit factor, lama tahan, alasan keluar, korelasi bulanan dengan H11a, persen trade yang sahamnya sedang dipegang H11a.

Gagal = ditutup tanpa variasi lebar gap, batas risiko, atau masa tahan.

Kelemahan (dicatat sebelum uji):
- Bagian inti rumus asli (orderbook/running trade) tidak diuji.
- Ambang 2% dan 10% dipilih sendiri (postingan tidak memberi angka).
- Mirip breakout H4 (gagal di 2024+) dan momentum jangka pendek yang biasanya kalah biaya.
- Dev 217 saham (survivorship); holdout tidak buta.

### Hasil H28 dev 2010-2019 (2026-11-01, dijalankan sekali, `backend/research/uji_h28.py --periode dev`, hasil `hasil_riset/h28_dev`): GAGAL 0/9, holdout tidak dibuka
| Kriteria | Hasil | |
|---|---|---|
| 1. Exp net > 0 | -2,42% (kotor -1,20%, median -3,72%) | ✘ |
| 2. Di atas pembanding (tahan 10 hari) | -2,42% vs -0,97% (kotor +0,28%) | ✘ |
| 3. Bootstrap 90% batas bawah > 0 | -4,63% | ✘ |
| 4. Tahun positif ≥ 70% | 22% (2010, 2011; 2017 tanpa sinyal) | ✘ |
| 5. Tanpa 10 trade terbaik > 0 | -6,87% | ✘ |
| 6. Tanpa 5 ticker terbaik > 0 | -4,77% (tanpa SMSM, ACES, PGAS, ITMG, ASGR) | ✘ |
| 7. Median CAGR > beli-tahan | -0,7% vs 8,1% | ✘ |
| 8. Bootstrap bulanan persentil 1 > 0 | -5,63% | ✘ |
| 9. CAGR/|DD| > H11a | -0,7/9,7 = -0,07 vs 0,36 | ✘ |

Laporan: hanya 29 trade (19 saham) dalam 10 tahun, 83% bulan tanpa posisi; winrate 31%, untung +6,87% vs rugi -6,60%, profit factor 0,47, tahan 8,1 hari; keluar 10 hari 55%, gap tertutup 41%, trailing 3%. Korelasi bulanan dengan H11a 0,04.

Kenapa: gap up yang celahnya bertahan jarang terjadi di saham syariah likuid (syarat ATR% ≤ 5 membuang saham paling liar), dan setelahnya harga rata-rata turun. Sampel kecil, tapi tidak ada tanda keunggulan; ditutup tanpa variasi lebar gap, batas risiko, masa tahan, atau syarat likuiditas. Klaim orderbook/running trade tetap tidak teruji.

### Pemeriksaan ulang H27 & H28 + kualitas open Yahoo (2026-11-01, atas permintaan user; EKSPLORASI, bukan bukti, status tidak berubah)
Cek manual 6 trade acak: sinyal, harga masuk/keluar, dan alasan keluar sesuai aturan. Ditemukan tiga kelemahan:
1. **H27 cacat rancangan**: syarat masuk tidak mewajibkan close > MA50, padahal aturan jual close < MA50 → 23% trade dibeli di bawah MA50 dan dijual 2-3 hari kemudian (30% trade keluar ≤ 3 hari). Trade lainnya juga minus (-1,25%).
2. **H28 saringan salah pilih**: 1.554 gap ≥ 2% yang bertahan (217 saham 2010-2019), hanya 38 lolos `lolos` standar. Tanpa batas ATR pun tinggal 47 trade (syarat nilai ≥ Rp5 M ikut membuang): saham yang gap besar umumnya tidak likuid.
3. **Open Yahoo 2010-2012 rusak**: open = close hari yang sama di 96-99% hari (2013 47%, 2014 63%, 2015-2019 17-23%). Pemeriksaan lama hanya membandingkan open dengan close kemarin. Semua uji yang membeli di open memakai harga close di tahun-tahun itu.

Eksplorasi (setelah melihat hasil, bukan bukti):
| Uji | Trade | Kotor | Pembanding kotor | Bersih | Median CAGR | Kriteria |
|---|---|---|---|---|---|---|
| H27 + close > MA50, 2010-2019 | 782 | 0,00% | +0,60% | -1,21% | -7,0% | 0/9 |
| H27 + close > MA50, 2015-2019 | 378 | -0,44% | +0,13% | -1,61% | -7,7% | 0/9 |
| H28 tanpa batas ATR, 2010-2019 | 47 | -1,59% | +0,35% | -2,87% | -1,4% | 0/9 |
| H28 tanpa batas ATR, 2015-2019 | 18 | -4,57% | +0,11% | -5,73% | -2,1% | 0/9 |

Dampak open rusak ke Follow Tren (H11a, median 100 simulasi Monte Carlo, kode sama):
| Periode | Open asli | Open diganti close |
|---|---|---|
| 2015-2019 (open bagus) | CAGR 8,5%, DD -17,5%, bersih/trade +1,90% | CAGR 9,5%, DD -20,2%, +2,49% |
| 2010-2019 (dev) | CAGR 9,1%, DD -25,5%, +2,10% (angka resmi) | CAGR 9,4%, DD -28,9%, +2,46% |

Kesimpulan: perbaikan rancangan tidak menolong H27 maupun H28; kesimpulan gagal tetap. Beli di close hari masuk ±1 poin/th lebih baik dari beli di open untuk H11a, jadi tahun 2010-2012 (open = close) sedikit terlalu bagus; perkiraan dampak ke dev H11a ±0,3 poin/th (9,1% kemungkinan ±8,8%). Tidak mengubah status H11a, aturan, atau batas paper.

## Audit H11a & H22 (2026-11-01, atas permintaan user; audit read-only + analisis, bukan uji baru)
Script: `audit/h11a_minimal.py` (implementasi ulang H11a dari nol) dan `audit/h22_ulang.py` (H11a & H22 dengan standar yang sama; salinan simulasi dicek identik dengan framework). Data 2020+ untuk H22 = eksplorasi (bukan bukti), holdout resmi H22 tetap tidak dibuka.
- **Tidak ada look-ahead pada sinyal/eksekusi H11a**; implementasi ulang independen memberi CAGR median 23,0% (framework 22,7% di data yang sama). Look-ahead kecil ditemukan di **ukuran posisi**: 10% dihitung dari ekuitas dengan close hari beli, padahal beli di open (`batas_paper.kurva_harian`, juga paper `tren_harian`). Diperbaiki 2026-11-01: ukuran posisi dari ekuitas close hari bursa sebelumnya (backtest langsung; paper H11a mulai 2026-11-02 supaya riwayat 21-30 Okt tetap identik). Dampak backtest: 2020+ median 22,7% → 22,8%, DD -38,2% → -38,0%; konservatif ARA/ARB 22,0% → 22,1%; dev 9,1% → 9,0%.
- **Kriteria lama tidak seragam.** H11a dinilai per trade ("tanpa 10 trade terbaik > 0", "tanpa 5 ticker > 0") tanpa sensitivitas. H22 dinilai relatif pasar ("tanpa 5 ticker terbaik > bobot sama", pembanding tidak dibuang pemenangnya) dan wajib lolos 3 sensitivitas. Asimetri muncul karena urutan waktu (kriteria H22 ditulis 24 Okt, setelah H11a lulus), bukan disengaja, tapi efeknya H11a lolos dengan standar lebih ringan.
- **H11a dengan standar H22/standar seragam** (median 30 simulasi Monte Carlo, sizing sudah diperbaiki):

| | Dev 2010-2019 | 2020+ |
|---|---|---|
| CAGR dasar | 8,9% (bobot sama universe H11a 6,8%) | 22,4% (bobot sama -1,5%; universe H22 3,6%) |
| Tanpa 5 saham terbaik (kas) vs pembanding tanpa 5 terbaiknya | 3,3% vs 3,7% ✘ | 10,0% vs -3,8% ✔ |
| Tanpa 10 saham terbaik (kas) vs pembanding tanpa 10 terbaiknya | -0,7% vs 1,8% ✘ | 2,0% vs -5,6% ✔ |
| Tanpa tahun terbaik vs pembanding tanpa tahun terbaiknya | 7,5% vs 2,4% ✔ | 9,1% vs -6,3% ✔ |
| S1 biaya 2 tick | 6,1% ✘ | 16,7% ✔ |
| S2 likuiditas ≥ Rp20 M | **3,7%** ✘ | **10,8%** ✔ (tanpa 5 saham 0,9% vs 0,75%, tipis) |
| S3 harga ≥ Rp200 | 6,9% (k5 ✘) | 21,6% ✔ |

- **H22 dengan tes simetris**: dev lebih kuat dari H11a (18,8% vs bobot sama 7,8%; tanpa 5 saham 7,7% vs 3,7%; Sharpe 0,58 vs 0,23); 2020+ (eksplorasi) runtuh: 5,3%, DD -53,7%, tanpa 5 saham -7,3%, 8 dari 10 pemenang terbesar di 2025. Sensitivitas dev tetap 1/3 (S1 gagal tipis, S2 gagal nyata).
- **Status tidak berubah.** H11a tetap paper trade (catatan ditambahkan di registry), H22 tetap gagal.

## Standar seragam (berlaku mulai 2026-11-01)
Dikunci 2026-11-01 atas persetujuan user, **sebelum hipotesis berikutnya diuji**. Berlaku untuk SEMUA hipotesis yang dikunci sesudah tanggal ini, apa pun jenisnya (trend-following, mean-reversion, faktor, dividen, rotasi aset, dst.). Tidak boleh dilonggarkan, diganti, atau dikecualikan setelah melihat hasil. Hipotesis boleh menambah kriteria khusus (ditulis sebelum uji), tapi tidak boleh mengurangi standar ini.

a. **Pembanding**: (1) bobot sama semua saham universe syariah likuid (universe dan filter sama dengan strategi, syariah point-in-time bila datanya ada, rebalance bulanan, tanpa biaya) dan (2) JII. Strategi wajib di atas keduanya.
b. **Tes konsentrasi simetris**: strategi tanpa 5 dan tanpa 10 saham penyumbang laba terbesar vs pembanding tanpa 5 dan tanpa 10 saham penyumbang terbesarnya (cara buang sama untuk keduanya); strategi tanpa tahun kalender terbaiknya vs pembanding tanpa tahun terbaiknya. Strategi harus tetap di atas pembanding di semua tes ini. JII hanya ikut tes tahun terbaik bila data anggota historisnya tidak ada.
c. **Sensitivitas wajib, semua harus lolos (a dan b tetap terpenuhi)**: S1 biaya 2 tick per sisi; S2 likuiditas ≥ Rp20 M (pembanding ikut universe ini); S3 harga ≥ Rp200 (pembanding ikut).
d. **Harus lolos di dev DAN holdout.** Holdout dibuka sekali, hanya kalau dev lulus semua.

Alasan: kriteria lama tidak seragam (H11a per trade tanpa sensitivitas, H22 relatif pasar dengan 3 sensitivitas), ditemukan di audit 2026-11-01. Standar ini berlaku ke depan saja: vonis hipotesis lama (H0-H28) tidak diubah.

**e. Kualitas data (ditambahkan 2026-11-02 atas keputusan user; berlaku untuk hipotesis yang dikunci mulai 2026-11-02, bagian dari template pra-registrasi):**
- Harga dibaca hanya lewat `backend/db/harga.py` (data sudah melewati registry `koreksi_harga`); kode riset tidak membaca koleksi `harga`/`harian` langsung dan tidak memanggil Yahoo.
- Sebelum backtest dev: jalankan `cek_kualitas_data`. Kalau ADA TEMUAN di ticker atau periode yang dipakai, perbaiki dulu lewat `koreksi_harga` (dengan bukti), baru boleh dites.
- Hasil hipotesis menyimpan `versi_data`: tanggal cek kualitas + statusnya, jumlah koreksi aktif, dan sidik (hash) data yang dipakai (`harga.sidik()`), supaya hasil bisa diulang persis.
- Laporan hasil wajib menyebut keterbatasan data: survivorship (saham delisting tidak ada di Yahoo), K4 sebelum 2020 yang tidak terverifikasi (label di registry), syariah point-in-time baru sejak Des 2019.
- Koreksi data baru setelah hipotesis divonis: hitung ulang hipotesis yang terdampak dan laporkan sebelum/sesudah; dicatat sebagai "pembaruan angka karena koreksi data", terpisah dari perubahan aturan. Vonis hanya berubah dengan persetujuan user.
- Aksi korporasi baru diterapkan otomatis hanya bila faktornya dari data resmi IDX dan wajar (0,2-5, cocok dengan data lain); selain itu ditahan untuk diputuskan user.

## H29: Momentum Blend, gabungan 50/50 H11a (Follow Tren) + H22 (RS 12-1) (dikunci 2026-11-01 atas permintaan user, SETELAH melihat data dev dan 2020+)
**Ditemukan setelah melihat hasil.** Ide gabungan muncul dari audit 2026-11-01 setelah return H11a dan H22 di dev dan 2020+ terlihat. Angka historisnya (simulasi dev Feb 2011-2019 CAGR 14,8%, DD -27,8%, Sharpe 0,50; 2020-Okt 2026 CAGR 14,7%, DD -32,7%, Sharpe 0,49; median 30 simulasi Monte Carlo bagian H11a) **bukan bukti**. Satu-satunya bukti yang sah adalah paper trade mulai 2026-11-01. Tidak ada parameter yang disetel atau diubah; standar seragam tidak dipakai menilai H29 karena H29 tidak punya data uji bersih.

Aturan (persis simulasi gabungan `audit/h22_ulang.py`, `satu_periode`):
- **Porsi modal**: 50% bagian H11a, 50% bagian H22.
- **Pengembalian ke 50/50**: tiap akhir bulan kalender (close hari bursa terakhir). Return bulanan H29 = 0,5 × return bulanan bagian H11a + 0,5 × return bulanan bagian H22. Pemindahan dana antar bagian dianggap tanpa biaya.
- **Bagian H11a**: aturan H11a persis. Saham syariah DES pada tanggal sinyal, lolos likuiditas (nilai transaksi 20 hari ≥ Rp5 M, ATR% 1,5-5, harga ≥ Rp50, tanpa volume nol 5 hari). Close ≥ close tertinggi 250 hari sebelumnya → beli open besok 10% ekuitas bagian, maks 10 posisi, sinyal > slot dipilih acak. Stop awal entry − 3×ATR14, trailing = max(stop, close tertinggi sejak entry − 3×ATR14), close < stop → jual open besok, batas 500 hari.
- **Bagian H22**: aturan H22 persis. Momentum = return close adjusted akhir bulan t−12 → akhir bulan t−1. Sinyal di close hari bursa terakhir bulan, eksekusi open hari bursa pertama bulan berikutnya. Universe DES pada tanggal sinyal + median nilai transaksi 60 hari ≥ Rp5 M + harga ≥ Rp100 + ≥ 250 hari data + volume > 0 di ≥ 90% dari 250 hari. N = maks(10, bulat(20% × saham lolos)). Pegang selama peringkat ≤ 2N dan masih lolos, slot kosong diisi peringkat teratas, saham baru 1/N ekuitas bagian, pangkas ke 1/N kalau bobot > 2/N. Transaksi ditunda kalau volume 0 atau candle satu harga dengan return ≥ +6,5% (beli) / ≤ -6,5% (jual).
- **Biaya**: fee beli 0,15% + jual 0,25% + 1 tick per sisi (fraksi IDX) di kedua bagian, termasuk pemangkasan.

Paper trade (mulai 2026-11-01, modal setara Rp100 jt, sama dengan H11a). Perbedaan eksekusi dari simulasi (realisme, bukan parameter):
- Bagian H11a = **paper H11a yang sudah berjalan** (sejak 21 Okt 2026): lot 100, beli dibatalkan di candle ARA terkunci, jual ditunda di candle terkunci (sama dengan versi konservatif), ukuran posisi dari ekuitas close hari sebelumnya mulai 2026-11-02.
- Bagian H22 = paper baru `backend/paper/h22_harian.py` (job `paper_h22`, koleksi `paper_h22_*`), modal Rp100 jt, titik awal close 30 Okt 2026, rebalance pertama di open 2 Nov 2026: lot 100, transaksi tertunda di candle terkunci (aturan H22), ukuran posisi dari ekuitas close hari sinyal, harga mentah + dividen tunai dipotong pajak 10% (simulasi memakai harga adjusted tanpa pajak), split menyesuaikan jumlah lembar.
- H29 dihitung dari kedua kurva paper (`backend/paper/h29.py`, API `/api/paper/h29`, panel di tab Paper Follow Tren): titik awal 30 Okt 2026 = Rp100 jt, dikembalikan ke 50/50 tiap akhir bulan secara virtual (tanpa biaya, sama dengan simulasi). Uang nyata butuh pemindahan dana antar dua bagian tiap bulan; biayanya tidak dimodelkan.
- Pengecekan mesin H22 (2026-11-01, db tes, Agu-Okt 2026): keputusan rebalance sama persis dengan `uji_h21_h22.simulasi`, selisih ekuitas maks 0,09% (lot, harga mentah, pajak dividen).

**Kriteria evaluasi paper (dikunci 2026-11-01, untuk H11a dan H29; keputusan zona 2026-11-01):**
- **H29**: evaluasi 12 bulan pada **2027-11-01**. **H11a**: jadwal yang dikunci 21 Okt 2026 tetap berlaku (cek eksekusi Jan 2027, cek tengah Apr 2027, **keputusan utama Okt 2027**: tidak pernah WASPADA/GAGAL → uang nyata kecil 10-20%). Syarat gagal di bawah ditambahkan di samping aturan itu, bukan menggantikan.
- **H11a GAGAL** kalau salah satu terjadi: (1) zona `batas_paper` h11a_v1 menyatakan GAGAL, yaitu return di bawah persentil 1 sejak hari ke-63, drawdown lebih dalam dari persentil 1, atau rugi beruntun di atas persentil 99. Zona ini tetap berlaku karena sudah dikunci 2026-10-22, sebelum kriteria baru. (2) Drawdown ekuitas paper lebih dalam dari **-45%** (ditambahkan 2026-11-01). (3) Ada bug eksekusi (ditambahkan 2026-11-01) yang membuat hasil paper tidak sesuai aturan.
- **H29 GAGAL** kalau drawdown ekuitas paper (angka utama) lebih dalam dari **-45%**, atau ada bug eksekusi.
- Hasil 12 bulan yang biasa-biasa saja atau rugi kecil **tidak** otomatis gagal (kecuali H11a jatuh ke zona GAGAL h11a_v1): audit 2026-11-01 menunjukkan tahun tanpa lonjakan besar itu normal (H11a tanpa tahun terbaiknya ±8-9%/th, 2022-2023 rugi).
- Di evaluasi, H11a, H29, bobot sama universe syariah likuid (dihitung harian di `paper_h22_ekuitas.ew`, tanpa biaya, dividen tanpa pajak), dan JII (indeks harga, `harian_indeks/JII`) dibandingkan pada periode yang sama.

**Angka kedua: H29 setelah estimasi biaya rebalance** (permintaan user 2026-11-01, laporan saja, bukan syarat). Angka utama H29 tetap tanpa biaya pemindahan (sama dengan simulasi). Angka kedua memotong biaya dari nilai yang dipindah tiap akhir bulan: nilai dipindah = |nilai bagian H11a − 50% nilai H29|, biaya = nilai dipindah × (fee jual 0,25% + fee beli 0,15% + 2 × 0,47%) = 1,34%. 0,47% = rata-rata biaya 1 tick per sisi trade backtest H11a 2020+ (median 0,42%), karena data posisi per bagian di tiap akhir bulan tidak tersimpan. Dihitung di `backend/paper/h29.py`, tampil berdampingan di panel Paper H29.

**Selisih metode paper vs simulasi (disengaja, bukan bug).** Saat evaluasi, angka paper tidak akan sama persis dengan simulasi audit karena:
1. Bagian H22 paper memakai **harga mentah + dividen tunai dipotong pajak 10%**, simulasi memakai **harga adjusted Yahoo (dividen masuk tanpa pajak)**. Paper sedikit lebih rendah di saham yang membagi dividen.
2. **Lot 100 lembar** di kedua bagian paper; simulasi memakai lembar pecahan. Sisa kas kecil tiap pembelian, dan saham mahal bisa batal kalau 1 lot melebihi jatah.
3. Bagian H11a paper **membatalkan beli di candle ARA terkunci dan menunda jual di candle terkunci** (versi konservatif ARA/ARB); simulasi audit H11a memakai versi dasar.
4. **Ukuran posisi dari ekuitas close hari sebelumnya** (H11a sejak 2026-11-02, H22 dari ekuitas close hari sinyal); simulasi H22 memakai ekuitas di harga open hari rebalance.
5. Bagian H22 paper menyesuaikan jumlah lembar saat split dan mengunduh harga saham yang dipegang tapi sudah keluar dari DES; simulasi memakai data historis yang sudah disesuaikan.
6. Paper H11a memakai koreksi hari tanpa transaksi (`koreksi_tanpa_transaksi`); simulasi tidak.
7. Pemilihan acak sinyal H11a di paper memakai seed = tanggal; simulasi = median 30/100 seed.
Pengecekan 2026-11-01 (db tes, Agu-Okt 2026): mesin paper H22 vs `uji_h21_h22.simulasi` di data yang sama, keputusan rebalance identik, selisih ekuitas maks 0,09% (poin 1, 2, 4).

**Cek ulang otomatis bagian H22** (`backend/paper/cek_h22.py`, job `paper_h22_cek`, jadwal harian setelah `paper_h22`): paper H22 dijalankan ulang dari nol di db `swing_cek_h22` dengan data harga lokal, lalu transaksi, posisi, ekuitas, rebalance, dan status dibandingkan dengan yang tersimpan. Hasil di koleksi `paper_h22_cek` dan di panel H29. Diuji 2026-11-01 di db tes: 64 hari COCOK, transaksi yang sengaja diubah terdeteksi BEDA.

Kelemahan (dicatat sebelum paper berjalan):
- Pasca hasil: dibentuk setelah melihat dev dan 2020+ kedua strategi; stabilnya angka gabungan (14,8% vs 14,7%) bisa kebetulan.
- **H22 gagal S2 (likuiditas Rp20 M)**, H11a juga hampir separuh di Rp20 M, jadi H29 tidak menyelesaikan masalah kapasitas: tetap hanya cocok untuk modal kecil.
- Korelasi bulanan H11a vs H22 0,64 (dev) / 0,51 (2020+); saham yang dipegang bersamaan hanya 19-21% dari posisi H11a.
- Dev kedua bagian memakai universe bias (H11a daftar 217, H22 kode DES 2019-2026); 2020+ H22 = eksplorasi.
- Pemindahan dana bulanan antar bagian tanpa biaya; di uang nyata ada biaya dan jeda.
- Bagian H11a bergantung pada paper H11a: reset paper H11a ikut memutus H29 (peringatan ditampilkan di tombol Reset).

**Simulasi harian untuk halaman Backtest Momentum Blend** (2026-11-01, `backend/research/simulasi_h29.py`, job `isi_backtest_h29`, versi `h29_dev` / `h29_2020` di `backtest_*`; dibuat setelah lihat hasil, bukan bukti): 50% kurva harian cara paper Follow Tren (100 simulasi Monte Carlo) + 50% kurva harian RS 12-1 (`uji_h21_h22.simulasi`, dicek identik), dikembalikan ke 50/50 tiap akhir bulan. Feb 2011-Des 2019: median CAGR 14,9% (p5-p95 14,4-15,2%), turun terdalam harian -28,6%, setelah biaya rebalance 14,7%. Jan 2020-Okt 2026: median 15,2% (13,8-17,3%), **turun terdalam harian -42,4% (rentang -40,3% s/d -44,2%)**, setelah biaya 14,9%. Angka turun terdalam audit (-27,8% / -32,7%) dihitung dari return bulanan; versi harian lebih dalam. Catatan: batas GAGAL H29 (-45%, dikunci 2026-11-01) hanya 1-5 poin dari penurunan yang sudah terjadi di simulasi 2020-2026. Kriteria tidak diubah.
**Catatan koreksi data (2026-11-02):** Setelah koreksi data 2026-11-02, simulasi 2020+ punya DD median -44,0% dan terburuk -46,2%, jadi batas -45% punya peluang nyata tersentuh oleh volatilitas normal. Kriteria tetap, karena dikunci sebelum koreksi. (CAGR median 2020+ 15,2% → 14,9%; dev tidak berubah 14,9% / -28,6%. Angka audit bulanan 14,8% / 14,7% di atas belum dihitung ulang.)

## H30: Residual Momentum (dikunci 2026-11-01 atas permintaan user, sebelum kode uji dibuat dan sebelum ada angka return apa pun)
Uji ke ±46. **Dipilih dari literatur, bukan dari data kita.** Dikunci 2026-11-01. Saat dikunci belum ada kode H30 dan belum ada angka return (strategi, pembanding, maupun r_m). Yang sudah dilakukan hanya cek ketersediaan data: rentang tanggal dan jumlah saham, tanpa return (lihat "Cek data sebelum dikunci"). Gagal = ditutup tanpa variasi (lookback, jendela regresi, faktor, skala, N, buffer, filter).

**Latar belakang.** H22 (momentum 12-1) kuat di dev 2011-2019, tapi gagal S1 dan S2. Di 2020+ (eksplorasi audit, bukan holdout resmi) hasilnya ambruk: 5,3%, DD -53,7%. Laba H22 juga terkonsentrasi di sedikit saham kecil/volatil. Literatur menunjukkan residual momentum (momentum dari return saham setelah pengaruh pasar dibuang) punya Sharpe sekitar 2× momentum biasa dengan volatilitas sekitar separuhnya. Hasilnya juga lebih konsisten antar periode, dan pemenangnya tidak terkumpul di saham kecil/volatil atau di industri tertentu.
Rujukan:
- Blitz, D., Huij, J. & Martens, M. (2011). "Residual Momentum". *Journal of Empirical Finance* 18(3), 506-521.
- Huij, J. & Lansdorp, S. (2017). "Residual Momentum and Reversal Strategies Revisited". ERIM, hdl.handle.net/1765/100801.
Beda dengan paper asli: hanya faktor pasar (paper memakai Fama-French 3 faktor). Faktor ukuran dan value tidak dipakai karena butuh kapitalisasi dan book value point-in-time.

**Hipotesis.** Di saham syariah likuid IDX, memegang saham dengan residual momentum tertinggi (return spesifik saham 12-1 bulan setelah pengaruh pasar dibuang, diskalakan dengan volatilitas residualnya) menghasilkan return di atas pembanding setelah biaya, dan lolos standar seragam 2026-11-01.

**Kerangka = H22 persis (dipakai ulang dari `backend/research/uji_h21_h22.py`, bukan ditulis ulang); hanya cara meranking yang berubah:**
- Universe dev: 766 kode yang pernah masuk DES 2019-2026, punya data Yahoo ≥ 250 hari, dianggap syariah sepanjang dev (sama dengan H22: DES point-in-time baru ada sejak 1 Des 2019). Universe holdout: DES OJK pada tanggal sinyal (`des_ojk.syariah_pada`) + 10 kode dari data resmi IDX (TECH, ENVY, DUCK, HKMU, JSKY, PURE, CBMF, FREN, META, WBSA).
- Filter di tanggal sinyal t (`lolos`): median nilai transaksi 60 hari bursa ≥ Rp5 M, close mentah ≥ Rp100, ≥ 250 hari data, volume > 0 di ≥ 90% dari 250 hari bursa terakhir. Kalender IHSG.
- Jadwal (`jadwal`): sinyal di close hari bursa terakhir tiap bulan, eksekusi di open hari bursa pertama bulan berikutnya. Transaksi ditunda ke hari bisa berikutnya kalau volume 0, atau kalau candle satu harga (high = low) dengan return ≤ -6,5% untuk jual / ≥ +6,5% untuk beli (`bisa`).
- Ukuran & buffer (`simulasi`): N = maks(10, bulat(20% × jumlah saham lolos filter)). Beli peringkat ≤ N. Yang dipegang tetap dipegang selama peringkat ≤ 2N dan masih lolos, selain itu dijual. Slot kosong diisi peringkat teratas yang belum dipegang. Kalau pegangan > N, peringkat terburuk dijual sampai N. Saham lolos yang tidak bisa diranking (butir 5 sinyal) tidak dapat peringkat, jadi kalau sedang dipegang ikut dijual.
- Bobot: saham baru dibeli 1/N ekuitas (kalau kas kurang, kas dibagi rata ke saham baru). Saham lama tidak diseimbangkan ulang, kecuali bobot > 2/N → dipangkas ke 1/N. Kas tidak berbunga. Lembar pecahan (simulasi H22 tidak memakai lot).
- Biaya: fee beli 0,15% + jual 0,25% + 1 tick per sisi (fraksi IDX, harga mentah) di setiap transaksi nyata, termasuk pemangkasan.
- Harga & saham hilang: Yahoo adjusted (dividen masuk tanpa pajak). 10 kode holdout memakai harga mentah IDX. Saham yang tidak aktif lagi sampai akhir data dinilai 0 sejak hari terakhir aktif. FREN → EXCL di close 14 Apr 2025. META dibekukan Rp238.

**Sinyal H30 (satu-satunya perubahan dari H22).** Di akhir bulan t, untuk tiap saham yang lolos filter:
1. Return bulanan saham r_i,τ = c_nilai(akhir bulan τ) / c_nilai(akhir bulan τ−1) − 1, dengan c_nilai = close adjusted ffill (sama dengan harga penilaian H22). Return pasar r_m,τ = rata-rata sederhana r_i,τ semua saham yang lolos filter di akhir bulan τ−1 (universe dan filter sama dengan pembanding bobot sama H22). Dihitung untuk τ = t−35 s/d t (36 bulan).
2. Excess return (lihat keputusan di bawah): y_i = r_i − rf, x = r_m − rf. Regresi OLS dengan konstanta: y_i,τ = a + b × x_τ + e_i,τ, pakai 36 bulan tersebut.
3. Ambil residual e_i,τ untuk τ = t−11 s/d t−1 (11 bulan; bulan t dilewati, sama dengan "12-1" di H22).
4. Sinyal = jumlah residual t−11..t−1 ÷ standar deviasi residual t−11..t−1 (ddof = 1; jumlah bulan sama untuk semua saham, jadi pilihan ddof tidak mengubah urutan). Peringkat 1 = tertinggi.
5. Saham tanpa 36 bulan return lengkap tidak diranking: c_nilai harus > 0 di ke-37 akhir bulan t−36..t, dan r_m harus ada di ke-36 bulan. Saham dengan standar deviasi residual 0 tidak diranking.

**Return yang dipakai di regresi: excess return terhadap bunga antarbank.** Alasan, dari ketersediaan data saja: `lab_data.makro/bunga_antarbank` (FRED `IRSTCI01IDM156N`, rata-rata bulanan % per tahun) ada lengkap 1990-01 s/d 2026-08 tanpa bulan bolong, jadi tersedia lengkap sejak 2010. Konversi bulanan = (1 + nilai/100)^(1/12) − 1, sama dengan `audit/h22_ulang.rf_bulanan`, memakai nilai bulan τ untuk return bulan τ. Bulan yang belum terbit di FRED (saat dikunci: Sep dan Okt 2026) memakai nilai terakhir yang ada (ffill). Dicatat: karena regresi memakai konstanta, beda excess vs mentah hanya lewat naik-turun rf × (1 − b), jadi kecil.

**Periode.**
- Dev: sinyal pertama di akhir bulan pertama yang punya 36 r_m. r_m pertama = Feb 2011 (filter H22 baru meloloskan saham di akhir Jan 2011, 49 saham; akhir Des 2010 masih 0 karena syarat 250 hari data). Jadi 36 r_m lengkap pertama ada di **sinyal akhir Jan 2014, eksekusi open hari bursa pertama Feb 2014**. Portofolio dev Feb 2014 s/d close 31 Des 2019 (harga dipotong 2019-12-31). Return saham sendiri bisa dihitung sejak Jan 2013, tapi r_m menjadi batasnya.
- Holdout: portofolio Jan 2020 s/d close 30 Okt 2026 (sinyal akhir Des 2019 s/d akhir Sep 2026). Dibuka sekali, hanya kalau dev lulus semua.
- **Holdout tidak sepenuhnya bersih**: data 2020+ sudah pernah terlihat lewat eksplorasi H22 (audit 2026-11-01: 5,3%, DD -53,7%), H11a (lulus di 2020+), H29, dan eksplorasi 2020+ hipotesis lain. **Dev juga tidak buta**: hasil H22 per tahun 2011-2019 sudah terbuka (dan residual momentum berkorelasi dengan momentum biasa).

**Kriteria lulus = standar seragam 2026-11-01 apa adanya, tanpa pengecualian (dev DAN holdout, semua):**
- a1. CAGR bersih > CAGR pembanding bobot sama (semua saham lolos, universe dan filter sama, rebalance bulanan, tanpa biaya; `pembanding_sama` / `audit.ew`).
- a2. CAGR bersih > CAGR JII (`indeks/JKII` close + dividen 2,5%/th diakru harian, tanpa biaya; sama dengan H22).
- b1. Tanpa 5 saham penyumbang laba terbesar: CAGR strategi > CAGR pembanding bobot sama tanpa 5 saham penyumbang terbesarnya.
- b2. Sama untuk 10 saham.
  Cara buang (sama untuk strategi dan pembanding): untung/rugi saham-saham itu dikeluarkan dari return bulanan (dianggap kas), seperti `audit/h22_ulang.buang` + `top_ticker`. Penyumbang = total laba per ticker sepanjang periode.
- b3. Tanpa tahun kalender terbaik: CAGR strategi tanpa tahun terbaiknya > CAGR pembanding bobot sama tanpa tahun terbaiknya, **dan** > CAGR JII tanpa tahun terbaiknya (JII ikut tes ini karena data anggota historis JII baru ada sejak Mar 2024). Cara audit `tanpa_tahun_terbaik`, return bulanan.
- c. Sensitivitas, masing-masing terpisah, a1-a2 dan b1-b3 harus tetap terpenuhi: S1 biaya 2 tick per sisi; S2 likuiditas median ≥ Rp20 M (pembanding ikut universe ini); S3 harga ≥ Rp200 (pembanding ikut).
- d. Lolos dev dulu, baru holdout dibuka sekali; lulus = lolos semua di keduanya. Lulus dev + holdout = kandidat uji maju (bukan langsung uang nyata).
- Metrik: CAGR dan tes konsentrasi dari return bulanan (`cagr_bln`), max DD harian juga dilaporkan.

**Laporan saja (bukan syarat):** dibandingkan dengan H22 di periode yang sama (H22 dijalankan ulang Feb 2014-2019 dan, kalau holdout H30 dibuka, Jan 2020-Okt 2026): CAGR, DD, volatilitas, Sharpe (rf bunga antarbank), turnover, N rata-rata, % kas, porsi laba 5/10 saham terbesar, korelasi bulanan dengan H22 dan Follow Tren, irisan saham yang dipegang H30 dan H22, per tahun.

**Cek data sebelum dikunci (2026-11-01, hanya tanggal dan jumlah saham, tanpa return):**
- `harga`: 921 ticker, 4 Jan 2010 s/d 30 Okt 2026. Ticker yang punya data per tahun: 2010 349, 2011 374, 2012 395, 2013 419, 2014 441, 2015 458, 2016 472, 2017 505, 2018 555, 2019 606, 2020 655, 2021 709, 2022 768, 2023 847, 2024 888, 2025 914, 2026 921 (survivorship: hanya saham yang masih ada).
- DES OJK (`des`): 823 kode, periode point-in-time paling awal mulai 1 Des 2019.
- Saham lolos filter H22 / lolos + 36 bulan return lengkap, di akhir Desember: dev 2013 58/53, 2014 61/55, 2015 52/48, 2016 60/53, 2017 59/56, 2018 58/51, 2019 68/61. Holdout (DES pada tanggal itu) 2019 63/56, 2020 72/68, 2021 87/79, 2022 88/75, 2023 86/74, 2024 97/83, 2025 129/111, 23 Okt 2026 108/103. Hitungan "ketat" (harga ada tepat di hari akhir bulan) sama persis dengan hitungan ffill.

**Keputusan user 2026-11-01 (sebelum kode H30 dibuat dan sebelum ada angka return; final, tidak diubah lagi):**
1. r_m di holdout untuk bulan yang universe-nya sebelum 1 Des 2019 (dibutuhkan regresi sinyal 2020-2022) memakai universe dev (kode DES 2019-2026), karena DES point-in-time belum ada. Mulai 1 Des 2019 memakai DES pada tanggal itu.
2. Holdout sampai close **30 Okt 2026** (hari bursa terakhir Okt 2026). Pembanding H22 dihitung ulang di periode yang sama.
3. r_m di S2/S3 tetap memakai universe dasar (Rp5 M, Rp100). Sensitivitas hanya mengubah saham yang boleh dipegang dan pembandingnya, bukan faktor pasar.
4. N dihitung dari semua saham lolos filter, sama dengan H22 (bukan hanya dari yang bisa diranking).
5. Dev Feb 2014 - Des 2019 (r_m dari universe H22).

Kelemahan (dicatat sebelum uji):
- Dev bukan point-in-time (status syariah dari DES 2019-2026, survivorship Yahoo), sama dengan H22.
- Dev hanya ±6 tahun (Feb 2014-2019, 71 rebalance) dan universe kecil (48-61 saham bisa diranking per akhir tahun). Pelajaran seri K: noise portofolio acak di universe sekecil ini bisa lebih besar dari keunggulan faktor beberapa poin per tahun.
- Hanya faktor pasar, dan r_m = bobot sama universe likuid (bukan indeks berbobot kapitalisasi). Sebagian efek ukuran/sektor bisa masih tersisa di residual.
- Regresi 36 bulan di saham yang baru 3 tahun lolos data → estimasi beta kasar.
- Holdout tidak bersih (lihat Periode). Dev juga tidak buta terhadap pola momentum.
- Pembanding bobot sama tanpa biaya (konservatif, disengaja). META/FREN/10 kode IDX sama kelemahannya dengan H22.
- Uji ke ±46: risiko lulus karena kebetulan tetap ada.
- **Kekuatan statistik dev rendah** (dicatat 2026-11-01 atas permintaan user, SEBELUM backtest): universe dev 48-61 saham, N sekitar 10-12, dev hanya 6 tahun. Hasil dev, lolos atau gagal, berbobot ringan.

### Hasil H30 dev Feb 2014 - Des 2019 (2026-11-01, dijalankan sekali, `backend/research/uji_h30.py --periode dev`, hasil `hasil_riset/h30_dev`): GAGAL, holdout tidak dibuka
Sebelum uji: cabang `h30` ditambahkan di `uji_h21_h22.peringkat`, dan `audit/h22_ulang.h22_log` diberi parameter `jenis` (bawaan `"h22"`). H22 dijalankan dengan kode lama dan kode baru (`PYTHONHASHSEED=0`) di 8 skenario (dev 2011 dan dev 2014 × dasar/S1/S2/S3): ekuitas, rekap rebalance, posisi, dan turnover **identik, selisih 0,0**. Tanpa seed hash tetap, selisihnya ±1e-15 karena urutan iterasi set (pembulatan floating point, keputusan sama persis). H30 dijalankan dengan `PYTHONHASHSEED=0`. Ekuitas `h22_log` = `simulasi` (selisih 0).
71 rebalance (sinyal 30 Jan 2014 - 29 Nov 2019). Rata-rata 60,9 saham lolos, 54,8 bisa diranking (min 42, maks 65), N rata-rata 12,2. Pembanding: bobot sama CAGR 7,27%, DD bulanan -30,53%; JII + dividen 2,5% CAGR 5,07%, DD -22,68%. CAGR dari return bulanan.

| Skenario | CAGR H30 vs bobot sama | a2 vs JII 5,07% | b1 tanpa 5 saham | b2 tanpa 10 saham | b3 tanpa tahun terbaik (vs bobot sama / JII 2,63%) | Hasil |
|---|---|---|---|---|---|---|
| Dasar | 11,20% vs 7,27% ✔ | ✔ | -2,87% vs 1,85% ✘ | -5,69% vs -0,08% ✘ | 5,69% vs 2,92% / 2,63% ✔ | gagal 3/5 |
| S1 biaya 2 tick | 9,07% vs 7,27% ✔ | ✔ | -4,81% vs 1,85% ✘ | -7,70% vs -0,08% ✘ | 3,72% vs 2,92% / 2,63% ✔ | gagal 3/5 |
| S2 likuiditas ≥ Rp20 M | 5,37% vs 3,26% ✔ | ✔ (5,37%) | -2,59% vs -0,16% ✘ | -6,16% vs -2,17% ✘ | 2,04% vs -0,29% / 2,63% ✘ | gagal 2/5 |
| S3 harga ≥ Rp200 | 10,01% vs 7,59% ✔ | ✔ | -2,74% vs 2,16% ✘ | -6,16% vs 0,16% ✘ | 3,42% vs 3,73% / 2,63% ✘ | gagal 2/5 |

Laporan saja, H30 vs H22 di periode yang sama (Feb 2014 - Des 2019, H22 dihitung ulang):

| | H30 | H22 | Bobot sama |
|---|---|---|---|
| CAGR (bulanan / harian) | 11,20% / 11,22% | 13,42% / 13,44% | 7,27% |
| Max DD bulanan / harian | -47,0% / -49,0% | -35,5% / -37,6% | -30,5% |
| Volatilitas tahunan | 21,9% | 21,4% | |
| Sharpe (rf bunga antarbank) | 0,33 | 0,42 | |
| Turnover/th | 149,2% | 129,3% | |
| Kas rata-rata | 4,0% | 4,7% | |
| Posisi / saham berbeda | 134 / 85 | 122 / 95 | |
| Laba 5 saham terbesar (% laba total) | 127% (INKP, TKIM, NIKL, BRPT, SMBR) | 134% (NIKL, TKIM, INKP, BRPT, PTPP) | 85% |
| Laba 10 saham terbesar | 162% | 176% | 114% |
| Standar seragam (dasar + S1-S3) | gagal di semua skenario | gagal di semua skenario | |
| Korelasi bulanan dengan Follow Tren (h11a_dev) | 0,65 | 0,57 | |
Korelasi bulanan H30 vs H22 0,89; rata-rata 53% saham H30 juga dipegang H22 di akhir bulan.
Per tahun H30 / H22 / bobot sama / JII: 2014 (Feb-Des) 15,0 / 33,5 / 20,1 / 17,2; 2015 -32,4 / -25,2 / -23,0 / -10,5; 2016 42,8 / 54,8 / 31,4 / 17,9; 2017 35,1 / 29,0 / 10,3 / 12,1; 2018 26,3 / 26,6 / 12,6 / -7,5; 2019 -1,0 / -16,5 / 0,3 / 4,4.

Catatan:
- H30 di atas bobot sama dan JII, tapi seluruh kelebihannya berasal dari segelintir saham (INKP, TKIM, NIKL, BRPT, SMBR). Tanpa 5 saham itu CAGR -2,9%, padahal bobot sama tanpa 5 penyumbang terbesarnya masih +1,9%. Gagal b1 dan b2 di semua skenario, b3 juga gagal di S2 dan S3.
- Klaim literatur (lebih stabil, tidak terkonsentrasi, volatilitas separuh) **tidak terlihat di data ini**: konsentrasi laba hampir sama dengan H22, drawdown lebih dalam (-47% vs -35,5%), turnover lebih tinggi, Sharpe lebih rendah. Sebagian besar pegangannya sama dengan H22 (korelasi 0,89).
- Sesuai kelemahan yang dicatat sebelum uji, kekuatan statistik dev rendah (6 tahun, ±55 saham, N ±12). Hasil ini berbobot ringan, tapi aturan pra-registrasi tetap berlaku: dev gagal → holdout tidak dibuka, ditutup tanpa variasi.
- **Temuan data (terpisah dari vonis)**: harga Yahoo MAPI (2, 4, 14 Mei 2018), ELTY (beberapa hari 2-14 Mei 2018) dan ATIC (2 Mei 2018) tercatat 1/10 dari seharusnya di sekitar aksi korporasi; TMAS sekali (23 Mei 2023). Pembanding bobot sama dev "membeli" MAPI di open 2 Mei 2018 seharga 82,5 lalu menilainya 815, sehingga MAPI menyumbang +22,9 poin laba palsu ke pembanding (saham berikutnya 6,7). H30 dan H22 tidak memegang saham itu di tanggal tersebut. Efeknya: pembanding bobot sama terlalu tinggi (merugikan strategi di a1, a1 tetap lulus); tes b1/b2 membuang MAPI dari pembanding, jadi vonis tidak berubah. Pembanding bobot sama H21/H22 dev lama juga terkena; vonis lama tidak diubah. Perbaikan data menunggu keputusan user.
- **Pembaruan angka karena koreksi data harga 2026-11-02 (bukan perubahan aturan; vonis tetap GAGAL).** Bobot sama Feb 2014-2019 7,27% → 4,98%. Dasar: CAGR 10,90% vs 4,98% ✔, JII 5,07% ✔, b1 -3,12% vs 1,70% ✘, b2 -6,15% vs -0,02% ✘, b3 5,35% vs 0,29% / JII 2,63% ✔ (3/5). S1 3/5 (9,39%), S2 2/5 (tidak berubah), **S3 3/5 (b3 berbalik lulus: 3,41% vs 1,05% / JII 2,63%)**. Turun terdalam bulanan -47,03%. H22 periode sama 13,41% / -35,52%. Hasil lama di `hasil_riset/h30_dev_pra_koreksi_20261102`.

## Koreksi data harga Yahoo (2026-11-02, atas persetujuan user; perbaikan data, bukan uji baru)
Pemicu: temuan H30 (MAPI Mei 2018 tercatat 1/10). Deteksi menyeluruh di `harga` (921 kode) dan `harian` (613 kode), semua tanggal, dicocokkan dengan close resmi IDX (`idx_harian`, 2020+). Modul `backend/ingest/koreksi_harga.py`, registry `lab_data.koreksi_harga` (11.352 dokumen: 11.302 aturan aktif + label/periksa; tiap aturan menyimpan nilai asli, nilai baru, alasan, bukti). Data asli 453 kode diarsip di GridFS `harga_asli/2026-11-02/`. Hanya `harga` yang dikoreksi; `harian` (data paper) belum, menunggu keputusan rencana sumber IDX untuk paper.
- K1 salah skala sementara (lompat di luar ARA/ARB lalu kembali ≤ 10 hari, harga ≥ Rp50, sebelum 2020): 46 sel dikali balik (rasio bersih ×2/×4/×5/×10, mis. MAPI/ELTY/TOWR/IBFN/BLTZ Mei 2018, SCCO Jun 2019), 67 baris dibuang (rasio tidak bersih, mis. ATIC, ASJT, kluster 23 Mar 2011 & 29 Agu 2012). Hari tanpa transaksi diisi close sebelumnya.
- K2 aksi korporasi tidak/salah disesuaikan Yahoo (2020+, faktor dari `Previous` IDX): 33 aturan faktor (semua harga sebelum awal jendela penyesuaian Yahoo dikali faktor, volume dibagi), mis. ENRG, VKTR, PACK, FORU, FISH, COCO, INET, SCCO 2024, BBRI 2021. 11 perubahan acuan IDX < 10% tanpa jendela/split (BABP, BBRI 2021-09, BBTN, BBYB, BEKS, DNAR, FASW, KIOS, TPIA) tidak dikoreksi (status `periksa`).
- K3 bar basi Yahoo (volume 0, harga lama, padahal IDX ada transaksi): 4.810 sel diganti data IDX × faktor; 14 rentang beku panjang yang menyambung ke 2020 dibuang (ADMF, ARGO, ASRM, BATA, BCIC, BKSL, BNBR, DART, MAIN, MITI, MYTX, SMMA, TIRA, VICO).
- K4: 2020+ 6.331 sel yang menyimpang > 5% dari IDX × faktor diganti data IDX. Sebelum 2020 hanya dengan bukti dokumen: NISP 18-20 Apr 2018 ×2 (bonus 1:1), KOPI rentang beku sebelum relisting 4 Mei 2015 dibuang. 39 lainnya diberi label tanpa koreksi: 26 tidak terverifikasi (mis. NIKL 2016, ANTM 2012, MAIN 2014, LPPF), 8 hari awal pencatatan, 5 lonjakan nyata menurut berita (BDMN 2012, TAXI 2016, BEKS 2016, ABBA 2019, HERO 2012).
- Verifikasi: sesudah koreksi tidak ada baris 2020+ yang menyimpang > 10% dari close IDX × faktor; 98 lompatan palsu di luar ARA/ARB hilang; sisa 9 "lompatan" = celah data setelah rentang beku dibuang.
- Pengunduh (`kumpul_data`): koreksi diterapkan ke setiap unduhan (pengecekan nilai asli, aman diulang); unduh penuh dipaksa bila ada aturan faktor dalam jendela 21 hari atau close Yahoo berubah ≥ 2% di ≥ 2 hari tumpang-tindih (dulu hanya rasio adj/close dicek, sehingga penyesuaian aksi korporasi Yahoo hanya tertimpa 21 hari terakhir). Diuji di `lab_data_tes`: pembaruan 21 hari dan unduh penuh identik dengan data terkoreksi.

**Hitung ulang sebelum/sesudah (2026-11-02, tanpa menulis `backtest_*`, `batas_paper`, `hasil_riset`; holdout H21/H22/H30 tetap tertutup).** "Sebelum" dijalankan ulang di salinan data asli dan sama persis dengan angka tersimpan. Harga eksekusi H11a/H29 memakai `harga` saja (sebelumnya `harga` + `harian`; tanpa koreksi hasilnya identik).

| | Sebelum | Sesudah | Vonis |
|---|---|---|---|
| H11a dev 2010-2019 (median 100 MC) | 9,0% (8,3..9,6), DD -25,5% | 9,1% (8,3..9,7), DD -25,6% | paper, tidak berubah |
| H11a 2020+ | 22,8% (20,0..27,5), DD -38,0% | **20,9% (17,9..24,2), DD -41,9%** | paper, tidak berubah |
| H11a 2020+ konservatif | 22,1%, DD -37,9% | 20,3% (17,7..23,4), DD -41,8% | |
| H29 dev | 14,9%, DD -28,6% | 14,9%, DD -28,6% (bobot sama 7,8 → 6,3%) | paper, tidak berubah |
| H29 2020+ | 15,2% (13,8..17,3), DD median -42,4% (terburuk -44,2%) | 14,9% (13,4..16,5), DD median **-44,0%** (terburuk **-46,2%**) | paper, tidak berubah |
| H21 dev | 6,25% vs bobot sama 7,80%; sens S1 ✔ S2 ✘ S3 ✘ S4 ✘ | 6,18% vs 6,28%; S1 ✔ S2 ✘ S3 ✘ (2,77 vs batas 4,27) **S4 ✔** | gagal (S2, S3), tidak berubah |
| H22 dev | 18,79% vs 7,80%; S1 ✘ (k5 7,73 vs 7,80) S2 ✘ S3 ✔ | 18,79% vs 6,28%; **S1 ✔** (k5 7,21 vs 6,27) S2 ✘ (-1,37 vs 3,57) S3 ✔ | gagal (S2), tidak berubah |
| H30 dev | 11,20% vs 7,27%; dasar 3/5, S1 3/5, S2 2/5, S3 2/5 | 10,90% vs 4,98%; dasar 3/5, S1 3/5, S2 2/5, **S3 3/5** (b3 lulus) | gagal (b1, b2 semua skenario), tidak berubah |

Penyebab utama turunnya H11a 2020+: 21 dari 697 sinyal berubah; PDPP 2024 (bar basi Yahoo Jan-Mar 2024 menyembunyikan penurunan, stop kena 30 Apr bukan 23 Jul: +51% → +19%), MPMX 2022 (68 bar basi, muncul 2 trade rugi), PACK 2026 (setelah aksi korporasi disesuaikan muncul breakout yang rugi -26%). Bobot sama dev turun 7,80 → 6,28% karena laba palsu MAPI Mei 2018 hilang. Catatan: batas GAGAL H29 (DD paper -45%, dikunci) kini terlampaui oleh simulasi terburuk 2020+ (-46,2%) dan median simulasi -44,0%; kriteria tidak diubah.

## Analisis cara masuk ke JII: sekaligus vs cicil vs cicil + tambah saat turun (dikunci 2026-11-07 atas permintaan user, sebelum kode dibuat dan sebelum ada angka return apa pun; deskriptif, bukan uji strategi) — SELESAI 2026-11-07
Id `analisis_cicil_jii`. Awalnya dari brief "H31"; atas keputusan user 2026-11-07 dijadikan **analisis deskriptif**, bukan hipotesis: tidak masuk katalog H, standar seragam tidak berlaku (bukan pencarian edge, tapi perbandingan cara masuk ke aset yang sama). Pra-registrasi tetap: aturan, kriteria, dan pembagian dev/holdout ditulis di sini sebelum dijalankan, tidak diubah setelah melihat hasil, holdout tertutup sampai user membukanya.

**Pertanyaan.** Untuk dana tetap yang mau dimasukkan ke indeks saham syariah, cara masuk mana yang hasilnya lebih baik: sekaligus, dicicil rata, atau dicicil dengan porsi lebih besar saat indeks turun?

**Data.**
- JII = `indeks/JKII` (close harian Yahoo, 3 Jul 2000 - 23 Okt 2026, close cocok 100% dengan IDX), dibaca lewat `harga.indeks`. Registry `koreksi_harga` hanya untuk saham; JII tidak ditarik ulang. Cek sebelum dikunci (tanpa return): 0 nilai kosong/nol, ±240 hari bursa per tahun, jeda terpanjang 12 hari kalender (libur).
- **Nilai aset = JII + dividen 2,5%/th diakru harian** (keputusan user, sama dengan pembanding JII H22/H30: close × 1,025^(hari kalender/365,25)). Versi harga saja (tanpa dividen) dilaporkan, bukan kriteria.
- **Sinyal turun memakai close harga JII (tanpa dividen).**
- Bunga kas: skenario utama 0%; sensitivitas 4%/th (diakru harian, 1,04^(hari/365,25)). Skenario ketiga (seri pasar uang syariah) **tidak dipakai**: NAV RD di repo baru ada sejak ±2013 (`rd_yakin.bulanan`, 166 bulan), tidak menutup dev 2010.
- Biaya (keputusan user): beli 0,15% + 0,4% = **0,55%** dari setiap pembelian, jual 0,25% + 0,4% = **0,65%** sekali di akhir horizon (sama untuk semua cara). 0,4% per sisi menggantikan 1 tick, karena indeks tidak punya tick; total ±1,2% pulang-pergi sama dengan model proyek. Setoran X → nilai aset X × (1 − 0,0055).

**Aturan (dana total = 100).**
| Kode | Nama | Aturan |
|---|---|---|
| `lump` | Sekaligus | 100 masuk di bulan ke-1 |
| `dca` | Cicil rata | 100/12 masuk tiap bulan selama 12 bulan |
| `dca_turun` | Cicil + tambah saat turun | Cicilan dasar 100/12 per bulan. Kalau JII di akhir bulan sebelumnya turun ≥ 10% dari tertinggi 250 hari bursa → cicilan bulan itu 2×; ≥ 20% → 3×. Cicilan tidak boleh melebihi sisa dana. Sisa di bulan ke-12 masuk semua di bulan ke-12. |

Detail eksekusi (yang tidak disebut di brief, diisi saat dikunci):
- Tanggal mulai = hari bursa terakhir bulan M (kalender JII). Pembelian ke-k (k = 1..12) di close hari bursa terakhir bulan M+k−1. `lump` beli semua di tanggal mulai.
- Sinyal `dca_turun` untuk pembelian ke-k: close JII di hari bursa terakhir bulan M+k−2 dibanding tertinggi close 250 hari bursa yang berakhir di hari itu (hari itu ikut). Jadi pembelian ke-1 memakai akhir bulan sebelum tanggal mulai. Harga hari beli tidak dipakai.
- Akhir horizon H tahun = hari bursa terakhir bulan M+12H. Seluruh aset dijual di close hari itu (biaya jual 0,65%); kas sisa (hanya mungkin di skenario yang belum habis, seharusnya tidak ada) ikut dihitung.
- Tidak ada penjualan di tengah.
- Kas berbunga (skenario 4%): cicilan dasar tetap nominal 100/12; tiap pembelian = min(kelipatan × 100/12, kas saat itu), dan pembelian ke-12 = seluruh kas (bunga ikut masuk). Berlaku sama untuk `dca` dan `dca_turun`. Dana dianggap habis saat kas ≤ 1e-9.

**Ukuran per tanggal mulai × cara × horizon × skenario.**
- `nilai_akhir`: nilai setelah biaya jual, dari dana 100.
- `dd_maks`: drawdown maksimum harian nilai portofolio (aset sebelum biaya jual + kas) dari tanggal mulai sampai akhir horizon, puncak awal = 100.
- `bulan_di_bawah_modal`: jumlah akhir bulan k = 1..12H di mana nilai aset (sebelum biaya jual) < total dana yang sudah disetor ke aset sampai bulan itu (termasuk biaya beli). Bulan ke-0 tidak dihitung (selalu di bawah karena biaya beli).
- `bulan_dana_habis`: pembelian ke berapa dana 100% sudah masuk (`lump` 1, `dca` 12, `dca_turun` 1-12).
- Menang = `nilai_akhir` lebih besar (sama persis = tidak menang).

**Periode.**
- Dev: tanggal mulai Jan 2010 - Des 2018 (108 tanggal mulai). Harga yang dipakai: 2009 (sinyal 250 hari) s/d Des 2021 (3 th) / Des 2023 (5 th).
- Holdout: tanggal mulai Jan 2019 s/d tanggal mulai terakhir yang horizonnya lengkap (data JII terakhir 23 Okt 2026). **Tertutup** sampai user memintanya.

**Kriteria (horizon 5 tahun, skenario utama: dividen 2,5%, bunga 0%, ambang 10%/20%).** `dca_turun` lebih baik dari `dca` kalau semua terpenuhi:
1. `nilai_akhir` menang di ≥ 60% tanggal mulai dev, **dan**
2. median `dd_maks` `dca_turun` tidak lebih buruk lebih dari 2 poin persen dari median `dd_maks` `dca`, **dan**
3. di horizon 3 tahun (skenario sama), persen menang `dca_turun` vs `dca` tidak di bawah 50%.

`lump` hanya pembanding deskriptif (seberapa sering menang, seberapa besar selisih).

**Laporan saja (tidak mengubah kriteria):**
- Ambang 7%/15% dan 15%/25%.
- Buang tanggal mulai di 12 bulan sebelum s/d 12 bulan sesudah bulan titik terendah terbesar: drawdown close JII (harga) terhadap tertinggi berjalan sejak 1 Jan 2010, dasar terdalam yang tanggalnya di Jan 2010 - Des 2018 (dicari otomatis oleh kode).
- Dev dipisah dua kelompok (permintaan user): tanggal mulai 2010-2014 (jendela 5 th tidak menyentuh 2020) dan 2015-2018.
- Versi harga saja (tanpa dividen) dan bunga kas 4%.
- Ringkasan per cara × horizon × skenario: median, p10, p90 `nilai_akhir`; median `dd_maks`; median `bulan_di_bawah_modal`; persen menang vs `dca` dan vs `lump`.

**Output.** `backend/research/analisis_cicil_jii.py`; hasil per tanggal mulai + ringkasan di `hasil_riset/analisis_cicil_jii_dev` (dengan `versi_data`: `dt.versi("indeks/JKII")`, sidik close JII yang dipakai, status cek kualitas terakhir). CSV sementara hanya di scratchpad (di luar repo), tombol unduh menyusul.

**Kelemahan (dicatat sebelum dijalankan):**
- JII tidak bisa dibeli langsung; dianggap lewat RD indeks/ETF tanpa tracking error dan tanpa biaya pengelolaan. Dividen 2,5%/th asumsi tetap.
- Jendela bergulir tumpang tindih: 108 tanggal mulai tidak independen. Jendela 5 th yang mulai berdekatan hampir sama, jadi "persen menang" bisa ditentukan oleh 1-2 kejadian pasar besar.
- **Jendela dev 2015-2018 tumpang tindih dengan harga periode holdout** (2019-2023, termasuk Covid 2020). Holdout tidak bersih: JII 2001-2014 sudah dipakai H20/H23, 2020+ sudah terlihat di banyak uji.
- `cek_kualitas_data` hanya memeriksa saham, bukan indeks; untuk JII hanya cek kelengkapan di atas.
- Hasil hanya berlaku untuk dana yang sudah ada di tangan (bukan gaji bulanan, yang memang harus dicicil).

### Hasil analisis cicil JII dev (2026-11-07, dijalankan sekali, `backend/research/analisis_cicil_jii.py --periode dev`, hasil `hasil_riset/analisis_cicil_jii_dev`): kriteria TERPENUHI 3/3 (tipis), holdout tertutup
108 tanggal mulai (Jan 2010 - Des 2018), harga JII s/d 29 Des 2023, sidik close `3983a128…`. Skenario utama: dividen 2,5%, bunga 0%, ambang 10%/20%.

| Kriteria | Nilai | Hasil |
|---|---|---|
| 1. 5 th: `dca_turun` menang vs `dca` ≥ 60% | 62,96% (68 menang, 16 kalah, 24 sama persis karena tidak pernah 2×) | ✔ (selisih 3 tanggal mulai dari batas) |
| 2. 5 th: median `dd_maks` tidak lebih buruk > 2 poin | -25,21% vs -25,21% (selisih 0) | ✔ |
| 3. 3 th: persen menang ≥ 50% | 62,96% | ✔ |

Ringkasan skenario utama (median `nilai_akhir` dari 100, p10-p90; median `dd_maks`; median bulan di bawah modal):
| Cara | 3 th | 5 th | DD 5 th | Bawah modal 5 th | Menang vs `lump` (5 th) |
|---|---|---|---|---|---|
| `lump` | 115,1 (86,9-137,0) | 113,6 (87,5-150,1) | -25,2% | 9 | |
| `dca` | 111,4 (84,4-130,0) | 112,6 (85,9-140,0) | -25,2% | 10,5 | 30,6% |
| `dca_turun` | 114,0 (85,3-132,9) | 112,2 (85,8-141,3) | -25,2% | 10 | 34,3% |
`lump` menang vs `dca` di 69,4% tanggal mulai (median selisih +4,3 poin), vs `dca_turun` 65,7% (+2,7 poin). Dana `dca_turun` habis median di bulan ke-10 (bulan 5-12).

Laporan saja:
- Ambang 7%/15%: menang 76,9% ✔; **15%/25%: 41,7% ✘** (kriteria 1 dan 3).
- Skenario lain (ambang 10/20): bunga 4% 58,3% (di bawah 60), harga saja 59,3%, harga saja + bunga 4% 55,6%.
- Titik terendah terbesar dev: 28 Sep 2015 (-26,2% dari puncak sejak 2010); tanpa 25 tanggal mulai Sep 2014 - Sep 2016: 63,9%, kriteria tetap terpenuhi.
- Kelompok: mulai 2010-2014 70,0% ✔; mulai 2015-2018 54,2% (kriteria 1 ✘). Jendela 2015-2018 tumpang tindih dengan harga periode holdout (2019-2023, termasuk Covid 2020).
- Per tahun mulai, `dca_turun` menang vs `dca`: 2010 75, 2011 100, 2012 67, 2013 83, 2014 25, 2015 92, 2016 33, 2017 0, 2018 92 (%).
- Saat hasilnya beda, selisih `dca_turun` - `dca` median +1,35 poin (min -1,6, maks +9,4).

Catatan (tidak mengubah kriteria):
- **Kriteria 3 otomatis sama dengan kriteria 1**: setelah bulan ke-12 kedua cara sudah 100% di aset yang sama tanpa kas, jadi pemenangnya hanya ditentukan jumlah unit, sama di horizon berapa pun (pemenang 3 th = 5 th di semua 108 tanggal mulai). Kelemahan desain yang baru terlihat setelah dijalankan.
- **Kriteria 2 hampir pasti lolos**: penurunan terdalam 5 th didominasi penurunan setelah dana masuk semua, yang persentasenya sama untuk kedua cara.
- Kesimpulan rapuh: lolos tipis (68 vs batas 65), berbalik di ambang 15/25, dengan bunga kas 4%, dengan harga saja, dan di kelompok 2015-2018. Keunggulannya kecil (median +1,35 poin dari 100 selama 5 tahun) dan ditentukan beberapa episode turun (2011, 2013, 2015, 2018).
- Yang konsisten: sekaligus (`lump`) mengalahkan kedua cara cicil di ±65-70% tanggal mulai.

### Hasil analisis cicil JII holdout (2026-11-07, dibuka sekali atas permintaan user, `analisis_cicil_jii.py --periode holdout`, hasil `hasil_riset/analisis_cicil_jii_holdout`): kriteria TERPENUHI 3/3, sampel terlalu kecil untuk disimpulkan
Aturan, skenario, dan uji kerapuhan sama persis dengan dev (kode dev dijalankan ulang setelah periode holdout ditambahkan: hasil identik). Data JII dipotong 30 Sep 2026 (data terakhir 23 Okt 2026, jadi Oktober belum punya hari bursa terakhir). Tanggal mulai: **horizon 3 th 57 (Jan 2019 - Sep 2023), horizon 5 th hanya 33 (Jan 2019 - Sep 2021)**. Sidik close `0dba37fc…`.

**Jumlah tanggal mulai 5 th (33) kurang untuk disimpulkan**: semuanya dalam rentang 33 bulan dan saling tumpang tindih, jadi praktis hanya satu episode pasar (Covid Mar 2020, turun -45,8%, lalu 2021-2022). Uji tanpa ±12 bulan di sekitar titik terendah hanya menyisakan 8 tanggal mulai 5 th.

| Kriteria | Nilai | Hasil |
|---|---|---|
| 1. 5 th: `dca_turun` menang vs `dca` ≥ 60% | 72,7% (24 menang, 9 kalah, 0 sama; n = 33) | ✔ |
| 2. 5 th: median `dd_maks` tidak lebih buruk > 2 poin | -36,95% vs -36,95% (selisih 0) | ✔ |
| 3. 3 th: persen menang ≥ 50% | 56,1% (32 menang, 20 kalah, 5 sama; n = 57) | ✔ |

Ringkasan skenario utama (median `nilai_akhir` dari 100, p10-p90; median `dd_maks`; median bulan di bawah modal):
| Cara | 3 th (n = 57) | 5 th (n = 33) | DD 5 th | Bawah modal 5 th | Menang vs `lump` (5 th) |
|---|---|---|---|---|---|
| `lump` | 94,5 (76,9-106,6) | 85,2 (77,6-106,2) | -39,0% | 41 | |
| `dca` | 96,3 (77,5-109,4) | 93,2 (75,2-108,2) | -37,0% | 32 | 60,6% |
| `dca_turun` | 98,7 (76,3-113,9) | 95,9 (77,8-108,1) | -37,0% | 22 | 69,7% |
`lump` menang vs `dca` hanya di 39,4% (5 th) / 36,8% (3 th) tanggal mulai, vs `dca_turun` 30,3% / 33,3%. Median dana `dca_turun` habis di bulan ke-6 (4-11). Median nilai akhir semua cara < 100: JII + dividen 2,5% turun di periode ini.

Laporan saja:
- Ambang 7%/15%: 5 th 63,6% ✔, **3 th 45,6% ✘**; 15%/25%: 75,8% / 59,6% ✔.
- Skenario lain (ambang 10/20, 5 th / 3 th): bunga 4% 69,7 / 52,6; harga saja 69,7 / 54,4; harga saja + bunga 4% 66,7 / 50,9 (semua terpenuhi).
- Titik terendah terbesar holdout: 24 Mar 2020 (-45,8%); tanpa 25 tanggal mulai Mar 2019 - Mar 2021: 5 th 75,0% (n = 8), **3 th 43,8% ✘** (n = 32).
- Kelompok 2010-2014 / 2015-2018 tidak berlaku di holdout.
- Per tahun mulai, `dca_turun` menang vs `dca` (3 th): 2019 58, 2020 75, 2021 92, 2022 42, 2023 0 (%).

Dev vs holdout: kriteria `dca_turun` vs `dca` terpenuhi di keduanya (dev tipis 63,0%, holdout 72,7% dari 33 tanggal mulai), tapi rapuh di uji kerapuhan masing-masing. Arah `lump` **berbalik**: dev menang ±65-70%, holdout kalah (menang ±30-39%).

### Status: SELESAI (2026-11-07, kesimpulan dari data, pilihan user)
Tidak ada pemenang tegas, tidak ada rekomendasi cara masuk.
- `dca_turun` vs `dca`: kriteria pra-registrasi terpenuhi di dev (63,0%) dan holdout (72,7%, 33 tanggal mulai), tapi rapuh (gagal di sebagian uji kerapuhan di kedua periode) dan untungnya kecil (median ±1-2 poin per 100 dana selama 5 tahun). Kriteria 2 dan 3 nyaris otomatis lolos karena desain (lihat catatan dev), jadi bobot bukti praktis hanya kriteria 1.
- `lump` vs cicil bergantung periode: dev (2010-2018, pasar naik bertahap) sekaligus menang ±65-70%; holdout (2019-2021, Covid lalu JII melemah) sekaligus kalah, menang hanya ±30-39%.
- Holdout 5 th terlalu kecil untuk disimpulkan (33 tanggal mulai tumpang tindih, praktis satu episode pasar).
- Tidak ada uji lanjutan atau variasi (ambang, horizon, aset) dari analisis ini.

## H31: H20 dengan kas = NAV reksa dana pasar uang syariah asli (dikunci 2026-11-07 atas permintaan user, sebelum kode uji dibuat dan sebelum ada angka return apa pun) — uji ulang pasca hasil
**Uji ulang pasca hasil (lencana `pasca_hasil`).** H20 gagal di kriteria 5 (kas 0%): kemampuannya menyamai beli-tahan bergantung pada asumsi bunga kas (FRED antarbank − 1,5%). H31 menguji sinyal H20 yang **persis sama**, hanya kas diganti NAV asli RD pasar uang syariah. Periode dan sinyal H20 sudah pernah dilihat (dev H20 2001-2014, eksplorasi H20 2020+), jadi hasilnya bukti lemah: lulus = kandidat uji maju untuk lapisan saham inti, bukan diadopsi. **Tujuan: mengurangi drawdown, bukan menambah return.** Satu hipotesis, tanpa varian. Gagal = ditutup tanpa variasi jumlah bulan, jenis MA, jeda, RD, atau instrumen. (Nama "H31" pernah dipakai di brief analisis cicil JII; analisis itu tidak masuk katalog H.)

Cek data sebelum dikunci (2026-11-07, hanya kelengkapan, tanpa return strategi):
- NAV harian Pasardana RD pasar uang syariah baru ada sejak Okt 2025 → tidak dipakai. NAB bulanan OJK (`swing.rd_ojk`, tipe Money Market Fund, syariah): 109 produk, Jun 2013 s/d Sep 2026; jumlah produk 1 (2013), 3 (2014), 10 (2015), 14-23 (2016-2017), 33-69 (2018-2026).
- Riwayat terpanjang (dipilih karena panjang, bukan hasil): **BNIAM Dana Lancar Syariah** (kunci `BNIAM DANA LANCAR SYARIAH|BANK MAYBANK INDONESIA`, fund Pasardana 380), Jun 2013 s/d Sep 2026, 157 dari 160 bulan (hilang 2018-06, 2018-12, 2019-02), tidak ada bulan |return| > 1,5%, NAB terkecil Rp10 M.

Data & instrumen:
- **JII**: sama persis dengan H20 (`indeks/JKII` close lewat `backend/db/harga.py` `indeks`, + dividen 2,5%/th − expense 2,0%/th diakru harian; open tidak dipakai).
- **Kas**: NAV bulanan OJK BNIAM Dana Lancar Syariah. Return bulan m = NAV akhir m ÷ NAV akhir m−1, dibagi rata geometris ke hari bursa JII di bulan m. Bulan NAV hilang: return dari NAV terakhir yang ada ke NAV berikutnya dibagi rata ke semua hari bursa di bulan-bulan itu. NAV sudah bersih dari biaya pengelolaan (tanpa potongan tambahan); keuntungan RD tidak dipajaki di investor; biaya beli/jual RD 0%.
- **Biaya JII** (model proyek, sama dengan H20): keluar 0,70% (fee jual 0,25% + 1 tick 0,45%), masuk 0,60% (fee beli 0,15% + 1 tick 0,45%).

Aturan (sinyal = H20 persis):
- Sinyal di close hari bursa terakhir tiap bulan: JII < rata-rata 10 close akhir bulan (termasuk bulan ini) → posisi berikutnya KAS (RD); ≥ → PASAR. Hanya bertindak kalau posisi berubah. Sinyal dihitung dari seluruh riwayat JII sejak 2000.
- Keluar (PASAR → KAS): jual JII di close hari bursa ke-1 bulan berikutnya (biaya 0,70%), hari ke-2 s/d 4 return 0, RD mulai berbunga hari ke-5.
- Masuk (KAS → PASAR): pencairan RD hari bursa ke-1 (bunga berhenti), hari ke-1 s/d 4 return 0, beli JII di close hari bursa ke-4 (biaya 0,60%).
- Beli-tahan (pembanding): JII + dividen 2,5% − expense 2,0%, satu kali biaya masuk 0,60%, tanpa perpindahan.

Periode (keputusan user 2026-11-07; data NAV terakhir Sep 2026):
- **Dev**: hari bursa pertama Jul 2013 s/d 31 Des 2019. Titik awal = close 28 Jun 2013 (hari bursa terakhir Jun 2013). Posisi awal H31 = sinyal akhir Jun 2013: kalau PASAR, H31 masuk seperti beli-tahan (biaya 0,60% di close hari bursa pertama Jul 2013); kalau KAS, RD berbunga sejak hari bursa pertama Jul 2013.
- **Holdout**: 1 Jan 2020 s/d 30 Sep 2026, **tidak bersih**. Dibuka SEKALI, hanya kalau dev lulus semua kriteria. Posisi awal = posisi H31 di akhir dev; beli-tahan dianggap sudah memegang (tanpa biaya masuk); CAGR, DD, dan jendela dihitung dari ekuitas awal Jan 2020 (puncak di-reset).
- **Catatan bobot bukti holdout (permintaan user):** kriteria 1-2 di holdout sudah praktis diketahui dari eksplorasi H20 2020+ (DD -26,1% vs -57,5%, CAGR -3,0% vs -10,4%, kas FRED). Bobot bukti holdout ada di kriteria **3, 5, dan 7**.

Kriteria lulus (dev dan holdout, semua harus terpenuhi):
1. Max drawdown H31 ≤ 2/3 × max drawdown beli-tahan JII.
2. CAGR H31 ≥ CAGR beli-tahan − 2%/th (ongkos asuransi maksimum; return tidak perlu lebih tinggi).
3. **Timing, bukan sekadar porsi saham lebih kecil**: campuran tetap JII (+ dividen/expense sama) dan RD yang sama, porsi JII = % hari H31 berada di pasar (1 − % hari di kas/transit), dikembalikan ke porsi itu tiap close hari bursa terakhir bulan, tanpa biaya. Lulus kalau max DD H31 lebih dangkal dari max DD campuran **dan** CAGR H31 ≥ CAGR campuran − 1%/th.
4. Rata-rata perpindahan ≤ 3 per tahun (setiap keluar = 1, setiap masuk = 1).
5. Jendela **3 tahun** bergulir (titik mulai tiap akhir bulan, ≥ 500 hari bursa): menang kalau DD H31 lebih dangkal dari DD beli-tahan **dan** CAGR H31 ≥ CAGR beli-tahan − 2%. Lulus kalau menang di ≥ 60% jendela.
6. Sensitivitas, masing-masing terpisah, kriteria 1-2 tetap lulus: 6a dividen 4%/th; 6b expense 1,6%/th.
7. Sensitivitas kas = median return bulanan semua RD pasar uang syariah IDR di `rd_ojk` yang punya NAV di bulan m−1 dan m (bulan tanpa satu pun: seperti bulan hilang di atas): kriteria 1-2 tetap lulus.

Standar seragam (keputusan user 2026-11-07 untuk bagian yang tidak cocok):
- a. Pembanding: beli-tahan JII, "di atas JII" = kriteria 1-2. Bobot sama universe syariah likuid **hanya dilaporkan** (H31 tidak memilih saham dan tujuannya DD): `uji_h21_h22.pembanding_sama` dev (universe & filter H22, tanpa biaya), dinilai ulang dari close 28 Jun 2013.
- b. Tanpa 5/10 saham terbaik: tidak berlaku (satu indeks). **Tanpa tahun kalender terbaik berlaku**: return harian tahun kalender terbaik H31 dibuang dari H31 dan tahun terbaik beli-tahan dibuang dari beli-tahan (2013 = Jul-Des ikut dihitung sebagai tahun), CAGR & DD dari sisa hari yang disambung; kriteria 1-2 tetap lulus.
- c. **S1 biaya 2 tick** berlaku: keluar 1,15%, masuk 1,05% (beli-tahan masuk 1,05%); kriteria 1-2 tetap lulus. S2 (Rp20 M) dan S3 (harga ≥ Rp200) tidak berlaku (tanpa universe saham).
- d. Lolos dev DAN holdout.
- e. Kualitas data: `cek_kualitas_data` hanya memeriksa saham; JII dan NAV dicek kelengkapan + lonjakan di kode uji. `versi_data` menyimpan `dt.versi("indeks/JKII")`, sidik close JII, sidik seri NAV yang dipakai, dan `harga.status_koreksi()`.

Hanya dilaporkan (bukan syarat):
- Kas 0% (pengganti kriteria 5 H20; keputusan user).
- Jeda pencairan RD 7 hari bursa: masuk = pencairan hari bursa ke-1, return 0 hari ke-1 s/d 8, beli JII di close hari bursa ke-8 (dana tiba T+7); keluar tidak berubah.
- Bobot sama universe syariah likuid (poin a).
Yang dilaporkan: CAGR, max DD, perpindahan/th, % waktu di kas, porsi & hasil campuran tetap, jendela menang, per tahun kalender, untuk dasar + semua skenario.

Kelemahan (dicatat sebelum uji):
- Satu RD saja, dipilih karena masih ada sampai sekarang (survivorship produk); NAV bulanan, bukan harian.
- Dev 6,5 tahun dengan ±1-3 kali pindah per tahun: kekuatan statistik rendah. Jul 2013 - Des 2014 sudah terlihat di dev H20; 2015-2019 sinyal H20 belum pernah dijalankan, tapi harga JII-nya sudah terlihat (analisis cicil JII).
- JII = indeks harga; dividen asumsi; eksekusi di close sedikit optimis (sama dengan H20). Kendaraan nyata = RD indeks syariah dengan biaya & jeda sendiri.
- Pencairan RD pasar uang nyata bisa sampai 7 hari bursa (dilaporkan).
- Uji ke ±47.

### Hasil H31 dev Jul 2013 - Des 2019 (2026-11-07, `backend/research/uji_h31.py --periode dev`, hasil `hasil_riset/h31_dev`): GAGAL, holdout tidak dibuka
Sebelum dijalankan, mekanisme dicek dengan data tiruan: keluar = return hari ke-1 × (1 − 0,70%), hari ke-2 s/d 4 return 0, RD berbunga mulai hari ke-5; masuk = return 0 hari ke-1 s/d 3, biaya 0,60% di close hari ke-4 (jeda 7: close hari ke-8). Satu bug sebelum uji diperbaiki: di holdout, sinyal akhir dev harus diproses di hari pertama holdout. Sesudah putaran pertama, baris 2013 (Jul-Des) hilang dari laporan per tahun (bug laporan saja, tidak dipakai kriteria mana pun); diperbaiki lalu dijalankan ulang, angka lain identik. `versi_data`: sidik close JII `9640098b05126973`, sidik NAV `43a6e373a616620c`, cek kualitas terakhir 2026-11-06 (status ADA TEMUAN, 0 temuan; hanya saham, tidak dipakai H31). Cek data: JII tanpa lonjakan > 15%, jeda terlama 12 hari kalender (libur Lebaran); NAV hilang 2018-06, 2018-12, 2019-02, tanpa lonjakan > 1,5%. Posisi awal = PASAR (sinyal Jun 2013). Periode efektif close 28 Jun 2013 s/d 30 Des 2019.

| Skenario | CAGR H31 | DD H31 | CAGR beli-tahan | DD beli-tahan | k1 | k2 |
|---|---|---|---|---|---|---|
| Dasar | 0,54% | -25,2% | 1,54% | -26,0% | ✘ (batas -17,4%) | ✔ |
| 6a. dividen 4% | 1,33% | -23,6% | 3,00% | -25,5% | ✘ | ✔ |
| 6b. expense 1,6% | 0,75% | -24,7% | 1,93% | -25,9% | ✘ | ✔ |
| 7. kas median RDPU syariah | 0,39% | -25,3% | 1,54% | -26,0% | ✘ | ✔ |
| S1 biaya 2 tick | -0,57% | -27,2% | 1,47% | -26,0% | ✘ | ✘ |
| Laporan: kas 0% | -1,78% | -29,2% | 1,54% | -26,0% | ✘ | ✘ |
| Laporan: jeda pencairan 7 hari | 0,45% | -26,0% | 1,54% | -26,0% | ✘ | ✔ |

Kriteria:
1. ✘ DD -25,2% vs batas 2/3 × -26,0% = -17,4%.
2. ✔ CAGR 0,54% vs batas -0,46%.
3. ✘ Campuran tetap 54% JII / 46% RD: DD -13,5%, CAGR 3,67%. H31 kalah di keduanya (DD lebih dalam, CAGR di bawah batas 2,67%).
4. ✔ 2,31 perpindahan/th (15 kali; H20 dev 1,24/th).
5. ✘ Menang di 47% dari 43 jendela 3 tahun.
6a/6b/7/S1 ✘ (kriteria 1 gagal di semua skenario).
Tanpa tahun terbaik ✘: H31 tanpa 2014 CAGR -1,05%, DD -25,2%; beli-tahan tanpa 2014 CAGR -1,30%, DD -29,2% (batas -19,5%).
Laporan: bobot sama universe syariah likuid (H22 dev, tanpa biaya) CAGR 2,19%, DD -34,5%.

Per tahun (%): 2013 (Jul-Des) H31 -1,5 / beli-tahan -10,1 / campuran -4,8; 2014 9,8 / 18,7 / 13,5; 2015 -4,5 / -12,3 / -3,7; 2016 7,0 / 15,6 / 11,6; 2017 -1,4 / 9,9 / 8,0; 2018 -3,6 / -9,3 / -3,0; 2019 -1,4 / 2,4 / 3,8.

Kesimpulan:
- Dengan kas realistis pun, di 2013-2019 filter MA10 **tidak mengurangi drawdown** (-25,2% vs -26,0%). JII periode ini tidak punya kejatuhan panjang seperti 2008. Yang ada penurunan pendek (2013, 2015, 2018) dan pemulihan cepat, sehingga sinyal bulanan keluar terlambat dan masuk lagi terlambat (whipsaw 15 kali).
- Memegang porsi tetap 54% JII + 46% RD (tanpa timing) jauh lebih baik di DD (-13,5%) dan CAGR (3,67%). Pengurangan risiko di periode ini datang dari porsi saham yang lebih kecil, bukan dari timing.
- Kas RD asli (±5%/th) vs kas 0% memang membantu (+2,3 poin CAGR), tapi tidak cukup menolong kriteria DD.
- Pelajaran tambahan (bukan bukti): hasil bagus H20 di dev 2001-2014 kemungkinan besar datang dari satu peristiwa (2008: -8% vs -56%).
- Sesuai aturan: GAGAL = ditutup, tanpa variasi. Holdout 2020+ tidak dibuka.

## H32: Frog-in-the-Pan (FIP) momentum (dikunci 2026-11-07 atas permintaan user, sebelum kode uji dibuat dan sebelum ada angka return apa pun)
Literatur: Da, Gurun & Warachka (2014), "Frog in the Pan: Continuous Information and Momentum", Review of Financial Studies 27(7), 2171-2218. Bukti internasional: Goyal, Jegadeesh & Subrahmanyam (2025), Review of Finance. Alasan (user): H22 dan H30 gagal karena hasilnya bergantung pada segelintir saham yang melonjak; FIP memilih saham momentum yang naiknya mulus (banyak hari naik kecil), bukan yang naik karena beberapa lonjakan. Satu hipotesis, tanpa varian. Gagal = ditutup tanpa variasi ukuran kelompok, jendela, atau cara menghitung ID.

Posisi di keluarga momentum (dari registry): yang bernama "momentum" = H11b, H22, H23 (dual momentum lintas aset), H29, H30 → **H32 = uji ke-6** (ke-5 kalau H23 tidak dihitung karena bukan momentum antar-saham; sinyal antar-saham yang benar-benar baru hanya H22 dan H30, H29 memakai ulang H22). Kategori "tren" seluruhnya (H11a + variannya) → ke-10. Seluruh katalog ±ke-48.

Sinyal (satu-satunya yang beda dari H22):
- **PRET** = return close tersesuaikan akhir bulan t−12 → akhir bulan t−1 (`uji_h21_h22.momentum`, sama persis dengan H22).
- **ID** = sign(PRET) × (%hari return negatif − %hari return positif). Return harian dari close tersesuaikan yang sama (`c`, ffill), hari bursa kalender IHSG sesudah akhir bulan t−12 s/d akhir bulan t−1 (bulan t dilewati seperti PRET). Penyebut = semua hari dengan return valid; hari return 0 (termasuk tanpa transaksi) ikut penyebut, tidak dihitung positif/negatif. Makin negatif ID = makin mulus.
- **Peringkat**: (1) kelompok momentum = 2N saham lolos dengan PRET tertinggi (N = rumus H22), diurutkan ID naik (seri: PRET lebih tinggi dulu); (2) lalu sisa saham lolos urut PRET turun; saham tanpa PRET tidak diranking.
- Mesin H22 tidak diubah: beli peringkat ≤ N, pegang selama ≤ 2N. Artinya beli N saham ID terendah di antara 2N momentum teratas; dijual saat keluar dari 2N teratas menurut PRET. Jumlah saham akhir = N, sama dengan H22.
- **Ukuran kelompok 2N (dipilih satu, disetujui user)**: N H22 = 20% saham lolos = kuintil teratas, jadi kelompok harus > N agar filter ID berarti; 2N (±40% teratas) = batas pegang H22 yang sudah dikunci, tidak ada angka baru, dan aturan jual tetap persis H22. Kelompok lebih besar menjauh dari paper (pilih di dalam momentum teratas).

Aturan lain = H22 persis (`uji_h21_h22.py`, cabang `h32` di `peringkat`; H22 dibuktikan identik sebelum uji): universe dev 766 kode DES 2019-2026; filter median nilai transaksi 60 hari ≥ Rp5 M, harga ≥ Rp100, data ≥ 250 hari, aktif ≥ 90%; sinyal close akhir bulan, eksekusi open hari bursa pertama; N = maks(10, 20% saham lolos); posisi baru 1/N, pangkas > 2/N; saham hilang & biaya ±1,2% pulang-pergi dari turnover nyata.

Periode:
- **Dev**: sinyal akhir Jan 2011, eksekusi Feb 2011 s/d Des 2019 (sama dengan H22).
- **Holdout**: Jan 2020 s/d Okt 2026, **tertutup**; dibuka sekali hanya kalau dev lulus, dengan izin user.

Kriteria = standar seragam penuh (semua harus lulus, daftar sama dengan H30):
- a1. CAGR bersih > bobot sama semua saham lolos (tanpa biaya).
- a2. CAGR bersih > JII + dividen 2,5%/th.
- b1. Tanpa 5 saham penyumbang laba terbesar: CAGR > bobot sama tanpa 5 penyumbang terbesarnya.
- b2. Tanpa 10 saham penyumbang laba terbesar: CAGR > bobot sama tanpa 10 penyumbang terbesarnya. (b1/b2 = tempat H22 dan H30 gagal.)
- b3. Tanpa tahun kalender terbaik: CAGR > bobot sama dan > JII, masing-masing tanpa tahun terbaiknya.
- S1 biaya 2 tick, S2 likuiditas ≥ Rp20 M, S3 harga ≥ Rp200 (pembanding ikut): a1-a2 dan b1-b3 tetap lulus.
- Lolos dev DAN holdout, tanpa pengecualian.

Pembanding H22 (wajib dilaporkan, **bukan syarat lulus**, keputusan user 2026-11-07): H22 dijalankan ulang dengan data, periode, dan versi data yang sama di semua skenario; dilaporkan CAGR, DD, b1/b2/b3 per skenario, korelasi bulanan H32 vs H22, % pegangan yang sama, 5 penyumbang terbesar masing-masing.

Kelemahan (dicatat sebelum uji):
- Dev tidak buta: pemenang H22 di dev (NIKL, BRPT, SMBR, TKIM, AKRA) dan hasil per tahunnya sudah terbuka.
- Kekuatan statistik rendah: ±58 saham lolos, kelompok ±24, N ±12, 9 tahun; pegangan kemungkinan besar banyak beririsan dengan H22.
- Dev bukan point-in-time (survivorship, status syariah); lompatan harga sebelum 2020 tanpa bukti dokumen tidak terverifikasi; open Yahoo 2010-2012 rusak.
- Pembanding bobot sama tanpa biaya (konservatif, disengaja). `versi_data` disimpan di hasil.

### Hasil H32 dev Feb 2011 - Des 2019 (2026-11-07, `backend/research/uji_h32.py --periode dev`, hasil `hasil_riset/h32_dev`): GAGAL, holdout tidak dibuka
Persiapan: `cek_kualitas_data` 2026-11-07 08:02 = 0 temuan; 6 aturan ditahan semuanya PPGL Okt-Nov 2026 (di luar dev). H22 dengan cabang baru dibuktikan identik dengan kode lama (selisih ekuitas 0, `PYTHONHASHSEED=0`, CAGR 18,79%). `versi_data`: sidik 805bc7de753a5142, 766 kode, 11.340 koreksi aktif. Catatan jalannya uji: run pertama berhenti karena error encoding saat mencetak nama skenario "≥", sebelum angka return apa pun tercetak dan tanpa hasil tersimpan; dijalankan ulang sekali dengan kode yang sama (`PYTHONIOENCODING=utf-8`).

Universe: rata-rata 58,4 saham lolos, N 11,9, kelompok momentum 23,7; 56,9% pilihan sinyal H32 = pilihan sinyal H22 di bulan yang sama.

| Skenario | H32 CAGR / DD | vs bobot sama | Tanpa 5 saham | Tanpa 10 saham | Tanpa tahun terbaik | H32 | H22 periode sama (laporan) |
|---|---|---|---|---|---|---|---|
| Dasar | 20,18% / -33,7% | 6,27% | 9,79% vs 3,82% | 3,40% vs 1,87% | 16,68% vs 3,46% / JII 5,30% | lulus 5/5 | 18,78% / -35,6%, lulus 5/5 |
| S1 biaya 2 tick | 18,35% / -34,9% | 6,27% | 8,21% vs 3,82% | 1,95% vs 1,87% | 14,95% vs 3,46% / JII 5,30% | lulus 5/5 | 17,12% / -37,5%, gagal 4/5 |
| S2 likuiditas ≥ Rp20 M | 7,17% / -39,8% | 3,57% | **-0,12% vs 0,25%** | **-3,51% vs -1,96%** | **4,98% vs 0,96% / JII 5,30%** | **gagal 2/5** | 7,24% / -44,1%, gagal 2/5 |
| S3 harga ≥ Rp200 | 19,61% / -35,1% | 6,60% | 9,87% vs 4,14% | 4,69% vs 2,11% | 16,53% vs 4,08% / JII 5,30% | lulus 5/5 | 22,90% / -30,1%, lulus 5/5 |

JII + dividen 2,5%/th: 6,96%, DD -22,68%. Angka CAGR/DD dari return bulanan (harian dasar 20,20% / -34,76%).

Per tahun (H32 / H22 / bobot sama): 2011 (Feb-Des) 41,9 / 36,9 / 12,9; 2012 30,2 / 26,6 / 17,0; 2013 0,7 / 13,6 / -5,5; 2014 36,8 / 37,2 / 24,3; 2015 -10,4 / -25,9 / -23,0; 2016 51,9 / 59,7 / 31,4; 2017 32,6 / 33,5 / 10,3; 2018 29,3 / 29,1 / -0,9; 2019 -13,3 / -15,8 / 0,3.

Lain-lain: volatilitas 21,8% (H22 24,5%), Sharpe 0,69 (H22 0,58), turnover 172,3%/th (H22 131,6%), kas rata-rata 4,2%. Korelasi bulanan dengan H22 0,93, 64,3% pegangan sama; korelasi dengan Follow Tren 0,65. Lima penyumbang terbesar INKP, TKIM, NIKL, BRPT, SMBR = 77,5% dari total laba (H22: TKIM, NIKL, INKP, BRPT, SMBR = 92,5%).

Kesimpulan:
- Gagal standar seragam di S2 (universe likuid Rp20 M): tanpa 5 dan tanpa 10 pemenang di bawah bobot sama, tanpa tahun terbaik di bawah JII. Dasar, S1, dan S3 lulus semua (S1 b2 sangat tipis, 1,95% vs 1,87%).
- Dibanding H22 di data dan periode yang sama (laporan, bukan syarat): sedikit lebih baik hampir di semua angka, termasuk lulus S1 yang gagal di H22, tapi pemenangnya sama dan korelasinya 0,93. Filter ID mengurangi ketergantungan pada lonjakan sedikit, tidak mengubah sifatnya.
- Pelajaran: H22, H30, dan H32 (tiga cara memilih momentum antar-saham) memberi pemenang yang sama, dan di saham yang benar-benar likuid hasilnya tetap bergantung pada segelintir saham yang naik besar.
- Sesuai aturan: GAGAL = ditutup, tanpa variasi ukuran kelompok, jendela, atau cara menghitung ID. Holdout 2020+ tidak dibuka.

## Penutupan keluarga momentum antar-saham (2026-11-07, keputusan user)
- Keluarga momentum antar-saham **H22 (RS 12-1), H30 (Residual Momentum), H32 (Frog-in-the-Pan) ditutup.** Ketiganya gagal standar seragam di dev dan berakhir di pemenang yang sama: INKP, TKIM, NIKL, BRPT, SMBR. Korelasi bulanan H30 vs H22 0,89, H32 vs H22 0,93. Cara memilih momentum yang berbeda tidak mengubah sumber hasilnya: segelintir saham yang naik besar, dan di universe likuid Rp20 M tes tanpa 5/10 saham terbaik gagal.
- **Tidak ada varian momentum antar-saham baru** (jendela lain, skor lain, filter tambahan, ukuran kelompok lain, gabungan sinyal) tanpa alasan yang benar-benar berbeda, misalnya data baru yang tidak tersedia saat H22/H30/H32 diuji, atau mekanisme ekonomi yang tidak bermuara pada peringkat return masa lalu. Alasan itu ditulis dan disetujui user sebelum kode dibuat.
- **H11a (Follow Tren) dan H29 (Momentum Blend) tetap jalan di paper trade** sesuai kriteria evaluasi yang sudah dikunci (H11a keputusan utama Okt 2027, H29 evaluasi 1 Nov 2027). Penutupan ini tidak mengubah aturan, data, atau jadwal kedua paper itu.

## Analisis penerbitan saham baru: apakah saham yang menerbitkan saham baru tertinggal setelahnya? (dikunci 2026-11-07 atas permintaan user, sebelum kode dibuat dan sebelum ada angka return apa pun; deskriptif, bukan uji strategi)
Id `analisis_penerbitan`. Awalnya diusulkan sebagai hipotesis H33 (bobot sama universe H22 dikurangi saham yang jumlah saham beredarnya naik > 5% dalam 12 bulan); atas keputusan user 2026-11-07 **tidak dikunci sebagai hipotesis** karena kekuatan statistiknya terlalu rendah (±5 dari ±56 saham universe per tahun terkena, 9 siklus dev), sehingga hasil uji kemungkinan besar "tidak terdeteksi". Diganti analisis deskriptif: tidak masuk katalog H, standar seragam tidak berlaku. Kalau hasilnya menunjukkan efek kuat (definisi di bawah), baru dibahas sebagai hipotesis (kemungkinan filter H11a); untuk itu keputusan user sudah dicatat: wajib di atas ketiga pembanding (bobot sama tahunan dengan biaya, bobot sama bulanan tanpa biaya, JII), konversi dan merger dihitung penerbitan, kasus diverifikasi sebelum backtest, dev = siklus Feb 2011 - Jan 2020.

**Literatur (campur, dicatat sebelum dijalankan).** McLean, Pontiff & Watanabe (JFE 2009, 41 negara): penerbitan saham memprediksi return lebih rendah, kuat. Rafik & Azmi (2019): underperformance pasca rights issue di Indonesia. Watanabe (2008): efeknya tidak ada di pasar berkembang. Sitasi dari user, belum dicek ulang.

**Data.**
- Jumlah saham beredar: `lab_data.ksei` kolom `saham` (KSEI BalanceposEfek akhir bulan, Des 2009 - Sep 2026, 202 bulan tanpa bolong). Dicek dengan kejadian yang diketahui: split BBCA ×5 Okt 2021, merger BRIS Feb 2021, split BBRI ×5 Nov 2017, HMETD BBRI Sep 2021 = cocok.
- Koreksi KSEI (2026-11-07, permintaan user; registry baru `lab_data.koreksi_ksei` lewat `backend/ingest/koreksi_ksei.py`, otomatis diterapkan di `ksei.bangun`; nilai asli + alasan + bukti disimpan): ADMF 2025-09, JTPE 2022-07, MSIN 2020-12, MFIN 2025-09 (persis ×100 bulan sebelumnya lalu kembali ke skala normal → nilai bulan sebelumnya); SMRA 2010-06 (8.673.140.840 → 6.873.140.840, digit tertukar); BUMI 2014-09 (52,97 M → 36,63 M: hasil HMETD 2014 hanya 15,85 M saham baru, 20,774 + 15,853 = nilai Okt 2014). Pola ×100 lain (BATA Sep 2013 dan MLBI Nov 2014 split 1:100, KOPI Mei 2014 reverse) adalah aksi korporasi sungguhan, tidak diubah. Tidak ada koreksi yang jatuh di nilai Desember kasus dev.
- Faktor split/reverse/saham bonus: `stock_splits` Yahoo (lewat `harga.banyak`). Dicek: saham bonus 1:1 SMRA Jun 2013 (bukti KSEI) tercatat sebagai split 2,0, jadi saham bonus ikut tersaring. Dividen saham diperlakukan sama bila Yahoo mencatatnya sebagai split.
- Sumber jadwal aksi korporasi yang dites (2026-11-07, Chrome Lab): `GetCalendar` IDX kosong untuk 2010-2017; `/primary/ListingActivity/GetIssuedHistory` (parameter `caType`, `dateFrom`/`dateTo` format `yyyymmdd`, `start`, `length`) ada sejak lama tetapi **tidak lengkap**: ±1 baris per emiten (1.791 baris untuk 1.029 kode; 2009-2019 hanya 6-67 baris per tahun), hanya 8 dari 42 kasus dev ditemukan. Dipakai sebagai bukti pendukung saja, tidak dijadikan sumber data. Pengumuman IDX di DB baru sejak 3 Jul 2023.
- Harga: `uji_h21_h22.susun` dengan konfigurasi dev diperpanjang sampai 31 Jan 2020 (data 1 Jan 2010 - 31 Jan 2020), harga adjusted Yahoo (dividen masuk), lewat `harga.py`. Cek kualitas terakhir 2026-11-07 08:02: 0 temuan; yang ditahan hanya PPGL Okt 2026 (di luar periode).

**Aturan.**
- Siklus Y = 2011..2019. Sinyal di close hari bursa terakhir Januari Y. Universe = `uji_h21_h22.lolos(S, t, 5e9, 100)` persis H22 dev (median nilai transaksi 60 hari ≥ Rp5 M, harga ≥ Rp100, ≥ 250 hari data, volume > 0 di ≥ 90% dari 250 hari; dev memakai semua kode yang pernah masuk DES, sama dengan H22 dev).
- Penerbitan bersih = saham KSEI akhir Des(Y−1) ÷ (saham KSEI akhir Des(Y−2) × hasil kali `stock_splits` Yahoo bertanggal sesudah tanggal KSEI Des(Y−2) s/d tanggal KSEI Des(Y−1)) − 1. Data KSEI Desember terbit sebelum akhir Januari (tanpa look-ahead).
- **Kejadian** = penerbitan bersih **> 5%**. Konversi (waran, obligasi, ESOP) dan merger dihitung penerbitan (keputusan user). Saham tanpa data KSEI di salah satu bulan → bukan kejadian, jumlahnya dilaporkan.
- Return 12 bulan setiap saham universe: beli di open hari bursa pertama Februari Y, nilai di close hari bursa terakhir Januari Y+1 (adjusted, dividen masuk, kotor tanpa biaya). Open ≤ 0/kosong → close hari itu (sama dengan `pembanding_sama`). Saham yang berhenti diperdagangkan > 30 hari sebelum akhir data bernilai 0 dan merger FREN → EXCL mengikuti `susun` (aturan H22).
- Pembanding per kejadian = rata-rata return 12 bulan semua saham universe siklus yang sama (bobot sama beli-tahan, termasuk saham kejadian). **Selisih** = return kejadian − pembanding.

**Ukuran.** Per kejadian: kode, siklus, penerbitan bersih, penyebab (tabel verifikasi di bawah), return, pembanding, selisih. Ringkasan: jumlah kejadian, **median selisih, rata-rata selisih, % kejadian tertinggal (selisih < 0)**, dan per siklus (jumlah kejadian, jumlah universe, pembanding, median & rata-rata selisih).

**Efek kuat** (ditetapkan sebelum dijalankan; semua harus terpenuhi):
1. median selisih ≤ −5 poin,
2. rata-rata selisih ≤ −5 poin,
3. ≥ 60% kejadian tertinggal,
4. median selisih per siklus negatif di ≥ 6 dari 9 siklus (siklus tanpa kejadian dihitung tidak negatif),
5. rata-rata selisih tetap negatif setelah 5 kejadian paling tertinggal dibuang.

**Laporan saja (tidak mengubah kesimpulan):** pembanding bobot sama tanpa saham kejadian; per penyebab (HMETD / tanpa HMETD / merger / konversi waran / campuran / belum bersumber); per besar penerbitan (5-20% vs > 20%); tanpa 5 kejadian paling unggul; uji tanda satu sisi (binomial) jumlah tertinggal.

**Periode.** Dev saja: siklus Feb 2011 - Jan 2020 (sinyal Jan 2011 - Jan 2019). **Kejadian siklus 2020+ tidak dihitung dan tidak dilihat** (kode menolak Y > 2019). Harga Jan 2020 ikut terpakai sebagai akhir siklus terakhir (disetujui user).

**Verifikasi 42 kasus dev (2026-11-07, sebelum return dilihat).** Semua 42 adalah penerbitan sungguhan, bukan split/bonus/salah cetak: tidak ada yang harganya turun sebanding jumlah saham di sekitar bulan perubahan (turun 1 hari terdalam vs 1/(1+kenaikan); MPPA 29 Apr 2010 turun ×0,84 = ex-date dividen Rp180), dan split di 5 kasus (MLPL, MEDC, PPRO, TPIA, IKAI) tanggalnya cocok dengan bulan KSEI. MLPL 2010: reverse 4:1 (7 Apr 2010, KSEI) lalu HMETD 9:32 → bersih KSEI +13,9% sebulan cocok. Penyebab bersumber 26/42, sisanya "belum bersumber" (tetap kejadian):

| Siklus | Kode | Bersih | Penyebab | Bukti |
|---|---|---|---|---|
| 2011 | AKRA | +20,9% | HMETD 5:1 | detik 21 Jan 2010 |
| 2011 | BLTA | +93,1% | HMETD | FinanceAsia / detik 2010 |
| 2011 | BSDE | +60,0% | HMETD | JPNN Nov 2010 |
| 2011 | BUMI | +7,1% | belum bersumber | rencana tanpa HMETD 10% 2010 |
| 2011 | ELTY | +100,4% | HMETD | detik 2010 |
| 2011 | ENRG | +181,8% | HMETD | Kontan (Rp4,84 T Feb 2010) |
| 2011 | LPKR | +25,0% | belum bersumber | |
| 2011 | MLPL | +355,6% | campuran (reverse 4:1 + HMETD 9:32) | KSEI |
| 2011 | MPPA | +18,1% | konversi waran Seri I | KSEI Apr 2010 |
| 2011 | SMRA | +6,8% | belum bersumber | |
| 2012 | KIJA | +43,8% | HMETD II | detik / jababeka.com |
| 2012 | LPKR | +6,7% | tanpa HMETD (1,45 M saham) | Bisnis 26 Mei 2011 |
| 2012 | PWON | +20,0% | HMETD 5:1 | KSEI / laporan tahunan 2011 |
| 2012 | UNTR | +12,1% | HMETD IV (403 jt saham) | Kontan |
| 2013 | ASRI | +10,0% | belum bersumber | |
| 2013 | ELTY | +9,0% | belum bersumber | |
| 2014 | BWPT | +10,4% | belum bersumber | |
| 2014 | MLPL | +30,2% | belum bersumber | |
| 2014 | SCMA | +50,0% | merger (Indosiar, efektif 1 Mei 2013) | Kontan |
| 2015 | AISA | +10,0% | tanpa HMETD | IDX GetIssuedHistory |
| 2015 | BUMI | +76,3% | campuran (HMETD sebagian + konversi utang) | Kontan / Bisnis |
| 2015 | BWPT | +605,1% | HMETD | IDX GetIssuedHistory |
| 2015 | MAIN | +5,7% | tanpa HMETD | IDX GetIssuedHistory |
| 2016 | ADHI | +97,7% | belum bersumber | |
| 2016 | ANTM | +151,9% | HMETD | IDX GetIssuedHistory |
| 2017 | AALI | +22,2% | HMETD | IDX GetIssuedHistory |
| 2017 | BTEK | +424,5% | HMETD | Bisnis Apr 2016 |
| 2017 | EXCL | +25,1% | belum bersumber | |
| 2017 | JPFA | +7,0% | tanpa HMETD (750 jt ke KKR) | Bisnis |
| 2017 | JSMR | +6,7% | HMETD | IDX GetIssuedHistory |
| 2017 | PTPP | +28,0% | HMETD | IDX GetIssuedHistory |
| 2017 | WIKA | +45,9% | belum bersumber | |
| 2018 | BUMI | +78,5% | belum bersumber | |
| 2018 | CTRA | +20,3% | belum bersumber | |
| 2018 | MEDC | +33,0% | belum bersumber (+ split 4, Yahoo) | |
| 2018 | PPRO | +9,8% | belum bersumber (+ split 4, Yahoo) | |
| 2018 | TKIM | +16,5% | konversi waran | Kontan |
| 2018 | TPIA | +8,5% | belum bersumber (+ split 5, Yahoo) | |
| 2019 | BRPT | +27,4% | HMETD | Kontan / Bareksa |
| 2019 | ERAA | +10,0% | belum bersumber | |
| 2019 | ESSA | +30,0% | HMETD 10:3 | Bisnis / Kontan |
| 2019 | IKAI | +664,2% | campuran (HMETD Jan + split 2 + HMETD akhir 2018) | Bareksa / Bisnis |

**Output.** `backend/research/analisis_penerbitan.py` (dijalankan sekali), hasil di `hasil_riset/analisis_penerbitan_dev` dengan `versi_data` (`dt.versi("ksei")`, sidik kolom `saham` KSEI kode universe, `harga.sidik` harga universe 2010-01-01 s/d 2020-01-31, `harga.status_koreksi()`, jumlah aturan `koreksi_ksei`).

**Kelemahan (dicatat sebelum dijalankan):**
- Sampel kecil (42 kejadian, 9 siklus); kejadian di siklus yang sama tidak independen (pasar sama).
- Survivorship: saham yang menerbitkan saham lalu delisting tidak ada di Yahoo → efek cenderung diremehkan.
- Universe dev bukan syariah point-in-time; K4 sebelum 2020 tidak terverifikasi; syariah point-in-time baru sejak Des 2019.
- Penyebab 16 kasus belum bersumber; pembagian per penyebab hanya laporan.
- Sinyal tahunan: penerbitan Feb-Des Y−1 baru terlihat Jan Y; sebagian efek (bila ada) mungkin sudah terjadi sebelum sinyal.

### Hasil analisis penerbitan dev (2026-11-07, dijalankan sekali, `backend/research/analisis_penerbitan.py`, hasil `hasil_riset/analisis_penerbitan_dev`): efek kuat TIDAK (3/5), tidak dilanjutkan jadi hipotesis
42 kejadian (sama persis dengan daftar verifikasi), universe 43-65 saham per siklus (113 kode), tidak ada saham universe tanpa data KSEI atau tanpa return. `versi_data`: KSEI sidik `09c5f430eeb27a83` (6 koreksi KSEI aktif), harga sidik `de27580279a54592` (113 kode, 252.205 baris, 2010-01-01 s/d 2020-01-31, 11.340 koreksi harga aktif), cek kualitas 2026-11-07 0 temuan.

| Kriteria efek kuat | Hasil | |
|---|---|---|
| 1. median selisih ≤ −5 poin | −15,1 poin | ✔ |
| 2. rata-rata selisih ≤ −5 poin | +1,2 poin | ✘ |
| 3. ≥ 60% kejadian tertinggal | 66,7% (28/42) | ✔ |
| 4. median per siklus negatif ≥ 6 dari 9 | 6 dari 9 | ✔ |
| 5. rata-rata tetap negatif tanpa 5 paling tertinggal | +10,5 poin | ✘ |

Per siklus (universe / kejadian / bobot sama / median selisih / rata-rata selisih): 2011 49 / 10 / +21,1% / −6,5 / +6,3; 2012 43 / 4 / +16,8% / +15,5 / +5,1; 2013 62 / 2 / −6,9% / −14,3 / −14,3; 2014 55 / 3 / +26,2% / +4,4 / −1,4; 2015 60 / 4 / −29,8% / −20,7 / −15,7; 2016 50 / 2 / +20,1% / +41,0 / +41,0; 2017 58 / 7 / +23,0% / −37,2 / −30,1; 2018 62 / 6 / −7,6% / −10,7 / +18,6; 2019 65 / 4 / −18,8% / −16,5 / +20,2.

Laporan saja: pembanding tanpa saham kejadian median −13,3 / rata-rata +1,3 / tertinggal 64%. Uji tanda 28/42, p satu sisi 0,022 (kejadian dalam siklus sama tidak independen, jadi p ini terlalu optimistis). Tanpa 5 kejadian paling unggul: rata-rata −19,3, median −20,2. Per besar: 5-20% (17) median −9,3 / rata-rata −2,9 / tertinggal 65%; > 20% (25) median −19,9 / rata-rata +4,0 / tertinggal 68%. Per penyebab: HMETD (16) median −1,4 / rata-rata +19,9 / tertinggal 50%; tanpa HMETD (4) median −10,6; konversi waran (2) MPPA −55,1, TKIM +192,6; merger (1) SCMA +4,4; campuran (3) semua tertinggal (MLPL, BUMI, IKAI); belum bersumber (16) median −14,7 / tertinggal 88%.

Bacaan (deskriptif):
- **Saham yang menerbitkan saham baru biasanya tertinggal** (2 dari 3 kejadian, median −15 poin dari bobot sama dalam 12 bulan), sejalan dengan McLean-Pontiff-Watanabe.
- **Tapi rata-ratanya tidak tertinggal**, karena segelintir penerbit justru menjadi pemenang terbesar: AKRA 2011 (+199 poin), TKIM 2018 (+193), BRPT 2019 (+169), ANTM 2016 (+119), MLPL 2014 (+83). Membuang semua penerbit juga membuang saham-saham ini; TKIM dan BRPT termasuk 5 pemenang yang menopang H22/H30/H32.
- Karena itu kriteria 2 dan 5 gagal: efeknya ada di "kejadian biasa", tapi tidak cukup untuk dipakai sebagai pengecualian di portofolio bobot sama (yang hasilnya ditentukan rata-rata, bukan median).
- Pembagian per penyebab terlalu kecil untuk dibaca; HMETD yang bersumber justru paling tidak tertinggal (median −1,4), sedangkan kelompok "belum bersumber" paling tertinggal (88%). Ini bukan bukti apa pun.

Keputusan: sesuai aturan yang dikunci, **efek kuat tidak terpenuhi → tidak dilanjutkan jadi hipotesis (termasuk sebagai filter H11a)**. Holdout (siklus 2020+) tidak dibuka dan tidak dilihat. Ide lanjutan yang muncul setelah melihat hasil (mis. hanya mengecualikan penerbitan besar, atau memakai median) adalah varian pasca hasil dan tidak dijalankan.

## Catatan: return universe syariah IDX didominasi segelintir pemenang besar (2026-11-07, permintaan user)
- **Pola yang berulang.** Return universe syariah likuid IDX banyak ditentukan oleh segelintir saham yang naik sangat besar, antara lain TKIM, BRPT, INKP, NIKL, SMBR, AKRA, ANTM. Ini sudah terlihat di:
  - H22, H30, H32: ketiganya berakhir di pemenang yang sama (INKP, TKIM, NIKL, BRPT, SMBR) dan gagal tes tanpa 5/10 saham terbaik di universe Rp20 M (lihat "Penutupan keluarga momentum antar-saham").
  - Audit H11a 2026-11-01: tanpa 10 saham terbaik, CAGR turun ke ±2%.
  - Analisis penerbitan saham: median penerbit tertinggal 15 poin, tapi rata-ratanya +1 poin karena AKRA 2011, TKIM 2018, BRPT 2019, ANTM 2016, MLPL 2014 termasuk pemenang terbesar; membuang semua penerbit juga membuang mereka.
- **Akibatnya**, filter yang terlihat masuk akal di "kejadian biasa" (median) bisa merugikan portofolio, karena hasil portofolio ditentukan rata-rata dan rata-rata ditentukan ekor kanan.
- **Aturan untuk hipotesis berikutnya.** Setiap filter atau aturan yang membuang saham secara sistematis dari universe atau strategi dasar (mis. syarat fundamental, penerbitan saham, likuiditas tambahan, sektor) wajib, sejak dikunci, mencantumkan uji dampaknya ke pemenang besar:
  1. Daftar 10 penyumbang laba terbesar strategi/pembanding dasar di periode uji, dan mana yang ikut terbuang oleh filter (berapa bulan atau siklus).
  2. Sumbangan laba yang hilang karena saham-saham itu terbuang, dibanding laba yang terselamatkan dari saham yang dibuang dan memang tertinggal.
  3. Hasil dilaporkan bersama tes konsentrasi simetris standar seragam (tanpa 5/10 saham terbaik). Uji dampak ini tambahan laporan wajib, bukan pengganti, dan tidak melonggarkan standar seragam.
- Catatan ini berlaku ke depan saja; vonis hipotesis lama tidak berubah.

## Pemantauan paper H11a & H29 (dikunci 2026-11-07, keputusan user; pencatatan dan pemantauan, bukan perubahan aturan strategi)

Tujuan: keputusan Okt/Nov 2027 bisa diambil dari catatan yang rapi. Aturan strategi, posisi paper, `paper_*`, dan `batas_paper/h11a_v1` tidak diubah; sidik isinya dicocokkan sebelum dan sesudah pekerjaan (sama). Job `pantau_paper` (`backend/paper/pantau.py`, `backend/paper/banding.py`) jalan tiap hari setelah cek ulang paper di jadwal 17:30; ambang dihitung oleh job `pantau_ambang` (`backend/research/ambang_pantau.py`) dan disimpan di `swing.pantau_batas`.

**Yang dicatat tiap hari (koleksi baru di `swing`, ikut backup harian):**
- `pantau_posisi_h11a`: jejak posisi H11a per hari (status, stop, tertinggi, close, jarak ke stop). Dibaca dari `paper_posisi` sesudah paper selesai; 21 Okt-5 Nov 2026 diisi mundur dengan menjalankan ulang mesin paper di db terpisah, hasil akhirnya dicek identik dengan paper tersimpan (label `rekonstruksi`).
- `pantau_banding`: paper dibandingkan dengan mesin backtest pada periode paper. H11a: sinyal per hari (`uji_tren` pada data riset vs `paper_sinyal`, penyebab beda diisi otomatis), tiap trade (tanggal/harga masuk & keluar, stop awal, dalam % dan tick), replay (trade backtest untuk saham pilihan paper) dan 100 simulasi Monte Carlo dari portofolio kosong. H22: isi tiap rebalance, harga beli, return; H29: replay 50/50 + Monte Carlo bagian Follow Tren. Tiap dokumen menyimpan `versi_data` (`harga.sidik`).
- `pantau_zona`: status harian H11a & H29 (normal / waspada / gagal + alasan), disimpan sekali per hari dan tidak ditimpa, sehingga syarat "tidak pernah WASPADA/GAGAL" Okt 2027 bisa dibaca langsung. Hari yang diisi mundur diberi tanda `isi_mundur` (atau `u2_isi_mundur` / `zona_isi_mundur` bila aturan baru ditambahkan ke catatan lama).
- `pantau_insiden`, `pantau_bulanan` (ringkasan return paper vs replay/backtest per bulan, ditulis sekali setelah bulan selesai).

**Aturan yang dikunci (tambahan, bukan pengganti kriteria 2026-10-22 dan 2026-11-01):**
1. **Bug eksekusi (U1):** cek ulang paper menemukan beda di transaksi/posisi/ekuitas/sinyal/status (pembulatan nilai JII tidak dihitung), atau perbandingan dengan mesin backtest menemukan keputusan berbeda padahal data masukannya sama → insiden. Kalau sampai hari bursa ke-6 sesudah hari ditemukan belum ada penjelasan (T = 5 hari bursa), syarat GAGAL "bug eksekusi" H11a/H29 terpenuhi. Insiden yang hilang sendiri sebelum batas (cek berikutnya cocok) = selesai.
2. **Selisih paper vs backtest (U2) = WASPADA DATA, bukan GAGAL.** Batas dari sebaran historis 2020-2026: backtest yang sama dijalankan dengan harga IDX resmi (cara paper) dan Yahoo (cara backtest). Hanya efek sumber data; lot 100 lembar tidak termasuk.
   - H11a (`u2_v1`): lebih dari **3 ticker-hari sinyal beda dalam 21 hari bursa** (p99; historis 0,91% hari ada beda, terbanyak 4); return paper - replay di luar **pita p1-p99** per lama hari (hari ke-21 -1,07/+1,10, ke-63 -1,26/+1,69, ke-126 -1,73/+2,64, ke-250 -2,08/+3,25 poin; sesudah hari ke-250 memakai pita hari ke-250); selisih harga masuk/keluar > 0,18% (p99; 98% trade persis sama) hanya dicatat.
   - H22/H29 (`u2_h22_v1`, metode sama, dikunci langsung): isi rebalance RS 12-1 beda **lebih dari 2 saham** (p99; 82 rebalance, 90% identik, terbanyak 2 = satu saham tertukar), saham yang beda karena koreksi peringkat 30 Okt 2026 tidak dihitung; return paper H22 - backtest di luar pita (hari ke-21 -4,42/+1,78, ke-63 -7,01/+2,74, ke-126 -9,08/+3,92, ke-250 -17,80/+2,30); return paper H29 - replay di luar pita (ke-21 -2,39/+0,98, ke-63 -3,54/+1,91, ke-126 -4,80/+2,33, ke-250 -8,03/+1,34); selisih harga beli > 0,43% (p99) hanya dicatat.
   - Pita H22 lebar dan condong negatif bukan karena harga salah (harga per saham IDX dan Yahoo sama di hari-hari selisih terbesar), melainkan karena satu saham yang tertukar bisa mengubah hasil banyak: 8 dari 82 rebalance beda satu saham, mis. Jul 2025 data IDX meloloskan 113 saham vs 112 sehingga N 23 vs 22, PANR masuk dan ARCI (pemenang besar 2025) tidak terbeli; selisih kumulatif 2020-2026 -14,7%. Sejalan dengan catatan "pemenang besar mendominasi".
3. **Zona normal H29 (U3, `h29_v1`) hanya laporan WASPADA:** cara sama dengan `h11a_v1` (bootstrap blok 20 hari, 5.000 jalur, kurva harian `h29_2020` seed 7 dengan data s/d 30 Okt 2026, DD kurva -43,39% = ringkasan -43,4%). WASPADA bila return < p5 mulai hari ke-21 atau DD terdalam < p5: p5 return/DD hari ke-21 -11,2/-15,6%, ke-63 -16,5/-22,8%, ke-126 -20,5/-29,5%, ke-250 -25,2/-37,8%, ke-500 -26,6/-46,2% (lebih dalam dari batas GAGAL -45%).
4. **Kelengkapan data (U4):** lebih dari 10% hari paper memakai cadangan Yahoo → evaluasi diberi catatan (WASPADA).

**Hasil pertama (data s/d 6 Nov 2026):** H11a sinyal 13/13 hari sama dengan backtest, 4/4 trade sama, harga masuk 0 tick, paper +0,50% vs replay +0,52% (selisih lot). H22 isi rebalance 30 Okt 22/22 sama, 110 saham lolos di keduanya, 22/22 harga beli sama; H22 paper -8,42% vs backtest -8,53%; H29 paper -4,24% vs replay -4,29%. Simulasi Monte Carlo belum menyebar (sinyal belum pernah melebihi slot), jadi persentil paper belum berarti. H29 tercatat **WASPADA 4 Nov 2026 (hari ke-3, isi mundur setelah zona dikunci)**: DD -4,4% lebih dalam dari p5 zona -4,04%, didorong bagian RS 12-1 yang juga turun di backtest; laporan saja, esoknya normal lagi. Alarm palsu cek ulang H22 3-6 Nov (nilai JII 279,965 vs 279,97) diperbaiki di `cek_h22.py`: nilai JII dicek terpisah dengan toleransi 0,1% sebagai info.

**Catatan teknis: pilihan acak backtest bergantung urutan baris (2026-11-07, belum diubah).** `laporan_bulanan.simulasi_portofolio` memberi angka acak per baris trade (`rng.random(len(t))` sesuai urutan baris), bukan per tanggal sinyal. Kalau ada satu trade baru (mis. sinyal MPMX 5 Nov 2026 setelah data bertambah), urutan bergeser dan pilihan seed yang sama berubah di banyak trade lain: H11a seed 7 berubah di 34 trade, CAGR contoh 22,3% → 21,3%, DD -42,6% → -43,6% (bersama penilaian ulang trade terbuka dengan harga baru, mis. PKPK 6.475 → 5.675). Median 100 simulasi Monte Carlo tidak terpengaruh dengan cara ini, tapi kurva contoh dan zona yang dibuat dari satu seed tidak stabil terhadap tambahan data. Sebaiknya pilihan acak diikat ke tanggal sinyal seperti paper (`default_rng(tanggal)`, permutasi kandidat hari itu), supaya pilihan di tanggal lama tidak berubah saat data bertambah. Mesin backtest dan hasil tersimpan (`backtest_*`, `batas_paper`) sengaja tidak diubah sekarang (keputusan user); zona H29 memakai data s/d 30 Okt 2026 supaya sama dengan backtest tersimpan.

**Peluang gagal syarat walau strategi normal (dihitung 2026-11-07, permintaan user; analisis, kriteria TIDAK diubah).** Pertanyaan: kalau strategi berjalan persis seperti backtest, seberapa sering zona yang dikunci tetap menyala dalam 250 hari bursa pertama? Dinilai dengan aturan persis (return mulai hari ke-21 / ke-63, drawdown dan rugi beruntun sejak hari pertama, `pantau.zona_h11a` / `zona_h29`). Script `backend/research/analisis_peluang_zona.py` (baca saja). Dua sumber jalur: (a) jalur bootstrap blok tempat zona dibangun (h11a_v1 sebenarnya dibuat dari SATU kurva, `h11a_2020_konservatif` seed 7, dipecah jadi 5.000 jalur, bukan dari 100 simulasi Monte Carlo); (b) 100 simulasi Monte Carlo backtest, jendela 250 hari mulai tiap 5 hari (±27.900 jendela, data s/d 30 Okt 2026).

| Peluang dalam 250 hari bursa pertama | h11a_v1 (a) bootstrap | h11a_v1 (b) Monte Carlo konservatif | h29_v1 (a) bootstrap | h29_v1 (b) Monte Carlo |
|---|---|---|---|---|
| Pernah WASPADA, return/drawdown | 35,2% | 41,7% | 33,6% | 26,8% |
| Pernah WASPADA, termasuk rugi beruntun | 43,3% | 48,6% | – | – |
| Pernah GAGAL zona (return p1 / drawdown p1) | 11,5% | 5,8% | – (laporan saja) | – |
| Pernah GAGAL zona termasuk rugi beruntun p99 dan DD < -45% | 13,5% | 12,6% | – | – |
| Pernah DD < -45% (syarat GAGAL H11a & H29) | 0,2% | 0,0% | 1,4% | 1,0% |

- Rincian h11a_v1 (a)/(b): WASPADA return 21,8/31,4%, drawdown 29,2/21,8%, rugi beruntun 12,4/27,0%; GAGAL return 4,2/1,7%, drawdown 10,1/4,3%, rugi beruntun 2,3/6,9%. h29_v1 (a)/(b): WASPADA return 23,5/14,3%, drawdown 27,6/17,0%.
- Artinya: syarat "tidak pernah WASPADA/GAGAL" untuk uang nyata Okt 2027 akan gagal di **sekitar 43-49% tahun normal** (H11a), dan syarat GAGAL h11a_v1 menyala di **sekitar 12-13% tahun normal**. Batas p5/p1 per hari tidak sama dengan peluang "pernah" selama 250 hari; menyentuh sekali di salah satu dari ratusan hari jauh lebih sering dari 5%/1%.
- Keterbatasan: (a) jalur bootstrap h11a_v1 dibuat ulang dari trade backtest sesudah koreksi data 2 Nov 2026 (hash trade beda dengan saat zona dibuat 22 Okt), jadi mendekati jalur asli, bukan persis sama; angka batasnya tetap yang dikunci. h29_v1 (a) identik dengan jalur saat dikunci. (b) jendela saling tumpang tindih dan mulai dengan posisi yang sudah dipegang backtest (paper mulai dari kas), rugi beruntun (b) hanya trade yang ditutup di dalam jendela; keduanya in-sample 2020-2026.
- Status, kriteria, dan zona tidak berubah. Kalau mau ditinjau, itu keputusan user dan dicatat terpisah sebagai perubahan aturan.

## H33: replikasi H11a (Follow Tren) di saham syariah Malaysia dan US (dikunci 2026-11-07 atas permintaan user, sebelum kode backtest dibuat dan sebelum ada angka return apa pun) — disetujui user 2026-11-07 sebelum backtest; HASIL: Malaysia gagal, US laporan saja → peringatan keras
Uji out-of-sample: aturan H11a **persis**, tidak ada parameter yang disetel, **satu kali jalan per pasar, tanpa varian**. Status paper H11a/H29 tidak berubah apa pun hasilnya (kecuali aturan peringatan keras di bawah, yang hanya mengubah cara keputusan Okt 2027 diambil, berlaku setelah disetujui user).

### Langkah 0: cek data (2026-11-07, sebelum ada hasil; `backend/research/analisis_h33_data.py`, hasil `hasil_riset/h33_data`)
Sumber baru (semua lewat server, tanpa Chrome Lab): `backend/ingest/syariah_my.py` (PDF daftar SC → GridFS `syariah_my/*.pdf` + koleksi `lab_data.syariah_my`), `backend/ingest/pasar_luar.py` (Yahoo `.KL` → `harga_my/*`, Yahoo US → `harga_us/*`, holding SPUS → `syariah_us`, indeks/kurs → `indeks_luar/*`). Dibaca lewat `harga.luar*`, `harga.indeks_luar`, `harga.syariah_luar`.

**Malaysia**
- Daftar syariah SAC SC point-in-time: 37 PDF Apr 2006 - Nov 2025 terurai (jumlah kode cocok dengan total tertulis di PDF kecuali Nov 2007 782 vs 853, Nov 2011 830 vs 839, Nov 2013 639 vs 653). Bolong: Okt 2006, Nov 2012, Mei 2020 (halaman SC rusak) → daftar sebelumnya diperpanjang; sebelum Okt 2005 PDF tidak terbaca (hasil scan). Berlaku dari tanggal daftar sampai sehari sebelum daftar berikutnya.
- Harga: 945 dari 1.335 kode syariah-pernah ada di Yahoo. **Tidak ada satu pun saham delisting** (semua data berjalan sampai 2026). Cakupan daftar per tanggal: 2006 62%, 2010 73%, 2015 88%, 2020 94%, 2025 99% → survivorship kuat di tahun awal.
- Open: open = close 27-39% hari bervolume, stabil semua tahun (tick kasar saham murah), **tidak** ada pola rusak seperti Yahoo IDX 2010-2012 (96-99%).
- **Aksi korporasi tidak disesuaikan**: 4.643 hari dengan |return| > 50% (batas harian Bursa ±30%), sebagian langsung balik (1.386), sebagian bertahan (3.257; contoh 0043 2012-03-21 1,76 → 4,09, 0045 2012-08-07 2,69 → 1,12). 128 kejadian di saham bernilai transaksi > RM1,2 jt. Butuh aturan mekanis (di bawah); tidak ada registry koreksi seperti IDX.
- Tick Bursa: < RM1 = 0,005; RM1-9,99 = 0,01; RM10-99,98 = 0,02; ≥ RM100 = 0,10 (tabel sekarang dipakai untuk semua tahun, sama seperti IDX).
- Biaya realistis per sisi: broker online 0,10% (tanpa minimum; broker online termurah ±0,03-0,10%, broker bank 0,10% min RM8), clearing 0,03%, bea meterai 0,10% (sempat 0,15% di 2022-2023, tidak dimodelkan) → 0,23% beli + 0,23% jual + 1 tick per sisi. Minimum fee RM8 tidak dimodelkan (posisi 10% × Rp100 jt ≈ RM2.700 → RM8 = 0,3%).
- Indeks syariah lokal: FBM Emas Shariah tidak ada di Yahoo, situs Bursa diblok Cloudflare. Proksi: ETF Eq8 DJIM Malaysia Titans 25 (`0821EA.KL`, 25 saham syariah terbesar, mirip JII), adj close (termasuk dividen, dikurangi biaya ETF), sejak 22 Jan 2008.
- Kurs: `MYRIDR=X` sejak Des 2003.

**US**
- Konstituen syariah point-in-time: **tidak ada yang lengkap gratis**. DJIM US hanya pengumuman perubahan 2009-2011. SPUS (S&P 500 Shariah, sejak Des 2019) / HLAL (FTSE USA Shariah, sejak Jul 2019): file holding hanya versi hari ini (HLAL CSV beku di 2022); Wayback hanya punya tabel holding penuh SPUS sejak 2024 (sebelumnya 10 teratas). Filing N-PORT SEC (kuartalan, 2019Q4+) ada, tapi SEC menolak akses tanpa email kontak di header (tidak dikirim tanpa izin user).
- Universe yang tersedia: 218 holding SPUS 6 Nov 2026 (215 ada di Yahoo) = daftar hari ini → survivorship penuh + status syariah melihat ke depan.
- Open: open = close 0,2-1,3%, lonjakan > 50% 0-1 per tahun. Data bersih.
- Tick: $0,01 (≥ $1). Biaya: komisi broker AS $0, SEC fee jual ±0,003%, tanpa bea meterai → 0% beli + 0,003% jual + 1 tick.
- Indeks syariah lokal: DJIM US `^IMUS` (harga saja, tanpa dividen, seperti JII) sejak Mei 2001. Kurs `IDR=X`.

**Nilai transaksi & saham lolos (rata-rata per hari bursa)**

Ambang IDX dalam mata uang lokal (kurs median tahun itu): Rp5 M = RM2,2 jt (2003) → RM1,1 jt (2026), $0,57 jt (2011) → $0,28 jt (2026); Rp50 = RM0,012-0,022 / $0,003-0,006; Rp200 = RM0,05-0,09 / $0,011-0,023.
Persentil setara IDX: Rp5 M ada di persentil 53% saham syariah IDX (dev, daftar 217) tapi 78% di 2020+ (DES semua saham) → median semua 59,5%; Rp50 = persentil 2,4%.

| Rata-rata lolos filter H11a per hari | 2007 | 2008 | 2009 | 2010-2019 | 2020-2026 |
|---|---|---|---|---|---|
| IDX (dev daftar 217 / 2020+ DES) | - | - | - | 27,5-41,1 | 43,1-85,3 |
| Malaysia, kurs | 41,2 | 23,9 | 26,2 | 36,7-82,8 | 81,5-138,8 |
| Malaysia, persentil setara IDX | 131,8 | 107,8 | 121,3 | 140,8-179,8 | 109,7-234,5 |
| Malaysia, kurs, S2 Rp20 M | 12,3 | 11,4 | 10,9 | 12,0-36,2 | 35,3-64,8 |
| US, kurs | 153,5 | 112,8 | 132,7 | 131,7-181,0 | 161,5-194,1 |
| US, persentil setara IDX | 61,6 | 47,4 | 57,5 | 48,6-71,5 | 65,0-77,4 |

Saham syariah dengan ATR% 1,5-5 dan tanpa volume nol 5 hari: Malaysia 136-434 per hari (dari 528-815 syariah), US 113-194 (dari 173-215), IDX 48-70 dev, 150-321 2020+. Di US ambang kurs praktis tidak menyaring apa pun (semua S&P 500 likuid); di Malaysia S3 (Rp200) dengan kurs sama dengan dasar (saham < RM0,09 sudah tersaring ATR% karena tick 0,005 = 5-10%).

### Langkah 1: aturan yang dikunci
- **Strategi**: H11a persis. Sinyal close (disesuaikan) ≥ close tertinggi 250 hari sebelumnya; beli open besok; maks 10 posisi @10% ekuitas, ukuran dari ekuitas close hari bursa sebelumnya; sinyal > slot dipilih acak; stop awal entry − 3×ATR14, trailing = max(stop, close tertinggi sejak entry − 3×ATR14); close < stop → jual open besok; batas 500 hari; satu posisi per saham; trade terbuka di akhir data ditutup di close terakhir. **100 simulasi Monte Carlo (seed 1-100), semua kriteria dinilai dari median.** Mesin = mesin backtest H11a yang sama (`batas_paper.kurva_harian` / `uji_tren.simulasi`), hanya sumber data, biaya, dan tick yang diganti.
- **Filter**: ATR% 1,5-5 dan tanpa volume nol 5 hari tetap. **Nilai transaksi 20 hari dan harga minimum: konversi kurs harian** (Rp5 M dan Rp50 dibagi kurs IDR per mata uang lokal hari itu). Alasan: (1) fungsi filter = posisi rupiah yang sama bisa dieksekusi, jadi arti ekonominya ikut uang, bukan peringkat; (2) persentil setara IDX tidak terdefinisi stabil (53% di dev vs 78% di 2020+ karena definisi universe IDX berubah); (3) jumlah saham lolos versi kurs (Malaysia 37-139/hari) paling dekat dengan IDX (28-85), versi persentil 2-3× lebih banyak. Cara persentil tidak dijalankan.
- **Universe syariah**: Malaysia point-in-time (daftar SC pada tanggal itu). US tidak point-in-time → **US = laporan saja** sejak awal, apa pun hasilnya. Bias US: survivorship penuh (hanya saham yang masih ada dan masih di S&P 500 Shariah 2026) + status syariah melihat ke depan + hanya saham besar → hasil cenderung terlalu bagus.
- **Biaya**: Malaysia per sisi broker max(0,10%, RM8) + clearing 0,03% + meterai 0,10% + 1 tick Bursa, dengan modal awal setara paper Rp100 jt (dikonversi kurs hari pertama; ekuitas dihitung dalam ringgit sehingga minimum fee RM8 berlaku nyata); US 0% beli + 0,003% jual + 1 tick ($0,01; < $1: $0,0001), modal awal setara Rp100 jt. Pajak dividen (ditetapkan sebelum run): Malaysia 0% (sistem single-tier, dividen bebas pajak), US 15% (tarif dividen qualified). Posisi pecahan lembar, sama dengan backtest H11a.
- **Putus data (keputusan user 2026-11-07, berlaku Malaysia dan US)**: hari dengan |return close disesuaikan| > 50% = putus data. Posisi yang dipegang ditutup di close terakhir sebelum hari putus (biaya jual normal; return hari putus = 0 untuk strategi DAN pembanding bobot sama). Riwayat saham dimulai ulang sejak hari putus sebagai seri baru (sinyal 250 hari dan ATR dihitung dari seri baru saja; seri < 250 hari dibuang). Untuk tes konsentrasi semua seri dari satu kode dihitung sebagai satu saham. Dilaporkan: jumlah kejadian, saham yang kena, kejadian di saham yang sedang lolos filter, dan trade yang ditutup karena putus. Catatan: menutup di close sebelum putus memakai pengetahuan bahwa besok data putus (diterima user sebagai cara netral).
- **Periode (ditetapkan dari jumlah saham lolos saja, sebelum ada hasil)**: aturan = tahun pertama dengan rata-rata saham lolos ≥ 30 per hari, sisa ≥ 5 tahun.
  - Malaysia: **2007-01-02 s/d 2026-11-06** (2007 = 41,2; sisa 19,8 tahun → bisa diuji). Dicatat: 2008 (23,9) dan 2009 (26,2) di bawah 30; aturan hanya memakai tahun pertama, tidak diubah (keputusan user). Hasil 2008-2009 dilaporkan terpisah. Harga dari 2005 dipakai untuk pemanasan 250 hari.
  - US (laporan saja): **2006-01-02 s/d 2026-11-06** (2005 sudah ≥ 30, tapi data mulai 2005 sehingga sinyal pertama baru mungkin 2006).
  - Seluruh periode pasar luar = data yang belum pernah dipakai H11a, dibuka **sekali**; tidak ada pemisahan dev/holdout (butir d standar seragam terpenuhi dengan satu kali buka ini). Sub-periode sampai 2019 dan 2020+ dilaporkan, bukan syarat.
- **Kriteria lolos per pasar (standar seragam, semua harus lulus, median 100 simulasi):**
  1. CAGR > bobot sama universe syariah likuid lokal (filter sama, rebalance bulanan, tanpa biaya, bias survivorship sama).
  2. CAGR > indeks syariah lokal (Malaysia: `0821EA.KL` adj close, diukur di jendela yang sama mulai Feb 2008, strategi juga diukur di jendela itu; US: `^IMUS`).
  3. Tanpa 5 saham penyumbang laba terbesar (kas) > bobot sama tanpa 5 penyumbang terbesarnya.
  4. Tanpa 10 saham penyumbang terbesar > bobot sama tanpa 10 penyumbang terbesarnya.
  5. Tanpa tahun kalender terbaik > bobot sama tanpa tahun terbaiknya DAN > indeks tanpa tahun terbaiknya (anggota historis indeks tidak ada).
  6. S1 biaya 2 tick per sisi: 1-5 tetap lulus.
  7. S2 likuiditas ≥ Rp20 M (kurs; pembanding ikut): 1-5 tetap lulus.
  8. S3 harga ≥ Rp200 (kurs; pembanding ikut): 1-5 tetap lulus.
  Laporan wajib (bukan syarat): dampak ke 10 penyumbang terbesar strategi dan pembanding (siapa, laba hilang vs terselamatkan bila dibuang), max DD median + p5-p95, jumlah trade, winrate, lama tahan, korelasi return bulanan dengan H11a IDX, jumlah kejadian putus data, `versi_data` (sidik `harga_my`/`harga_us` + jumlah PDF SC).
- **Vonis per pasar**: lolos (semua 1-8) / gagal / tidak bisa diuji / laporan saja. Dua yang terakhir tidak dihitung lolos maupun gagal. Saat ini: Malaysia = bisa diuji, US = laporan saja.
- **Arti gabungan (dikunci sekarang)**:
  - lolos 2 pasar = bukti replikasi kuat;
  - lolos 1 = campur, dicatat;
  - kalau hanya 1 pasar bervonis, hasil terbaik = "campur", tidak pernah "bukti kuat" (berlaku sekarang: hanya Malaysia bervonis);
  - lolos 0 dari pasar yang bervonis = **peringatan keras**: keputusan uang nyata H11a Okt 2027 tidak boleh otomatis walau paper tidak pernah WASPADA/GAGAL; harus diputuskan ulang secara eksplisit oleh user, dengan porsi awal maks 10% dari total dana investasi yang direncanakan untuk H11a.
- Tidak ada pasar pengganti (Indonesia non-syariah, Timur Tengah, dst.) yang ditambahkan setelah melihat hasil. Tidak ada varian filter, biaya, atau periode.
- **Pembanding replikasi yang sudah gagal**: H13 Set A (H11a di saham non-syariah IDX 2010-2026): CAGR 1,9% < beli-tahan bulanan 5,0%. Hasil H33 dilaporkan berdampingan dengan angka ini.
- **Keterbatasan (ditulis sebelum uji)**: survivorship (Malaysia 27-38% kode syariah 2006-2010 hilang dari Yahoo; US penuh); syariah point-in-time hanya Malaysia, dengan 3 daftar bolong diperpanjang; kualitas open Yahoo `.KL` tidak bisa dicek silang dengan data resmi Bursa (diblok Cloudflare), aksi korporasi tidak disesuaikan (aturan putus data); kurs Yahoo harian, ambang rupiah tidak disesuaikan inflasi (sama dengan IDX); indeks Malaysia = proksi ETF (25 saham, ada biaya ETF) mulai 2008; minimum fee broker Malaysia tidak dimodelkan; tabel tick sekarang dipakai untuk semua tahun; literatur 52-week high (George & Hwang 2004) berasal dari data US, jadi US tidak sepenuhnya baru secara gagasan.

### Keputusan user (2026-11-07, sebelum backtest)
1. Konversi ambang: kurs harian.
2. US: laporan saja; email tidak dipakai di header SEC.
3. Putus data: lihat butir "Putus data" di atas (tutup di close terakhir sebelum putus, riwayat dimulai ulang, laporkan kejadian).
4. Malaysia mulai 2007 sesuai aturan; 2008-2009 dilaporkan terpisah.
5. Indeks Malaysia = `0821EA.KL`, kriteria vs indeks dihitung mulai Feb 2008. Biaya 0,23%/sisi plus minimum fee broker RM8, modal setara paper Rp100 jt.
6. **Catatan bias (ditulis sebelum uji, kriteria tidak diubah)**: survivorship Malaysia (hanya 62% kode daftar 2006 dan 73% daftar 2010 ada di Yahoo) membuat kriteria vs indeks bias menguntungkan strategi, karena indeks (ETF) memuat saham yang kemudian delisting sedangkan universe strategi tidak. Bobot bukti ada di kriteria vs bobot sama (bias survivorship sama dengan strategi).
7. Aturan peringatan keras masuk catatan kriteria evaluasi paper H11a, 2026-11-07.

### Hasil H33 (2026-11-07, sekali jalan per pasar; `backend/research/uji_h33.py`, hasil `hasil_riset/h33_hasil`)
Cek mesin sebelum dijalankan di data luar: salinan mesin portofolio (parameter biaya/tick/mata uang per pasar) dijalankan di IDX dev 2010-2019 dengan biaya IDX → return bulanan identik dengan mesin audit H11a (`audit/h22_ulang.h11a_log`, selisih 7e-16 setelah harga dibulatkan ke rupiah seperti mesin lama; tanpa pembulatan 0,001). Bobot sama identik persis. `versi_data`: Malaysia sidik `7aa4eda9a2d9543b` (935 kode, 3,9 jt baris, 37 daftar SC), US `166abf1ca600d0f3` (214 kode, holding SPUS 6 Nov 2026). `cek_kualitas_data` hanya untuk IDX; data luar diperiksa di Langkah 0 + aturan putus data.

**Vonis: Malaysia GAGAL, US laporan saja → gabungan = PERINGATAN KERAS** (lolos 0 dari 1 pasar bervonis). Sesuai kunci: keputusan uang nyata H11a Okt 2027 tidak otomatis walau paper tidak pernah WASPADA/GAGAL; diputuskan ulang eksplisit oleh user, porsi awal maks 10% dari dana yang direncanakan untuk H11a. Status paper H11a/H29 tidak berubah.

**Malaysia 2007-01-02 s/d 2026-11-06** (median 100 simulasi Monte Carlo; rata-rata 75,9 saham lolos per hari, 734 saham pernah lolos, 3.397 sinyal, ±1.125 trade, winrate 40%, tahan median 28 hari)

| Skenario | CAGR (p5-p95) | 1. vs bobot sama | 2. vs indeks (Feb 2008+) | 3. tanpa 5 saham | 4. tanpa 10 saham | 5a. tanpa tahun terbaik vs bobot sama | 5b. vs indeks | Lulus |
|---|---|---|---|---|---|---|---|---|
| Dasar | 9,43% (7,6-11,3), DD -36,4% | 9,43 vs 5,39 ✔ | 9,34 vs 1,67 ✔ | 5,56 vs 3,99 ✔ | 3,68 vs 3,02 ✔ | 5,94 vs 3,13 ✔ | 5,69 vs -0,19 ✔ | 6/6 |
| S1 biaya 2 tick | 1,12% (-1,0-3,1), DD -54,4% | 1,12 vs 5,39 ✘ | 0,91 vs 1,67 ✘ | -2,29 vs 3,99 ✘ | -4,35 vs 3,02 ✘ | -2,08 vs 3,13 ✘ | -2,39 vs -0,19 ✘ | 0/6 |
| S2 ≥ Rp20 M (29,4 lolos/hari) | 5,19% (4,5-5,7), DD -44,9% | 5,19 vs 5,62 ✘ | 5,21 vs 1,67 ✔ | 1,26 vs 3,59 ✘ | -1,03 vs 2,00 ✘ | 1,74 vs 3,33 ✘ | 1,55 vs -0,19 ✔ | 2/6 |
| S3 ≥ Rp200 | 9,97% (8,0-12,0), DD -36,3% | 9,97 vs 5,39 ✔ | 9,93 vs 1,67 ✔ | 6,13 vs 4,01 ✔ | 4,18 vs 3,04 ✔ | 6,49 vs 3,13 ✔ | 6,25 vs -0,19 ✔ | 6/6 |

- **Penyebab gagal**: (1) biaya tick. Satu tick tambahan per sisi memotong 8,3 poin/th: tick Bursa 0,005 di saham < RM1 = 0,5-2% per sisi, dan ±56 trade/th @10% ekuitas. Keunggulan dasar hanya ada di asumsi 1 tick. (2) Di saham yang benar-benar likuid (≥ Rp20 M ≈ RM5-6 jt/hari) strategi kalah dari bobot sama (5,2% vs 5,6%) dan bergantung pada pemenang besar (tanpa 5 saham 1,3% vs 3,6%). Pola sama dengan H11a di dev IDX (S2 3,7%).
- Sub-periode (laporan): s/d 2019 9,35% (bobot sama 6,03%, indeks 2,59%), 2020+ 8,88% (4,19%, 0,11%), **2008-2009 -0,58%/th** (bobot sama -2,77%, indeks -8,88%); 2008 dan 2009 rata-rata saham lolos < 30.
- Tahun terbaik strategi 2020 (contoh seed 7 +115,7%), bobot sama dan indeks 2009. Per tahun (seed 7): 2007 +12,7, 2008 -14,8, 2009 +16,7, 2010 +9,0, 2011 +11,8, 2012 -5,0, 2013 +19,1, 2014 -8,6, 2015 +17,7, 2016 -11,0, 2017 +60,1, 2018 -14,4, 2019 +29,7, 2020 +115,7, 2021 -1,2, 2022 -4,1, 2023 -21,3, 2024 +15,0, 2025 -7,5, 2026 -2,3.
- 10 penyumbang terbesar (seed 7): 7106, 5273, 0155, 3867, 7153, 5012, 8869, 5202, 7113, 3336 = 119% dari total laba (sisanya rugi bersih). Di S2 semua 10 masih ada di universe; pemenang S2: 7106, 8869, 7153, 0225, 3867, 5878, 5141, 5168, 0208, 7113 (127% laba). Bobot sama: 5878, 8869, 7160, 7153, 5141, 5286, 0128, 4065, 5005, 7113 (dua sama dengan strategi: 8869, 7153, 7113).
- Putus data: 4.428 kejadian di 389 saham dalam periode uji (4.642 sejak 2005); hanya 11 kejadian di saham yang sedang lolos filter (0065, 0086, 0097, 0162, 5099, 5141, 5202, 5843, 7195, 8052, 9466); median 2 trade per simulasi ditutup karena putus.
- Dalam rupiah (laporan): 12,4%/th (ringgit menguat terhadap rupiah). Korelasi return bulanan dengan H11a IDX 0,13. DD median -36,4% (p5 -44,0%, p95 -31,5%).

**US 2006-01-02 s/d 2026-11-06 (laporan saja; universe holding SPUS hari ini, survivorship penuh)**: CAGR 11,36% (9,8-13,3), DD -28,7%; bobot sama 16,61%; `^IMUS` 10,41%; tanpa 5 saham 8,31% vs 15,88%; tanpa 10 6,68% vs 15,20%; tanpa tahun terbaik 10,03% vs 15,52% (indeks 9,42%). Lulus 2/6 di semua skenario (hanya kalahkan indeks). S1 10,94%, S2 11,48%, S3 sama dengan dasar (filter tidak menyaring). Sub-periode: s/d 2019 10,9% (bobot sama 17,0%), 2020+ 12,8% (15,8%), 2008-2009 -9,1% (-0,2%). Penyumbang terbesar: FLEX, TWLO, VRT, CIEN, AMD, NVDA, CEG, TYL, WELL, URI. Bobot sama sangat terbantu survivorship (hanya saham yang masih ada dan masih di S&P 500 Shariah 2026), jadi perbandingannya tidak adil ke dua arah; tidak dihitung lolos/gagal. Putus data 8 kejadian (3 di saham lolos: AMD, JCI, VRTX). Korelasi dengan H11a IDX 0,08.

**Dibanding replikasi lain**: H13 Set A (IDX non-syariah) CAGR 1,9% < beli-tahan 5,0%. Malaysia dasar lebih baik (9,4% vs 5,4%), tapi tidak tahan biaya 2 tick dan universe likuid. Gambaran yang sama dengan audit H11a di dev IDX: keunggulan hanya muncul di saham kecil-menengah dengan asumsi biaya minimal, dan hilang di saham likuid.

**Pelajaran**: Follow Tren tidak terreplikasi di pasar syariah kedua dengan standar seragam. Hasil 2020+ IDX (CAGR ±21%) tetap tidak punya pendukung di luar IDX; harapan untuk uang nyata harus rendah.

## Audit aturan evaluasi paper H11a & H29 (dikunci 2026-11-07 atas permintaan user, sebelum dihitung; analisis sifat aturan, BUKAN hipotesis baru dan BUKAN reaksi atas hasil paper) — aturan v2 dikunci 2026-11-07
Konteks saat ditulis: H11a NORMAL dan belum pernah WASPADA; H29 pernah WASPADA 4 Nov 2026 (drawdown, zona laporan saja). Lanjutan dari "Peluang gagal syarat walau strategi normal" (43-49% / 12-13%). `paper_*`, `paper_h22_*`, `batas_paper/h11a_v1`, `pantau_batas`, `pantau_zona` tidak diubah; sidik isi dicocokkan sebelum dan sesudah. Script `backend/research/audit_aturan_paper.py` (baca saja), hasil `hasil_riset/audit_aturan_paper`.

### Aturan yang diaudit
1. **Zona h11a_v1 WASPADA**: return < p5 mulai hari ke-21; DD terdalam < p5; rugi beruntun > p95 (per jumlah trade).
2. **Zona h11a_v1 GAGAL**: return < p1 mulai hari ke-63; DD < p1; rugi beruntun > p99.
3. **DD paper < -45%** = GAGAL (H11a dan H29).
4. **Syarat uang nyata H11a Okt 2027**: tidak pernah WASPADA/GAGAL. Di kode (`pantau.status_gabung`) WASPADA juga menyala karena insiden yang belum terjelaskan (< 5 hari bursa), U2 WASPADA DATA, dan U4; dihitung terpisah di butir 8-10.
5. **Peringatan keras H33** (sudah menyala 2026-11-07): sifatnya dinilai dari angka yang ada (seberapa mungkin strategi yang punya keunggulan lolos standar seragam di pasar lain), tidak ada alarm berjalan.
6. **Zona h29_v1** (laporan WASPADA): return < p5 mulai hari ke-21; DD < p5.
7. **H29 GAGAL**: DD < -45% atau bug eksekusi. Kriteria 2027 H29 = tidak GAGAL; "rugi kecil dibandingkan dengan bobot sama dan JII" bukan syarat angka.
8. **U1 bug eksekusi**: insiden tak terjelaskan > 5 hari bursa → GAGAL; insiden terbuka ≤ 5 hari → WASPADA (ikut butir 4).
9. **U2** `u2_v1` (H11a: > 3 ticker-hari sinyal beda per 21 hari, return paper - replay di luar pita p1-p99) dan `u2_h22_v1` (isi rebalance beda > 2 saham, pita H22 dan H29) → WASPADA DATA.
10. **U4**: > 10% hari memakai cadangan Yahoo → WASPADA (catatan).
Aturan lain yang ditemukan di kode: tidak ada (selisih harga > p99 hanya dicatat, bukan status).

### Definisi "normal" (dua versi)
- **(a) bootstrap 2020+** (data sudah terbuka, in-sample): bootstrap blok 20 hari, 5.000 jalur, seed 20261022, cara yang sama dengan pembuatan h11a_v1. H11a: kurva harian `h11a_2020_konservatif` contoh seed 7 (dibangun ulang dari trade tersimpan); rugi beruntun diambil acak dari net trade selesai seperti h11a_v1. H29: kurva h29_v1 (hash dicek sama).
- **(b) jendela bergulir dev 2010-2019**: 100 simulasi Monte Carlo H11a dev (universe 217, versi konservatif ARA/ARB, mesin dan biaya sama dengan backtest), kurva harian penuh; jendela mulai tiap 5 hari bursa sejak 2011-01-03 (sesudah pemanasan 250 hari); rugi beruntun dari trade yang selesai di dalam jendela. H29 dev: H11a dev (100 simulasi) + H22 dev (`uji_h21_h22`, deterministik) digabung 50/50 dengan `simulasi_h29.gabung`, Feb 2011-2019. Jendela mulai dengan posisi yang sudah dipegang (paper mulai dari kas): dicatat sebagai keterbatasan.

### Definisi "tanpa edge" (null), dihitung di dua rezim yang sama dengan (a) dan (b)
1. **Bobot sama** universe syariah likuid (filter H11a; dev = daftar 217, 2020+ = DES point-in-time), rebalance akhir bulan, biaya sama: tiap rebalance, nilai yang berpindah × (fee rata-rata 0,20% + 1 tick/harga) per sisi.
2. **Beli-tahan JII** (`indeks/JKII`, harga saja, tanpa biaya).
3. **Pilihan acak**: tiap saham-hari yang lolos filter jadi sinyal dengan peluang p = jumlah sinyal H11a / jumlah saham-hari lolos di periode itu; masuk open besok, slot 10 @10% dipilih acak, stop 3×ATR14 trailing, jual open besok, batas 500 hari, versi konservatif dan biaya persis H11a (`uji_tren.simulasi`). **200 simulasi Monte Carlo** per periode (seed 1001-1200).
- H29 null = 50% null (3) + 50% null (1), digabung dengan `simulasi_h29.gabung`.
- Rezim (a): null (1) dan (2) = bootstrap blok 20 hari 5.000 jalur dari return harian 2020+; null (3) = 25 jalur bootstrap per simulasi (5.000 jalur). Rezim (b): jendela bergulir dev seperti normal (b).

### Kriteria "lolos 2027" yang dipakai untuk lolos palsu
- H11a: tidak pernah WASPADA/GAGAL zona h11a_v1 (butir 1-2) dan DD tidak pernah < -45% selama T hari.
- H29: DD tidak pernah < -45% selama T hari (kriteria resmi); dilaporkan juga versi ketat "tidak pernah WASPADA h29_v1".
- Butir 4/8-10 (insiden, data) tidak berlaku untuk jalur simulasi.

### Ukuran yang dihitung (horizon 63 / 125 / 250 hari bursa)
- Alarm palsu: P(pernah WASPADA), P(pernah GAGAL), P(pernah DD < -45%) di jalur normal (a) dan (b).
- Lolos palsu: P(null lolos) untuk null (1), (2), (3).
- Daya pembeda: P(normal lolos) vs P(null lolos).
- **Horizon minimum T** (1-60 bulan, 21 hari bursa per bulan): kriteria posisi akhir "return hari T ≥ persentil 20 normal" (jadi P(normal lolos) = 80% menurut definisi); T terkecil dengan P(null lolos) ≤ 10%, per null dan per rezim. Bila tidak tercapai sampai 60 bulan, ditulis apa adanya. Rezim (b) memakai jendela dev sepanjang T (makin panjang makin sedikit jendela).
- U1/U2/U4: dari riwayat yang ada. U2: pasangan IDX vs Yahoo historis yang dipakai membuat pita (kalau bisa dihitung ulang) → P(pernah keluar pita dalam 250 hari). U1/U4: kalau riwayat tidak cukup, ditulis tidak cukup.

### Ambang keputusan (dikunci sekarang)
- Aturan GAGAL dianggap rusak bila alarm palsu 250 hari > 5%.
- WASPADA: bila dipakai sebagai syarat uang nyata, alarm palsu 250 hari harus ≤ 10%; bila hanya info, tanpa ambang.
- Aturan tidak punya daya pembeda bila P(null lolos kriteria 2027) > 20%.

### Kandidat pengganti (hanya ini; dipilih dari sifat aturan, bukan dari hasil paper)
- **(i) pita simultan**: satu kuantil q untuk return (mulai hari ke-21 WASPADA / ke-63 GAGAL, seperti v1), DD, dan rugi beruntun, digeser sampai P(pernah menyentuh dalam 250 hari) di jalur normal (a) = 5% (GAGAL) / 10% (WASPADA); diperiksa silang di (b).
- **(ii) posisi akhir**: hanya return dan DD terdalam di hari ke-250, kuantil q yang sama sehingga P(normal kena) = 5% (GAGAL) / 10% (WASPADA).
- **(iii) info saja**.
- Cara memilih (dikunci): untuk tiap aturan yang rusak, pilih (i) atau (ii) yang alarm palsunya memenuhi ambang di (a) DAN (b) dengan P(null kena) terbesar (daya pembeda); bila keduanya tidak memberi P(null lolos) ≤ 20% atau alarm palsu (b) melewati ambang, pilih (iii).

### Hasil audit (2026-11-07; `hasil_riset/audit_aturan_paper`; sidik 17 koleksi paper/zona/pantau sama sebelum dan sesudah)
Jalur: H11a normal (a) 5.000, (b) 38.900 jendela; H29 normal (a) 5.000 (kurva sama dengan h29_v1: ya), (b) 38.500; null (1)/(2) (a) 5.000 jalur bootstrap, (b) ±390-400 jendela (satu kurva); null (3) 200 simulasi per periode (peluang sinyal acak 3,6% 2020+ / 4,1% dev; CAGR median -4,7% / -1,0%); bobot sama dengan biaya -5,9%/th 2020+, 6,3%/th dev. Jendela null (3) dev tiap 10 hari (memori).

**H11a, aturan sekarang (peluang dalam T hari bursa, %)**

| | Normal (a) 63/125/250 | Normal (b) 63/125/250 | Null 1 bobot sama (a)/(b) 250 | Null 2 JII (a)/(b) 250 | Null 3 acak (a)/(b) 250 |
|---|---|---|---|---|---|
| Pernah WASPADA | 33,3 / 40,5 / **44,9** | 12,7 / 18,5 / **23,9** | 55,7 / 47,4 | 67,0 / 42,9 | 68,1 / 58,4 |
| Pernah GAGAL zona | 8,6 / 11,1 / **13,4** | 2,2 / 2,2 / 2,2 | 33,8 / 25,3 | 43,2 / 14,7 | 34,4 / 29,5 |
| Pernah DD < -45% | 0 / 0 / 0,1 (500 hari: 1,5) | 0 / 0 / 0 (500: 0) | 7,6 / 0 | 9,0 / 0 | 4,0 / 0,6 |
| **Lolos kriteria 2027** | 66,7 / 59,5 / **55,1** | 87,3 / 81,5 / **76,1** | **44,3 / 52,6** | **33,0 / 57,1** | **31,9 / 41,6** |

**H29, aturan sekarang**: lolos (DD > -45%) normal 99,0% (a) / 100% (b), null (50% acak + 50% bobot sama) 96,7% / 100% → tidak ada daya pembeda. Zona h29_v1 pernah WASPADA 250 hari: normal 32,1% / 12,5%, null 37,3% / 30,9% (laporan saja). DD < -45%: normal 1,0% di 250 hari, 5,7% di 500 hari (a).

**Kandidat (kuantil dikalibrasi di normal (a), 250 hari)**

| Aturan | Kandidat | Batas | Alarm palsu (a)/(b) | P(null kena) (a) 1/2/3; (b) 1/2/3 |
|---|---|---|---|---|
| H11a GAGAL | (i) pita simultan q 0,34% | hari 63: return -22,4% / DD -25,5%; hari 250: -35,5% / -41,4%; beruntun 20 trade > 16 | 5,0 / 1,0 | 26,9 / 33,8 / 23,0; 17,0 / 4,9 / 18,5 |
| H11a GAGAL | (ii) posisi akhir q 3,46% | hari 250: return < -22,7% atau DD < -33,3% | 5,0 / 0,0 | 27,4 / 33,7 / 25,1; 9,3 / 0,0 / 15,3 |
| H11a WASPADA | (i) q 0,70% | hari 63: -20,2% / -23,9%; hari 250: -33,0% / -39,0%; beruntun 20 > 14 | 10,1 / 1,0 | 31,7 / 40,1 / 31,7; 22,6 / 11,8 / 26,0 |
| H11a WASPADA | (ii) q 7,08% | hari 250: return < -16,5% atau DD < -29,7% | 10,0 / 0,2 | 36,0 / 45,2 / 36,4; 17,5 / 1,3 / 24,8 |
| H29 GAGAL (baru) | (i) q 0,40% | hari 250: -40,5% / -49,2% | 5,0 / 0,3 | 8,4; 3,8 |
| H29 GAGAL (baru) | (ii) q 3,66% | hari 250: return < -27,0% atau DD < -39,1% | 5,0 / 0,0 | 13,3; 6,3 |

Kriteria 2027 H11a dengan kandidat (i) WASPADA + (i) GAGAL + DD -45%: normal lolos 90,0% / 99,0%, null lolos 68,4 / 59,9 / 68,3 (a), 77,4 / 88,2 / 74,0 (b). Dengan (ii): normal 90,0 / 99,8%, null 64,0 / 54,8 / 63,6 (a), 82,5 / 98,7 / 75,2 (b). **Semua > 20% → kriteria 12 bulan tidak punya daya pembeda dengan kandidat mana pun.**

**Horizon minimum** (return hari T ≥ persentil 20 normal; T terkecil dengan P(null) ≤ 10%):
- H11a (a): vs bobot sama 48 bulan, vs JII 32 bulan, vs acak **tidak tercapai** (10,6% di 60 bulan). (b): vs bobot sama 51, vs JII **tidak tercapai** (28,9% di 60), vs acak 45. Di 12 bulan P(null) 36-80%.
- H29 (a): **tidak tercapai** (15,5% di 60 bulan). (b): 43 bulan. Di 12 bulan 54-73%.
- Jendela (b) 48-60 bulan dari dev 9 tahun hanya ±1-2 jalur independen.

**U1/U2/U4**
- U2 `u2_v1` pita replay H11a: pernah keluar dalam 250 hari **16,8%** di riwayat (in-sample, ambang dibuat dari data yang sama); sinyal beda > 3 per 21 hari 1,8%. `u2_h22_v1`: pita H22 24,1% (satu jalur, 278 jendela), pita H29 25,6%, isi rebalance > 2 saham 0% (maks historis 2 = batas). Di kode WASPADA DATA ikut mengubah status H11a jadi WASPADA, jadi ikut syarat "tidak pernah WASPADA".
- U1: belum ada satu pun insiden tercatat → **data tidak cukup**.
- U4: 10 catatan sumber paper (0 cadangan), jadwal harian 5 hari → **data tidak cukup**.

**Peringatan keras H33**: tidak ada alarm berjalan; sudah menyala. Sifatnya: H11a sendiri gagal standar seragam di dev IDX (S1 6,1%, S2 3,7%), jadi strategi seperti H11a hampir pasti gagal standar ini di pasar lain walau punya keunggulan kecil; aturan ini mengukur ketahanan terhadap biaya/likuiditas, bukan membedakan edge vs tanpa edge. Tidak ada kandidat yang perlu dihitung.

**Penilaian terhadap ambang yang dikunci**
- H11a GAGAL zona h11a_v1: alarm palsu (a) 13,4% > 5% → **rusak** (di (b) 2,2%).
- H11a WASPADA sebagai syarat uang nyata: 44,9% / 23,9% > 10% → **rusak**.
- Kriteria 2027 H11a: null lolos 32-57% > 20% → **tanpa daya pembeda**.
- DD -45% (H11a & H29): alarm palsu ≤ 1% di 250 hari → **lulus** sebagai rem darurat; daya pembedanya kecil (null 0-9%).
- Kriteria 2027 H29: null lolos 97-100% → **tanpa daya pembeda**. Zona h29_v1 info saja → tanpa ambang.
- U2 WASPADA DATA sebagai bagian syarat uang nyata: 16,8% > 10% → **rusak** sebagai syarat; wajar sebagai info.

**Pilihan kandidat menurut aturan pilih yang dikunci**: aturan pilih menulis "pilih (iii) bila tidak ada kandidat yang memberi P(null lolos) ≤ 20%". Dibaca harfiah, semua kandidat jatuh ke (iii) karena tidak ada aturan 12 bulan yang punya daya pembeda. Kalau syarat daya pembeda dibaca hanya untuk kriteria 2027 (bukan untuk rem GAGAL), pilihan dengan P(null kena) terbesar: H11a GAGAL (i), H11a WASPADA (i), H29 GAGAL (ii). **Tafsir mana yang dipakai = keputusan user** (dicatat sebelum dikunci).

**Keterbatasan**: survivorship (saham delisting tidak ada); syariah point-in-time baru sejak Des 2019 (dev memakai daftar 217 hari ini); bootstrap blok mengabaikan rezim pasar; jalur independen sedikit (2020+ ±7 tahun, dev 9 tahun; jendela saling tumpang tindih); (a) in-sample (data 2020+ sudah terbuka, kandidat dikalibrasi di sana); jendela (b) mulai dengan posisi yang sudah dipegang; null (1)/(2) tidak punya trade sehingga aturan rugi beruntun tidak pernah menyala untuk mereka; zona dibuat dari volatilitas 2020+ sehingga di dev yang lebih tenang alarm lebih jarang.

### Keputusan user & penguncian aturan v2 (2026-11-07)
**Alasan perubahan = sifat aturan dari audit di atas, bukan hasil paper.** Dicatat terpisah sebagai perubahan aturan evaluasi; aturan strategi H11a/H29 (sinyal, stop, ukuran, dst.) TIDAK berubah.

Keputusan user:
1. Tafsir aturan pilih: syarat daya pembeda (P null lolos ≤ 20%) hanya untuk kriteria keputusan 2027. Rem GAGAL dinilai dari alarm palsu (≤ 5%).
2. Dikunci (job `kunci_aturan_v2`, `backend/paper/aturan_v2.py`):
   - **`batas_paper/h11a_v2`** GAGAL = pita simultan q 0,34% (kandidat i): return < pita mulai hari ke-63, drawdown terdalam < pita, atau rugi beruntun > pita; contoh batas hari ke-63 return -22,4% / DD -25,5%, hari ke-250 -35,5% / -41,4%, 20 trade > 16 rugi beruntun. Hari > 500 memakai pita hari ke-500.
   - WASPADA H11a = pita simultan q 0,70%, **info saja** (bukan syarat uang nyata).
   - **`pantau_batas/h29_v2`** GAGAL H29 (kandidat ii): di hari bursa ke-250 return < -26,96% (≈ -27,0%) atau drawdown terdalam sampai hari itu < -39,06% (≈ -39,1%).
   - U2 (`u2_v1`, `u2_h22_v1`) semua = info saja: di status v2 tidak lagi mengubah status (catatan `info_data`).
   - DD -45%, U1 (bug eksekusi > 5 hari bursa → GAGAL; insiden terbuka = info waspada), U4 (cadangan Yahoo > 10% = info waspada) tetap.
3. **Kriteria Okt/Nov 2027**: syarat "tidak pernah WASPADA/GAGAL → uang nyata 10-20%" DIGANTI. Okt 2027 (H11a) dan 1 Nov 2027 (H29) = **keputusan manual user dengan porsi kecil** (peringatan keras H33: porsi awal maks 10% dari dana yang direncanakan untuk H11a), dicatat eksplisit **BUKAN bukti edge**. Rem GAGAL tetap mengikat.
   - **Horizon bukti** (audit, return hari T ≥ persentil 20 normal dan P(null) ≤ 10%): **H11a ±32-51 bulan** (vs JII 32, vs bobot sama 48-51, vs pilihan acak 45 bulan di dev; di rezim 2020+ vs pilihan acak tidak tercapai sampai 60 bulan); **H29 ±43 bulan atau lebih** (dev 43; 2020+ tidak tercapai sampai 60 bulan).
4. Aturan lama (`h11a_v1`, `h29_v1`) tetap dihitung dan disimpan berdampingan di `pantau_zona` (logika lama tidak diubah, termasuk U2 di status lama, sebagai pembanding). Status v2 disimpan di koleksi baru `swing.pantau_zona_v2` (satu dokumen per hari per strategi, tidak ditimpa; 6 Nov ke belakang diisi mundur dengan tanda `isi_mundur`), dihitung di job `pantau_paper` langkah 5.

**Saat dikunci (2026-11-07, Sabtu, data paper s/d 6 Nov 2026):** H11a 13 hari tercatat, status NORMAL, belum pernah WASPADA/GAGAL; H29 6 hari tercatat, status NORMAL, pernah WASPADA 4 Nov 2026 (zona h29_v1, laporan). Sidik isi saat dikunci (sha256 16 huruf, sama dengan sebelum audit): paper_cek 23 dok `dc02aef41eb90306`, paper_ekuitas 13 `b0b8dc96d7158df2`, paper_h22_cek 7 `a9025d98b609ed47`, paper_h22_ekuitas 6 `92d4d9ca18f07556`, paper_h22_koreksi 110 `0305b8363ca593ba`, paper_h22_posisi 22 `390290bc37599e99`, paper_h22_rebalance 1 `8fbd2633abc41469`, paper_h22_status 1 `14c5310747b3a86e`, paper_h22_transaksi 22 `033550948002fd37`, paper_posisi 4 `2560a774ac92c180`, paper_sinyal 13 `7cf342de799b9649`, paper_status 1 `37273c0fa1feb253`, paper_sumber 10 `004630f51591dcda`, paper_transaksi 0 `e3b0c44298fc1c14`, batas_paper/h11a_v1 `2f994a438fb3c013`. Dokumen lama di `pantau_batas` (3 dok, `343a48e3746ce584`) dan `pantau_zona` (19 dok, `76e65ea493670b74`) tidak berubah; yang bertambah hanya `batas_paper/h11a_v2` dan `pantau_batas/h29_v2`. Sidik juga disimpan di dokumen v2 (`sidik_paper`, `status_paper`).

Tampilan: panel "Aturan evaluasi (v2)" di tab Paper Follow Tren dan Momentum Blend (status v2, rem hari ini, keputusan 2027, aturan lama sebagai pembanding, tabel hasil audit, horizon bukti); grafik zona h11a_v1 diberi label "lama (pembanding)" dan garis rem GAGAL v2. API `/api/paper/aturan?strategi=h11a|h29`.

## Keputusan lapisan Likuiditas & Pendapatan (2026-11-08, keputusan user; deskriptif, bukan hipotesis)
- Likuiditas **Opsi 1 "Tanpa SBN"** = RD pendapatan tetap syariah / RD pasar uang syariah 50/50, rebalance tahunan (semua bisa dicairkan kapan saja).
- **Opsi 2 "Dengan SBN"** = porsi SBN ritel syariah (tangga SR/ST dibeli di pasar perdana, dipegang sampai jatuh tempo, uang terkunci) + sisanya RD PT/PU 50/50. SBN di dalam RD tidak dihitung sebagai "SBN" di sini.
- Patokan Likuiditas direvisi: rata-rata jangka panjang ≥ inflasi + 1,5%/th, DD maks -10%; periode 3 tahun di bawah target diterima.
- Dana darurat terpisah, 100% RD pasar uang syariah (tidak boleh di SBN).
- Lapisan Pendapatan dirumuskan ulang: penghasilan = penarikan rutin dari portofolio (+ kupon SBN di Opsi 2), bukan memilih saham/RD pembagi dividen. Kedua opsi dianalisis dan nanti ditampilkan berdampingan.

### Portofolio Konservatif: keranjang produk & asumsi simulasi (2026-11-08, deskriptif)
- **Simulasi penarikan** (`analisis_penarikan.py`): penarikan bulanan naik ikut inflasi tiap 12 bulan; kupon SBN bersih (pajak 10%) dipakai dulu, kekurangannya diambil **proporsional** dari semua bagian yang bisa dicairkan (RD PT, RD PU, uang SBN yang menunggu penawaran); RD PT/PU dikembalikan ke 50/50 tiap akhir Desember. "Aman" = modal riil ≥ 100% di ≥ 80% tanggal mulai dan tidak pernah kehabisan dana cair (langkah 0,1%, 0-3%).
- **Cek "jual RD PU dulu"** (cara yang ditulis di jadwal halaman; kekurangan diambil dari RD PU, lalu uang SBN yang menunggu, lalu RD PT; rebalance Desember sama): tingkat aman 3 th / 5 th **identik** dengan cara proporsional di semua opsi (Opsi 1 0,6/1,1%, SBN 30% 0,9/1,5%, SBN 50% 1,2/1,8%, SBN 70% 1,5/2,0%; data s/d Okt 2026). Teks jadwal "jual 1 RD PU bergiliran" dipertahankan, dengan catatan di bagian detail halaman.
- **Lompatan NAV PT/PU** (ambang `analisis_likuiditas.LOMPAT`: PU ±10%, PT ±15% per bulan): 39 kejadian, 33 di indeks utama (tanpa bagi hasil tunai): PU 2017-2025 (terbanyak 2020, 2021, 2023, 2025), PT 2020-2023. Isinya data rusak, mis. Principal Cash Fund Syariah +70.037% lalu -100% (Mei-Jun 2021), SAM Dana Kas Syariah +8.158% (Jul 2023), Mega Asset Multicash Syariah +6.851% (Mei 2021). Kalau tetap dimasukkan, tingkat aman semua opsi naik ke 3,0% (batas atas pencarian): artefak data, jadi aturan mengeluarkan bulan itu dipertahankan.
- **Keranjang 10 produk** (`keranjang.py`, `lab_data.keranjang_konservatif`, 1 dokumen per perubahan; skenario terpisah per aplikasi semua/Bibit/Ajaib/Makmur): saringan syariah, rupiah, aktif (NAV ≤ 14 hari), riwayat ≥ 3 th, bukan bagi hasil tunai, biaya diketahui, dana kelolaan ≥ median; urut biaya termurah, 5 PT + 5 PU bobot sama; return tidak dipakai. Indeks keranjang = rata-rata return produk, bulan tanpa data diisi return kategori (dilaporkan % isian). Halaman memakai skenario yang tingkat amannya lebih kecil (keranjang vs kategori); sampai Okt 2026 selalu kategori (keranjang lebih tinggi karena hanya produk yang masih hidup).
- **Aturan pembentukan ulang (disetujui user 2026-11-08)**: seluruh keranjang dibentuk ulang tiap Januari. Di tengah tahun hanya produk yang keluar yang diganti (calon termurah berikutnya dari urutan yang sama), kalau: (1) NAV tidak terbit > 14 hari / bubar, (2) mulai membagi hasil tunai, (3) biaya naik di atas biaya produk ke-5 calon pengganti, (4) dana kelolaan < persentil 25 produk yang lolos 2 bulan berturut-turut (dicatat di `keranjang_pantau`). Dicek harian (job `keranjang_cek`).

### Analisis profil Moderat & Agresif (2026-11-08, deskriptif, bukan hipotesis, tidak dikunci)
- Skrip `analisis_profil.py`. Indeks RD saham syariah (`Equity Fund`, 69 seri) dan RD campuran syariah (`Mixed Asset Fund`, 35 seri) dari NAB bulanan OJK, aturan sama dengan `analisis_likuiditas` (satu RD satu seri, termasuk yang bubar, min 5 produk/bulan, RD bagi hasil tunai Pasardana dikeluarkan); lompatan > ±30%/bulan dikeluarkan dan didaftar. Index Fund/ETF tidak dipakai.
- **Asumsi**: Konservatif = RD PT/PU 50/50; Moderat = 30% RD saham + 70% Konservatif (35% PT, 35% PU); Agresif = 60% RD saham + 40% Konservatif (20% PT, 20% PU); RD campuran 100%. Tanpa SBN. Rebalance tiap akhir Desember ke bobot awal, tanpa ambang. Penarikan proporsional dari semua bagian (profil dipakai sebagai satu aset di jalur RD tanpa SBN `analisis_penarikan`; Konservatif lewat jalur ini identik dengan Opsi 1).
- **Lompatan saham/campuran (37)**: saham 33 (2017: 5, 2018: 2, 2019: 14 (12 penurunan di Nov 2019, ±31-47%, kemungkinan rugi asli), 2020: 2, 2021: 3, 2024: 2, 2025: 2, 2026: 3), campuran 4 (2019: 1 (Nov 2019 -32%), 2021: 2, 2022: 1). Koreksi 2026-11-08: laporan awal menyebut 13 penurunan saham Nov 2019; yang benar 12 saham + 1 campuran. Karena penurunan Nov 2019 dikeluarkan, indeks saham cenderung terlalu bagus.
- **Hasil Apr 2016 - Okt 2026**: Konservatif +4,51%/th nominal, +1,54% riil, turun terdalam -1,5%, pulih 2 bln, aman 3/5 th 0,6/1,1%. Moderat +1,80% / -1,09%, -11,3%, 41 bln, tidak ada tingkat aman. Agresif -1,04% / -3,84%, -28,5%, belum pulih, tidak ada. RD campuran +0,13% / -2,71%, -20,0%, 67 bln, tidak ada. Jendela 5 th yang modalnya mengalahkan Konservatif: 0 dari 68 untuk ketiganya.
- **Keterbatasan**: 2016-2026 buruk untuk saham Indonesia (hasil sangat bergantung periode, hanya ±2 jendela 5 th terpisah); NAV saja tanpa biaya; RD dikelola aktif oleh MI, bukan indeks.

## Harga bersih 2020+ bebas survivorship (2026-11-08, permintaan user; data, bukan uji)
- Koleksi `lab_data.harga_bersih_2020` (`backend/ingest/harga_bersih.py`, job `harga_bersih`, tombol 'Bangun' di Perawatan, dibaca lewat `harga.bersih*`): semua kode di ringkasan perdagangan resmi IDX 2 Jan 2020 – data terakhir (989 kode, termasuk 26 delisting yang datanya berhenti di hari terakhir tercatat dan 68 kode yang tidak ada di harga Yahoo). Info per kode di `harga_bersih_2020_info` (status, alasan henti dari pengumuman Jul 2023+, periode beku ≥ 20 hari bursa tanpa transaksi, faktor + buktinya, dividen IDX tanpa nilai).
- Penyesuaian = faktor resmi IDX (`Previous ÷ close kemarin`, |f−1| > 2%), hanya diterapkan dengan bukti: split Yahoo (rasio cocok / ada), Yahoo kontinu di ex-date, registry koreksi, pengumuman IDX (kategori aksi korporasi atau judul harga teoretis / saham bonus / HMETD / pemecahan nominal), atau saham tercatat IDX berubah > 1% di −5..+45 hari. Tanpa bukti: harga mentah + kolom `faktor_tanpa_bukti` (saat ini 0 kasus; MFIN 23 Okt 2024 dibuktikan pengumuman 'Harga Teoretis (Saham Bonus)', WSKT 27 Des 2021 dan BABP/DNAR 2021 dibuktikan saham tercatat naik (HMETD)).
- **Pengecualian aturan faktor 0,2–5 (disetujui user 2026-11-08)**: 28 split besar (1:10 s/d 1:25, mis. BYAN, DSSA, CUAN, PTRO) diterapkan karena dikonfirmasi split Yahoo dengan rasio cocok atau Yahoo kontinu. Faktor ekstrem tanpa bukti itu tetap ditahan. Berlaku untuk koleksi ini saja, aturan registry `koreksi_harga` tidak berubah.
- Dividen terpisah (kolom `dividen` disesuaikan, `dividen_mentah`, `dividen_sumber`): Yahoo (diskalakan ke seri IDX) + kalender IDX (tanggal ex; nilai IDX bila ada dan tidak beda > 3× dari Yahoo).
- Open: IDX mengosongkan OpenPrice di ±93% hari 2020-2024 → open Yahoo bila close Yahoo cocok ≤ 2%, selain itu close IDX (`sumber_open`).
- Validasi vs `harga` (921 kode): selisih return harian median 0, p99 0, beda > 1% di 0,03% hari (tidak sepenuhnya independen: `harga` sudah ditambal sel IDX).
- 19 kode DES tidak ada di data IDX 2020+: bukan ganti kode, tapi perusahaan publik yang sudah delisting / tidak tercatat dan masih melapor ke OJK (BRAU, CPDW, RINA, ATPK, ...).

## H34: "Warren Buffett" — cicil saham syariah berkualitas + tambah beli saat turun (dikunci 2026-11-08 atas permintaan user, sebelum kode uji dibuat dan sebelum ada angka return apa pun)
Draf diusulkan 2026-11-08, disetujui user dengan perubahan (keranjang = ROE TTM terendah 8 kuartal tertinggi; delisting utama dinilai 0; laporkan kas menganggur dan saham tak terbeli). Uji ke ±50. Satu versi, tanpa varian.

**Ide.** Cicil rutin ke 10 saham syariah yang ROE-nya konsisten tinggi, tambah beli dari kas cadangan saat harga turun jauh dari rata-rata beli dan valuasi murah dibanding dirinya sendiri, jual hanya kalau kualitas memburuk atau keluar DES.

**Data & periode.** Harga `harga_bersih_2020` (IDX resmi, termasuk delisting & suspensi, lewat `harga.bersih*`), DES `swing.des` (point-in-time), fundamental `swing.fundamental` (hanya laporan dengan `tgl_publikasi` < tanggal keputusan; laba = laba pemilik entitas induk, YTD). Dev Jan 2020 – Des 2023 (data dipotong 29 Des 2023), holdout Jan 2024 – data terakhir, dibuka sekali dan hanya kalau dev lulus semua, setelah review user.

**Aturan.**
- Universe (tiap keputusan): DES pada tanggal itu, median nilai transaksi 60 hari bursa terakhir ≥ Rp5 M, close mentah ≥ Rp50, tidak beku di hari terakhir, ≥ 60 hari data.
- ROE TTM per laporan = laba TTM ÷ ekuitas induk akhir periode; laba TTM = YTD + laba setahun tahun lalu − YTD tahun lalu (`laba_lalu`); laporan tahunan (AUDIT) = labanya sendiri. Laba setahun 2018 diambil dari `laba_lalu` laporan tahunan 2019, dianggap terbit 2019-04-30 (laporan 2018 sudah publik saat itu; satu-satunya sumber di data kita). Ekuitas ≤ 0 → tidak lolos. Ekuitas awal tidak tersedia untuk 2019, jadi pakai ekuitas akhir periode (keputusan teknis sebelum uji).
- Saringan kualitas: laporan dengan periode akhir dalam 24 bulan sebelum keputusan, laporan terbaru ≤ 300 hari; minimal 4 ROE TTM (8 bila ada). **ROE terendah ≥ 12%** (keuangan ≥ 10%). Non-keuangan juga: arus kas operasi TTM laporan terbaru > 0 dan DER = liabilitas ÷ ekuitas total ≤ 1,0. Keuangan = sektor 'Keuangan' di `profil_idx` (snapshot hari ini; kode tanpa profil = non-keuangan). Data tidak cukup = tidak lolos.
- Keranjang: 10 saham universe yang lolos dengan **ROE TTM terendah (8 kuartal) tertinggi**, bobot sama. Dibentuk di hari bursa pertama bulan pertama sejak Jan 2020 dengan ≥ 10 saham lolos (fundamental baru ada sejak 2019, jadi kemungkinan Mar-Mei 2020) atau di Juni pertama, mana yang lebih dulu; lalu dibentuk ulang tiap hari bursa pertama Juni. Kurang dari 10 lolos = semua yang lolos.
- Cicil: tiap hari bursa pertama bulan sejak Jan 2020 setor Rp5 jt: 80% ke kas cicil, 20% ke cadangan (indeks RD pasar uang syariah `analisis_likuiditas` 'PU', bulanan). Kas cicil (sisa + dividen + hasil jual) dibagi rata ke saham keranjang yang ada transaksi hari itu, beli lot utuh (100 lembar mentah) di open. Jatah < 1 lot = "tidak terbeli" (dihitung), uang tetap di kas. Sebelum keranjang ada, uang menunggu di kas cicil.
- Tambah saat turun: tiap close hari bursa terakhir bulan, untuk saham yang dipegang dan masih DES: close ≤ rata-rata harga beli × 0,85 **dan** PBV < median PBV sendiri **dan** lolos saringan kualitas (data terbit ≤ hari itu) → beli di open hari bursa berikutnya sebesar min(cadangan, Rp5 jt), lot utuh, urut penurunan terdalam dulu. Cadangan dicairkan di nilai akhir bulan. PBV = close × saham tercatat ÷ ekuitas induk laporan terakhir yang terbit (USD × kurs). Median PBV sendiri = median PBV di akhir tiap kuartal kalender sebelum keputusan (minimal 4 titik); titik 2019 memakai harga `harga.saham` (Yahoo, satu-satunya harga 2019) × saham tercatat 2 Jan 2020 (keputusan teknis sebelum uji).
- Batas: nilai satu saham maks 15% total (saham + kas + cadangan); pembelian (cicil maupun tambahan) dipotong supaya tidak melewati batas.
- Jual (semua lembar, open, −1 tick, fee 0,25%): (1) di hari rebalance Juni kalau gagal saringan kualitas (termasuk data tidak cukup); (2) tiap hari bursa pertama bulan kalau tidak lagi di DES. Saham yang keluar dari 10 besar tapi masih lolos tetap dipegang tanpa cicilan. Tidak ada jual karena harga. Tidak bisa ditransaksikan (beku) → coba bulan berikutnya.
- Biaya: fee beli 0,15% + jual 0,25% + 1 tick fraksi IDX per sisi (harga mentah). Dividen tunai (kolom `dividen`) × lembar × 0,9 masuk kas cicil di tanggal ex.
- Delisting (data berhenti sebelum akhir dev): **utama dinilai 0**; sensitivitas dicairkan di harga beku terakhir. Saham beku belum delisting: utama dinilai di harga beku terakhir; sensitivitas dinilai 0 selama beku.

**Ukuran.** XIRR dari setoran bulanan dan nilai akhir 29 Des 2023 (utama); turun terdalam harian dari nilai ÷ total setoran; kas menganggur = kas cicil ÷ total setoran (rata-rata & maks harian, cadangan dilaporkan terpisah); jumlah kejadian tidak terbeli; return tertimbang waktu (TWR) per tahun kalender.

**Pembanding.** (a) keranjang dan aturan jual sama, 100% setoran ke cicilan, tanpa cadangan & tambahan; (b) cicil JII (`indeks/JKII`, close hari bursa pertama bulan) + dividen asumsi 2,5%/th diakru harian, tanpa biaya (angka khayal, bukan produk); (c) cicil indeks RD saham syariah (`analisis_profil`, NAV bulanan sudah setelah biaya MI, masuk di NAV akhir bulan sebelumnya), laporan; (d) plasebo 500 acakan (seed 0-499): jumlah dan nominal kejadian tambahan sama dengan H34, tiap kejadian dipindah ke akhir bulan acak (setelah keranjang ada) dan saham acak di antara yang dipegang saat itu, tetap dibatasi cadangan & 15%; (e) standar seragam: cicil bobot sama semua saham universe (rebalance bulanan, tanpa biaya, close + dividen tanpa pajak, delisting diperlakukan sama).

**Kriteria lulus dev (semua):**
1. XIRR > bobot sama universe. 2. XIRR > JII + 2,5%.
3. Tanpa 5 saham penyumbang laba terbesar (dijalankan ulang tanpa saham itu di universe) > bobot sama tanpa 5 penyumbang terbesarnya. 4. Sama untuk 10 saham.
5. TWR tahunan gabungan tanpa tahun kalender terbaik > bobot sama dan JII tanpa tahun terbaiknya masing-masing.
6-8. S1 biaya 2 tick, S2 likuiditas ≥ Rp20 M (pembanding ikut), S3 harga ≥ Rp200 (pembanding ikut): 1-5 tetap lulus.
9. XIRR > (a). 10. XIRR > persentil 95 plasebo (d). 11. Turun terdalam tidak lebih buruk dari (a) lebih dari 2 poin.
Holdout: semua kriteria yang sama tidak boleh gagal.
Laporan saja: (c), sensitivitas delisting di harga beku, beku dinilai 0, setoran Rp1 jt/bulan, isi keranjang per Juni, kejadian tambahan per tahun, 10 penyumbang terbesar (aturan "pemenang besar mendominasi").

**Peringatan sebelum uji.**
- Riset lama keluarga kualitas/valuasi gagal semua: H16a-c (Undervalue tidak mengalahkan pasar), K1-K3 (kalah dari bobot sama; K3 hanya > 26% portofolio acak), analisis konvergensi (Undervalue tidak menambah peluang), analisis cicil JII (tambah saat turun hanya +1-2 poin dan rapuh).
- Kekuatan statistik rendah: dev 4 tahun, 10 saham, keranjang pertama baru ±Mar-Mei 2020, kejadian tambahan kemungkinan sedikit. Dev tidak buta: harga 2020-2023 sudah dipakai di H11a holdout dan eksplorasi 2020+.
- Risiko utama: averaging down ke saham yang terus turun atau dibekukan; laporan keuangan terlambat ±1-3 bulan sehingga "masih lolos kualitas" bisa basi.
- Keterbatasan data: fundamental baru sejak 2019, sektor snapshot hari ini, open IDX 2020-2024 sebagian besar dari Yahoo, 19 kode DES tidak tercatat di IDX.

### Hasil H34 dev (2026-11-08, dijalankan sekali, `backend/research/uji_h34.py dev`, hasil `hasil_riset/h34_dev`): GAGAL, holdout tidak dibuka
`versi_data`: `harga_bersih_2020` 914 kode 2020-01-02 s/d 2023-12-29 (sidik di hasil), cek kualitas 2026-11-07 0 temuan aktif. Sebelum run resmi: bug mekanik diperbaiki dari uji mekanik yang hanya mencetak keranjang/kejadian/kas (dasar batas 15% terhitung ganda, dividen ke saham yang dibeli di hari ex, pembelian terpotong batas 15% terhitung "tidak terbeli", rumus TWR pembanding); tidak ada angka return yang terlihat sebelum perbaikan.
- Universe baru terisi Apr 2020 (syarat 60 hari data dari 2 Jan 2020); keranjang pertama 4 Mei 2020 (15 lolos). Keranjang: Mei 2020 BTPS, SIDO, PTBA, ACES, ICBP, MYOR, MNCN, CPIN, UNTR, KLBF; Jun 2020 BTPS, SIDO, ACES, ICBP, PTBA, SCMA, PWON, MNCN, TLKM, CPIN; Jun 2021 SIDO, SCMA, MYOR, LINK, MIKA, CPIN, KLBF, DMAS, ACES, BTPS; Jun 2022 MARK, SIDO, TLKM, SCMA, MIKA, KLBF, BSSR, LINK, TAPG, DMAS; Jun 2023 BYAN, ADMR, SIDO, BTPS, MIKA, MARK, PTBA, KLBF, TLKM, PRDA.
- Tambah saat turun: 27 kali (2020: 2, 2021: 2, 2022: 11, 2023: 12).

| | XIRR | Turun terdalam | Kas menganggur rata / maks | Tidak terbeli |
|---|---|---|---|---|
| H34 | -8,27% | -42,7% | 8,7% / 80% (cadangan rata 6,1%) | 39 |
| (a) tanpa cadangan & tambahan | -7,69% | -42,2% | 10,3% / 100% | 23 |
| (b) JII + dividen 2,5% | -0,60% | -37,4% | – | – |
| (c) indeks RD saham syariah | -3,63% | -17,6% (bulanan) | – | – |
| Bobot sama universe | -0,56% | -42,6% | – | – |
Kas maks 80-100% = Jan-Apr 2020 sebelum keranjang ada. Setor Rp240 jt, nilai akhir H34 Rp202,4 jt. TWR per tahun H34 38,7 / -8,8 / -11,6 / -14,7% (2020-2023), bobot sama 72,5 / 9,8 / -13,4 / -8,5%.
- Plasebo 500: H34 di persentil 11 (p5 -8,47%, p50 -7,61%, p95 -6,82%): menambah di waktu acak lebih baik dari aturan.
- Standar seragam: dasar 0/5, S1 0/5, S2 1/5 (hanya tanpa 10 saham -12,38% vs -12,48%), S3 0/5. Khusus: 9 ✘, 10 ✘, 11 ✔ (-42,7% vs -42,2%).
- Laporan: delisting di harga beku dan beku dinilai 0 sama persis dengan utama (tidak ada saham delisting/beku yang dipegang); setoran Rp1 jt -6,88% ((a) -6,68%), 176 kali tidak terbeli.
- Penyumbang: laba dari ADMR, BSSR, MIKA, BYAN, DMAS, PTBA, UNTR, TLKM, PWON; rugi terbesar SCMA (-Rp15,5 jt, harga 458 → 170), LINK, BTPS, SIDO, ACES. Pembanding bobot sama penyumbang terbesar: CUAN, MSIN, FILM, BEBS, ISAT.
- Kesimpulan: GAGAL. ROE tinggi yang konsisten di 2019-2020 tidak memprediksi harga 2021-2023; averaging down tanpa jual karena harga menambah uang ke saham yang terus turun.

## H35: "Syariah Global" — lapisan Apresiasi di IDX, global, atau campuran (dikunci 2026-11-08 atas permintaan user, sebelum kode uji dibuat dan sebelum return apa pun dihitung) — lencana pasca hasil (kontaminasi tercatat)
- **Ide**: lapisan Apresiasi lebih terlindung dari "dekade hilang" kalau dipegang campuran saham syariah IDX + global (dalam rupiah) daripada 100% IDX. Tujuannya perlindungan, bukan menang di tiap dekade.
- **Kontaminasi (jujur)**: arah umum sudah diketahui (IDX jauh lebih baik dari AS di 2000-2015, sebaliknya sesudahnya; JII 2026 turun ±45% s/d Okt). Saat audit data 2026-11-08 sempat terlihat level JII per akhir tahun dan level awal-akhir ^IMUS/^IMXL (return per periode tidak dihitung). Kriteria K1-K4 dipilih user sesudah audit itu. Tidak ada holdout bersih. Jadi: kalau lolos, statusnya **"lolos pasca hasil"** dan **wajib uji maju mulai Jan 2027 (indeks RD/ETF, 3 th)** sebelum dipakai untuk porsi besar; kalau gagal, gagal.
- **Data (audit 2026-11-08)**: `indeks/JKII` (Yahoo ^JKII, harga saja, Jul 2000+, diperbarui s/d 6 Nov 2026, riwayat lama identik); `indeks_luar/gl_djim_titans` (^IMXL, Dow Jones Islamic Market Titans 100, harga saja, Mei 2001+); `indeks_luar/gl_msci_world_islamic` (ISDW.L, iShares MSCI World Islamic USD Dist, total return lewat adj_close, TER 0,30% sudah di dalam, Jan 2008+); `indeks_luar/us_djim` (^IMUS, DJ Islamic Market US, harga saja) untuk sensitivitas; keduanya diunduh `backend/ingest/pasar_luar.py indeks --nama ...`. ISWD.L/ISUS.L (kelas GBp) tidak dipakai (adj tanpa dividen, data rusak sebelum Jun 2017). DJIM World, S&P 500 Shariah, S&P Global BMI Shariah, MSCI World Islamic (indeks) tidak tersedia di Yahoo; situs S&P/MSCI bukan sumber Chrome Lab yang diizinkan.
- **Kurs (keputusan user)**: bulanan `makro/kurs_akhir_bulan` (FRED CCUSSP02IDM650N, kurs akhir periode), tidak menambal kurs harian. FRED berhenti Des 2023 (dicek 2026-11-08), jadi **Jan 2024 - Okt 2026 memakai close terakhir tiap bulan `kurs/USD`** (bulan-bulan itu lengkap, tanpa tambalan). Selisih FRED vs `kurs/USD` akhir bulan dilaporkan untuk bulan yang datanya lengkap (tidak ada jeda > 7 hari dan tidak ada titik > 5% dari median 21 hari di bulan itu).
- **Jalur 1 (indeks, bulanan, return Jun 2001 - Okt 2026)**:
  - IDX = JKII close akhir bulan × dividen 2,5%/th (dibagi rata per bulan) − biaya 0,5%/th.
  - Global (USD) = ^IMXL + dividen 1,8%/th − biaya 0,6%/th s/d Jan 2008 (return Feb 2008 pertama yang punya close ISDW.L akhir Jan); mulai Feb 2008 ISDW.L adj_close − biaya tambahan 0,3%/th (TER sudah di NAV). Rupiah = (1 + return USD) × (1 + perubahan kurs) − 1.
  - Cek asumsi dividen JII (laporan saja): XIJI (`etf/XIJI`, TR) vs JKII harga di periode yang sama 2013+.
- **Portofolio**: 100% IDX, 70/30, **50/50 (utama)**, 100% global (IDX/global); dikembalikan ke bobot awal tiap akhir Desember, biaya rebalance 0,5% dari nilai yang dipindah.
- **Metrik (rupiah)**: CAGR, turun terdalam (bulanan), lama pulih (bulan dari puncak ke pulih; "belum pulih" bila belum), MAR = CAGR ÷ |turun terdalam|, jendela 10 th bergulir (120 bulan, tiap bulan): terburuk, terbaik, % jendela > 100% IDX; korelasi bulanan IDX vs global; pemecahan global: CAGR USD vs CAGR kurs vs CAGR rupiah. Per dekade (Jun 2001 - Des 2009, 2010-2019, Jan 2020 - Okt 2026) dilaporkan, **bukan kriteria**.
- **Kriteria lolos (semua harus lolos; dinilai untuk 50/50)**:
  - K1: CAGR jendela 10 th TERBURUK 50/50 > jendela 10 th terburuk 100% IDX.
  - K2: seluruh periode, MAR 50/50 ≥ MAR 100% IDX.
  - K3: seluruh periode, CAGR 50/50 tidak lebih rendah dari 100% IDX lebih dari 2 poin/th.
  - K4: K1-K3 tetap lolos di skenario pesimis gabungan (dividen JII 0%, dividen global 1,0%, ^IMUS menggantikan ^IMXL sampai Jan 2008). Varian satu-per-satu dilaporkan, bukan kriteria.
- **Jalur 2 (produk nyata, deskriptif, bukan kriteria)**: indeks RD saham syariah IDR (`analisis_profil.indeks_baru`, aturan sama) vs indeks RD Global Fund saham syariah USD dari NAB bulanan OJK: satu RD satu seri (kelas dobel dikeluarkan), termasuk yang bubar, min 5 produk/bulan (mulai Jul 2016), RD bagi hasil tunai Pasardana dikeluarkan, RD sukuk/campuran/pendapatan/emas dikeluarkan (dari nama), lompatan > ±30%/bulan dikeluarkan dan didaftar. Rupiah = NAB ÷ unit (kurs OJK sendiri); NAV USD di `rd_ojk` dihitung dari kurs Yahoo jadi selisih kurs OJK tidak bisa diukur dari sini (pengukuran lama Pasardana: median 18 bp, p95 ±3%). Biaya sudah di NAV. Isi kategori campuran: ±22 global, 12 Asia/China/ASEAN/India, 3 US. Periode Jul 2016 - Okt 2026 menguntungkan global (IDX buruk), jadi hanya gambaran.
- **Risiko wajib**: (1) indeks global syariah ±40-60% teknologi AS (mega-cap sedikit); (2) kurs dua arah: pelemahan rupiah 2001-2026 menambah hasil global, kalau rupiah menguat hasil tergerus; (3) saringan syariah beda: DES OJK (utang berbasis bunga ≤ 45% aset, pendapatan non-halal ≤ 10%) vs AAOIFI/DJIM/MSCI (utang ≤ 33% kapitalisasi pasar/aset, non-halal ≤ 5%); (4) biaya RD global ±2%/th + selisih kurs beli/jual bank; (5) minimal beli RD USD (sering US$10-100) dan tidak semua ada di Bibit/Ajaib/Makmur; (6) RD Global Fund campuran wilayah, bukan indeks dunia; (7) jalur 1 indeks tanpa biaya nyata RD dan dividen sebelum 2008 diasumsikan; (8) bebas survivorship hanya di jalur 2.
- Script `backend/research/uji_h35.py`, hasil `hasil_riset/h35_hasil`. Dijalankan sekali.

### Hasil H35 (2026-11-08, dijalankan sekali, `backend/research/uji_h35.py`, hasil `hasil_riset/h35_hasil`): K1-K4 LOLOS → **lolos pasca hasil**, wajib uji maju Jan 2027
- Perbaikan kode sebelum ada angka tercetak: jalur 2 crash di hitungan per dekade (tidak berlaku untuk 2016+) dan encoding terminal; tidak ada angka yang terlihat sebelum perbaikan. JKII diperbarui s/d 6 Nov 2026, riwayat lama identik (0 beda).
- Jalur 1, return bulanan Jun 2001 - Okt 2026 (305 bulan), rupiah:

| Portofolio | CAGR | Turun terdalam | Lama pulih | MAR | J10 th terburuk | J10 th terbaik | % J10 > IDX |
|---|---|---|---|---|---|---|---|
| 100% IDX | +8,3% | -61,4% (Feb-Okt 2008) | 31 bln | 0,14 | -7,2% (s/d Okt 2026) | +29,2% | - |
| 70/30 | +9,4% | -49,6% | 33 bln | 0,19 | +0,1% | +23,4% | 60% |
| **50/50** | **+9,5%** | **-42,6%** | 33 bln | **0,22** | **+2,8%** (s/d Mar 2025) | +19,3% | 56% |
| 100% global | +7,8% | -46,5% (2001-2003) | 73 bln | 0,17 | -0,5% | +14,5% | 55% |

- Korelasi bulanan IDX vs global (rupiah) 0,08. Terlama di bawah puncak: 100% IDX 105 bulan (masih berjalan), 50/50 32 bulan.
- Per dekade (laporan): Jun 2001-2009 IDX +27,2%, 50/50 +14,2%, global -1,3%; 2010-2019 IDX +7,4%, 50/50 +9,4%, global +10,6%; 2020 - Okt 2026 IDX -10,4%, 50/50 +3,9%, global +15,9%.
- Pemecahan global (USD lokal / kurs / rupiah): penuh +5,7 / +2,0 / +7,8%; 2001-2009 +0,5 / -1,9 / -1,3%; 2010-2019 +6,3 / +4,0 / +10,6%; 2020+ +11,5 / +3,9 / +15,9%.
- Kriteria: K1 +2,8% vs -7,2% ✔; K2 MAR 0,222 vs 0,135 ✔; K3 +9,5% vs +8,3% (batas +6,3%) ✔; K4 pesimis gabungan: K1 +1,6% vs -9,4%, K2 0,191 vs 0,087, K3 +8,1% vs +5,7% ✔. Varian satu-per-satu (dividen JII 0%, global 1,0%, ^IMUS pra-2008) semuanya ✔.
- Kurs: FRED vs `kurs/USD` akhir bulan di 260 bulan lengkap: median 0,26%, p95 1,47%, maks 4,78%, > 3% hanya 1 bulan; 10 bulan tidak lengkap. 2024+: 1 pencilan (26 Des 2024, bukan akhir bulan, tidak terpakai).
- Cek dividen JII: XIJI TR vs JKII harga Mei 2013 - Okt 2026 selisih +2,29%/th (asumsi dividen 2,5% − biaya 0,5% = +2,0%), asumsi wajar.
- Jalur 2 (deskriptif, Jul 2016 - Okt 2026; lokal 69 seri, global 34 seri (7 bubar), 5-27 produk/bulan; 1 lompatan dikeluarkan: Panin Global Sharia Equity Apr 2026 +35,8%): 100% RD saham lokal -5,8%/th, DD -52,8% (belum pulih); 70/30 -1,6% / -35,1%; 50/50 +1,0% / -25,3%; 100% RD global +7,1% / -29,0%. Korelasi 0,07. Semua jendela 5 th: campuran & global > lokal.
- Catatan penting: jendela 10 th terburuk 100% IDX berakhir Okt 2026, jadi K1 sangat dipengaruhi kejatuhan JII 2026 (±-45% s/d Okt). Data 2001-2009 menguntungkan IDX, 2020+ menguntungkan global; campuran menang karena keduanya bergantian, bukan karena satu dekade.
- Kesimpulan: lolos pasca hasil (bukan bukti). Aturan uji maju Jan 2027 (produk RD/ETF mana, kriteria) belum dikunci, perlu keputusan user. Status registry `uji_maju` + lencana pasca hasil.

## Portofolio Pertumbuhan Syariah (2026-11-08, permintaan user; cara investasi dari H35 yang lolos pasca hasil, deskriptif, bukan bukti)
- **Cara**: setoran bulanan tetap ke 50% RD saham syariah Indonesia + 50% RD saham syariah global, dikembalikan ke 50/50 tiap akhir Desember. Halaman `#pertumbuhan`, `backend/research/keranjang_pertumbuhan.py` (job `pertumbuhan_hitung`, jadwal harian `--bila-perlu` setelah `keranjang_cek`), API `/api/pertumbuhan`, `/api/pertumbuhan/rencana`.
- **Keranjang** (`lab_data.keranjang_pertumbuhan`, satu dokumen per perubahan, per aplikasi semua/bibit/makmur/ajaib): saringan seperti keranjang konservatif (aktif ≤ 14 hari, riwayat ≥ 3 th, biaya diketahui, dana kelolaan ≥ median sejenis, urut biaya termurah), return tidak dipakai. **Platform wajib** (≥ 1 aplikasi Bibit/Makmur/Ajaib; kosong = gugur "platform tidak diketahui"). **Minimal beli tidak menyaring** (angka MI sering jauh lebih besar dari aplikasi, mis. Schroder US$10.000); di kartu "cek di aplikasi" bila > Rp1 jt / US$100.
- **Aturan bagi hasil untuk RD saham (disetujui user 2026-11-08)**: hanya tanda bagi hasil tunai Pasardana. Aturan keranjang konservatif (CAGR < 1% dianggap bagi hasil) salah membuang 35 RD saham yang sekadar rugi; keranjang konservatif tidak diubah.
- **Lokal**: 3 RD saham/indeks/ETF syariah IDR. **Global (keputusan user 2026-11-08)**: hanya RD global luas; regional (Asia/China/ASEAN/India/US-only) dan satu sektor ditolak (RD teknologi BNP DJIM Tech Titans 50 & Batavia Technology: "ditolak: satu sektor, menambah risiko konsentrasi teknologi AS"). Yang lolos hanya **Schroder Global Sharia Equity Fund USD** (Bibit), menanggung seluruh porsi global 50%. Kalau Schroder gagal saringan: keranjang global kosong + peringatan + daftar calon pengganti, tidak dipilih otomatis. Makmur & Ajaib: tidak ada RD global luas → peringatan "gunakan Bibit untuk porsi global", tidak diisi diam-diam.
- **Hitungan**: jalur indeks = hasil H35; jalur produk = NAB bulanan OJK (rupiah = NAB/unit), aturan jalur 2 H35, bulan sebelum produk ada diisi indeks kategori (lokal RD saham syariah, global RD Global Fund saham syariah), lompatan > ±30% diganti kategori. SIP Rp1/bulan dari tiap tanggal mulai, jendela 5 & 10 th. **Rem MIN**: 5 th = skenario utuh dengan median lebih rendah antara keranjang dan kategori; 10 th = antara indeks, kategori, dan keranjang (label sumber + jumlah tanggal mulai).
- **Hasil awal (2026-11-08, data s/d Okt 2026)**: keranjang semua/Bibit = BRI Indeks Syariah, BNP Paribas Pesona Syariah, Manulife Syariah Sektoral Amanah A + Schroder. Isian kategori lokal 12,1% (Manulife Amanah 36%), global 0%. SIP Rp1 jt/bln: 5 th sumber kategori (65 tanggal mulai) median Rp59,1 jt dari setoran Rp60 jt, terburuk Rp52,9 jt, untung 31%; 10 th sumber kategori (5 tanggal mulai) median Rp140,1 jt dari Rp120 jt, terburuk Rp132,6 jt; jalur indeks 10 th (186 tanggal mulai) median Rp192,3 jt, terburuk Rp135,5 jt, untung 100%. Lolos per aplikasi (lokal / global luas): Bibit 6/1, Makmur 3/0, Ajaib 4/0.
- **Perubahan rem MIN sisi global (2026-11-08, permintaan user, dilakukan SETELAH melihat hasil)**: pembanding "kategori" sisi global dulu = semua RD saham syariah USD (termasuk regional Asia/China/ASEAN/India dan satu sektor) yang justru dikeluarkan dari keranjang, jadi tidak sejenis. Sekarang = RD saham syariah global luas saja (penanda sama dengan saringan keranjang, ditambah "EM/pasar berkembang" sebagai regional; tetap termasuk yang bubar). Jumlahnya hanya 1-10 produk per bulan (< 5 sampai 2020, 13 seri, 3 bubar), jadi dipakai **pengganti: ISDW.L (MSCI World Islamic, total return, rupiah) − biaya 2%/th**, berlabel jelas. Sisi Indonesia tidak berubah. Angka versi lama disimpan di `hasil_riset/pertumbuhan.versi_lama` dan tampil di tab Data historis.
  - Sebelum → sesudah (setor Rp1 jt/bln, semua/Bibit): **5 th** sumber kategori (65 bulan mulai) median Rp59,1 jt → Rp64,3 jt, terburuk Rp52,9 → Rp57,9 jt, untung 31% → 95% (sumber tetap kategori, karena keranjang Rp67,2 jt lebih tinggi). **10 th** sumber kategori → **keranjang** (5 bulan mulai): median Rp140,1 → Rp155,4 jt, terburuk Rp132,6 → Rp143,0 jt, untung 100% → 100% (kategori baru Rp160,8 jt lebih tinggi dari keranjang). Makmur/Ajaib (tanpa keranjang global): 10 th sumber kategori Rp160,8 jt.
- **Halaman dirombak (2026-11-08, permintaan user)**: tiga tab tanpa bagian terlipat: Rencana & daftar belanja (isi data, hasil 5 & 10 th berdampingan, kartu produk + kinerja masa lalu dalam rupiah, jadwal, risiko), Data historis (ringkasan 25 th, grafik Rp1 + turun dari puncak untuk indeks/keranjang/kategori, per dekade, hasil per tahun, hasil setor rutin per bulan mulai, semua sumber + versi lama, hasil H35 + pecahan kurs), Cara kerja & aturan (penjelasan, beda dengan menu lain, langkah, istilah, aturan keranjang, lolos per aplikasi, calon pengganti global, produk gugur, data & keterbatasan, tombol Hitung ulang).


## H37: "Syariah Global + Emas" — saham + emas: 40% JII / 40% global syariah / 20% emas, rupiah (dikunci 2026-11-12 atas permintaan user, sebelum return portofolio apa pun dihitung)

- **Data**: persis H35 (JII dividen 2,5%/th biaya 0,5%/th; ^IMXL s/d Jan 2008 dividen 1,8%/th, lalu ISDW.L adj_close; kurs FRED s/d Des 2023 lalu Yahoo). Emas = GC=F akhir bulan x kurs akhir bulan yang sama, biaya kepemilikan 0,5%/th. Bulan bolong = error. Tidak ada seri emas rupiah nyata dan tidak ada data spread di database.
- **Portofolio**: 40/40/20 mulai Jun 2001, rebalance akhir Desember. Biaya JII & global = cara H35. Spread emas 3% pulang-pergi (1,5% per sisi, termasuk pembelian awal). Pembanding = H35 50/50 dihitung ulang dengan kode dan data sama di periode sama.
- **Periode**: dev Jun 2001 - Des 2013; holdout Jan 2014 - Okt 2026, disegel (`holdout_disegel_h37`), dibuka sekali atas konfirmasi user.
- **Kriteria (utama wajib 3/3)**: (1) DD bulanan lebih baik dari H35 ≥ 5 poin; (2) CAGR 10 th bergulir terburuk > H35; (3) CAGR ≥ H35 − 1 poin/th. **Sensitivitas terdaftar**: bobot 45/45/10 dan 35/35/30 (spread 3%), spread pulang-pergi emas 1% dan 6% (biaya kepemilikan tetap 0,5%/th); tiap varian ≥ 2/3, gagal satu = H37 gagal.
- **Hasil dev (2026-11-12, `uji_h37.py`, `hasil_riset/h37_dev`)**: LOLOS dev. H37 CAGR 14,6% / DD -34,2% (lembah Okt 2008) / J10 terburuk +14,7% / vol 13,6%; H35 14,1% / -42,6% / +13,7% / 15,8%. Korelasi emas-JII -0,04, emas-global 0,24. Sensitivitas: 45/45/10 2/3 (K1 gagal, DD -38,4%), 35/35/30 3/3, emas 1% 3/3, emas 6% 2/3 (K2 gagal, J10 +13,4%). 32 jendela 10 th (tumpang tindih). Holdout belum dibuka.
- **Keterbatasan**: dev pendek dan berisi krisis 2008 yang menguntungkan emas; emas futures bukan Antam; asumsi biaya; kontaminasi arah data (H35).
