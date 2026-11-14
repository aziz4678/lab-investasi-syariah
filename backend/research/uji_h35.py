import hashlib
import re
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.db import koneksi as d
from backend.research import analisis_likuiditas as al
from backend.research import analisis_profil as apf

AWAL = pd.Period("2001-05", "M")
AKHIR = pd.Period("2026-10", "M")
SAMBUNG = pd.Period("2008-01", "M")
FRED_AKHIR = pd.Period("2023-12", "M")
DASAR = {"div_jii": 0.025, "div_gl": 0.018, "pra2008": "gl_djim_titans"}
PESIMIS = {"div_jii": 0.0, "div_gl": 0.010, "pra2008": "us_djim"}
BIAYA_JII, BIAYA_GL_PRA, BIAYA_GL_ETF, BIAYA_REBAL = 0.005, 0.006, 0.003, 0.005
PORTO = [("100% IDX", 1.0), ("70/30", 0.7), ("50/50", 0.5), ("100% global", 0.0)]
DEKADE = [("Jun 2001-2009", AWAL, pd.Period("2009-12", "M")), ("2010-2019", pd.Period("2009-12", "M"), pd.Period("2019-12", "M")),
          ("2020-Okt 2026", pd.Period("2019-12", "M"), AKHIR)]
JENDELA = 120
JENDELA_RD = 60
LOMPAT_RD = 0.30
BUKAN_SAHAM = re.compile(r"SUKUK|BALANCED|MIXED|INCOME|GOLD|FIXED|PASAR UANG|MONEY", re.I)


def bulanan(s):
    s = s.dropna().sort_index()
    s.index = pd.to_datetime(s.index)
    m = s.resample("ME").last()
    m.index = m.index.to_period("M")
    return m


def sidik(s):
    return hashlib.sha1(np.round(s.to_numpy(dtype=float), 6).tobytes()).hexdigest()[:12]


def kurs_harian():
    k = harga.indeks("kurs/USD")["close"].dropna().sort_index()
    k.index = pd.to_datetime(k.index)
    return k


def kurs():
    f = harga.indeks("makro/kurs_akhir_bulan")["nilai"].astype(float)
    f.index = pd.to_datetime(f.index).to_period("M")
    f = f.loc[:FRED_AKHIR]
    k = bulanan(kurs_harian()).loc[FRED_AKHIR + 1:AKHIR]
    return pd.concat([f, k]).loc[AWAL:AKHIR]


def cek_kurs():
    k = kurs_harian()
    med = k.rolling(21, center=True, min_periods=5).median()
    pencil = (k / med - 1).abs() > 0.05
    jeda = k.index.to_series().diff().dt.days > 7
    buruk = set(k.index[pencil | jeda].to_period("M"))
    f = harga.indeks("makro/kurs_akhir_bulan")["nilai"].astype(float)
    f.index = pd.to_datetime(f.index).to_period("M")
    m = bulanan(k)
    bln = [b for b in f.loc[pd.Period("2001-07", "M"):FRED_AKHIR].index if b in m.index and b not in buruk]
    sel = (m.loc[bln] / f.loc[bln] - 1).abs()
    pasca = k.loc["2024-01":"2026-10"]
    return {"bulan": len(bln), "bulan_buruk": len([b for b in buruk if AWAL <= b <= FRED_AKHIR]), "median": float(sel.median()), "p95": float(sel.quantile(0.95)),
            "maks": float(sel.max()), "beda_1": int((sel > 0.01).sum()), "beda_3": int((sel > 0.03).sum()),
            "pasca2023_pencil": int(pencil.loc["2024-01":"2026-10"].sum()), "pasca2023_jeda": int(jeda.loc["2024-01":"2026-10"].sum()), "pasca2023_hari": len(pasca)}


