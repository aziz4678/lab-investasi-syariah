import argparse
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

HARI_TH = 252
BIAYA_KELUAR = 0.007
BIAYA_MASUK = 0.006
JEDA = 3
BULAN_MA = 10
DEV = ("2001-04-30", "2014-12-31")
HOLDOUT = ("2015-01-01", "2026-10-23")
SKENARIO = {
    "dasar": {"div": 2.5, "exp": 2.0, "kas_nol": False},
    "5_kas_0": {"div": 2.5, "exp": 2.0, "kas_nol": True},
    "6a_dividen_4": {"div": 4.0, "exp": 2.0, "kas_nol": False},
    "6b_expense_1_6": {"div": 2.5, "exp": 1.6, "kas_nol": False},
    "gabungan_terburuk": {"div": 4.0, "exp": 1.6, "kas_nol": True},
}


def jii():
    nama = "indeks/JKII"
    if dt.ada(nama):
        s = dt.baca(nama)["close"]
        if s.index.max() >= pd.Timestamp(HOLDOUT[1]):
            return s
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    h = yf.Ticker("^JKII").history(period="max", auto_adjust=False)
    h.index = h.index.tz_localize(None).normalize()
    df = h[["Close"]].rename(columns={"Close": "close"}).dropna()
    dt.tulis(nama, df)
    return df["close"]


def bunga_bulanan():
    fred = dt.baca("makro/bunga_antarbank")["nilai"]
    fred.index = fred.index.to_period("M")
    bi = dt.baca("makro/bi_rate")["nilai"].sort_index()
    bulan = pd.period_range("2000-01", pd.Timestamp(HOLDOUT[1]).to_period("M"), freq="M")
    hasil = {}
    for b in bulan:
        if b in fred.index:
            hasil[b] = float(fred[b])
        else:
            sebelum = bi[bi.index <= b.start_time]
            hasil[b] = float(sebelum.iloc[-1]) if len(sebelum) else np.nan
    return pd.Series(hasil)


def sinyal(c):
    akhir = c.groupby(c.index.to_period("M")).tail(1)
    ma = akhir.rolling(BULAN_MA).mean()
    s = pd.Series(np.where(akhir >= ma, "pasar", "kas"), index=akhir.index.to_period("M"))
    return s.where(ma.notna().to_numpy())


def simulasi(c, bunga, sk, mulai, akhir, awal_h20, awal_bh):
    sig = sinyal(c[c.index <= pd.Timestamp(akhir)])
    c = c[(c.index > pd.Timestamp(mulai) - pd.Timedelta(days=40)) & (c.index <= pd.Timestamp(akhir))]
    idx = c.index[c.index > pd.Timestamp(mulai)]
    pasar_hari = (1 + (sk["div"] - sk["exp"]) / 100) ** (1 / HARI_TH)
    v_h = v_b = 1.0
    keadaan = awal_h20
    bh_masuk = awal_bh == "pasar"
    transit, beli_di, keluar_hari = 0, None, None
    ek_h, ek_b, kas_hari, tindakan = [], [], 0, []
    sebelumnya = c[c.index <= pd.Timestamp(mulai)].iloc[-1] if (c.index <= pd.Timestamp(mulai)).any() else c.iloc[0]
    bulan_lalu = None
    urutan_bulan = 0
    for t in idx:
        px = c[t]
        r = px / sebelumnya
        bln = t.to_period("M")
        if bln != bulan_lalu:
            urutan_bulan = 1
            bulan_lalu = bln
            target = sig.get(bln - 1)
            if isinstance(target, str) and target != keadaan and keadaan in ("pasar", "kas"):
                tindakan.append((t, "keluar" if keadaan == "pasar" else "masuk"))
                keadaan = "akan_keluar" if keadaan == "pasar" else "akan_masuk"
        else:
            urutan_bulan += 1
        kas_r = 1.0 if sk["kas_nol"] else (1 + (bunga.get(bln, np.nan) - 1.5) / 100) ** (1 / HARI_TH)
        if keadaan in ("pasar", "akan_keluar"):
            v_h *= r * pasar_hari
            if keadaan == "akan_keluar":
                v_h *= 1 - BIAYA_KELUAR
                keadaan, transit = "transit_kas", JEDA
        elif keadaan == "kas":
            v_h *= kas_r
            kas_hari += 1
        elif keadaan == "transit_kas":
            transit -= 1
            kas_hari += 1
            if transit == 0:
                keadaan = "kas"
        elif keadaan == "akan_masuk":
            keadaan, transit = "transit_pasar", JEDA
            kas_hari += 1
        elif keadaan == "transit_pasar":
            transit -= 1
            kas_hari += 1
            if transit == 0:
                v_h *= 1 - BIAYA_MASUK
                keadaan = "pasar"
        if bh_masuk:
            v_b *= r * pasar_hari
        elif urutan_bulan == 1:
            v_b *= 1 - BIAYA_MASUK
            bh_masuk = True
        ek_h.append(v_h)
        ek_b.append(v_b)
        sebelumnya = px
    eh = pd.Series(ek_h, index=idx)
    eb = pd.Series(ek_b, index=idx)
    return eh, eb, tindakan, kas_hari / len(idx), keadaan


