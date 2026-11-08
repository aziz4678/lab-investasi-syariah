import ctypes
import os
import subprocess
import sys
import uuid
from datetime import datetime

from backend.core.config import ROOT
from backend.db import koneksi as d

PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
PERINTAH = {
    "paper_harian": ("Perbarui paper trade", ["-m", "backend.paper.tren_harian"]),
    "paper_unduh": ("Unduh harga harian paper (Yahoo, dikoreksi)", ["-m", "backend.paper.unduh_paper"]),
    "kualitas_data": ("Cek kualitas data harga + aksi korporasi otomatis", ["-m", "backend.ingest.cek_kualitas"]),
    "koreksi_ekspor": ("Ekspor registry koreksi harga ke data/koreksi_harga.jsonl", ["-m", "backend.ingest.koreksi_harga", "ekspor"]),
    "koreksi_impor": ("Pulihkan registry koreksi harga dari data/koreksi_harga.jsonl", ["-m", "backend.ingest.koreksi_harga", "impor"]),
    "impor_ojk_nab": ("Impor NAB bulanan OJK", ["-m", "backend.ingest.ojk_nab"]),
    "impor_logo": ("Impor logo emiten IDX", ["-m", "backend.ingest.impor_browser", "logo"]),
    "logo_perbarui": ("Perbarui logo emiten & produk", ["-m", "backend.ingest.logo"]),
    "etf_perbarui": ("Perbarui ETF syariah (harga bursa)", ["-m", "backend.ingest.etf"]),
    "harga_perbarui": ("Perbarui harga saham riset (sejak 2010)", ["-m", "backend.ingest.kumpul_data", "harga"]),
    "pasar_perbarui": ("Perbarui data pasar (IHSG, kurs, komoditas, indeks dunia)", ["-m", "backend.ingest.kumpul_data", "pasar"]),
    "harga_unduh_ulang": ("Unduh ulang penuh harga saham riset & data pasar", ["-m", "backend.ingest.kumpul_data", "penuh"]),
    "makro_perbarui": ("Perbarui data makro (BI-Rate, inflasi)", ["-m", "backend.ingest.makro", "perbarui"]),
    "rd_perbarui": ("Perbarui reksa dana & sukuk", ["-m", "backend.ingest.reksadana"]),
    "rd_platform_perbarui": ("Perbarui platform tempat beli reksa dana", ["-m", "backend.ingest.rd_platform"]),
    "rd_cek_platform": ("Cek silang angka reksa dana dengan aplikasi", ["-m", "backend.app.services.cek_platform"]),
    "isi_backtest": ("Hitung ulang hasil backtest", ["-m", "backend.db.isi_backtest"]),
    "isi_backtest_h29": ("Hitung ulang simulasi Momentum Blend", ["-m", "backend.research.simulasi_h29"]),
    "eksplorasi_2020": ("Eksplorasi ulang 2020+ (bukan bukti)", ["-m", "backend.research.eksplorasi_2020"]),
    "impor_fundamental": ("Impor laporan keuangan", ["-m", "backend.ingest.impor_browser", "fundamental"]),
    "impor_lapkeu": ("Impor tanggal laporan keuangan", ["-m", "backend.ingest.impor_browser", "lapkeu"]),
    "ksei_perbarui": ("Perbarui kepemilikan KSEI", ["-m", "backend.ingest.ksei", "unduh"]),
    "impor_profil": ("Impor profil emiten IDX", ["-m", "backend.ingest.impor_browser", "profil"]),
    "impor_dividen": ("Impor jadwal dividen IDX", ["-m", "backend.ingest.impor_browser", "dividen"]),
    "des_perbarui": ("Cek DES baru di OJK", ["-m", "backend.ingest.des_ojk", "perbarui"]),
    "impor_pengumuman": ("Impor pengumuman & aksi korporasi IDX", ["-m", "backend.ingest.impor_browser", "pengumuman"]),
    "impor_idx_harian": ("Impor ringkasan perdagangan IDX", ["-m", "backend.ingest.impor_browser", "idx_harian"]),
    "impor_keuangan_idx": ("Impor data keuangan & rasio emiten IDX", ["-m", "backend.ingest.keuangan_idx", "gabung"]),
    "impor_kepemilikan": ("Impor transaksi orang dalam & pemegang besar", ["-m", "backend.ingest.kepemilikan_idx", "impor"]),
    "otomatis": ("Ambil otomatis lewat Chrome Lab", ["-m", "backend.ingest.otomatis"]),
    "paper_cek": ("Cek ulang paper trade", ["-m", "backend.paper.cek_ulang"]),
    "paper_h22": ("Perbarui paper H29 (bagian H22)", ["-m", "backend.paper.h22_harian"]),
    "paper_h22_cek": ("Cek ulang paper H29 (bagian H22)", ["-m", "backend.paper.cek_h22"]),
    "pantau_paper": ("Pantau paper: jejak posisi, banding backtest, catatan evaluasi", ["-m", "backend.paper.pantau", "harian"]),
    "pantau_ambang": ("Hitung usulan ambang pantau paper (U2 & zona H29)", ["-m", "backend.research.ambang_pantau"]),
    "audit_aturan_paper": ("Audit aturan evaluasi paper (alarm palsu & daya pembeda)", ["-m", "backend.research.audit_aturan_paper", "--u2"]),
    "kunci_aturan_v2": ("Kunci aturan evaluasi paper v2 (h11a_v2 & h29_v2)", ["-m", "backend.paper.aturan_v2", "kunci"]),
    "cadangan": ("Backup database", ["-m", "backend.db.cadangan", "buat"]),
    "cadangan_data": ("Backup data pasar (mingguan)", ["-m", "backend.db.cadangan", "data"]),
    "pulihkan": ("Pulihkan database dari backup", ["-m", "backend.db.cadangan", "pulihkan"]),
}
BATAS_LOG = 400
BENTROK = {
    "koreksi_impor": {"kualitas_data", "koreksi_ekspor", "harga_perbarui", "harga_unduh_ulang", "paper_unduh", "pulihkan"},
    "koreksi_ekspor": {"koreksi_impor", "pulihkan"},
    "paper_unduh": {"paper_harian", "paper_h22", "paper_cek", "paper_h22_cek", "cadangan_data", "pulihkan", "kualitas_data"},
    "kualitas_data": {"harga_perbarui", "harga_unduh_ulang", "paper_unduh", "paper_harian", "paper_h22", "isi_backtest", "isi_backtest_h29", "cadangan_data", "pulihkan"},
    "paper_harian": {"paper_cek", "paper_h22", "pulihkan", "des_perbarui", "paper_unduh", "kualitas_data"},
    "paper_cek": {"paper_harian", "pulihkan", "paper_unduh"},
    "paper_h22": {"paper_harian", "paper_h22_cek", "pulihkan", "des_perbarui", "cadangan_data", "paper_unduh", "kualitas_data"},
    "paper_h22_cek": {"paper_h22", "pulihkan", "paper_unduh"},
    "des_perbarui": {"paper_harian", "paper_h22", "pulihkan"},
    "cadangan": {"pulihkan"},
    "rd_cek_platform": {"rd_perbarui"},
    "cadangan_data": {"pulihkan", "paper_harian", "paper_h22", "rd_perbarui", "impor_pengumuman", "impor_idx_harian", "harga_perbarui", "pasar_perbarui", "harga_unduh_ulang", "paper_unduh", "kualitas_data"},
    "harga_perbarui": {"harga_unduh_ulang", "isi_backtest", "isi_backtest_h29", "cadangan_data", "pulihkan", "kualitas_data"},
    "pasar_perbarui": {"harga_unduh_ulang", "isi_backtest", "isi_backtest_h29", "cadangan_data", "pulihkan"},
    "harga_unduh_ulang": {"harga_perbarui", "pasar_perbarui", "isi_backtest", "isi_backtest_h29", "cadangan_data", "pulihkan"},
    "isi_backtest": {"harga_perbarui", "pasar_perbarui", "harga_unduh_ulang", "pulihkan", "isi_backtest_h29", "kualitas_data"},
    "isi_backtest_h29": {"harga_perbarui", "pasar_perbarui", "harga_unduh_ulang", "pulihkan", "isi_backtest", "kualitas_data"},
    "eksplorasi_2020": {"harga_perbarui", "pasar_perbarui", "harga_unduh_ulang", "impor_idx_harian", "cadangan_data", "pulihkan"},
    "impor_pengumuman": {"pulihkan", "cadangan_data"},
    "impor_idx_harian": {"pulihkan", "cadangan_data"},
    "impor_kepemilikan": {"pulihkan", "cadangan_data", "otomatis"},
    "otomatis": {"pulihkan", "cadangan_data", "impor_kepemilikan", "impor_pengumuman", "impor_idx_harian"},
    "impor_fundamental": {"impor_lapkeu", "pulihkan"},
    "impor_lapkeu": {"impor_fundamental", "pulihkan"},
    "pantau_paper": {"paper_harian", "paper_h22", "paper_unduh", "paper_cek", "paper_h22_cek", "kualitas_data", "harga_perbarui", "harga_unduh_ulang", "pasar_perbarui", "pulihkan", "pantau_ambang"},
    "pantau_ambang": {"harga_perbarui", "harga_unduh_ulang", "pasar_perbarui", "kualitas_data", "isi_backtest", "isi_backtest_h29", "pulihkan", "pantau_paper"},
    "audit_aturan_paper": {"harga_perbarui", "harga_unduh_ulang", "pasar_perbarui", "kualitas_data", "isi_backtest", "isi_backtest_h29", "pulihkan"},
    "kunci_aturan_v2": {"pantau_paper", "audit_aturan_paper", "pulihkan", "paper_harian", "paper_h22"},
    "pulihkan": set(PERINTAH),
}