def seri(asumsi):
    j = bulanan(harga.indeks("indeks/JKII")["close"]).loc[AWAL:AKHIR]
    pra = bulanan(harga.indeks_luar(asumsi["pra2008"])["close"]).loc[AWAL:SAMBUNG]
    etf = bulanan(harga.indeks_luar("gl_msci_world_islamic")["adj_close"]).loc[SAMBUNG:AKHIR]
    fx = kurs()
    bulan = pd.period_range(AWAL + 1, AKHIR, freq="M")
    for nama, s in (("JKII", j), ("kurs", fx)):
        hilang = [b for b in pd.period_range(AWAL, AKHIR, freq="M") if b not in s.index]
        if hilang:
            raise harga.DataTidakAda(f"{nama} bolong: {hilang[:5]}")
    r_j = (j / j.shift(1) - 1).reindex(bulan)
    r_idx = (1 + r_j) * (1 + asumsi["div_jii"]) ** (1 / 12) * (1 - BIAYA_JII) ** (1 / 12) - 1
    r_pra = (pra / pra.shift(1)) *(1 + asumsi["div_gl"]) ** (1 / 12) * (1 - BIAYA_GL_PRA) ** (1 / 12) - 1
    r_etf = (1 + (etf / etf.shift(1) - 1)) * (1 - BIAYA_GL_ETF) ** (1 / 12) - 1
    r_usd = pd.concat([r_pra.loc[AWAL + 1:SAMBUNG], r_etf.loc[SAMBUNG + 1:]]).reindex(bulan)
    r_fx = (fx / fx.shift(1) - 1).reindex(bulan)
    if r_usd.isna().any() or r_idx.isna().any() or r_fx.isna().any():
        raise harga.DataTidakAda("ada bulan tanpa return")
    r_gl = (1 + r_usd) * (1 + r_fx) - 1
    return pd.DataFrame({"idx": r_idx, "gl": r_gl, "gl_usd": r_usd, "fx": r_fx})


def porto(R, w_idx, biaya=BIAYA_REBAL):
    t = {"idx": w_idx, "gl": 1 - w_idx}
    w = dict(t)
    nilai, total_biaya = [1.0], 0.0
    for b, r in R.iterrows():
        for x in w:
            w[x] *= 1 + r[x]
        tot = sum(w.values())
        if b.month == 12 and 0 < w_idx < 1:
            pindah = sum(max(0.0, w[x] - t[x] * tot) for x in w)
            c = biaya * pindah
            total_biaya += c
            tot -= c
            w = {x: t[x] * tot for x in t}
        nilai.append(tot)
    return pd.Series(nilai, index=[R.index[0] - 1] + list(R.index)), total_biaya


def cagr(V, a=None, b=None):
    V = V.loc[a:b]
    n = len(V) - 1
    return float((V.iloc[-1] / V.iloc[0]) ** (12 / n) - 1)


def turun(V):
    dd = V / V.cummax() - 1
    pos = int(np.argmin(dd.to_numpy()))
    puncak = int(np.argmax(V.to_numpy()[:pos + 1]))
    sesudah = np.nonzero(V.to_numpy()[pos:] >= V.iloc[puncak])[0]
    pulih = int(pos + sesudah[0] - puncak) if len(sesudah) else None
    bawah = (dd < 0).astype(int).to_numpy()
    terlama, jalan = 0, 0
    for x in bawah:
        jalan = jalan + 1 if x else 0
        terlama = max(terlama, jalan)
    return {"dd": float(dd.min()), "puncak": str(V.index[puncak]), "lembah": str(V.index[pos]), "pulih": pulih,
            "sejak_puncak": int(len(V) - 1 - puncak), "terlama_bawah": terlama}


def jendela(V, n):
    a = V.to_numpy()
    return pd.Series((a[n:] / a[:-n]) ** (12 / n) - 1, index=V.index[n:])


def metrik(V, Vi, n=JENDELA):
    t = turun(V)
    c = cagr(V)
    j, ji = jendela(V, n), jendela(Vi, n)
    return {"cagr": c, **t, "mar": c / abs(t["dd"]) if t["dd"] < 0 else None, "j_buruk": float(j.min()), "j_buruk_akhir": str(j.idxmin()),
            "j_baik": float(j.max()), "j_baik_akhir": str(j.idxmax()), "j_menang": float((j > ji).mean()), "n_jendela": len(j),
            "dekade": {nm: cagr(V, a, b) for nm, a, b in DEKADE} if V.index[0] <= AWAL else {}}


