import argparse
import hashlib
import json

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga

BIAYA_BELI = 0.0055
BIAYA_JUAL = 0.0065
DANA = 100.0
CICIL = 12
HORIZON = (3, 5)
CARA = ("lump", "dca", "dca_turun")
AMBANG_UTAMA = (10, 20)
AMBANG = ((10, 20), (7, 15), (15, 25))
DIVIDEN = (2.5, 0.0)
BUNGA = (0.0, 4.0)
PERIODE = {"dev": ("2010-01", "2018-12", "2023-12-31"), "holdout": ("2019-01", None, "2026-09-30")}
KELOMPOK = {"2010-2014": ("2010-01", "2014-12"), "2015-2018": ("2015-01", "2018-12")}


def siapkan(akhir_data):
    c = harga.indeks("indeks/JKII")["close"].astype(float)
    c.index = pd.to_datetime(c.index)
    c = c.sort_index()
    c = c[c.index <= pd.Timestamp(akhir_data)]
    puncak = c.rolling(250, min_periods=250).max()
    turun = (c / puncak - 1) * 100
    akhir_bulan = c.groupby(c.index.to_period("M")).apply(lambda s: s.index[-1])
    return c, turun, akhir_bulan


def aset(c, dividen):
    hari = (c.index - c.index[0]).days.values
    return pd.Series(c.values * (1 + dividen / 100) ** (hari / 365.25), index=c.index)


def kelipatan(t, ambang):
    if t is None or np.isnan(t):
        return 1
    if t <= -ambang[1]:
        return 3
    if t <= -ambang[0]:
        return 2
    return 1


def simulasi(cara, i, tahun, nilai, turun, ab, bunga, ambang):
    tgl_beli = [ab.iloc[i + k] for k in range(CICIL)]
    tgl_akhir = ab.iloc[i + 12 * tahun]
    jalur = nilai.loc[tgl_beli[0]:tgl_akhir]
    tgl = jalur.index
    harga_j = jalur.values
    tumbuh = (1 + bunga / 100) ** (np.diff(tgl.values).astype("timedelta64[D]").astype(float) / 365.25)
    beli = {}
    if cara == "lump":
        beli[tgl_beli[0]] = None
    else:
        for k, d in enumerate(tgl_beli):
            beli[d] = k
    unit, kas, disetor = 0.0, DANA, 0.0
    puncak, dd = DANA, 0.0
    habis = None
    harian = []
    for j, d in enumerate(tgl):
        if j > 0:
            kas *= tumbuh[j - 1]
        if d in beli:
            k = beli[d]
            if cara == "lump" or k == CICIL - 1:
                x = kas
            else:
                m = 1 if cara == "dca" else kelipatan(turun.get(ab.iloc[i + k - 1]), ambang)
                x = min(m * DANA / CICIL, kas)
            unit += x * (1 - BIAYA_BELI) / harga_j[j]
            kas -= x
            disetor += x
            if kas <= 1e-9:
                kas = 0.0
                if habis is None:
                    habis = 1 if cara == "lump" else k + 1
        v = unit * harga_j[j] + kas
        puncak = max(puncak, v)
        dd = min(dd, v / puncak - 1)
        harian.append((d, unit * harga_j[j], disetor))
    hr = pd.DataFrame(harian, columns=["tgl", "aset", "disetor"]).set_index("tgl")
    tgl_bulan = [ab.iloc[i + k] for k in range(1, 12 * tahun + 1)]
    bawah = int((hr.loc[tgl_bulan, "aset"] < hr.loc[tgl_bulan, "disetor"] - 1e-9).sum())
    akhir = unit * harga_j[-1] * (1 - BIAYA_JUAL) + kas
    return {"nilai_akhir": akhir, "dd_maks": dd * 100, "bulan_di_bawah_modal": bawah, "bulan_dana_habis": habis}


def titik_terendah(c, dari, sampai):
    s = c[c.index >= pd.Timestamp(dari + "-01")]
    dd = s / s.cummax() - 1
    dd = dd[dd.index <= pd.Timestamp(sampai) + pd.offsets.MonthEnd(0)]
    return dd.idxmin(), float(dd.min() * 100)


