import io
import re
import zipfile

import pandas as pd

BULAN = {"januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "agustus": 8, "september": 9, "oktober": 10,
         "november": 11, "desember": 12}
KOLEKSI = "indeks_anggota"
KELUAR = "indeks_keluar"


def tanggal(s):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s or "")
    if not m or m.group(2).lower() not in BULAN:
        return None
    return pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1))).to_pydatetime()


def angka(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def baca_excel(isi):
    df = pd.read_excel(io.BytesIO(isi), header=None, dtype=object)
    baris = [[x for x in r.tolist() if pd.notna(x)] for _, r in df.iterrows()]
    info = {}
    for b in baris:
        if len(b) >= 2 and isinstance(b[0], str):
            kunci = b[0].strip().lower()
            nilai = str(b[1]).lstrip(": ").strip()
            if kunci.startswith("nama indeks"):
                info["indeks"] = nilai.upper()
            elif kunci.startswith("evaluasi"):
                info["evaluasi"] = nilai
            elif kunci.startswith("periode efektif konsituen") or kunci.startswith("periode efektif konstituen"):
                bagian = re.split(r"\s+s\.?\s*d\.?\s+", nilai)
                info["akhir"] = tanggal(bagian[1]) if len(bagian) > 1 else None
                info["mulai"] = tanggal(bagian[0])
                m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s*$", bagian[0].strip())
                if info["mulai"] is None and m and info["akhir"] and m.group(2).lower() in BULAN:
                    b = BULAN[m.group(2).lower()]
                    th = info["akhir"].year - (1 if b > info["akhir"].month else 0)
                    info["mulai"] = pd.Timestamp(th, b, int(m.group(1))).to_pydatetime()
    anggota, keluar, mode = [], [], "anggota"
    for b in baris:
        teks = " ".join(str(x) for x in b).lower()
        if "keluar" in teks and "konstituen" in teks:
            mode = "keluar"
            continue
        if len(b) >= 2 and re.fullmatch(r"\d+", str(b[0]).strip()) and re.fullmatch(r"[A-Z0-9]{4}", str(b[1]).strip()):
            kode = str(b[1]).strip()
            if mode == "anggota":
                status = next((str(x) for x in b[2:] if str(x).strip() in ("Baru", "Tetap", "Naik", "Turun")), None)
                bobot = [angka(x) for x in b[2:] if angka(x) is not None and 0 <= angka(x) <= 1]
                anggota.append({"kode": kode, "baru": any(str(x).strip() == "Baru" for x in b[2:]), "status": status,
                                "bobot": bobot[-1] if bobot else None})
            else:
                keluar.append({"kode": kode, "nama": str(b[2]).strip() if len(b) > 2 else None})
    return info, anggota, keluar


def baca_zip(isi):
    hasil = []
    with zipfile.ZipFile(io.BytesIO(isi)) as z:
        for n in z.namelist():
            if not n.lower().endswith(".xlsx"):
                continue
            try:
                info, anggota, keluar = baca_excel(z.read(n))
            except Exception as e:
                print(f"  gagal membaca {n}: {e}")
                continue
            if info.get("indeks") and info.get("mulai") and anggota:
                hasil.append((info, anggota, keluar, n))
    return hasil


def simpan(db, pengumuman, isi):
    from pymongo import UpdateOne
    ops, ops_k, indeks = [], [], set()
    for info, anggota, keluar, nama in baca_zip(isi):
        indeks.add(info["indeks"])
        dasar = {"indeks": info["indeks"], "mulai": info["mulai"], "akhir": info.get("akhir"), "evaluasi": info.get("evaluasi"),
                 "pengumuman": pengumuman, "jumlah": len(anggota)}
        for a in anggota:
            ops.append(UpdateOne({"_id": f"{info['indeks']}_{info['mulai']:%Y%m%d}_{a['kode']}"}, {"$set": {**dasar, **a}}, upsert=True))
        for k in keluar:
            ops_k.append(UpdateOne({"_id": f"{info['indeks']}_{info['mulai']:%Y%m%d}_{k['kode']}"}, {"$set": {**dasar, **k}}, upsert=True))
    if ops:
        db[KOLEKSI].bulk_write(ops, ordered=False)
    if ops_k:
        db[KELUAR].bulk_write(ops_k, ordered=False)
    return len(ops), sorted(indeks)
