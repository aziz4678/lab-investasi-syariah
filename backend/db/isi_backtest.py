from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.riset import uji_tren as ut
from backend.riset.batas_paper import kurva_harian
from backend.riset.laporan_bulanan import simulasi_portofolio
from backend.riset.uji_dividen import bersih

POSISI = 10
BOBOT = 0.10


def konservatif(tr, siap):
    hasil = []
    for r in tr.itertuples(index=False):
        x = siap[r.ticker]
        pos = x.index.get_loc(r.tgl)
        m = x.iloc[pos + 1]
        if m["high"] == m["low"] and m["open"] > x["close"].iloc[pos]:
            continue
        baris = r._asdict()
        if r.alasan == "stop":
            k = x.index.get_loc(r.tgl_exit)
            while k < len(x) - 1 and x["high"].iloc[k] == x["low"].iloc[k]:
                k += 1
            if x.index[k] != r.tgl_exit:
                rs = (x["close_mentah"] / x["close"]).to_numpy()
                e, px = x["open"].iloc[pos + 1], x["open"].iloc[k]
                baris["net"] = bersih(e, px, e * rs[pos + 1], px * rs[k])
                baris["kotor"] = (px / e - 1) * 100
                baris["tgl_exit"] = x.index[k]
                baris["hari"] = k - pos
        hasil.append(baris)
    return pd.DataFrame(hasil)


def harga_pasar(x, tgl, geser, kolom):
    pos = x.index.get_loc(tgl) + geser
    return float(x[kolom].iloc[pos] * x["close_mentah"].iloc[pos] / x["close"].iloc[pos]), x.index[pos]


def dokumen_trade(versi, tr, dipilih, siap):
    dok = []
    for r in tr.itertuples():
        x = siap[r.ticker]
        beli, tgl_beli = harga_pasar(x, r.tgl, 1, "open")
        if r.alasan == "stop":
            jual, _ = harga_pasar(x, r.tgl_exit, 0, "open")
        else:
            jual = float(x.loc[r.tgl_exit, "close_mentah"])
        dok.append({
            "versi": versi, "ticker": r.ticker, "tgl_sinyal": r.tgl.to_pydatetime(), "tgl_beli": tgl_beli.to_pydatetime(),
            "harga_beli": round(beli), "tgl_jual": r.tgl_exit.to_pydatetime(), "harga_jual": round(jual),
            "hari": int(r.hari), "kotor": round(float(r.kotor), 2), "net": round(float(r.net), 2),
            "status": {"stop": "selesai", "terbuka": "terbuka", "waktu": "batas_waktu", "akhir_data": "selesai"}.get(r.alasan, r.alasan),
            "stop_awal_pct": round(float(r.stop_pct), 2), "dipilih": bool(r.Index in dipilih),
        })
    return dok


def bulanan_benchmark(siap, mulai, akhir):
    potong = []
    for x in siap.values():
        c = x["close"].resample("ME").last()
        ok = x["lolos"].resample("ME").last().fillna(False).astype(bool)
        r = c.pct_change().shift(-1)
        potong.append(r[ok])
    r = pd.concat(potong).groupby(level=0).mean().dropna()
    r.index = (r.index + pd.offsets.MonthEnd(1)).to_period("M")
    return r[(r.index >= mulai.to_period("M")) & (r.index <= akhir.to_period("M"))]


def kurva(p, mulai, akhir):
    f = 1 + BOBOT * p["net"] / 100
    bln = f.groupby(p["tgl_exit"].dt.to_period("M")).prod()
    semua = pd.period_range(mulai.to_period("M"), max(akhir, p["tgl_exit"].max()).to_period("M"), freq="M")
    return bln.reindex(semua, fill_value=1.0) - 1


def kurva_paper(dok, mulai, akhir):
    tr = pd.DataFrame([x for x in dok if x["dipilih"]])
    tr["tgl_beli"] = pd.to_datetime(tr["tgl_beli"])
    tr["tgl_jual"] = pd.to_datetime(tr["tgl_jual"]).where(tr["status"] != "terbuka")
    tr = tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    harian = kurva_harian(tr, mulai, akhir)
    bln = harian.resample("ME").last()
    bln.index = bln.index.to_period("M")
    semua = pd.period_range(mulai.to_period("M"), akhir.to_period("M"), freq="M")
    bln = bln.reindex(semua).ffill().fillna(1.0)
    return bln / bln.shift(1).fillna(1.0) - 1, harian


