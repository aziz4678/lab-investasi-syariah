import json
import re
import runpy
import shutil
import sys
from datetime import datetime
from pathlib import Path

from backend.db import data as dt
from backend.db import koneksi as d

ROOT = Path(__file__).resolve().parents[2]
TEMPAT = [Path.home() / "Downloads", ROOT]
ARSIP_LAPKEU = "idx_lapkeu_mentah.json"


def cari(pola):
    hasil = []
    for t in TEMPAT:
        if t.exists():
            hasil += [f for f in t.glob(pola) if f.is_file()]
    return sorted(set(hasil), key=lambda f: f.stat().st_mtime, reverse=True)


def jalankan_modul(modul, argumen=()):
    lama = sys.argv
    sys.argv = [modul, *argumen]
    try:
        runpy.run_module(modul, run_name="__main__")
    finally:
        sys.argv = lama


def fundamental():
    disalin, sebagian = [], []
    terbaru = {}
    for f in cari("idx_fundamental_*.json"):
        if "_sebagian" in f.stem:
            sebagian.append(f.name)
            continue
        terbaru.setdefault(re.sub(r" \(\d+\)(?=\.json$)", "", f.name), f)
    for nama, f in terbaru.items():
        if dt.waktu_arsip(nama) >= f.stat().st_mtime:
            continue
        try:
            isi = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"LEWATI {f.name}: bukan JSON yang utuh")
            continue
        if not isinstance(isi, list) or not isi:
            print(f"LEWATI {f.name}: isi kosong / format tidak dikenal")
            continue
        dt.simpan_arsip(nama, f.read_bytes(), "fundamental")
        disalin.append(f"{nama} ({len(isi)} laporan, dari {f.parent})")
    print("File baru disimpan ke arsip MongoDB:" if disalin else "Tidak ada file fundamental baru di Downloads / folder proyek.")
    for x in disalin:
        print("  " + x)
    if sebagian:
        print(f"PERINGATAN: file *_sebagian.json tidak diimpor (unduhan terputus): {', '.join(sorted(set(sebagian)))}. Jalankan ulang script browser untuk tahun itu.")
    print("\nMembangun ulang koleksi fundamental...")
    jalankan_modul("backend.riset.fundamental")


def lapkeu():
    calon = [f for f in cari("idx_lapkeu*.json") if f.name != ARSIP_LAPKEU]
    if not calon:
        print("Tidak ada file idx_lapkeu*.json di Downloads / folder proyek. Jalankan dulu script browser idx_lapkeu_browser.js.")
        return
    f = calon[0]
    if dt.waktu_arsip(ARSIP_LAPKEU) >= f.stat().st_mtime:
        print(f"{f.name} tidak lebih baru dari data yang sudah diimpor. Tidak ada yang diubah.")
        return
    isi = json.loads(f.read_text(encoding="utf-8"))
    baris = len(isi.get("data", [])) if isinstance(isi, dict) else 0
    sekarang = d.koneksi().lapkeu.count_documents({})
    if not baris or "kolom" not in isi:
        raise SystemExit(f"{f.name}: format tidak dikenal")
    if baris < 0.9 * sekarang:
        raise SystemExit(f"{f.name} hanya {baris} baris, data sekarang {sekarang}. Kemungkinan unduhan terputus; tidak diimpor.")
    dt.simpan_arsip(ARSIP_LAPKEU, f.read_bytes(), "mentah")
    print(f"Disimpan {f} ({baris} baris) ke arsip MongoDB ({ARSIP_LAPKEU})")
    jalankan_modul("backend.riset.idx_lapkeu")
    print("\nTanggal publikasi berubah, membangun ulang koleksi fundamental...")
    jalankan_modul("backend.riset.fundamental")


def kunci(x, *nama):
    if not isinstance(x, dict):
        return None
    kecil = {k.lower(): v for k, v in x.items()}
    for n in nama:
        v = kecil.get(n.lower())
        if v not in (None, "", "-"):
            return v.strip() if isinstance(v, str) else v
    return None


