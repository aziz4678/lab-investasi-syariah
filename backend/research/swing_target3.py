import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from backend.db import data as dt

KONFIG = {
    "file_ticker": "data/syariah_tickers.txt",
    "periode_data": "3y",
    "target_min_pct": 3.0,
    "mode_sl": "persen",
    "sl_pct": 2.0,
    "sl_mult_atr": 1.5,
    "sl_min_pct": 2.0,
    "sl_maks_pct": 8.0,
    "basis_sl": "intraday",
    "sl_darurat_pct": 8.0,
    "mode_entry": "open",
    "buffer_konfirmasi_pct": 0.1,
    "maks_hari_tahan": 7,
    "mult_trailing": 2.5,
    "fee_beli_pct": 0.15,
    "fee_jual_pct": 0.25,
    "gap_maks_pct": 2.0,
    "min_value_harian": 5_000_000_000,
    "min_atr_pct": 2.0,
    "min_skor": 4,
    "maks_posisi": 3,
    "risiko_per_trade_pct": 1.0,
    "pakai_regime": True,
    "top_n": 15,
    "horizon": 5,
}

NAMA_SYARAT = {
    "ok_tren": "tren (close>EMA20>EMA50)",
    "ok_breakout": "belum dekat high 20 hari",
    "ok_volume": "volume < 1.3x rata2",
    "ok_rsi": "RSI di luar 50-72",
    "ok_momentum": "momentum 5 hari < 2%",
}

VARIAN_SL = [
    ("persen", 2.0, "intraday"),
    ("persen", 3.0, "intraday"),
    ("persen", 4.0, "intraday"),
    ("atr", 1.5, "intraday"),
    ("atr", 2.0, "intraday"),
    ("persen", 3.0, "close"),
    ("atr", 1.5, "close"),
    ("atr", 2.0, "close"),
]


def baca_ticker(path):
    hasil = []
    sumber = Path(path).read_text().splitlines() if Path(path).exists() else dt.baca_daftar(Path(path).stem)
    for baris in sumber:
        t = baris.strip().upper()
        if not t or t.startswith("#"):
            continue
        hasil.append(t if t.endswith(".JK") else t + ".JK")
    return sorted(set(hasil))


def rapikan_index(df):
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    return df


def unduh_data(daftar, periode):
    mentah = yf.download(
        daftar, period=periode, interval="1d", auto_adjust=True,
        group_by="ticker", threads=True, progress=False,
    )
    hasil = {}
    for t in daftar:
        try:
            df = mentah[t].dropna(subset=["Open", "High", "Low", "Close"]).copy()
        except KeyError:
            continue
        df.columns = [c.lower() for c in df.columns]
        df = df[(df["close"] > 0) & (df["volume"] >= 0)]
        if len(df) < 120:
            continue
        hasil[t] = rapikan_index(df)
    return hasil


def ambil_ihsg(periode):
    try:
        ihsg = yf.download("^JKSE", period=periode, interval="1d", auto_adjust=True, progress=False)
    except Exception:
        return None
    if ihsg is None or ihsg.empty:
        return None
    if isinstance(ihsg.columns, pd.MultiIndex):
        ihsg.columns = ihsg.columns.get_level_values(0)
    return rapikan_index(ihsg)["Close"]


def bentuk_regime(ihsg):
    return ihsg > ihsg.ewm(span=50, adjust=False).mean()


