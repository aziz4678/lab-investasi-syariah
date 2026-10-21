import json
import sys
from pathlib import Path

import pandas as pd

from backend.db import data as dt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def sama(a, b):
    pd.testing.assert_frame_equal(a, b, check_freq=False)


def frame(nama, f):
    a = pd.read_parquet(f)
    dt.tulis(nama, a)
    sama(a, dt.baca(nama))
    return len(a)


def jalan():
    ringkas = {}
    for folder, koleksi in (("harga", "harga"), ("harian", "harian")):
        fs = sorted((DATA / folder).glob("*.parquet"))
        for i, f in enumerate(fs):
            frame(f"{koleksi}/{f.stem}", f)
            if (i + 1) % 200 == 0:
                print(f"  {koleksi}: {i + 1}/{len(fs)}")
        ringkas[koleksi] = len(fs)
        print(f"{koleksi}: {len(fs)} tabel dipindah dan dicek sama")
    for nama, f in (("pasar", DATA / "pasar.parquet"), ("idx_harian", DATA / "idx_harian.parquet"), ("ksei", DATA / "ksei" / "kepemilikan.parquet")):
        if f.exists():
            n = frame(nama, f)
            ringkas[nama] = n
            print(f"{nama}: {n} baris dipindah dan dicek sama")

    n = 0
    for f in sorted((DATA / "hasil").iterdir()):
        nama = f.stem
        if f.suffix == ".csv":
            a = pd.read_csv(f)
            dt.simpan_hasil(nama, a)
            sama(a, dt.baca_hasil(nama))
        elif f.suffix == ".json":
            isi = json.loads(f.read_text(encoding="utf-8"))
            dt.simpan_hasil(nama, isi)
            assert dt.baca_hasil(nama) == isi
        elif f.suffix == ".txt":
            isi = f.read_text(encoding="utf-8")
            dt.simpan_hasil(nama, isi)
            assert dt.baca_hasil(nama) == isi
        else:
            continue
        n += 1
    f = DATA / "ringkasan_data.csv"
    if f.exists():
        a = pd.read_csv(f)
        dt.simpan_hasil("ringkasan_data", a)
        sama(a, dt.baca_hasil("ringkasan_data"))
        n += 1
    ringkas["hasil_riset"] = n
    print(f"hasil_riset: {n} hasil uji dipindah dan dicek sama")

    for nama in ("syariah_tickers", "nonsyariah_kode"):
        f = DATA / f"{nama}.txt"
        if f.exists():
            isi = f.read_text(encoding="utf-8").split()
            dt.simpan_daftar(nama, isi)
            assert dt.baca_daftar(nama) == isi
            print(f"daftar {nama}: {len(isi)} kode")
    f = DATA / "des" / "des_kode.txt"
    if f.exists():
        isi = f.read_text(encoding="utf-8").split()
        dt.simpan_daftar("des_kode", isi)
        print(f"daftar des_kode: {len(isi)} kode")

    arsip = []
    for folder, pola in (("fundamental", "fundamental/*.json"), ("ojk_nab", "ojk_nab/*.json"), ("ksei", "ksei/*.zip"), ("des", "des/*.xlsx")):
        for f in sorted(DATA.glob(pola)):
            arsip.append((folder, f))
    for nama in ("idx_lapkeu_mentah.json", "idx_dividen_mentah.json"):
        if (DATA / nama).exists():
            arsip.append(("mentah", DATA / nama))
    for i, (folder, f) in enumerate(arsip):
        b = f.read_bytes()
        dt.simpan_arsip(f.name, b, folder)
        assert dt.baca_arsip(f.name) == b
        if (i + 1) % 50 == 0:
            print(f"  arsip: {i + 1}/{len(arsip)}")
    ringkas["arsip"] = len(arsip)
    print(f"arsip (GridFS): {len(arsip)} file sumber disimpan dan dicek byte per byte")
    print("\nSELESAI. Ukuran di MongoDB (database " + dt.NAMA_DB + "):")
    for k, v in sorted(dt.ringkas().items()):
        print(f"  {k}: {v['dokumen']} dokumen, {v['mb']} MB")


if __name__ == "__main__":
    jalan()
