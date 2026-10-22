import argparse

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.riset import des_ojk
from backend.riset import uji_h13 as h13
from backend.riset import uji_h16 as h
from backend.riset.uji_h15 import harga_buka, kalender

BATAS = pd.Timestamp("2023-12-31")
HORIZON = [1, 3, 6, 12]
CEK = ["ROE konsisten", "Utang", "Kualitas laba", "Laba tumbuh", "Margin", "Current ratio", "Likuid"]


def konteks(pasar, t):
    p = pasar[pasar.index <= t]
    ih = p["ihsg"].dropna()
    ubah = lambda s, n: (s.iloc[-1] / s.iloc[-1 - n] - 1) * 100 if len(s) > n else np.nan
    return {"ihsg_atas_ma200": bool(ih.iloc[-1] > ih.tail(200).mean()), "ihsg_6b": ubah(ih, 126), "minyak_6b": ubah(p["minyak"].dropna(), 126),
            "usdidr_6b": ubah(p["usdidr"].dropna(), 126), "vix": float(p["vix"].dropna().iloc[-1])}


def kandidat(df):
    g3 = df["g3"]
    return df["layak"] & (df["mos"] >= 40) & (g3.isna() | (g3 <= 50)) & df["ihsg_atas_ma200"]


def ringkas_kelompok(df, nama, saring):
    q = df[saring]
    teks = " | ".join(f"x{n} {q[f'x{n}'].mean():+.1f}% (median {q[f'x{n}'].median():+.1f}%, n={q[f'x{n}'].notna().sum()})" for n in (3, 6, 12) if f"x{n}" in q)
    print(f"{nama:<50} {len(q):>4} pilihan, {q['kode'].nunique():>3} saham | {teks}")


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--non", action="store_true")
    a = ap.parse_args()
    des = des_ojk.baca()
    fund = set(d.koneksi().fundamental.distinct("kode"))
    info = None
    if a.non:
        from backend.api import profil
        kode = sorted(k for k in (x.strip()[:-3] for x in dt.baca_daftar("nonsyariah_kode")) if k in fund)
        info = {}
        for k in kode:
            y = profil.yahoo(k) or {}
            info[k] = (y.get("sektor"), y.get("industri"))
        anggota = lambda t: set(kode)
        label = "NON-SYARIAH"
    else:
        kode = sorted(set(des["kode"]) & fund)
        anggota = lambda t: des_ojk.syariah_pada(des, t)
        label = "SYARIAH"
    akhir_bulan = list(pd.date_range(h.MULAI_PANEL, BATAS, freq="ME"))
    siap = h13.siapkan(kode)
    siap = {k: x[x.index <= BATAS] for k, x in siap.items()}
    panel = h.bangun_panel(kode, akhir_bulan, des, info)
    pasar = dt.baca("pasar")
    kal = kalender(siap)
    akhir = pd.Series(kal, index=kal).groupby(kal.to_period("M")).max()
    tgl = [t for t in akhir if pd.Period(h.DEV[0], "M") - 1 <= t.to_period("M") <= pd.Period(h.DEV[1], "M")]
    likuid = {}
    for k, x in siap.items():
        nol = (x["volume"] == 0).rolling(5).sum()
        likuid[k] = (x["value_mentah"] >= h.sc.MIN_VALUE) & (x["close_mentah"] >= h.sc.HARGA_MIN) & (nol == 0)
    baris = []
    for i, t in enumerate(tgl):
        bln = panel["tgl"][panel["tgl"].dt.to_period("M") == t.to_period("M")]
        if bln.empty:
            continue
        v = h.nilai_bulan(panel, bln.iloc[0], anggota(t))
        v = v[v["kode"].map(lambda s: s in siap and t in siap[s].index and bool(likuid[s].get(t, False)))]
        v = v[np.isfinite(v["mos"])]
        if len(v) < 10:
            continue
        e = kal[kal > t].min()
        ret = {}
        for n in HORIZON:
            j = i + n
            if j >= len(tgl) or tgl[j] >= BATAS:
                continue
            k_ = kal[kal > tgl[j]].min()
            if pd.isna(k_) or k_ > BATAS:
                continue
            r = {}
            for s in v["kode"]:
                a, b = harga_buka(siap[s], e), harga_buka(siap[s], k_)
                if np.isfinite(a) and np.isfinite(b) and a > 0:
                    r[s] = (b / a - 1) * 100
            ret[n] = pd.Series(r)
        kt = konteks(pasar, t)
        for r in v[v["layak"] | v["berkualitas"]].itertuples():
            dok = {"bulan": str(t.to_period("M")), "kode": r.kode, "layak": r.layak, "berkualitas": r.berkualitas, "sektor": r.sektor or "?", "siklikal": r.siklikal, "bank": r.bank,
                   "mos": r.mos, "pbv": r.pbv, "per": r.per, "pbv_z": r.pbv_z, "roe": r.roe, "der": r.der, "g1": r.g1, "g3": r.g3, "dy": r.dy,
                   "jarak_ma200": r.jarak_ma200, "skor": f"{r.skor}/{r.maks}", **kt,
                   **{f"cek_{CEK[n]}": c for n, c in enumerate(r.cek)}}
            for n, rs in ret.items():
                if r.kode in rs:
                    dok[f"r{n}"] = rs[r.kode]
                    dok[f"x{n}"] = rs[r.kode] - rs.mean()
            baris.append(dok)
    df = pd.DataFrame(baris)
    dt.simpan_hasil(f"analisis_h16_{label.lower()}", df.reset_index(drop=True))
    print(f"\n===== {label}: cek pola kandidat H17 (belum dikunci), dev 2021-04..2023-12, selisih vs rata-rata universe =====")
    ringkas_kelompok(df, "Undervalue + bukan Hindari", df["berkualitas"])
    ringkas_kelompok(df, "Layak", df["layak"])
    ringkas_kelompok(df, "Layak + MoS>=40 + laba 3th<=50% + IHSG>MA200", kandidat(df))
    ringkas_kelompok(df, "  sama, dari Undervalue+bukan Hindari", df["berkualitas"] & (df["mos"] >= 40) & (df["g3"].isna() | (df["g3"] <= 50)) & df["ihsg_atas_ma200"])
    ringkas_kelompok(df, "Undervalue+bukan Hindari, laba 3th > 50%", df["berkualitas"] & (df["g3"] > 50))
    ringkas_kelompok(df, "Undervalue+bukan Hindari, IHSG < MA200", df["berkualitas"] & ~df["ihsg_atas_ma200"])
    lay = df[df["layak"]]
    if lay.empty:
        return
    print(f"\n===== Saham LAYAK dev 2021-04..2023-12: {len(lay)} pilihan (saham-bulan), {lay['kode'].nunique()} saham =====")
    print("x = selisih return vs rata-rata universe pada horizon yang sama (%). Return yang melewati Des 2023 tidak dihitung.")
    print(lay[[f"x{n}" for n in HORIZON]].describe().loc[["count", "mean", "50%"]].round(2).to_string())
    print("\n--- per saham (rata-rata selisih) ---")
    per = lay.groupby("kode").agg(bulan=("bulan", "size"), pertama=("bulan", "min"), sektor=("sektor", "first"), x1=("x1", "mean"), x3=("x3", "mean"), x6=("x6", "mean"))
    print(per.sort_values("x3", ascending=False).round(1).to_string())
    print("\n--- menurut kondisi pasar saat dipilih (rata-rata x3) ---")
    for kol in ["ihsg_atas_ma200", "siklikal", "bank"]:
        print(f"{kol}: " + " | ".join(f"{k}: {g['x3'].mean():+.1f}% (n={g['x3'].notna().sum()})" for k, g in lay.groupby(kol)))
    lay = lay.assign(tahun=lay["bulan"].str[:4], minyak_naik=lay["minyak_6b"] > 0)
    for kol in ["tahun", "minyak_naik", "sektor"]:
        print(f"{kol}: " + " | ".join(f"{k}: {g['x3'].mean():+.1f}% (n={g['x3'].notna().sum()})" for k, g in lay.groupby(kol)))
    print("\n--- yang menang vs kalah (selisih 3 bulan > 0 vs <= 0), median ciri saat dipilih ---")
    q = lay[lay["x3"].notna()].assign(hasil=lambda z: np.where(z["x3"] > 0, "menang", "kalah"))
    kol = ["mos", "pbv", "per", "pbv_z", "roe", "der", "g1", "g3", "dy", "jarak_ma200", "ihsg_6b", "minyak_6b", "usdidr_6b", "vix"]
    print(q.groupby("hasil")[kol].median().round(1).T.to_string())
    print("\njumlah:", q["hasil"].value_counts().to_dict())
    bk = df[df["berkualitas"] & ~df["layak"]] if "berkualitas" in df else df.iloc[0:0]
    print(f"\nPembanding: Undervalue+bukan Hindari yang TIDAK layak ({len(bk)} pilihan): x3 rata-rata {bk['x3'].mean():+.1f}%; "
          f"bedanya dengan Layak terutama syarat harga >= MA200 dan kualitas >= maks-1.")


if __name__ == "__main__":
    utama()