def metrik(e, mulai):
    awal = pd.concat([pd.Series([1.0], index=[pd.Timestamp(mulai)]), e])
    th = (awal.index[-1] - awal.index[0]).days / 365.25
    cagr = (awal.iloc[-1] ** (1 / th) - 1) * 100
    dd = (awal / awal.cummax() - 1).min() * 100
    return cagr, dd


def jendela(eh, eb, mulai, akhir):
    menang, total = 0, 0
    titik = pd.date_range(pd.Timestamp(mulai), pd.Timestamp(akhir), freq="ME")
    for s in titik:
        u = s + pd.DateOffset(years=5)
        if u > pd.Timestamp(akhir):
            break
        h = eh[(eh.index > s) & (eh.index <= u)]
        b = eb[(eb.index > s) & (eb.index <= u)]
        if len(h) < 200:
            continue
        hs = eh[eh.index <= s].iloc[-1] if (eh.index <= s).any() else 1.0
        bs = eb[eb.index <= s].iloc[-1] if (eb.index <= s).any() else 1.0
        ch, dh = metrik(h / hs, s)
        cb, db = metrik(b / bs, s)
        total += 1
        if abs(dh) < abs(db) and ch >= cb - 2:
            menang += 1
    return menang, total


def jalankan(periode):
    c = jii()
    bunga = bunga_bulanan()
    mulai, akhir = DEV if periode == "dev" else HOLDOUT
    awal_h20, awal_bh = "kas", "kas"
    if periode == "holdout":
        eh0, _, _, _, posisi = simulasi(c, bunga, SKENARIO["dasar"], DEV[0], DEV[1], "kas", "kas")
        awal_h20 = "pasar" if posisi in ("pasar", "akan_keluar", "transit_pasar") else "kas"
        awal_bh = "pasar"
    print(f"\n##### H20 {periode.upper()} {mulai} s/d {akhir} | JII {c.index.min():%Y-%m-%d} s/d {c.index.max():%Y-%m-%d} | posisi awal H20: {awal_h20}")
    hasil = {}
    for nama, sk in SKENARIO.items():
        if periode == "holdout" and nama != "dasar":
            eh0, _, _, _, posisi = simulasi(c, bunga, sk, DEV[0], DEV[1], "kas", "kas")
            awal_h20 = "pasar" if posisi in ("pasar", "akan_keluar", "transit_pasar") else "kas"
        eh, eb, tindakan, kas_pct, _ = simulasi(c, bunga, sk, mulai, akhir, awal_h20, awal_bh)
        ch, dh = metrik(eh, mulai)
        cb, db = metrik(eb, mulai)
        th = (eh.index[-1] - pd.Timestamp(mulai)).days / 365.25
        pindah = len(tindakan) / th
        m, n = jendela(eh, eb, mulai, akhir)
        hasil[nama] = {"cagr_h20": ch, "dd_h20": dh, "cagr_bh": cb, "dd_bh": db, "pindah_th": pindah, "kas_pct": kas_pct * 100,
                       "jendela": m / n * 100 if n else np.nan, "n_jendela": n, "k1": abs(dh) <= abs(db) * 2 / 3, "k2": ch >= cb - 2,
                       "k3": pindah <= 3, "k4": n > 0 and m / n >= 0.6, "tindakan": tindakan, "eh": eh, "eb": eb}
    print(f"{'skenario':20s} {'CAGR H20':>9s} {'DD H20':>8s} {'CAGR BH':>8s} {'DD BH':>8s} {'pindah/th':>9s} {'% kas':>6s} {'jendela':>8s}  k1 k2 k3 k4")
    for nama, h in hasil.items():
        print(f"{nama:20s} {h['cagr_h20']:8.2f}% {h['dd_h20']:7.1f}% {h['cagr_bh']:7.2f}% {h['dd_bh']:7.1f}% {h['pindah_th']:9.2f} {h['kas_pct']:5.0f}% "
              f"{h['jendela']:7.0f}%  {'Y' if h['k1'] else '-'}  {'Y' if h['k2'] else '-'}  {'Y' if h['k3'] else '-'}  {'Y' if h['k4'] else '-'}")
    da = hasil["dasar"]
    print(f"\nKriteria dasar ({periode}):")
    print(f"  [{'LULUS' if da['k1'] else 'GAGAL'}] 1. DD H20 <= 2/3 DD beli-tahan: {da['dd_h20']:.1f}% vs batas {da['dd_bh'] * 2 / 3:.1f}% (BH {da['dd_bh']:.1f}%)")
    print(f"  [{'LULUS' if da['k2'] else 'GAGAL'}] 2. CAGR H20 >= CAGR BH - 2%: {da['cagr_h20']:.2f}% vs batas {da['cagr_bh'] - 2:.2f}% (BH {da['cagr_bh']:.2f}%)")
    print(f"  [{'LULUS' if da['k3'] else 'GAGAL'}] 3. perpindahan <= 3/th: {da['pindah_th']:.2f}/th ({len(da['tindakan'])} kali)")
    print(f"  [{'LULUS' if da['k4'] else 'GAGAL'}] 4. menang di >= 60% jendela 5 th: {da['jendela']:.0f}% dari {da['n_jendela']} jendela")
    sens = {}
    for nama in ("5_kas_0", "6a_dividen_4", "6b_expense_1_6"):
        h = hasil[nama]
        sens[nama] = h["k1"] and h["k2"]
        print(f"  [{'LULUS' if sens[nama] else 'GAGAL'}] {nama}: k1 {h['dd_h20']:.1f}% vs {h['dd_bh'] * 2 / 3:.1f}% | k2 {h['cagr_h20']:.2f}% vs {h['cagr_bh'] - 2:.2f}%")
    g = hasil["gabungan_terburuk"]
    print(f"  (laporan) gabungan terburuk: CAGR {g['cagr_h20']:.2f}% vs BH {g['cagr_bh']:.2f}%, DD {g['dd_h20']:.1f}% vs {g['dd_bh']:.1f}%")
    lulus = da["k1"] and da["k2"] and da["k3"] and da["k4"] and all(sens.values())
    print(f"\nHASIL AKHIR H20 {periode.upper()}: {'LULUS' if lulus else 'GAGAL'}")
    th_h = da["eh"].groupby(da["eh"].index.year).last()
    th_b = da["eb"].groupby(da["eb"].index.year).last()
    ret = pd.DataFrame({"H20": th_h.pct_change() * 100, "BH": th_b.pct_change() * 100})
    ret.iloc[0] = [(th_h.iloc[0] - 1) * 100, (th_b.iloc[0] - 1) * 100]
    print("\nPer tahun (%):\n" + ret.round(1).T.to_string())
    print("\nPerpindahan: " + ", ".join(f"{t:%Y-%m} {j}" for t, j in da["tindakan"]))
    dt.simpan_hasil(f"h20_{periode}", pd.DataFrame({k: {x: v[x] for x in ("cagr_h20", "dd_h20", "cagr_bh", "dd_bh", "pindah_th", "kas_pct", "jendela", "k1", "k2", "k3", "k4")}
                                                    for k, v in hasil.items()}).T.reset_index())
    return lulus


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    a = ap.parse_args()
    if a.periode == "holdout":
        penanda = d.penanda("holdout_dibuka_h20")
        if penanda.exists():
            raise SystemExit(f"holdout H20 sudah pernah dibuka ({penanda.read_text().strip()})")
        penanda.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
