import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset import uji_h13 as h13
from backend.riset import uji_tren as ut

FILE = "ksei"
JEDA_HARI = 30
BULAN_UBAH = 3
DESIL_MIN = 5
SYARAT_TAHUN = 70
LIPUTAN_MIN = 80
DEV_A = ("2011-01-01", "2019-12-31")
HOLDOUT_A = ("2020-01-01", "2026-12-31")
PENANDA = d.penanda("holdout_dibuka_h15a")


def baca_ksei():
    df = dt.baca(FILE).sort_values(["kode", "tgl"])
    inst = df[["L_IS", "L_PF", "L_IB", "L_MF"]].sum(axis=1) + df["F_total"] - df["F_ID"]
    df["inst"] = inst / df["saham"] * 100
    df["ritel"] = df["L_ID"] / df["saham"] * 100
    g = df.groupby("kode")
    jarak = (df["tgl"] - g["tgl"].shift(BULAN_UBAH)).dt.days
    sah = jarak.between(80, 100)
    df["d_inst"] = (df["inst"] - g["inst"].shift(BULAN_UBAH)).where(sah)
    df["d_ritel"] = (df["ritel"] - g["ritel"].shift(BULAN_UBAH)).where(sah)
    df["tersedia"] = df["tgl"] + pd.Timedelta(days=JEDA_HARI)
    return df[["kode", "tgl", "tersedia", "d_inst", "d_ritel"]].dropna(subset=["d_inst", "d_ritel"], how="all")


def kalender(siap):
    jumlah = pd.Series([t for x in siap.values() for t in x.index]).value_counts()
    return pd.DatetimeIndex(sorted(jumlah[jumlah >= max(10, 0.3 * len(siap))].index))


def biaya_sisi(harga, beli):
    return (sc.FEE_BELI if beli else sc.FEE_JUAL) / 100 + float(sc.fraksi(harga)) / harga


def harga_buka(x, tgl):
    if tgl in x.index and np.isfinite(x.at[tgl, "open"]):
        return float(x.at[tgl, "open"])
    sebelum = x.loc[:tgl, "close"].dropna()
    return float(sebelum.iloc[-1]) if len(sebelum) else np.nan


def simulasi_a(siap, ks, mulai, akhir, des=None):
    kal = kalender(siap)
    akhir_bulan = pd.Series(kal, index=kal).groupby(kal.to_period("M")).max()
    akhir_bulan = akhir_bulan[(akhir_bulan >= pd.Timestamp(mulai) - pd.offsets.MonthEnd(1)) & (akhir_bulan <= pd.Timestamp(akhir))]
    likuid = {}
    for t, x in siap.items():
        nol = (x["volume"] == 0).rolling(5).sum()
        likuid[t] = (x["value_mentah"] >= sc.MIN_VALUE) & (x["close_mentah"] >= sc.HARGA_MIN) & (nol == 0)
    hasil, lama = [], []
    tgl_bentuk = list(akhir_bulan)
    for i in range(len(tgl_bentuk) - 1):
        t, t2 = tgl_bentuk[i], tgl_bentuk[i + 1]
        e = kal[kal > t].min()
        k = kal[kal > t2].min()
        if pd.isna(e) or pd.isna(k):
            break
        syariah = des_ojk.syariah_pada(des, t) if des is not None else None
        uni = [s for s, x in siap.items() if t in x.index and bool(likuid[s].get(t, False)) and (syariah is None or s in syariah)]
        if len(uni) < 20:
            continue
        pot = ks[ks["tersedia"] <= t].sort_values("tersedia").groupby("kode").tail(1).set_index("kode")
        pot = pot[pot["tersedia"] >= t - pd.Timedelta(days=JEDA_HARI + 45)]
        sinyal = pot["d_inst"].reindex(uni).dropna()
        ret = {}
        for s in uni:
            x = siap[s]
            a, b = harga_buka(x, e), harga_buka(x, k)
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                ret[s] = b / a - 1
        ret = pd.Series(ret)
        sinyal = sinyal[sinyal.index.isin(ret.index)]
        n = max(DESIL_MIN, int(np.ceil(len(sinyal) / 10)))
        if len(sinyal) < 2 * n:
            continue
        urut = sinyal.sort_values(ascending=False)
        atas, bawah = list(urut.index[:n]), list(urut.index[-n:])
        masuk = [s for s in atas if s not in lama]
        keluar = [s for s in lama if s not in atas]
        harga = {s: float(siap[s].at[t, "close_mentah"]) if t in siap[s].index else np.nan for s in set(masuk) | set(keluar)}
        drag = sum(biaya_sisi(harga[s], True) for s in masuk if np.isfinite(harga[s])) / len(atas)
        if lama:
            drag += sum(biaya_sisi(harga[s], False) for s in keluar if np.isfinite(harga[s])) / len(lama)
        kotor = ret[atas].mean()
        hasil.append({"bulan": t2.to_period("M"), "universe": len(uni), "liputan": len(sinyal) / len(uni) * 100, "n": n,
                      "atas_kotor": kotor * 100, "bawah_kotor": ret[bawah].mean() * 100, "pembanding": ret.mean() * 100,
                      "atas_bersih": (kotor - drag) * 100, "biaya": drag * 100, "ganti": len(masuk)})
        lama = atas
    h = pd.DataFrame(hasil)
    h["selisih"] = h["atas_bersih"] - h["pembanding"]
    return h


