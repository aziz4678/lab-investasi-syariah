import re

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

KELOMPOK = {"PU": ["Money Market Fund"], "PT": ["Fixed Income Fund", "Sukuk Based Fund"]}
LOMPAT = {"PU": 0.10, "PT": 0.15}
MIN_PRODUK = 5
DATAR = 0.01
INFLASI_TAMBAHAN = {"2026-10": 3.23}
EPISODE = {"2013": ("2013-05", "2013-12"), "2015": ("2015-01", "2015-12"), "2018": ("2018-01", "2018-12"),
           "Mar2020": ("2020-02", "2020-04"), "2026": ("2026-01", "2026-12")}
CAMPURAN = [(0, 100), (30, 70), (50, 50), (70, 30)]


def p(x, n=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x * 100:+.{n}f}".replace(".", ",")


def muat():
    db = d.koneksi()
    tipe = [t for v in KELOMPOK.values() for t in v]
    df = pd.DataFrame(list(db.rd_ojk.find({"syariah": True, "denominasi": "IDR", "tipe": {"$in": tipe}},
                                           {"_id": 0, "kunci": 1, "produk": 1, "tipe": 1, "tgl": 1, "nav": 1, "nab": 1, "fund": 1})))
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    df["kelompok"] = df["tipe"].map({t: k for k, v in KELOMPOK.items() for t in v})
    fund = df["fund"].astype("Int64").astype(str)
    df["seri"] = np.where(df["fund"].notna(), "f" + fund, df["kunci"])
    bagi = {int(x["_id"]) for x in db.rd_produk.find({"Dividend": True}, {"_id": 1})}
    return df, bagi


def pilih_seri(df, bagi):
    akhir = df.sort_values("tgl").groupby("seri").tail(1).set_index("seri")
    info = pd.DataFrame({
        "kunci": akhir["kunci"], "produk": akhir["produk"], "kelompok": akhir["kelompok"], "fund": akhir["fund"],
        "mulai": df.groupby("seri")["tgl"].min(), "selesai": df.groupby("seri")["tgl"].max(), "nab": df.groupby("seri")["nab"].mean()})
    info["dasar"] = info["kunci"].map(lambda k: re.sub(r" KELAS [A-Z0-9]+(?=\|)", "", k))
    info = info.sort_values(["mulai", "nab"], ascending=[True, False])
    pilih = info.groupby(["kelompok", "dasar"]).head(1).copy()
    dobel = len(info) - len(pilih)
    seri = {s: g.groupby("tgl")["nav"].last().sort_index() for s, g in df[df["seri"].isin(pilih.index)].groupby("seri")}
    pilih["bh_pasardana"] = pilih["fund"].map(lambda f: pd.notna(f) and int(f) in bagi)
    def datar(s):
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))
        r12 = (s / s.shift(12) - 1).dropna()
        return len(r12) >= 6 and r12.median() < DATAR
    pilih["bh_datar"] = [datar(seri[s]) for s in pilih.index]
    pilih["bh"] = pilih["bh_pasardana"] | pilih["bh_datar"]
    return pilih, seri, dobel


def tabel_return(seri, idx):
    semua = pd.period_range(min(seri[s].index.min() for s in idx), max(seri[s].index.max() for s in idx), freq="M")
    return pd.DataFrame({s: seri[s].reindex(semua).pct_change(fill_method=None) for s in idx})


def indeks(R):
    n = R.notna().sum(axis=1)
    cukup = n[n >= MIN_PRODUK]
    if cukup.empty:
        return None, n
    mulai = cukup.index[0]
    r = R.loc[mulai:].mean(axis=1, skipna=True).fillna(0.0)
    level = pd.concat([pd.Series([1.0], index=[mulai - 1]), (1 + r).cumprod()])
    return level, n


def cpi():
    s = dt.baca("makro/inflasi")["nilai"].astype(float)
    s.index = pd.to_datetime(s.index).to_period("M")
    for b, v in INFLASI_TAMBAHAN.items():
        s.loc[pd.Period(b, "M")] = v
    s = s.sort_index()
    return ((1 + s / 100) ** (1 / 12)).cumprod()


def per_tahun(L, c):
    hasil = {}
    th = sorted({x.year for x in L.index[1:]})
    for y in th:
        a = L[L.index < pd.Period(f"{y}-01", "M")]
        a = a.index[-1] if len(a) else L.index[0]
        b = L[L.index <= pd.Period(f"{y}-12", "M")].index[-1]
        nom = L[b] / L[a] - 1
        inf = c.get(b, np.nan) / c.get(a, np.nan) - 1
        label = f"{y}" if (b.month == 12 and a.month == 12) else f"{y} ({(a + 1).strftime('%b')}-{b.strftime('%b')})"
        hasil[y] = (label, nom, (1 + nom) / (1 + inf) - 1)
    return hasil


