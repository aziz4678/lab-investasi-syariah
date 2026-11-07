import argparse
import hashlib
import json
import math

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.ingest import koreksi_ksei
from backend.research import uji_h21_h22 as u

AMBANG = 0.05
SIKLUS = list(range(2011, 2020))
KUNCI = "dev_penerbitan"
KONFIGURASI = {"data": ("2010-01-01", "2020-01-31"), "sinyal_awal": "2011-01-01", "akhir": "2020-01-31"}
BESAR = 0.20

PENYEBAB = {
    (2011, "AKRA"): "HMETD", (2011, "BLTA"): "HMETD", (2011, "BSDE"): "HMETD", (2011, "BUMI"): "belum bersumber",
    (2011, "ELTY"): "HMETD", (2011, "ENRG"): "HMETD", (2011, "LPKR"): "belum bersumber", (2011, "MLPL"): "campuran",
    (2011, "MPPA"): "konversi waran", (2011, "SMRA"): "belum bersumber",
    (2012, "KIJA"): "HMETD", (2012, "LPKR"): "tanpa HMETD", (2012, "PWON"): "HMETD", (2012, "UNTR"): "HMETD",
    (2013, "ASRI"): "belum bersumber", (2013, "ELTY"): "belum bersumber",
    (2014, "BWPT"): "belum bersumber", (2014, "MLPL"): "belum bersumber", (2014, "SCMA"): "merger",
    (2015, "AISA"): "tanpa HMETD", (2015, "BUMI"): "campuran", (2015, "BWPT"): "HMETD", (2015, "MAIN"): "tanpa HMETD",
    (2016, "ADHI"): "belum bersumber", (2016, "ANTM"): "HMETD",
    (2017, "AALI"): "HMETD", (2017, "BTEK"): "HMETD", (2017, "EXCL"): "belum bersumber", (2017, "JPFA"): "tanpa HMETD",
    (2017, "JSMR"): "HMETD", (2017, "PTPP"): "HMETD", (2017, "WIKA"): "belum bersumber",
    (2018, "BUMI"): "belum bersumber", (2018, "CTRA"): "belum bersumber", (2018, "MEDC"): "belum bersumber",
    (2018, "PPRO"): "belum bersumber", (2018, "TKIM"): "konversi waran", (2018, "TPIA"): "belum bersumber",
    (2019, "BRPT"): "HMETD", (2019, "ERAA"): "belum bersumber", (2019, "ESSA"): "HMETD", (2019, "IKAI"): "campuran",
}


def siapkan():
    u.PERIODE[KUNCI] = KONFIGURASI
    return u.susun(KUNCI)


def ksei_desember():
    k = dt.baca("ksei", kolom=["kode", "tgl", "saham"])
    k = k[k["tgl"].dt.month == 12]
    return {(r.kode, r.tgl.year): (r.tgl, float(r.saham)) for r in k.itertuples()}


def penerbitan(kode, y, dec, split):
    a, b = dec.get((kode, y - 2)), dec.get((kode, y - 1))
    if a is None or b is None or a[1] <= 0:
        return np.nan, 1.0
    s = split.get(kode)
    f = 1.0
    if s is not None:
        s = s[(s.index > a[0]) & (s.index <= b[0]) & (s > 0)]
        f = float(s.prod()) if len(s) else 1.0
    return b[1] / (a[1] * f) - 1, f


def tanggal_siklus(S, y):
    tgl = S["tgl"]
    ab = S["akhir_bulan"]
    return ab.loc[pd.Period(f"{y}-01", "M")], tgl[tgl >= pd.Timestamp(f"{y}-02-01")][0], ab.loc[pd.Period(f"{y + 1}-01", "M")]


def return_saham(S, k, d0, d1):
    P = S["P"]
    o, cn = P["o"].at[d0, k], P["c_nilai"].at[d0, k]
    beli = o if o == o and o > 0 else cn
    if not (beli == beli and beli > 0):
        return np.nan
    akhir = P["c_nilai"].at[d1, k]
    return (akhir if akhir == akhir else 0.0) / beli - 1


def binomial_atas(n, m):
    return sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n


