import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset.uji_dividen import bersih, evaluasi
from backend.riset.uji_setup import pembanding
from backend.db import koneksi as d

DEV = (2010, 2019)
HOLDOUT_MULAI = 2020
MULT_ATR = 3.0
MAKS_HARI = 500
POSISI = 10
PEMBANDING_HARI = 20
PENANDA = d.penanda("holdout_dibuka_tren")


def tambah_fitur(x):
    x["ema200"] = x["close"].ewm(span=200, adjust=False).mean()
    x["mom120"] = (x["close"] / x["close"].shift(120) - 1) * 100
    x["maks250"] = x["close"].rolling(250).max().shift(1)
    return x


def siapkan_dev():
    data = {t: d[d.index <= f"{DEV[1]}-12-31"] for t, d in sc.baca_harga().items()}
    data = {t: d for t, d in data.items() if len(d) >= 300}
    pasar = sc.baca_pasar(data)
    return {t: tambah_fitur(sc.fitur_ticker(d, pasar)) for t, d in data.items()}


def siapkan_holdout():
    des = des_ojk.baca()
    data = sc.baca_harga(set(des["kode"]))
    pasar = sc.baca_pasar(data)
    siap = {}
    for t, d in data.items():
        d = d[d.index >= "2018-01-01"]
        if len(d) < 300:
            continue
        x = tambah_fitur(sc.fitur_ticker(d, pasar))
        syariah = pd.Series(False, index=x.index)
        for r in des[des["kode"] == t].itertuples():
            syariah |= (x.index >= r.mulai) & (x.index <= r.akhir)
        x["lolos"] = x["lolos"] & syariah
        siap[t] = x
    return siap


def tambah_peringkat_mom(siap):
    potong = []
    for t, x in siap.items():
        p = x.loc[x["lolos"], ["mom120"]].dropna()
        p["ticker"] = t
        potong.append(p)
    panel = pd.concat(potong)
    panel.index.name = "tgl"
    panel = panel.reset_index()
    jml = panel.groupby("tgl")["mom120"].transform("size")
    panel = panel[jml >= sc.MIN_SAHAM_HARI]
    panel["pct"] = panel.groupby("tgl")["mom120"].rank(pct=True)
    for t, x in siap.items():
        x["pct_mom"] = panel[panel["ticker"] == t].set_index("tgl")["pct"].reindex(x.index)


def simulasi(x, t, sinyal):
    o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
    atr = x["atr"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    n = len(x)
    hasil = []
    bebas = 0
    for i in np.flatnonzero(sinyal):
        if i < bebas or i + 1 >= n or not np.isfinite(atr[i]):
            continue
        e = o[i + 1]
        stop = e - MULT_ATR * atr[i]
        tertinggi = c[i + 1]
        alasan = None
        j = i + 1
        while True:
            if c[j] < stop:
                if j + 1 <= n - 1:
                    k, px, alasan = j + 1, o[j + 1], "stop"
                else:
                    k, px, alasan = j, c[j], "akhir_data"
                break
            tertinggi = max(tertinggi, c[j])
            if np.isfinite(atr[j]):
                stop = max(stop, tertinggi - MULT_ATR * atr[j])
            if j - (i + 1) >= MAKS_HARI:
                k, px, alasan = j, c[j], "waktu"
                break
            if j == n - 1:
                k, px, alasan = j, c[j], "terbuka"
                break
            j += 1
        hasil.append({
            "ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k], "hari": k - i,
            "stop_pct": MULT_ATR * atr[i] / e * 100, "mom120": x["mom120"].iloc[i],
            "kotor": (px / e - 1) * 100,
            "net": bersih(e, px, e * rasio[i + 1], px * rasio[k]),
            "alasan": alasan,
        })
        bebas = k
    return hasil


def kumpulkan(siap, syarat):
    semua = []
    for t, x in siap.items():
        semua += simulasi(x, t, (syarat(x) & x["lolos"]).fillna(False).to_numpy(bool))
    return pd.DataFrame(semua)


def benchmark(siap, mulai, akhir):
    potong = []
    for x in siap.values():
        r = x["close"].pct_change()
        ok = x["lolos"].shift(1, fill_value=False)
        potong.append(r[ok])
    r = pd.concat(potong).groupby(level=0).mean()
    r = r[(r.index >= mulai) & (r.index <= akhir)]
    ekuitas = (1 + r).cumprod()
    tahun = (r.index[-1] - r.index[0]).days / 365.25
    return (ekuitas.iloc[-1] ** (1 / tahun) - 1) * 100


def jalankan(siap, periode, label, hanya=None):
    tambah_peringkat_mom(siap)
    hipotesis = {
        "H11a 52w_high": lambda x: x["close"] >= x["maks250"],
        "H11b momentum6b": lambda x: (x["pct_mom"] > 0.9) & (x["close"] > x["ema200"]),
    }
    if hanya:
        hipotesis = {k: v for k, v in hipotesis.items() if k.startswith(hanya)}
    th_awal, th_akhir = periode
    mulai, akhir = pd.Timestamp(th_awal, 1, 1), pd.Timestamp(th_akhir, 12, 31)
    dasar = pembanding(siap, PEMBANDING_HARI)
    dasar = dasar[(dasar["tgl"] >= mulai) & (dasar["tgl"] <= akhir)]
    cagr_bm = benchmark(siap, mulai, akhir)
    print(f"\n##### {label}: CAGR beli-tahan semua saham universe (bobot sama, tanpa biaya): {cagr_bm:.1f}%")
    for nama, syarat in hipotesis.items():
        tr = kumpulkan(siap, syarat)
        tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].copy()
        if tr.empty:
            print(f"{nama}: tidak ada trade")
            continue
        dt.simpan_hasil(f"trades_{nama.split()[0]}_{label.split()[0].lower()}", tr.reset_index(drop=True))
        print(f"\nrata2 tahan {tr['hari'].mean():.0f} hari (median {tr['hari'].median():.0f}) | "
              f"alasan: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in tr["alasan"].value_counts(normalize=True).items()) +
              " | 5 terbaik: " + ", ".join(f"{r.ticker} {r.net:.0f}%" for r in tr.nlargest(5, "net").itertuples()))
        ok, bln = evaluasi(tr, dasar, f"{nama} {label}", maks=POSISI, kembalikan_bulanan=True)
        ok7 = bln.get("cagr", -np.inf) > cagr_bm
        print(f"  [{'LULUS' if ok7 else 'GAGAL'}] 7. CAGR portofolio > beli-tahan: {bln.get('cagr', np.nan):.1f}% vs {cagr_bm:.1f}%")
        print(f"  HASIL AKHIR {nama} {label}: {'LULUS' if ok and ok7 else 'GAGAL'}")


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--paksa", action="store_true")
    a = ap.parse_args()
    if a.periode == "dev":
        jalankan(siapkan_dev(), DEV, "DEV 2010-2019 (217 saham)")
        return
    if PENANDA.exists() and not a.paksa:
        print(f"holdout tren sudah pernah dibuka ({PENANDA.read_text().strip()})")
        return
    PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    jalankan(siapkan_holdout(), (HOLDOUT_MULAI, 2026), "HOLDOUT 2020+ (DES historis)", hanya="H11a")


if __name__ == "__main__":
    utama()
