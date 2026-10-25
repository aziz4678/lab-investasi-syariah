import argparse
import json
import math

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.ingest import des_ojk
from backend.research import screener as sc

FEE_BELI = 0.0015
FEE_JUAL = 0.0025
BATAS_KUNCI = 0.065
PERIODE = {
    "dev": {"data": ("2010-01-01", "2019-12-31"), "sinyal_awal": "2011-01-01", "akhir": "2019-12-31"},
    "holdout": {"data": ("2010-01-01", "2026-10-23"), "sinyal_awal": "2019-12-01", "akhir": "2026-10-23"},
}
KODE_IDX = ["TECH", "ENVY", "DUCK", "HKMU", "JSKY", "PURE", "CBMF", "FREN", "META", "WBSA"]
META_HARGA = 238.0
MERGER = {"FREN": "EXCL"}
SEED = 7


def kalender(akhir):
    t = dt.baca("pasar")["ihsg"].dropna().index
    return t[(t >= "2010-01-01") & (t <= akhir)]


def panel_yahoo(kode, tgl):
    out = {}
    for k, df in dt.baca_banyak("harga", sorted(kode)).items():
        df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
        if len(df) < 250:
            continue
        f = df["adj_close"] / df["close"]
        out[k] = pd.DataFrame({"o_raw": df["open"], "h_raw": df["high"], "l_raw": df["low"], "c_raw": df["close"],
                               "o": df["open"] * f, "c": df["adj_close"], "v": df["volume"]}).reindex(tgl)
    return out


def panel_idx(tgl):
    i = dt.baca("idx_harian")
    i = i[i["StockCode"].isin(KODE_IDX)].copy()
    i["tgl"] = pd.to_datetime(i["tgl"])
    out = {}
    for k, g in i.groupby("StockCode"):
        g = g.drop_duplicates("tgl").set_index("tgl").sort_index()
        c = g["Close"].astype(float).where(g["Close"] > 0)
        o = g["OpenPrice"].astype(float).where(g["OpenPrice"] > 0).fillna(c)
        h = g["High"].astype(float).where(g["High"] > 0).fillna(c)
        lo = g["Low"].astype(float).where(g["Low"] > 0).fillna(c)
        out[k] = pd.DataFrame({"o_raw": o, "h_raw": h, "l_raw": lo, "c_raw": c, "o": o, "c": c, "v": g["Volume"].astype(float)}).reindex(tgl)
    return out


