import json
import sys
from pathlib import Path

import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

AKHIR_PERIODE = {"TW1": "03-31", "TW2": "06-30", "TW3": "09-30", "AUDIT": "12-31"}


def utama():
    sumber = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    isi = json.loads(sumber.read_text(encoding="utf-8")) if sumber and sumber.exists() else dt.baca_arsip_json("idx_lapkeu_mentah.json")
    df = pd.DataFrame(isi["data"], columns=isi["kolom"])
    df["kode"] = df["kode"].astype(str).str.strip().str.upper()
    df["periode"] = df["periode"].astype(str).str.upper()
    df["tahun"] = pd.to_numeric(df["tahun"], errors="coerce")
    fm = pd.to_datetime(df["file_modified"], errors="coerce", format="ISO8601")
    lt = pd.to_datetime(df["lampiran_terawal"], errors="coerce", format="ISO8601")
    gagal = (fm.isna() & df["file_modified"].notna()).sum() + (lt.isna() & df["lampiran_terawal"].notna()).sum()
    if gagal:
        print(f"PERINGATAN: {gagal} nilai waktu gagal dibaca")
    waktu = pd.concat([fm, lt], axis=1).min(axis=1)
    df["waktu_publikasi"] = waktu
    df["tgl_publikasi"] = waktu.dt.normalize()
    akhir = pd.to_datetime(df["tahun"].astype("Int64").astype(str) + "-" + df["periode"].map(AKHIR_PERIODE), errors="coerce")
    df["akhir_periode"] = akhir
    df["jeda_hari"] = (df["tgl_publikasi"] - akhir).dt.days
    awal = len(df)
    df = df.dropna(subset=["tgl_publikasi", "akhir_periode"]).drop_duplicates(["kode", "periode", "tahun"])
    telat = df["jeda_hari"] > 183
    negatif = df["jeda_hari"] < 0
    print(f"{awal} record | unik {len(df)} | dibuang karena > 6 bulan setelah akhir periode: {telat.sum()} | "
          f"tanggal sebelum akhir periode (aneh): {negatif.sum()}")
    df = df[~telat & ~negatif]
    print(df.groupby(["tahun", "periode"]).size().unstack().fillna(0).astype(int).to_string())
    print(f"jeda publikasi (hari setelah akhir periode): median {df['jeda_hari'].median():.0f}, "
          f"persentil 10/90: {df['jeda_hari'].quantile(0.1):.0f}/{df['jeda_hari'].quantile(0.9):.0f}")
    print(f"jam publikasi: {(df['waktu_publikasi'].dt.hour >= 16).mean() * 100:.0f}% setelah jam 16:00")
    n = d.simpan_df("lapkeu", df[["kode", "periode", "tahun", "akhir_periode", "waktu_publikasi", "tgl_publikasi", "jeda_hari"]])
    print(f"-> mongo koleksi lapkeu ({n} dokumen)")


if __name__ == "__main__":
    utama()
