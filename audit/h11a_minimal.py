import argparse

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi

MULAI = pd.Timestamp("2020-01-01")
DATA_MULAI = "2018-01-01"
JENDELA = 250
ATR_N = 14
MULT = 3.0
SLOT = 10
BOBOT = 0.10
FEE_BELI = 0.0015
FEE_JUAL = 0.0025
PAJAK_DIV = 0.10
LOT = 100
NILAI_MIN = 5e9
ATR_LO, ATR_HI = 1.5, 5.0
HARGA_MIN = 50
MAKS_HARI = 500
MODAL = 1e8


def tick(p):
    p = np.asarray(p, float)
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25)


def baca_des():
    df = pd.DataFrame(list(koneksi.koneksi().des.find({}, {"_id": 0, "kode": 1, "mulai": 1, "akhir": 1})))
    df["mulai"], df["akhir"] = pd.to_datetime(df["mulai"]), pd.to_datetime(df["akhir"])
    return df


def atr_wilder(h, l, c):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    out = np.full(len(c), np.nan)
    if len(c) <= ATR_N:
        return out
    out[ATR_N - 1] = tr[:ATR_N].mean()
    for i in range(ATR_N, len(c)):
        out[i] = (out[i - 1] * (ATR_N - 1) + tr[i]) / ATR_N
    return out


def siapkan_ticker(raw, periode, adj):
    df = raw.dropna(subset=["open", "high", "low", "close", "adj_close", "volume"])
    df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
    df = df[df.index >= DATA_MULAI]
    if len(df) < JENDELA + 20:
        return None
    f = (df["adj_close"] / df["close"]).to_numpy() if adj else np.ones(len(df))
    ro, rh, rl, rc = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    o, c = ro * f, rc * f
    h = np.maximum.reduce([rh * f, o, c])
    l = np.minimum.reduce([rl * f, o, c])
    atr = atr_wilder(h, l, c)
    cs = pd.Series(c, index=df.index)
    maks = cs.rolling(JENDELA).max().shift(1).to_numpy()
    vol = df["volume"].to_numpy(float)
    nilai = pd.Series(rc * vol, index=df.index).rolling(20).mean().to_numpy()
    nol = pd.Series(vol == 0, index=df.index).rolling(5).sum().to_numpy()
    syariah = np.zeros(len(df), bool)
    for r in periode.itertuples():
        syariah |= (df.index >= r.mulai) & (df.index <= r.akhir)
    atr_pct = atr / c * 100
    sinyal = (c >= maks) & (nilai >= NILAI_MIN) & (atr_pct >= ATR_LO) & (atr_pct <= ATR_HI) & (rc >= HARGA_MIN) & (nol == 0) & syariah
    pc = np.r_[np.nan, rc[:-1]]
    div = np.zeros(len(df)) if adj else df["dividends"].fillna(0).to_numpy(float)
    return pd.DataFrame({"o": o, "h": h, "l": l, "c": c, "atr": atr, "sinyal": sinyal, "div": div, "ro": ro, "rc": rc,
                         "kunci_atas": (rh == rl) & (ro > pc), "kunci_bawah": (rh == rl) & (ro < pc)}, index=df.index)


def muat(adj):
    des = baca_des()
    kode = sorted(set(des.loc[des["akhir"] >= MULAI, "kode"]))
    data = {}
    for t, x in hg.banyak(kode).items():
        s = siapkan_ticker(x, des[des["kode"] == t], adj)
        if s is not None:
            data[t] = s
    semua = pd.concat([pd.Series(1, index=x.index[x.index >= MULAI]) for x in data.values()])
    jml = semua.groupby(level=0).size()
    tanggal = jml.index[jml >= 50].sort_values()
    tk = sorted(data)
    m = {k: np.vstack([data[t][k].reindex(tanggal).to_numpy() for t in tk]).T for k in ("o", "c", "atr", "div", "ro", "rc")}
    for k in ("sinyal", "kunci_atas", "kunci_bawah"):
        m[k] = np.vstack([data[t][k].reindex(tanggal).fillna(False).to_numpy(bool) for t in tk]).T
    return tk, tanggal, m


def biaya_sisi(p):
    return tick(p) / p