def susun(periode):
    cfg = PERIODE[periode]
    tgl = kalender(cfg["akhir"])
    des = des_ojk.baca()
    data = panel_yahoo(set(des["kode"]), tgl)
    if periode == "holdout":
        for k, df in panel_idx(tgl).items():
            if k not in data:
                data[k] = df
    kode = sorted(data)
    P = {kol: pd.DataFrame({k: data[k][kol] for k in kode}, index=tgl) for kol in ["o_raw", "h_raw", "l_raw", "c_raw", "o", "c", "v"]}
    P["v"] = P["v"].fillna(0)
    aktif_hari = P["v"] > 0
    akhir = pd.Timestamp(cfg["akhir"])
    terakhir = {k: (aktif_hari[k][aktif_hari[k]].index.max() if aktif_hari[k].any() else None) for k in kode}
    P["c_nilai"] = P["c"].ffill()
    P["c_raw_ff"] = P["c_raw"].ffill()
    P["konversi"] = pd.DataFrame(False, index=tgl, columns=kode)
    for k in kode:
        t = terakhir[k]
        if t is None:
            continue
        sesudah = tgl > t
        if k == "META" and t < akhir - pd.Timedelta(days=30):
            P["c_nilai"].loc[sesudah, k] = META_HARGA
            P["c"].loc[sesudah, k] = np.nan
        elif k in MERGER and t < akhir - pd.Timedelta(days=30) and MERGER[k] in P["c"]:
            p = MERGER[k]
            skala = P["c_nilai"].at[t, k] / P["c_nilai"].at[t, p]
            for kol in ["o", "c", "c_nilai"]:
                P[kol].loc[sesudah, k] = P[kol].loc[sesudah, p] * skala
            for kol in ["o_raw", "h_raw", "l_raw", "c_raw", "c_raw_ff", "v"]:
                P[kol].loc[sesudah, k] = P[kol].loc[sesudah, p]
            P["konversi"].loc[sesudah, k] = True
        elif t < akhir - pd.Timedelta(days=30):
            P["c_nilai"].loc[sesudah, k] = 0.0
            P["o"].loc[sesudah, k] = np.nan
            P["c"].loc[sesudah, k] = np.nan
            P["v"].loc[sesudah, k] = 0
    nilai = (P["c_raw"] * P["v"]).fillna(0)
    P["med60"] = nilai.rolling(60, min_periods=60).median()
    P["aktif250"] = (P["v"] > 0).astype(float).rolling(250, min_periods=250).mean()
    P["jml_data"] = P["c_raw"].notna().cumsum()
    ret = P["c"].ffill().pct_change(fill_method=None)
    P["vol250"] = ret.rolling(250, min_periods=250).std()
    akhir_bulan = pd.Series(tgl, index=tgl).groupby(tgl.to_period("M")).max()
    return {"tgl": tgl, "P": P, "des": des, "kode": kode, "akhir_bulan": akhir_bulan, "terakhir": terakhir, "cfg": cfg, "periode": periode}


def momentum(S, t):
    ab = S["akhir_bulan"]
    i = ab.index.get_loc(t.to_period("M"))
    if i < 12:
        return pd.Series(dtype=float)
    a, b = ab.iloc[i - 12], ab.iloc[i - 1]
    c = S["P"]["c"].ffill()
    m = c.loc[b] / c.loc[a] - 1
    return m.where(c.loc[a] > 0)


def lolos(S, t, min_nilai, min_harga):
    P = S["P"]
    ok = (P["med60"].loc[t] >= min_nilai) & (P["c_raw_ff"].loc[t] >= min_harga) & (P["jml_data"].loc[t] >= 250) & (P["aktif250"].loc[t] >= 0.9) & ~P["konversi"].loc[t]
    if S["periode"] == "holdout":
        ok &= ok.index.isin(list(des_ojk.syariah_pada(S["des"], t)))
    return ok[ok].index


def peringkat(S, t, jenis, calon):
    if jenis == "h21":
        s = S["P"]["vol250"].loc[t, calon].dropna()
        return list(s.sort_values(kind="mergesort").index)
    s = momentum(S, t).reindex(calon).dropna()
    return list(s.sort_values(ascending=False, kind="mergesort").index)


def jadwal(S):
    ab = S["akhir_bulan"]
    tgl = S["tgl"]
    out = []
    for t in ab[(ab >= S["cfg"]["sinyal_awal"])]:
        nxt = tgl[tgl > t]
        if len(nxt) == 0:
            continue
        out.append((t, nxt[0]))
    return out


def bisa(P, k, d, arah):
    v = P["v"].at[d, k]
    o = P["o"].at[d, k]
    if not (v > 0) or not (o > 0):
        return False
    h, lo = P["h_raw"].at[d, k], P["l_raw"].at[d, k]
    i = P["c_raw_ff"].index.get_loc(d)
    prev = P["c_raw_ff"].iat[i - 1, P["c_raw_ff"].columns.get_loc(k)] if i > 0 else np.nan
    cr = P["c_raw"].at[d, k]
    if h == lo and prev > 0 and cr > 0:
        r = cr / prev - 1
        if arah == "jual" and r <= -BATAS_KUNCI:
            return False
        if arah == "beli" and r >= BATAS_KUNCI:
            return False
    return True


def biaya_tick(P, k, d, kali):
    raw = P["o_raw"].at[d, k]
    if not (raw > 0):
        raw = P["c_raw_ff"].at[d, k]
    return kali * float(sc.fraksi(raw)) / raw


