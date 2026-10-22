import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.api import valuasi as vl
from backend.api.emiten import baca_mentah
from backend.db import koneksi as d
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset import uji_h13 as h13
from backend.riset.uji_h15 import biaya_sisi, harga_buka, kalender

MULAI_PANEL = pd.Timestamp("2019-01-31")
DEV = ("2021-04", "2023-12")
HOLDOUT = ("2024-01", "2026-09")
PENANDA = d.penanda("holdout_dibuka_h16")
PENANDA_C = d.penanda("holdout_dibuka_h16c")


def panel_kode(kode, akhir_bulan, des, info):
    lap = vl.laporan(kode)
    sh = vl.saham(kode)
    m = baca_mentah(kode)
    if lap.empty or sh.empty or m is None or len(m) < 30:
        return []
    c = m["close"]
    div = m["dividends"].fillna(0) if "dividends" in m else pd.Series(0.0, index=m.index)
    nilai_tx = (m["close"] * m["volume"]).rolling(20).mean()
    ma200 = c.rolling(200).mean()
    split = vl.split_dari(m)
    sektor, industri = info.get(kode, (None, None))
    baris = []
    for t in akhir_bulan:
        hrg = c[c.index <= t]
        if hrg.empty or (t - hrg.index[-1]).days > 10:
            continue
        r = vl.pada(lap, t)
        n = vl.saham_pada(sh, t, split)
        if r is None or not np.isfinite(n):
            continue
        p = float(hrg.iloc[-1])
        fx = vl.nilai_kurs(r, t)
        laba, ek = r["laba_ttm"], r["ekuitas"]
        if not (np.isfinite(laba) and np.isfinite(ek)):
            continue
        eps, bv = laba * fx / n, ek * fx / n
        dps = float(div[(div.index > t - pd.Timedelta(days=365)) & (div.index <= t)].sum())
        tahun_div = sum(1 for y in range(t.year - 3, t.year) if div[div.index.year == y].sum() > 0)
        audit = lap[(lap["periode"] == "AUDIT") & (lap["tgl_publikasi"] <= t)].sort_values("tahun").tail(3)
        roe_th = [a.laba / a.ekuitas * 100 for a in audit.itertuples() if a.ekuitas and a.ekuitas > 0]
        pend, pend1 = r["pendapatan_ttm"], r["pendapatan_ttm_1"]
        bank = sektor in vl.KEUANGAN or (np.isnan(r.get("pendapatan", np.nan)) and np.isnan(r.get("aset_lancar", np.nan)))
        baris.append({
            "kode": kode, "tgl": t, "harga": p, "eps": eps, "bvps": bv, "laba": laba,
            "per": p / eps if eps > 0 else np.nan, "pbv": p / bv if bv > 0 else np.nan,
            "dps": dps, "tahun_div": tahun_div, "payout": dps / eps * 100 if eps > 0 and dps > 0 else np.nan,
            "roe3": roe_th if len(roe_th) == 3 else None,
            "der": r["liabilitas"] / r["ekuitas_total"] if r["ekuitas_total"] and r["ekuitas_total"] > 0 else np.nan,
            "cfo": r["arus_kas_operasi_ttm"],
            "g3": vl.cagr(laba, r["laba_ttm_3"], 3), "g1": vl.tumbuh(laba, r["laba_ttm_1"]),
            "npm": laba / pend * 100 if np.isfinite(pend) and pend > 0 else np.nan,
            "npm1": r["laba_ttm_1"] / pend1 * 100 if np.isfinite(pend1) and pend1 > 0 else np.nan,
            "cr": r["aset_lancar"] / r["liabilitas_lancar"] if np.isfinite(r.get("aset_lancar", np.nan)) and r.get("liabilitas_lancar", 0) > 0 else np.nan,
            "nilai_tx": float(nilai_tx[nilai_tx.index <= t].iloc[-1]) if (nilai_tx.index <= t).any() else np.nan,
            "ma200": float(ma200[ma200.index <= t].iloc[-1]) if (ma200.index <= t).any() else np.nan,
            "sektor": sektor, "industri": industri, "bank": bool(bank), "siklikal": sektor in vl.SIKLIKAL,
        })
    return baris


def bangun_panel(kode_semua, akhir_bulan, des, info=None):
    info = info or {x["ticker"][:-3]: (x.get("sector"), x.get("industry")) for x in d.koneksi().info_saham.find({}, {"ticker": 1, "sector": 1, "industry": 1})}
    semua = []
    for i, k in enumerate(kode_semua):
        semua += panel_kode(k, akhir_bulan, des, info)
        if (i + 1) % 100 == 0:
            print(f"  panel {i + 1}/{len(kode_semua)} kode")
    return pd.DataFrame(semua)


