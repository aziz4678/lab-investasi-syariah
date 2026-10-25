import argparse

import numpy as np
import pandas as pd

from backend.app.services import valuasi as vl
from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc

PAJAK = 0.10
JUMLAH = 10
MIN_CALON = 5
DEPOSITO = 5.0
DEV = (2014, 2019)
HOLDOUT = (2020, 2026)
H17B = (2021, 2026)
PENANDA = d.penanda("holdout_dibuka_h17a")


def biaya(harga, beli):
    return (sc.FEE_BELI if beli else sc.FEE_JUAL) / 100 + float(sc.fraksi(harga)) / harga


def muat_harga(kode):
    data = {}
    for k in kode:
        m = baca_mentah(k)
        if m is None or len(m) < 60:
            continue
        m = m.copy()
        m["dividends"] = m["dividends"].fillna(0) if "dividends" in m else 0.0
        m["nilai20"] = (m["close"] * m["volume"]).rolling(20).mean()
        data[k] = m
    return data


def kalender(data):
    hit = pd.Series([t for m in data.values() for t in m.index]).value_counts()
    return pd.DatetimeIndex(sorted(hit[hit >= max(10, 0.3 * len(data))].index))


def nilai_pada(s, t):
    x = s[s.index <= t]
    return float(x.iloc[-1]) if len(x) else np.nan


def harga_buka(m, t):
    if t in m.index and np.isfinite(m.at[t, "open"]) and m.at[t, "open"] > 0:
        return float(m.at[t, "open"])
    return nilai_pada(m["close"], t)


def filter_antitrap(k, m, t, dps12):
    lap = vl.laporan(k)
    sh = vl.saham(k)
    if lap.empty or sh.empty:
        return False, "tanpa laporan"
    r = vl.pada(lap, t)
    if r is None:
        return False, "tanpa laporan"
    n = vl.saham_pada(sh, t, vl.split_dari(m))
    fx = vl.nilai_kurs(r, t)
    if not np.isfinite(n) or not np.isfinite(r["laba_ttm"]):
        return False, "data kurang"
    eps = r["laba_ttm"] * fx / n
    if eps <= 0 or dps12 > eps:
        return False, "payout > 100% / rugi"
    g = vl.tumbuh(r["laba_ttm"], r["laba_ttm_1"])
    if g is not None and g < -30:
        return False, "laba turun > 30%"
    bank = np.isnan(r.get("pendapatan", np.nan)) and np.isnan(r.get("aset_lancar", np.nan))
    if not bank and r["ekuitas_total"] and r["ekuitas_total"] > 0 and r["liabilitas"] / r["ekuitas_total"] > 2:
        return False, "DER > 2"
    if np.isfinite(r["arus_kas_operasi_ttm"]) and r["arus_kas_operasi_ttm"] * fx < dps12 * n:
        return False, "arus kas < dividen"
    return True, ""


def pilih(data, kode_univ, t, tahun, antitrap=False):
    calon, univ, alasan_buang = [], [], {}
    for k in kode_univ:
        m = data.get(k)
        if m is None:
            continue
        hrg = m["close"][m.index <= t]
        if hrg.empty or (t - hrg.index[-1]).days > 10:
            continue
        p = float(hrg.iloc[-1])
        if p < sc.HARGA_MIN or not (nilai_pada(m["nilai20"], t) >= sc.MIN_VALUE):
            continue
        univ.append(k)
        dv = m["dividends"]
        if not all(dv[dv.index.year == y].sum() > 0 for y in (tahun - 3, tahun - 2, tahun - 1)):
            continue
        dps12 = float(dv[(dv.index > t - pd.Timedelta(days=365)) & (dv.index <= t)].sum())
        if dps12 <= 0:
            continue
        if antitrap:
            akhir, sebelum = dv[dv.index.year == tahun - 1].sum(), dv[dv.index.year == tahun - 2].sum()
            if sebelum > 0 and akhir < 0.7 * sebelum:
                alasan_buang[k] = "dividen dipotong"
                continue
            ok, why = filter_antitrap(k, m, t, dps12)
            if not ok:
                alasan_buang[k] = why
                continue
        calon.append((k, dps12 / p * 100))
    calon.sort(key=lambda x: -x[1])
    terpilih = [k for k, _ in calon[:JUMLAH]] if len(calon) >= MIN_CALON else [k for k, _ in calon]
    return terpilih, dict(calon), univ, alasan_buang


