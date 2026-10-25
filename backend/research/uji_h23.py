import argparse
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest.final import buang_belum_final
from backend.research.uji_h20 import HARI_TH, bunga_bulanan, jendela, jii, metrik

JEDA = 3
BULAN_LIHAT = 12
DEV = ("2002-06-30", "2014-12-31")
HOLDOUT = ("2015-01-01", "2026-10-23")
ASET = ("jii", "emas", "kas")
SKENARIO = {
    "dasar": {"div": 2.5, "exp": 2.0, "kas_nol": False, "emas": 0.01},
    "6_kas_0": {"div": 2.5, "exp": 2.0, "kas_nol": True, "emas": 0.01},
    "7_emas_4": {"div": 2.5, "exp": 2.0, "kas_nol": False, "emas": 0.02},
    "8_dividen_4": {"div": 4.0, "exp": 2.0, "kas_nol": False, "emas": 0.01},
    "gabungan_terburuk": {"div": 4.0, "exp": 2.0, "kas_nol": True, "emas": 0.02},
}
FRED_KURS = "CCUSSP02IDM650N"


def emas_usd():
    nama = "pasar_panjang/emas_usd"
    if dt.ada(nama):
        df = dt.baca(nama)
        if df.index.max() >= pd.Timestamp(HOLDOUT[1]):
            return df["close"]
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    h = yf.Ticker("GC=F").history(period="max", auto_adjust=False)
    h.index = h.index.tz_localize(None).normalize()
    df = buang_belum_final(h[["Close"]].rename(columns={"Close": "close"}).dropna(), "GC=F")
    dt.tulis(nama, df)
    return df["close"]


def kurs_fred():
    nama = "makro/kurs_akhir_bulan"
    if dt.ada(nama):
        return dt.baca(nama)["nilai"]
    from backend.ingest.makro import fred
    df = fred(FRED_KURS)
    dt.tulis(nama, df)
    return df["nilai"]


def kurs_bersih():
    k = dt.baca("kurs/USD")["close"].sort_index()
    med = k.rolling(21, center=True, min_periods=5).median()
    k = k[(k / med - 1).abs() <= 0.05]
    f = kurs_fred()
    f.index = f.index.to_period("M").to_timestamp("M")
    tgl = k.index.to_series()
    jarak = tgl.diff().dt.days
    celah = [(akhir - pd.Timedelta(days=int(hari)), akhir) for akhir, hari in jarak[jarak > 7].items()]
    jangkar = pd.concat([k] + [f[(f.index > a) & (f.index < b)] for a, b in celah])
    jangkar = jangkar[~jangkar.index.duplicated(keep="first")].sort_index()
    semua = pd.date_range(k.index.min(), k.index.max(), freq="D")
    log = np.log(jangkar).reindex(semua.union(jangkar.index))
    interp = log.interpolate(method="time").reindex(semua)
    terus = np.log(k).reindex(semua).ffill()
    di_celah = pd.Series(False, index=semua)
    for a, b in celah:
        di_celah[(semua > a) & (semua < b)] = True
    return np.exp(interp.where(di_celah, terus))


def emas_idr(kalender):
    e = emas_usd()
    k = kurs_bersih()
    gab = pd.concat([e.rename("e"), k.rename("k")], axis=1, sort=True)
    gab["k"] = gab["k"].ffill()
    gab = gab.dropna(subset=["e", "k"])
    gab = gab[gab.index.weekday < 5]
    nilai = gab["e"] * gab["k"]
    pos = nilai.index.searchsorted(kalender, side="left") - 1
    hasil = pd.Series(np.where(pos >= 0, nilai.to_numpy()[np.clip(pos, 0, None)], np.nan), index=kalender)
    return hasil