def simulasi(S, jenis, min_nilai=5e9, min_harga=100, tick=1):
    P = S["P"]
    tgl = S["tgl"]
    rb = jadwal(S)
    mulai = rb[0][1]
    hari = tgl[tgl >= mulai]
    rb_map = {d: t for t, d in rb}
    kas = 1.0
    pegang = {}
    tunda_jual = set()
    tunda_beli = {}
    ekuitas = []
    pnl = {}
    bobot_awal = {}
    nilai_kemarin = {}
    rekap = []
    dagang = 0.0
    cn = P["c_nilai"]
    for d in hari:
        aliran = {}
        if d in rb_map:
            t = rb_map[d]
            for k, a in tunda_beli.items():
                kas += a
            tunda_beli = {}
            calon = lolos(S, t, min_nilai, min_harga)
            urut = peringkat(S, t, jenis, calon)
            n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
            rank = {k: i + 1 for i, k in enumerate(urut)}
            harga_o = {k: (P["o"].at[d, k] if P["o"].at[d, k] > 0 else cn.at[d, k]) for k in pegang}
            eq_o = kas + sum(pegang[k] * (harga_o[k] if harga_o[k] == harga_o[k] else 0) for k in pegang)
            tetap = sorted([k for k in pegang if rank.get(k, 10 ** 9) <= 2 * n], key=lambda k: rank[k])
            jual = [k for k in pegang if k not in tetap]
            if len(tetap) > n:
                jual += tetap[n:]
                tetap = tetap[:n]
            baru = [k for k in urut if k not in pegang][: max(0, n - len(tetap))]
            for k in jual:
                tunda_jual.add(k)
            for k in tetap:
                w = pegang[k] * harga_o[k] / eq_o if eq_o > 0 else 0
                if w > 2 / n and bisa(P, k, d, "jual"):
                    lembar = pegang[k] - (eq_o / n) / harga_o[k]
                    terima = lembar * P["o"].at[d, k] * (1 - FEE_JUAL - biaya_tick(P, k, d, tick))
                    pegang[k] -= lembar
                    kas += terima
                    dagang += lembar * P["o"].at[d, k]
                    aliran[k] = aliran.get(k, 0) + terima
            for k in list(tunda_jual):
                if k in pegang and bisa(P, k, d, "jual"):
                    terima = pegang[k] * P["o"].at[d, k] * (1 - FEE_JUAL - biaya_tick(P, k, d, tick))
                    dagang += pegang[k] * P["o"].at[d, k]
                    kas += terima
                    aliran[k] = aliran.get(k, 0) + terima
                    del pegang[k]
                    tunda_jual.discard(k)
                elif k not in pegang:
                    tunda_jual.discard(k)
            if baru:
                anggaran = min(eq_o / n, kas / len(baru))
                for k in baru:
                    tunda_beli[k] = anggaran
                    kas -= anggaran
            rekap.append({"sinyal": t, "rebalance": d, "lolos": len(calon), "n": n, "jual": len(jual), "beli": len(baru)})
        else:
            for k in list(tunda_jual):
                if k in pegang and bisa(P, k, d, "jual"):
                    terima = pegang[k] * P["o"].at[d, k] * (1 - FEE_JUAL - biaya_tick(P, k, d, tick))
                    dagang += pegang[k] * P["o"].at[d, k]
                    kas += terima
                    aliran[k] = aliran.get(k, 0) + terima
                    del pegang[k]
                    tunda_jual.discard(k)
        for k in list(tunda_beli):
            if bisa(P, k, d, "beli"):
                a = tunda_beli.pop(k)
                harga = P["o"].at[d, k]
                pegang[k] = pegang.get(k, 0) + a / (harga * (1 + FEE_BELI + biaya_tick(P, k, d, tick)))
                dagang += a
                aliran[k] = aliran.get(k, 0) - a
        nilai = {k: pegang[k] * (cn.at[d, k] if cn.at[d, k] == cn.at[d, k] else 0) for k in pegang}
        eq = kas + sum(tunda_beli.values()) + sum(nilai.values())
        bln = d.to_period("M")
        for k in set(nilai) | set(aliran) | set(nilai_kemarin):
            pnl.setdefault((k, bln), 0.0)
            pnl[(k, bln)] += nilai.get(k, 0) - nilai_kemarin.get(k, 0) + aliran.get(k, 0)
            if (k, bln) not in bobot_awal:
                bobot_awal[(k, bln)] = nilai_kemarin.get(k, 0) + max(0, -aliran.get(k, 0))
        nilai_kemarin = nilai
        ekuitas.append((d, eq, kas + sum(tunda_beli.values()), len(pegang)))
    e = pd.DataFrame(ekuitas, columns=["tgl", "ekuitas", "kas", "posisi"]).set_index("tgl")
    return {"ekuitas": e["ekuitas"], "kas": e["kas"] / e["ekuitas"], "posisi": e["posisi"], "rekap": pd.DataFrame(rekap),
            "pnl": pnl, "bobot_awal": bobot_awal, "dagang": dagang, "mulai": mulai}