def hasil_saham(m, e, x):
    a, b = harga_buka(m, e), harga_buka(m, x)
    if not (np.isfinite(a) and a > 0):
        return None
    if not np.isfinite(b):
        b = nilai_pada(m["close"], x)
    dv = m["dividends"]
    div = float(dv[(dv.index >= e) & (dv.index < x)].sum()) * (1 - PAJAK)
    bulan = sorted({int(t.month) for t in dv[(dv.index >= e) & (dv.index < x) & (dv > 0)].index})
    return {"harga": (b / a - 1) * 100, "penghasilan": div / a * 100, "total": ((b + div) / a - 1) * 100, "masuk": a, "keluar": b, "bulan": bulan}


def simulasi(data, des, daftar217, tahun_awal, tahun_akhir, antitrap=False):
    kal = kalender(data)
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    baris, lama = [], []
    for th in range(tahun_awal, tahun_akhir + 1):
        t = kal[kal <= pd.Timestamp(f"{th - 1}-12-31")].max()
        e = kal[kal > t].min()
        x = kal[kal >= pd.Timestamp(f"{th + 1}-01-01")].min()
        parsial = pd.isna(x)
        if parsial:
            x = kal.max()
        univ_kode = sorted(daftar217) if th <= 2019 else sorted(des_ojk.syariah_pada(des, t))
        pil, yld, univ, buang = pilih(data, univ_kode, t, th, antitrap)
        hs = {k: hasil_saham(data[k], e, x) for k in pil}
        hs = {k: v for k, v in hs.items() if v}
        hb = [hasil_saham(data[k], e, x) for k in univ]
        hb = [v for v in hb if v]
        drag = 0.0
        if hs:
            masuk = [k for k in hs if k not in lama]
            drag = sum(biaya(hs[k]["masuk"], True) for k in masuk) / len(hs) * 100
        port_total = np.mean([v["total"] for v in hs.values()]) - drag if hs else 0.0
        baris.append({
            "tahun": th, "parsial": parsial, "dari": e.date(), "sampai": x.date(), "jumlah": len(hs), "saham": " ".join(hs),
            "yield_masuk": np.mean([yld[k] for k in hs]) if hs else np.nan,
            "penghasilan": np.mean([v["penghasilan"] for v in hs.values()]) if hs else 0.0,
            "harga": np.mean([v["harga"] for v in hs.values()]) if hs else 0.0,
            "total": port_total, "biaya": drag, "ganti": len([k for k in hs if k not in lama]),
            "pembanding_total": np.mean([v["total"] for v in hb]) if hb else np.nan,
            "pembanding_penghasilan": np.mean([v["penghasilan"] for v in hb]) if hb else np.nan,
            "universe": len(univ), "ihsg": (nilai_pada(ihsg, x) / nilai_pada(ihsg, e) - 1) * 100,
            "bulan": sorted({b for v in hs.values() for b in v["bulan"]}), "dibuang": buang,
        })
        lama = list(hs)
    df = pd.DataFrame(baris)
    jual_biaya = []
    for i in range(len(df)):
        kini = set(df.loc[i, "saham"].split())
        nanti = set(df.loc[i + 1, "saham"].split()) if i + 1 < len(df) else set()
        keluar = [k for k in kini if k not in nanti]
        b = 0.0
        for k in keluar:
            m = data[k]
            px = nilai_pada(m["close"], pd.Timestamp(df.loc[i, "sampai"]))
            if np.isfinite(px) and px > 0:
                b += biaya(px, False)
        jual_biaya.append(b / max(1, len(kini)) * 100 if i + 1 < len(df) else 0.0)
    df["total"] = df["total"] - jual_biaya
    df["biaya"] = df["biaya"] + jual_biaya
    return df


def ringkas(df, kolom="total"):
    n = len(df)
    lama = sum((pd.Timestamp(r.sampai) - pd.Timestamp(r.dari)).days for r in df.itertuples()) / 365.25
    cagr = ((1 + df[kolom] / 100).prod() ** (1 / lama) - 1) * 100 if lama > 0 else np.nan
    return cagr


def penghasilan_rp(df):
    nilai, hasil = 100.0, []
    for r in df.itertuples():
        hasil.append(nilai * r.penghasilan / 100)
        nilai *= 1 + r.total / 100
    return hasil


