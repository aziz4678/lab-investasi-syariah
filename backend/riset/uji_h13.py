from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset import uji_tren as ut

POSISI = 10
RISIKO = 0.01
BOBOT_MAKS = 0.20
BOBOT_TETAP = 0.10
KONFIG = {
    "H11a": dict(S=False, R=False, P=False),
    "S": dict(S=True, R=False, P=False),
    "R": dict(S=False, R=True, P=False),
    "P": dict(S=False, R=False, P=True),
    "S+R+P": dict(S=True, R=True, P=True),
}


def regime_ihsg():
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    return ihsg > ihsg.ewm(span=200, adjust=False).mean()


def portofolio(tr, S, R, P, regime, seed=7):
    t = tr.copy()
    if R:
        t = t[regime.reindex(t["tgl"]).fillna(False).to_numpy()]
    t["acak"] = np.random.default_rng(seed).random(len(t))
    t = t.sort_values(["tgl", "mom120" if P else "acak"], ascending=[True, False])
    t["bobot"] = np.minimum(BOBOT_MAKS, RISIKO / (t["stop_pct"] / 100)) if S else BOBOT_TETAP
    buka = []
    ambil = []
    for r in t.itertuples():
        buka = [(x, w) for x, w in buka if x > r.tgl]
        if len(buka) >= POSISI or sum(w for _, w in buka) + r.bobot > 1.0 + 1e-9:
            continue
        buka.append((r.tgl_exit, r.bobot))
        ambil.append(r.Index)
    return t.loc[ambil]


def metrik(p, mulai, akhir):
    f = 1 + p["bobot"] * p["net"] / 100
    bln = f.groupby(p["tgl_exit"].dt.to_period("M")).prod()
    semua = pd.period_range(mulai.to_period("M"), max(akhir, p["tgl_exit"].max()).to_period("M"), freq="M")
    bln = bln.reindex(semua, fill_value=1.0)
    ek = bln.cumprod()
    cagr = (ek.iloc[-1] ** (12 / len(semua)) - 1) * 100
    dd = (ek / ek.cummax() - 1).min() * 100
    return {"trade": len(p), "WR %": round((p["net"] > 0).mean() * 100), "bobot rata2 %": round(p["bobot"].mean() * 100, 1),
            "CAGR %": round(cagr, 1), "DD %": round(dd, 1), "MAR": round(cagr / abs(dd), 2) if dd < 0 else np.nan,
            "bulan + %": round(((bln - 1) > 0).mean() * 100), "bulan terburuk %": round((bln.min() - 1) * 100, 1)}


def siapkan(daftar, batas_akhir=None, des=None):
    data = sc.baca_harga(set(daftar))
    if batas_akhir:
        data = {t: d[d.index <= batas_akhir] for t, d in data.items()}
    data = {t: d for t, d in data.items() if len(d) >= 300}
    pasar = sc.baca_pasar(data)
    siap = {}
    for t, d in data.items():
        x = ut.tambah_fitur(sc.fitur_ticker(d, pasar))
        if des is not None:
            syariah = pd.Series(False, index=x.index)
            for r in des[des["kode"] == t].itertuples():
                syariah |= (x.index >= r.mulai) & (x.index <= r.akhir)
            x["lolos"] = x["lolos"] & syariah
        siap[t] = x
    return siap


def jalankan(nama_set, siap, mulai, akhir, regime):
    tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)]
    bm = ut.benchmark(siap, mulai, akhir)
    baris = []
    for nama, k in KONFIG.items():
        m = metrik(portofolio(tr, regime=regime, **k), mulai, akhir)
        baris.append({"set": nama_set, "konfig": nama, **m, "> beli-tahan": "ya" if m["CAGR %"] > bm else "TIDAK"})
    hasil = pd.DataFrame(baris)
    print(f"\n##### {nama_set}: {len(siap)} saham, {len(tr)} sinyal-trade, beli-tahan CAGR {bm:.1f}%, "
          f"net/trade H11a {tr['net'].mean():+.2f}% (WR {(tr['net'] > 0).mean() * 100:.0f}%)")
    print(hasil.drop(columns="set").to_string(index=False))
    return hasil, bm


def utama():
    regime = regime_ihsg()
    des = des_ojk.baca()
    daftar217 = sc.daftar_syariah()
    non = [k.strip()[:-3] for k in dt.baca_daftar("nonsyariah_kode")]
    di_luar_217 = sorted(set(des["kode"]) - daftar217)

    hasil = []
    for nama, daftar, akhir_data, mulai, akhir, pakai_des in [
        ("A non-syariah 2010-2026", non, None, "2010-01-01", "2026-12-31", False),
        ("B DES di luar 217, 2010-2019", di_luar_217, "2019-12-31", "2010-01-01", "2019-12-31", False),
        ("info: 217 saham 2010-2019", sorted(daftar217), "2019-12-31", "2010-01-01", "2019-12-31", False),
        ("info: DES historis 2020+", sorted(set(des["kode"])), None, "2020-01-01", "2026-12-31", True),
    ]:
        siap = siapkan(daftar, akhir_data, des if pakai_des else None)
        h, bm = jalankan(nama, siap, pd.Timestamp(mulai), pd.Timestamp(akhir), regime)
        h["beli_tahan"] = bm
        hasil.append(h)
    semua = pd.concat(hasil)
    dt.simpan_hasil(f"hasil_h13", semua.reset_index(drop=True))

    print("\n\n===== KEPUTUSAN (hanya Set A dan Set B) =====")
    inti = semua[semua["set"].str.startswith(("A ", "B "))]
    mar = inti.pivot(index="konfig", columns="set", values="MAR")
    cagr_ok = inti.pivot(index="konfig", columns="set", values="> beli-tahan")
    for k in ["S", "R", "P", "S+R+P"]:
        naik = all(mar.loc[k, s] > mar.loc["H11a", s] for s in mar.columns)
        syarat = naik and (k != "S+R+P" or all(cagr_ok.loc[k, s] == "ya" for s in cagr_ok.columns))
        print(f"  {k:6s}: MAR {' / '.join(f'{mar.loc[k, s]:.2f}' for s in mar.columns)} vs H11a "
              f"{' / '.join(f'{mar.loc['H11a', s]:.2f}' for s in mar.columns)} -> {'DIADOPSI' if syarat else 'tidak'}")
    for s in cagr_ok.columns:
        if cagr_ok.loc["H11a", s] != "ya":
            print(f"  PERINGATAN: H11a kalah dari beli-tahan di {s}")


if __name__ == "__main__":
    utama()