def persen(v):
    try:
        return round(float(str(v).replace(",", ".").replace("%", "")), 4)
    except (TypeError, ValueError):
        return None


def orang(daftar):
    hasil = []
    for x in daftar or []:
        nama = kunci(x, "Nama", "Name")
        if nama:
            hasil.append({"nama": nama, "jabatan": kunci(x, "Jabatan", "Position", "Title")})
    return hasil


def profil():
    calon = cari("idx_profil*.json")
    if not calon:
        print("Tidak ada file idx_profil*.json di Downloads / folder proyek. Jalankan dulu script profil IDX di Console.")
        return
    f = calon[0]
    data = json.loads(f.read_text(encoding="utf-8"))
    db = d.koneksi()
    sekarang = datetime.now()
    ok, gagal = 0, []
    for r in data:
        p = r.get("profil")
        if not p:
            gagal.append(r.get("kode"))
            continue
        pemegang = []
        for x in r.get("pemegang") or []:
            nama = kunci(x, "Nama", "Name")
            if nama:
                pemegang.append({"nama": nama, "persen": persen(kunci(x, "Persentase", "Percentage")), "jumlah": kunci(x, "Jumlah", "Amount"),
                                 "kategori": kunci(x, "Kategori", "Category")})
        pemegang.sort(key=lambda x: -(x["persen"] or 0))
        tgl = kunci(p, "TanggalPencatatan", "ListingDate")
        dok = {
            "kode": str(r["kode"]).upper(), "diimpor": sekarang, "nama": kunci(p, "NamaEmiten", "Nama"),
            "kegiatan": kunci(p, "KegiatanUsahaUtama", "KegiatanUsaha", "BusinessActivity"),
            "sektor": kunci(p, "Sektor"), "subsektor": kunci(p, "SubSektor"), "industri": kunci(p, "Industri"), "subindustri": kunci(p, "SubIndustri"),
            "tanggal_pencatatan": str(tgl)[:10] if tgl else None, "papan": kunci(p, "PapanPencatatan", "Papan"),
            "alamat": kunci(p, "Alamat", "Address"), "website": kunci(p, "Website"), "telepon": kunci(p, "Telepon", "Phone"),
            "pemegang": pemegang, "direksi": orang(r.get("direktur")), "komisaris": orang(r.get("komisaris")),
        }
        db.profil_idx.replace_one({"kode": dok["kode"]}, dok, upsert=True)
        ok += 1
    print(f"{f.name}: {ok} profil diimpor ke koleksi profil_idx, {len(gagal)} tanpa profil")
    if gagal:
        print("tanpa profil (mungkin sudah delisting / ganti kode): " + ", ".join(str(x) for x in gagal[:40]) + (" ..." if len(gagal) > 40 else ""))
    contoh = db.profil_idx.find_one({"pemegang.0": {"$exists": True}}, {"_id": 0, "kode": 1, "nama": 1, "pemegang": {"$slice": 2}})
    if contoh:
        print("contoh:", contoh)


def dividen():
    from backend.riset import dividen_idx
    calon = [f for f in cari("idx_dividen*.json") if "_sebagian" not in f.stem and f.name != dividen_idx.FILE]
    sebagian = [f.name for f in cari("idx_dividen_sebagian*.json")]
    if not calon:
        print("Tidak ada file idx_dividen.json di Downloads / folder proyek. Jalankan dulu script dividen IDX di Console.")
        if sebagian:
            print(f"Ada {', '.join(sebagian)} (unduhan terputus, tidak diimpor). Jalankan ulang script-nya.")
        return
    f = calon[0]
    if dt.waktu_arsip(dividen_idx.FILE) >= f.stat().st_mtime:
        print(f"{f.name} tidak lebih baru dari data yang sudah diimpor, impor ulang dari arsip.")
    else:
        dt.simpan_arsip(dividen_idx.FILE, f.read_bytes(), "mentah")
        print(f"Disimpan {f} ke arsip MongoDB ({dividen_idx.FILE})")
    dividen_idx.impor(dividen_idx.FILE)


