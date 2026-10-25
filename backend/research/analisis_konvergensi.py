import argparse
import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research import uji_h13 as h13
from backend.research import uji_h16 as h

BATAS = pd.Timestamp("2023-12-31")
HORIZON = [21, 63, 126, 252, 504]
KONTROL_PER_KEJADIAN = 5


def jalur(c, t, target):
    p = c[(c.index > t) & (c.index <= BATAS)]
    if p.empty:
        return None
    sampai = np.flatnonzero(p.to_numpy() >= target)
    harga0 = float(c[c.index <= t].iloc[-1])
    if len(sampai):
        i = int(sampai[0])
        sebelum = p.iloc[: i + 1]
        return {"sampai": True, "hari": i + 1, "tgl_sampai": p.index[i], "turun_dulu": (sebelum.min() / harga0 - 1) * 100}
    return {"sampai": False, "hari": len(p), "tgl_sampai": None, "turun_dulu": (p.min() / harga0 - 1) * 100, "naik_maks": (p.max() / harga0 - 1) * 100}


def km(df, horizon=HORIZON):
    x = df[["hari", "sampai"]].dropna()
    if x.empty:
        return {hz: np.nan for hz in horizon}
    waktu = np.sort(x.loc[x["sampai"], "hari"].unique())
    s, hasil, j = 1.0, {}, 0
    for hz in horizon:
        while j < len(waktu) and waktu[j] <= hz:
            w = waktu[j]
            risiko = (x["hari"] >= w).sum()
            kejadian = ((x["hari"] == w) & x["sampai"]).sum()
            if risiko:
                s *= 1 - kejadian / risiko
            j += 1
        hasil[hz] = (1 - s) * 100
    return hasil


def baris_km(nama, df):
    r = km(df)
    sampai = df[df["sampai"]]
    print(f"{nama:<44} n={len(df):>4} | " + " | ".join(f"{hz}h {r[hz]:5.1f}%" for hz in HORIZON)
          + f" | median hari (yang sampai) {sampai['hari'].median():.0f}" if len(sampai) else f"{nama:<44} n={len(df):>4} | belum ada yang sampai")


def ringkas_grup(g):
    s = g[g["sampai"]]
    b = g[~g["sampai"]]
    return {"n": int(len(g)), "peluang": {str(k): (round(v, 1) if np.isfinite(v) else None) for k, v in km(g).items()},
            "median_hari": float(s["hari"].median()) if len(s) else None, "turun_dulu": float(s["turun_dulu"].median()) if len(s) else None,
            "belum_naik_maks": float(b["naik_maks"].median()) if len(b) else None, "belum_turun": float(b["turun_dulu"].median()) if len(b) else None}


def simpan_ringkas(ke, ko):
    grup_perlu = lambda df: pd.cut(df["perlu"], [0, 25, 50, 100, 10000], labels=["<25", "25-50", "50-100", ">100"])
    hasil = {
        "dibuat": datetime.now().isoformat(timespec="minutes"), "periode": "kejadian 2021-04..2026-09, harga s/d 2026-10-20",
        "perlu_median": float(ke["perlu"].median()), "semua": ringkas_grup(ke), "pembanding": ringkas_grup(ko),
        "mos": {str(k): ringkas_grup(g) for k, g in ke.groupby(pd.cut(ke["mos"], [20, 35, 50, 1000], labels=["20-35", "35-50", ">50"], right=False), observed=True)},
        "perlu": {str(k): {"undervalue": ringkas_grup(ke[grup_perlu(ke) == k]), "wajar": ringkas_grup(ko[grup_perlu(ko) == k])} for k in ["25-50", "50-100", ">100"]},
        "ihsg": {"naik": ringkas_grup(ke[ke["ihsg_naik"]]), "turun": ringkas_grup(ke[~ke["ihsg_naik"]])},
        "periode_kejadian": {p: {"undervalue": ringkas_grup(ke[ke["periode"] == p]), "wajar": ringkas_grup(ko[ko["periode"] == p])}
                             for p in ["kejadian 2021-2023", "kejadian 2024-2026"]},
    }
    dt.simpan_hasil("konvergensi_ringkas", json.loads(json.dumps(hasil)))
    print("ringkasan disimpan ke MongoDB (lab_data.hasil_riset: konvergensi_ringkas)")