def hitung_indikator(df):
    d = df.copy()
    d["ema20"] = d["close"].ewm(span=20, adjust=False).mean()
    d["ema50"] = d["close"].ewm(span=50, adjust=False).mean()

    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - d["close"].shift()).abs(),
        (d["low"] - d["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["atr_pct"] = d["atr"] / d["close"] * 100

    selisih = d["close"].diff()
    naik = selisih.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    turun = (-selisih.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["rsi"] = 100 - 100 / (1 + naik / turun.replace(0, np.nan))

    d["vol_rasio"] = d["volume"] / d["volume"].rolling(20).mean()
    d["value_rata"] = (d["close"] * d["volume"]).rolling(20).mean()
    d["high20"] = d["high"].rolling(20).max().shift(1)
    d["mom5"] = (d["close"] / d["close"].shift(5) - 1) * 100
    d["mom20"] = (d["close"] / d["close"].shift(20) - 1) * 100
    d["jarak_high20"] = (d["close"] / d["high20"] - 1) * 100
    d["jarak_ema20"] = (d["close"] / d["ema20"] - 1) * 100
    d["kontraksi"] = d["atr_pct"] / d["atr_pct"].rolling(60).mean()
    d["posisi_close"] = (d["close"] - d["low"]) / (d["high"] - d["low"]).replace(0, np.nan)
    return d


def beri_skor(d, k):
    d["ok_tren"] = (d["close"] > d["ema20"]) & (d["ema20"] > d["ema50"])
    d["ok_breakout"] = d["close"] >= d["high20"] * 0.99
    d["ok_volume"] = d["vol_rasio"] >= 1.3
    d["ok_rsi"] = d["rsi"].between(50, 72)
    d["ok_momentum"] = d["mom5"] > 2
    d["skor"] = d[list(NAMA_SYARAT)].sum(axis=1)
    d["lolos_likuid"] = (d["value_rata"] >= k["min_value_harian"]) & (d["atr_pct"] >= k["min_atr_pct"])
    return d


def siapkan(data, k):
    return {t: beri_skor(hitung_indikator(d0), k) for t, d0 in data.items()}


def jarak_sl_pct(atr, harga, k):
    if k["mode_sl"] == "atr":
        mentah = k["sl_mult_atr"] * atr / harga * 100
        return float(np.clip(mentah, k["sl_min_pct"], k["sl_maks_pct"]))
    return k["sl_pct"]


def simulasi_trade(d, i, k):
    n = len(d)
    if i + 1 >= n:
        return None

    o, h, l, c = d["open"].values, d["high"].values, d["low"].values, d["close"].values

    if k["mode_entry"] == "konfirmasi":
        level = h[i] * (1 + k["buffer_konfirmasi_pct"] / 100)
        if h[i + 1] < level:
            return None
        entry = max(o[i + 1], level)
    else:
        entry = o[i + 1]

    gap = (entry / c[i] - 1) * 100
    if gap > k["gap_maks_pct"]:
        return None

    atr = d["atr"].values[i]
    jarak = jarak_sl_pct(atr, entry, k)
    sl = entry * (1 - jarak / 100)
    darurat = entry * (1 - k["sl_darurat_pct"] / 100)
    stop = sl
    puncak = entry
    tinggi_maks = entry
    batas = i + k["maks_hari_tahan"]
    harga_keluar = None
    alasan = None

    for j in range(i + 1, min(batas, n - 1) + 1):
        tinggi_maks = max(tinggi_maks, h[j])
        if k["basis_sl"] == "close":
            if o[j] <= darurat:
                harga_keluar, alasan = o[j], "gap_darurat"
            elif l[j] <= darurat:
                harga_keluar, alasan = darurat, "darurat"
            elif c[j] <= stop:
                harga_keluar = c[j]
                alasan = "trailing" if stop > sl else "sl"
        else:
            if o[j] <= stop:
                harga_keluar, alasan = o[j], "gap_stop"
            elif l[j] <= stop:
                harga_keluar = stop
                alasan = "trailing" if stop > sl else "sl"
        if harga_keluar is not None:
            break
        puncak = max(puncak, h[j])
        stop = max(stop, puncak - k["mult_trailing"] * atr)

    if harga_keluar is None:
        if batas > n - 1:
            return None
        harga_keluar, alasan = c[batas], "waktu"
        j = batas

    ret = (harga_keluar * (1 - k["fee_jual_pct"] / 100)) / (entry * (1 + k["fee_beli_pct"] / 100)) - 1
    return {
        "tgl_sinyal": d.index[i],
        "tgl_entry": d.index[i + 1],
        "tgl_exit": d.index[j],
        "skor": d["skor"].values[i],
        "gap_pct": round(gap, 2),
        "entry": round(entry, 2),
        "exit": round(harga_keluar, 2),
        "sl_pct": round(jarak, 2),
        "hari": j - i,
        "mfe_pct": round((tinggi_maks / entry - 1) * 100, 2),
        "ret_bersih_pct": round(ret * 100, 2),
        "alasan_exit": alasan,
    }


def buat_sinyal(d, regime, k, mode, kolom=None):
    if mode == "baseline":
        s = d["lolos_likuid"].copy()
    elif mode == "skor":
        s = d["lolos_likuid"] & (d["skor"] >= k["min_skor"])
    elif mode == "penuh":
        s = d["lolos_likuid"] & (d["skor"] == len(NAMA_SYARAT))
    elif mode == "sendiri":
        s = d["lolos_likuid"] & d[kolom]
    else:
        lain = [x for x in NAMA_SYARAT if x != kolom]
        s = d["lolos_likuid"] & d[lain].all(axis=1)

    if regime is not None and k["pakai_regime"]:
        s = s & regime.reindex(d.index).fillna(False)
    return s


def backtest_ticker(t, d, regime, k, mode, kolom=None):
    sinyal = buat_sinyal(d, regime, k, mode, kolom)
    hasil = []
    bebas_dari = 0
    for i in np.flatnonzero(sinyal.values):
        if i < bebas_dari:
            continue
        tr = simulasi_trade(d, i, k)
        if tr is None:
            continue
        tr["ticker"] = t
        hasil.append(tr)
        bebas_dari = i + tr["hari"]
    return hasil


def kumpulkan(siap, regime, k, mode, kolom=None):
    semua = []
    for t, d in siap.items():
        semua += backtest_ticker(t, d, regime, k, mode, kolom)
    return pd.DataFrame(semua)


def batasi_posisi(tr, maks):
    urut = tr.sort_values(["tgl_entry", "skor"], ascending=[True, False])
    terisi, lolos = [], []
    for idx, baris in urut.iterrows():
        terisi = [x for x in terisi if x >= baris["tgl_entry"]]
        if len(terisi) >= maks:
            continue
        terisi.append(baris["tgl_exit"])
        lolos.append(idx)
    return tr.loc[lolos].sort_values("tgl_entry").reset_index(drop=True)


def tentukan_batas(siap, uji_mulai):
    if uji_mulai:
        return pd.Timestamp(uji_mulai)
    awal = min(d.index[0] for d in siap.values())
    akhir = max(d.index[-1] for d in siap.values())
    return (awal + (akhir - awal) * 0.7).normalize()


def statistik(tr, k):
    if tr is None or tr.empty:
        return None
    t = k["target_min_pct"]
    r = tr["ret_bersih_pct"]
    menang, kalah = r[r > 0], r[r <= 0]
    pf = menang.sum() / abs(kalah.sum()) if kalah.sum() != 0 else float("inf")
    return {
        "n": len(tr),
        "hit_pot": (tr["mfe_pct"] >= t).mean() * 100,
        "hit_real": (r >= t).mean() * 100,
        "win": (r > 0).mean() * 100,
        "exp": r.mean(),
        "exp_R": (r / tr["sl_pct"]).mean(),
        "rata_menang": menang.mean() if len(menang) else 0.0,
        "rata_kalah": kalah.mean() if len(kalah) else 0.0,
        "pf": pf,
        "hari": tr["hari"].mean(),
    }


def kurva_ekuitas(tr, k):
    ekuitas, puncak, dd_maks = 1.0, 1.0, 0.0
    for _, b in tr.sort_values("tgl_exit").iterrows():
        bobot = min(1 / k["maks_posisi"], k["risiko_per_trade_pct"] / b["sl_pct"])
        ekuitas *= 1 + bobot * b["ret_bersih_pct"] / 100
        puncak = max(puncak, ekuitas)
        dd_maks = min(dd_maks, ekuitas / puncak - 1)
    return ekuitas, dd_maks * 100


def ringkas(tr, judul, k):
    print(f"\n=== {judul} ===")
    s = statistik(tr, k)
    if s is None:
        print("tidak ada trade")
        return
    t = k["target_min_pct"]
    print(f"jumlah trade            : {s['n']}")
    print(f"hit potensi (MFE>={t:g}%)  : {s['hit_pot']:.1f}%")
    print(f"hit realisasi (net>={t:g}%) : {s['hit_real']:.1f}%")
    print(f"win rate (net>0)        : {s['win']:.1f}%")
    print(f"expectancy / trade      : {s['exp']:.2f}%  ({s['exp_R']:.2f}R)")
    print(f"rata2 menang / kalah    : {s['rata_menang']:.2f}% / {s['rata_kalah']:.2f}%")
    print(f"profit factor           : {s['pf']:.2f}")
    print(f"rata2 hari tahan        : {s['hari']:.1f}")


def ringkas_detail(tr):
    print("\n--- alasan exit ---")
    print(tr["alasan_exit"].value_counts().to_string())

    kelompok = pd.cut(tr["hari"], bins=[0, 1, 3, 7, 14, 999], labels=["1", "2-3", "4-7", "8-14", "15+"])
    tabel = tr.groupby(kelompok, observed=True)["ret_bersih_pct"].agg(["count", "mean"]).round(2)
    print("\n--- hari tahan vs return ---")
    print(tabel.to_string())

    urut = tr["ret_bersih_pct"].sort_values(ascending=False)
    total_pos = urut[urut > 0].sum()
    sepuluh = urut.head(10).sum()
    sisa = (tr["ret_bersih_pct"].sum() - sepuluh) / max(len(tr) - 10, 1)
    print(f"\n10 trade terbaik nyumbang {sepuluh:.0f} dari total untung {total_pos:.0f}; expectancy tanpa 10 terbaik {sisa:.2f}%")


def jalankan_backtest(siap, regime, k, uji_mulai):
    tr = kumpulkan(siap, regime, k, "skor")
    dasar = kumpulkan(siap, regime, k, "baseline")
    if tr.empty:
        print("tidak ada sinyal sama sekali, longgarkan filter")
        return

    tr = batasi_posisi(tr, k["maks_posisi"])
    dt.simpan_hasil("trades_swing", tr.reset_index(drop=True))

    print(f"setelan: SL {k['mode_sl']} "
          f"({k['sl_pct'] if k['mode_sl'] == 'persen' else str(k['sl_mult_atr']) + 'x ATR'}) basis {k['basis_sl']} | "
          f"entry {k['mode_entry']} | maks hari {k['maks_hari_tahan']}")
    ringkas(dasar, "BASELINE (semua hari lolos likuiditas, tanpa skor)", k)
    ringkas(tr, f"SINYAL skor>={k['min_skor']} (maks {k['maks_posisi']} posisi)", k)

    batas = tentukan_batas(siap, uji_mulai)
    ringkas(tr[tr["tgl_entry"] < batas], f"IN-SAMPLE (< {batas.date()})", k)
    ringkas(tr[tr["tgl_entry"] >= batas], f"OUT-OF-SAMPLE (>= {batas.date()})", k)

    ringkas_detail(tr)
    eks, dd = kurva_ekuitas(tr, k)
    print(f"\nekuitas akhir (risiko {k['risiko_per_trade_pct']:g}% per trade, maks 1/{k['maks_posisi']} modal per posisi): "
          f"{eks:.3f}x | max drawdown {dd:.1f}%")
    print("trade lengkap disimpan ke trades_swing.csv")


def baris_ringkas(tr, k, batas, label, entry):
    s = statistik(tr, k)
    ins = statistik(tr[tr["tgl_entry"] < batas], k)
    oos = statistik(tr[tr["tgl_entry"] >= batas], k)
    eks, dd = kurva_ekuitas(tr, k)
    return {
        "varian": label,
        "entry": entry,
        "n": s["n"],
        "hit_real": round(s["hit_real"], 1),
        "win": round(s["win"], 1),
        "exp": round(s["exp"], 2),
        "exp_R": round(s["exp_R"], 3),
        "pf": round(s["pf"], 2),
        "IS_R": round(ins["exp_R"], 3) if ins else np.nan,
        "OOS_n": oos["n"] if oos else 0,
        "OOS_R": round(oos["exp_R"], 3) if oos else np.nan,
        "ekuitas": round(eks, 2),
        "dd%": round(dd, 1),
    }


def jalankan_bandingkan(siap, regime, k, uji_mulai):
    batas = tentukan_batas(siap, uji_mulai)
    baris = []
    for mode_sl, angka, basis in VARIAN_SL:
        for mode_entry in ("open", "konfirmasi"):
            k2 = dict(k, mode_sl=mode_sl, basis_sl=basis, mode_entry=mode_entry)
            k2["sl_pct" if mode_sl == "persen" else "sl_mult_atr"] = angka
            tr = kumpulkan(siap, regime, k2, "skor")
            if tr.empty:
                continue
            tr = batasi_posisi(tr, k2["maks_posisi"])
            satuan = "%" if mode_sl == "persen" else "xATR"
            label = f"SL {angka:g}{satuan}/{basis}"
            baris.append(baris_ringkas(tr, k2, batas, label, mode_entry))
            print(f"selesai: {label} + {mode_entry}", flush=True)

    hasil = pd.DataFrame(baris).sort_values("IS_R", ascending=False)
    dt.simpan_hasil("bandingkan_swing", hasil.reset_index(drop=True))
    print(f"\nbatas in-sample / out-of-sample: {batas.date()} | diurutkan berdasarkan IS_R (R = return dibagi jarak SL)")
    print(hasil.to_string(index=False))
    print("\nPilih berdasarkan IS_R, lalu cek OOS_R. Jangan pilih yang OOS_R-nya paling bagus, itu sama aja ngintip data uji.")
    print("hasil disimpan ke bandingkan_swing.csv")


def jalankan_ablasi(siap, regime, k, uji_mulai):
    batas = tentukan_batas(siap, uji_mulai)
    daftar = [("baseline (tanpa skor)", "baseline", None),
              (f"skor >= {k['min_skor']}", "skor", None),
              (f"skor == {len(NAMA_SYARAT)} (semua)", "penuh", None)]
    daftar += [(f"hanya {kol[3:]}", "sendiri", kol) for kol in NAMA_SYARAT]
    daftar += [(f"semua kecuali {kol[3:]}", "tanpa", kol) for kol in NAMA_SYARAT]

    baris = []
    for nama, mode, kol in daftar:
        tr = kumpulkan(siap, regime, k, mode, kol)
        if tr.empty:
            continue
        s = statistik(tr, k)
        ins = statistik(tr[tr["tgl_entry"] < batas], k)
        oos = statistik(tr[tr["tgl_entry"] >= batas], k)
        baris.append({
            "varian": nama,
            "n": s["n"],
            "hit_real": round(s["hit_real"], 1),
            "win": round(s["win"], 1),
            "exp": round(s["exp"], 2),
            "exp_R": round(s["exp_R"], 3),
            "pf": round(s["pf"], 2),
            "IS_R": round(ins["exp_R"], 3) if ins else np.nan,
            "OOS_n": oos["n"] if oos else 0,
            "OOS_R": round(oos["exp_R"], 3) if oos else np.nan,
        })

    hasil = pd.DataFrame(baris)
    dt.simpan_hasil("ablasi_swing", hasil.reset_index(drop=True))
    print(f"batas in-sample / out-of-sample: {batas.date()} | tanpa batas posisi, non-overlap per ticker")
    print(hasil.to_string(index=False))
    print("\nBaca: kalau 'semua kecuali X' lebih bagus dari 'skor == 5', X justru merusak. "
          "Kalau 'hanya X' nggak beda dari baseline, X nggak nyumbang apa-apa.")
    print("hasil disimpan ke ablasi_swing.csv")


def jalankan_pindai(siap, regime, k):
    regime_ok = True if regime is None else bool(regime.iloc[-1])
    baris = []
    for t, d in siap.items():
        b = d.iloc[-1]
        gagal = [NAMA_SYARAT[x] for x in NAMA_SYARAT if not b[x]]
        if not b["lolos_likuid"]:
            gagal.append("likuiditas/ATR kurang")
        if k["pakai_regime"] and not regime_ok:
            gagal.append("IHSG di bawah EMA50")

        sinyal = b["skor"] >= k["min_skor"] and b["lolos_likuid"] and (regime_ok or not k["pakai_regime"])
        close = b["close"]
        if k["mode_entry"] == "konfirmasi":
            acuan = b["high"] * (1 + k["buffer_konfirmasi_pct"] / 100)
        else:
            acuan = close
        jarak = jarak_sl_pct(b["atr"], acuan, k)
        baris.append({
            "ticker": t,
            "tanggal": d.index[-1].date(),
            "close": round(close, 2),
            "skor": int(b["skor"]),
            "sinyal": bool(sinyal),
            "atr_pct": round(b["atr_pct"], 2),
            "vol_rasio": round(b["vol_rasio"], 2),
            "rsi": round(b["rsi"], 1),
            "acuan_entry": round(acuan, 2),
            "sl": round(acuan * (1 - jarak / 100), 2),
            "sl_pct": round(jarak, 2),
            "target_net": round(
                acuan * (1 + k["target_min_pct"] / 100)
                * (1 + k["fee_beli_pct"] / 100) / (1 - k["fee_jual_pct"] / 100), 2),
            "alasan_gagal": "; ".join(gagal),
        })

    hasil = pd.DataFrame(baris).sort_values(["sinyal", "skor", "vol_rasio"], ascending=False)
    dt.simpan_hasil("kandidat_swing", hasil.reset_index(drop=True))

    print(f"regime IHSG: {'OK' if regime_ok else 'LEMAH'} | sinyal lolos: {int(hasil['sinyal'].sum())} dari {len(hasil)} ticker")
    print(hasil.head(k["top_n"]).to_string(index=False))
    print("\nsemua ticker disimpan ke kandidat_swing.csv")
    if k["mode_entry"] == "konfirmasi":
        print("entry: pasang buy stop di acuan_entry, batal kalau besok nggak kesentuh")
    else:
        print(f"entry: open besok, skip kalau gap naik > {k['gap_maks_pct']:g}%")


FITUR = {
    "mom5": "momentum 5 hari (%)",
    "mom20": "momentum 20 hari (%)",
    "rsi": "RSI 14",
    "jarak_high20": "jarak ke high 20 hari (%)",
    "vol_rasio": "volume / rata2 20 hari",
    "jarak_ema20": "jarak ke EMA20 (%)",
    "atr_pct": "ATR % (volatilitas)",
    "kontraksi": "ATR sekarang / rata2 60 hari",
    "posisi_close": "posisi close di range harian",
}


def bangun_panel(siap, regime, k, horizon):
    potongan = []
    langsung = list(FITUR)
    for t, d in siap.items():
        p = d[["lolos_likuid"] + langsung].copy()
        entry = d["open"].shift(-1)
        keluar = d["close"].shift(-horizon)
        tertinggi = d["high"].rolling(horizon).max().shift(-horizon)
        p["fwd"] = ((keluar * (1 - k["fee_jual_pct"] / 100)) / (entry * (1 + k["fee_beli_pct"] / 100)) - 1) * 100
        p["mfe"] = (tertinggi / entry - 1) * 100
        p["regime_ok"] = regime.reindex(d.index).fillna(False) if regime is not None else True
        p["ticker"] = t
        potongan.append(p)

    panel = pd.concat(potongan)
    panel.index.name = "tgl"
    panel = panel[panel["lolos_likuid"]].dropna(subset=["fwd"])
    return panel.reset_index()


def analisis_fitur(panel, nama, k, horizon, batas):
    sub = panel.dropna(subset=[nama])
    jml = sub.groupby("tgl")["fwd"].transform("size")
    sub = sub[jml >= 30]
    if len(sub) < 3000:
        return None

    target = k["target_min_pct"]
    tgl = sub["tgl"]
    rf = sub.groupby("tgl")[nama].rank()
    ry = sub.groupby("tgl")["fwd"].rank()
    rf = rf - rf.groupby(tgl).transform("mean")
    ry = ry - ry.groupby(tgl).transform("mean")
    pembilang = (rf * ry).groupby(tgl).sum()
    penyebut = np.sqrt((rf ** 2).groupby(tgl).sum() * (ry ** 2).groupby(tgl).sum())
    ic = (pembilang / penyebut).dropna()

    sampel = ic.iloc[::horizon]
    if len(sampel) > 2 and sampel.std() > 0:
        t_stat = sampel.mean() / sampel.std() * np.sqrt(len(sampel))
    else:
        t_stat = np.nan

    pct = sub.groupby("tgl")[nama].rank(pct=True)
    desil = np.minimum((pct * 10).astype(int), 9) + 1
    tabel = sub.groupby(desil).agg(
        n=("fwd", "size"),
        ret=("fwd", "mean"),
        hit_pot=("mfe", lambda x: (x >= target).mean() * 100),
        hit_close=("fwd", lambda x: (x >= target).mean() * 100),
    )
    ic_is = ic[ic.index < batas].mean()
    ic_oos = ic[ic.index >= batas].mean()
    arah = np.sign(ic.mean())
    konsisten = abs(t_stat) >= 3 and np.sign(ic_is) == arah and np.sign(ic_oos) == arah
    return {
        "fitur": nama,
        "n": len(sub),
        "IC": ic.mean(),
        "t": t_stat,
        "IC_IS": ic_is,
        "IC_OOS": ic_oos,
        "D1": tabel.loc[1, "ret"],
        "D10": tabel.loc[10, "ret"],
        "spread": tabel.loc[10, "ret"] - tabel.loc[1, "ret"],
        "lolos": "YA" if konsisten else "-",
        "_ic": ic,
        "_tabel": tabel,
    }


def jalankan_desil(siap, ihsg, k, horizon, uji_mulai):
    regime = bentuk_regime(ihsg) if ihsg is not None else None
    panel = bangun_panel(siap, regime, k, horizon)
    batas = tentukan_batas(siap, uji_mulai)
    target = k["target_min_pct"]

    kelompok = {"semua hari": panel}
    if regime is not None:
        kelompok["regime OK"] = panel[panel["regime_ok"]]

    print(f"horizon {horizon} hari bursa (entry open besok, exit close hari ke-{horizon}), return net fee, "
          f"hanya ticker lolos likuiditas | batas IS/OOS {batas.date()}")
    semua = []
    for nama_kel, p in kelompok.items():
        print(f"\n##### {nama_kel}: {len(p)} observasi, {p['tgl'].nunique()} hari")
        print(f"rata2 return semua observasi {p['fwd'].mean():.2f}% | "
              f"hit potensi >={target:g}%: {(p['mfe'] >= target).mean() * 100:.1f}% | "
              f"hit close >={target:g}%: {(p['fwd'] >= target).mean() * 100:.1f}%")
        baris = []
        for f in FITUR:
            r = analisis_fitur(p, f, k, horizon, batas)
            if r is None:
                continue
            r["subset"] = nama_kel
            baris.append(r)
        if not baris:
            print("data nggak cukup")
            continue
        tabel = pd.DataFrame(baris)
        tabel["abs_t"] = tabel["t"].abs()
        tabel = tabel.sort_values("abs_t", ascending=False)
        tampil = tabel[["fitur", "n", "IC", "t", "IC_IS", "IC_OOS", "D1", "D10", "spread", "lolos"]].copy()
        for kol in ["IC", "IC_IS", "IC_OOS"]:
            tampil[kol] = tampil[kol].round(4)
        for kol in ["t", "D1", "D10", "spread"]:
            tampil[kol] = tampil[kol].round(2)
        print(tampil.to_string(index=False))
        semua += baris

    if not semua:
        return

    ringkas_csv = pd.DataFrame([{x: v for x, v in b.items() if not x.startswith("_")} for b in semua])
    dt.simpan_hasil("desil_swing", ringkas_csv.reset_index(drop=True))

    urut = sorted(semua, key=lambda b: abs(b["t"]) if pd.notna(b["t"]) else 0, reverse=True)[:2]
    for b in urut:
        print(f"\n--- detail {b['fitur']} ({b['subset']}): return net per desil (D1 = nilai fitur terendah) ---")
        tb = b["_tabel"].copy()
        tb[["ret", "hit_pot", "hit_close"]] = tb[["ret", "hit_pot", "hit_close"]].round(2)
        print(tb.to_string())
        per_tahun = b["_ic"].groupby(b["_ic"].index.year).mean().round(4)
        print("IC per tahun: " + " | ".join(f"{th}: {v}" for th, v in per_tahun.items()))

    uji = len(semua)
    print(f"\nada {uji} uji (fitur x kelompok). 'lolos' = |t| >= 3 dan arah IC sama di in-sample dan out-of-sample. "
          "IC rata2 di bawah sekitar 0.02 praktis nggak bisa dipakai walau t-nya besar; "
          "D10-D1 harus lebih besar dari selisih fee yang sudah dihitung.")
    print("hasil disimpan ke desil_swing.csv")


HIPOTESIS_FITUR = ["mom20", "rsi", "jarak_ema20"]
HIPOTESIS_HORIZON = [3, 5, 7]
HIPOTESIS_UTAMA = 5


def bangun_komposit(siap, regime):
    potongan = []
    for t, d in siap.items():
        p = d[["lolos_likuid"] + HIPOTESIS_FITUR].copy()
        p["ticker"] = t
        potongan.append(p)
    panel = pd.concat(potongan)
    panel.index.name = "tgl"
    panel = panel[panel["lolos_likuid"]].dropna(subset=HIPOTESIS_FITUR).reset_index()
    jml = panel.groupby("tgl")["ticker"].transform("size")
    panel = panel[jml >= 30].copy()
    for f in HIPOTESIS_FITUR:
        panel["r_" + f] = panel.groupby("tgl")[f].rank(pct=True)
    panel["komposit"] = panel[["r_" + f for f in HIPOTESIS_FITUR]].mean(axis=1)
    panel["komposit_pct"] = panel.groupby("tgl")["komposit"].rank(pct=True)
    panel["top"] = panel["komposit_pct"] >= 0.9
    panel["regime_ok"] = regime.reindex(panel["tgl"]).fillna(False).values
    return panel


def simulasikan_pool(siap, pool, k):
    baris = []
    for t, g in pool.groupby("ticker"):
        d = siap[t]
        posisi = d.index.get_indexer(g["tgl"])
        for i, kp, top in zip(posisi, g["komposit_pct"].values, g["top"].values):
            if i < 0:
                continue
            tr = simulasi_trade(d, i, k)
            if tr is None:
                continue
            tr["ticker"] = t
            tr["komposit_pct"] = kp
            tr["top"] = bool(top)
            baris.append(tr)
    hasil = pd.DataFrame(baris)
    hasil["R"] = hasil["ret_bersih_pct"] / hasil["sl_pct"]
    return hasil


def uji_permutasi(tr, langkah, n_perm, seed=7):
    tgl_unik = np.sort(tr["tgl_sinyal"].unique())
    s = tr[tr["tgl_sinyal"].isin(tgl_unik[::langkah])]
    sinyal = s[s["top"]]
    if len(sinyal) < 30:
        return None
    n_target = sinyal.groupby("tgl_sinyal").size()
    kolam = s[s["tgl_sinyal"].isin(n_target.index)].reset_index(drop=True)
    kode = pd.factorize(kolam["tgl_sinyal"])[0]
    target = n_target.reindex(kolam["tgl_sinyal"]).values
    nilai_r = kolam["R"].values
    nilai_ret = kolam["ret_bersih_pct"].values

    rng = np.random.default_rng(seed)
    acak_r, acak_ret = [], []
    for _ in range(n_perm):
        urutan = pd.Series(rng.random(len(kolam))).groupby(kode).rank(method="first").values
        pilih = urutan <= target
        acak_r.append(nilai_r[pilih].mean())
        acak_ret.append(nilai_ret[pilih].mean())
    acak_r, acak_ret = np.array(acak_r), np.array(acak_ret)
    asli_r, asli_ret = sinyal["R"].mean(), sinyal["ret_bersih_pct"].mean()
    return {
        "n": len(sinyal),
        "R_asli": asli_r,
        "R_acak": acak_r.mean(),
        "p_R": (np.sum(acak_r >= asli_r) + 1) / (n_perm + 1),
        "p_ret": (np.sum(acak_ret >= asli_ret) + 1) / (n_perm + 1),
    }


def tanpa_tumpang_tindih(tr):
    lolos = []
    for _, g in tr.sort_values("tgl_sinyal").groupby("ticker"):
        bebas = pd.Timestamp.min
        for idx, b in g.iterrows():
            if b["tgl_sinyal"] < bebas:
                continue
            lolos.append(idx)
            bebas = b["tgl_exit"]
    return tr.loc[lolos]


def selisih_r(sin, dasar):
    a, b = statistik(sin, KONFIG), statistik(dasar, KONFIG)
    if a is None or b is None:
        return np.nan
    return a["exp_R"] - b["exp_R"]


def jalankan_hipotesis(siap, ihsg, k, uji_mulai, n_perm):
    if ihsg is None:
        print("data IHSG dibutuhkan buat uji ini")
        return
    if k["mode_sl"] == "persen":
        k = dict(k, mode_sl="atr", sl_mult_atr=1.5)
    k = dict(k, basis_sl="intraday", mode_entry="open")

    regime = bentuk_regime(ihsg)
    panel = bangun_komposit(siap, regime)
    pool = panel[panel["regime_ok"]]
    batas = tentukan_batas(siap, uji_mulai)
    print("HIPOTESIS (ditetapkan sebelum dijalankan):")
    print("  beli saham dengan skor komposit kekuatan tren di desil teratas "
          f"(rata2 peringkat harian {', '.join(HIPOTESIS_FITUR)}) HANYA saat regime IHSG OK")
    print(f"  exit: SL {k['sl_mult_atr']:g}xATR intraday, trailing {k['mult_trailing']:g}xATR, paksa keluar di hari ke-H; "
          f"entry open besok; fee {k['fee_beli_pct']}%/{k['fee_jual_pct']}%")
    print(f"  pembanding: semua ticker lolos likuiditas pada hari regime OK ({len(pool)} ticker-hari) | batas IS/OOS {batas.date()}")

    hasil, ringkasan, perm_utama = {}, [], None
    for H in HIPOTESIS_HORIZON:
        print(f"\nmenyimulasikan horizon {H} hari...", flush=True)
        k2 = dict(k, maks_hari_tahan=H)
        tr = simulasikan_pool(siap, pool, k2)
        hasil[H] = tr
        sin = tr[tr["top"]]
        s_sin, s_dasar = statistik(sin, k2), statistik(tr, k2)
        perm = uji_permutasi(tr, H, n_perm)
        is_s, is_d = sin["tgl_entry"] < batas, tr["tgl_entry"] < batas
        d_is = selisih_r(sin[is_s], tr[is_d])
        d_oos = selisih_r(sin[~is_s], tr[~is_d])
        ringkasan.append({
            "H": H,
            "n_sinyal": s_sin["n"],
            "hit_real_sinyal": round(s_sin["hit_real"], 1),
            "hit_real_dasar": round(s_dasar["hit_real"], 1),
            "exp_sinyal": round(s_sin["exp"], 2),
            "exp_dasar": round(s_dasar["exp"], 2),
            "pf_sinyal": round(s_sin["pf"], 2),
            "R_sinyal": round(s_sin["exp_R"], 3),
            "R_dasar": round(s_dasar["exp_R"], 3),
            "delta_R": round(s_sin["exp_R"] - s_dasar["exp_R"], 3),
            "delta_R_IS": round(d_is, 3),
            "delta_R_OOS": round(d_oos, 3),
            "p_permutasi_R": round(perm["p_R"], 4) if perm else np.nan,
            "p_permutasi_ret": round(perm["p_ret"], 4) if perm else np.nan,
        })

    tabel = pd.DataFrame(ringkasan)
    dt.simpan_hasil("hipotesis_swing", tabel.reset_index(drop=True))
    print("\n=== HASIL PER HORIZON (sinyal = desil teratas komposit, dasar = semua kandidat regime OK) ===")
    print(tabel.to_string(index=False))
    print("p_permutasi: peluang pilihan acak (jumlah sama per hari) dapat hasil sama baik; dihitung di tanggal non-overlap (tiap H hari).")

    H = HIPOTESIS_UTAMA
    tr = hasil[H]
    sin = tr[tr["top"]]
    tahun = pd.DataFrame({
        "n_sinyal": sin.groupby(sin["tgl_entry"].dt.year).size(),
        "R_sinyal": sin.groupby(sin["tgl_entry"].dt.year)["R"].mean(),
        "R_dasar": tr.groupby(tr["tgl_entry"].dt.year)["R"].mean(),
    })
    tahun["delta_R"] = tahun["R_sinyal"] - tahun["R_dasar"]
    print(f"\n--- per tahun (horizon {H}) ---")
    print(tahun.round(3).to_string())

    utama = tabel[tabel["H"] == H].iloc[0]
    sah = tahun[tahun["n_sinyal"] >= 20]
    thn_positif = (sah["delta_R"] > 0).mean() if len(sah) else 0
    lainnya = tabel[tabel["H"] != H]
    kriteria = [
        (f"K1 delta_R > 0 dan p permutasi < 0.0167 (horizon {H})",
         utama["delta_R"] > 0 and utama["p_permutasi_R"] < 0.0167),
        ("K2 expectancy net >= +0.30% per trade dan PF >= 1.15",
         utama["exp_sinyal"] >= 0.30 and utama["pf_sinyal"] >= 1.15),
        ("K3 delta_R positif di in-sample dan out-of-sample",
         utama["delta_R_IS"] > 0 and utama["delta_R_OOS"] > 0),
        (f"K4 delta_R positif di >= 70% tahun (n>=20), minimal 5 tahun ({len(sah)} tahun valid)",
         len(sah) >= 5 and thn_positif >= 0.7),
        ("K5 horizon lain: delta_R > 0 dan expectancy net > 0",
         bool(((lainnya["delta_R"] > 0) & (lainnya["exp_sinyal"] > 0)).all())),
    ]
    print("\n=== KRITERIA (ditetapkan sebelum dijalankan; semua harus lolos) ===")
    for nama, ok in kriteria:
        print(f"[{'LOLOS' if ok else 'GAGAL'}] {nama}")
    semua_lolos = all(ok for _, ok in kriteria)
    print("\nKESIMPULAN: " + ("semua kriteria lolos, lanjut ke paper trade, bukan ke duit beneran."
                               if semua_lolos else "hipotesis TIDAK lolos, jangan dipakai."))

    nyata = tanpa_tumpang_tindih(sin)
    nyata = nyata.assign(skor=nyata["komposit_pct"])
    nyata = batasi_posisi(nyata, k["maks_posisi"])
    dt.simpan_hasil("trades_hipotesis", nyata.reset_index(drop=True))
    k5 = dict(k, maks_hari_tahan=H)
    ringkas(nyata, f"SIMULASI REALISTIS horizon {H} (non-overlap per ticker, maks {k['maks_posisi']} posisi)", k5)
    batas_is = nyata["tgl_entry"] < batas
    ringkas(nyata[batas_is], "  in-sample", k5)
    ringkas(nyata[~batas_is], "  out-of-sample", k5)
    eks, dd = kurva_ekuitas(nyata, k5)
    print(f"\nekuitas akhir: {eks:.3f}x | max drawdown {dd:.1f}%")
    print("trade realistis disimpan ke trades_hipotesis.csv, ringkasan ke hipotesis_swing.csv")


def utama():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["backtest", "pindai", "bandingkan", "ablasi", "desil", "hipotesis"])
    p.add_argument("--ticker-file")
    p.add_argument("--periode")
    p.add_argument("--sl", type=float)
    p.add_argument("--sl-atr", type=float)
    p.add_argument("--basis-sl", choices=["intraday", "close"])
    p.add_argument("--entry", choices=["open", "konfirmasi"])
    p.add_argument("--target", type=float)
    p.add_argument("--maks-hari", type=int)
    p.add_argument("--trailing", type=float)
    p.add_argument("--min-skor", type=int)
    p.add_argument("--maks-posisi", type=int)
    p.add_argument("--top", type=int)
    p.add_argument("--horizon", type=int)
    p.add_argument("--permutasi", type=int, default=500)
    p.add_argument("--uji-mulai")
    p.add_argument("--tanpa-regime", action="store_true")
    a = p.parse_args()

    k = dict(KONFIG)
    if a.ticker_file: k["file_ticker"] = a.ticker_file
    if a.periode: k["periode_data"] = a.periode
    if a.sl:
        k["sl_pct"] = a.sl
        k["mode_sl"] = "persen"
    if a.sl_atr:
        k["sl_mult_atr"] = a.sl_atr
        k["mode_sl"] = "atr"
    if a.basis_sl: k["basis_sl"] = a.basis_sl
    if a.entry: k["mode_entry"] = a.entry
    if a.target: k["target_min_pct"] = a.target
    if a.maks_hari: k["maks_hari_tahan"] = a.maks_hari
    if a.trailing: k["mult_trailing"] = a.trailing
    if a.min_skor: k["min_skor"] = a.min_skor
    if a.maks_posisi: k["maks_posisi"] = a.maks_posisi
    if a.top: k["top_n"] = a.top
    if a.horizon: k["horizon"] = a.horizon
    if a.tanpa_regime: k["pakai_regime"] = False

    daftar = baca_ticker(k["file_ticker"])
    print(f"{len(daftar)} ticker dibaca, mengunduh data...")
    data = unduh_data(daftar, k["periode_data"])
    print(f"{len(data)} ticker punya data cukup")

    butuh_ihsg = k["pakai_regime"] or a.mode in ("desil", "hipotesis")
    ihsg = ambil_ihsg(k["periode_data"]) if butuh_ihsg else None
    if ihsg is None and butuh_ihsg:
        print("peringatan: data IHSG gagal diambil, filter regime dimatikan")
    regime = bentuk_regime(ihsg) if (ihsg is not None and k["pakai_regime"]) else None

    siap = siapkan(data, k)
    if a.mode == "hipotesis":
        jalankan_hipotesis(siap, ihsg, k, a.uji_mulai, a.permutasi)
    elif a.mode == "desil":
        jalankan_desil(siap, ihsg, k, k["horizon"], a.uji_mulai)
    elif a.mode == "backtest":
        jalankan_backtest(siap, regime, k, a.uji_mulai)
    elif a.mode == "bandingkan":
        jalankan_bandingkan(siap, regime, k, a.uji_mulai)
    elif a.mode == "ablasi":
        jalankan_ablasi(siap, regime, k, a.uji_mulai)
    else:
        jalankan_pindai(siap, regime, k)


if __name__ == "__main__":
    utama()