def logo():
    import base64
    calon = cari("idx_logo*.json")
    if not calon:
        print("Tidak ada file idx_logo.json di Downloads / folder proyek. Jalankan dulu script logo IDX di Console.")
        return
    f = calon[0]
    isi = json.loads(f.read_text(encoding="utf-8")).get("logo") or {}
    db = d.koneksi()
    dt_db = dt.db()
    n = 0
    for kode, x in isi.items():
        try:
            b = base64.b64decode(x["isi"])
        except Exception:
            continue
        if len(b) < 300:
            continue
        dt.simpan_arsip(f"logo/emiten/{kode.upper()}", b, "logo")
        dt_db.logo_info.replace_one({"_id": f"emiten/{kode.upper()}"}, {"_id": f"emiten/{kode.upper()}", "domain": "idx.co.id", "ada": True,
                                                                         "jenis": x.get("jenis"), "sumber": "idx", "dicek": datetime.now()}, upsert=True)
        n += 1
    print(f"{f.name}: {n} logo emiten resmi IDX disimpan (menggantikan logo dari situs perusahaan)")
    print(f"Total logo tersimpan: {dt_db.logo_info.count_documents({'ada': True})}")


def idx_harian():
    import pandas as pd
    berkas = [f for f in cari("idx_harian_baru_*.json")]
    baru = [f for f in berkas if dt.waktu_arsip(f"idx_harian/{f.name}") < f.stat().st_mtime]
    if not berkas:
        print("Tidak ada file idx_harian_baru_*.json di Downloads / folder proyek. Jalankan dulu script ringkasan perdagangan IDX di Console.")
        return
    if not baru:
        print("Semua file idx_harian_baru_*.json sudah pernah diimpor. Jalankan script lagi untuk hari bursa baru.")
        return
    potongan = []
    for f in baru:
        for hari in json.loads(f.read_text(encoding="utf-8")):
            if hari.get("data"):
                df = pd.DataFrame(hari["data"], columns=hari["kolom"])
                df.insert(0, "tgl", hari["tgl"])
                potongan.append(df)
        print(f"{f.name} dibaca")
    if not potongan:
        print("File berisi 0 hari bursa, tidak ada yang diimpor.")
        return
    tambah = pd.concat(potongan, ignore_index=True)
    tambah["tgl"] = pd.to_datetime(tambah["tgl"])
    tambah["StockCode"] = tambah["StockCode"].astype(str).str.strip().str.upper()
    for kol in tambah.columns.drop(["tgl", "StockCode", "Remarks"]):
        tambah[kol] = pd.to_numeric(tambah[kol], errors="coerce")
    lama = dt.baca("idx_harian")
    n_lama = 0 if lama is None else len(lama)
    semua = tambah if lama is None else pd.concat([lama, tambah[lama.columns]], ignore_index=True)
    semua = semua.drop_duplicates(["tgl", "StockCode"], keep="last").sort_values(["tgl", "StockCode"]).reset_index(drop=True)
    dt.tulis("idx_harian", semua)
    for f in baru:
        dt.simpan_arsip(f"idx_harian/{f.name}", f.read_bytes(), "idx_harian")
    print(f"Ditambahkan {tambah['tgl'].nunique()} hari bursa ({tambah['tgl'].min():%Y-%m-%d} s/d {tambah['tgl'].max():%Y-%m-%d}). "
          f"Total {len(semua)} baris (sebelumnya {n_lama}), {semua['tgl'].nunique()} hari, {semua['StockCode'].nunique()} kode, "
          f"{semua['tgl'].min():%Y-%m-%d} s/d {semua['tgl'].max():%Y-%m-%d}.")


def pengumuman():
    from backend.riset import pengumuman_idx
    pengumuman_idx.impor()


if __name__ == "__main__":
    {"fundamental": fundamental, "lapkeu": lapkeu, "profil": profil, "dividen": dividen, "logo": logo,
     "idx_harian": idx_harian, "pengumuman": pengumuman}[sys.argv[1]]()