class Bentrok(RuntimeError):
    pass


def hidup(pid):
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))
    if not h:
        return False
    kode = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(kode))
    k.CloseHandle(h)
    return bool(ok) and kode.value == 259


def bersihkan_yatim():
    db = d.koneksi()
    for p in db.pekerjaan.find({"status": "berjalan"}, {"pid": 1}):
        if not hidup(p.get("pid")):
            db.pekerjaan.update_one({"_id": p["_id"], "status": "berjalan"}, {"$set": {"status": "terputus", "selesai": datetime.now()}})


def mulai(jenis, argumen=None, tunggu=False, oleh="tombol"):
    if jenis not in PERINTAH:
        raise KeyError(jenis)
    db = d.koneksi()
    jalan = db.pekerjaan.find_one({"jenis": jenis, "status": "berjalan"})
    if jalan:
        return jalan["_id"], False
    lain = db.pekerjaan.find_one({"jenis": {"$in": sorted(BENTROK.get(jenis, set()) - {jenis})}, "status": "berjalan"})
    if lain:
        raise Bentrok(f"Tunggu \"{lain['label']}\" selesai dulu.")
    label, perintah = PERINTAH[jenis]
    if jenis == "otomatis" and argumen:
        from backend.app.services import sumber_data as sd
        nama = next((s["nama"] for s in sd.SUMBER if s["id"] == str(argumen[0])), str(argumen[0]))
        label = f"Ambil otomatis: {nama}"
    id_ = uuid.uuid4().hex[:12]
    argumen = [str(a) for a in (argumen or [])]
    db.pekerjaan.insert_one({"_id": id_, "jenis": jenis, "label": label, "argumen": argumen, "status": "berjalan", "oleh": oleh,
                             "mulai": datetime.now(), "selesai": None, "kode": None, "log": []})
    python = str(PYTHON) if PYTHON.exists() else sys.executable
    bendera = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proses = subprocess.Popen([python, "-m", "backend.app.jobs.pembungkus", id_, python, *perintah, *argumen], cwd=ROOT,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=bendera)
    db.pekerjaan.update_one({"_id": id_}, {"$set": {"pid": proses.pid}})
    if tunggu:
        proses.wait()
    return id_, True


def ambil(id_):
    return d.koneksi().pekerjaan.find_one({"_id": id_})


def terbaru(batas=10):
    return list(d.koneksi().pekerjaan.find({}, {"log": 0}).sort("mulai", -1).limit(batas))
