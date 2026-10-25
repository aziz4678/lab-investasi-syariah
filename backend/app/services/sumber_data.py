import json
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from backend.core.config import ROOT
from backend.db import data as dt
from backend.db import koneksi as d

URL_LAPKEU = "https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan/"
TENGGAT = {"TW1": (4, 30, 0), "TW2": (8, 31, 0), "TW3": (10, 31, 0), "AUDIT": (3, 31, 1)}
URUT = {"TW1": 1, "TW2": 2, "TW3": 3, "AUDIT": 4}
JEDA_LAPORAN = 10
JEDA_KSEI = 25
MIN_EMITEN = 300
JEDA_DIVIDEN = 30
JEDA_PENGUMUMAN = 7
JEDA_IDX_HARIAN = 5
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

SUMBER = [
    {"id": "harga", "nama": "Harga harian saham", "dipakai": ["Follow Tren", "Emiten"], "strategi": True,
     "sumber": "Yahoo Finance (gratis, otomatis)", "cara": "otomatis", "frekuensi": "Setiap hari bursa setelah 17:00",
     "langkah": ["Otomatis saat 'Perbarui hari ini' atau jadwal 17:30 (mengunduh 2 tahun terakhir semua saham DES)."],
     "tombol": "paper_harian", "label_tombol": "Perbarui hari ini"},
    {"id": "harga_riset", "nama": "Harga saham riset sejak 2010 (921 saham)", "dipakai": ["Backtest", "Hipotesis", "Emiten (grafik harga panjang)"], "strategi": False,
     "sumber": "Yahoo Finance (gratis, otomatis). Hanya bar yang sudah final (setelah 17:00 WIB) yang disimpan", "cara": "otomatis",
     "frekuensi": "Setiap hari bursa (jadwal 17:30)",
     "langkah": ["Otomatis lewat jadwal 17:30, atau tekan 'Perbarui harga riset'. Data ±3 minggu terakhir selalu ditimpa ulang supaya angka sementara terkoreksi.",
                 "Saham yang ada dividen/split baru diunduh ulang penuh sejak 2010 supaya harga tersesuaikan tidak patah.",
                 "Unduh ulang semua sejak 2010: tombol di panel Perawatan."],
     "tombol": "harga_perbarui", "label_tombol": "Perbarui harga riset"},
    {"id": "pasar", "nama": "Data pasar (IHSG, kurs USD/IDR, minyak, emas, S&P 500, VIX, EEM)", "dipakai": ["Beranda", "ETF", "Reksa Dana", "Emiten (Valuasi)", "Riset"], "strategi": False,
     "sumber": "Yahoo Finance (gratis, otomatis). Bar hari berjalan tidak disimpan (IDX final 17:00 WIB, AS setelah tutup New York, kurs/komoditas besoknya)", "cara": "otomatis",
     "frekuensi": "Setiap hari bursa (jadwal 17:30)",
     "langkah": ["Otomatis lewat jadwal 17:30, atau tekan 'Perbarui data pasar'. Data ±3 minggu terakhir selalu ditimpa ulang."],
     "tombol": "pasar_perbarui", "label_tombol": "Perbarui data pasar"},
    {"id": "des", "nama": "Daftar Efek Syariah (DES)", "dipakai": ["Follow Tren", "Emiten"], "strategi": True,
     "sumber": "OJK (gratis, otomatis)", "cara": "otomatis", "frekuensi": "2x setahun: berlaku 1 Juni dan 1 Desember (terbit akhir Mei / akhir November)",
     "langkah": ["Jadwal 17:30 mengecek sendiri dari 20 Mei-Juni dan 20 November-Desember.",
                 "Bisa juga tekan 'Cek DES baru'. Lampiran XLSX disimpan ke arsip MongoDB dan daftar syariah dibangun ulang.",
                 "Kalau OJK menerbitkan di luar jadwal biasa, cek tanggal berlaku di log."],
     "tombol": "des_perbarui", "label_tombol": "Cek DES baru"},
    {"id": "ksei", "nama": "Kepemilikan saham KSEI", "dipakai": ["Emiten (panel Kepemilikan)"], "strategi": False,
     "sumber": "KSEI (gratis, lewat tombol)", "cara": "tombol", "frekuensi": f"Bulanan, data akhir bulan terbit ±{JEDA_KSEI} hari kemudian",
     "langkah": ["Tekan 'Perbarui KSEI' saat statusnya 'perlu diperbarui'. Hanya bulan yang belum ada yang diunduh."],
     "tombol": "ksei_perbarui", "label_tombol": "Perbarui KSEI"},
    {"id": "lapkeu", "nama": "Tanggal publikasi laporan keuangan", "dipakai": ["Emiten (jadwal laporan)", "Laporan keuangan (tanggal terbit)"], "strategi": False,
     "sumber": "IDX, lewat browser (situs IDX menolak script)", "cara": "browser", "frekuensi": "Tiap kuartal: TW1 (Mei), TW2 (Sep), TW3 (Nov), tahunan (April)",
     "skrip": "idx_lapkeu_browser.js", "url": URL_LAPKEU,
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "Di tab IDX tekan F12 → tab Console. Kalau Chrome meminta, ketik allow pasting lalu Enter.",
                 "Tekan 'Salin script' di sini, tempel di Console, lalu Enter.",
                 "Tunggu sampai muncul 'SELESAI' (±5-10 menit). File idx_lapkeu.json terunduh ke folder Downloads.",
                 "Kembali ke sini, tekan 'Impor tanggal laporan'. File diambil otomatis dari Downloads."],
     "tombol": "impor_lapkeu", "label_tombol": "Impor tanggal laporan"},
    {"id": "fundamental", "nama": "Isi laporan keuangan (laba, pendapatan, neraca)", "dipakai": ["Emiten (panel Fundamental)"], "strategi": False,
     "sumber": "IDX inline XBRL, lewat browser", "cara": "browser", "frekuensi": "Tiap kuartal, setelah tanggal laporan diimpor",
     "skrip": "idx_fundamental_browser.js", "url": URL_LAPKEU,
     "langkah": ["Impor tanggal laporan dulu (baris di atas).",
                 "Buka halaman IDX → F12 → Console (tab yang sama boleh).",
                 "Tekan 'Salin script' di sini, tempel di Console, Enter. Otomatis mengambil tahun ini (semua kuartal) + laporan tahunan tahun lalu.",
                 "Lama (±1-2 jam), tunggu sampai muncul 'SEMUA SELESAI'. Biarkan tab terbuka. Kalau IDX menolak terus, script berhenti dan menyimpan *_sebagian.json; jalankan ulang nanti.",
                 "Tekan 'Impor laporan keuangan'. File idx_fundamental_<tahun>.json diambil dari Downloads lalu koleksi dibangun ulang."],
     "tombol": "impor_fundamental", "label_tombol": "Impor laporan keuangan"},
    {"id": "profil", "nama": "Profil emiten (bidang usaha, pemegang saham, direksi)", "dipakai": ["Emiten (header profil)"], "strategi": False,
     "sumber": "IDX, lewat browser. Tanpa ini dipakai Yahoo Finance (bahasa Inggris, tanpa nama pemegang saham)", "cara": "browser",
     "frekuensi": "Tiap 3 bulan, atau setelah RUPS / perubahan pemegang saham besar",
     "skrip": "idx_profil_browser.js", "url": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/",
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' di sini → tempel → Enter. Daftar kode saham sudah terisi otomatis.",
                 "Tunggu sampai muncul 'SELESAI' (±10-15 menit). File idx_profil.json terunduh ke Downloads.",
                 "Tekan 'Impor profil emiten'."],
     "tombol": "impor_profil", "label_tombol": "Impor profil emiten"},
    {"id": "reksadana", "nama": "Reksa dana & sukuk syariah (NAV, biaya, kupon, yield)", "dipakai": ["Reksa Dana & Sukuk"], "strategi": False,
     "sumber": "Pasardana (gratis, otomatis). Riwayat NAV baru ±1 tahun; data disimpan tiap hari supaya makin panjang", "cara": "otomatis",
     "frekuensi": "Setiap hari bursa (jadwal 17:30); detail produk diambil ulang tiap 7 hari",
     "langkah": ["Otomatis lewat jadwal 17:30, atau tekan 'Perbarui reksa dana'. Pengambilan pertama ±6 menit, berikutnya ±1 menit."],
     "tombol": "rd_perbarui", "label_tombol": "Perbarui reksa dana"},
    {"id": "ojk_nab", "nama": "NAB bulanan reksa dana sejak 2013 (OJK)", "dipakai": ["Reksa Dana & Sukuk (riwayat panjang)"], "strategi": False,
     "sumber": "Portal reksa dana OJK, lewat browser (situs menolak script). Termasuk reksa dana yang sudah bubar", "cara": "browser",
     "frekuensi": "Bulanan, data akhir bulan terbit tanggal 8 bulan berikutnya",
     "skrip": "ojk_nab_browser.js", "url": "https://reksadana.ojk.go.id/Public/StatistikNABReksadanaPublic.aspx",
     "langkah": ["Tekan 'Buka halaman OJK' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' → tempel → Enter. Kalau Chrome bertanya 'download multiple files', pilih Allow.",
                 "Tunggu sampai muncul '[ojk] SELESAI' (±15-30 menit untuk 2013 s/d sekarang). Satu file ojk_nab_<tahun>.json per tahun masuk Downloads.",
                 "Tekan 'Impor NAB OJK'. Untuk pembaruan bulanan, ubah TAHUN_MULAI di baris pertama script ke tahun berjalan."],
     "tombol": "impor_ojk_nab", "label_tombol": "Impor NAB OJK"},
    {"id": "dividen_idx", "nama": "Jadwal dividen resmi (cum, ex, bayar)", "dipakai": ["Pemburu Dividen (jadwal, kalkulator)", "Emiten (panel Dividen)"], "strategi": False,
     "sumber": "Kalender IDX + profil emiten, lewat browser. Nilai dividen lama tetap dari Yahoo Finance", "cara": "browser",
     "frekuensi": f"Tiap {JEDA_DIVIDEN} hari; paling ramai April-Juli (musim RUPS)",
     "skrip": "idx_dividen_browser.js", "url": "https://www.idx.co.id/id/perusahaan-tercatat/aksi-korporasi/",
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' di sini → tempel → Enter.",
                 "Tunggu sampai muncul 'SELESAI' (±3-5 menit: kalender 2015 s/d 3 bulan ke depan + nilai dividen terbaru). File idx_dividen.json terunduh ke Downloads.",
                 "Tekan 'Impor jadwal dividen'. Log menampilkan hasil pencocokan dengan Yahoo."],
     "tombol": "impor_dividen", "label_tombol": "Impor jadwal dividen"},
    {"id": "idx_logo", "nama": "Logo resmi emiten", "dipakai": ["Semua tabel saham", "Emiten (header)", "Pencarian"], "strategi": False,
     "sumber": "Logo emiten di situs IDX, lewat browser. Emiten tanpa logo IDX memakai ikon situs perusahaan", "cara": "browser",
     "frekuensi": "Tiap 180 hari, atau saat banyak emiten baru",
     "skrip": "idx_logo_browser.js", "url": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/",
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' di sini → tempel → Enter.",
                 "Tunggu sampai kotak progres menulis 'SELESAI' (±5-10 menit). File idx_logo.json terunduh ke Downloads.",
                 "Tekan 'Impor logo'."],
     "tombol": "impor_logo", "label_tombol": "Impor logo"},
    {"id": "pengumuman", "nama": "Pengumuman & aksi korporasi IDX",
     "dipakai": ["Emiten (panel Pengumuman & aksi korporasi)"], "strategi": False,
     "sumber": "Keterbukaan informasi IDX (RUPS, dividen, right issue, buyback, suspensi, laporan kepemilikan), lewat browser. Riwayat tersedia sejak Juli 2023", "cara": "browser",
     "frekuensi": f"Setiap hari bursa; cukup diperbarui tiap {JEDA_PENGUMUMAN} hari",
     "skrip": "idx_pengumuman_browser.js", "url": "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi/",
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' di sini → tempel → Enter. Script otomatis hanya mengambil bulan sejak data terakhir di database.",
                 "Tunggu sampai kotak progres menulis 'SELESAI' (pembaruan ±1-3 menit; pengambilan pertama ±30 menit dan ±10 file). File idx_pengumuman_<tanggal>_XX.json masuk Downloads.",
                 "Kalau jumlah file di Downloads kurang dari yang ditulis log, izinkan unduhan otomatis untuk idx.co.id lalu ketik simpanUlangPengumuman() di Console.",
                 "Tekan 'Impor pengumuman'. File yang sudah pernah diimpor dilewati."],
     "tombol": "impor_pengumuman", "label_tombol": "Impor pengumuman"},
    {"id": "kepemilikan_pdf", "nama": "Transaksi orang dalam, pemegang besar & anggota indeks", "dipakai": ["Emiten (panel Transaksi orang dalam & pemegang besar, chip anggota indeks)"],
     "strategi": False,
     "sumber": "Isi PDF laporan kepemilikan KSEI di IDX (format standar sejak 28 Nov 2025) + daftar pemegang saham di atas 1% (bulanan sejak Mar 2026) + lampiran Excel evaluasi indeks (JII, JII70, ISSI, LQ45, IDX30, dll, sejak 2024). File tidak disimpan, hanya angkanya",
     "cara": "browser", "frekuensi": f"Setiap hari bursa; cukup diperbarui tiap {JEDA_PENGUMUMAN} hari, setelah pengumuman diperbarui",
     "skrip": "idx_kepemilikan_browser.js", "url": "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi/",
     "langkah": ["Perbarui pengumuman dulu (baris di atas), karena daftar PDF diambil dari pengumuman.",
                 "Tekan 'Ambil otomatis' (Chrome Lab) atau salin script ke Console IDX. Daftar PDF yang belum dibaca terisi otomatis.",
                 "Pengambilan pertama ±3.200 PDF (±1 jam); berikutnya hanya PDF baru. PDF dibungkus jadi file idx_kepemilikan_<tanggal>_XX.json di Downloads.",
                 "Tekan 'Impor kepemilikan' (otomatis kalau lewat 'Ambil otomatis')."],
     "tombol": "impor_kepemilikan", "label_tombol": "Impor kepemilikan"},
    {"id": "idx_harian", "nama": "Ringkasan perdagangan & transaksi asing harian IDX", "dipakai": ["Riset (data asing, uji H7)"], "strategi": False,
     "sumber": "Ringkasan perdagangan IDX, lewat browser. Semua saham termasuk yang sudah delisting, sejak 2020", "cara": "browser",
     "frekuensi": f"Setiap hari bursa; cukup diperbarui tiap {JEDA_IDX_HARIAN} hari bursa",
     "skrip": "idx_harian_browser.js", "url": "https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/",
     "langkah": ["Tekan 'Buka halaman IDX' dan tunggu halamannya selesai dimuat.",
                 "F12 → Console → tekan 'Salin script' di sini → tempel → Enter. Tanggal mulai terisi otomatis (hari setelah data terakhir).",
                 "Tunggu sampai kotak progres menulis 'SELESAI' (±2 detik per hari bursa). File idx_harian_baru_*.json masuk Downloads.",
                 "Tekan 'Impor ringkasan perdagangan'. Data baru digabung ke data lama, tidak menimpa."],
     "tombol": "impor_idx_harian", "label_tombol": "Impor ringkasan perdagangan"},
    {"id": "makro", "nama": "Makro Indonesia (BI-Rate, inflasi)", "dipakai": ["Reksa Dana & Sukuk (Perbandingan)", "Beranda"], "strategi": False,
     "sumber": "Bank Indonesia (unduhan Excel resmi, gratis, otomatis): BI-Rate sejak Apr 2016, inflasi tahunan sejak 2003; suku bunga antarbank dari FRED",
     "cara": "otomatis", "frekuensi": "BI-Rate tiap rapat dewan gubernur (bulanan), inflasi awal bulan; diperiksa tiap hari bursa (jadwal 17:30)",
     "langkah": ["Otomatis lewat jadwal 17:30, atau tekan 'Perbarui makro'."],
     "tombol": "makro_perbarui", "label_tombol": "Perbarui makro"},
    {"id": "etf", "nama": "ETF syariah Indonesia & luar negeri (harga, biaya, AUM, dividen)", "dipakai": ["ETF"], "strategi": False,
     "sumber": "Yahoo Finance + Pasardana (gratis, otomatis)", "cara": "otomatis", "frekuensi": "Setiap hari bursa (jadwal 17:30)",
     "langkah": ["Otomatis lewat jadwal 17:30, atau tekan 'Perbarui ETF'."],
     "tombol": "etf_perbarui", "label_tombol": "Perbarui ETF"},
]
PERSIAPAN_CHROME = ("Sekali saja di Chrome yang dipakai: buka chrome://settings/downloads lalu matikan 'Tanyakan lokasi penyimpanan setiap file', "
                    "dan di chrome://settings/content/automaticDownloads tambahkan situs ini ke 'Diizinkan'. Setelah itu file langsung masuk folder Downloads tanpa ditanya.")
