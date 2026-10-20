import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.db import data as dt
from backend.riset import swing_target3 as s
from backend.riset.laporan_bulanan import ringkas_bulanan
from backend.db import koneksi as d

TP = 3.0
SL = 3.0
MAKS_HARI = 60
FEE_BELI = 0.15
FEE_JUAL = 0.25
MIN_VALUE = 5e9
ATR_MIN = 1.5
ATR_MAKS = 5.0
HARGA_MIN = 50
MIN_SAHAM_HARI = 20
TAHUN_LATIH_MIN = 4
DEV = (2015, 2021)
HOLDOUT_MULAI = 2022

FITUR_SAHAM = ["mom5", "mom20", "mom60", "jarak_ema20", "jarak_ema50", "rsi", "atr_pct", "kontraksi",
               "vol_rasio", "jarak_high20", "posisi_close", "rs20", "log_value"]
FITUR_PASAR = ["ihsg_atas", "ihsg_mom20", "breadth"]
NAMA_FITUR = {
    "mom5": "momentum 5h", "mom20": "momentum 20h", "mom60": "momentum 60h",
    "jarak_ema20": "jarak EMA20", "jarak_ema50": "jarak EMA50", "rsi": "RSI",
    "atr_pct": "volatilitas", "kontraksi": "kontraksi ATR", "vol_rasio": "lonjakan volume",
    "jarak_high20": "dekat high 20h", "posisi_close": "close dekat high harian",
    "rs20": "kuat vs IHSG", "log_value": "likuiditas",
    "ihsg_atas": "IHSG > EMA50", "ihsg_mom20": "momentum IHSG", "breadth": "breadth syariah",
}


def tag():
    return f"tp{TP:g}_sl{SL:g}"


def file_status():
    return d.penanda(f"status_screener_{tag()}")


def penanda_holdout():
    return d.penanda(f"holdout_dibuka_{tag()}")


def fraksi(harga):
    harga = np.asarray(harga, dtype=float)
    return np.select([harga < 200, harga < 500, harga < 2000, harga < 5000], [1, 2, 5, 10], 25)


def daftar_syariah():
    return {t.removesuffix(".JK") for t in s.baca_ticker("data/syariah_tickers.txt")}


def baca_harga(daftar=None):
    data = {}
    syariah = daftar_syariah() if daftar is None else set(daftar)
    for kode, df in sorted(dt.baca_banyak("harga", sorted(syariah)).items()):
        df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
        if len(df) < 250:
            continue
        faktor = df["adj_close"] / df["close"]
        o, h, l, c = df["open"] * faktor, df["high"] * faktor, df["low"] * faktor, df["adj_close"]
        data[kode] = pd.DataFrame({
            "open": o,
            "high": pd.concat([o, h, l, c], axis=1).max(axis=1),
            "low": pd.concat([o, h, l, c], axis=1).min(axis=1),
            "close": c,
            "volume": df["volume"],
            "close_mentah": df["close"],
        }, index=df.index)
    return data


def baca_pasar(data):
    p = dt.baca("pasar")
    ihsg = p["ihsg"].dropna()
    pasar = pd.DataFrame({
        "ihsg_atas": (ihsg > ihsg.ewm(span=50, adjust=False).mean()).astype(float),
        "ihsg_mom20": (ihsg / ihsg.shift(20) - 1) * 100,
    })
    semua_tgl = pasar.index
    for d in data.values():
        semua_tgl = semua_tgl.union(d.index)
    return pasar.reindex(semua_tgl).ffill()