def ringkas(x):
    s = x["selisih"]
    return {"n": int(len(s)), "median": float(s.median()) if len(s) else None, "rata": float(s.mean()) if len(s) else None,
            "tertinggal_pct": float((s < 0).mean() * 100) if len(s) else None}


def efek_kuat(kej, siklus):
    s = kej["selisih"]
    tanpa5 = s.sort_values().iloc[5:]
    neg = sum(1 for r in siklus if r["n_kejadian"] and r["median_selisih"] < 0)
    k = [
        {"no": 1, "nama": "median selisih ≤ -5 poin", "nilai": float(s.median() * 100), "lulus": bool(s.median() <= -0.05)},
        {"no": 2, "nama": "rata-rata selisih ≤ -5 poin", "nilai": float(s.mean() * 100), "lulus": bool(s.mean() <= -0.05)},
        {"no": 3, "nama": "≥ 60% kejadian tertinggal", "nilai": float((s < 0).mean() * 100), "lulus": bool((s < 0).mean() >= 0.60)},
        {"no": 4, "nama": "median selisih per siklus negatif di ≥ 6 dari 9 siklus", "nilai": neg, "lulus": bool(neg >= 6)},
        {"no": 5, "nama": "rata-rata selisih tetap negatif tanpa 5 kejadian paling tertinggal", "nilai": float(tanpa5.mean() * 100), "lulus": bool(tanpa5.mean() < 0)},
    ]
    return k, all(x["lulus"] for x in k)


def sidik_ksei(kode):
    k = dt.baca("ksei", kolom=["kode", "tgl", "saham"])
    k = k[k["kode"].isin(kode)].sort_values(["kode", "tgl"])
    return hashlib.sha256(pd.util.hash_pandas_object(k[["kode", "tgl", "saham"]], index=False).values.tobytes()).hexdigest()[:16]