def pembanding_sama(S, min_nilai=5e9, min_harga=100):
    P = S["P"]
    tgl = S["tgl"]
    rb = jadwal(S)
    hari = tgl[tgl >= rb[0][1]]
    rb_map = {d: t for t, d in rb}
    cn = P["c_nilai"]
    eq = 1.0
    lembar = {}
    out = []
    for d in hari:
        if d in rb_map:
            if lembar:
                eq = sum(l * (P["o"].at[d, k] if P["o"].at[d, k] > 0 else (cn.at[d, k] if cn.at[d, k] == cn.at[d, k] else 0)) for k, l in lembar.items())
            calon = list(lolos(S, rb_map[d], min_nilai, min_harga))
            lembar = {}
            for k in calon:
                h = P["o"].at[d, k] if P["o"].at[d, k] > 0 else cn.at[d, k]
                if h > 0:
                    lembar[k] = (eq / len(calon)) / h
        nilai = sum(l * (cn.at[d, k] if cn.at[d, k] == cn.at[d, k] else 0) for k, l in lembar.items())
        out.append((d, nilai if lembar else eq))
    return pd.Series(dict(out))


def pembanding_jii(S, mulai):
    j = dt.baca("indeks/JKII")["close"]
    j.index = pd.to_datetime(j.index)
    tgl = S["tgl"]
    j = j.reindex(tgl.union(j.index)).ffill().reindex(tgl)
    i = tgl.get_loc(mulai)
    dasar = tgl[i - 1]
    s = j.loc[dasar:]
    hari = (s.index - dasar).days
    return (s / s.iloc[0]) * (1.025 ** (hari / 365.25))


def bulanan(e):
    m = e.groupby(e.index.to_period("M")).last()
    return m.pct_change().fillna(m.iloc[0] / 1.0 - 1)


def cagr(e, awal=1.0):
    hari = (e.index[-1] - e.index[0]).days + 1
    return ((e.iloc[-1] / awal) ** (365.25 / hari) - 1) * 100


def max_dd(e):
    return ((e / e.cummax()) - 1).min() * 100


def vol_tahunan(e):
    return bulanan(e).std() * math.sqrt(12) * 100


def per_tahun(e, awal=1.0):
    y = e.groupby(e.index.year).last()
    prev = y.shift(1)
    prev.iloc[0] = awal
    return (y / prev - 1) * 100