def faktor(c, emas, bunga, sk):
    r_jii = (c / c.shift(1)) * (1 + (sk["div"] - sk["exp"]) / 100) ** (1 / HARI_TH)
    r_emas = emas / emas.shift(1)
    if sk["kas_nol"]:
        r_kas = pd.Series(1.0, index=c.index)
    else:
        b = pd.Series([bunga.get(t.to_period("M"), np.nan) for t in c.index], index=c.index)
        r_kas = (1 + (b - 1.5) / 100) ** (1 / HARI_TH)
    return pd.DataFrame({"jii": r_jii, "emas": r_emas, "kas": r_kas})


def sinyal(f):
    f = f.dropna()
    idx = f.cumprod()
    akhir = idx.groupby(idx.index.to_period("M")).tail(1)
    akhir.index = akhir.index.to_period("M")
    r12 = akhir / akhir.shift(BULAN_LIHAT) - 1
    r12 = r12[r12.notna().all(axis=1)]
    return r12.idxmax(axis=1)


def biaya(aset, sisi, sk):
    if aset == "jii":
        return 0.006 if sisi == "beli" else 0.007
    if aset == "emas":
        return sk["emas"]
    return 0.0


def simulasi(f, sig, sk, mulai, akhir, awal, sudah_pegang):
    f = f[(f.index > pd.Timestamp(mulai)) & (f.index <= pd.Timestamp(akhir))]
    v = 1.0
    pegang, target, sisa = awal, None, 0
    bh = 1.0
    bh_masuk = sudah_pegang
    mx = {"jii": 0.5, "emas": 0.5}
    if not sudah_pegang:
        mx = {a: 0.5 * (1 - biaya(a, "beli", sk)) for a in mx}
    ek, ek_bh, ek_mx, tindakan = [], [], [], []
    hari = {"jii": 0, "emas": 0, "kas": 0, "pindah": 0}
    bulan_lalu = None
    tahun_lalu = f.index[0].year
    pertama = not sudah_pegang
    for t, r in f.iterrows():
        bln = t.to_period("M")
        hari_satu = bln != bulan_lalu
        bulan_lalu = bln
        if hari_satu and sisa == 0:
            tuju = sig.get(bln - 1)
            if isinstance(tuju, str) and tuju != pegang:
                tindakan.append((t, pegang, tuju))
                if pegang != "kas":
                    v *= r[pegang]
                    v *= 1 - biaya(pegang, "jual", sk)
                target, sisa = tuju, JEDA
                hari["pindah"] += 1
                pegang = None
        elif sisa > 0:
            sisa -= 1
            hari["pindah"] += 1
            if sisa == 0:
                v *= 1 - biaya(target, "beli", sk)
                pegang, target = target, None
        else:
            v *= r[pegang]
            hari[pegang] += 1
        if bh_masuk:
            bh *= r["jii"]
        else:
            bh *= 1 - biaya("jii", "beli", sk)
            bh_masuk = True
        if not pertama:
            mx = {a: x * r[a] for a, x in mx.items()}
            if t.year != tahun_lalu:
                tot = sum(mx.values())
                lebih = max(mx, key=mx.get)
                kurang = "emas" if lebih == "jii" else "jii"
                geser = mx[lebih] - tot / 2
                mx[lebih] -= geser
                mx[kurang] += geser * (1 - biaya(lebih, "jual", sk)) * (1 - biaya(kurang, "beli", sk))
        tahun_lalu = t.year
        pertama = False
        ek.append(v)
        ek_bh.append(bh)
        ek_mx.append(sum(mx.values()))
    akhir_pegang = pegang if pegang is not None else target
    n = len(f)
    porsi = {a: hari[a] / n * 100 for a in hari}
    return (pd.Series(ek, index=f.index), pd.Series(ek_bh, index=f.index), pd.Series(ek_mx, index=f.index),
            tindakan, porsi, akhir_pegang)


def rasio(cagr, dd):
    return cagr / abs(dd) if dd else np.inf


def siapkan():
    c = jii()
    kal = c.index
    emas = emas_idr(kal)
    return c, emas, bunga_bulanan()