OTOMATIS = ("Cara cepat: tekan 'Buka Chrome Lab' di atas (sekali), lalu 'Ambil otomatis'. Script dijalankan sendiri di Chrome Lab dan hasilnya langsung diimpor; "
            "kalau Cloudflare menampilkan kotak centang di Chrome Lab, klik sekali. Langkah manual di bawah tetap bisa dipakai.")
for _s in SUMBER:
    if _s.get("cara") == "browser":
        _s["langkah"] = [OTOMATIS, PERSIAPAN_CHROME] + _s["langkah"]
        _s["otomatis"] = True
SKRIP = {s["skrip"] for s in SUMBER if s.get("skrip")}


def tgl(x):
    return x.strftime("%Y-%m-%d") if x is not None else None


def hari_bursa_harapan(sekarang):
    h = sekarang.date() if sekarang.hour >= 17 else sekarang.date() - timedelta(days=1)
    while h.weekday() >= 5:
        h -= timedelta(days=1)
    return h


def des_harapan(hari):
    calon = sorted(date(t, b, 1) for t in (hari.year - 1, hari.year, hari.year + 1) for b in (6, 12))
    return max(c for c in calon if c <= hari), min(c for c in calon if c > hari)


def ksei_harapan(hari):
    akhir = [(pd.Timestamp(hari).to_period("M") - k).end_time.date() for k in range(0, 5)]
    harap = next(a for a in akhir if a + timedelta(days=JEDA_KSEI) <= hari)
    berikut = (pd.Timestamp(harap) + pd.offsets.MonthEnd(1)).date()
    return harap, berikut + timedelta(days=JEDA_KSEI)


