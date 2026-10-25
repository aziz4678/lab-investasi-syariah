import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research.uji_dividen import evaluasi
from backend.research.uji_setup import pembanding, sinyal_tahan

DEV = (2020, 2023)
HOLDOUT_MULAI = 2024
PENANDA = d.penanda("holdout_dibuka_tahap2")


def siapkan():
    des = des_ojk.baca()
    data = sc.baca_harga(set(des["kode"]))
    pasar = sc.baca_pasar(data)
    idx = dt.baca("idx_harian")
    idx = idx[idx["StockCode"].isin(data)]
    siap = {}
    for t, d in data.items():
        d = d[d.index >= "2019-06-01"]
        if len(d) < 80:
            continue
        x = sc.fitur_ticker(d, pasar)
        rentang = des[des["kode"] == t]
        syariah = pd.Series(False, index=x.index)
        for r in rentang.itertuples():
            syariah |= (x.index >= r.mulai) & (x.index <= r.akhir)
        x["syariah"] = syariah
        x["lolos"] = x["lolos"] & syariah
        i = idx[idx["StockCode"] == t].set_index("tgl").sort_index().reindex(x.index)
        for k in ["Close", "Value", "NonRegularValue", "NonRegularVolume", "Bid", "Offer", "BidVolume", "OfferVolume"]:
            x["idx_" + k] = i[k]
        siap[t] = x
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    return siap, ihsg


def tambah_imbalance(siap):
    potong = []
    for t, x in siap.items():
        ok = (x["idx_Bid"] > 0) & (x["idx_Offer"] > x["idx_Bid"])
        total = x["idx_BidVolume"] + x["idx_OfferVolume"]
        x["imbalance"] = np.where(ok & (total > 0), (x["idx_BidVolume"] - x["idx_OfferVolume"]) / total, np.nan)
        p = x.loc[x["lolos"], ["imbalance"]].dropna()
        p["ticker"] = t
        potong.append(p)
    panel = pd.concat(potong)
    panel.index.name = "tgl"
    panel = panel.reset_index()
    jml = panel.groupby("tgl")["imbalance"].transform("size")
    panel = panel[jml >= sc.MIN_SAHAM_HARI]
    panel["pct"] = panel.groupby("tgl")["imbalance"].rank(pct=True)
    for t, x in siap.items():
        x["pct_imbalance"] = panel[panel["ticker"] == t].set_index("tgl")["pct"].reindex(x.index)


def tambah_lapkeu(siap, ihsg):
    lk = d.baca_df("lapkeu")
    if lk.empty:
        return False
    lk["tgl_publikasi"] = pd.to_datetime(lk["tgl_publikasi"])
    for t, x in siap.items():
        x["sinyal_lapkeu"] = False
        tgl = lk.loc[lk["kode"] == t, "tgl_publikasi"].dropna().sort_values().unique()
        if not len(tgl):
            continue
        ih = ihsg.reindex(x.index).ffill()
        pos = x.index.searchsorted(pd.DatetimeIndex(tgl))
        for p in pos:
            if p < 1 or p + 1 >= len(x):
                continue
            r_saham = x["close"].iloc[p + 1] / x["close"].iloc[p - 1] - 1
            r_ihsg = ih.iloc[p + 1] / ih.iloc[p - 1] - 1
            if (r_saham - r_ihsg) * 100 >= 4:
                x.iloc[p + 1, x.columns.get_loc("sinyal_lapkeu")] = True
    return True


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
    if a.periode == "holdout":
        if PENANDA.exists() and not a.paksa:
            print(f"holdout tahap 2 sudah pernah dibuka ({PENANDA.read_text().strip()})")
            return
        PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")

    siap, ihsg = siapkan()
    tambah_imbalance(siap)
    ada_lapkeu = tambah_lapkeu(siap, ihsg)
    lolos = sum(int(x.loc[x.index.year >= DEV[0], "lolos"].sum()) for x in siap.values())
    per_hari = pd.concat([x.loc[x["lolos"] & (x.index.year >= DEV[0])].index.to_series() for x in siap.values()]).value_counts().mean()
    print(f"universe DES historis: {len(siap)} ticker berdata, {lolos} hari-saham lolos sejak {DEV[0]}, rata2 {per_hari:.0f} saham/hari")

    hipotesis = {
        "H9 blok_negosiasi": (lambda x: (x["idx_NonRegularValue"] >= 0.5 * x["idx_Value"].rolling(20).mean())
                              & (x["idx_NonRegularValue"] / x["idx_NonRegularVolume"] >= x["idx_Close"] * 1.02), 10),
        "H10 imbalance_bid": (lambda x: x["pct_imbalance"] > 0.9, 5),
    }
    if ada_lapkeu:
        hipotesis["H8 reaksi_lapkeu"] = (lambda x: x["sinyal_lapkeu"], 10)
    else:
        print("koleksi lapkeu kosong: H8 dilewati")

    dasar = {}
    for nama, (syarat, h) in hipotesis.items():
        if h not in dasar:
            dasar[h] = potong(pembanding(siap, h), a.periode)
        tr = potong(sinyal_tahan(siap, syarat, h), a.periode)
        if tr.empty:
            print(f"\n{nama}: tidak ada trade")
            continue
        dt.simpan_hasil(f"trades_{nama.split()[0]}_{a.periode}", tr.reset_index(drop=True))
        evaluasi(tr, dasar[h], f"{nama} {a.periode} (tahan {h} hari)")


if __name__ == "__main__":
    utama()
