import io
import re
from datetime import datetime

import pdfplumber
import pypdfium2 as pdfium

BULAN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6, "jul": 7, "agu": 8, "agt": 8, "aug": 8, "sep": 9, "okt": 10,
         "oct": 10, "nov": 11, "des": 12, "dec": 12, "januari": 1, "februari": 2, "maret": 3, "april": 4, "juni": 6, "juli": 7, "agustus": 8,
         "september": 9, "oktober": 10, "november": 11, "desember": 12}
KOLOM_LK = [("jenis", "Jenis"), ("repo", "Repurchase"), ("status", "Status"), ("pemilik", "Nama"), ("ebe", "yang"), ("batas", "Batas"),
            ("jumlah", "Jumlah"), ("klasifikasi", "Klasifikasi"), ("harga", "Harga"), ("tanggal", "Tanggal"), ("tujuan", "Tujuan")]
KELAS_KSEI = ["Financial Institutional", "State Owned Enterprises", "State Owned Company", "Sovereign Wealth Fund", "Private Equity", "Investment Manager",
              "Investment Bank", "Mutual Fund", "Pension Fund", "Securities Company", "Insurance", "Foundation", "Government", "Individual",
              "Corporate", "Bank", "Others", "Other"]


def angka(s):
    s = (s or "").strip().replace(" ", "")
    if not s or s == "-":
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def persen(s):
    return angka((s or "").replace("%", ""))


def tanggal(s):
    s = (s or "").replace("\n", " ").replace("- ", "-").strip()
    m = re.search(r"(\d{1,2})[- ]([A-Za-z]+)[- ](\d{4})", s)
    if not m or m.group(2).lower()[:3] not in BULAN and m.group(2).lower() not in BULAN:
        return None
    b = BULAN.get(m.group(2).lower()) or BULAN.get(m.group(2).lower()[:3])
    try:
        return datetime(int(m.group(3)), b, int(m.group(1)))
    except ValueError:
        return None


def ambil(teks, label):
    m = re.search(re.escape(label) + r"[ \t]*:[ \t]*([^\n]*)", teks)
    if not m:
        return None
    v = m.group(1).strip()
    return None if not v or re.search(r"\w : ", v) else v


def transaksi_lk(pdf):
    hasil = []
    for pg in pdf.pages[1:]:
        kata = pg.extract_words()
        teks = " ".join(w["text"] for w in kata)
        if "Transaction Type" in teks or "Ownership Status" in teks:
            break
        kepala = [w for w in kata if w["top"] < 95]
        if not kepala:
            continue
        mulai = {}
        for k, judul in KOLOM_LK:
            calon = [w for w in kepala if w["text"] == judul]
            if k == "jumlah":
                calon = [w for w in calon if 55 <= w["top"] <= 65]
            if calon:
                mulai[k] = min(w["x0"] for w in calon)
        if "jumlah" not in mulai:
            continue
        batas_bawah = min([w["top"] for w in kata if w["text"] in ("Keterangan", "Saya")] + [pg.height])
        isi = [w for w in kata if 92 < w["top"] < batas_bawah]
        urut = sorted(mulai.items(), key=lambda z: z[1])

        def kolom(w):
            k = urut[0][0]
            for nama, x in urut:
                if w["x0"] + 2 >= x:
                    k = nama
            return k

        pusat = [w["top"] + w["bottom"] for w in isi if kolom(w) == "jumlah" and angka(w["text"]) is not None]
        pusat = sorted({round(p / 2) for p in pusat})
        if not pusat:
            continue
        baris = [{k: [] for k, _ in KOLOM_LK} for _ in pusat]
        for w in sorted(isi, key=lambda w: (w["top"], w["x0"])):
            t = (w["top"] + w["bottom"]) / 2
            i = min(range(len(pusat)), key=lambda j: abs(pusat[j] - t))
            baris[i][kolom(w)].append(w["text"])
        for b in baris:
            g = {k: " ".join(v).strip() for k, v in b.items()}
            hasil.append({"jenis": g["jenis"] or None, "status": g["status"] or None, "pemilik_langsung": g["pemilik"] or None,
                          "jumlah": angka(g["jumlah"]), "harga": angka(g["harga"]), "tanggal": tanggal(g["tanggal"]),
                          "klasifikasi": g["klasifikasi"] or None, "tujuan": g["tujuan"] or None, "repo": g["repo"] or None})
    return hasil