def periode_laporan(hari):
    daftar = []
    for th in range(hari.year - 2, hari.year + 1):
        for p, (b, h, geser) in TENGGAT.items():
            daftar.append((th, p, date(th + geser, b, h) + timedelta(days=JEDA_LAPORAN)))
    daftar.sort(key=lambda x: x[2])
    harap = [x for x in daftar if x[2] <= hari][-1]
    berikut = next(x for x in daftar if x[2] > hari)
    return harap, berikut


def harga_terakhir():
    kode = [k for k in dt.daftar("harian") if not k.startswith("_")][:30]
    t = [x.index.max() for x in dt.baca_banyak("harian", kode, ["close"]).values() if x is not None and len(x)]
    return max(t).date() if t else None


def jumlah_periode(db, koleksi, th, p, syarat=None):
    return db[koleksi].count_documents({"tahun": th, "periode": p, **(syarat or {})})


def status():
    db = d.koneksi()
    sekarang = datetime.now()
    hari = sekarang.date()
    hasil = {}

    h = harga_terakhir()
    harap = hari_bursa_harapan(sekarang)
    telat = int(np.busday_count(h + timedelta(days=1), harap + timedelta(days=1))) if h else None
    hasil["harga"] = {"terakhir": tgl(h), "seharusnya": tgl(harap), "perlu": h is None or telat > 0,
                      "alasan": f"Tertinggal {telat} hari bursa (abaikan kalau hari itu libur bursa)" if h and telat > 0 else None,
                      "berikutnya": "hari bursa berikutnya setelah 17:00"}

    for id_, nama, kunci in (("harga_riset", "harga", ["BBRI", "TLKM", "ASII", "BBCA", "ANTM"]), ("pasar", "pasar", None)):
        if kunci:
            ada = [x.index.max() for x in dt.baca_banyak(nama, kunci, ["close"]).values() if x is not None and len(x)]
        else:
            ada = [dt.baca(nama)["ihsg"].dropna().index.max()] if dt.ada(nama) else []
        hr = max(ada).date() if ada else None
        telat_r = int(np.busday_count(hr + timedelta(days=1), harap + timedelta(days=1))) if hr else None
        hasil[id_] = {"terakhir": f"s/d {tgl(hr)}" if hr else None, "seharusnya": tgl(harap), "perlu": hr is None or telat_r > 0,
                      "alasan": "Belum pernah diambil" if hr is None else f"Tertinggal {telat_r} hari bursa (abaikan kalau hari itu libur bursa)" if telat_r > 0 else None,
                      "berikutnya": "hari bursa berikutnya 17:30"}

    des = db.des.find_one(sort=[("mulai", -1)])
    cek = db.penanda.find_one({"_id": "des_cek"})
    harap, berikut = des_harapan(hari)
    mulai = des["mulai"].date() if des else None
    terbit = berikut - timedelta(days=12)
    kurang = mulai is None or mulai < harap
    segera = not kurang and hari >= terbit and mulai < berikut
    hasil["des"] = {"terakhir": f"{des['kep']} · berlaku {tgl(mulai)}" if des else None, "dicek": cek["isi"] if cek else None,
                    "seharusnya": f"periode berlaku {tgl(harap)}", "perlu": kurang or segera,
                    "alasan": f"Belum ada DES yang berlaku {tgl(harap)}" if kurang else
                              f"DES periode {tgl(berikut)} biasanya terbit akhir bulan ini; tekan Cek DES baru" if segera else None,
                    "berikutnya": f"{tgl(berikut - timedelta(days=12))} (DES berlaku {tgl(berikut)})"}

    tk = dt.baca("ksei", kolom=["tgl"])["tgl"].max().date() if dt.ada("ksei") else None
    harap, berikut = ksei_harapan(hari)
    kurang = tk is None or (tk.year, tk.month) < (harap.year, harap.month)
    if tk:
        berikut = max(berikut, (pd.Timestamp(tk).to_period("M") + 1).end_time.date() + timedelta(days=JEDA_KSEI))
    hasil["ksei"] = {"terakhir": f"data akhir {tgl(tk)}" if tk else None, "seharusnya": f"data akhir {BULAN[harap.month]} {harap.year}",
                     "perlu": kurang, "alasan": f"Data {BULAN[harap.month]} {harap.year} seharusnya sudah terbit" if kurang else None,
                     "berikutnya": tgl(berikut)}

    (th, p, _), (th2, p2, tb) = periode_laporan(hari)
    n_lk = jumlah_periode(db, "lapkeu", th, p)
    lk = db.lapkeu.find_one(sort=[("tgl_publikasi", -1)])
    w_lk = dt.waktu_arsip("idx_lapkeu_mentah.json")
    nama_p = lambda t, q: f"{'Tahunan' if q == 'AUDIT' else q} {t}"
    hasil["lapkeu"] = {"terakhir": f"terbit terakhir {tgl(lk['tgl_publikasi'])}" if lk else None,
                       "diimpor": datetime.fromtimestamp(w_lk).isoformat(timespec="minutes") if w_lk else None,
                       "seharusnya": f"{nama_p(th, p)} sudah ada", "perlu": n_lk < MIN_EMITEN,
                       "alasan": f"{nama_p(th, p)} baru {n_lk} emiten, seharusnya sudah lengkap" if n_lk < MIN_EMITEN else None,
                       "berikutnya": f"{tgl(tb)} ({nama_p(th2, p2)})"}

    n_f = jumlah_periode(db, "fundamental", th, p, {"ada_angka": True})
    per = list(db.fundamental.aggregate([{"$match": {"ada_angka": True}}, {"$group": {"_id": {"t": "$tahun", "p": "$periode"}, "n": {"$sum": 1}}}]))
    per = sorted([x for x in per if x["n"] >= 100], key=lambda x: (x["_id"]["t"], URUT.get(x["_id"]["p"], 0)), reverse=True)
    w_f = max([dt.waktu_arsip(n) for n in dt.daftar_arsip(folder="fundamental")] or [0])
    hasil["fundamental"] = {"terakhir": f"lengkap s/d {nama_p(per[0]['_id']['t'], per[0]['_id']['p'])} ({per[0]['n']} emiten)" if per else None,
                            "diimpor": datetime.fromtimestamp(w_f).isoformat(timespec="minutes") if w_f else None,
                            "seharusnya": f"{nama_p(th, p)} sudah ada", "perlu": n_f < MIN_EMITEN,
                            "alasan": f"{nama_p(th, p)} baru {n_f} emiten, seharusnya sudah lengkap" if n_f < MIN_EMITEN else None,
                            "berikutnya": f"{tgl(tb)} ({nama_p(th2, p2)})"}

    pi = db.profil_idx.find_one(sort=[("diimpor", -1)])
    n_pi = db.profil_idx.count_documents({})
    hasil["profil"] = {"terakhir": f"{n_pi} emiten" if n_pi else None,
                       "diimpor": pi["diimpor"].isoformat(timespec="minutes") if pi else None,
                       "perlu": not pi or (sekarang - pi["diimpor"]).days > 100,
                       "alasan": "Belum pernah diimpor; header Emiten memakai Yahoo Finance" if not pi else
                                 "Sudah lebih dari 100 hari sejak impor terakhir" if (sekarang - pi["diimpor"]).days > 100 else None,
                       "berikutnya": (pi["diimpor"] + timedelta(days=100)).strftime("%Y-%m-%d") if pi else "sekarang"}
    ri = db.rd_info.find_one({"_id": "ringkas"})
    umur_rd = int(np.busday_count((ri["diperbarui"] + timedelta(days=1)).date(), hari_bursa_harapan(sekarang) + timedelta(days=1))) if ri else None
    hasil["reksadana"] = {"terakhir": f"{ri['produk']} produk · {ri['nav']} titik NAV · {ri['sukuk']} sukuk" if ri else None,
                          "diimpor": ri["diperbarui"].isoformat(timespec="minutes") if ri else None,
                          "perlu": ri is None or umur_rd > 0,
                          "alasan": "Belum pernah diambil" if ri is None else f"Tertinggal {umur_rd} hari bursa" if umur_rd > 0 else None,
                          "berikutnya": "hari bursa berikutnya 17:30"}
    oj = ((db.rd_info.find_one({"_id": "ringkas"}) or {}).get("ojk"))
    harap_ojk = (pd.Timestamp(hari) - pd.DateOffset(days=8)).to_period("M") - 1
    kurang_ojk = oj is None or pd.Period(oj["sampai"], "M") < harap_ojk
    hasil["ojk_nab"] = {"terakhir": f"{oj['dari']} s/d {oj['sampai']} · {oj['produk']} produk ({oj['syariah']} syariah)" if oj else None,
                        "diimpor": oj["diimpor"].isoformat(timespec="minutes") if oj else None, "perlu": kurang_ojk,
                        "alasan": "Belum pernah diimpor" if oj is None else f"Data {harap_ojk} seharusnya sudah terbit" if kurang_ojk else None,
                        "berikutnya": f"tanggal 8 bulan depan"}
    di = db.dividen_idx_info.find_one({"_id": "ringkas"})
    umur = (sekarang - di["diimpor"]).days if di else None
    cek = (di or {}).get("cek") or {}
    hasil["dividen_idx"] = {"terakhir": f"{di['kejadian']} kejadian · cocok Yahoo {cek.get('persen_yahoo_di_idx', '–')}%" if di else None,
                            "diimpor": di["diimpor"].isoformat(timespec="minutes") if di else None,
                            "perlu": di is None or umur > JEDA_DIVIDEN,
                            "alasan": "Belum pernah diimpor; tanggal bayar masih perkiraan" if di is None else
                                      f"Sudah {umur} hari sejak impor terakhir; jadwal dividen baru mungkin sudah diumumkan" if umur > JEDA_DIVIDEN else None,
                            "berikutnya": (di["diimpor"] + timedelta(days=JEDA_DIVIDEN)).strftime("%Y-%m-%d") if di else "sekarang"}
    lg = dt.db().logo_info
    n_idx = lg.count_documents({"sumber": "idx"})
    akhir = next(iter(lg.find({"sumber": "idx"}).sort("dicek", -1).limit(1)), None)
    umur_logo = (sekarang - akhir["dicek"]).days if akhir else None
    hasil["idx_logo"] = {"terakhir": f"{n_idx} logo resmi IDX · {lg.count_documents({'ada': True})} logo total" if akhir else None,
                         "diimpor": akhir["dicek"].isoformat(timespec="minutes") if akhir else None,
                         "perlu": akhir is None or umur_logo > 180,
                         "alasan": "Belum pernah diimpor; logo diambil dari situs perusahaan" if akhir is None else
                                   f"Sudah {umur_logo} hari sejak impor terakhir" if umur_logo > 180 else None,
                         "berikutnya": (akhir["dicek"] + timedelta(days=180)).strftime("%Y-%m-%d") if akhir else "sekarang"}
    pg = dt.db().pengumuman_info.find_one({"_id": "ringkas"})
    umur_pg = (sekarang - pg["diimpor"]).days if pg else None
    hasil["pengumuman"] = {"terakhir": f"{pg['total']:,} pengumuman · {pg['emiten']:,} emiten · {tgl(pg['dari'])} s/d {tgl(pg['sampai'])}".replace(",", ".") if pg else None,
                           "diimpor": pg["diimpor"].isoformat(timespec="minutes") if pg else None,
                           "perlu": pg is None or umur_pg > JEDA_PENGUMUMAN,
                           "alasan": "Belum pernah diimpor" if pg is None else
                                     f"Sudah {umur_pg} hari sejak impor terakhir" if umur_pg > JEDA_PENGUMUMAN else None,
                           "berikutnya": (pg["diimpor"] + timedelta(days=JEDA_PENGUMUMAN)).strftime("%Y-%m-%d") if pg else "sekarang"}
    mk = dt.db().makro_info.find_one({"_id": "ringkas"})
    umur_mk = (sekarang - mk["diperbarui"]).days if mk else None
    br, inf = (mk or {}).get("bi_rate"), (mk or {}).get("inflasi")
    hasil["makro"] = {"terakhir": f"BI-Rate {br['nilai']}% ({tgl(br['terakhir'])}) · inflasi {inf['nilai']}% ({inf['terakhir']:%b %Y})" if br and inf else None,
                      "diimpor": mk["diperbarui"].isoformat(timespec="minutes") if mk else None,
                      "perlu": mk is None or umur_mk > 3 or not br or not inf,
                      "alasan": "Belum pernah diambil" if mk is None else f"Sudah {umur_mk} hari sejak diperbarui" if umur_mk > 3 else
                                "Sebagian data gagal diambil" if not br or not inf else None,
                      "berikutnya": "hari bursa berikutnya 17:30"}
    ki = dt.db().kepemilikan_info.find_one({"_id": "ringkas"})
    umur_ki = (sekarang - ki["diimpor"]).days if ki else None
    hasil["kepemilikan_pdf"] = {"terakhir": f"{ki['laporan']:,} laporan · {ki['pemegang']:,} baris pemegang >=1% · laporan s/d {tgl(ki.get('sampai'))} · {ki['sisa']:,} PDF belum dibaca".replace(",", ".") if ki else None,
                                "diimpor": ki["diimpor"].isoformat(timespec="minutes") if ki else None,
                                "perlu": ki is None or umur_ki > JEDA_PENGUMUMAN or ki.get("sisa", 0) > 200,
                                "alasan": "Belum pernah diimpor" if ki is None else f"{ki['sisa']} PDF belum dibaca" if ki.get("sisa", 0) > 200 else
                                          f"Sudah {umur_ki} hari sejak impor terakhir" if umur_ki > JEDA_PENGUMUMAN else None,
                                "berikutnya": (ki["diimpor"] + timedelta(days=JEDA_PENGUMUMAN)).strftime("%Y-%m-%d") if ki else "sekarang"}
    th_ = idx_harian_terakhir()
    harap = hari_bursa_harapan(sekarang)
    telat = int(np.busday_count(th_ + timedelta(days=1), harap + timedelta(days=1))) if th_ else None
    hasil["idx_harian"] = {"terakhir": f"data s/d {tgl(th_)}" if th_ else None, "seharusnya": tgl(harap),
                           "perlu": th_ is None or telat > JEDA_IDX_HARIAN,
                           "alasan": "Belum ada data" if th_ is None else f"Tertinggal {telat} hari bursa" if telat > JEDA_IDX_HARIAN else None,
                           "berikutnya": tgl(th_ + timedelta(days=JEDA_IDX_HARIAN + 2)) if th_ else "sekarang"}
    te = dt.baca("etf/XIJI").index.max().date() if dt.ada("etf/XIJI") else None
    telat_e = int(np.busday_count(te + timedelta(days=1), harap + timedelta(days=1))) if te else None
    hasil["etf"] = {"terakhir": f"harga s/d {tgl(te)} · {db.etf_luar.estimated_document_count()} ETF luar negeri" if te else None,
                    "seharusnya": tgl(harap), "perlu": te is None or telat_e > 0,
                    "alasan": "Belum pernah diambil" if te is None else f"Tertinggal {telat_e} hari bursa" if telat_e > 0 else None,
                    "berikutnya": "hari bursa berikutnya 17:30"}
    return [{**s, **hasil.get(s["id"], {})} for s in SUMBER]


