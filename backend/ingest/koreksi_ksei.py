import sys
from datetime import datetime

import pandas as pd

from backend.db import data as dt

KOLEKSI = "koreksi_ksei"


def aturan():
    return list(dt.db()[KOLEKSI].find({"status": "aktif"}))


def terapkan(df, daftar=None):
    df = df.copy()
    for a in aturan() if daftar is None else daftar:
        m = (df["kode"] == a["kode"]) & (df["tgl"] == pd.Timestamp(a["tgl"]))
        if not m.any():
            print(f"koreksi KSEI {a['_id']}: baris tidak ada", flush=True)
            continue
        kini = df.loc[m, "saham"].iloc[0]
        if kini not in (a["saham_asli"], a["saham"]):
            print(f"koreksi KSEI {a['_id']}: nilai sekarang {kini:,.0f} bukan nilai asli {a['saham_asli']:,.0f}, dilewati", flush=True)
            continue
        df.loc[m, "saham"] = a["saham"]
    return df


def simpan(daftar, disetujui):
    k = dt.db()[KOLEKSI]
    for a in daftar:
        dok = dict(a, _id=f"{a['kode']}:{a['tgl']}", status="aktif", disetujui=disetujui, dibuat=datetime.now())
        k.replace_one({"_id": dok["_id"]}, dok, upsert=True)
    return len(daftar)


def perbarui():
    df = dt.baca("ksei")
    baru = terapkan(df)
    n = int((baru["saham"] != df["saham"]).sum())
    if n:
        dt.tulis("ksei", baru)
    print(f"{len(aturan())} aturan koreksi KSEI aktif, {n} baris diubah", flush=True)
    return n


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "perbarui":
        perbarui()
    else:
        for a in aturan():
            print(a["_id"], a["saham_asli"], "->", a["saham"], a["alasan"])
