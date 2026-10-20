import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.riset import screener as sc
from backend.riset.uji_dividen import evaluasi
from backend.riset.uji_setup import pembanding, siapkan, sinyal_tahan
from backend.db import koneksi as d

DEV = (2020, 2023)
HOLDOUT_MULAI = 2024
TAHAN = 10
PENANDA = d.penanda("holdout_dibuka_asing")
FILE_IDX = "idx_harian"


def baca_idx():
    df = pd.read_parquet(FILE_IDX) if str(FILE_IDX).endswith(".parquet") else dt.baca(FILE_IDX)
    df = df[df["StockCode"].isin(sc.daftar_syariah())].copy()
    df["net_asing"] = (df["ForeignBuy"] - df["ForeignSell"]) * df["Close"]
    ok = (df["Bid"] > 0) & (df["Offer"] > df["Bid"])
    tengah = (df["Bid"] + df["Offer"]) / 2
    df["spread_pct"] = np.where(ok, (df["Offer"] - df["Bid"]) / tengah * 100, np.nan)
    return df


def tempel_asing(siap, idx):
    for t, x in siap.items():
        d = idx[idx["StockCode"] == t].set_index("tgl").sort_index()
        d = d.reindex(x.index)
        nilai20 = d["Value"].rolling(20, min_periods=15).mean()
        x["akum5"] = d["net_asing"].rolling(5, min_periods=5).sum() / nilai20
        x["half_spread"] = d["spread_pct"].rolling(20, min_periods=10).median() / 2
        x["close_idx"] = d["Close"]
    panel = pd.concat({t: x.loc[x["lolos"], ["akum5"]] for t, x in siap.items()}, names=["ticker", "tgl"])
    panel = panel.dropna().reset_index()
    panel["pct"] = panel.groupby("tgl")["akum5"].rank(pct=True)
    jml = panel.groupby("tgl")["akum5"].transform("size")
    panel = panel[jml >= sc.MIN_SAHAM_HARI]
    for t, x in siap.items():
        p = panel[panel["ticker"] == t].set_index("tgl")["pct"]
        x["pct_asing"] = p.reindex(x.index)


def cek_kualitas(siap):
    baris = []
    for t, x in siap.items():
        s = x[x.index.year >= DEV[0]]
        if s.empty:
            continue
        ada = s["close_idx"].notna()
        cocok = (s.loc[ada, "close_idx"] - s.loc[ada, "close_mentah"]).abs() <= sc.fraksi(s.loc[ada, "close_mentah"])
        baris.append({"ticker": t, "lolos": s["lolos"].sum(), "lolos_ada_asing": (s["lolos"] & s["akum5"].notna()).sum(),
                      "hari_idx": ada.sum(), "close_cocok": cocok.sum()})
    r = pd.DataFrame(baris)
    liputan = r["lolos_ada_asing"].sum() / max(r["lolos"].sum(), 1) * 100
    cocok = r["close_cocok"].sum() / max(r["hari_idx"].sum(), 1) * 100
    print(f"liputan asing di baris lolos universe (2020+): {liputan:.1f}% | close IDX cocok dengan yfinance (selisih <= 1 tick): {cocok:.1f}%")
    jelek = r[(r["hari_idx"] > 0) & (r["close_cocok"] / r["hari_idx"].clip(lower=1) < 0.9)]
    if len(jelek):
        print(f"ticker dengan kecocokan close < 90%: {', '.join(jelek['ticker'].head(15))}")
    return liputan


