
import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

TAHUN_WAJIB = range(2019, 2027)


def nilai(f, nama, konteks):
    v = (f or {}).get(f"{nama}@{konteks}")
    return float(v) if v is not None else np.nan


def baca_json():
    baris = []
    for nama in dt.daftar_arsip(folder="fundamental", awalan="idx_fundamental_"):
        for r in dt.baca_arsip_json(nama):
            r["_file"] = nama
            baris.append(r)
    return baris


def bangun():
    baris = baca_json()
    data = []
    for r in baris:
        f = r.get("fakta") or {}
        ok = len([k for k in f if not k.startswith("_")]) > 3
        laba = nilai(f, "ProfitLossAttributableToParentEntity", "CurrentYearDuration")
        laba_lalu = nilai(f, "ProfitLossAttributableToParentEntity", "PriorYearDuration")
        if np.isnan(laba):
            laba, laba_lalu = nilai(f, "ProfitLoss", "CurrentYearDuration"), nilai(f, "ProfitLoss", "PriorYearDuration")
        data.append({
            "kode": str(r["kode"]).upper(), "tahun": int(r["tahun"]), "periode": str(r["periode"]).upper(), "ada_angka": ok,
            "error": r.get("error"), "unit": f.get("_unit"), "laba": laba, "laba_lalu": laba_lalu,
            "pendapatan": nilai(f, "SalesAndRevenue", "CurrentYearDuration"), "pendapatan_lalu": nilai(f, "SalesAndRevenue", "PriorYearDuration"),
            "ekuitas": nilai(f, "EquityAttributableToEquityOwnersOfParentEntity", "CurrentYearInstant"),
            "ekuitas_total": nilai(f, "Equity", "CurrentYearInstant"), "aset": nilai(f, "Assets", "CurrentYearInstant"), "liabilitas": nilai(f, "Liabilities", "CurrentYearInstant"),
            "arus_kas_operasi": nilai(f, "NetCashFlowsReceivedFromUsedInOperatingActivities", "CurrentYearDuration"),
            "arus_kas_operasi_lalu": nilai(f, "NetCashFlowsReceivedFromUsedInOperatingActivities", "PriorYearDuration"),
            "laba_kotor": nilai(f, "GrossProfit", "CurrentYearDuration"), "laba_kotor_lalu": nilai(f, "GrossProfit", "PriorYearDuration"),
            "kas": nilai(f, "CashAndCashEquivalents", "CurrentYearInstant"),
            "aset_lancar": nilai(f, "CurrentAssets", "CurrentYearInstant"), "liabilitas_lancar": nilai(f, "CurrentLiabilities", "CurrentYearInstant"),
            "eps": nilai(f, "BasicEarningsLossPerShareFromContinuingOperations", "CurrentYearDuration"), "_file": r["_file"],
        })
    df = pd.DataFrame(data).sort_values("ada_angka").drop_duplicates(["kode", "tahun", "periode"], keep="last")
    lk = d.baca_df("lapkeu", kolom=["kode", "tahun", "periode", "tgl_publikasi"])
    lk["tgl_publikasi"] = pd.to_datetime(lk["tgl_publikasi"])
    lk["tahun"] = lk["tahun"].astype(int)
    df = df.merge(lk, on=["kode", "tahun", "periode"], how="left")
    df["seimbang"] = (df["aset"] - df["liabilitas"] - df["ekuitas_total"]).abs() <= df["aset"].abs() * 0.01
    aset_idr = df["aset"].abs() * np.where(df["unit"] == "USD", 15000.0, 1.0)
    median_aset = aset_idr[df["ada_angka"]].groupby(df.loc[df["ada_angka"], "kode"]).median()
    rasio = aset_idr / df["kode"].map(median_aset)
    aneh = df["ada_angka"] & ((rasio > 1000) | (rasio < 0.001))
    df.loc[aneh, "ada_angka"] = False
    df.loc[aneh, "error"] = "skala angka tidak wajar (>1000x dari laporan lain)"
    if aneh.any():
        print(f"skala angka tidak wajar, tidak dipakai: {', '.join(df.loc[aneh, 'kode'] + ' ' + df.loc[aneh, 'tahun'].astype(str) + ' ' + df.loc[aneh, 'periode'])}")
    d.simpan_df("fundamental", df)
    return df


def baca():
    df = d.baca_df("fundamental")
    df["tgl_publikasi"] = pd.to_datetime(df["tgl_publikasi"])
    return df


def lengkap(df):
    ada = set(df["tahun"].unique())
    kurang = [t for t in TAHUN_WAJIB if t not in ada]
    gagal = df[~df["ada_angka"]].groupby(["tahun", "periode"]).size()
    return kurang, gagal


def laporan_pada(df, kode, tgl):
    d = df[(df["kode"] == kode) & df["ada_angka"] & df["tgl_publikasi"].notna() & (df["tgl_publikasi"] < tgl)]
    if d.empty:
        return None
    return d.loc[d["tgl_publikasi"].idxmax()]


def lolos_h14(lap):
    if lap is None or np.isnan(lap["laba"]) or np.isnan(lap["laba_lalu"]):
        return False, False
    a = bool(lap["laba"] > 0 and lap["laba"] > lap["laba_lalu"])
    b = a and not np.isnan(lap["pendapatan"]) and not np.isnan(lap["pendapatan_lalu"]) and lap["pendapatan"] > lap["pendapatan_lalu"]
    return a, bool(b)


if __name__ == "__main__":
    df = bangun()
    kurang, gagal = lengkap(df)
    print(f"{len(df)} laporan unik, {df['ada_angka'].sum()} berisi angka, {df['kode'].nunique()} kode -> mongo koleksi fundamental")
    print("per tahun-periode (berisi angka):")
    print(df[df["ada_angka"]].groupby(["tahun", "periode"]).size().unstack().fillna(0).astype(int).to_string())
    print(f"gagal/tanpa angka: {dict(gagal)}" if len(gagal) else "tidak ada yang gagal")
    print(f"tahun belum ada: {kurang}")
    ok = df[df["ada_angka"]]
    print(f"tanggal publikasi ketemu: {ok['tgl_publikasi'].notna().mean() * 100:.1f}% | mata uang: {ok['unit'].value_counts().to_dict()}")
    print(f"laba terisi {ok['laba'].notna().mean() * 100:.1f}% | laba tahun lalu {ok['laba_lalu'].notna().mean() * 100:.1f}% | "
          f"pendapatan {ok['pendapatan'].notna().mean() * 100:.1f}% | neraca seimbang (aset = liabilitas + ekuitas total) {ok['seimbang'].mean() * 100:.1f}%")
