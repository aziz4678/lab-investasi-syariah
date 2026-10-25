import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import screener as sc
from backend.research.laporan_bulanan import ringkas_bulanan

SEBELUM_EX = 5
DEV = (2010, 2021)
HOLDOUT_MULAI = 2022
YIELD_MIN = 3.0
PENANDA = d.penanda("holdout_dibuka_dividen")


def bersih(e, x, e_mentah, x_mentah):
    beli = e * (1 + sc.fraksi(e_mentah) / e_mentah) * (1 + sc.FEE_BELI / 100)
    jual = x * (1 - sc.fraksi(x_mentah) / x_mentah) * (1 - sc.FEE_JUAL / 100)
    return (jual / beli - 1) * 100


def kumpulkan():
    data = sc.baca_harga()
    pasar = sc.baca_pasar(data)
    event = []
    pembanding = []
    for t, d in data.items():
        mentah = dt.baca(f"harga/{t}").reindex(d.index)
        x = sc.fitur_ticker(d, pasar)
        o, c = d["open"].to_numpy(float), d["close"].to_numpy(float)
        rasio = (d["close_mentah"] / d["close"]).to_numpy(float)
        lolos = x["lolos"].to_numpy(bool)
        div = mentah["dividends"].fillna(0).to_numpy(float) if "dividends" in mentah else np.zeros(len(d))

        for k in np.flatnonzero(div > 0):
            i = k - SEBELUM_EX - 1
            if i < 0 or not lolos[i]:
                continue
            e, xk = o[k - SEBELUM_EX], c[k - 1]
            event.append({
                "ticker": t, "tgl": d.index[i], "tgl_entry": d.index[k - SEBELUM_EX], "tgl_cum": d.index[k - 1], "tgl_exit": d.index[k - 1],
                "yield": div[k] / d["close_mentah"].iloc[i] * 100,
                "kotor": (xk / e - 1) * 100,
                "net": bersih(e, xk, e * rasio[k - SEBELUM_EX], xk * rasio[k - 1]),
            })

        n = len(d)
        idx = np.flatnonzero(lolos[: n - 4])
        e, xk = o[idx + 1], c[idx + 4]
        pembanding.append(pd.DataFrame({
            "tgl": d.index[idx], "ticker": t,
            "kotor": (xk / e - 1) * 100,
            "net": bersih(e, xk, e * rasio[idx + 1], xk * rasio[idx + 4]),
        }))
    return pd.DataFrame(event), pd.concat(pembanding, ignore_index=True)


def evaluasi(tr, dasar, label, maks=5, kembalikan_bulanan=False):
    exp = tr["net"].mean()
    base = dasar["net"].mean()
    lo, hi = sc.bootstrap(tr)
    th = tr.groupby(tr["tgl"].dt.year)["net"].mean()
    th_pos = (th > 0).mean() * 100
    tanpa10 = tr.drop(tr["net"].nlargest(10).index)["net"].mean()
    lima = tr.groupby("ticker")["net"].sum().nlargest(5).index
    tanpa5 = tr[~tr["ticker"].isin(lima)]["net"].mean()

    print(f"\n--- {label}: {len(tr)} event, {tr['ticker'].nunique()} ticker ---")
    print(f"exp net {exp:.2f}% | kotor {tr['kotor'].mean():.2f}% | median net {tr['net'].median():.2f}% | "
          f"menang (net>0) {(tr['net'] > 0).mean() * 100:.0f}% | kotor >= 3%: {(tr['kotor'] >= 3).mean() * 100:.0f}%")
    print(f"pembanding (semua tahanan dengan lama sama): net {base:.2f}%, kotor {dasar['kotor'].mean():.2f}%, kotor >= 3%: "
          f"{(dasar['kotor'] >= 3).mean() * 100:.0f}%")
    print(f"bootstrap 90%: [{lo:.2f}, {hi:.2f}]")
    print("per tahun: " + " | ".join(f"{t}: {v:.2f}% ({(tr['tgl'].dt.year == t).sum()})" for t, v in th.items()))
    print(f"tanpa 10 terbaik {tanpa10:.2f}% | tanpa 5 ticker ({', '.join(lima)}) {tanpa5:.2f}%")
    kriteria = [
        ("exp net > 0", exp > 0, f"{exp:.2f}%"),
        ("lebih tinggi dari pembanding", exp > base, f"{exp:.2f} vs {base:.2f}"),
        ("bootstrap 5% > 0", lo > 0, f"{lo:.2f}%"),
        ("tahun positif >= 70%", th_pos >= 70, f"{th_pos:.0f}%"),
        ("tanpa 10 terbaik > 0", tanpa10 > 0, f"{tanpa10:.2f}%"),
        ("tanpa 5 ticker > 0", tanpa5 > 0, f"{tanpa5:.2f}%"),
    ]
    for nama, ok, nilai in kriteria:
        print(f"  [{'LULUS' if ok else 'GAGAL'}] {nama}: {nilai}")
    semua = all(ok for _, ok, _ in kriteria)
    print(f"hasil {label}: {'LULUS' if semua else 'GAGAL'}")
    bulanan = ringkas_bulanan(tr, maks)
    return (semua, bulanan) if kembalikan_bulanan else semua


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--paksa", action="store_true")
    a = ap.parse_args()
    if a.periode == "holdout":
        if PENANDA.exists() and not a.paksa:
            print(f"holdout dividen sudah pernah dibuka ({PENANDA.read_text().strip()})")
            return
        PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")

    ev, dasar = kumpulkan()
    th_ev, th_d = ev["tgl"].dt.year, dasar["tgl"].dt.year
    if a.periode == "dev":
        ev, dasar = ev[(th_ev >= DEV[0]) & (th_ev <= DEV[1])], dasar[(th_d >= DEV[0]) & (th_d <= DEV[1])]
    else:
        ev, dasar = ev[th_ev >= HOLDOUT_MULAI], dasar[th_d >= HOLDOUT_MULAI]
    print(f"periode {a.periode}: {ev['tgl'].min().date()} s/d {ev['tgl'].max().date()} | "
          f"entry open ex-{SEBELUM_EX}, exit close cum date")
    dt.simpan_hasil(f"trades_dividen_{a.periode}", ev.reset_index(drop=True))
    evaluasi(ev, dasar, f"UTAMA {a.periode}")
    evaluasi(ev[ev["yield"] >= YIELD_MIN].copy(), dasar, f"YIELD>={YIELD_MIN:g}% {a.periode}")


if __name__ == "__main__":
    utama()
