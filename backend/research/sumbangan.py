from collections import defaultdict

import numpy as np
import pandas as pd

from backend.db.harga import mentah as baca_mentah
from backend.db import data as dt
from backend.paper.tren_harian import BOBOT, PAJAK_DIVIDEN, biaya_beli, hasil_jual

TOLERANSI = 0.006


def tabel_ft(dok):
    tr = pd.DataFrame(dok)
    tr["tgl_beli"] = pd.to_datetime(tr["tgl_beli"])
    tr["tgl_jual"] = pd.to_datetime(tr["tgl_jual"]).where(tr["status"] != "terbuka")
    return tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)


def harian_ft(tr, mulai, akhir, mentah=None):
    harga, dividen = {}, {}
    for t in tr["ticker"].unique():
        m = mentah[t] if mentah is not None and t in mentah else baca_mentah(t)
        harga[t] = m["close"] if m is not None else pd.Series(dtype=float)
        dividen[t] = m["dividends"].fillna(0) if m is not None and "dividends" in m else pd.Series(dtype=float)
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    hari = ihsg.index[(ihsg.index >= pd.Timestamp(mulai)) & (ihsg.index <= pd.Timestamp(akhir))]
    tabel, dv = {}, {}
    for t, s in harga.items():
        s = s[s.index.isin(hari)].astype(float)
        tabel[t] = s[np.isfinite(s.to_numpy())].reindex(hari).ffill().to_numpy()
        d_ = dividen[t]
        d_ = d_[d_.index.isin(hari) & (d_ > 0)]
        dv[t] = {k: float(v) for k, v in d_.items()}
    ticker = tr["ticker"].to_numpy()
    harga_beli = tr["harga_beli"].to_numpy(float)
    beli = {k: v for k, v in tr.groupby("tgl_beli")}
    jual = {k: v for k, v in tr[tr["tgl_jual"].notna()].groupby("tgl_jual")}
    kas, posisi, lalu, nilai = 1.0, {}, {}, []
    inc = defaultdict(dict)
    for j, tgl in enumerate(hari):
        hari_ini = defaultdict(float)
        for i, l in posisi.items():
            d_ = dv[ticker[i]].get(tgl)
            if d_:
                kas += l * d_ * (1 - PAJAK_DIVIDEN)
                hari_ini[i] += l * d_ * (1 - PAJAK_DIVIDEN)
        if tgl in jual:
            for r in jual[tgl].itertuples():
                lembar = posisi.pop(r.Index, 0.0)
                kas += lembar * hasil_jual(r.harga_jual)
                if r.Index in lalu:
                    hari_ini[r.Index] += lembar * hasil_jual(r.harga_jual) - lalu.pop(r.Index)
        ekuitas_kemarin = nilai[-1] if nilai else 1.0
        if tgl in beli:
            for r in beli[tgl].itertuples():
                dana = min(BOBOT * ekuitas_kemarin, kas)
                if dana <= 0:
                    continue
                kas -= dana
                posisi[r.Index] = dana / biaya_beli(r.harga_beli)
                lalu[r.Index] = dana
        total = kas
        for i, l in posisi.items():
            h = tabel[ticker[i]][j]
            v = l * (h if h == h else harga_beli[i])
            total += v
            hari_ini[i] += v - lalu[i]
            lalu[i] = v
        nilai.append(total)
        for i, x in hari_ini.items():
            if x:
                inc[i][tgl] = x
    return pd.Series(nilai, index=hari), inc


def per_bulan(inc_hari, batas):
    b = pd.DatetimeIndex(sorted(batas))
    hasil = defaultdict(float)
    for tgl, x in inc_hari.items():
        k = b.searchsorted(tgl)
        if k < len(b):
            hasil[str(b[k].to_period("M"))] += x
    return dict(hasil)


def batas_kalender(index):
    s = pd.Series(index, index=index)
    return list(s.groupby(index.to_period("M")).max())


def cocokkan(pnl_total, ekuitas_awal, ret_tersimpan, nama):
    beda = []
    for bln, ret in ret_tersimpan.items():
        r = pnl_total.get(bln, 0.0) / ekuitas_awal[bln] * 100
        if abs(r - ret) > TOLERANSI:
            beda.append((bln, round(r, 4), ret))
    if beda:
        raise RuntimeError(f"{nama}: sumbangan per trade tidak sama dengan return bulanan ({len(beda)} bulan, contoh {beda[:3]})")


def bulat(pnl):
    return {k: round(float(v), 8) for k, v in sorted(pnl.items()) if abs(v) > 1e-12}


def h11a(dok, mulai, akhir, mentah=None):
    pilih = [x for x in dok if x["dipilih"]]
    tr = tabel_ft(pilih)
    ek, inc = harian_ft(tr, mulai, akhir, mentah)
    batas = batas_kalender(ek.index)
    pnl = {i: per_bulan(inc.get(i, {}), batas) for i in tr.index}
    kunci = {(r.ticker, r.tgl_beli): i for i, r in zip(tr.index, tr.itertuples())}
    return ek, batas, {k: pnl[i] for k, i in kunci.items()}


def ekuitas_awal_bulan(ek, batas, dasar=1.0):
    awal, sebelum = {}, dasar
    for b in batas:
        awal[str(b.to_period("M"))] = sebelum
        sebelum = float(ek[b])
    return awal


def h29(e11, inc11_hari, e22, inc22_hari, v):
    idx = v.index
    batas = batas_kalender(idx)
    a0 = e11[e11.index < idx[0]]
    a0 = float(a0.iloc[-1]) if len(a0) else 1.0
    awal_v = ekuitas_awal_bulan(v, batas)
    awal_11 = ekuitas_awal_bulan(e11.reindex(idx), batas, a0)
    awal_22 = ekuitas_awal_bulan(e22.reindex(idx), batas, 1.0)

    def ubah(inc_hari, awal_bagian, sejak):
        hasil = {}
        for k, x in inc_hari.items():
            p = per_bulan({t: y for t, y in x.items() if sejak is None or t >= sejak}, batas)
            hasil[k] = {b: awal_v[b] * 0.5 * y / awal_bagian[b] for b, y in p.items()}
        return hasil

    return batas, awal_v, ubah(inc11_hari, awal_11, idx[0]), ubah(inc22_hari, awal_22, None)