def idx_harian_terakhir():
    if not dt.ada("idx_harian"):
        return None
    return dt.baca("idx_harian", kolom=["tgl"], salin=False)["tgl"].max().date()


def jumlah_perlu():
    return sum(1 for s in status() if s.get("perlu"))


def skrip(nama):
    if nama not in SKRIP:
        return None
    isi = (ROOT / "browser" / nama).read_text(encoding="utf-8")
    if "__ojk" not in isi and "window.__logo" not in isi:
        judul = next((s["nama"] for s in SUMBER if s.get("skrip") == nama), nama)
        isi = (ROOT / "browser" / "_pantau.js").read_text(encoding="utf-8").replace("__JUDUL__", json.dumps(judul)) + "\n" + isi
    if "__DARI__" in isi and nama == "idx_pengumuman_browser.js":
        from backend.ingest import pengumuman_idx
        isi = isi.replace("__DARI__", json.dumps(pengumuman_idx.bulan_terakhir()))
    if "__DARI__" in isi and nama == "idx_harian_browser.js":
        akhir = idx_harian_terakhir()
        isi = isi.replace("__DARI__", json.dumps(tgl(akhir + timedelta(days=1)) if akhir else "2020-01-02"))
    if "__DAFTAR__" in isi:
        from backend.ingest import kepemilikan_idx
        isi = isi.replace("__DAFTAR__", json.dumps(kepemilikan_idx.daftar_unduh()))
    if "__KODE__" in isi:
        kode = sorted(d.koneksi().des.distinct("kode"))
        isi = isi.replace("__KODE__", json.dumps(kode))
    return isi
