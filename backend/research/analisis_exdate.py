import json

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_ihsg, baca_mentah
from backend.db import data as dt
from backend.ingest import des_ojk

MULAI = pd.Timestamp("2015-01-01")
NILAI_MIN = 1e9
PAJAK = 0.10
BIAYA = 0.6
HARI = [1, 5, 10, 20, 60]
PULIH = [5, 20, 60, 120]
KELOMPOK = [(0, 3, "< 3%"), (3, 6, "3–6%"), (6, 10, "6–10%"), (10, 1000, "≥ 10%")]


def nilai(s, t):
    x = s[s.index <= t]
    return float(x.iloc[-1]) if len(x) else np.nan


def kejadian():
    des = des_ojk.baca()
    awal_des = des["mulai"].min()
    daftar = {x.replace(".JK", "") for x in dt.baca_daftar("syariah_tickers")}
    ihsg = baca_ihsg()
    baris = []
    for kode in sorted(set(des["kode"]) | daftar):
        m = baca_mentah(kode)
        if m is None or "dividends" not in m or len(m) < 80:
            continue
        m = m[m["close"] > 0]
        nilai20 = (m["close"] * m["volume"]).rolling(20).mean()
        dv = m["dividends"].fillna(0)
        for t in dv[(dv > 0) & (dv.index >= MULAI)].index:
            i = m.index.get_loc(t)
            if i < 21 or i + 1 >= len(m):
                continue
            cum = m.index[i - 1]
            if cum < awal_des:
                if kode not in daftar:
                    continue
            elif kode not in des_ojk.syariah_pada(des, cum):
                continue
            p0 = float(m["close"].iloc[i - 1])
            if not (nilai20.iloc[i - 1] >= NILAI_MIN):
                continue
            dps = float(dv.loc[t])
            y = dps / p0 * 100
            if y <= 0 or y > 60:
                continue
            r = {"kode": kode, "ex": t.strftime("%Y-%m-%d"), "tahun": t.year, "harga_cum": p0, "dps": dps, "yield": y,
                 "gap": (float(m["open"].iloc[i]) / p0 - 1) * 100}
            i0 = nilai(ihsg, cum)
            for k in HARI:
                j = i + k - 1
                if j >= len(m):
                    r[f"h{k}"] = np.nan
                    continue
                tk = m.index[j]
                r[f"h{k}"] = (float(m["close"].iloc[j]) / p0 - 1) * 100
                r[f"ihsg{k}"] = (nilai(ihsg, tk) / i0 - 1) * 100 if np.isfinite(i0) else np.nan
            sesudah = m["close"].iloc[i:]
            pulih = np.nonzero(sesudah.values >= p0)[0]
            r["hari_pulih"] = int(pulih[0]) + 1 if len(pulih) else None
            r["sisa_data"] = len(sesudah)
            baris.append(r)
    return pd.DataFrame(baris)


def ringkas(df):
    if df.empty:
        return {}
    bersih = df["yield"] * (1 - PAJAK)
    hasil = {"n": int(len(df)), "yield_median": round(float(df["yield"].median()), 2),
             "gap_median": round(float(df["gap"].median()), 2),
             "turun_vs_dividen_median": round(float((-df["h1"] / df["yield"]).median()), 2)}
    for k in HARI:
        ok = df[f"h{k}"].notna()
        tot = df.loc[ok, f"h{k}"] + bersih[ok] - BIAYA
        hasil[f"harga_h{k}"] = round(float(df.loc[ok, f"h{k}"].median()), 2)
        hasil[f"total_h{k}"] = round(float(tot.median()), 2)
        hasil[f"rugi_h{k}"] = round(float((tot < 0).mean() * 100), 1)
        hasil[f"lebih_ihsg_h{k}"] = round(float((df.loc[ok, f"h{k}"] + bersih[ok] - df.loc[ok, f"ihsg{k}"]).median()), 2)
    for k in PULIH:
        ok = df["sisa_data"] >= k
        hasil[f"pulih_{k}"] = round(float((df.loc[ok, "hari_pulih"].fillna(10**6) <= k).mean() * 100), 1)
    p = df["hari_pulih"].dropna()
    hasil["hari_pulih_median"] = int(p.median()) if len(p) else None
    return hasil


def utama():
    df = kejadian()
    dt.simpan_hasil("exdate_kejadian", df.reset_index(drop=True))
    semua = ringkas(df)
    per_yield = [{"label": l, **ringkas(df[(df["yield"] >= a) & (df["yield"] < b)])} for a, b, l in KELOMPOK]
    per_tahun = [{"tahun": int(t), **ringkas(g)} for t, g in df.groupby("tahun")]
    df["total20"] = df["h20"] + df["yield"] * (1 - PAJAK) - BIAYA
    terburuk = df[df["yield"] >= 4].dropna(subset=["total20"]).nsmallest(12, "total20")
    contoh = [{"kode": r["kode"], "ex": r["ex"], "yield": round(r["yield"], 1), "h1": round(r["h1"], 1), "h20": round(r["h20"], 1),
               "total20": round(r["total20"], 1), "hari_pulih": int(r["hari_pulih"]) if pd.notna(r["hari_pulih"]) else None}
              for _, r in terburuk.iterrows()]
    keluar = {"dibuat": pd.Timestamp.today().strftime("%Y-%m-%d"), "mulai": MULAI.strftime("%Y-%m-%d"), "nilai_min": NILAI_MIN, "biaya": BIAYA,
              "pajak": PAJAK, "semua": semua, "per_yield": per_yield, "per_tahun": per_tahun, "terburuk": contoh}
    dt.simpan_hasil("exdate_ringkas", json.loads(json.dumps(keluar, ensure_ascii=False, default=lambda x: None if x is None or (isinstance(x, float) and np.isnan(x)) else x)))
    s = semua
    print(f"{s['n']} kejadian dividen saham syariah likuid sejak {MULAI:%Y}, yield median {s['yield_median']}%")
    print(f"Harga dibuka di ex-date median {s['gap_median']}% dari close cum; turun = {s['turun_vs_dividen_median']}x dividen di hari ex")
    for k in HARI:
        print(f"  beli close cum, jual close hari ke-{k}: harga {s[f'harga_h{k}']:+.2f}%, total (dividen bersih - biaya {BIAYA}%) {s[f'total_h{k}']:+.2f}%, "
              f"rugi {s[f'rugi_h{k}']}% kasus, lebih dari IHSG {s[f'lebih_ihsg_h{k}']:+.2f}%")
    print("  kembali ke harga cum dalam " + ", ".join(f"{k} hari: {s[f'pulih_{k}']}%" for k in PULIH) + f" (median {s['hari_pulih_median']} hari)")
    print("\nPer tingkat yield:")
    for g in per_yield:
        if g.get("n"):
            print(f"  {g['label']:>6}: n={g['n']}, turun {g['turun_vs_dividen_median']}x dividen, total 20 hari {g['total_h20']:+.2f}% "
                  f"(rugi {g['rugi_h20']}%), pulih 60 hari {g['pulih_60']}%")


if __name__ == "__main__":
    utama()
