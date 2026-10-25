from functools import lru_cache

import numpy as np
import pandas as pd

from backend.db import koneksi as d

HARI_TAHUN = 250
MIN_TITIK = 200
TOLERANSI_HARI = 14
NAV_LAMA_HARI = 7
BATAS_BEKU = 0.5
LABEL = {
    "pasar_uang": "Pasar uang", "pendapatan_tetap": "Pendapatan tetap", "campuran": "Campuran", "saham": "Saham", "indeks": "Indeks",
    "etf": "ETF", "global": "Global (luar negeri)", "terproteksi": "Terproteksi", "penyertaan_terbatas": "Penyertaan terbatas", "dire": "DIRE/DINFRA", "lain": "Lainnya",
}
URUT_KATEGORI = list(LABEL)
BOBOT = {
    "pasar_uang": {"ret_1th": 0.6, "biaya": 0.2, "aum": 0.2},
    "default": {"ret_1th": 0.4, "dd": 0.25, "vol": 0.15, "biaya": 0.1, "aum": 0.1},
}
ARAH = {"ret_1th": 1, "dd": 1, "vol": -1, "biaya": -1, "aum": 1}
PROFIL = {
    "konservatif": {"label": "Konservatif", "ket": "Utamakan modal aman, penghasilan stabil", "porsi": {"pasar_uang": 50, "pendapatan_tetap": 40, "saham": 10}},
    "moderat": {"label": "Moderat", "ket": "Seimbang antara stabil dan tumbuh", "porsi": {"pasar_uang": 20, "pendapatan_tetap": 40, "saham": 40}},
    "agresif": {"label": "Agresif", "ket": "Kejar pertumbuhan, siap turun dalam", "porsi": {"pasar_uang": 10, "pendapatan_tetap": 20, "saham": 70}},
}
PAJAK = {"rd": "Bukan objek pajak bagi pemegang unit", "sr": "Kupon kena pajak final 10%", "deposito": "Bunga kena pajak final 20%",
         "dividen": "Dividen kena pajak final 10% (bisa bebas kalau diinvestasikan ulang)", "saham": "Pajak jual 0,1% dari nilai jual"}


def versi():
    db = d.koneksi()
    i = db.rd_info.find_one({"_id": "ringkas"}) or {}
    return str(i.get("diperbarui")), db.rd_nav.estimated_document_count(), str((i.get("ojk") or {}).get("diimpor"))


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
    b = [x for x in (det or {}).get("biaya") or [] if x.get("nilai") is not None]
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


