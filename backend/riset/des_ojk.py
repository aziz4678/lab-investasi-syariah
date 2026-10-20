import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import pandas as pd
from backend.db import data as dt
from backend.db import koneksi as d

SITUS = "https://ojk.go.id"
DAFTAR = SITUS + "/id/kanal/syariah/data-dan-statistik/daftar-efek-syariah/default.aspx"
MIN_SAHAM, MAKS_SAHAM = 400, 1200
PERIODE = [
    ("SK DES 2019", "KEP-76/D.04/2019", "2019-12-01"),
    ("PERIODE I - 2020", "KEP-44/D.04/2020", "2020-08-01"),
    ("PERIODE II - 2020", "KEP-63/D.04/2020", "2020-12-01"),
    ("PERIODE I - 2021", "KEP-33/D.04/2021", "2021-08-01"),
    ("PERIODE II TAHUN 2021", "KEP-62/D.04/2021", "2021-12-01"),
    ("PERIODE I - 2022", "KEP-38/D.04/2022", "2022-06-01"),
    ("P2 2022", "KEP-81/D.04/2022", "2022-12-01"),
    ("PERIODE I - 2023", "KEP-52/D.04/2023", "2023-06-01"),
    ("PERIODE II - 2023", "KEP-92/D.04/2023", "2023-12-01"),
    ("PERIODE I - 2024", "KEP-20/D.04/2024", "2024-06-01"),
    ("PERIODE II 2024", "KEP-51/D.04/2024", "2024-12-01"),
    ("PERIODE I 2025", "KEP-28/D.04/2025", "2025-06-01"),
    ("PERIODE II 2025", "KEP-59/D.04/2025", "2025-12-01"),
    ("PERIODE I 2026", "KEP-21/D.04/2026", "2026-06-01"),
]


def kode_dari_file(f):
    kode = set()
    sumber = dt.bytes_io(dt.baca_arsip(f)) if isinstance(f, str) else f
    for df in pd.read_excel(sumber, sheet_name=None, header=None, dtype=str).values():
        for v in df.to_numpy().ravel():
            if isinstance(v, str) and re.fullmatch(r"[A-Z]{4}", v.strip().upper()):
                kode.add(v.strip().upper())
    return kode


def cari_file(penanda):
    cocok = [n for n in dt.daftar_arsip(folder="des") if re.search(r"\.xlsx?$", n, re.I) and penanda.upper() in n.upper()]
    if len(cocok) != 1:
        raise RuntimeError(f"penanda '{penanda}' cocok dengan {len(cocok)} file: {cocok}")
    return cocok[0]


def semua_periode():
    tambahan = [(r["penanda"], r["kep"], r["mulai"]) for r in d.koneksi().des_periode.find({}, {"_id": 0})]
    return sorted(PERIODE + tambahan, key=lambda x: x[2])


def bangun():
    baris = []
    periode = semua_periode()
    for i, (penanda, kep, mulai) in enumerate(periode):
        akhir = pd.Timestamp(periode[i + 1][2]) - pd.Timedelta(days=1) if i + 1 < len(periode) else pd.Timestamp("2099-12-31")
        f = cari_file(penanda)
        for k in sorted(kode_dari_file(f)):
            baris.append({"kode": k, "mulai": pd.Timestamp(mulai), "akhir": akhir, "kep": kep})
    df = pd.DataFrame(baris)
    d.simpan_df("des", df)
    return df


def nomor_kep(teks):
    m = re.search(r"KEP[\s-]*(\d+)\W*D\W*0?4\W*(\d{4})", teks.upper())
    return (int(m.group(2)), int(m.group(1))) if m else None


def ambil(url):
    from curl_cffi import requests
    r = requests.get(url, impersonate="chrome", timeout=90)
    r.raise_for_status()
    return r