def hitung(periode, c, emas, bunga):
    mulai, akhir = DEV if periode == "dev" else HOLDOUT
    cc = c[c.index <= pd.Timestamp(akhir)]
    ee = emas[emas.index <= pd.Timestamp(akhir)]
    hasil = {}
    for nama, sk in SKENARIO.items():
        f = faktor(cc, ee, bunga, sk)
        sig = sinyal(f)
        if periode == "dev":
            awal, sudah = "kas", False
        else:
            *_, posisi = simulasi(f, sig, sk, DEV[0], DEV[1], "kas", False)
            awal, sudah = posisi, True
        e, b, m, tindakan, porsi, _ = simulasi(f, sig, sk, mulai, akhir, awal, sudah)
        ch, dh = metrik(e, mulai)
        cb, db = metrik(b, mulai)
        cm, dm = metrik(m, mulai)
        th = (e.index[-1] - pd.Timestamp(mulai)).days / 365.25
        pindah = len(tindakan) / th
        jm, jn = jendela(e, b, mulai, akhir)
        hasil[nama] = {"cagr": ch, "dd": dh, "cagr_bh": cb, "dd_bh": db, "cagr_mx": cm, "dd_mx": dm,
                       "pindah_th": pindah, "n_pindah": len(tindakan), "jendela": jm / jn * 100 if jn else np.nan, "n_jendela": jn,
                       "porsi_jii": porsi["jii"], "porsi_emas": porsi["emas"], "porsi_kas": porsi["kas"], "porsi_pindah": porsi["pindah"],
                       "k1": abs(dh) <= abs(db) * 2 / 3, "k2": ch >= cb - 2, "k3": ch >= cm and rasio(ch, dh) >= rasio(cm, dm),
                       "k4": pindah <= 4, "k5": jn > 0 and jm / jn >= 0.6,
                       "tindakan": tindakan, "e": e, "b": b, "m": m, "posisi_awal": awal}
    return hasil