def baca_lk(isi):
    with pdfplumber.open(io.BytesIO(isi)) as pdf:
        teks = "\n".join(pg.extract_text() or "" for pg in pdf.pages)
        perusahaan = ambil(teks, "Nama Perusahaan Tbk") or ""
        m = re.match(r"([A-Z0-9]{4})\s*-\s*(.*)", perusahaan)
        nomor = re.search(r"LK/(\d{2})(\d{2})(\d{4})/\d+/\d+", teks)
        dok = {
            "nomor": nomor.group(0) if nomor else None,
            "tgl_lapor": datetime(int(nomor.group(3)), int(nomor.group(2)), int(nomor.group(1))) if nomor else None,
            "nama": ambil(teks, "Nama (sesuai SID)"), "orang_dalam": (ambil(teks, "Anggota Direksi/Dewan Komisaris") or "").lower().startswith("ya"),
            "jabatan": ambil(teks, "Jabatan") or None, "kewarganegaraan": ambil(teks, "Kewarganegaraan"),
            "kode": m.group(1) if m else None, "emiten": m.group(2) if m else perusahaan or None,
            "saham_sebelum": angka((ambil(teks, "Jumlah Saham Sebelum Transaksi") or "").replace("Unit", "")),
            "saham_sesudah": angka((ambil(teks, "Jumlah Saham Setelah Transaksi") or "").replace("Unit", "")),
            "persen_sebelum": persen(ambil(teks, "Hak Suara Sebelum Transaksi")),
            "persen_sesudah": persen(ambil(teks, "Hak Suara Setelah Transaksi")),
            "transaksi": transaksi_lk(pdf),
        }
    pengendali = re.search(r"Keterangan Pengendali\s*:\s*(\w+)", teks)
    dok["pengendali"] = bool(pengendali and pengendali.group(1).lower().startswith("ya"))
    return dok


POLA_KSEI1 = re.compile(r"^(\d{2}-[A-Za-z]{3}-\d{4}) ([A-Z0-9]{4}) (.+?) ([\d.]+) ([\d.]+) ([\d.]+) ([\d,]+)$")
POLA_TENGAH = re.compile(r"^(.*?)(?: (" + "|".join(KELAS_KSEI) + r"))? ([LF])(?: (.*))?$")


def baca_ksei1(isi, nama_emiten=None):
    pdf = pdfium.PdfDocument(isi)
    hasil, gagal = [], []
    for i in range(len(pdf)):
        for baris in pdf[i].get_textpage().get_text_range().splitlines():
            baris = baris.strip()
            if not re.match(r"\d{2}-[A-Za-z]{3}-\d{4} ", baris):
                continue
            m = POLA_KSEI1.match(baris)
            if not m:
                gagal.append(baris)
                continue
            tgl, kode, tengah, scripless, scrip, total, pct = m.groups()
            kelas = la = asal = None
            t2 = POLA_TENGAH.match(tengah)
            if t2:
                tengah, kelas, la, asal = t2.groups()
            emiten = (nama_emiten or {}).get(kode)
            if emiten and tengah.upper().startswith(emiten.upper()):
                investor = tengah[len(emiten):].strip()
            else:
                k = re.search(r"\bTbk\.?(?:,? PT\.?)?\s", tengah)
                investor = tengah[k.end():].strip() if k else tengah
                emiten = tengah[:k.end()].strip() if k else None
            hasil.append({"tgl": tanggal(tgl), "kode": kode, "investor": investor, "klasifikasi": kelas, "lokal_asing": la,
                          "asal": (asal or "").strip() or None, "saham": angka(total), "persen": angka(pct)})
    return hasil, gagal


KOLEKSI_LK = "kepemilikan_lapor"
KOLEKSI_BESAR = "kepemilikan_besar"
INFO = "kepemilikan_info"


def daftar_unduh():
    from backend.db import data as dt
    c = dt.db().pengumuman
    hasil = []
    q = {"$or": [{"kategori": "kepemilikan", "lampiran.url": {"$regex": "From_KSEI/LK-"}}, {"kategori": "ksei_1"},
                 {"judul": {"$regex": "^(Pengumuman )?(Revisi )?Evaluasi (Insidental )?Indeks", "$options": "i"}}]}
    for x in c.find(q, {"kategori": 1, "lampiran": 1, "pdf": 1, "judul": 1}).sort("tgl", -1):
        sudah = x.get("pdf") or {}
        for a in x["lampiran"]:
            kunci = a["url"].rsplit("/", 1)[-1].replace(".", "_")
            if sudah.get(kunci) in ("terbaca", "kosong"):
                continue
            if a["url"].lower().endswith(".zip") and "valuasi" in (x.get("judul") or "").lower():
                hasil.append([x["_id"], a["url"], "indeks"])
            elif x["kategori"] == "ksei_1" and not a.get("utama"):
                hasil.append([x["_id"], a["url"], "ksei1"])
            elif x["kategori"] == "kepemilikan" and "From_KSEI/LK-" in a["url"]:
                hasil.append([x["_id"], a["url"], "lk"])
    return hasil