def mulai_dari_nama(nama, tahun):
    m = re.search(r"PERIODE\s*(II|I|2|1)\b\D*(\d{4})?", nama.upper()) or re.search(r"\bP(2|1)\b", nama.upper())
    if not m:
        return None
    ke = 2 if m.group(1) in ("II", "2") else 1
    th = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else tahun
    return f"{th}-{'12' if ke == 2 else '06'}-01"


def perbarui():
    dikenal = {nomor_kep(p[1]) for p in semua_periode()}
    terakhir = max(dikenal)
    print(f"DES terakhir di data: KEP-{terakhir[1]}/D.04/{terakhir[0]}")
    halaman = ambil(DAFTAR).text
    entri = {}
    for href, judul in re.findall(r'href="([^"]*daftar-efek-syariah/Pages/[^"]+\.aspx)"[^>]*>([^<]{0,200})', halaman, re.I):
        n = nomor_kep(judul) or nomor_kep(href)
        if n and n not in entri:
            entri[n] = (href, re.sub(r"[​\s]+", " ", judul).strip())
    baru = sorted(n for n in entri if n > terakhir and n not in dikenal)
    print(f"{len(entri)} KEP di halaman OJK, terbaru KEP-{max(entri)[1]}/D.04/{max(entri)[0]}")
    if not baru:
        print("Tidak ada DES baru. Data sudah terbaru.")
        d.koneksi().penanda.update_one({"_id": "des_cek"}, {"$set": {"isi": datetime.now().isoformat(timespec="seconds")}}, upsert=True)
        return 0
    ditambah = 0
    for n in baru:
        href, judul = entri[n]
        kep = f"KEP-{n[1]}/D.04/{n[0]}"
        print(f"\nDES baru: {judul}")
        isi = ambil(SITUS + href if href.startswith("/") else href).text
        lampiran = sorted({unquote(x) for x in re.findall(r'href="([^"]+\.xlsx?)"', isi, re.I)})
        if not lampiran:
            print(f"  {kep}: tidak ada lampiran XLSX, lewati (cek manual di {SITUS + href})")
            continue
        calon = []
        for u in lampiran:
            nama = u.rsplit("/", 1)[-1]
            data = ambil(SITUS + quote(u) if u.startswith("/") else u).content
            dt.simpan_arsip(nama, data, "des")
            kode = kode_dari_file(nama)
            print(f"  {nama}: {len(kode)} kode")
            calon.append((len(kode), nama))
        jumlah, nama = max(calon)
        mulai = mulai_dari_nama(nama, n[0]) or mulai_dari_nama(judul, n[0])
        if not (MIN_SAHAM <= jumlah <= MAKS_SAHAM) or not mulai:
            print(f"  {kep}: {jumlah} kode / tanggal berlaku {mulai} tidak wajar, tidak dipakai. Cek manual.")
            continue
        d.koneksi().des_periode.update_one({"kep": kep}, {"$set": {"penanda": nama, "kep": kep, "mulai": mulai}}, upsert=True)
        print(f"  dipakai: {nama} ({jumlah} saham), berlaku {mulai}")
        ditambah += 1
    if ditambah:
        des = bangun()
        akhir = des["mulai"].max()
        print(f"\nKoleksi des dibangun ulang: periode terbaru berlaku {akhir.date()}, {int((des['mulai'] == akhir).sum())} saham")
    d.koneksi().penanda.update_one({"_id": "des_cek"}, {"$set": {"isi": datetime.now().isoformat(timespec="seconds")}}, upsert=True)
    return ditambah


def baca():
    df = d.baca_df("des")
    for k in ["mulai", "akhir"]:
        df[k] = pd.to_datetime(df[k])
    return df


def syariah_pada(des, tanggal):
    t = pd.Timestamp(tanggal)
    return set(des.loc[(des["mulai"] <= t) & (des["akhir"] >= t), "kode"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "perbarui":
        perbarui()
        sys.exit(0)
    des = bangun()
    print(des.groupby(["mulai", "kep"]).size().rename("saham").to_string())
    print(f"\n{des['kode'].nunique()} kode pernah masuk DES sejak {des['mulai'].min().date()} -> mongo koleksi des")