def jalur1(asumsi):
    R = seri(asumsi)
    V = {nm: porto(R, w) for nm, w in PORTO}
    Vi = V["100% IDX"][0]
    hasil = {nm: {**metrik(v, Vi), "biaya_rebal": b} for nm, (v, b) in V.items()}
    return R, hasil


def kriteria(h):
    a, b = h["50/50"], h["100% IDX"]
    k1 = a["j_buruk"] > b["j_buruk"]
    k2 = a["mar"] >= b["mar"]
    k3 = a["cagr"] >= b["cagr"] - 0.02
    return {"K1": [k1, a["j_buruk"], b["j_buruk"]], "K2": [k2, a["mar"], b["mar"]], "K3": [k3, a["cagr"], b["cagr"]]}


def pecah(R):
    out = {}
    for nm, a, b in [("Penuh", AWAL, AKHIR)] + DEKADE:
        x = R.loc[a + 1:b]
        g = lambda r: float((1 + r).prod() ** (12 / len(x)) - 1)
        out[nm] = {"usd": g(x["gl_usd"]), "kurs": g(x["fx"]), "rupiah": g(x["gl"]), "idx": g(x["idx"])}
    return out


def cek_xiji():
    x = harga.indeks("etf/XIJI")
    xa = bulanan(x["adj_close"])
    j = bulanan(harga.indeks("indeks/JKII")["close"])
    a = max(xa.index[0] + 1, j.index[0])
    a, b = a, AKHIR
    rx = (xa / xa.shift(1) - 1).loc[a + 1:b]
    rj = (j / j.shift(1) - 1).loc[a + 1:b]
    n = len(rx)
    cx = float((1 + rx).prod() ** (12 / n) - 1)
    cj = float((1 + rj).prod() ** (12 / n) - 1)
    rh = x["close"].pct_change().abs()
    return {"mulai": str(a), "akhir": str(b), "bulan": n, "xiji_tr": cx, "jkii_harga": cj, "selisih": cx - cj,
            "div_xiji_per_th": float(x.loc[x["dividends"] > 0, "dividends"].groupby(pd.to_datetime(x.loc[x["dividends"] > 0].index).year).sum().mean()) if (x["dividends"] > 0).any() else 0.0,
            "lonjakan_15": int((rh > 0.15).sum())}


def indeks_rd_global():
    db = d.koneksi()
    df = pd.DataFrame(list(db.rd_ojk.find({"syariah": True, "denominasi": "USD", "tipe": {"$in": ["Global Fund", "Equity Fund"]}},
                                          {"_id": 0, "kunci": 1, "produk": 1, "tipe": 1, "tgl": 1, "nab": 1, "unit": 1, "fund": 1})))
    keluar = sorted(df.loc[df["produk"].str.contains(BUKAN_SAHAM), "produk"].unique())
    df = df[~df["produk"].str.contains(BUKAN_SAHAM)].copy()
    df["nav"] = df["nab"] / df["unit"]
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    df["kelompok"] = "GL"
    df["seri"] = np.where(df["fund"].notna(), "f" + df["fund"].astype("Int64").astype(str), df["kunci"])
    bagi = {int(x["_id"]) for x in db.rd_produk.find({"Dividend": True}, {"_id": 1})}
    pilih, s, dobel = al.pilih_seri(df, bagi)
    idx = pilih[~pilih["bh_pasardana"]].index
    R = al.tabel_return(s, idx)
    ek = R.abs() > LOMPAT_RD
    periksa = [(pilih.loc[x, "produk"], str(t), float(v)) for x in idx for t, v in R[x][ek[x]].items()]
    L, n = al.indeks(R.mask(ek))
    return L, n, {"seri": len(idx), "dobel": int(dobel), "bh_pasardana": int(pilih["bh_pasardana"].sum()), "bubar": int((pilih.loc[idx, "selesai"] < AKHIR).sum()),
                  "bukan_saham": len(keluar), "periksa": periksa}