def laporan_spread(siap, idx):
    s = idx[(idx["tgl"].dt.year >= DEV[0]) & idx["spread_pct"].notna()].copy()
    s["tick_pct"] = sc.fraksi(s["Close"]) / s["Close"] * 100
    s["kelas"] = pd.cut(s["Close"], [0, 200, 500, 2000, 5000, 1e9], labels=["<200", "200-499", "500-1999", "2000-4999", "5000+"])
    r = s.groupby("kelas", observed=True).agg(n=("spread_pct", "size"), spread_median=("spread_pct", "median"),
                                              tick_median=("tick_pct", "median"))
    r["spread_dlm_tick"] = (r["spread_median"] / r["tick_median"]).round(2)
    print("\nspread penutupan nyata (Offer - Bid) / tengah, saham syariah 2020+:")
    print(r.round(3).to_string())
    print("model biaya sekarang = 1 tick per sisi = sekitar 'tick_median' per sisi; setengah spread = spread_median / 2 per sisi")


def net_alternatif(tr, siap):
    hs = []
    for r in tr.itertuples():
        hs.append(siap[r.ticker]["half_spread"].get(r.tgl, np.nan))
    s = np.array(hs, dtype=float) / 100
    beli = (1 + s) * (1 + sc.FEE_BELI / 100)
    jual = (1 + tr["kotor"].to_numpy() / 100) * (1 - s) * (1 - sc.FEE_JUAL / 100)
    return (jual / beli - 1) * 100


def potong(df, periode):
    th = df["tgl"].dt.year
    if periode == "dev":
        return df[(th >= DEV[0]) & (th <= DEV[1])].copy()
    return df[th >= HOLDOUT_MULAI].copy()


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--paksa", action="store_true")
    a = ap.parse_args()
    if not FILE_IDX.exists():
        print(f"{FILE_IDX} belum ada, jalankan 'python idx_asing.py impor' dulu")
        return
    if a.periode == "holdout":
        if PENANDA.exists() and not a.paksa:
            print(f"holdout asing sudah pernah dibuka ({PENANDA.read_text().strip()})")
            return
        PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")

    siap, _ = siapkan()
    idx = baca_idx()
    tempel_asing(siap, idx)
    liputan = cek_kualitas(siap)
    laporan_spread(siap, idx)
    if liputan < 80:
        print(f"\nliputan {liputan:.1f}% < 80%: sesuai rencana, hasil H7 TIDAK dipakai. Uji tetap dicetak untuk informasi.")

    dasar = potong(pembanding(siap, TAHAN), a.periode)
    hipotesis = {
        "H4 breakout (pembanding H7b, bukan uji baru)": lambda x: (x["kontraksi"].shift(1) < 0.8) & (x["close"] > x["high20"]) & (x["vol_rasio"] >= 2),
        "H7a asing_top10": lambda x: x["pct_asing"] > 0.9,
        "H7b breakout_asing": lambda x: (x["kontraksi"].shift(1) < 0.8) & (x["close"] > x["high20"]) & (x["vol_rasio"] >= 2) & (x["akum5"] > 0),
    }
    exp_h4 = np.nan
    for nama, syarat in hipotesis.items():
        tr = potong(sinyal_tahan(siap, syarat, TAHAN), a.periode)
        if tr.empty:
            print(f"\n{nama}: tidak ada trade")
            continue
        dt.simpan_hasil(f"trades_{nama.split()[0]}_{a.periode}", tr.reset_index(drop=True))
        evaluasi(tr, dasar, f"{nama} {a.periode}")
        if nama.startswith("H4"):
            exp_h4 = tr["net"].mean()
        if nama.startswith("H7b"):
            ok = tr["net"].mean() > exp_h4
            print(f"  [{'LULUS' if ok else 'GAGAL'}] tambahan: exp H7b > exp H4: {tr['net'].mean():.2f} vs {exp_h4:.2f}")
            if len(tr) < 50:
                print(f"H7b cuma {len(tr)} trade (< 50): sesuai rencana, tidak cukup bukti apa pun hasilnya")
        alt = net_alternatif(tr, siap)
        print(f"biaya alternatif (setengah spread nyata per sisi): exp net {np.nanmean(alt):.2f}% "
              f"(model 1 tick: {tr['net'].mean():.2f}%) -> kalau cuma lulus di sini, statusnya kandidat")


if __name__ == "__main__":
    utama()
