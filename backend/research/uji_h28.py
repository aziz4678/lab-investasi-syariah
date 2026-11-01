import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import uji_h27 as h27
from backend.research.uji_dividen import bersih

GAP_MIN = 1.02
RISIKO_MAKS = 1.10
MULT_ATR = 3.0
N_MAKS = 10
PENANDA = d.penanda("holdout_dibuka_h28")


def sinyal(x):
    h_kemarin = x["high"].shift(1)
    s = (x["low"] >= h_kemarin * GAP_MIN) & (x["close"] <= h_kemarin * RISIKO_MAKS) & x["lolos"]
    return s.fillna(False).to_numpy(bool)


def simulasi(x, t, s):
    o, c, h = x["open"].to_numpy(float), x["close"].to_numpy(float), x["high"].to_numpy(float)
    atr = x["atr"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    n = len(x)
    hasil, bebas = [], 0
    for i in np.flatnonzero(s):
        if i < bebas or i < 1 or i + 1 >= n or not np.isfinite(atr[i]):
            continue
        batas = h[i - 1]
        e = o[i + 1]
        if e <= batas:
            continue
        stop = batas
        tertinggi = c[i + 1]
        j = i + 1
        while True:
            if c[j] < stop:
                sebab = "gap_tutup" if stop == batas else "trailing"
                if j + 1 <= n - 1:
                    k, px, alasan = j + 1, o[j + 1], "stop"
                else:
                    k, px, alasan = j, c[j], "akhir_data"
                break
            if j >= i + N_MAKS:
                k, px, alasan, sebab = j, c[j], "waktu", "waktu"
                break
            if j == n - 1:
                k, px, alasan, sebab = j, c[j], "terbuka", "terbuka"
                break
            tertinggi = max(tertinggi, c[j])
            if np.isfinite(atr[j]):
                stop = max(stop, tertinggi - MULT_ATR * atr[j])
            j += 1
        hasil.append({"ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k], "hari": k - i,
                      "stop_pct": (e - batas) / e * 100, "kotor": (px / e - 1) * 100,
                      "net": bersih(e, px, e * rasio[i + 1], px * rasio[k]), "alasan": alasan, "sebab": sebab})
        bebas = k
    return hasil


def kumpulkan(siap, mulai, akhir):
    semua = []
    for t, x in siap.items():
        semua += simulasi(x, t, sinyal(x))
    tr = pd.DataFrame(semua)
    return tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].reset_index(drop=True)


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    p = ap.parse_args().periode
    if p == "dev":
        hasil = h27.jalankan(h27.siapkan("dev"), pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31"), "dev 2010-2019",
                             kumpul=kumpulkan, hari_pemb=N_MAKS, kode="H28")
        hasil["dibuat"] = datetime.now().isoformat()
        dt.simpan_hasil("h28_dev", hasil)
        return
    dev = dt.baca_hasil("h28_dev")
    if not dev or not dev.get("lulus"):
        raise SystemExit("holdout H28 hanya dibuka kalau dev lulus semua kriteria")
    if PENANDA.exists():
        raise SystemExit(f"holdout H28 sudah pernah dibuka ({PENANDA.read_text().strip()})")
    PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    siap = h27.siapkan("holdout")
    akhir = max(x.index.max() for x in siap.values())
    hasil = h27.jalankan(siap, pd.Timestamp("2020-01-01"), akhir, "holdout 2020+", kumpul=kumpulkan, hari_pemb=N_MAKS, kode="H28")
    hasil["dibuat"] = datetime.now().isoformat()
    dt.simpan_hasil("h28_holdout", hasil)


if __name__ == "__main__":
    utama()