def nilai_h17a(df, nama, lengkap=True):
    penuh = df[~df["parsial"]]
    cagr, cagr_b = ringkas(df), ringkas(df, "pembanding_total")
    syarat = {
        "(1) CAGR bersih >= pembanding": cagr >= cagr_b,
        "(2) rata-rata yield penghasilan >= 4%": penuh["penghasilan"].mean() >= 4,
        "(3) penghasilan >= 3% di >= 80% tahun": (penuh["penghasilan"] >= 3).mean() >= 0.8,
        "(4) tahun terburuk >= pembanding terburuk - 5": df["total"].min() >= df["pembanding_total"].min() - 5,
    }
    if not lengkap:
        syarat = {k: v for k, v in syarat.items() if not k.startswith("(4)")}
    cetak(df, nama, cagr, cagr_b)
    for k, v in syarat.items():
        print(f"  {'LULUS' if v else 'GAGAL'}  {k}")
    lulus = all(syarat.values())
    print(f"=> {nama}: {'LULUS' if lulus else 'GAGAL'} ({sum(syarat.values())}/{len(syarat)})")
    return lulus


def cetak(df, nama, cagr, cagr_b):
    print(f"\n### {nama}")
    tampil = df[["tahun", "jumlah", "yield_masuk", "penghasilan", "harga", "total", "biaya", "pembanding_penghasilan", "pembanding_total", "ihsg", "saham"]].copy()
    tampil["tahun"] = tampil["tahun"].astype(str) + np.where(df["parsial"], "*", "")
    print(tampil.round(1).to_string(index=False))
    rp = penghasilan_rp(df)
    turun = sum(1 for a, b in zip(rp, rp[1:]) if a > 0 and b < 0.7 * a)
    penuh = df[~df["parsial"]]
    print(f"CAGR bersih {cagr:+.1f}% vs pembanding {cagr_b:+.1f}% vs deposito {DEPOSITO:.1f}% | yield penghasilan rata-rata {penuh['penghasilan'].mean():.1f}% "
          f"(pembanding {penuh['pembanding_penghasilan'].mean():.1f}%) | tahun penghasilan turun > 30%: {turun} | biaya rata-rata {df['biaya'].mean():.2f}%/th")
    print("(* = tahun berjalan, belum penuh)")
    return turun


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("uji", choices=["a", "b"])
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    des = des_ojk.baca()
    daftar217 = sc.daftar_syariah()
    kode = sorted(set(des["kode"]) | set(daftar217))
    print(f"memuat harga & dividen {len(kode)} kode...")
    data = muat_harga(kode)
    status = dt.hasil_teks("status_h17a")
    if a.uji == "a" and not a.holdout:
        df = simulasi(data, des, daftar217, *DEV)
        dt.simpan_hasil(f"hasil_h17a_dev", df.reset_index(drop=True))
        lulus = nilai_h17a(df, "H17a dev 2014-2019")
        status.write_text("LULUS" if lulus else "GAGAL", encoding="utf-8")
        return
    if a.uji == "a":
        if not status.exists() or status.read_text(encoding="utf-8").strip() != "LULUS":
            print("DITOLAK: holdout H17a hanya dibuka kalau dev LULUS.")
            return
        if PENANDA.exists():
            print(f"DITOLAK: holdout H17a sudah dibuka ({PENANDA.read_text()}).")
            return
        PENANDA.write_text(pd.Timestamp.now().isoformat())
        df = simulasi(data, des, daftar217, *HOLDOUT)
        dt.simpan_hasil(f"hasil_h17a_holdout", df.reset_index(drop=True))
        nilai_h17a(df, "H17a holdout 2020-2026", lengkap=False)
        return
    da = simulasi(data, des, daftar217, *H17B)
    db = simulasi(data, des, daftar217, *H17B, antitrap=True)
    dt.simpan_hasil(f"hasil_h17a_2021", da.reset_index(drop=True))
    dt.simpan_hasil(f"hasil_h17b", db.reset_index(drop=True))
    turun_a = cetak(da, "H17a 2021-2026 (pembanding)", ringkas(da), ringkas(da, "pembanding_total"))
    turun_b = cetak(db, "H17b dividen + anti-trap 2021-2026", ringkas(db), ringkas(db, "pembanding_total"))
    syarat = {
        "CAGR bersih > H17a": ringkas(db) > ringkas(da),
        "tahun penghasilan turun > 30% lebih sedikit": turun_b < turun_a,
        "rata-rata yield penghasilan >= 4%": db[~db["parsial"]]["penghasilan"].mean() >= 4,
    }
    for k, v in syarat.items():
        print(f"  {'LULUS' if v else 'GAGAL'}  {k}")
    print(f"=> H17b: {'DIADOPSI' if all(syarat.values()) else 'tidak diadopsi'}")
    semua_buang = pd.Series([w for x in db["dibuang"] for w in x.values()]).value_counts()
    print("alasan saham dibuang saringan anti-trap:", semua_buang.to_dict())


if __name__ == "__main__":
    utama()