def fitur_ticker(d, pasar):
    x = s.hitung_indikator(d)
    x["mom60"] = (x["close"] / x["close"].shift(60) - 1) * 100
    x["jarak_ema50"] = (x["close"] / x["ema50"] - 1) * 100
    x["value_mentah"] = (d["close_mentah"] * d["volume"]).rolling(20).mean()
    x["log_value"] = np.log10(x["value_mentah"].clip(lower=1))
    x["atas_ema20"] = (x["close"] > x["ema20"]).astype(float)
    x["rs20"] = x["mom20"] - pasar["ihsg_mom20"].reindex(x.index)
    vol_nol = (d["volume"] == 0).rolling(5).sum()
    x["lolos"] = (
        (x["value_mentah"] >= MIN_VALUE)
        & x["atr_pct"].between(ATR_MIN, ATR_MAKS)
        & (d["close_mentah"] >= HARGA_MIN)
        & (vol_nol == 0)
    )
    return x


def label_ticker(x):
    o, h, l, c = (x[k].to_numpy(float) for k in ["open", "high", "low", "close"])
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    n = len(x)
    menang = np.full(n, np.nan)
    net = np.full(n, np.nan)
    kotor = np.full(n, np.nan)
    hari = np.full(n, np.nan)
    idx_keluar = np.full(n, -1)
    alasan = np.full(n, None, dtype=object)

    for i in np.flatnonzero(x["lolos"].to_numpy()):
        if i + 1 >= n:
            continue
        e = o[i + 1]
        tp = e * (1 + TP / 100)
        sl = e * (1 - SL / 100)
        hasil = None
        for j in range(i + 1, min(i + MAKS_HARI, n - 1) + 1):
            kunci = h[j] == l[j]
            if j > i + 1 and o[j] <= sl:
                if kunci:
                    continue
                hasil = (o[j], 0, "gap_sl", j)
                break
            if j > i + 1 and o[j] >= tp:
                hasil = (o[j], 1, "gap_tp", j)
                break
            if l[j] <= sl:
                if kunci:
                    continue
                hasil = (sl, 0, "sl", j)
                break
            if h[j] >= tp:
                hasil = (tp, 1, "tp", j)
                break
        if hasil is None:
            if i + MAKS_HARI > n - 1:
                continue
            j = i + MAKS_HARI
            hasil = (c[j], 0, "waktu", j)

        px, win, why, j = hasil
        masuk_mentah = e * rasio[i + 1]
        keluar_mentah = px * rasio[j]
        tk_masuk = fraksi(masuk_mentah) / masuk_mentah
        tk_keluar = fraksi(keluar_mentah) / keluar_mentah
        beli = e * (1 + tk_masuk) * (1 + FEE_BELI / 100)
        jual = px * (1 - tk_keluar) * (1 - FEE_JUAL / 100)
        menang[i] = win
        net[i] = (jual / beli - 1) * 100
        kotor[i] = (px / e - 1) * 100
        hari[i] = j - i
        idx_keluar[i] = j
        alasan[i] = why

    tgl_exit = pd.Series(pd.NaT, index=x.index, dtype="datetime64[ns]")
    ada = idx_keluar >= 0
    tgl_exit.iloc[np.flatnonzero(ada)] = x.index[idx_keluar[ada]]
    return pd.DataFrame({
        "menang": menang, "net": net, "kotor": kotor, "hari": hari,
        "alasan": alasan, "tgl_exit": tgl_exit,
    }, index=x.index)


def bangun_panel():
    data = baca_harga()
    pasar = baca_pasar(data)
    potong = []
    for t, d in data.items():
        x = fitur_ticker(d, pasar)
        x = x.join(label_ticker(x))
        x["ticker"] = t
        potong.append(x)
    semua = pd.concat(potong)
    semua.index.name = "tgl"
    semua = semua.reset_index()
    breadth = semua.groupby("tgl")["atas_ema20"].mean() * 100
    p = semua[semua["lolos"]].copy()
    p["breadth"] = p["tgl"].map(breadth)
    p = p.merge(pasar, left_on="tgl", right_index=True, how="left")
    p = p.dropna(subset=FITUR_SAHAM + FITUR_PASAR)
    jml = p.groupby("tgl")["ticker"].transform("size")
    p = p[jml >= MIN_SAHAM_HARI].copy()
    for f in FITUR_SAHAM:
        p["r_" + f] = p.groupby("tgl")[f].rank(pct=True)
    print(f"panel: {len(p)} baris, {p['ticker'].nunique()} ticker, {p['tgl'].min().date()} s/d {p['tgl'].max().date()}, "
          f"{p['menang'].notna().sum()} berlabel")
    return p.reset_index(drop=True)


