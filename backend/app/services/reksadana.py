import re
from functools import lru_cache

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

HARI_TAHUN = 250
TOLERANSI_HARI = 14
NAV_LAMA_HARI = 7
BATAS_BEKU = 0.5
LABEL = {
    "pasar_uang": "Pasar uang", "pendapatan_tetap": "Pendapatan tetap", "campuran": "Campuran", "saham": "Saham", "indeks": "Indeks",
    "etf": "ETF", "global": "Global (luar negeri)", "terproteksi": "Terproteksi", "penyertaan_terbatas": "Penyertaan terbatas", "dire": "DIRE/DINFRA", "lain": "Lainnya",
}
URUT_KATEGORI = list(LABEL)
PROFIL = {
    "konservatif": {"label": "Konservatif", "ket": "Utamakan modal aman, penghasilan stabil", "porsi": {"pasar_uang": 50, "pendapatan_tetap": 40, "saham": 10}},
    "moderat": {"label": "Moderat", "ket": "Seimbang antara stabil dan tumbuh", "porsi": {"pasar_uang": 20, "pendapatan_tetap": 40, "saham": 40}},
    "agresif": {"label": "Agresif", "ket": "Kejar pertumbuhan, siap turun dalam", "porsi": {"pasar_uang": 10, "pendapatan_tetap": 20, "saham": 70}},
}
BATAS_MULUS = 0.35
BULAN_MULUS = 24
MIN_BULAN_MULUS = 12
BATAS_EFEK = 15
BATAS_AUM = 3
KATEGORI_MULUS = {"pendapatan_tetap", "campuran", "saham", "indeks", "global", "etf", "terproteksi"}
EFEK_NEGARA = re.compile(r"NEGARA|SBSN|\bPBS|\bSR ?0|\bSBR|\bST ?0|\bSPN|\bSDSN|\bSBSR|\bIFR|\bFR ?\d|DEPOSITO|GIRO|\bKAS\b|PEMERINTAH|INDOIS|\bINDON\b|PERUSAHAAN PENERBIT|GOV", re.I)
KATEGORI_EFEK = {"pendapatan_tetap", "campuran", "saham"}
MIN_AUM = {"IDR": 1e10, "USD": 6e5}
MIN_TAHUN_LENCANA = 3
BATAS_KONSISTEN = 60
BATAS_INFLASI = 0.8
MIN_BULAN_KONSISTEN = 12
MIN_PRODUK_MEDIAN = 3
LENCANA = {
    "konsisten": ("Konsisten", "Dalam {n} dari {total} periode 12 bulan ({pct:.0f}%), hasilnya di atas median RD sejenis. Lencana diberikan bila ≥ 60% dan data ≥ 3 tahun."),
    "inflasi": ("Kalahkan inflasi", "Hasil di atas inflasi pada {n} dari {total} tahun penuh. Lencana diberikan bila ≥ 80% dari minimal 3 tahun."),
    "tahan": ("Tahan banting", "Turun terburuk sepanjang riwayat {v}%, lebih ringan dari median RD sejenis ({m}%). Tidak diberikan bila NAV terlalu mulus."),
    "murah": ("Biaya murah", "Biaya per tahun {v}%, termasuk 25% termurah di kategorinya (batas {m}%)."),
}
PAJAK = {"rd": "Bukan objek pajak bagi pemegang unit", "sr": "Kupon kena pajak final 10%", "deposito": "Bunga kena pajak final 20%",
         "dividen": "Dividen kena pajak final 10% (bisa bebas kalau diinvestasikan ulang)", "saham": "Pajak jual 0,1% dari nilai jual"}


def versi():
    db = d.koneksi()
    i = db.rd_info.find_one({"_id": "ringkas"}) or {}
    pf = db.rd_platform_info.find_one({}, {"diambil": 1}, sort=[("diambil", -1)]) or {}
    return str(i.get("diperbarui")), db.rd_nav.estimated_document_count(), str((i.get("ojk") or {}).get("diimpor")), str(pf.get("diambil"))