def nilai_a(h, nama, lengkap=True):
    rng = np.random.default_rng(15)
    boot = np.percentile([rng.choice(h["selisih"], len(h)).mean() for _ in range(10000)], 5)
    h = h.copy()
    h["tahun"] = h["bulan"].dt.year
    per_tahun = h.groupby("tahun").apply(lambda g: ((1 + g["atas_bersih"] / 100).prod() / (1 + g["pembanding"] / 100).prod() - 1) * 100, include_groups=False)
    syarat = {
        "(1) rata-rata selisih bulanan bersih > 0": h["selisih"].mean() > 0,
        "(2) bootstrap 5% selisih > 0": boot > 0,
        "(3) tahun positif >= 70%": (per_tahun > 0).mean() * 100 >= SYARAT_TAHUN,
        "(4) desil atas kotor > desil bawah kotor": h["atas_kotor"].mean() > h["bawah_kotor"].mean(),
        "(5) liputan KSEI >= 80%": h["liputan"].mean() >= LIPUTAN_MIN,
    }
    if not lengkap:
        syarat = {k: v for k, v in syarat.items() if k[:3] in ("(1)", "(3)", "(4)")}
    print(f"\n### H15a {nama}: {len(h)} bulan, universe rata-rata {h['universe'].mean():.0f} saham, desil {h['n'].mean():.0f} saham, "
          f"liputan {h['liputan'].mean():.0f}%, ganti {h['ganti'].mean():.1f} saham/bulan, biaya {h['biaya'].mean():.2f}%/bulan")
    print(f"rata-rata per bulan: desil atas kotor {h['atas_kotor'].mean():+.2f}% | bersih {h['atas_bersih'].mean():+.2f}% | "
          f"desil bawah kotor {h['bawah_kotor'].mean():+.2f}% | pembanding {h['pembanding'].mean():+.2f}% | selisih {h['selisih'].mean():+.2f}% "
          f"(bootstrap 5%: {boot:+.2f}%)")
    print("selisih per tahun (%): " + ", ".join(f"{t}: {v:+.1f}" for t, v in per_tahun.items()))
    for k, v in syarat.items():
        print(f"  {'LULUS' if v else 'GAGAL'}  {k}")
    lulus = all(syarat.values())
    print(f"=> H15a {nama}: {'LULUS' if lulus else 'GAGAL'} ({sum(syarat.values())}/{len(syarat)})")
    return lulus