def ringkas(versi, label, tr, p, ret, bm, ihsg):
    ek = (1 + ret).cumprod()
    dd = ek / ek.cummax() - 1
    n = len(ret)
    cagr = (ek.iloc[-1] ** (12 / n) - 1) * 100
    m = p["net"] > 0
    tahunan = ((1 + ret).groupby(ret.index.year).prod() - 1) * 100
    return {
        "versi": versi, "label": label, "dibuat": datetime.now(),
        "mulai": str(ret.index[0]), "akhir": str(ret.index[-1]),
        "sinyal": int(len(tr)), "trade": int(len(p)), "win_rate": round(float(m.mean() * 100), 1),
        "rata_menang": round(float(p.loc[m, "net"].mean()), 2), "rata_kalah": round(float(p.loc[~m, "net"].mean()), 2),
        "net_per_trade": round(float(p["net"].mean()), 2), "median_trade": round(float(p["net"].median()), 2),
        "rata_hari": round(float(p["hari"].mean()), 1), "cagr": round(float(cagr), 1), "dd_maks": round(float(dd.min() * 100), 1),
        "bulan_positif": round(float((ret > 0).mean() * 100), 1), "bulan_terburuk": round(float(ret.min() * 100), 1),
        "bulan_terbaik": round(float(ret.max() * 100), 1),
        "cagr_beli_tahan": round(float(((1 + bm).prod() ** (12 / len(bm)) - 1) * 100), 1),
        "cagr_ihsg": round(float(((1 + ihsg).prod() ** (12 / len(ihsg)) - 1) * 100), 1),
        "per_tahun": {str(k): round(float(v), 1) for k, v in tahunan.items()},
    }


def simpan_versi(db, versi, label, siap, tr, mulai, akhir, ihsg_bln):
    p = simulasi_portofolio(tr, POSISI, 7)
    lama = kurva(p, mulai, akhir)
    dok_tr = dokumen_trade(versi, tr, set(p.index), siap)
    ret, harian = kurva_paper(dok_tr, mulai, akhir)
    bm = bulanan_benchmark(siap, mulai, akhir).reindex(ret.index).fillna(0)
    ih = ihsg_bln.reindex(ret.index).fillna(0)
    ek, ek_bm, ek_ih = (1 + ret).cumprod(), (1 + bm).cumprod(), (1 + ih).cumprod()
    dok_ek = [{"versi": versi, "bulan": str(b), "return": round(float(ret[b] * 100), 2), "ekuitas": round(float(ek[b]), 4),
               "drawdown": round(float((ek[b] / ek[:b].max() - 1) * 100), 2), "beli_tahan": round(float(ek_bm[b]), 4),
               "ihsg": round(float(ek_ih[b]), 4)} for b in ret.index]
    d.ganti_versi(db, "backtest_trade", versi, dok_tr)
    d.ganti_versi(db, "backtest_ekuitas", versi, dok_ek)
    rk = ringkas(versi, label, tr, p, ret, bm, ih)
    ek_lama = (1 + lama).cumprod()
    rk["metode"] = "harian: 10% ekuitas saat beli, harga pasar, dividen dipotong pajak (sama dengan paper)"
    rk["cagr_metode_lama"] = round(float((ek_lama.iloc[-1] ** (12 / len(lama)) - 1) * 100), 1)
    rk["dd_harian"] = round(float((harian / harian.cummax() - 1).min() * 100), 1)
    rk["dd_maks"] = rk["dd_harian"]
    db.backtest_ringkasan.replace_one({"versi": versi}, rk, upsert=True)
    print(f"{versi}: {len(tr)} sinyal, {len(p)} trade portofolio, CAGR {rk['cagr']}% (metode lama {rk['cagr_metode_lama']}%), "
          f"DD bulanan {rk['dd_maks']}% / harian {rk['dd_harian']}%, "
          f"WR {rk['win_rate']}%, beli-tahan {rk['cagr_beli_tahan']}%, IHSG {rk['cagr_ihsg']}%")


def utama():
    db = d.koneksi()
    d.siapkan_indeks(db)
    ihsg = dt.baca("pasar")["ihsg"].dropna().resample("ME").last().pct_change()
    ihsg.index = ihsg.index.to_period("M")
    sinyal = lambda x: x["close"] >= x["maks250"]

    siap = ut.siapkan_holdout()
    tr = ut.kumpulkan(siap, sinyal)
    tr = tr[tr["tgl"] >= "2020-01-01"].reset_index(drop=True)
    mulai, akhir = pd.Timestamp("2020-01-01"), tr["tgl_exit"].max()
    simpan_versi(db, "h11a_2020", "H11a 2020+ (DES historis)", siap, tr, mulai, akhir, ihsg)
    simpan_versi(db, "h11a_2020_konservatif", "H11a 2020+ konservatif (ARA/ARB)", siap, konservatif(tr, siap), mulai, akhir, ihsg)

    siap = ut.siapkan_dev()
    tr = ut.kumpulkan(siap, sinyal)
    tr = tr[(tr["tgl"] >= "2010-01-01") & (tr["tgl"] <= "2019-12-31")].reset_index(drop=True)
    simpan_versi(db, "h11a_dev", "H11a 2010-2019 (217 saham)", siap, tr, pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31"), ihsg)


if __name__ == "__main__":
    utama()