def kolom_x():
    return ["r_" + f for f in FITUR_SAHAM] + FITUR_PASAR


def latih_model(latih):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    m.fit(latih[kolom_x()].to_numpy(float), latih["menang"].to_numpy(int))
    return m


def walk_forward(p):
    p["skor"] = np.nan
    awal = p["tgl"].dt.year.min()
    for th in range(awal + TAHUN_LATIH_MIN, p["tgl"].dt.year.max() + 1):
        batas = pd.Timestamp(th, 1, 1)
        latih = p[(p["tgl_exit"] < batas) & p["menang"].notna()]
        uji = p["tgl"].dt.year == th
        if latih.empty or not uji.any():
            continue
        m = latih_model(latih)
        p.loc[uji, "skor"] = m.predict_proba(p.loc[uji, kolom_x()].to_numpy(float))[:, 1]
    return p


def simulasi(top):
    terakhir = {}
    ambil = []
    for r in top.sort_values(["tgl", "skor"], ascending=[True, False]).itertuples():
        if r.ticker in terakhir and r.tgl < terakhir[r.ticker]:
            continue
        terakhir[r.ticker] = r.tgl_exit
        ambil.append(r.Index)
    return top.loc[ambil]


def bootstrap(tr, n=2000, seed=7):
    g = tr.groupby(tr["tgl"].dt.to_period("M"))["net"].agg(["sum", "size"])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), (n, len(g)))
    rata = g["sum"].to_numpy()[idx].sum(1) / g["size"].to_numpy()[idx].sum(1)
    return np.percentile(rata, [5, 95])