def median_grup(x, kolom, nilai):
    g = x[x[kolom] == nilai]
    if len(g) < 4:
        return None
    return {"per": g["per"][g["per"] > 0].median(), "pbv": g["pbv"][g["pbv"] > 0].median()}


def nilai_bulan(panel, t, syariah):
    x = panel[(panel["tgl"] == t) & panel["kode"].isin(syariah)]
    riw = panel[(panel["tgl"] <= t) & (panel["tgl"] > t - pd.DateOffset(years=vl.TAHUN_BAND))]
    hasil = []
    for r in x.itertuples():
        h = riw[riw["kode"] == r.kode]
        per_h, pbv_h = h["per"].dropna(), h["pbv"].dropna()
        med_per = per_h.median() if len(per_h) >= vl.BULAN_MIN else np.nan
        med_pbv = pbv_h.median() if len(pbv_h) >= vl.BULAN_MIN else np.nan
        peer = (median_grup(x, "industri", r.industri) if r.industri else None) or (median_grup(x, "sektor", r.sektor) if r.sektor else None)
        metode = []
        if r.eps > 0 and np.isfinite(med_per) and not r.siklikal and not r.bank:
            metode.append(r.eps * med_per)
        if r.bvps > 0 and np.isfinite(med_pbv):
            metode.append(r.bvps * med_pbv)
        if r.eps > 0 and r.bvps > 0 and not r.bank:
            metode.append((22.5 * r.eps * r.bvps) ** 0.5)
        if peer and r.eps > 0 and np.isfinite(peer["per"]) and not r.siklikal and not r.bank:
            metode.append(r.eps * peer["per"])
        if peer and r.bvps > 0 and np.isfinite(peer["pbv"]):
            metode.append(r.bvps * peer["pbv"])
        if r.tahun_div == 3 and r.dps > 0 and np.isfinite(r.payout) and r.payout >= vl.PAYOUT_DDM:
            g = min(max((r.g3 or 0) / 100, 0), vl.G_DDM_MAKS)
            metode.append(r.dps * (1 + g) / (vl.R_DDM - g))
        wajar = float(np.median(metode)) if metode and r.laba > 0 else np.nan
        mos = (wajar - r.harga) / wajar * 100 if np.isfinite(wajar) and wajar > 0 else np.nan
        cek = [
            all(v > vl.ROE_MIN for v in r.roe3) if r.roe3 else None,
            (r.der < vl.DER_MAKS) if np.isfinite(r.der) and not r.bank else None,
            (r.cfo > 0 and r.cfo >= r.laba) if np.isfinite(r.cfo) else None,
            (r.g3 > 0) if r.g3 is not None else ((r.g1 > 0) if r.g1 is not None else None),
            (r.npm >= r.npm1) if np.isfinite(r.npm) and np.isfinite(r.npm1) and not r.bank else None,
            (r.cr > 1) if np.isfinite(r.cr) and not r.bank else None,
            (r.nilai_tx >= vl.NILAI_MIN) if np.isfinite(r.nilai_tx) else None,
        ]
        berlaku = [c for c in cek if c is not None]
        skor = sum(berlaku)
        layak = np.isfinite(mos) and mos >= vl.MOS_MURAH and skor >= len(berlaku) - 1 and np.isfinite(r.ma200) and r.harga >= r.ma200
        hasil.append({"kode": r.kode, "mos": mos, "undervalue": np.isfinite(mos) and mos >= vl.MOS_MURAH,
                      "berkualitas": bool(np.isfinite(mos) and mos >= vl.MOS_MURAH and berlaku and skor > len(berlaku) / 2),
                      "overvalue": np.isfinite(mos) and mos < vl.MOS_MAHAL, "layak": bool(layak), "skor": skor, "maks": len(berlaku),
                      "harga": r.harga, "per": r.per, "pbv": r.pbv, "jml_metode": len(metode),
                      "pbv_z": (r.pbv - pbv_h.mean()) / pbv_h.std() if len(pbv_h) >= vl.BULAN_MIN and pbv_h.std() > 0 and np.isfinite(r.pbv) else np.nan,
                      "roe": r.eps / r.bvps * 100 if r.bvps > 0 else np.nan, "der": r.der, "g1": r.g1, "g3": r.g3,
                      "dy": r.dps / r.harga * 100 if r.harga > 0 else np.nan, "jarak_ma200": (r.harga / r.ma200 - 1) * 100 if np.isfinite(r.ma200) else np.nan,
                      "sektor": r.sektor, "siklikal": r.siklikal, "bank": r.bank, "cek": cek, "wajar": wajar,
                      "sikap": "layak" if layak else ("hindari" if r.laba <= 0 or (berlaku and skor <= len(berlaku) / 2) else "pantau")})
    return pd.DataFrame(hasil)