def utama():
    global BATAS
    ap = argparse.ArgumentParser()
    ap.add_argument("--semua", action="store_true", help="2021-2026 (data 2024-2026 tesis Undervalue sudah dibuka)")
    a = ap.parse_args()
    if a.semua:
        BATAS = pd.Timestamp("2026-10-20")
    akhir_kejadian = pd.Timestamp("2026-09-30") if a.semua else pd.Timestamp("2023-11-30")
    des = des_ojk.baca()
    kode = sorted(set(des["kode"]) & set(d.koneksi().fundamental.distinct("kode")))
    akhir_bulan = list(pd.date_range(h.MULAI_PANEL, BATAS, freq="ME"))
    siap = h13.siapkan(kode)
    siap = {k: x[x.index <= BATAS] for k, x in siap.items()}
    panel = h.bangun_panel(kode, akhir_bulan, des)
    harga = {}
    for k in kode:
        m = baca_mentah(k)
        if m is not None:
            harga[k] = m["close"][m.index <= BATAS].dropna()
    pasar = dt.baca("pasar")["ihsg"].dropna()
    likuid = {}
    for k, x in siap.items():
        nol = (x["volume"] == 0).rolling(5).sum()
        likuid[k] = (x["value_mentah"] >= sc.MIN_VALUE) & (x["close_mentah"] >= sc.HARGA_MIN) & (nol == 0)
    bulan = sorted(t for t in panel["tgl"].unique() if pd.Timestamp("2021-03-31") <= t <= akhir_kejadian)
    rng = np.random.default_rng(22)
    aktif, kejadian, kontrol = {}, [], []
    for t in bulan:
        t = pd.Timestamp(t)
        v = h.nilai_bulan(panel, t, des_ojk.syariah_pada(des, t))
        def lk(s):
            if s not in siap:
                return False
            x = likuid[s][likuid[s].index <= t]
            return bool(x.iloc[-1]) if len(x) else False
        v = v[v["kode"].map(lk) & np.isfinite(v["mos"]) & v["kode"].isin(harga)]
        ih = pasar[pasar.index <= t]
        ihsg_naik = bool(ih.iloc[-1] > ih.tail(200).mean())
        wajar_grup = v[(v["mos"] >= -15) & (v["mos"] < 5)]
        for r in v[v["undervalue"]].itertuples():
            if r.kode in aktif and (aktif[r.kode] is None or aktif[r.kode] > t):
                continue
            perlu = (r.wajar / r.harga - 1) * 100
            j = jalur(harga[r.kode], t, r.wajar)
            if j is None:
                continue
            aktif[r.kode] = j["tgl_sampai"]
            kejadian.append({"kode": r.kode, "bulan": str(t.to_period("M")), "harga": r.harga, "target": r.wajar, "perlu": perlu, "mos": r.mos,
                             "sikap": r.sikap, "siklikal": r.siklikal, "sektor": r.sektor or "?", "skor": r.skor, "maks": r.maks, "g3": r.g3,
                             "ihsg_naik": ihsg_naik, **j})
            calon = wajar_grup["kode"].to_numpy()
            for k in rng.choice(calon, size=min(KONTROL_PER_KEJADIAN, len(calon)), replace=False) if len(calon) else []:
                p0 = float(harga[k][harga[k].index <= t].iloc[-1])
                jk = jalur(harga[k], t, p0 * (1 + perlu / 100))
                if jk:
                    kontrol.append({"kode": k, "bulan": str(t.to_period("M")), "perlu": perlu, **jk})
    ke = pd.DataFrame(kejadian)
    ko = pd.DataFrame(kontrol)
    ke["periode"] = np.where(ke["bulan"] < "2024-01", "kejadian 2021-2023", "kejadian 2024-2026")
    ko["periode"] = np.where(ko["bulan"] < "2024-01", "kejadian 2021-2023", "kejadian 2024-2026")
    dt.simpan_hasil(f"konvergensi_undervalue{'_2021_2026' if a.semua else ''}", ke.reset_index(drop=True))
    print()
    print(f"Jalur harga sampai {BATAS.date()}")
    print(f"\n===== Konvergensi ke nilai wajar, {'2021-04..2026-09' if a.semua else 'dev 2021-04..2023-12'} (jalur harga dipotong {BATAS.date()}) =====")
    print(f"{len(ke)} kejadian Undervalue dari {ke['kode'].nunique()} saham; kenaikan yang dibutuhkan median {ke['perlu'].median():.0f}% "
          f"(persentil 25/75: {ke['perlu'].quantile(.25):.0f}%/{ke['perlu'].quantile(.75):.0f}%)")
    print("\nPeluang sudah mencapai target setelah N hari bursa (Kaplan-Meier, 21 hari ≈ 1 bulan, 252 ≈ 1 tahun):")
    baris_km("Undervalue -> nilai wajar", ke)
    baris_km("Pembanding: saham Wajar, target naik sama", ko)
    if a.semua:
        for p in ["kejadian 2021-2023", "kejadian 2024-2026"]:
            baris_km(f"  Undervalue, {p}", ke[ke["periode"] == p])
            baris_km(f"  Wajar,      {p}", ko[ko["periode"] == p])
    s = ke[ke["sampai"]]
    print(f"\nYang sampai: {len(s)} kejadian. Hari bursa: median {s['hari'].median():.0f}, persentil 25/75 {s['hari'].quantile(.25):.0f}/{s['hari'].quantile(.75):.0f}. "
          f"Sebelum sampai, harga sempat turun median {s['turun_dulu'].median():.0f}% (persentil 25: {s['turun_dulu'].quantile(.25):.0f}%).")
    b = ke[~ke["sampai"]]
    print(f"Yang belum sampai: {len(b)} kejadian, diamati median {b['hari'].median():.0f} hari; kenaikan tertinggi median {b['naik_maks'].median():.0f}%, "
          f"penurunan terdalam median {b['turun_dulu'].median():.0f}%.")
    print("\nPer kelompok (peluang sampai, Kaplan-Meier):")
    ke["mos_grup"] = pd.cut(ke["mos"], [20, 35, 50, 1000], labels=["MoS 20-35%", "MoS 35-50%", "MoS > 50%"], right=False)
    ke["laba_melonjak"] = ke["g3"] > 50
    for kol in ["mos_grup", "sikap", "siklikal", "ihsg_naik", "laba_melonjak"]:
        for nilai, g in ke.groupby(kol, observed=True):
            baris_km(f"  {kol} = {nilai}", g)
    for kol in ["mos_grup"]:
        print(f"\nPembanding per kebutuhan kenaikan (saham Wajar):")
        ko["perlu_grup"] = pd.cut(ko["perlu"], [0, 25, 50, 100, 10000], labels=["naik < 25%", "naik 25-50%", "naik 50-100%", "naik > 100%"])
        ke["perlu_grup"] = pd.cut(ke["perlu"], [0, 25, 50, 100, 10000], labels=["naik < 25%", "naik 25-50%", "naik 50-100%", "naik > 100%"])
        for nilai in ke["perlu_grup"].cat.categories:
            baris_km(f"  Undervalue, butuh {nilai}", ke[ke["perlu_grup"] == nilai])
            baris_km(f"  Wajar,      butuh {nilai}", ko[ko["perlu_grup"] == nilai])
    if a.semua:
        simpan_ringkas(ke, ko)
    print("\nContoh yang sampai paling cepat dan yang belum sampai:")
    print(s.sort_values("hari")[["kode", "bulan", "harga", "target", "perlu", "hari", "turun_dulu", "sikap", "sektor"]].head(8).round(1).to_string(index=False))
    print(b.sort_values("perlu")[["kode", "bulan", "harga", "target", "perlu", "hari", "naik_maks", "turun_dulu", "sikap", "sektor"]].head(8).round(1).to_string(index=False))


if __name__ == "__main__":
    utama()
