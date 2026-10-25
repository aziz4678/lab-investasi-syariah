import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research.uji_dividen import bersih, evaluasi
from backend.research.uji_setup import pembanding
from backend.research.uji_tren import benchmark

DEV = (2010, 2019)
HOLDOUT_MULAI = 2020
MULT_ATR = 3.0
POSISI = 10


def rsi_wilder(c, n):
    beda = c.diff()
    naik = beda.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    turun = (-beda.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rsi = 100 - 100 / (1 + naik / turun.replace(0, np.nan))
    return rsi.mask((turun == 0) & (naik > 0), 100.0).mask((turun == 0) & (naik == 0), 50.0)


def tambah_fitur(x):
    c, h, l, o, v = x["close"], x["high"], x["low"], x["open"], x["volume"]
    x["ma20"] = c.rolling(20).mean()
    x["ma50"] = c.rolling(50).mean()
    x["ma200"] = c.rolling(200).mean()
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    x["macd"], x["macd_sig"] = macd, macd.ewm(span=9, adjust=False).mean()
    lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
    x["stoch_k"] = (c - lo14) / (hi14 - lo14).replace(0, np.nan) * 100
    x["stoch_d"] = x["stoch_k"].rolling(3).mean()
    x["rsi2"] = rsi_wilder(c, 2)
    sd = c.rolling(20).std()
    x["bb_atas"] = x["ma20"] + 2 * sd
    x["bb_lebar"] = 4 * sd / x["ma20"]
    x["vol_rata"] = v.rolling(20).mean().shift(1)
    x["low20"] = l.rolling(20).min().shift(1)
    rng = (h - l).replace(0, np.nan)
    x["posisi"] = (c - l) / rng
    return x


def sinyal(nama, x):
    c, o, h, l, v = x["close"], x["open"], x["high"], x["low"], x["volume"]
    k1 = lambda s: s.shift(1)
    if nama == "H19a":
        return (x["ma50"] > x["ma200"]) & (k1(x["ma50"]) <= k1(x["ma200"])), x["ma50"] < x["ma200"], 500, 20
    if nama == "H19b":
        s = (x["macd"] > x["macd_sig"]) & (k1(x["macd"]) <= k1(x["macd_sig"])) & (x["macd"] > 0) & (c > x["ma200"])
        return s, x["macd"] < x["macd_sig"], 500, 20
    if nama == "H19c":
        s = (x["stoch_k"] > x["stoch_d"]) & (k1(x["stoch_k"]) <= k1(x["stoch_d"])) & (k1(x["stoch_d"]) < 20) & (c > x["ma200"])
        return s, x["stoch_k"] > 80, 20, 10
    if nama == "H19d":
        return (x["rsi2"] < 10) & (c > x["ma200"]), x["rsi2"] > 70, 10, 5
    if nama == "H19e":
        sempit = k1(x["bb_lebar"]) <= x["bb_lebar"].rolling(120).min().shift(1) * 1.0000001
        s = sempit & (c > x["bb_atas"]) & (v >= 1.5 * x["vol_rata"])
        return s, c < x["ma20"], 500, 20
    if nama == "H19f":
        badan = (c - o).abs()
        rng = h - l
        engulf = (k1(c) < k1(o)) & (c > o) & (o <= k1(c)) & (c >= k1(o))
        bawah = np.minimum(o, c) - l
        atas = h - np.maximum(o, c)
        hammer = (rng > 0) & (badan <= rng / 3) & (bawah >= 2 * badan) & (atas <= badan) & (x["posisi"] >= 2 / 3)
        s = (engulf | hammer) & (l <= x["low20"] * 1.02) & (v >= x["vol_rata"])
        return s, None, 5, 5
    if nama == "H19g":
        return (x["posisi"] >= 0.95) & (v >= 2 * x["vol_rata"]) & (c > k1(c)), None, 1, None
    raise KeyError(nama)


def simulasi(x, t, s, keluar, n_maks):
    o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
    atr = x["atr"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    kx = keluar.fillna(False).to_numpy(bool) if keluar is not None else np.zeros(len(x), bool)
    n = len(x)
    hasil, bebas = [], 0
    for i in np.flatnonzero(s):
        if i < bebas or i + 1 >= n or not np.isfinite(atr[i]):
            continue
        e = o[i + 1]
        stop = e - MULT_ATR * atr[i]
        tertinggi = c[i + 1]
        j = i + 1
        while True:
            if c[j] < stop or (j > i + 1 and kx[j]):
                alasan = "stop" if c[j] < stop else "aturan"
                k, px = (j + 1, o[j + 1]) if j + 1 <= n - 1 else (j, c[j])
                break
            if j >= i + n_maks:
                k, px, alasan = j, c[j], "waktu"
                break
            if j == n - 1:
                k, px, alasan = j, c[j], "terbuka"
                break
            tertinggi = max(tertinggi, c[j])
            if np.isfinite(atr[j]):
                stop = max(stop, tertinggi - MULT_ATR * atr[j])
            j += 1
        hasil.append({"ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k], "hari": k - i, "kotor": (px / e - 1) * 100,
                      "net": bersih(e, px, e * rasio[i + 1], px * rasio[k]), "alasan": alasan})
        bebas = k
    return hasil


def simulasi_bsjp(x, t, s):
    o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    hasil = []
    for i in np.flatnonzero(s):
        if i + 1 >= len(x):
            continue
        hasil.append({"ticker": t, "tgl": x.index[i], "tgl_exit": x.index[i + 1], "hari": 1, "kotor": (o[i + 1] / c[i] - 1) * 100,
                      "net": bersih(c[i], o[i + 1], c[i] * rasio[i], o[i + 1] * rasio[i + 1]), "alasan": "pagi"})
    return hasil


def pembanding_bsjp(siap):
    potong = []
    for t, x in siap.items():
        lolos = x["lolos"].to_numpy(bool)
        idx = np.flatnonzero(lolos[:-1])
        o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
        rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
        potong.append(pd.DataFrame({"ticker": t, "tgl": x.index[idx], "kotor": (o[idx + 1] / c[idx] - 1) * 100,
                                    "net": [bersih(c[i], o[i + 1], c[i] * rasio[i], o[i + 1] * rasio[i + 1]) for i in idx]}))
    return pd.concat(potong, ignore_index=True)


def persentil_bulanan(tr, q, n=2000, seed=7):
    g = tr.groupby(tr["tgl"].dt.to_period("M"))["net"].agg(["sum", "size"])
    idx = np.random.default_rng(seed).integers(0, len(g), (n, len(g)))
    rata = g["sum"].to_numpy()[idx].sum(1) / g["size"].to_numpy()[idx].sum(1)
    return np.percentile(rata, q)


def siapkan(periode):
    if periode == "dev":
        data = {t: v[v.index <= f"{DEV[1]}-12-31"] for t, v in sc.baca_harga().items()}
        data = {t: v for t, v in data.items() if len(v) >= 300}
        pasar = sc.baca_pasar(data)
        return {t: tambah_fitur(sc.fitur_ticker(v, pasar)) for t, v in data.items()}
    des = des_ojk.baca()
    data = sc.baca_harga(set(des["kode"]))
    pasar = sc.baca_pasar(data)
    siap = {}
    for t, v in data.items():
        v = v[v.index >= "2018-01-01"]
        if len(v) < 300:
            continue
        x = tambah_fitur(sc.fitur_ticker(v, pasar))
        syariah = pd.Series(False, index=x.index)
        for r in des[des["kode"] == t].itertuples():
            syariah |= (x.index >= r.mulai) & (x.index <= r.akhir)
        x["lolos"] = x["lolos"] & syariah
        siap[t] = x
    return siap


def jalankan(siap, periode, label, daftar):
    th_awal, th_akhir = periode
    mulai, akhir = pd.Timestamp(th_awal, 1, 1), pd.Timestamp(th_akhir, 12, 31)
    cagr_bm = benchmark(siap, mulai, akhir)
    print(f"\n##### {label}: CAGR beli-tahan semua saham universe (bobot sama, tanpa biaya): {cagr_bm:.1f}%")
    dasar_cache, ringkas = {}, []
    for nama in daftar:
        semua = []
        p = None
        for t, x in siap.items():
            s, keluar, n_maks, p = sinyal(nama, x)
            s = (s & x["lolos"]).fillna(False).to_numpy(bool)
            semua += simulasi_bsjp(x, t, s) if nama == "H19g" else simulasi(x, t, s, keluar, n_maks)
        tr = pd.DataFrame(semua)
        tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].copy() if not tr.empty else tr
        if tr.empty:
            print(f"\n{nama}: tidak ada trade")
            continue
        kunci = p or "bsjp"
        if kunci not in dasar_cache:
            b = pembanding_bsjp(siap) if nama == "H19g" else pembanding(siap, p)
            dasar_cache[kunci] = b[(b["tgl"] >= mulai) & (b["tgl"] <= akhir)]
        dt.simpan_hasil(f"trades_{nama}_{label.split()[0].lower()}", tr.reset_index(drop=True))
        menang, kalah = tr.loc[tr["net"] > 0, "net"], tr.loc[tr["net"] <= 0, "net"]
        pf = menang.sum() / -kalah.sum() if kalah.sum() < 0 else np.inf
        print(f"\nrata2 tahan {tr['hari'].mean():.1f} hari | alasan: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in tr["alasan"].value_counts(normalize=True).items())
              + f" | winrate {len(menang) / len(tr) * 100:.0f}% | rata2 untung {menang.mean():.2f}% vs rugi {kalah.mean():.2f}% "
              f"(rasio {menang.mean() / -kalah.mean():.2f}) | profit factor {pf:.2f}")
        ok, bln = evaluasi(tr, dasar_cache[kunci], f"{nama} {label}", maks=POSISI, kembalikan_bulanan=True)
        ok7 = bln.get("cagr", -np.inf) > cagr_bm
        p1 = persentil_bulanan(tr, 1)
        ok8 = p1 > 0
        print(f"  [{'LULUS' if ok7 else 'GAGAL'}] 7. CAGR portofolio > beli-tahan: {bln.get('cagr', np.nan):.1f}% vs {cagr_bm:.1f}%")
        print(f"  [{'LULUS' if ok8 else 'GAGAL'}] 8. bootstrap bulanan persentil 1 > 0: {p1:.2f}%")
        lulus = ok and ok7 and ok8
        print(f"  HASIL AKHIR {nama} {label}: {'LULUS' if lulus else 'GAGAL'}")
        ringkas.append({"hipotesis": nama, "trade": len(tr), "winrate": len(menang) / len(tr) * 100, "untung": menang.mean(), "rugi": kalah.mean(),
                        "exp": tr["net"].mean(), "pf": pf, "cagr": bln.get("cagr"), "dd": bln.get("dd"), "bulan_positif": bln.get("bulan_positif"),
                        "lulus": lulus})
    r = pd.DataFrame(ringkas)
    print(f"\n##### RINGKASAN {label} (beli-tahan {cagr_bm:.1f}%/th)")
    print(r.round(2).to_string(index=False))
    dt.simpan_hasil(f"ringkas_h19_{label.split()[0].lower()}", r)
    return r


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--hanya", nargs="*")
    a = ap.parse_args()
    semua = ["H19a", "H19b", "H19c", "H19d", "H19e", "H19f", "H19g"]
    if a.periode == "dev":
        jalankan(siapkan("dev"), DEV, "DEV 2010-2019 (217 saham)", semua)
        return
    if not a.hanya:
        raise SystemExit("holdout hanya untuk hipotesis yang lulus dev: sebutkan --hanya H19x")
    penanda = d.penanda("holdout_dibuka_h19")
    if penanda.exists():
        raise SystemExit(f"holdout H19 sudah pernah dibuka ({penanda.read_text().strip()})")
    penanda.write_text(f"{datetime.now():%Y-%m-%d %H:%M} {' '.join(a.hanya)}\n")
    jalankan(siapkan("holdout"), (HOLDOUT_MULAI, 2026), "HOLDOUT 2020+ (DES historis)", a.hanya)


if __name__ == "__main__":
    utama()