def jalur2():
    Lg, ng, info = indeks_rd_global()
    baru, periksa_lokal = apf.indeks_baru(cetak=False)
    Ll, nl, idl = baru["SH"]
    a = max(Lg.index[0], Ll.index[0])
    b = min(Lg.index[-1], Ll.index[-1], AKHIR)
    rl = (Ll / Ll.shift(1) - 1).loc[a + 1:b]
    rg = (Lg / Lg.shift(1) - 1).loc[a + 1:b]
    R = pd.DataFrame({"idx": rl, "gl": rg})
    V = {nm: porto(R, w, biaya=0.0)[0] for nm, w in PORTO}
    Vi = V["100% IDX"]
    hasil = {nm: metrik(v, Vi, n=JENDELA_RD) for nm, v in V.items()}
    for h in hasil.values():
        h.pop("dekade")
    info.update({"lokal_seri": len(idl), "lokal_lompatan": sum(1 for x in periksa_lokal if x[0] == "SH"), "mulai": str(a), "akhir": str(b),
                 "produk_global_min": int(ng.loc[a + 1:b].min()), "produk_global_maks": int(ng.loc[a + 1:b].max()),
                 "produk_lokal_min": int(nl.loc[a + 1:b].min()), "korelasi": float(R["idx"].corr(R["gl"]))})
    return hasil, info


def p(x, n=1):
    return "-" if x is None else f"{x * 100:+.{n}f}%".replace(".", ",")


def cetak_tabel(h, label_j="10 th"):
    print(f"  {'Portofolio':<12} {'CAGR':>8} {'Turun':>8} {'Pulih':>12} {'MAR':>6} {'J' + label_j + ' buruk':>13} {'J' + label_j + ' baik':>12} {'% > IDX':>8}")
    for nm, m in h.items():
        pl = f"{m['pulih']} bln" if m["pulih"] is not None else f"belum ({m['sejak_puncak']})"
        menang = "-" if nm == "100% IDX" else f"{m['j_menang'] * 100:.0f}%"
        mar = f"{m['mar']:.2f}".replace(".", ",") if m["mar"] is not None else "-"
        print(f"  {nm:<12} {p(m['cagr']):>8} {p(m['dd']):>8} {pl:>12} {mar:>6} {p(m['j_buruk']):>13} {p(m['j_baik']):>12} {menang:>8}")