def simulasi(siap, panel, des, mulai, akhir):
    kal = kalender(siap)
    akhir_bln = pd.Series(kal, index=kal).groupby(kal.to_period("M")).max()
    tgl = [t for t in akhir_bln if pd.Period(mulai, "M") - 1 <= t.to_period("M") <= pd.Period(akhir, "M")]
    likuid = {}
    for k, x in siap.items():
        nol = (x["volume"] == 0).rolling(5).sum()
        likuid[k] = (x["value_mentah"] >= sc.MIN_VALUE) & (x["close_mentah"] >= sc.HARGA_MIN) & (nol == 0)
    lama = {"undervalue": [], "layak": [], "overvalue": [], "berkualitas": []}
    baris = []
    for i in range(len(tgl) - 1):
        t, t2 = tgl[i], tgl[i + 1]
        e, k = kal[kal > t].min(), kal[kal > t2].min()
        if pd.isna(e) or pd.isna(k):
            break
        syariah = des_ojk.syariah_pada(des, t)
        bulan_akhir = panel["tgl"][panel["tgl"].dt.to_period("M") == t.to_period("M")]
        if bulan_akhir.empty:
            continue
        v = nilai_bulan(panel, bulan_akhir.iloc[0], syariah)
        if v.empty:
            continue
        v = v[v["kode"].map(lambda s: s in siap and t in siap[s].index and bool(likuid[s].get(t, False)))]
        v = v[np.isfinite(v["mos"])]
        if len(v) < 10:
            continue
        ret = {}
        for s in v["kode"]:
            a, b = harga_buka(siap[s], e), harga_buka(siap[s], k)
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                ret[s] = b / a - 1
        ret = pd.Series(ret)
        v = v[v["kode"].isin(ret.index)]
        b0 = {"bulan": t2.to_period("M"), "universe": len(v), "pembanding": ret.mean() * 100}
        for g in lama:
            isi = list(v.loc[v[g], "kode"])
            b0[f"n_{g}"] = len(isi)
            if not isi:
                b0[f"{g}_kotor"] = np.nan
                b0[f"{g}_bersih"] = 0.0
                lama[g] = []
                continue
            masuk = [s for s in isi if s not in lama[g]]
            keluar = [s for s in lama[g] if s not in isi]
            harga = lambda s: float(siap[s].at[t, "close_mentah"]) if t in siap[s].index else np.nan
            drag = sum(biaya_sisi(harga(s), True) for s in masuk if np.isfinite(harga(s))) / len(isi)
            if lama[g]:
                drag += sum(biaya_sisi(harga(s), False) for s in keluar if np.isfinite(harga(s))) / len(lama[g])
            kotor = ret[isi].mean()
            b0[f"{g}_kotor"] = kotor * 100
            b0[f"{g}_bersih"] = (kotor - drag) * 100
            lama[g] = isi
        baris.append(b0)
    return pd.DataFrame(baris)


