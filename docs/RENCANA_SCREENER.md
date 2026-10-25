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

## Uji maju Pemburu Dividen (dividen_v1), dikunci 2026-10-23

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