def utama():
    kk = cek_kurs()
    R, h = jalur1(DASAR)
    kr = kriteria(h)
    varian = {"pesimis gabungan": PESIMIS, "dividen JII 0%": {**DASAR, "div_jii": 0.0}, "dividen global 1,0%": {**DASAR, "div_gl": 0.010},
              "^IMUS pra-2008": {**DASAR, "pra2008": "us_djim"}}
    hv = {}
    for nm, asm in varian.items():
        _, hx = jalur1(asm)
        hv[nm] = {"kriteria": kriteria(hx), "ringkas": {k: {"cagr": v["cagr"], "dd": v["dd"], "mar": v["mar"], "j_buruk": v["j_buruk"]} for k, v in hx.items()}}
    k4 = all(v[0] for v in hv["pesimis gabungan"]["kriteria"].values())
    lolos = all(v[0] for v in kr.values()) and k4
    pc = pecah(R)
    xj = cek_xiji()
    h2, i2 = jalur2()
    korel = float(R["idx"].corr(R["gl"]))

    print(f"H35 jalur 1: return bulanan {AWAL + 1} s/d {AKHIR} ({len(R)} bulan), rupiah, dividen JII 2,5%, global 1,8% pra-2008, ^IMXL → ISDW.L Feb 2008")
    cetak_tabel(h)
    print(f"  Korelasi bulanan IDX vs global (rupiah): {korel:.2f}".replace(".", ","))
    print("\nPer dekade (CAGR rupiah, laporan):")
    for nm, _, _ in DEKADE:
        print(f"  {nm:<15} " + "  ".join(f"{k} {p(m['dekade'][nm])}" for k, m in h.items()))
    print("\nPemecahan return global (CAGR): USD lokal / efek kurs / rupiah  | IDX rupiah")
    for nm, x in pc.items():
        print(f"  {nm:<15} {p(x['usd'])} / {p(x['kurs'])} / {p(x['rupiah'])}  | {p(x['idx'])}")
    print("\nKriteria (50/50 vs 100% IDX):")
    print(f"  K1 jendela 10 th terburuk: {p(kr['K1'][1])} vs {p(kr['K1'][2])} → {'LULUS' if kr['K1'][0] else 'GAGAL'}")
    print(f"  K2 MAR: {kr['K2'][1]:.3f} vs {kr['K2'][2]:.3f} → {'LULUS' if kr['K2'][0] else 'GAGAL'}")
    print(f"  K3 CAGR: {p(kr['K3'][1])} vs {p(kr['K3'][2])} (batas {p(kr['K3'][2] - 0.02)}) → {'LULUS' if kr['K3'][0] else 'GAGAL'}")
    for nm, v in hv.items():
        kx = v["kriteria"]
        print(f"  {'K4 ' if nm == 'pesimis gabungan' else '   '}{nm}: K1 {p(kx['K1'][1])} vs {p(kx['K1'][2])} {'✔' if kx['K1'][0] else '✘'} | "
              f"K2 {kx['K2'][1]:.3f} vs {kx['K2'][2]:.3f} {'✔' if kx['K2'][0] else '✘'} | K3 {p(kx['K3'][1])} vs {p(kx['K3'][2])} {'✔' if kx['K3'][0] else '✘'}")
    print(f"  HASIL: {'LOLOS PASCA HASIL (wajib uji maju 1 Des 2026, amandemen a1)' if lolos else 'GAGAL'}")
    print(f"\nKurs: FRED vs kurs/USD akhir bulan di {kk['bulan']} bulan lengkap: median {kk['median'] * 100:.2f}%, p95 {kk['p95'] * 100:.2f}%, maks {kk['maks'] * 100:.2f}%, "
          f"> 1%: {kk['beda_1']}, > 3%: {kk['beda_3']}; bulan tidak lengkap {kk['bulan_buruk']}. 2024+ (kurs/USD): pencilan {kk['pasca2023_pencil']}, jeda > 7 hari {kk['pasca2023_jeda']}")
    print(f"XIJI {xj['mulai']}-{xj['akhir']}: TR {p(xj['xiji_tr'], 2)} vs JKII harga {p(xj['jkii_harga'], 2)} → selisih {p(xj['selisih'], 2)}/th (asumsi 2,5% − 0,5% = +2,0%); lonjakan harian > 15%: {xj['lonjakan_15']}")
    print(f"\nJalur 2 (deskriptif) {i2['mulai']} s/d {i2['akhir']}: RD saham syariah lokal ({i2['lokal_seri']} seri) vs RD Global Fund saham syariah ({i2['seri']} seri, {i2['bubar']} bubar, produk/bulan {i2['produk_global_min']}-{i2['produk_global_maks']}), jendela 5 th")
    cetak_tabel(h2, "5 th")
    print(f"  Korelasi {i2['korelasi']:.2f}; lompatan global dikeluarkan: {len(i2['periksa'])} {i2['periksa']}".replace(".", ",", 1))

    versi = {"dibuat": datetime.now(), "seri": {}}
    for nm in ["indeks/JKII", "indeks_luar/gl_djim_titans", "indeks_luar/gl_msci_world_islamic", "indeks_luar/us_djim", "makro/kurs_akhir_bulan", "kurs/USD", "etf/XIJI"]:
        versi["seri"][nm.replace("/", ":")] = str(dt.versi(nm))
    versi["sidik_return"] = sidik(R[["idx", "gl"]])
    versi["keterbatasan"] = ["Indeks, bukan produk; dividen sebelum 2008 dan dividen JII diasumsikan.", "FRED kurs akhir periode s/d Des 2023, 2024+ Yahoo kurs/USD.",
                            "Arah umum data sudah diketahui (pasca hasil).", "Jalur 2 bebas survivorship tapi hanya 2016+ dan campuran wilayah."]
    dt.simpan_hasil("h35_hasil", {"jalur1": h, "kriteria": kr, "varian": hv, "k4": k4, "lolos": lolos, "pecah": pc, "korelasi": korel, "kurs": kk, "xiji": xj,
                                  "jalur2": h2, "jalur2_info": i2, "asumsi": {"dasar": DASAR, "pesimis": PESIMIS, "biaya": [BIAYA_JII, BIAYA_GL_PRA, BIAYA_GL_ETF, BIAYA_REBAL]},
                                  "versi_data": versi})


if __name__ == "__main__":
    utama()