def impor():
    import base64
    import hashlib
    import json as js

    from pymongo import UpdateOne

    from backend.db import data as dt
    from backend.ingest.impor_browser import cari
    db = dt.db()
    berkas = [f for f in cari("idx_kepemilikan_*.json") + cari("idx_indeks_*.json") if dt.waktu_arsip(f"kepemilikan/{f.name}") < f.stat().st_mtime]
    if not berkas:
        print("Tidak ada file idx_kepemilikan_*.json baru di Downloads.")
        return
    peng = {x["_id"]: x for x in db.pengumuman.find({"_id": {"$in": list({i["id"] for f in berkas for i in js.loads(f.read_text(encoding="utf-8"))["item"]})}},
                                                   {"tgl": 1, "kode": 1})}
    n_lk = n_besar = n_kosong = n_gagal = n_indeks = 0
    for f in berkas:
        item = js.loads(f.read_text(encoding="utf-8"))["item"]
        ops_lk, ops_besar, tanda = [], [], []
        for x in item:
            kunci = x["url"].rsplit("/", 1)[-1].replace(".", "_")
            if x.get("gagal"):
                n_gagal += 1
                tanda.append((x["id"], kunci, "gagal_unduh"))
                continue
            isi = base64.b64decode(x["b64"])
            p = peng.get(x["id"], {})
            try:
                if x["jenis"] == "indeks":
                    from backend.ingest import indeks_idx
                    n, daftar = indeks_idx.simpan(db, x["id"], isi)
                    n_indeks += n
                    tanda.append((x["id"], kunci, "terbaca" if n else "kosong"))
                elif x["jenis"] == "ksei1":
                    baris, _ = baca_ksei1(isi)
                    for b in baris:
                        kid = hashlib.md5(f"{b['tgl']:%Y%m%d}|{b['kode']}|{b['investor']}|{b['saham']}".encode()).hexdigest()
                        ops_besar.append(UpdateOne({"_id": kid}, {"$set": {**b, "sumber": x["id"]}}, upsert=True))
                    n_besar += len(baris)
                    tanda.append((x["id"], kunci, "terbaca" if baris else "kosong"))
                else:
                    d = baca_lk(isi)
                    if not d.get("kode") and not d.get("nama"):
                        n_kosong += 1
                        tanda.append((x["id"], kunci, "kosong"))
                        continue
                    d.update({"_id": f"{x['id']}#{kunci}", "pengumuman": x["id"], "url": x["url"], "tgl": p.get("tgl"),
                              "kode": d.get("kode") or p.get("kode")})
                    ops_lk.append(UpdateOne({"_id": d["_id"]}, {"$set": d}, upsert=True))
                    n_lk += 1
                    tanda.append((x["id"], kunci, "terbaca"))
            except Exception as e:
                n_gagal += 1
                tanda.append((x["id"], kunci, "gagal_baca"))
                print(f"  gagal membaca {x['url'][-40:]}: {e}")
        if ops_lk:
            db[KOLEKSI_LK].bulk_write(ops_lk, ordered=False)
        for i in range(0, len(ops_besar), 5000):
            db[KOLEKSI_BESAR].bulk_write(ops_besar[i:i + 5000], ordered=False)
        if tanda:
            db.pengumuman.bulk_write([UpdateOne({"_id": i}, {"$set": {f"pdf.{k}": s}}) for i, k, s in tanda], ordered=False)
        dt.simpan_arsip(f"kepemilikan/{f.name}", js.dumps({"dibuat": None, "jumlah": len(item)}), "kepemilikan")
        print(f"{f.name}: {len(item)} PDF diproses")
    db[KOLEKSI_LK].create_index([("kode", 1), ("tgl_lapor", -1)])
    db[KOLEKSI_BESAR].create_index([("kode", 1), ("tgl", -1)])
    db.indeks_anggota.create_index([("kode", 1), ("mulai", -1)])
    db.indeks_anggota.create_index([("indeks", 1), ("mulai", -1)])
    ringkas = {"_id": "ringkas", "diimpor": datetime.now(), "laporan": db[KOLEKSI_LK].estimated_document_count(),
               "pemegang": db[KOLEKSI_BESAR].estimated_document_count(), "sisa": len(daftar_unduh())}
    akhir = db[KOLEKSI_LK].find_one(sort=[("tgl_lapor", -1)])
    ringkas["sampai"] = akhir.get("tgl_lapor") if akhir else None
    db[INFO].replace_one({"_id": "ringkas"}, ringkas, upsert=True)
    print(f"\nLaporan perubahan kepemilikan terbaca: {n_lk} baru (total {ringkas['laporan']}), baris KSEI >=1%: {n_besar}, "
          f"baris anggota indeks: {n_indeks}, format tidak terbaca: {n_kosong}, gagal: {n_gagal}. Sisa file belum diunduh: {ringkas['sisa']}.")
    print("File PDF tidak disimpan; hanya angka hasil bacaan yang masuk database.")


if __name__ == "__main__":
    import sys
    {"impor": impor}[sys.argv[1] if len(sys.argv) > 1 else "impor"]()