def jendela(e_s, e_b, panjang=36):
    ms = e_s.groupby(e_s.index.to_period("M")).last()
    bulan = list(ms.index)
    menang, total = 0, 0
    for i in range(0, len(bulan) - panjang + 1):
        b0, b1 = bulan[i], bulan[i + panjang - 1]
        def potong(e):
            per = e.index.to_period("M")
            awal = e[per < b0]
            a = awal.iloc[-1] if len(awal) else 1.0
            x = np.concatenate([[a], e[(per >= b0) & (per <= b1)].values])
            dd = (x / np.maximum.accumulate(x) - 1).min() * 100
            cg = ((x[-1] / a) ** (12 / panjang) - 1) * 100
            return dd, cg
        dds, cgs = potong(e_s)
        ddb, cgb = potong(e_b)
        total += 1
        if dds > ddb and cgs >= cgb - 2:
            menang += 1
    return menang, total


def bootstrap_blok(x, blok=3, n=5000, seed=SEED):
    x = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    m = len(x)
    k = math.ceil(m / blok)
    hasil = np.empty(n)
    for i in range(n):
        awal = rng.integers(0, m - blok + 1, size=k)
        idx = (awal[:, None] + np.arange(blok)).ravel()[:m]
        hasil[i] = x[idx].mean()
    return np.percentile(hasil, 5) * 100


def tanpa_top5(sim, e_b):
    eq = sim["ekuitas"]
    mb = eq.groupby(eq.index.to_period("M")).last()
    awal_bln = mb.shift(1)
    awal_bln.iloc[0] = 1.0
    r = mb / awal_bln - 1
    rb = bulanan(e_b).reindex(r.index).fillna(0)
    kontrib = {}
    for (k, b), v in sim["pnl"].items():
        kontrib[k] = kontrib.get(k, 0) + v / awal_bln[b]
    top = [k for k, _ in sorted(kontrib.items(), key=lambda x: -x[1])[:5]]
    r2 = r.copy()
    for (k, b), v in sim["pnl"].items():
        if k in top:
            w = sim["bobot_awal"].get((k, b), 0) / awal_bln[b]
            r2[b] += -v / awal_bln[b] + w * rb[b]
    e2 = (1 + r2).cumprod()
    eb2 = (1 + rb).cumprod()
    tahun = len(r2) / 12
    dd = lambda s: (np.concatenate([[1.0], s.values]) / np.maximum.accumulate(np.concatenate([[1.0], s.values])) - 1).min() * 100
    return (e2.iloc[-1] ** (1 / tahun) - 1) * 100, (eb2.iloc[-1] ** (1 / tahun) - 1) * 100, top, dd(e2), dd(eb2)


def korelasi_follow_tren(e, versi):
    rows = list(kdb.koneksi().backtest_ekuitas.find({"versi": versi}, {"_id": 0, "bulan": 1, "return": 1}))
    ft = pd.Series({pd.Period(r["bulan"], "M"): r["return"] for r in rows})
    m = bulanan(e)
    gab = pd.concat([m, ft], axis=1, join="inner").dropna()
    return round(float(gab.iloc[:, 0].corr(gab.iloc[:, 1])), 2), len(gab)


def ringkas(e):
    return {"cagr": round(cagr(e), 2), "dd": round(max_dd(e), 2), "vol": round(vol_tahunan(e), 2)}


def nilai_h21(S, base, eb, ej):
    s, b, j = ringkas(base["ekuitas"]), ringkas(eb), ringkas(ej)
    m, tot = jendela(base["ekuitas"], eb)
    k = [
        ("1. DD ≤ 0,75 × bobot sama", f"{s['dd']}% vs batas {round(0.75 * b['dd'], 2)}%", s["dd"] >= 0.75 * b["dd"]),
        ("2. DD tidak lebih dalam dari JII", f"{s['dd']}% vs {j['dd']}%", s["dd"] >= j["dd"]),
        ("3. CAGR ≥ bobot sama − 2", f"{s['cagr']}% vs batas {round(b['cagr'] - 2, 2)}%", s["cagr"] >= b["cagr"] - 2),
        ("4. CAGR ≥ JII − 2", f"{s['cagr']}% vs batas {round(j['cagr'] - 2, 2)}%", s["cagr"] >= j["cagr"] - 2),
        ("5. Vol ≤ 0,85 × bobot sama", f"{s['vol']}% vs batas {round(0.85 * b['vol'], 2)}%", s["vol"] <= 0.85 * b["vol"]),
        ("6. Menang ≥ 60% jendela 36 bln", f"{m}/{tot} = {round(100 * m / max(tot, 1), 1)}%", tot > 0 and m / tot >= 0.6),
    ]
    return k, s, b, j