def ringkas(df):
    hasil = []
    kunci = ["skenario", "horizon"]
    for (sk, h), g in df.groupby(kunci):
        p = g.pivot(index="mulai", columns="cara", values="nilai_akhir")
        for cara, x in g.groupby("cara"):
            hasil.append({
                "skenario": sk, "horizon": h, "cara": cara, "n": len(x),
                "median": x["nilai_akhir"].median(), "p10": x["nilai_akhir"].quantile(0.1), "p90": x["nilai_akhir"].quantile(0.9),
                "dd_median": x["dd_maks"].median(), "bawah_modal_median": x["bulan_di_bawah_modal"].median(),
                "dana_habis_median": x["bulan_dana_habis"].median(),
                "menang_vs_dca": float((p[cara] > p["dca"]).mean() * 100), "menang_vs_lump": float((p[cara] > p["lump"]).mean() * 100),
                "selisih_vs_lump_median": float((p[cara] - p["lump"]).median()),
            })
    return pd.DataFrame(hasil)


def kriteria(df):
    def menang(h):
        g = df[df["horizon"] == h].pivot(index="mulai", columns="cara", values="nilai_akhir")
        return float((g["dca_turun"] > g["dca"]).mean() * 100), len(g)
    m5, n5 = menang(5)
    m3, n3 = menang(3)
    d5 = df[df["horizon"] == 5]
    dd_t = float(d5[d5["cara"] == "dca_turun"]["dd_maks"].median())
    dd_d = float(d5[d5["cara"] == "dca"]["dd_maks"].median())
    k = [
        {"kriteria": "1. 5 th: dca_turun menang vs dca di >= 60% tanggal mulai", "nilai": m5, "n": n5, "lulus": m5 >= 60},
        {"kriteria": "2. 5 th: median dd_maks dca_turun tidak lebih buruk > 2 poin dari dca", "nilai": dd_t - dd_d, "dd_dca_turun": dd_t, "dd_dca": dd_d, "lulus": dd_t >= dd_d - 2},
        {"kriteria": "3. 3 th: persen menang dca_turun vs dca >= 50%", "nilai": m3, "n": n3, "lulus": m3 >= 50},
    ]
    return k, all(x["lulus"] for x in k)


def nama_skenario(dividen, bunga, ambang):
    return f"div{dividen:g}_bunga{bunga:g}_ambang{ambang[0]}-{ambang[1]}"