@lru_cache(maxsize=2)
def _nav(kunci):
    df = pd.DataFrame(list(d.koneksi().rd_nav.find({}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    if df.empty:
        return pd.DataFrame()
    df["tgl"] = pd.to_datetime(df["tgl"])
    return df.pivot_table(index="tgl", columns="fund", values="nav").sort_index()


def nav():
    return _nav(versi())


def ret_sejak(s, hari):
    if s.empty:
        return None
    t = s.index[-1] - pd.Timedelta(days=hari)
    awal = s[s.index <= t]
    if awal.empty:
        if (s.index[0] - t).days > TOLERANSI_HARI:
            return None
        return (s.iloc[-1] / s.iloc[0] - 1) * 100
    return (s.iloc[-1] / awal.iloc[-1] - 1) * 100


def metrik(s):
    s = s.dropna()
    s = s[s > 0]
    if len(s) < 5:
        return {"titik": len(s)}
    s1 = s[s.index >= s.index[-1] - pd.Timedelta(days=365)]
    r = s1.pct_change().dropna()
    puncak = s1.cummax()
    awal_th = s[s.index < pd.Timestamp(f"{s.index[-1].year}-01-01")]
    mingguan = s1.resample("W").last().pct_change().dropna()
    return {
        "titik": len(s), "dari": s.index[0].strftime("%Y-%m-%d"), "sampai": s.index[-1].strftime("%Y-%m-%d"),
        "ret_1bln": ret_sejak(s, 30), "ret_3bln": ret_sejak(s, 91), "ret_6bln": ret_sejak(s, 182), "ret_1th": ret_sejak(s, 365),
        "ret_ytd": (s.iloc[-1] / awal_th.iloc[-1] - 1) * 100 if len(awal_th) else None,
        "vol": float(r.std() * np.sqrt(HARI_TAHUN) * 100) if len(r) > 20 else None,
        "dd": float((s1 / puncak - 1).min() * 100),
        "minggu_naik": float((mingguan > 0).mean() * 100) if len(mingguan) >= 8 else None,
        "nav_beku": bool(len(r) > 20 and (r.abs() < 1e-9).mean() > BATAS_BEKU),
    }


def bersih(x):
    if isinstance(x, dict):
        return {k: bersih(v) for k, v in x.items()}
    if isinstance(x, list):
        return [bersih(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 4)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    return x


def pisah_aset(aset):
    unik = {}
    for a in aset or []:
        unik.setdefault((a.get("jenis") == 0, (a.get("nama") or "").strip().lower()), a)
    urut = sorted(unik.values(), key=lambda a: -(a.get("bobot") or 0))
    return [a for a in urut if a.get("jenis") == 0], [a for a in urut if a.get("jenis") != 0]


def biaya_terakhir(det):
    b = [x for x in (det or {}).get("biaya") or [] if x.get("nilai") is not None and x["nilai"] > 0]
    return b[-1]["nilai"] * 100 if b else None


def jangka_panjang(oj, s):
    g = s if oj is None or oj.empty else pd.concat([oj[oj.index < s.index[0]] if len(s) else oj, s]).sort_index()
    g = g[g > 0]
    if len(g) < 2:
        return {"cagr_3": None, "cagr_5": None, "cagr_semua": None, "cagr_mulai": None, "tahun_data": None}
    tahun = (g.index[-1] - g.index[0]).days / 365.25
    semua = ((g.iloc[-1] / g.iloc[0]) ** (1 / tahun) - 1) * 100 if tahun >= 1 else None

    def cagr(th):
        if tahun < th - 0.05:
            return None
        x = g[g.index <= g.index[-1] - pd.DateOffset(years=th)]
        return None if x.empty else ((g.iloc[-1] / x.iloc[-1]) ** (1 / th) - 1) * 100
    return {"cagr_3": cagr(3), "cagr_5": cagr(5), "cagr_semua": semua, "cagr_mulai": g.index[0].strftime("%Y-%m-%d"), "tahun_data": round(tahun, 1)}


def gerak_bulanan(oj, s):
    g = s if oj is None or oj.empty else pd.concat([oj[oj.index < s.index[0]] if len(s) else oj, s]).sort_index()
    g = g[g > 0]
    if len(g) < 2:
        return None, None
    r = g.resample("ME").last().dropna().pct_change().dropna().iloc[-BULAN_MULUS:]
    if len(r) < MIN_BULAN_MULUS:
        return None, None
    return float(r.std() * 100), int((r < 0).sum())


def efek_terbesar(det):
    efek = [a for a in pisah_aset(det.get("aset"))[1] if a.get("bobot") and not EFEK_NEGARA.search(a.get("nama") or "")]
    return (efek[0]["nama"], float(efek[0]["bobot"])) if efek else (None, None)


def ubah_aum(det):
    a = sorted([(pd.Timestamp(x["tgl"]), float(x["nilai"])) for x in det.get("aum") or [] if x.get("tgl") and x.get("nilai")])
    if len(a) < 2:
        return None
    t, akhir = a[-1]
    lalu = [v for tt, v in a if t - pd.DateOffset(months=6) - pd.Timedelta(days=20) <= tt <= t - pd.DateOffset(months=6) + pd.Timedelta(days=20)]
    if not lalu or lalu[-1] <= 0:
        return None
    return {"awal": lalu[-1], "akhir": akhir, "kali": akhir / lalu[-1]}


def tandai(df):
    med = df[df["vol_bulan"].notna()].groupby(["kategori", "mata_uang"])["vol_bulan"].median()
    hasil = []
    for r in df.itertuples():
        w = []
        m = med.get((r.kategori, r.mata_uang))
        if r.kategori in KATEGORI_MULUS and pd.notna(r.vol_bulan) and m and r.vol_bulan < BATAS_MULUS * m and r.bulan_turun == 0:
            w.append({"kode": "mulus", "label": "NAV terlalu mulus",
                      "ket": f"Naik-turun bulanan {r.vol_bulan:.2f}% vs median kategori {m:.2f}%, tidak pernah turun dalam {BULAN_MULUS} bulan terakhir. "
                             "Bisa berarti isinya jarang diperdagangkan sehingga harganya tidak mengikuti pasar; risikonya baru terlihat saat ada masalah."})
        if r.kategori in KATEGORI_EFEK and pd.notna(r.efek_bobot) and r.efek_bobot > BATAS_EFEK:
            w.append({"kode": "terpusat", "label": f"1 efek {r.efek_bobot:.0f}%",
                      "ket": f"{r.efek_nama}: {r.efek_bobot:.1f}% dari dana (peringatan di atas {BATAS_EFEK}%; surat berharga negara dan deposito tidak dihitung)."})
        a = r.aum_6bln
        batas = MIN_AUM.get(r.mata_uang, MIN_AUM["IDR"])
        if isinstance(a, dict) and a["awal"] >= batas and a["akhir"] < batas:
            w.append({"kode": "aum", "label": "AUM hampir habis", "ket": "Dana kelolaan menyusut tajam dalam 6 bulan sampai di bawah batas wajar; produk bisa dibubarkan."})
        elif isinstance(a, dict) and a["awal"] >= batas and (a["kali"] >= BATAS_AUM or a["kali"] <= 1 / BATAS_AUM):
            naik = a["kali"] >= 1
            w.append({"kode": "aum", "label": f"AUM {'naik' if naik else 'turun'} {a['kali'] if naik else 1 / a['kali']:.1f}×",
                      "ket": f"Dana kelolaan {'naik' if naik else 'turun'} {a['kali'] if naik else 1 / a['kali']:.1f}× dalam 6 bulan. "
                             + ("Dana masuk deras bisa terbalik jadi pencairan besar, dan efek yang sulit dijual terpaksa dilepas." if naik else "Banyak investor keluar; cari tahu sebabnya sebelum masuk.")})
        hasil.append(w)
    return hasil


def koma(v, d):
    return f"{v:.{d}f}".replace(".", ",")


def cagr_bulanan(m, th):
    if len(m) <= 12 * th:
        return None
    return float(((m.iloc[-1] / m.iloc[-1 - 12 * th]) ** (1 / th) - 1) * 100)


def riwayat_bulanan(ids, usd=()):
    from backend.app.services import rd_yakin
    b = rd_yakin.bulanan()
    kurs = dt.baca("pasar")["usdidr"].dropna().resample("ME").last() if usd else None
    inf = rd_yakin.inflasi()
    des = inf[inf.index.month == 12]
    des.index = des.index.year
    hasil = {}
    for f in ids:
        if f not in b.columns:
            continue
        m = b[f].dropna()
        if len(m) < 13:
            continue
        th = rd_yakin.ret_tahun(m).dropna()
        if m.index[-1].month < 12:
            th = th[th.index < m.index[-1].year]
        banding = [x for x in th.index if x in des.index]
        hasil[f] = {"turun_terburuk": float((m / m.cummax() - 1).min() * 100),
                    "tahun_terburuk": {"tahun": int(th.idxmin()), "ret": float(th.min())} if len(th) else None,
                    "inflasi_menang": int(sum(th[x] > des[x] for x in banding)), "inflasi_tahun": len(banding),
                    "r12": (m / m.shift(12) - 1).dropna(),
                    "untung_12bln": float(((m / m.shift(12) - 1).dropna() > 0).mean() * 100) if len(m) > 13 else None}
        mr = (m * kurs.reindex(m.index)).dropna() if f in usd and kurs is not None else m
        hasil[f].update({"cagr_3_rp": cagr_bulanan(mr, 3), "cagr_5_rp": cagr_bulanan(mr, 5), "turun_terburuk_rp": float((mr / mr.cummax() - 1).min() * 100) if len(mr) else None})
    return hasil


def lencana(df):
    riwayat = riwayat_bulanan(df["id"].tolist(), set(df.loc[df["mata_uang"] == "USD", "id"]))
    for kolom in ("turun_terburuk", "tahun_terburuk", "inflasi_menang", "inflasi_tahun", "untung_12bln", "cagr_3_rp", "cagr_5_rp", "turun_terburuk_rp", "konsisten_n", "konsisten_total", "urut", "jumlah_kategori"):
        df[kolom] = None
    df["lencana"] = [[] for _ in range(len(df))]
    for i, r in df.iterrows():
        x = riwayat.get(r["id"])
        if x:
            for k in ("turun_terburuk", "tahun_terburuk", "inflasi_menang", "inflasi_tahun", "untung_12bln", "cagr_3_rp", "cagr_5_rp", "turun_terburuk_rp"):
                df.at[i, k] = x[k]
    for i, r in df.iterrows():
        tambahan = []
        if (r["tahun_data"] or 0) < MIN_TAHUN_LENCANA:
            th = f"{r['tahun_data'] or 0:.1f}".replace(".", ",")
            tambahan.append({"kode": "pendek", "label": "Data pendek",
                             "ket": f"Riwayat baru {th} tahun. Butuh minimal {MIN_TAHUN_LENCANA} tahun untuk dinilai konsisten atau tahan banting."})
        if pd.isna(r["biaya"]) and r["kategori"] != "etf":
            tambahan.append({"kode": "biaya", "label": "Biaya tidak diketahui", "ket": "Biaya tahunan tidak tercantum di data; cek prospektus atau fund fact sheet sebelum membeli."})
        df.at[i, "peringatan"] = list(r["peringatan"]) + tambahan
    for _, g in df.groupby(["kategori", "mata_uang"]):
        r12 = pd.DataFrame({r["id"]: riwayat[r["id"]]["r12"] for _, r in g.iterrows() if r["id"] in riwayat})
        if not r12.empty:
            cukup = r12.notna().sum(axis=1) >= MIN_PRODUK_MEDIAN
            med = r12[cukup].median(axis=1)
            for i, r in g.iterrows():
                if r["id"] not in r12.columns:
                    continue
                s = r12.loc[cukup, r["id"]].dropna()
                if len(s) >= MIN_BULAN_KONSISTEN:
                    df.at[i, "konsisten_n"] = int((s > med.reindex(s.index)).sum())
                    df.at[i, "konsisten_total"] = int(len(s))
        lama = g[g["tahun_data"].fillna(0) >= MIN_TAHUN_LENCANA]
        turun_lama = pd.to_numeric(df.loc[lama.index, "turun_terburuk"], errors="coerce").dropna()
        med_turun = turun_lama.median() if len(turun_lama) >= MIN_PRODUK_MEDIAN else None
        biaya = g["biaya"].dropna()
        batas_biaya = biaya.quantile(0.25) if len(biaya) >= 4 else None
        for i, r in g.iterrows():
            w = []
            panjang = (r["tahun_data"] or 0) >= MIN_TAHUN_LENCANA
            mulus = any(p["kode"] == "mulus" for p in df.at[i, "peringatan"])
            kn, kt = df.at[i, "konsisten_n"], df.at[i, "konsisten_total"]
            if panjang and kt and kn / kt * 100 >= BATAS_KONSISTEN:
                w.append({"kode": "konsisten", "label": LENCANA["konsisten"][0], "ket": LENCANA["konsisten"][1].format(n=kn, total=kt, pct=kn / kt * 100)})
            im, it = df.at[i, "inflasi_menang"], df.at[i, "inflasi_tahun"]
            if it and it >= MIN_TAHUN_LENCANA and im / it >= BATAS_INFLASI:
                w.append({"kode": "inflasi", "label": LENCANA["inflasi"][0], "ket": LENCANA["inflasi"][1].format(n=im, total=it)})
            tb = df.at[i, "turun_terburuk"]
            if panjang and not mulus and tb is not None and med_turun is not None and tb > med_turun:
                w.append({"kode": "tahan", "label": LENCANA["tahan"][0], "ket": LENCANA["tahan"][1].format(v=koma(tb, 1), m=koma(med_turun, 1))})
            if batas_biaya is not None and pd.notna(r["biaya"]) and r["biaya"] <= batas_biaya:
                w.append({"kode": "murah", "label": LENCANA["murah"][0], "ket": LENCANA["murah"][1].format(v=koma(r["biaya"], 2), m=koma(batas_biaya, 2))})
            df.at[i, "lencana"] = w
    df["jumlah_lencana"] = df["lencana"].map(len)
    df["jumlah_peringatan"] = df["peringatan"].map(lambda w: sum(1 for x in w if x["kode"] != "biaya"))
    for _, g in df.groupby(["kategori", "mata_uang"]):
        urut = g.assign(_c=g["cagr_3"].fillna(-1e9)).sort_values(["jumlah_lencana", "jumlah_peringatan", "_c"], ascending=[False, True, False])
        for n, i in enumerate(urut.index, 1):
            df.at[i, "urut"] = n
            df.at[i, "jumlah_kategori"] = len(g)


@lru_cache(maxsize=2)
def _daftar(kunci):
    db = d.koneksi()
    produk = list(db.rd_produk.find({"tidak_aktif": {"$ne": True}}))
    detail = {x["_id"]: x for x in db.rd_detail.find({}, {"biaya": 1, "risiko": 1, "pembanding": 1, "tgl_terbit": 1, "min_beli": 1, "aset": 1, "aum": 1})}
    platform = {}
    for x in db.rd_platform.find({}, {"fund": 1, "platform": 1, "url": 1}).sort("platform", 1):
        platform.setdefault(x["fund"], []).append({"kode": x["platform"], "url": x["url"]})
    n = nav()
    oj = pd.DataFrame(list(db.rd_ojk.find({"fund": {"$ne": None}}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    oj = {f: g.assign(tgl=pd.to_datetime(g["tgl"])).set_index("tgl")["nav"].sort_index() for f, g in oj.groupby("fund")} if not oj.empty else {}
    baris = []
    for p in produk:
        s = n[p["_id"]] if p["_id"] in n.columns else pd.Series(dtype=float)
        m = metrik(s)
        m.update(jangka_panjang(oj.get(p["_id"]), s.dropna()))
        det = detail.get(p["_id"], {})
        vol_bulan, bulan_turun = gerak_bulanan(oj.get(p["_id"]), s.dropna())
        efek_nama, efek_bobot = efek_terbesar(det)
        m.update({"vol_bulan": vol_bulan, "bulan_turun": bulan_turun, "efek_nama": efek_nama, "efek_bobot": efek_bobot, "aum_6bln": ubah_aum(det)})
        baris.append({
            "id": p["_id"], "nama": p["nama"], "mi": p.get("InvestmentManagerName"), "kategori": p["kategori"], "kategori_label": LABEL.get(p["kategori"], p["kategori"]),
            "mata_uang": p["mata_uang"], "nav": p.get("NetAssetValue"), "nav_tgl": p["nav_tgl"].strftime("%Y-%m-%d") if p.get("nav_tgl") else None,
            "aum": p.get("AssetUnderManagement"), "biaya": biaya_terakhir(det), "biaya_mi": p.get("InvestmentManagerFee"), "min_beli": p.get("MinimumSubscription"),
            "risiko": det.get("risiko") or p.get("RiskClassificationValue"), "pembanding": det.get("pembanding"),
            "terbit": det["tgl_terbit"].strftime("%Y-%m-%d") if det.get("tgl_terbit") else None, "etf": bool(p.get("ExchangeTradedFund")),
            "sumber_ret_1th": (p.get("YearlyReturn") * 100) if p.get("YearlyReturn") is not None else None,
            "platform": platform.get(p["_id"], []), **m,
        })
    df = pd.DataFrame(baris)
    if df.empty:
        return []
    tgl_nav = pd.to_datetime(df["nav_tgl"])
    df["peringatan"] = tandai(df)
    df["nav_lama"] = (tgl_nav < tgl_nav.max() - pd.Timedelta(days=NAV_LAMA_HARI)).fillna(True)
    lencana(df)
    return bersih(df.replace({np.nan: None}).to_dict("records"))


def daftar():
    data = _daftar(versi())
    info = d.koneksi().rd_info.find_one({"_id": "ringkas"}, {"_id": 0})
    return {"data": data, "info": bersih(info), "label": LABEL, "lencana": {k: {"label": v[0]} for k, v in LENCANA.items()}}


def ringkas_kategori(data=None):
    data = data or _daftar(versi())
    df = pd.DataFrame(data)
    if df.empty:
        return []
    hasil = []
    for k in URUT_KATEGORI:
        if k == "etf":
            continue
        g = df[df["kategori"] == k]
        if g.empty:
            continue
        top = (g[g["mata_uang"] == "IDR"] if (g["mata_uang"] == "IDR").any() else g).sort_values("urut").head(3)
        hasil.append({"kategori": k, "label": LABEL[k], "jumlah": len(g), "ret_1th": g["ret_1th"].median(), "ret_1th_q3": g["ret_1th"].quantile(0.75),
                      "dd": g["dd"].median(), "biaya": g["biaya"].median(), "aum": g["aum"].sum(), "vol": g["vol"].median(),
                      "cagr_3": g.loc[g["mata_uang"] == "IDR", "cagr_3"].median(), "turun_terburuk": pd.to_numeric(g.loc[g["mata_uang"] == "IDR", "turun_terburuk"], errors="coerce").median(),
                      "untung_12bln": pd.to_numeric(g.loc[g["mata_uang"] == "IDR", "untung_12bln"], errors="coerce").median(),
                      "tahun_terburuk": pd.Series([x["ret"] for x in g.loc[g["mata_uang"] == "IDR", "tahun_terburuk"] if isinstance(x, dict)], dtype=float).median(),
                      "cagr_3_ada": int(g.loc[g["mata_uang"] == "IDR", "cagr_3"].notna().sum()), "cagr_3_minus": int((g.loc[g["mata_uang"] == "IDR", "cagr_3"] < 0).sum()),
                      "di_platform": int(g["platform"].map(bool).sum()),
                      "terbaik": top[["id", "nama", "ret_1th", "cagr_3", "jumlah_lencana"]].to_dict("records")})
    return bersih(hasil)


def riwayat_aum(oj, pasardana, mata_uang):
    a = pd.Series(dtype=float)
    if not oj.empty and "nab" in oj:
        a = oj.assign(tgl=pd.to_datetime(oj["tgl"])).set_index("tgl")["nab"].dropna().sort_index()
        if mata_uang == "USD" and len(a):
            try:
                from backend.db import data as dt
                k = dt.baca("pasar")["usdidr"].dropna().sort_index()
                a = a / k.reindex(a.index, method="ffill").to_numpy()
            except Exception:
                a = pd.Series(dtype=float)
    pd_ = pd.Series({pd.Timestamp(x["tgl"]) + pd.offsets.MonthEnd(0): float(x["nilai"]) for x in pasardana if x.get("tgl") and x.get("nilai")}).sort_index()
    if len(pd_):
        a = pd.concat([a[a.index < pd_.index[0]] if len(a) else a, pd_]) if len(a) else pd_
    a = a[a > 0].dropna()
    a = a[~a.index.duplicated(keep="last")].sort_index()
    return {"tgl": [t.strftime("%Y-%m-%d") for t in a.index], "nilai": [round(float(v), 2) for v in a]}


def mulai():
    from backend.app.services import rd_yakin
    inf = rd_yakin.inflasi()
    ab = dt.baca("makro/bunga_antarbank")
    dep = float(ab["nilai"].dropna().iloc[-1]) * (1 - rd_yakin.PAJAK_DEPOSITO) if ab is not None else None
    return bersih({"kategori": ringkas_kategori(), "inflasi": {"nilai": float(inf.iloc[-1]), "tgl": inf.index[-1].strftime("%Y-%m-%d")} if len(inf) else None,
                   "deposito": dep})


def platform_info():
    from backend.ingest.rd_platform import PLATFORM
    db = d.koneksi()
    info = {x["_id"]: x for x in db.rd_platform_info.find()}
    hasil = []
    for k, p in PLATFORM.items():
        x = info.get(k) or {}
        hasil.append({"kode": k, "nama": p["nama"], "situs": p["situs"], "cocok": x.get("cocok"), "diambil": x.get("diambil"),
                      "izin_ojk": x.get("izin_ojk") or [], "sumber": "halaman publik (filter Syariah)" if p["cara"] == "browser" else "sitemap publik"})
    pto = list(db.rd_pto.find({}, {"_id": 0}).sort("no", 1))
    return bersih({"platform": hasil, "pto": pto, "total_rd": len(db.rd_platform.distinct("fund")),
                   "pto_sumber": "https://reksadana.ojk.go.id/Public/PTOPublic.aspx"})


def kurs_usd():
    try:
        from backend.db import data as dt
        return float(dt.baca("pasar")["usdidr"].dropna().iloc[-1])
    except Exception:
        return None


def detail(fid):
    db = d.koneksi()
    p = db.rd_produk.find_one({"_id": fid})
    if not p:
        return None
    det = db.rd_detail.find_one({"_id": fid}) or {}
    data = _daftar(versi())
    baris = next((x for x in data if x["id"] == fid), {})
    n = nav()
    s = n[fid].dropna() if fid in n.columns else pd.Series(dtype=float)
    bm = pd.DataFrame(det.get("pembanding_deret") or [])
    oj = pd.DataFrame(list(db.rd_ojk.find({"fund": fid}, {"_id": 0, "tgl": 1, "nav": 1, "nab": 1})))
    grafik_aum = riwayat_aum(oj, det.get("aum") or [], p.get("mata_uang"))
    panjang = None
    if not oj.empty:
        oj = oj.assign(tgl=pd.to_datetime(oj["tgl"])).set_index("tgl")["nav"].sort_index()
        awal = oj[oj.index < s.index[0]] if len(s) else oj
        s = pd.concat([awal, s]).sort_index()
        bulanan = s.resample("ME").last().dropna()
        tahun = (s.index[-1] - s.index[0]).days / 365.25
        def cagr(th):
            if tahun < th - 0.05:
                return None
            x = s[s.index <= s.index[-1] - pd.DateOffset(years=th)]
            return None if x.empty else ((s.iloc[-1] / x.iloc[-1]) ** (1 / th) - 1) * 100
        th_ret = bulanan.groupby(bulanan.index.year).last()
        per_tahun = (th_ret / th_ret.shift(1) - 1).dropna() * 100
        panjang = {"mulai": s.index[0].strftime("%Y-%m-%d"), "tahun": round(tahun, 1), "cagr_3": cagr(3), "cagr_5": cagr(5),
                   "cagr_semua": ((s.iloc[-1] / s.iloc[0]) ** (1 / tahun) - 1) * 100 if tahun >= 1 else None,
                   "dd": float((bulanan / bulanan.cummax() - 1).min() * 100),
                   "tahun_naik": int((per_tahun > 0).sum()), "tahun_dihitung": int(len(per_tahun)),
                   "per_tahun": [{"tahun": int(t), "ret": float(v)} for t, v in per_tahun.items()]}
    grafik = {"tgl": [t.strftime("%Y-%m-%d") for t in s.index], "nav": s.round(4).tolist(), "aum": grafik_aum}
    if not bm.empty and len(s):
        bm["tgl"] = pd.to_datetime(bm["tgl"])
        b = bm.set_index("tgl")["nilai"].reindex(s.index, method="ffill")
        if b.notna().any() and b.dropna().max() < 30:
            r = b.ffill() * (100 if b.dropna().max() < 1 else 1)
            hari = pd.Series(s.index, index=s.index).diff().dt.days.fillna(0)
            faktor = (1 + r.shift(1).fillna(r) / 100 * hari / 365).where(r.notna())
            b = faktor.cumprod()
        if b.notna().any():
            dasar = b.dropna().iloc[0]
            mulai = s[b.notna()].iloc[0]
            grafik["pembanding"] = [None if pd.isna(v) else round(v / dasar * mulai, 4) for v in b]
    sekategori = [x for x in data if x["kategori"] == p["kategori"] and x["mata_uang"] == p["mata_uang"]]
    med = lambda k: float(np.nanmedian([x[k] for x in sekategori if x.get(k) is not None])) if any(x.get(k) is not None for x in sekategori) else None
    aum_d = [x for x in det.get("aum") or [] if x.get("nilai")]
    aum_ubah = (aum_d[-1]["nilai"] / aum_d[-2]["nilai"] - 1) * 100 if len(aum_d) >= 2 else None
    sekelola = [x for x in data if x.get("mi") == baris.get("mi") and x.get("aum")]
    kurs = kurs_usd() if any(x["mata_uang"] == "USD" for x in sekelola) else None
    aum_mi = sum(x["aum"] * ((kurs or 0) if x["mata_uang"] == "USD" else 1) for x in sekelola)
    tingkat = baris.get("risiko")
    dokumen = [{**dk, "jenis_label": "Prospektus" if dk.get("jenis") == 0 else "Fund fact sheet", "url": f"https://pasardana.id/fund/{fid}"}
               for dk in sorted(det.get("dokumen") or [], key=lambda z: pd.Timestamp(z.get("tgl") or 0), reverse=True)]
    hasil = {
        **baris, "deskripsi": det.get("deskripsi"), "kustodian": p.get("CustodianBankName"), "isin": p.get("IsinCode"),
        "min_beli_lagi": det.get("min_beli_lagi"), "min_jual": det.get("min_jual"), "aset": pisah_aset(det.get("aset"))[1], "alokasi_aset": pisah_aset(det.get("aset"))[0], "catatan_risiko": det.get("catatan_risiko"),
        "aum_deret": det.get("aum") or [], "biaya_deret": det.get("biaya") or [], "dokumen": dokumen, "url_sumber": f"https://pasardana.id/fund/{fid}",
        "aum_tgl": (p.get("AumPublishedDate") or "")[:10] or None, "aum_ubah": aum_ubah,
        "aum_mi": aum_mi or None, "aum_mi_produk": len(sekelola), "aum_mi_kurs": kurs,
        "risiko_label": None if tingkat is None else ("Rendah" if tingkat <= 3 else "Sedang" if tingkat <= 6 else "Tinggi"), "dividen": det.get("dividen") or [],
        "kinerja_sumber": det.get("kinerja_1th"), "grafik": grafik, "panjang": panjang, "detail_diambil": det.get("diambil"),
        "median_kategori": {k: med(k) for k in ("ret_1bln", "ret_3bln", "ret_6bln", "ret_ytd", "ret_1th", "dd", "vol", "biaya")},
        "jumlah_kategori_semua": len(sekategori),
    }
    etf = None
    m = db.rd_etf.find_one({"_id": fid}, {"kode": 1})
    if m and m.get("kode"):
        try:
            from backend.app.services.etf import metrik_bursa
            etf = metrik_bursa(m["kode"])
        except Exception:
            etf = None
    from backend.app.services import kesimpulan, rd_yakin
    hasil["keyakinan"] = rd_yakin.keyakinan(fid, s, p["kategori"], p["mata_uang"])
    hasil["kesimpulan"] = kesimpulan.reksadana(hasil, sekategori, etf)
    return bersih(hasil)


JANGKA = {
    "pendek": {"label": "Kurang dari 1 tahun", "metrik": "cagr_3", "sukuk": (0, 1)},
    "menengah": {"label": "1–3 tahun", "metrik": "cagr_3", "sukuk": (1, 3)},
    "panjang": {"label": "5 tahun atau lebih", "metrik": "cagr_5", "sukuk": (5, 10)},
}
RACIKAN = {
    ("pendek", "rendah"): {"pasar_uang": 100},
    ("pendek", "sedang"): {"pasar_uang": 70, "pendapatan_tetap": 30},
    ("pendek", "tinggi"): {"pasar_uang": 50, "pendapatan_tetap": 50},
    ("menengah", "rendah"): {"sukuk": 50, "pendapatan_tetap": 30, "pasar_uang": 20},
    ("menengah", "sedang"): {"sukuk": 40, "pendapatan_tetap": 40, "saham_global": 20},
    ("menengah", "tinggi"): {"sukuk": 25, "pendapatan_tetap": 25, "saham_global": 40, "saham": 10},
    ("panjang", "rendah"): {"sukuk": 60, "pendapatan_tetap": 40},
    ("panjang", "sedang"): {"sukuk": 30, "pendapatan_tetap": 30, "saham_global": 30, "saham": 10},
    ("panjang", "tinggi"): {"sukuk": 10, "pendapatan_tetap": 10, "saham_global": 70, "saham": 10},
}
JENIS_SUKUK_NEGARA = {"SR", "PBS", "SPNS"}
PAJAK_KUPON = 0.1
JUMLAH_TERATAS = 5
NAMA_INSTRUMEN = {"pasar_uang": "Reksa dana pasar uang", "pendapatan_tetap": "Reksa dana pendapatan tetap", "saham": "Reksa dana saham syariah Indonesia",
                  "saham_global": "Reksa dana saham syariah global (dolar AS)",
                  "sukuk": "Sukuk negara (dipegang sampai jatuh tempo)"}


def racikan(jangka="menengah", profil="rendah"):
    jangka = jangka if jangka in JANGKA else "menengah"
    profil = profil if profil in ("rendah", "sedang", "tinggi") else "rendah"
    j = JANGKA[jangka]
    semua = pd.DataFrame(_daftar(versi()))
    df = semua[semua["mata_uang"] == "IDR"]
    bagian = []
    for kunci, porsi in RACIKAN[(jangka, profil)].items():
        if kunci == "sukuk":
            s = pd.DataFrame(sukuk()["data"])
            a, b = j["sukuk"]
            s = s[s["jenis"].isin(JENIS_SUKUK_NEGARA) & s["ytm"].notna() & s["sisa_tahun"].between(a, b)].copy()
            s["bersih"] = (s["ytm"] - s["kupon"].fillna(0) * PAJAK_KUPON) * 100
            est = float(s["bersih"].median()) if len(s) else None
            pilihan = s.sort_values("bersih", ascending=False).head(4)
            bagian.append({"kode": kunci, "nama": NAMA_INSTRUMEN[kunci], "persen": porsi, "atas": est, "biasa": est, "turun": None,
                           "dasar": f"hasil kalau ditahan (YTM) {len(s)} seri sukuk negara bersisa {a}–{b} tahun, dikurangi pajak kupon 10%",
                           "sukuk": [{"kode": r.kode, "jenis": r.jenis, "bersih": r.bersih, "ytm": r.ytm * 100, "kupon": (r.kupon or 0) * 100,
                                      "jatuh_tempo": r.jatuh_tempo, "sisa_tahun": r.sisa_tahun, "harga": r.harga} for r in pilihan.itertuples()]})
            continue
        if kunci == "saham_global":
            g = semua[(semua["mata_uang"] == "USD") & semua["kategori"].isin(["global", "indeks"])].copy()
            g["cagr_3"], g["cagr_5"], g["turun_terburuk"] = g["cagr_3_rp"], g["cagr_5_rp"], g["turun_terburuk_rp"]
        else:
            g = df[df["kategori"].isin(["saham", "indeks"]) if kunci == "saham" else df["kategori"] == kunci]
        metrik = j["metrik"] if g[j["metrik"]].notna().sum() >= 5 else "cagr_3"
        urut = g.assign(_c=g["cagr_3"].fillna(-1e9)).sort_values(["jumlah_lencana", "jumlah_peringatan", "_c"], ascending=[False, True, False])
        dasar_atas = urut[urut[metrik].notna()].head(JUMLAH_TERATAS)
        di_platform = urut[urut["platform"].map(bool)]
        pilihan = (di_platform if len(di_platform) >= 3 else urut).head(3)
        bagian.append({"kode": kunci, "nama": NAMA_INSTRUMEN[kunci], "persen": porsi, "atas": float(dasar_atas[metrik].median()) if len(dasar_atas) else None,
                       "biasa": float(g[metrik].median()) if g[metrik].notna().any() else None,
                       "turun": float(pd.to_numeric(g["turun_terburuk"], errors="coerce").median()),
                       "metrik": metrik, "dasar": f"rata-rata per tahun {'5' if metrik == 'cagr_5' else '3'} tahun terakhir{' dalam rupiah (termasuk kurs)' if kunci == 'saham_global' else ''}: {JUMLAH_TERATAS} produk teratas (urutan lencana) vs nilai tengah {int(g[metrik].notna().sum())} produk",
                       "rugi": int((g[metrik] < 0).sum()), "dihitung": int(g[metrik].notna().sum()),
                       "terbaik": {"id": int(g.loc[g[metrik].idxmax(), "id"]), "nama": g.loc[g[metrik].idxmax(), "nama"], "nilai": float(g[metrik].max())} if g[metrik].notna().any() else None,
                       "produk": pilihan["id"].tolist()})
    def tertimbang(k):
        ada = [x for x in bagian if x[k] is not None]
        bobot = sum(x["persen"] for x in ada)
        return sum(x[k] * x["persen"] for x in ada) / bobot if bobot else None
    turun = sum((x["turun"] or 0) * x["persen"] / 100 for x in bagian)
    m = mulai()
    return bersih({"jangka": jangka, "profil": profil, "jangka_label": j["label"], "bagian": bagian, "atas": tertimbang("atas"), "biasa": tertimbang("biasa"),
                   "turun": turun, "inflasi": m.get("inflasi"), "deposito": m.get("deposito")})


def sukuk():
    db = d.koneksi()
    data = list(db.rd_sukuk.find({}))
    for x in data:
        x["kode"] = x.pop("_id")
    df = pd.DataFrame(data)
    ringkas = []
    if not df.empty:
        for j, g in df.groupby("jenis"):
            ringkas.append({"jenis": j, "jumlah": len(g), "kupon_median": g["kupon"].median() * 100 if g["kupon"].notna().any() else None,
                            "ytm_median": g["ytm"].median() * 100 if g["ytm"].notna().any() else None})
    return bersih({"data": data, "ringkas": ringkas})


def sukuk_riwayat(kode):
    db = d.koneksi()
    x = db.rd_sukuk.find_one({"_id": kode})
    if x is None:
        return None
    r = list(db.rd_sukuk_harga.find({"kode": kode}).sort("tgl", 1))
    return bersih({"kode": kode, "nama": x.get("nama"), "tgl": [z["tgl"].strftime("%Y-%m-%d") for z in r], "harga": [z["harga"] for z in r],
                   "ytm": [None if z.get("ytm") is None else z["ytm"] * 100 for z in r]})


def tren52_cagr():
    r = d.koneksi().backtest_ringkasan.find_one({"_id": "h11a_2020"}) or d.koneksi().backtest_ringkasan.find_one({"versi": "h11a_2020"})
    return (r or {}).get("cagr")


def banding():
    data = _daftar(versi())
    df = pd.DataFrame(data)
    opsi = []

    def rd(k, nama, risiko, catatan):
        g = df[(df["kategori"] == k) & (df["mata_uang"] == "IDR")] if not df.empty else df
        if g is None or g.empty or g["ret_1th"].notna().sum() == 0:
            return
        opsi.append({"nama": nama, "jenis": "Reksa dana", "hasil": g["ret_1th"].median(), "hasil_atas": g["ret_1th"].quantile(0.75),
                     "dd": g["dd"].median(), "risiko": risiko, "pajak": PAJAK["rd"], "catatan": catatan, "dasar": f"median 1 tahun terakhir, {len(g)} produk"})

    rd("pasar_uang", "RD pasar uang syariah", 1, "Pengganti tabungan/deposito, bisa dicairkan kapan saja (T+1/T+2)")
    rd("pendapatan_tetap", "RD pendapatan tetap syariah", 2, "Isi utamanya sukuk; naik-turun kecil saat suku bunga berubah")
    rd("campuran", "RD campuran syariah", 3, "Campuran saham dan sukuk")
    rd("saham", "RD saham syariah", 4, "Isi saham syariah; bisa turun dalam")
    rd("indeks", "RD indeks syariah", 4, "Mengikuti indeks (mis. JII/ISSI), biaya biasanya lebih rendah")
    sk = sukuk()["data"]
    s = pd.DataFrame(sk)
    if not s.empty:
        sr = s[s["jenis"] == "SR"].sort_values("terbit")
        if len(sr):
            x = sr.iloc[-1]
            opsi.append({"nama": f"Sukuk ritel {x['kode']}", "jenis": "SBN ritel", "hasil": x["kupon"] * 100, "hasil_atas": None, "dd": None, "risiko": 1,
                         "pajak": PAJAK["sr"], "catatan": "Kupon tetap dijamin negara; seri terbaru yang tercatat (bisa ditawarkan ulang dengan kupon berbeda)",
                         "dasar": "kupon seri terbaru, sebelum pajak"})
        pbs = s[(s["jenis"] == "PBS") & s["ytm"].notna() & (s["sisa_tahun"] <= 5)]
        if len(pbs):
            opsi.append({"nama": "Sukuk negara PBS (≤ 5 th)", "jenis": "SBN pasar sekunder", "hasil": pbs["ytm"].median() * 100, "hasil_atas": None, "dd": None,
                         "risiko": 2, "pajak": PAJAK["sr"], "catatan": "Dibeli di pasar sekunder lewat broker/bank; harga bisa naik-turun sebelum jatuh tempo",
                         "dasar": f"median yield to maturity {len(pbs)} seri"})
        kor = s[(s["jenis"] == "Korporasi") & s["ytm"].notna() & (s["ytm"] > 0) & (s["ytm"] < 0.25)]
        if len(kor):
            opsi.append({"nama": "Sukuk korporasi", "jenis": "Sukuk perusahaan", "hasil": kor["ytm"].median() * 100, "hasil_atas": kor["ytm"].quantile(0.75) * 100,
                         "dd": None, "risiko": 3, "pajak": PAJAK["sr"], "catatan": "Risiko gagal bayar penerbit; cek rating; likuiditas rendah",
                         "dasar": f"median yield to maturity {len(kor)} seri yang ada harga"})
    try:
        from backend.app.services import dividen as dvn
        dd_ = [x["yield"] for x in dvn.daftar()["data"] if x.get("dps12", 0) > 0 and x.get("beruntun", 0) >= 3]
        if dd_:
            opsi.append({"nama": "Dividen saham syariah", "jenis": "Saham", "hasil": float(np.median(dd_)), "hasil_atas": None, "dd": None, "risiko": 4,
                         "pajak": PAJAK["dividen"], "catatan": "Hanya penghasilan dividen; harga saham bisa turun (lihat Pemburu Dividen)",
                         "dasar": f"median yield 12 bulan, {len(dd_)} saham yang bayar ≥ 3 th berturut"})
    except Exception:
        pass
    c = tren52_cagr()
    if c is not None:
        opsi.append({"nama": "Follow Tren (backtest)", "jenis": "Strategi saham", "hasil": c, "hasil_atas": None, "dd": None, "risiko": 5,
                     "pajak": PAJAK["saham"], "catatan": "Hasil backtest 2020-2026, bukan hasil nyata; sedang diuji paper",
                     "dasar": "CAGR backtest cara paper"})
    return bersih({"data": opsi})


def alokasi(profil, modal):
    p = PROFIL.get(profil) or PROFIL["moderat"]
    data = _daftar(versi())
    df = pd.DataFrame(data)
    hasil = []
    for k, persen in p["porsi"].items():
        g = df[(df["kategori"].isin(["saham", "indeks"]) if k == "saham" else df["kategori"] == k) & (df["mata_uang"] == "IDR")] if not df.empty else df
        top = g.sort_values("urut").head(3) if not g.empty else g
        hasil.append({"kategori": k, "label": LABEL[k] + (" & indeks" if k == "saham" else ""), "persen": persen, "nilai": modal * persen / 100,
                      "ret_1th": g["ret_1th"].median() if not g.empty else None, "dd": g["dd"].median() if not g.empty else None,
                      "pilihan": top[["id", "nama", "mi", "lencana", "peringatan", "ret_1th", "cagr_3", "dd", "turun_terburuk", "biaya", "min_beli"]].to_dict("records") if not top.empty else []})
    ret = sum((x["ret_1th"] or 0) * x["persen"] / 100 for x in hasil)
    dd = sum((x["dd"] or 0) * x["persen"] / 100 for x in hasil)
    return bersih({"profil": profil, "label": p["label"], "ket": p["ket"], "porsi": hasil, "ret_1th": ret, "dd": dd, "modal": modal,
                   "semua_profil": {k: {"label": v["label"], "ket": v["ket"], "porsi": v["porsi"]} for k, v in PROFIL.items()}})