def nilai_h22(S, base, eb, ej):
    s, b, j = ringkas(base["ekuitas"]), ringkas(eb), ringkas(ej)
    ms, mb = bulanan(base["ekuitas"]), bulanan(eb)
    selisih = (ms - mb.reindex(ms.index)).dropna()
    bs = bootstrap_blok(selisih.values)
    ys, yb = per_tahun(base["ekuitas"]), per_tahun(eb)
    pos = int(((ys - yb.reindex(ys.index)) > 0).sum())
    cg5, cgb5, top, _, _ = tanpa_top5(base, eb)
    k = [
        ("1. CAGR > bobot sama", f"{s['cagr']}% vs {b['cagr']}%", s["cagr"] > b["cagr"]),
        ("2. CAGR > JII + 2,5", f"{s['cagr']}% vs batas {round(j['cagr'] + 2.5, 2)}%", s["cagr"] > j["cagr"] + 2.5),
        ("3. Bootstrap blok 3 bln p5 > 0", f"{round(bs, 3)}%/bln", bs > 0),
        ("4. Selisih tahunan + ≥ 60% tahun", f"{pos}/{len(ys)} tahun", pos / len(ys) >= 0.6),
        ("5. Tanpa 5 ticker terbaik > bobot sama", f"{round(cg5, 2)}% vs {round(cgb5, 2)}% (tanpa {', '.join(top)})", cg5 > cgb5),
        ("6. DD ≥ bobot sama − 10", f"{s['dd']}% vs batas {round(b['dd'] - 10, 2)}%", s["dd"] >= b["dd"] - 10),
    ]
    return k, s, b, j


def cetak_kriteria(judul, k):
    print(f"\n{judul}: {sum(1 for x in k if x[2])}/{len(k)} lulus")
    for nama, nilai, ok in k:
        print(f"  {'LULUS' if ok else 'GAGAL'}  {nama}: {nilai}")