def evaluasi(p, label):
    p = p.dropna(subset=["skor", "menang"]).copy()
    base = p["menang"].mean() * 100
    pct = p.groupby("tgl")["skor"].rank(pct=True)
    p["desil"] = np.ceil(pct * 10).clip(1, 10).astype(int)
    tabel = p.groupby("desil").agg(
        n=("menang", "size"),
        hit=("menang", lambda v: v.mean() * 100),
        net=("net", "mean"),
        hari=("hari", "mean"),
    )
    rho = pd.Series(tabel.index, index=tabel.index).corr(tabel["hit"], method="spearman")

    top = p[p["desil"] == 10]
    tr = simulasi(top)
    exp = tr["net"].mean()
    lo, hi = bootstrap(tr)
    th = tr.groupby(tr["tgl"].dt.year)["net"].mean()
    th_pos = (th > 0).mean() * 100
    tanpa10 = tr.drop(tr["net"].nlargest(10).index)["net"].mean()
    per_ticker = tr.groupby("ticker")["net"].sum().sort_values(ascending=False)
    lima = per_ticker.head(5).index
    tanpa5 = tr[~tr["ticker"].isin(lima)]["net"].mean()
    hit_top = tabel.loc[10, "hit"]

    print(f"\n========== {label} | {p['tgl'].min().date()} s/d {p['tgl'].max().date()} ==========")
    print(f"observasi {len(p)} | base rate (TP +{TP:g}% sebelum SL -{SL:g}%): {base:.1f}% | "
          f"rata2 net semua observasi {p['net'].mean():.2f}%")
    tampil = tabel.round(2)
    print(tampil.to_string())
    print(f"spearman desil vs hit: {rho:.2f}")
    print(f"\nsimulasi desil 10 (1 posisi per ticker): {len(tr)} trade | hit {tr['menang'].mean() * 100:.1f}% | "
          f"exp net {exp:.2f}% | median {tr['net'].median():.2f}% | rata2 hari {tr['hari'].mean():.1f}")
    print(f"alasan exit: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in tr["alasan"].value_counts(normalize=True).items()))
    print(f"bootstrap 90%: [{lo:.2f}, {hi:.2f}]")
    print("per tahun: " + " | ".join(f"{t}: {v:.2f}% ({(tr['tgl'].dt.year == t).sum()})" for t, v in th.items()))
    print(f"tanpa 10 trade terbaik: {tanpa10:.2f}% | tanpa 5 ticker teratas ({', '.join(lima)}): {tanpa5:.2f}%")

    kriteria = [
        ("1. hit desil 10 >= base +5", hit_top >= base + 5, f"{hit_top:.1f} vs {base + 5:.1f}"),
        ("2. spearman >= 0.7", rho >= 0.7, f"{rho:.2f}"),
        ("3. exp net > 0", exp > 0, f"{exp:.2f}%"),
        ("4. bootstrap 5% > 0", lo > 0, f"{lo:.2f}%"),
        ("5. tahun positif >= 70%", th_pos >= 70, f"{th_pos:.0f}%"),
        ("6a. tanpa 10 terbaik > 0", tanpa10 > 0, f"{tanpa10:.2f}%"),
        ("6b. tanpa 5 ticker > 0", tanpa5 > 0, f"{tanpa5:.2f}%"),
    ]
    print("\nkriteria:")
    for nama, ok, nilai in kriteria:
        print(f"  [{'LULUS' if ok else 'GAGAL'}] {nama}: {nilai}")
    semua_ok = all(ok for _, ok, _ in kriteria)
    print(f"hasil {label}: {'LULUS' if semua_ok else 'GAGAL'}")
    ringkas_bulanan(tr)

    nama = f"{label.split()[0].lower()}_{tag()}"
    dt.simpan_hasil(f"trades_screener_{nama}", tr.drop(columns=[c for c in tr.columns if c.startswith("r_")]).reset_index(drop=True))
    dt.simpan_hasil(f"desil_screener_{nama}", tabel.reset_index())
    return semua_ok


def jalankan_uji(a):
    if a.periode == "holdout" and penanda_holdout().exists() and not a.paksa:
        print(f"holdout {tag()} sudah pernah dibuka ({penanda_holdout().read_text().strip()}). Pakai --paksa kalau memang perlu.")
        return
    p = walk_forward(bangun_panel())
    th = p["tgl"].dt.year
    if a.periode == "dev":
        ok = evaluasi(p[(th >= DEV[0]) & (th <= DEV[1])], f"DEV {DEV[0]}-{DEV[1]}")
        file_status().write_text(f"{tag()} dev {'LULUS' if ok else 'GAGAL'} ({datetime.now():%Y-%m-%d}), holdout belum dibuka\n")
    else:
        penanda_holdout().write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
        ok = evaluasi(p[th >= HOLDOUT_MULAI], f"HOLDOUT {HOLDOUT_MULAI}+")
        file_status().write_text(f"{tag()} holdout {'LULUS' if ok else 'GAGAL'} ({datetime.now():%Y-%m-%d})\n")


def pendorong(m, baris):
    skala = m.named_steps["standardscaler"]
    koef = m.named_steps["logisticregression"].coef_[0]
    z = (baris[kolom_x()].to_numpy(float) - skala.mean_) / skala.scale_
    kontribusi = z * koef
    nama = [c.removeprefix("r_") for c in kolom_x()]
    hasil = []
    for k, zz in zip(kontribusi, z):
        urut = np.argsort(-k)[:3]
        hasil.append(", ".join(
            f"{NAMA_FITUR[nama[u]]} {'tinggi' if zz[u] > 0 else 'rendah'}" for u in urut if k[u] > 0
        ))
    return hasil


def jalankan_pindai(a):
    p = bangun_panel()
    akhir = p["tgl"].max()
    m = latih_model(p[p["menang"].notna()])
    hari_ini = p[p["tgl"] == akhir].copy()
    hari_ini["peluang"] = m.predict_proba(hari_ini[kolom_x()].to_numpy(float))[:, 1] * 100
    hari_ini["pendorong"] = pendorong(m, hari_ini)
    hari_ini = hari_ini.sort_values("peluang", ascending=False).reset_index(drop=True)
    hari_ini["peringkat"] = hari_ini.index + 1
    hari_ini["close"] = hari_ini["close_mentah"]
    hari_ini["tp_ref"] = (hari_ini["close"] * (1 + TP / 100)).round(0)
    hari_ini["sl_ref"] = (hari_ini["close"] * (1 - SL / 100)).round(0)
    base_hist = p["menang"].mean() * 100
    rata_hari = hari_ini["peluang"].mean()

    kolom = ["peringkat", "ticker", "close", "tp_ref", "sl_ref", "peluang", "pendorong"]
    out = hari_ini[kolom].copy()
    out["peluang"] = out["peluang"].round(1)
    nama = f"rekomendasi_{akhir:%Y%m%d}_{tag()}"
    dt.simpan_hasil(nama, out.reset_index(drop=True))

    log = out.assign(tgl=akhir, base_hari=round(rata_hari, 1), konfig=tag())
    d.simpan_df("rekomendasi_log", log, {"tgl": akhir.to_pydatetime(), "konfig": tag()})

    status = file_status().read_text().strip() if file_status().exists() else f"{tag()} belum diuji"
    print(f"\ndata terakhir {akhir.date()} | status model: {status}")
    print(f"base rate historis {base_hist:.1f}% | rata2 peluang semua saham lolos hari ini {rata_hari:.1f}% | "
          f"IHSG > EMA50: {'ya' if hari_ini['ihsg_atas'].iloc[0] else 'tidak'} | breadth {hari_ini['breadth'].iloc[0]:.0f}%")
    print("TP/SL di bawah dihitung dari close; hitung ulang dari harga open besok.\n")
    print(out.head(a.tampil).to_string(index=False))
    print(f"\n{len(out)} saham lolos filter, semua tersimpan di {nama}")


def jalankan_cek(a):
    log = d.baca_df("rekomendasi_log", {"konfig": tag()})
    if log.empty:
        print("belum ada log rekomendasi")
        return
    log["tgl"] = pd.to_datetime(log["tgl"])
    p = bangun_panel()
    g = log.merge(p[["tgl", "ticker", "menang", "net", "hari", "alasan"]], on=["tgl", "ticker"], how="left")
    selesai = g[g["menang"].notna()]
    print(f"{len(log)} rekomendasi, {len(selesai)} sudah selesai")
    if selesai.empty:
        return
    selesai = selesai.copy()
    selesai["kelompok"] = pd.cut(selesai["peringkat"], [0, 5, 10, 20, 10_000], labels=["1-5", "6-10", "11-20", "21+"])
    r = selesai.groupby("kelompok", observed=True).agg(
        n=("menang", "size"), hit=("menang", lambda v: v.mean() * 100),
        perkiraan=("peluang", "mean"), net=("net", "mean"),
    ).round(2)
    print(r.to_string())


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["uji", "pindai", "cek"])
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--paksa", action="store_true")
    ap.add_argument("--tampil", type=int, default=30)
    ap.add_argument("--tp", type=float, default=3.0)
    ap.add_argument("--sl", type=float, default=3.0)
    a = ap.parse_args()
    global TP, SL
    TP, SL = a.tp, a.sl
    {"uji": jalankan_uji, "pindai": jalankan_pindai, "cek": jalankan_cek}[a.mode](a)


if __name__ == "__main__":
    utama()