def tandai_b(tr, ks):
    t = tr.sort_values("tgl").reset_index(drop=True)
    t["tgl"] = t["tgl"].astype("datetime64[ns]")
    k = ks.dropna(subset=["d_ritel"]).sort_values("tersedia").copy()
    k["tersedia"] = k["tersedia"].astype("datetime64[ns]")
    m = pd.merge_asof(t, k[["kode", "tersedia", "d_ritel"]].rename(columns={"kode": "ticker"}), left_on="tgl", right_on="tersedia",
                      by="ticker", direction="backward", tolerance=pd.Timedelta(days=JEDA_HARI + 45))
    m["h15b"] = m["d_ritel"] <= 0
    return m


def uji_b(ks):
    regime = h13.regime_ihsg()
    non = [k.strip()[:-3] for k in dt.baca_daftar("nonsyariah_kode")]
    sets = [
        ("dev 217 syariah 2010-2019", lambda: h13.siapkan(sorted(sc.daftar_syariah()), "2019-12-31"), "2010-01-01", "2019-12-31"),
        ("A non-syariah 2020-2026", lambda: h13.siapkan(non), "2020-01-01", "2026-12-31"),
        ("syariah DES 2020-2026", ut.siapkan_holdout, "2020-01-01", "2026-12-31"),
    ]
    baris = []
    for nama, buat, mulai, akhir in sets:
        siap = buat()
        tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
        tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)]
        tr = tandai_b(tr, ks)
        print(f"\n{nama}: {len(tr)} sinyal-trade, tanpa data KSEI {tr['d_ritel'].isna().sum()} ({tr['d_ritel'].isna().mean() * 100:.0f}%), "
              f"lolos H15b {tr['h15b'].mean() * 100:.0f}%")
        for label, t in [("H11a", tr), ("H15b", tr[tr["h15b"]])]:
            m = h13.metrik(h13.portofolio(t, False, False, False, regime), pd.Timestamp(mulai), pd.Timestamp(akhir))
            baris.append({"set": nama, "konfig": label, "sinyal": len(t), "net/trade": round(t["net"].mean(), 2), **m})
    hasil = pd.DataFrame(baris)
    print("\n" + hasil.to_string(index=False))
    dt.simpan_hasil(f"hasil_h15b", hasil.reset_index(drop=True))
    ok = all(
        hasil[(hasil.set == s) & (hasil.konfig == "H15b")]["net/trade"].iloc[0] > hasil[(hasil.set == s) & (hasil.konfig == "H11a")]["net/trade"].iloc[0]
        and hasil[(hasil.set == s) & (hasil.konfig == "H15b")]["MAR"].iloc[0] > hasil[(hasil.set == s) & (hasil.konfig == "H11a")]["MAR"].iloc[0]
        for s in hasil["set"].unique())
    print(f"\nkeputusan H15b (net/trade DAN MAR lebih tinggi dari H11a di ketiga set): {'DIADOPSI' if ok else 'tidak diadopsi'}")


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("uji", choices=["a", "b"])
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    ks = baca_ksei()
    if a.uji == "b":
        uji_b(ks)
        return
    if not a.holdout:
        siap = h13.siapkan(sorted(sc.daftar_syariah()), DEV_A[1])
        h = simulasi_a(siap, ks, *DEV_A)
        dt.simpan_hasil(f"hasil_h15a_dev", h.reset_index(drop=True))
        lulus = nilai_a(h, "dev 2011-2019")
        dt.hasil_teks("status_h15a").write_text("LULUS" if lulus else "GAGAL", encoding="utf-8")
        return
    status = dt.hasil_teks("status_h15a")
    if not status.exists() or status.read_text(encoding="utf-8").strip() != "LULUS":
        print("DITOLAK: holdout H15a hanya dibuka kalau dev LULUS.")
        return
    if PENANDA.exists():
        print(f"DITOLAK: holdout H15a sudah dibuka ({PENANDA.read_text()}).")
        return
    PENANDA.write_text(pd.Timestamp.now().isoformat())
    des = des_ojk.baca()
    siap = h13.siapkan(sorted(set(des["kode"])))
    h = simulasi_a(siap, ks, *HOLDOUT_A, des=des)
    dt.simpan_hasil(f"hasil_h15a_holdout", h.reset_index(drop=True))
    nilai_a(h, "holdout 2020-2026", lengkap=False)


if __name__ == "__main__":
    utama()