def jalankan(periode):
    S = susun(periode)
    akhir = S["cfg"]["akhir"]
    print(f"Periode {periode}: {len(S['kode'])} kode, kalender {S['tgl'][0].date()}..{S['tgl'][-1].date()}")
    eb = pembanding_sama(S)
    hasil = {}
    for jenis in ["h21", "h22"]:
        base = simulasi(S, jenis)
        e = base["ekuitas"]
        ej = pembanding_jii(S, base["mulai"])
        ebj = eb.reindex(e.index)
        f = nilai_h21 if jenis == "h21" else nilai_h22
        k, s, b, j = f(S, base, ebj, ej)
        tahun = (e.index[-1] - e.index[0]).days / 365.25
        info = {
            "mulai": str(base["mulai"].date()), "akhir": str(e.index[-1].date()),
            "n_rata": round(base["rekap"]["n"].mean(), 1), "lolos_rata": round(base["rekap"]["lolos"].mean(), 1),
            "turnover_th": round(base["dagang"] / 2 / e.mean() / tahun * 100, 1), "kas_rata": round(base["kas"].mean() * 100, 1),
        }
        kor = korelasi_follow_tren(e, "h11a_dev" if periode == "dev" else "h11a_2020")
        print(f"\n===== {jenis.upper()} {periode} =====")
        print(f"strategi {s} | bobot sama {b} | JII {j}")
        print(f"info {info} | korelasi Follow Tren {kor}")
        cetak_kriteria(f"{jenis.upper()} kriteria dasar", k)
        th = pd.DataFrame({"strategi": per_tahun(e), "bobot_sama": per_tahun(ebj), "jii": per_tahun(ej, ej.iloc[0])}).round(1)
        print(th.to_string())
        sens = {}
        daftar = [("S1 biaya 2 tick", {"tick": 2}, {}), ("S2 likuiditas ≥ Rp20 M", {"min_nilai": 20e9}, {"min_nilai": 20e9}),
                  ("S4 harga ≥ Rp200" if jenis == "h21" else "S3 harga ≥ Rp200", {"min_harga": 200}, {"min_harga": 200})]
        for nama, ps, pb in daftar:
            sim = simulasi(S, jenis, **ps)
            ebx = pembanding_sama(S, **pb).reindex(sim["ekuitas"].index) if pb else ebj
            kx, sx, bx, _ = f(S, sim, ebx, ej)
            wajib = [kx[0], kx[2]] if jenis == "h21" else [kx[0], kx[4]]
            sens[nama] = {"strategi": sx, "bobot_sama": bx, "wajib": [(a, v, o) for a, v, o in wajib], "lulus": all(o for _, _, o in wajib)}
            print(f"  {nama}: {'LULUS' if sens[nama]['lulus'] else 'GAGAL'} | strategi {sx} | bobot sama {bx} | " + " ; ".join(f"{a}: {v} {'✔' if o else '✘'}" for a, v, o in wajib))
        if jenis == "h21":
            cg5, cgb5, top, dd5, ddb5 = tanpa_top5(base, ebj)
            dd_ok = dd5 >= 0.75 * ddb5
            ok = dd_ok and cg5 >= cgb5 - 2
            sens["S3 tanpa 5 ticker terbaik"] = {"cagr": round(cg5, 2), "cagr_bobot_sama": round(cgb5, 2), "dd_bulanan": round(dd5, 2), "dd_bobot_sama_bulanan": round(ddb5, 2), "top": top, "lulus": ok}
            print(f"  S3 tanpa 5 ticker terbaik ({', '.join(top)}): {'LULUS' if ok else 'GAGAL'} | CAGR {round(cg5, 2)}% vs batas {round(cgb5 - 2, 2)}% {'✔' if cg5 >= cgb5 - 2 else '✘'} ; DD bulanan {round(dd5, 2)}% vs batas {round(0.75 * ddb5, 2)}% {'✔' if dd_ok else '✘'}")
        lulus = all(x[2] for x in k) and all(v["lulus"] for v in sens.values())
        print(f"\n>>> {jenis.upper()} {periode}: {'LULUS SEMUA' if lulus else 'GAGAL'}")
        hasil[jenis] = {"kriteria": [(a, v, bool(o)) for a, v, o in k], "strategi": s, "bobot_sama": b, "jii": j, "info": info,
                        "korelasi_follow_tren": kor, "sensitivitas": sens, "lulus": lulus,
                        "per_tahun": th.reset_index().rename(columns={"index": "tahun"}).to_dict("records"),
                        "kurva": {"tgl": [str(x.date()) for x in e.index[::5]], "strategi": [round(float(x), 4) for x in e.values[::5]],
                                  "bobot_sama": [round(float(x), 4) for x in ebj.values[::5]], "jii": [round(float(x), 4) for x in ej.reindex(e.index).values[::5]]}}
    hasil = json.loads(json.dumps(hasil, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    dt.simpan_hasil(f"h2122_{periode}", hasil)
    return hasil


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--buka-holdout", action="store_true")
    a = ap.parse_args()
    if a.periode == "holdout":
        if not a.buka_holdout:
            raise SystemExit("Holdout terkunci. Perlu --buka-holdout setelah user melihat hasil dev.")
        if dt.baca_hasil("h2122_holdout") is not None:
            raise SystemExit("Holdout H21/H22 sudah pernah dibuka. Tidak boleh dijalankan ulang.")
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