@lru_cache(maxsize=2)
def _daftar(kunci):
    db = d.koneksi()
    produk = list(db.rd_produk.find({"tidak_aktif": {"$ne": True}}))
    detail = {x["_id"]: x for x in db.rd_detail.find({}, {"biaya": 1, "risiko": 1, "pembanding": 1, "tgl_terbit": 1, "min_beli": 1})}
    n = nav()
    oj = pd.DataFrame(list(db.rd_ojk.find({"fund": {"$ne": None}}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    oj = {f: g.assign(tgl=pd.to_datetime(g["tgl"])).set_index("tgl")["nav"].sort_index() for f, g in oj.groupby("fund")} if not oj.empty else {}
    baris = []
    for p in produk:
        s = n[p["_id"]] if p["_id"] in n.columns else pd.Series(dtype=float)
        m = metrik(s)
        m.update(jangka_panjang(oj.get(p["_id"]), s.dropna()))
        det = detail.get(p["_id"], {})
        baris.append({
            "id": p["_id"], "nama": p["nama"], "mi": p.get("InvestmentManagerName"), "kategori": p["kategori"], "kategori_label": LABEL.get(p["kategori"], p["kategori"]),
            "mata_uang": p["mata_uang"], "nav": p.get("NetAssetValue"), "nav_tgl": p["nav_tgl"].strftime("%Y-%m-%d") if p.get("nav_tgl") else None,
            "aum": p.get("AssetUnderManagement"), "biaya": biaya_terakhir(det), "biaya_mi": p.get("InvestmentManagerFee"), "min_beli": p.get("MinimumSubscription"),
            "risiko": det.get("risiko") or p.get("RiskClassificationValue"), "pembanding": det.get("pembanding"),
            "terbit": det["tgl_terbit"].strftime("%Y-%m-%d") if det.get("tgl_terbit") else None, "etf": bool(p.get("ExchangeTradedFund")),
            "sumber_ret_1th": (p.get("YearlyReturn") * 100) if p.get("YearlyReturn") is not None else None, **m,
        })
    df = pd.DataFrame(baris)
    if df.empty:
        return []
    tgl_nav = pd.to_datetime(df["nav_tgl"])
    df["nav_lama"] = (tgl_nav < tgl_nav.max() - pd.Timedelta(days=NAV_LAMA_HARI)).fillna(True)
    df["skor"] = np.nan
    for k, g in df.groupby("kategori"):
        cukup = g[(g["titik"] >= MIN_TITIK) & ~g["nav_beku"].fillna(False).astype(bool)]
        if len(cukup) < 3:
            continue
        bobot = BOBOT.get(k, BOBOT["default"])
        total = pd.Series(0.0, index=cukup.index)
        dipakai = pd.Series(0.0, index=cukup.index)
        for kolom, w in bobot.items():
            v = cukup[kolom]
            ada = v.notna()
            if ada.sum() < 3:
                continue
            pr = v[ada].rank(pct=True, ascending=ARAH[kolom] > 0)
            total[ada] += pr * w
            dipakai[ada] += w
        df.loc[cukup.index, "skor"] = (total / dipakai.replace(0, np.nan) * 100).round(0)
        df.loc[cukup.index, "peringkat"] = df.loc[cukup.index, "skor"].rank(ascending=False, method="min")
        df.loc[cukup.index, "jumlah_kategori"] = len(cukup)
    return bersih(df.replace({np.nan: None}).to_dict("records"))


def daftar():
    data = _daftar(versi())
    info = d.koneksi().rd_info.find_one({"_id": "ringkas"}, {"_id": 0})
    return {"data": data, "info": bersih(info), "label": LABEL, "bobot": BOBOT, "min_titik": MIN_TITIK}


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
        top = g[g["skor"].notna()].sort_values("skor", ascending=False).head(3)
        hasil.append({"kategori": k, "label": LABEL[k], "jumlah": len(g), "ret_1th": g["ret_1th"].median(), "ret_1th_q3": g["ret_1th"].quantile(0.75),
                      "dd": g["dd"].median(), "biaya": g["biaya"].median(), "aum": g["aum"].sum(), "vol": g["vol"].median(),
                      "terbaik": top[["id", "nama", "skor", "ret_1th"]].to_dict("records")})
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
    from backend.app.services import kesimpulan
    hasil["kesimpulan"] = kesimpulan.reksadana(hasil, sekategori, etf)
    return bersih(hasil)


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
        top = g[g["skor"].notna()].sort_values("skor", ascending=False).head(3) if not g.empty else g
        hasil.append({"kategori": k, "label": LABEL[k] + (" & indeks" if k == "saham" else ""), "persen": persen, "nilai": modal * persen / 100,
                      "ret_1th": g["ret_1th"].median() if not g.empty else None, "dd": g["dd"].median() if not g.empty else None,
                      "pilihan": top[["id", "nama", "mi", "skor", "ret_1th", "dd", "biaya", "min_beli"]].to_dict("records") if not top.empty else []})
    ret = sum((x["ret_1th"] or 0) * x["persen"] / 100 for x in hasil)
    dd = sum((x["dd"] or 0) * x["persen"] / 100 for x in hasil)
    return bersih({"profil": profil, "label": p["label"], "ket": p["ket"], "porsi": hasil, "ret_1th": ret, "dd": dd, "modal": modal,
                   "semua_profil": {k: {"label": v["label"], "ket": v["ket"], "porsi": v["porsi"]} for k, v in PROFIL.items()}})