def simulasi(tk, tanggal, m, seed, ketat=False):
    rng = np.random.default_rng(seed)
    O, C, A, D, RO, S = m["o"], m["c"], m["atr"], m["div"], m["ro"], m["sinyal"]
    KA, KB = m["kunci_atas"], m["kunci_bawah"]
    kas, pos, tunda_jual, tunda_beli = MODAL, {}, set(), []
    terakhir = {}
    kurva, trades = np.empty(len(tanggal)), []
    for d in range(len(tanggal)):
        for j, p in pos.items():
            if D[d, j] > 0:
                masuk = p["lembar"] * D[d, j] * (1 - PAJAK_DIV)
                kas += masuk
                p["div"] += masuk
        for j in sorted(tunda_jual):
            if not np.isfinite(O[d, j]) or (ketat and KB[d, j]):
                continue
            p = pos.pop(j)
            hasil = p["lembar"] * O[d, j] * (1 - biaya_sisi(RO[d, j])) * (1 - FEE_JUAL)
            kas += hasil
            tunda_jual.discard(j)
            trades.append({"ticker": tk[j], "tgl_sinyal": p["sinyal"], "tgl_beli": p["tgl"], "harga_beli": p["harga"], "tgl_jual": tanggal[d],
                           "harga_jual": O[d, j], "puncak": p["puncak"], "atr_keluar": p["atr_kini"],
                           "ret": (hasil + p["div"]) / p["biaya"] * 100 - 100, "selesai": True})
        if tunda_beli:
            ekuitas = kas + sum(p["lembar"] * terakhir.get(j, p["harga"]) for j, p in pos.items())
            calon = [x for x in tunda_beli if x[0] not in pos]
            rng.shuffle(calon)
            for j, atr_sinyal, tgl_sinyal in calon:
                if len(pos) >= SLOT:
                    break
                if not np.isfinite(O[d, j]) or (ketat and KA[d, j]):
                    continue
                harga = O[d, j] * (1 + biaya_sisi(RO[d, j])) * (1 + FEE_BELI)
                dana = min(BOBOT * ekuitas, kas)
                lembar = np.floor(dana / harga / LOT) * LOT
                if lembar <= 0:
                    continue
                kas -= lembar * harga
                pos[j] = {"lembar": lembar, "biaya": lembar * harga, "harga": O[d, j], "tgl": tanggal[d], "sinyal": tgl_sinyal,
                          "stop": O[d, j] - MULT * atr_sinyal, "puncak": -np.inf, "hari": 0, "div": 0.0, "atr_kini": atr_sinyal}
        tunda_beli = []
        for j, p in pos.items():
            if not np.isfinite(C[d, j]):
                continue
            terakhir[j] = C[d, j]
            if j in tunda_jual:
                continue
            p["hari"] += 1
            if np.isfinite(A[d, j]):
                p["atr_kini"] = A[d, j]
            if C[d, j] < p["stop"] or p["hari"] > MAKS_HARI:
                tunda_jual.add(j)
                continue
            p["puncak"] = max(p["puncak"], C[d, j])
            if np.isfinite(A[d, j]):
                p["stop"] = max(p["stop"], p["puncak"] - MULT * A[d, j])
        for j in np.flatnonzero(S[d]):
            if j not in pos and np.isfinite(A[d, j]):
                tunda_beli.append((j, A[d, j], tanggal[d]))
        kurva[d] = kas + sum(p["lembar"] * terakhir.get(j, p["harga"]) for j, p in pos.items())
    for j, p in pos.items():
        nilai = p["lembar"] * terakhir.get(j, p["harga"]) * (1 - biaya_sisi(m["rc"][~np.isnan(m["rc"][:, j]), j][-1])) * (1 - FEE_JUAL)
        trades.append({"ticker": tk[j], "tgl_sinyal": p["sinyal"], "tgl_beli": p["tgl"], "harga_beli": p["harga"], "tgl_jual": None,
                       "harga_jual": terakhir.get(j), "puncak": p["puncak"], "atr_keluar": p["atr_kini"],
                       "ret": (nilai + p["div"]) / p["biaya"] * 100 - 100, "selesai": False})
    return pd.Series(kurva, index=tanggal), pd.DataFrame(trades)


def metrik(kurva):
    th = (kurva.index[-1] - kurva.index[0]).days / 365.25
    awal = MODAL
    cagr = ((kurva.iloc[-1] / awal) ** (1 / th) - 1) * 100
    dd = (kurva / np.maximum(kurva.cummax(), awal) - 1).min() * 100
    return cagr, dd


def sharpe(bulanan, rf_bulanan):
    ex = (bulanan - rf_bulanan.reindex(bulanan.index).ffill().bfill()).dropna()
    return ex.mean() / ex.std() * np.sqrt(12)


