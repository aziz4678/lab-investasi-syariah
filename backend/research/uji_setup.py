import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import screener as sc
from backend.research.uji_dividen import bersih, evaluasi

DEV = (2010, 2021)
HOLDOUT_MULAI = 2022
PENANDA = d.penanda("holdout_dibuka_setup")
LEBARAN = ["2010-09-10", "2011-08-30", "2012-08-19", "2013-08-08", "2014-07-28", "2015-07-17", "2016-07-06",
           "2017-06-25", "2018-06-15", "2019-06-05", "2020-05-24", "2021-05-13", "2022-05-02", "2023-04-22",
           "2024-04-10", "2025-03-31", "2026-03-20"]


def siapkan():
    data = sc.baca_harga()
    pasar = sc.baca_pasar(data)
    hasil = {}
    for t, d in data.items():
        x = sc.fitur_ticker(d, pasar)
        x["mom3"] = (x["close"] / x["close"].shift(3) - 1) * 100
        hasil[t] = x
    kalender = dt.baca("pasar")["ihsg"].dropna().index
    return hasil, kalender


def trade(x, t, masuk, keluar):
    o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    e, k = o[masuk], c[keluar]
    return pd.DataFrame({
        "ticker": t, "tgl": x.index[masuk - 1], "tgl_exit": x.index[keluar],
        "kotor": (k / e - 1) * 100,
        "net": bersih(e, k, e * rasio[masuk], k * rasio[keluar]),
    })


def tanpa_tumpang(idx, h):
    ambil = []
    akhir = -1
    for i in idx:
        if i >= akhir:
            ambil.append(i)
            akhir = i + h
    return np.array(ambil, dtype=int)


def sinyal_tahan(siap, syarat, h):
    potong = []
    for t, x in siap.items():
        idx = np.flatnonzero((syarat(x) & x["lolos"]).to_numpy(bool))
        idx = tanpa_tumpang(idx[idx + h <= len(x) - 1], h)
        if len(idx):
            potong.append(trade(x, t, idx + 1, idx + h))
    return pd.concat(potong, ignore_index=True)


def pembanding(siap, h):
    potong = []
    for t, x in siap.items():
        idx = np.flatnonzero(x["lolos"].to_numpy(bool))
        idx = idx[idx + h <= len(x) - 1]
        potong.append(trade(x, t, idx + 1, idx + h))
    return pd.concat(potong, ignore_index=True)


def sinyal_tanggal(siap, pasangan):
    potong = []
    for t, x in siap.items():
        pos = pd.Series(np.arange(len(x)), index=x.index)
        lolos = x["lolos"].to_numpy(bool)
        masuk, keluar = [], []
        for tm, tk in pasangan:
            if tm in pos.index and tk in pos.index:
                m, k = pos[tm], pos[tk]
                if m >= 1 and k > m and lolos[m - 1]:
                    masuk.append(m)
                    keluar.append(k)
        if masuk:
            potong.append(trade(x, t, np.array(masuk), np.array(keluar)))
    return pd.concat(potong, ignore_index=True)


def pasangan_bulan(kalender):
    s = pd.Series(kalender, index=kalender)
    bulan = s.groupby(kalender.to_period("M"))
    akhir = bulan.max()
    pasangan = []
    periode = list(akhir.index)
    for p, q in zip(periode[:-1], periode[1:]):
        hari_q = bulan.get_group(q)
        if len(hari_q) >= 3:
            pasangan.append((akhir[p], hari_q.iloc[2]))
    return pasangan


def pasangan_lebaran(kalender):
    pasangan = []
    for tg in LEBARAN:
        sebelum = kalender[kalender < pd.Timestamp(tg)]
        if len(sebelum) < 5:
            continue
        sesudah = kalender[kalender >= pd.Timestamp(tg)]
        libur = (sesudah[0] - sebelum[-1]).days if len(sesudah) else None
        print(f"  lebaran {tg}: hari bursa terakhir {sebelum[-1].date()}, libur {libur} hari kalender")
        pasangan.append((sebelum[-5], sebelum[-1]))
    return pasangan


def potong_periode(df, periode):
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
            print(f"holdout setup sudah pernah dibuka ({PENANDA.read_text().strip()})")
            return
        PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")

    siap, kalender = siapkan()
    hipotesis = {
        "H3 pullback": (lambda: sinyal_tahan(siap, lambda x: (x["ema20"] > x["ema50"]) & (x["close"] > x["ema50"]) & (x["mom3"] <= -5), 10), 10),
        "H4 breakout": (lambda: sinyal_tahan(siap, lambda x: (x["kontraksi"].shift(1) < 0.8) & (x["close"] > x["high20"]) & (x["vol_rasio"] >= 2), 10), 10),
        "H5 pergantian_bulan": (lambda: sinyal_tanggal(siap, pasangan_bulan(kalender)), 4),
        "H6 lebaran": (lambda: sinyal_tanggal(siap, pasangan_lebaran(kalender)), 5),
    }
    dasar_cache = {}
    ringkas = []
    for nama, (buat, h) in hipotesis.items():
        if h not in dasar_cache:
            dasar_cache[h] = pembanding(siap, h)
        tr = potong_periode(buat(), a.periode)
        dasar = potong_periode(dasar_cache[h], a.periode)
        dt.simpan_hasil(f"trades_{nama.split()[0]}_{a.periode}", tr.reset_index(drop=True))
        ok = evaluasi(tr, dasar, f"{nama} {a.periode} (tahan {h} hari)")
        ringkas.append((nama, ok, len(tr), tr["net"].mean(), tr["kotor"].mean(), dasar["kotor"].mean()))

    print("\nringkasan:")
    for nama, ok, n, net, kotor, dk in ringkas:
        print(f"  {nama:22s} {'LULUS' if ok else 'GAGAL'} | n {n} | kotor {kotor:.2f}% (pembanding {dk:.2f}%) | net {net:.2f}%")


if __name__ == "__main__":
    utama()