def jalankan(periode="dev"):
    dari, sampai, akhir_data = PERIODE[periode]
    c, turun, ab = siapkan(akhir_data)
    bulan = list(ab.index)
    awal = {}
    for tahun in HORIZON:
        awal[tahun] = [i for i, b in enumerate(bulan) if b >= pd.Period(dari, "M") and (sampai is None or b <= pd.Period(sampai, "M"))]
        if sampai is None:
            awal[tahun] = [i for i in awal[tahun] if i + 12 * tahun < len(ab)]
    sampai_mulai = sampai or str(max(bulan[i] for x in awal.values() for i in x))
    baris = []
    for dividen in DIVIDEN:
        nilai = aset(c, dividen)
        for bunga in BUNGA:
            for ambang in AMBANG:
                if ambang != AMBANG_UTAMA and (dividen, bunga) != (DIVIDEN[0], BUNGA[0]):
                    continue
                sk = nama_skenario(dividen, bunga, ambang)
                for tahun in HORIZON:
                    for i in awal[tahun]:
                        if i + 12 * tahun >= len(ab):
                            raise RuntimeError(f"horizon {tahun} th dari {bulan[i]} melewati data")
                        for cara in CARA:
                            r = simulasi(cara, i, tahun, nilai, turun, ab, bunga, ambang)
                            baris.append({"skenario": sk, "dividen": dividen, "bunga": bunga, "ambang": f"{ambang[0]}/{ambang[1]}",
                                          "horizon": tahun, "mulai": str(bulan[i]), "tgl_mulai": ab.iloc[i].strftime("%Y-%m-%d"),
                                          "cara": cara, **r})
    df = pd.DataFrame(baris)
    utama = nama_skenario(DIVIDEN[0], BUNGA[0], AMBANG_UTAMA)
    rk = ringkas(df)
    k, lulus = kriteria(df[df["skenario"] == utama])
    tt, tt_dd = titik_terendah(c, dari, sampai_mulai)
    pt = pd.Period(tt, "M")
    df["mulai_p"] = df["mulai"].map(lambda s: pd.Period(s, "M"))
    tanpa = df[(df["mulai_p"] < pt - 12) | (df["mulai_p"] > pt + 12)]
    kerapuhan = {"titik_terendah": tt.strftime("%Y-%m-%d"), "turun_pct": tt_dd, "dibuang": int(df[df["skenario"] == utama]["mulai"].nunique() - tanpa[tanpa["skenario"] == utama]["mulai"].nunique())}
    kerapuhan["tanpa_sekitar_terendah"] = kriteria(tanpa[tanpa["skenario"] == utama])[0]
    kerapuhan["ambang"] = {}
    for ambang in AMBANG:
        sk = nama_skenario(DIVIDEN[0], BUNGA[0], ambang)
        kerapuhan["ambang"][f"{ambang[0]}/{ambang[1]}"] = kriteria(df[df["skenario"] == sk])[0]
    kerapuhan["skenario_lain"] = {}
    for dividen in DIVIDEN:
        for bunga in BUNGA:
            sk = nama_skenario(dividen, bunga, AMBANG_UTAMA)
            kerapuhan["skenario_lain"][sk] = kriteria(df[df["skenario"] == sk])[0]
    kelompok = {}
    for nm, (a, b) in KELOMPOK.items():
        g = df[(df["skenario"] == utama) & (df["mulai_p"] >= pd.Period(a, "M")) & (df["mulai_p"] <= pd.Period(b, "M"))]
        if g.empty:
            continue
        kelompok[nm] = {"kriteria": kriteria(g)[0], "ringkas": ringkas(g).to_dict("records")}
    df = df.drop(columns="mulai_p")
    sidik = hashlib.sha256(pd.util.hash_pandas_object(c, index=True).values.tobytes()).hexdigest()
    versi_data = {"sumber": "indeks/JKII", "versi": dt.versi("indeks/JKII"), "sidik_close": sidik,
                  "dari": c.index[0].strftime("%Y-%m-%d"), "sampai": c.index[-1].strftime("%Y-%m-%d"), **harga.status_koreksi()}
    hasil = {"periode": periode, "dari": dari, "sampai": sampai_mulai,
             "jumlah_mulai": {str(k): len(v) for k, v in awal.items()}, "skenario_utama": utama, "kriteria": k, "lulus": lulus,
             "kerapuhan": kerapuhan, "kelompok": kelompok, "ringkas": rk.to_dict("records"), "per_mulai": df.to_dict("records"),
             "versi_data": versi_data}
    hasil = json.loads(json.dumps(hasil, default=lambda x: x.isoformat() if hasattr(x, "isoformat") else float(x)))
    dt.simpan_hasil(f"analisis_cicil_jii_{periode}", hasil)
    return hasil


def cetak(h):
    print(f"Analisis cicil JII {h['periode']} {h['dari']}..{h['sampai']}, skenario utama {h['skenario_utama']}")
    for x in h["kriteria"]:
        print(f"  {'LULUS' if x['lulus'] else 'GAGAL'}  {x['kriteria']}: {x['nilai']:.2f}")
    print(f"  dca_turun lebih baik dari dca: {'YA' if h['lulus'] else 'TIDAK'}")
    rk = pd.DataFrame(h["ringkas"])
    print(rk.round(2).to_string(index=False))
    print(json.dumps({k: v for k, v in h["kerapuhan"].items()}, indent=1, default=str)[:6000])
    for nm, g in h["kelompok"].items():
        print(nm, [(x["kriteria"][:2], round(x["nilai"], 2), x["lulus"]) for x in g["kriteria"]])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--periode", default="dev", choices=list(PERIODE))
    cetak(jalankan(p.parse_args().periode))