def metrik(L, c):
    bulan = (L.index[-1] - L.index[0]).n
    cagr = (L.iloc[-1] / L.iloc[0]) ** (12 / bulan) - 1
    inf = (c[L.index[-1]] / c[L.index[0]]) ** (12 / bulan) - 1
    riil = (1 + cagr) / (1 + inf) - 1
    j = [(t, (L[t] / L[t - 36]) ** (1 / 3) - 1, (c[t] / c[t - 36]) ** (1 / 3) - 1 + 0.015) for t in L.index if (t - 36) in L.index and t in c.index and (t - 36) in c.index]
    lulus = np.mean([a >= b for _, a, b in j]) if j else np.nan
    dd = L / L.cummax() - 1
    lembah = dd.idxmin()
    puncak = L.loc[:lembah].idxmax()
    pulih = L.loc[lembah:][L.loc[lembah:] >= L[puncak]]
    lama = f"{(pulih.index[0] - lembah).n} bln" if len(pulih) else "belum"
    ep = {}
    for k, (a, b) in EPISODE.items():
        w = dd.loc[pd.Period(a, "M"):pd.Period(b, "M")]
        ep[k] = w.min() if len(w) and w.index[0] <= pd.Period(b, "M") and pd.Period(a, "M") >= L.index[0] else np.nan
    return {"cagr": cagr, "riil": riil, "jendela": lulus, "n_jendela": len(j), "dd": dd.min(), "lembah": lembah, "pulih": lama, "ep": ep}


def campur(Lpt, Lpu, w_pt):
    mulai = max(Lpt.index[0], Lpu.index[0])
    rpt = (Lpt / Lpt.shift(1) - 1).loc[mulai + 1:]
    rpu = (Lpu / Lpu.shift(1) - 1).loc[mulai + 1:]
    a, b = w_pt, 1 - w_pt
    nilai = [1.0]
    for t in rpt.index:
        a *= 1 + rpt[t]
        b *= 1 + rpu[t]
        nilai.append(a + b)
        if t.month == 12:
            tot = a + b
            a, b = tot * w_pt, tot * (1 - w_pt)
    return pd.Series(nilai, index=[mulai] + list(rpt.index))


def sebaran(seri, idx, akhir, lompat):
    baris = {}
    for s in idx:
        x = seri[s]
        for y in range(2014, akhir.year + 1):
            if (s, y) in lompat:
                continue
            a = pd.Period(f"{y - 1}-12", "M")
            b = pd.Period(f"{y}-12", "M") if y < akhir.year else akhir
            if a in x.index and b in x.index:
                baris.setdefault(y, []).append(x[b] / x[a] - 1)
    return baris