def nilai(h, g, nama, lengkap=True, banding=None):
    x = h.copy()
    x["selisih"] = x[f"{g}_bersih"] - x["pembanding"]
    x.loc[x[f"n_{g}"] == 0, "selisih"] = 0 - x["pembanding"]
    rng = np.random.default_rng(16)
    boot = np.percentile([rng.choice(x["selisih"], len(x)).mean() for _ in range(10000)], 5)
    x["tahun"] = x["bulan"].dt.year
    per_tahun = x.groupby("tahun").apply(lambda q: ((1 + q[f"{g}_bersih"] / 100).prod() / (1 + q["pembanding"] / 100).prod() - 1) * 100, include_groups=False)
    syarat = {
        "(1) rata-rata selisih bulanan bersih > 0": x["selisih"].mean() > 0,
        "(2) bootstrap 5% selisih > 0": boot > 0,
        "(3) selisih tahunan positif >= 2 dari 3 tahun": (per_tahun > 0).sum() >= 2,
        "(4) kotor > kelompok Overvalue": x[f"{g}_kotor"].mean() > x["overvalue_kotor"].mean(),
        "(5) rata-rata isi >= 5 saham": x[f"n_{g}"].mean() >= 5,
    }
    if banding:
        sel_b = x[f"{banding}_bersih"] - x["pembanding"]
        print(f"pembanding filter: {banding.upper()} selisih {sel_b.mean():+.2f}%/bulan, isi {x[f'n_{banding}'].mean():.1f} saham")
        syarat["(6) selisih > " + banding.upper()] = x["selisih"].mean() > sel_b.mean()
    if not lengkap:
        syarat = {k: v for k, v in syarat.items() if k[:3] in ("(1)", "(3)", "(4)", "(6)")}
    print(f"\n### {g.upper()} {nama}: {len(x)} bulan, universe rata-rata {x['universe'].mean():.0f}, isi rata-rata {x[f'n_{g}'].mean():.1f} saham "
          f"(bulan kosong {(x[f'n_{g}'] == 0).mean() * 100:.0f}%)")
    print(f"rata-rata/bulan: kotor {x[f'{g}_kotor'].mean():+.2f}% | bersih {x[f'{g}_bersih'].mean():+.2f}% | Overvalue kotor {x['overvalue_kotor'].mean():+.2f}% | "
          f"pembanding {x['pembanding'].mean():+.2f}% | selisih {x['selisih'].mean():+.2f}% (bootstrap 5%: {boot:+.2f}%)")
    print("selisih per tahun (%): " + ", ".join(f"{t}: {v:+.1f}" for t, v in per_tahun.items()))
    for k, v in syarat.items():
        print(f"  {'LULUS' if v else 'GAGAL'}  {k}")
    lulus = all(syarat.values())
    print(f"=> {g.upper()} {nama}: {'LULUS' if lulus else 'GAGAL'} ({sum(syarat.values())}/{len(syarat)})")
    return lulus


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--varian", choices=["ab", "c"], default="ab")
    a = ap.parse_args()
    if a.varian == "c":
        return utama_c(a.holdout)
    des = des_ojk.baca()
    kode = sorted(set(des["kode"]) & set(d.koneksi().fundamental.distinct("kode")))
    status = dt.hasil_teks("status_h16")
    if a.holdout:
        if not status.exists() or "LULUS" not in status.read_text(encoding="utf-8"):
            print("DITOLAK: holdout H16 hanya dibuka kalau dev H16a atau H16b LULUS.")
            return
        if PENANDA.exists():
            print(f"DITOLAK: holdout H16 sudah dibuka ({PENANDA.read_text()}).")
            return
        PENANDA.write_text(pd.Timestamp.now().isoformat())
    periode = HOLDOUT if a.holdout else DEV
    akhir_bulan = list(pd.date_range(MULAI_PANEL, pd.Period(periode[1], "M").to_timestamp(how="end").normalize(), freq="ME"))
    print(f"menyiapkan harga {len(kode)} kode...")
    siap = h13.siapkan(kode)
    print("membangun panel valuasi bulanan (point-in-time)...")
    panel = bangun_panel(kode, akhir_bulan, des)
    print(f"panel: {len(panel):,} baris, {panel['kode'].nunique()} kode")
    h = simulasi(siap, panel, des, *periode)
    nama = "holdout 2024-01..2026-09" if a.holdout else "dev 2021-04..2023-12"
    dt.simpan_hasil(f"hasil_h16_{'holdout' if a.holdout else 'dev'}", h.reset_index(drop=True))
    lulus = {g: nilai(h, g, nama, lengkap=not a.holdout) for g in ["undervalue", "layak"]}
    if not a.holdout:
        status.write_text(" ".join(f"{g}:{'LULUS' if v else 'GAGAL'}" for g, v in lulus.items()), encoding="utf-8")


def utama_c(holdout):
    des = des_ojk.baca()
    kode = sorted(set(des["kode"]) & set(d.koneksi().fundamental.distinct("kode")))
    status = dt.hasil_teks("status_h16c")
    if holdout:
        if not status.exists() or status.read_text(encoding="utf-8").strip() != "LULUS":
            print("DITOLAK: holdout H16c hanya dibuka kalau dev H16c LULUS.")
            return
        if PENANDA_C.exists():
            print(f"DITOLAK: holdout H16c sudah dibuka ({PENANDA_C.read_text()}).")
            return
        PENANDA_C.write_text(pd.Timestamp.now().isoformat())
    periode = HOLDOUT if holdout else DEV
    akhir_bulan = list(pd.date_range(MULAI_PANEL, pd.Period(periode[1], "M").to_timestamp(how="end").normalize(), freq="ME"))
    print(f"menyiapkan harga {len(kode)} kode...")
    siap = h13.siapkan(kode)
    print("membangun panel valuasi bulanan (point-in-time)...")
    panel = bangun_panel(kode, akhir_bulan, des)
    h = simulasi(siap, panel, des, *periode)
    nama = "holdout 2024-01..2026-09" if holdout else "dev 2021-04..2023-12"
    dt.simpan_hasil(f"hasil_h16c_{'holdout' if holdout else 'dev'}", h.reset_index(drop=True))
    lulus = nilai(h, "berkualitas", nama, lengkap=not holdout, banding="undervalue")
    if not holdout:
        status.write_text("LULUS" if lulus else "GAGAL", encoding="utf-8")


if __name__ == "__main__":
    utama()
