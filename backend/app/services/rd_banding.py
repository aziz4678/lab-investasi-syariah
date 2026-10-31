import numpy as np
import pandas as pd

from backend.app.services import rd_yakin
from backend.app.services import reksadana as rd
from backend.db import data as dt

MAKS = 5
PERIODE = {"1y": 1, "3y": 3, "5y": 5, "10y": 10}
PEMBANDING = {
    "x:deposito": ("Deposito (perkiraan)", "Bunga antarbank dipotong pajak 20%, dibungakan tiap bulan"),
    "x:jii": ("JII", "Indeks saham syariah, harga saja tanpa dividen"),
    "x:emas": ("Emas", "Harga emas dunia dalam rupiah, tanpa biaya simpan/jual-beli"),
}


def pilihan():
    data = rd._daftar(rd.versi())
    rd_list = [{"id": f"rd:{x['id']}", "nama": x["nama"], "mi": x.get("mi"), "kategori": x["kategori"], "kategori_label": x["kategori_label"],
                "mata_uang": x["mata_uang"], "tahun_data": x.get("tahun_data")} for x in data if x.get("tahun_data")]
    return {"pembanding": [{"id": k, "nama": v[0], "ket": v[1]} for k, v in PEMBANDING.items()], "rd": rd_list}


def bulan(s):
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.resample("ME").last().dropna()


def kurs():
    return bulan(dt.baca("pasar")["usdidr"])


def seri(kunci, rupiah, info):
    if kunci == "x:deposito":
        b = bulan(dt.baca("makro/bunga_antarbank")["nilai"])
        b = b.reindex(pd.date_range(b.index[0], pd.Timestamp.today() + pd.offsets.MonthEnd(0), freq="ME")).ffill()
        return (1 + b.shift(1).fillna(b.iloc[0]) / 100 * (1 - rd_yakin.PAJAK_DEPOSITO) / 12).cumprod()
    if kunci == "x:jii":
        return bulan(dt.baca("indeks/JKII")["close"])
    if kunci == "x:emas":
        e = bulan(dt.baca("pasar")["emas"])
        return (e * kurs().reindex(e.index)).dropna()
    fid = int(kunci.split(":")[1])
    b = rd_yakin.bulanan()
    if fid not in b.columns:
        return None
    s = b[fid].dropna()
    if rupiah and info.get(fid, {}).get("mata_uang") == "USD":
        s = (s * kurs().reindex(s.index)).dropna()
    return s


def bandingkan(kunci_list, periode="5y", rupiah=True):
    data = {x["id"]: x for x in rd._daftar(rd.versi())}
    kunci_list = [k for k in dict.fromkeys(kunci_list) if k in PEMBANDING or (k.startswith("rd:") and k[3:].isdigit())][:MAKS]
    semua = {}
    for k in kunci_list:
        s = seri(k, rupiah, data)
        if s is not None and len(s) >= 3:
            semua[k] = s
    if len(semua) < 2:
        return {"error": "Pilih minimal 2 produk yang punya data."}
    df = pd.concat(semua, axis=1).sort_index()
    mulai = max(s.index[0] for s in semua.values())
    termuda = [k for k, s in semua.items() if s.index[0] == mulai]
    akhir = min(s.index[-1] for s in semua.values())
    th = PERIODE.get(periode)
    diminta = akhir - pd.DateOffset(years=th) + pd.offsets.MonthEnd(0) if th else None
    dipotong = diminta is None or mulai > diminta
    if th:
        mulai = max(mulai, diminta)
    df = df[(df.index >= mulai) & (df.index <= akhir)].ffill().dropna()
    if len(df) < 4:
        return {"error": "Periode bersama terlalu pendek (kurang dari 4 bulan)."}
    norm = df / df.iloc[0] * 100
    r = df.pct_change().dropna()
    tahun = (df.index[-1] - df.index[0]).days / 365.25
    inf = rd_yakin.inflasi()
    inf_des = inf[inf.index.month == 12]
    inf_des.index = inf_des.index.year
    metrik, nama = {}, {}
    for k in df.columns:
        s = df[k]
        akhir_th = s.groupby(s.index.year).last()
        per_th = ((akhir_th / akhir_th.shift(1) - 1) * 100).dropna()
        per_th = per_th[per_th.index < df.index[-1].year] if df.index[-1].month < 12 else per_th
        dibanding = [t for t in per_th.index if t in inf_des.index]
        x = data.get(int(k[3:])) if k.startswith("rd:") else None
        nama[k] = x["nama"] if x else PEMBANDING[k][0]
        metrik[k] = {
            "total": float((s.iloc[-1] / s.iloc[0] - 1) * 100),
            "per_tahun": float(((s.iloc[-1] / s.iloc[0]) ** (1 / tahun) - 1) * 100) if tahun >= 1 else None,
            "dd": float((s / s.cummax() - 1).min() * 100),
            "vol": float(r[k].std() * np.sqrt(12) * 100) if len(r) >= 6 else None,
            "bulan_turun": int((r[k] < 0).sum()), "bulan_dihitung": int(len(r)),
            "tahun_terbaik": float(per_th.max()) if len(per_th) else None,
            "tahun_terburuk": float(per_th.min()) if len(per_th) else None,
            "tahun_naik": int((per_th > 0).sum()), "tahun_dihitung": int(len(per_th)),
            "kalahkan_inflasi": int(sum(per_th[t] > inf_des[t] for t in dibanding)), "tahun_inflasi": len(dibanding),
            "per_th": {int(t): float(v) for t, v in per_th.items()},
        }
        if x:
            metrik[k].update({"biaya": x.get("biaya"), "aum": x.get("aum"), "mata_uang": x["mata_uang"], "kategori": x["kategori_label"],
                              "mi": x.get("mi"), "peringatan": x.get("peringatan") or [], "tahun_data": x.get("tahun_data")})
        else:
            metrik[k].update({"kategori": "Pembanding", "ket": PEMBANDING[k][1], "mata_uang": "IDR"})
    kor = r.corr().round(2) if len(r) >= 6 else None
    tahun_list = sorted({t for m in metrik.values() for t in m["per_th"]})
    return rd.bersih({
        "tgl": [t.strftime("%Y-%m-%d") for t in norm.index], "seri": {k: norm[k].round(2).tolist() for k in df.columns},
        "nama": nama, "metrik": metrik, "tahun_list": tahun_list,
        "inflasi": {int(t): float(inf_des[t]) for t in tahun_list if t in inf_des.index},
        "korelasi": {a: {b: float(kor.loc[a, b]) for b in kor.columns} for a in kor.index} if kor is not None else None,
        "mulai": df.index[0].strftime("%Y-%m-%d"), "akhir": df.index[-1].strftime("%Y-%m-%d"), "tahun": round(tahun, 1), "rupiah": rupiah,
        "penentu_mulai": [nama[k] for k in termuda] if dipotong else [],
        "tidak_ada": [k for k in kunci_list if k not in semua],
    })