def lapor(periode, hasil):
    mulai, akhir = DEV if periode == "dev" else HOLDOUT
    print(f"\n##### H23 {periode.upper()} {mulai} s/d {akhir} | posisi awal: {hasil['dasar']['posisi_awal']}")
    print(f"{'skenario':18s} {'CAGR':>7s} {'DD':>7s} {'BH':>7s} {'DD BH':>7s} {'50/50':>7s} {'DD mx':>7s} {'pindah':>6s} {'jii%':>5s} {'emas%':>5s} {'kas%':>5s} {'jendela':>7s}  k1 k2 k3 k4 k5")
    for nama, h in hasil.items():
        tanda = " ".join("Y " if h[x] else "- " for x in ("k1", "k2", "k3", "k4", "k5"))
        print(f"{nama:18s} {h['cagr']:6.2f}% {h['dd']:6.1f}% {h['cagr_bh']:6.2f}% {h['dd_bh']:6.1f}% {h['cagr_mx']:6.2f}% {h['dd_mx']:6.1f}% "
              f"{h['pindah_th']:6.2f} {h['porsi_jii']:5.0f} {h['porsi_emas']:5.0f} {h['porsi_kas']:5.0f} {h['jendela']:6.0f}%  {tanda}")
    da = hasil["dasar"]
    print(f"\nKriteria dasar ({periode}):")
    print(f"  [{'LULUS' if da['k1'] else 'GAGAL'}] 1. DD <= 2/3 DD beli-tahan: {da['dd']:.1f}% vs batas {da['dd_bh'] * 2 / 3:.1f}%")
    print(f"  [{'LULUS' if da['k2'] else 'GAGAL'}] 2. CAGR >= BH - 2%: {da['cagr']:.2f}% vs batas {da['cagr_bh'] - 2:.2f}%")
    print(f"  [{'LULUS' if da['k3'] else 'GAGAL'}] 3. vs 50/50: CAGR {da['cagr']:.2f}% vs {da['cagr_mx']:.2f}%, CAGR/|DD| {rasio(da['cagr'], da['dd']):.2f} vs {rasio(da['cagr_mx'], da['dd_mx']):.2f}")
    print(f"  [{'LULUS' if da['k4'] else 'GAGAL'}] 4. perpindahan <= 4/th: {da['pindah_th']:.2f}/th ({da['n_pindah']} kali)")
    print(f"  [{'LULUS' if da['k5'] else 'GAGAL'}] 5. jendela 5 th >= 60%: {da['jendela']:.0f}% dari {da['n_jendela']}")
    sens = {}
    for nama in ("6_kas_0", "7_emas_4", "8_dividen_4"):
        h = hasil[nama]
        sens[nama] = h["k1"] and h["k2"] and h["k3"]
        print(f"  [{'LULUS' if sens[nama] else 'GAGAL'}] {nama}: k1 {h['dd']:.1f}% vs {h['dd_bh'] * 2 / 3:.1f}% | k2 {h['cagr']:.2f}% vs {h['cagr_bh'] - 2:.2f}% | "
              f"k3 {h['cagr']:.2f}% vs {h['cagr_mx']:.2f}%, rasio {rasio(h['cagr'], h['dd']):.2f} vs {rasio(h['cagr_mx'], h['dd_mx']):.2f}")
    g = hasil["gabungan_terburuk"]
    print(f"  (laporan) gabungan terburuk: CAGR {g['cagr']:.2f}% / DD {g['dd']:.1f}% vs BH {g['cagr_bh']:.2f}% / {g['dd_bh']:.1f}% vs 50/50 {g['cagr_mx']:.2f}% / {g['dd_mx']:.1f}%")
    lulus = all(da[x] for x in ("k1", "k2", "k3", "k4", "k5")) and all(sens.values())
    print(f"\nHASIL AKHIR H23 {periode.upper()}: {'LULUS' if lulus else 'GAGAL'}")
    th = pd.DataFrame({x: da[x].groupby(da[x].index.year).last() for x in ("e", "b", "m")})
    ret = th.pct_change() * 100
    ret.iloc[0] = (th.iloc[0] - 1) * 100
    ret.columns = ["H23", "BH JII", "50/50"]
    print("\nPer tahun (%):\n" + ret.round(1).T.to_string())
    print("\nPerpindahan: " + ", ".join(f"{t:%Y-%m} {a}->{b}" for t, a, b in da["tindakan"]))
    return lulus


def simpan(periode, hasil):
    kolom = ("cagr", "dd", "cagr_bh", "dd_bh", "cagr_mx", "dd_mx", "pindah_th", "n_pindah", "jendela", "n_jendela",
             "porsi_jii", "porsi_emas", "porsi_kas", "porsi_pindah", "k1", "k2", "k3", "k4", "k5")
    dt.simpan_hasil(f"h23_{periode}", pd.DataFrame({k: {x: v[x] for x in kolom} for k, v in hasil.items()}).T.reset_index())
    da = hasil["dasar"]
    bln = pd.DataFrame({"h23": da["e"], "beli_tahan": da["b"], "campuran": da["m"]}).resample("ME").last()
    bln.index = bln.index.strftime("%Y-%m")
    dt.simpan_hasil(f"h23_{periode}_kurva", bln.reset_index(names="bulan"))
    dt.simpan_hasil(f"h23_{periode}_pindah", pd.DataFrame([{"tgl": f"{t:%Y-%m-%d}", "dari": a, "ke": b} for t, a, b in da["tindakan"]]))


def jalankan(periode):
    c, emas, bunga = siapkan()
    print(f"JII {c.index.min():%Y-%m-%d} s/d {c.index.max():%Y-%m-%d} | emas rupiah pertama {emas.first_valid_index():%Y-%m-%d}")
    hasil = hitung(periode, c, emas, bunga)
    lulus = lapor(periode, hasil)
    simpan(periode, hasil)
    return lulus


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    a = ap.parse_args()
    if a.periode == "holdout":
        penanda = d.penanda("holdout_dibuka_h23")
        if penanda.exists():
            raise SystemExit(f"holdout H23 sudah pernah dibuka ({penanda.read_text().strip()})")
        penanda.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