def jalankan():
    S = siapkan()
    dec = ksei_desember()
    split = {k: df["stock_splits"].dropna() for k, df in harga.banyak(S["kode"], kolom=["stock_splits"]).items() if "stock_splits" in df}
    semua, siklus, semua_kode = [], [], set()
    for y in SIKLUS:
        if y > 2019:
            raise RuntimeError("siklus holdout tidak boleh dihitung")
        t, d0, d1 = tanggal_siklus(S, y)
        uni = list(u.lolos(S, t, 5e9, 100))
        semua_kode.update(uni)
        baris = []
        for k in uni:
            n, f = penerbitan(k, y, dec, split)
            r = return_saham(S, k, d0, d1)
            baris.append({"siklus": y, "kode": k, "penerbitan": None if n != n else float(n), "faktor_split": f,
                          "kejadian": bool(n == n and n > AMBANG), "return": None if r != r else float(r)})
        df = pd.DataFrame(baris)
        ada = df[df["return"].notna()]
        ew = float(ada["return"].mean())
        ew_tanpa = float(ada.loc[~ada["kejadian"], "return"].mean())
        df["pembanding"] = ew
        df["selisih"] = df["return"] - ew
        kj = df[df["kejadian"] & df["return"].notna()]
        siklus.append({"siklus": y, "sinyal": t.strftime("%Y-%m-%d"), "beli": d0.strftime("%Y-%m-%d"), "akhir": d1.strftime("%Y-%m-%d"),
                       "n_universe": int(len(df)), "n_tanpa_return": int(df["return"].isna().sum()),
                       "n_tanpa_ksei": int(df["penerbitan"].isna().sum()), "n_kejadian": int(len(kj)),
                       "pembanding": ew, "pembanding_tanpa_kejadian": ew_tanpa,
                       "median_selisih": float(kj["selisih"].median()) if len(kj) else None,
                       "rata_selisih": float(kj["selisih"].mean()) if len(kj) else None})
        semua.append(df)
    df = pd.concat(semua, ignore_index=True)
    kej = df[df["kejadian"]].copy()
    tanpa_ret = kej[kej["return"].isna()]
    if len(tanpa_ret):
        raise RuntimeError(f"kejadian tanpa return: {tanpa_ret[['siklus', 'kode']].values.tolist()}")
    kunci = set(zip(kej["siklus"], kej["kode"]))
    if kunci != set(PENYEBAB):
        raise RuntimeError(f"kejadian beda dengan daftar verifikasi: baru {sorted(kunci - set(PENYEBAB))}, hilang {sorted(set(PENYEBAB) - kunci)}")
    kej["penyebab"] = [PENYEBAB[(a, b)] for a, b in zip(kej["siklus"], kej["kode"])]
    kej["selisih_tanpa_kejadian"] = kej["return"] - kej["siklus"].map({r["siklus"]: r["pembanding_tanpa_kejadian"] for r in siklus})
    k, kuat = efek_kuat(kej, siklus)
    m = int((kej["selisih"] < 0).sum())
    s = kej["selisih"]
    laporan = {
        "pembanding_tanpa_kejadian": ringkas(kej.assign(selisih=kej["selisih_tanpa_kejadian"])),
        "per_penyebab": {p: ringkas(g) for p, g in kej.groupby("penyebab")},
        "per_besar": {"5-20%": ringkas(kej[kej["penerbitan"] <= BESAR]), ">20%": ringkas(kej[kej["penerbitan"] > BESAR])},
        "tanpa_5_paling_unggul": {"rata": float(s.sort_values().iloc[:-5].mean()), "median": float(s.sort_values().iloc[:-5].median())},
        "uji_tanda": {"n": int(len(s)), "tertinggal": m, "p_satu_sisi": binomial_atas(len(s), m)},
    }
    kode = sorted(semua_kode)
    versi_data = {"ksei_versi": dt.versi("ksei"), "ksei_sidik": sidik_ksei(kode), "koreksi_ksei": len(koreksi_ksei.aturan()),
                  "harga": harga.sidik(kode, "2010-01-01", "2020-01-31")}
    hasil = {"periode": "dev", "siklus": f"Feb {SIKLUS[0]} - Jan {SIKLUS[-1] + 1}", "ambang": AMBANG,
             "ringkas": ringkas(kej), "efek_kuat": k, "kuat": kuat, "per_siklus": siklus, "laporan": laporan,
             "kejadian": kej.sort_values(["siklus", "kode"]).to_dict("records"),
             "universe": df.to_dict("records"), "versi_data": versi_data}
    hasil = json.loads(json.dumps(hasil, default=lambda x: x.isoformat() if hasattr(x, "isoformat") else (None if x != x else float(x))))
    dt.simpan_hasil("analisis_penerbitan_dev", hasil)
    return hasil


def cetak(h):
    r = h["ringkas"]
    print(f"Dev {h['siklus']}: {r['n']} kejadian, median selisih {r['median'] * 100:+.1f} poin, rata-rata {r['rata'] * 100:+.1f} poin, tertinggal {r['tertinggal_pct']:.0f}%")
    for x in h["efek_kuat"]:
        print(f"  {x['no']}. {x['nama']}: {x['nilai']:.1f} {'✔' if x['lulus'] else '✘'}")
    print(f"  EFEK KUAT: {'YA' if h['kuat'] else 'TIDAK'}")
    for s in h["per_siklus"]:
        med = "-" if s["median_selisih"] is None else f"{s['median_selisih'] * 100:+.1f}"
        rata = "-" if s["rata_selisih"] is None else f"{s['rata_selisih'] * 100:+.1f}"
        print(f"  {s['siklus']}: universe {s['n_universe']}, kejadian {s['n_kejadian']}, bobot sama {s['pembanding'] * 100:+.1f}%, median selisih {med}, rata {rata}")
    lp = h["laporan"]
    print("  tanpa kejadian di pembanding:", lp["pembanding_tanpa_kejadian"])
    for p, v in lp["per_penyebab"].items():
        print(f"  {p}: {v}")
    print("  per besar:", lp["per_besar"])
    print("  tanpa 5 paling unggul:", lp["tanpa_5_paling_unggul"])
    print("  uji tanda:", lp["uji_tanda"])
    for x in h["kejadian"]:
        print(f"    {x['siklus']} {x['kode']:5s} +{x['penerbitan'] * 100:6.1f}% {x['penyebab']:16s} return {x['return'] * 100:+7.1f}% selisih {x['selisih'] * 100:+7.1f}")


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    cetak(jalankan())