def utama():
    df, bagi = muat()
    pilih, seri, dobel = pilih_seri(df, bagi)
    c = cpi()
    akhir = df["tgl"].max()
    print(f"Data rd_ojk syariah IDR s/d {akhir}. Seri kelas dobel dikeluarkan: {dobel}. Seri dipakai: {len(pilih)} "
          f"(PU {sum(pilih.kelompok == 'PU')}, PT {sum(pilih.kelompok == 'PT')}).")
    print(f"Bagi hasil tunai dikeluarkan: {int(pilih.bh.sum())} (tanda Pasardana {int(pilih.bh_pasardana.sum())}, "
          f"NAV datar <{DATAR * 100:.0f}%/th median 12 bln {int((pilih.bh_datar & ~pilih.bh_pasardana).sum())} tambahan); "
          f"per kelompok PU {int(pilih[pilih.kelompok == 'PU'].bh.sum())}, PT {int(pilih[pilih.kelompok == 'PT'].bh.sum())}.")
    L, periksa, lompat = {}, [], set()
    for k in KELOMPOK:
        for versi, saring in (("", ~pilih.bh), ("+bh", pilih.bh | ~pilih.bh)):
            idx = pilih[(pilih.kelompok == k) & saring].index
            R = tabel_return(seri, idx)
            ekstrem = R.abs() > LOMPAT[k]
            if versi == "+bh":
                for s in idx:
                    r = R[s][ekstrem[s]]
                    for t, v in r.items():
                        periksa.append((abs(v), k, pilih.loc[s, "produk"], str(t), v, bool(pilih.loc[s, "bh"])))
                        lompat.add((s, t.year))
            R = R.mask(ekstrem)
            lv, n = indeks(R)
            L[k + versi] = lv
            if lv is not None:
                print(f"  {k + versi:6s} mulai {lv.index[1]}  produk awal {n[lv.index[1]]}, akhir {n[akhir] if akhir in n.index else 0}, "
                      f"min sesudah mulai {n.loc[lv.index[1]:].min()}, total seri {len(idx)}")

    nama = ["PU", "PT", "PU+bh", "PT+bh"]
    M = {k: metrik(L[k], c) for k in nama}
    T = {k: per_tahun(L[k], c) for k in nama}
    th = sorted(set().union(*[T[k].keys() for k in nama]))
    print("\nTabel indeks (bobot sama; +bh = termasuk RD bagi hasil tunai; nominal / riil)")
    print(f"{'tahun':18s}" + "".join(f"{k:>16s}" for k in nama))
    for y in th:
        lab = f"{y} s/d {akhir.strftime('%b')}" if y == akhir.year else f"{y}"
        print(f"{lab:18s}" + "".join(f"{(p(T[k][y][1]) + ' / ' + p(T[k][y][2])) if y in T[k] else '-':>16s}" for k in nama))
    baris = [("CAGR nom / riil", lambda m: p(m["cagr"]) + " / " + p(m["riil"])),
             ("3th >= inf+1,5%", lambda m: f"{m['jendela'] * 100:.0f}% (n={m['n_jendela']})"),
             ("max DD", lambda m: f"{p(m['dd'], 2)} {m['lembah']}"),
             ("pulih dr lembah", lambda m: m["pulih"])] + \
            [(f"DD {e}", (lambda e: lambda m: p(m["ep"][e], 2))(e)) for e in EPISODE]
    for lab, f in baris:
        print(f"{lab:18s}" + "".join(f"{f(M[k]):>16s}" for k in nama))

    print("\nCampuran tetap PT/PU (indeks tanpa bagi hasil tunai, rebalance tiap akhir Desember)")
    print(f"{'PT/PU':8s}{'mulai':>9s}{'CAGR nom':>10s}{'riil':>8s}{'3th lulus':>11s}{'max DD':>9s}{'pulih':>8s}" + "".join(f"{'DD ' + e:>11s}" for e in EPISODE))
    for a, b in CAMPURAN:
        Lc = campur(L["PT"], L["PU"], a / 100)
        m = metrik(Lc, c)
        print(f"{f'{a}/{b}':8s}{str(Lc.index[1]):>9s}{p(m['cagr']):>10s}{p(m['riil']):>8s}{m['jendela'] * 100:>10.0f}%{p(m['dd'], 2):>9s}{m['pulih']:>8s}"
              + "".join(f"{p(m['ep'][e], 2):>11s}" for e in EPISODE))

    print("\nSebaran return per produk per tahun (tanpa bagi hasil tunai, seri lengkap Des-Des): n p10 / p50 / p90")
    sb = {k: sebaran(seri, pilih[(pilih.kelompok == k) & ~pilih.bh].index, akhir, lompat) for k in KELOMPOK}
    print(f"{'tahun':10s}{'PU':>30s}{'PT':>30s}")
    for y in sorted(set(sb["PU"]) | set(sb["PT"])):
        sel = []
        for k in KELOMPOK:
            v = sb[k].get(y, [])
            sel.append(f"{len(v):3d}  " + " / ".join(p(np.percentile(v, q)) for q in (10, 50, 90)) if len(v) >= 3 else f"{len(v):3d}  -")
        lab = f"{y}" if y < akhir.year else f"{y} s/d {akhir.strftime('%b')}"
        print(f"{lab:10s}" + "".join(f"{s:>30s}" for s in sel))

    periksa.sort(reverse=True)
    print(f"\nDaftar periksa lompatan NAV bulanan (> +/-{LOMPAT['PU'] * 100:.0f}% PU, > +/-{LOMPAT['PT'] * 100:.0f}% PT): {len(periksa)} kejadian di "
          f"{len({x[2] for x in periksa})} produk; bulan itu dikeluarkan dari indeks, tahun produk itu dikeluarkan dari sebaran")
    for _, k, prod, t, v, bh in periksa[:10]:
        print(f"  {k} {t} {p(v)}  {prod}{'  [bagi hasil, hanya di versi +bh]' if bh else ''}")

    print("\nKeterbatasan")
    print("  - NAV bulanan akhir bulan: penurunan di tengah bulan tidak terlihat; NAV saja, bukan return total.")
    print("  - Tanda bagi hasil tunai Pasardana hanya untuk produk yang masih ada; RD bubar hanya tersaring lewat NAV datar.")
    print("  - Kelas & seri lama disambung heuristik (nama + kustodian); salah sambung bisa menimbulkan lompatan.")
    print("  - Inflasi = YoY BPS dibagi rata per bulan (pendekatan IHK); deskriptif, bukan hipotesis, tidak ada biaya beli/jual.")


if __name__ == "__main__":
    utama()