def rf_bulanan():
    b = dt.baca("makro/bunga_antarbank")["nilai"].dropna()
    b.index = pd.to_datetime(b.index).to_period("M")
    return (1 + b / 100) ** (1 / 12) - 1


def bulanan(seri):
    s = seri.resample("ME").last()
    r = s.pct_change()
    r.iloc[0] = s.iloc[0] / seri.iloc[0] - 1
    r.index = r.index.to_period("M")
    return r


def pembanding(mulai, akhir):
    jii = dt.baca("indeks/JKII")["close"].dropna()
    p = dt.baca("pasar")
    emas = (p["emas"] * p["usdidr"]).dropna()
    jii = jii[(jii.index >= mulai) & (jii.index <= akhir)]
    emas = emas[(emas.index >= mulai) & (emas.index <= akhir)]
    gab = pd.concat([jii.rename("jii"), emas.rename("emas")], axis=1).ffill().dropna()
    nilai, porsi, tahun = [], None, None
    for tgl, r in gab.iterrows():
        if porsi is None or tgl.year != tahun:
            total = 1.0 if porsi is None else porsi["jii"] * r["jii"] + porsi["emas"] * r["emas"]
            porsi = {"jii": total * 0.5 / r["jii"], "emas": total * 0.5 / r["emas"]}
            tahun = tgl.year
        nilai.append(porsi["jii"] * r["jii"] + porsi["emas"] * r["emas"])
    campur = pd.Series(nilai, index=gab.index)
    return {"Beli-tahan JII (indeks harga, tanpa dividen)": gab["jii"] / gab["jii"].iloc[0] * MODAL,
            "50% JII + 50% emas, rebalance tahunan": campur * MODAL}


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=100)
    a = ap.parse_args()
    rf = rf_bulanan()
    hasil = {}
    for adj in (False, True):
        tk, tanggal, m = muat(adj)
        print(f"universe {len(tk)} ticker, {len(tanggal)} hari, {tanggal[0].date()} s/d {tanggal[-1].date()}", flush=True)
        for ketat in (False, True):
            baris = []
            for seed in range(1, a.seed + 1):
                kurva, tr = simulasi(tk, tanggal, m, seed, ketat)
                cagr, dd = metrik(kurva)
                sel = tr[tr["selesai"]]
                baris.append({"seed": seed, "cagr": cagr, "dd": dd, "trade": len(sel), "terbuka": int((~tr["selesai"]).sum()),
                              "winrate": (sel["ret"] > 0).mean() * 100, "sharpe": sharpe(bulanan(kurva), rf)})
                if seed == 7:
                    hasil[(adj, ketat, "kurva7")] = kurva
                    hasil[(adj, ketat, "trade7")] = tr
            df = pd.DataFrame(baris)
            hasil[(adj, ketat)] = df
            nama = f"harga {'disesuaikan dividen' if adj else 'mentah + dividen tunai'}{', ARA/ARB terkunci dilewati' if ketat else ''}"
            q = df.quantile([0.05, 0.5, 0.95])
            print(f"{nama}: CAGR median {q.loc[0.5, 'cagr']:.1f}% (p5 {q.loc[0.05, 'cagr']:.1f} p95 {q.loc[0.95, 'cagr']:.1f}), "
                  f"DD median {q.loc[0.5, 'dd']:.1f}% (p5 {q.loc[0.05, 'dd']:.1f} p95 {q.loc[0.95, 'dd']:.1f}), "
                  f"trade median {q.loc[0.5, 'trade']:.0f}, winrate {q.loc[0.5, 'winrate']:.1f}%, Sharpe {q.loc[0.5, 'sharpe']:.2f}", flush=True)
    kurva = hasil[(False, False, "kurva7")]
    print(f"\npembanding {kurva.index[0].date()} s/d {kurva.index[-1].date()} (Sharpe: excess return di atas bunga antarbank, bulanan disetahunkan)")
    for nama, seri in pembanding(kurva.index[0], kurva.index[-1]).items():
        cagr, dd = metrik(seri)
        print(f"  {nama}: CAGR {cagr:.1f}%, DD {dd:.1f}%, Sharpe {sharpe(bulanan(seri), rf):.2f}")
    tr = hasil[(False, False, "trade7")]
    contoh = tr[tr["selesai"]].sample(10, random_state=42).sort_values("tgl_beli")
    print("\n10 trade acak (seed 7, harga mentah, random_state 42):")
    print(contoh.assign(puncak=contoh["puncak"].round(0), atr_keluar=contoh["atr_keluar"].round(1), ret=contoh["ret"].round(2)).to_string(index=False))


if __name__ == "__main__":
    utama()
