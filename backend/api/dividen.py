import json
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from backend.api import valuasi as vl
from backend.api.emiten import ROOT, baca_mentah
from backend.db import data as dt
from backend.db import koneksi as d
from backend.riset import des_ojk

NILAI_MIN = 1e9
SIKLIKAL = {"Energy", "Basic Materials"}
PAJAK = 0.10
TANDA = {
    "spesial": "Dividen spesial: 12 bulan terakhir > 2x biasanya, kemungkinan tidak berulang",
    "laba_turun_30": "Laba 12 bulan turun > 30%: dividen berikutnya bisa dipotong",
    "arus_kas_kurang": "Arus kas operasi lebih kecil dari dividen yang dibayar",
    "payout_lebih_100": "Dividen lebih besar dari laba (payout > 100%) atau perusahaan rugi",
    "yield_tinggi": "Yield > 12%: secara historis paling sering jadi trap",
    "siklikal": "Sektor komoditas: dividen ikut siklus harga komoditas",
    "harga_turun_20": "Harga turun > 20% setahun terakhir: yield tinggi karena harga jatuh",
    "di_bawah_ma200": "Harga di bawah rata-rata 200 hari (tren turun)",
    "der_tinggi": "Utang tinggi (DER > 2)",
}


def json_hasil(nama):
    return dt.baca_hasil(Path(nama).stem)


def info_sektor():
    db = d.koneksi()
    hasil = {x["ticker"][:-3]: (x.get("sector"), x.get("industry")) for x in db.info_saham.find({}, {"ticker": 1, "sector": 1, "industry": 1})}
    for x in db.profil_yahoo.find({}, {"kode": 1, "sektor": 1, "industri": 1}):
        hasil.setdefault(x["kode"], (x.get("sektor"), x.get("industri")))
    return hasil


def nama_dari(db, kode):
    i = db.profil_idx.find_one({"kode": kode}, {"nama": 1}) or db.profil_yahoo.find_one({"kode": kode}, {"nama": 1})
    return (i or {}).get("nama")


def fundamental_tanda(kode, m, t, dps12):
    lap = vl.laporan(kode)
    sh = vl.saham(kode)
    if lap.empty or sh.empty:
        return {}, {}
    r = vl.pada(lap, t)
    if r is None:
        return {}, {}
    n = vl.saham_pada(sh, t, vl.split_dari(m))
    fx = vl.nilai_kurs(r, t)
    if not np.isfinite(n) or not np.isfinite(r["laba_ttm"]):
        return {}, {}
    eps = r["laba_ttm"] * fx / n
    g = vl.tumbuh(r["laba_ttm"], r["laba_ttm_1"])
    bank = np.isnan(r.get("pendapatan", np.nan)) and np.isnan(r.get("aset_lancar", np.nan))
    der = r["liabilitas"] / r["ekuitas_total"] if r["ekuitas_total"] and r["ekuitas_total"] > 0 else np.nan
    cfo = r["arus_kas_operasi_ttm"]
    tanda = {"payout_lebih_100": bool(eps <= 0 or dps12 > eps), "laba_turun_30": bool(g is not None and g < -30),
             "arus_kas_kurang": bool(np.isfinite(cfo) and cfo * fx < dps12 * n), "der_tinggi": bool(not bank and np.isfinite(der) and der > 2)}
    angka = {"eps": eps, "payout": dps12 / eps * 100 if eps > 0 else None, "g_laba": g, "der": der if np.isfinite(der) else None}
    return tanda, angka


def analisis(kode, m, sektor):
    t = m.index.max()
    c = m["close"]
    p = float(c.iloc[-1])
    dv = m["dividends"].fillna(0) if "dividends" in m else pd.Series(0.0, index=m.index)
    dv = dv[dv > 0]
    dps12 = float(dv[dv.index > t - pd.Timedelta(days=365)].sum())
    per_tahun = dv.groupby(dv.index.year).sum()
    tahun_lalu = t.year - 1
    beruntun = 0
    for y in range(tahun_lalu, 2009, -1):
        if per_tahun.get(y, 0) > 0:
            beruntun += 1
        else:
            break
    med3 = float(np.median([per_tahun.get(y, 0) for y in (t.year - 3, t.year - 2, t.year - 1)]))
    bulan = Counter(int(x.month) for x in dv[dv.index.year >= t.year - 3].index)
    p_lalu = vl_nilai(c, t - pd.Timedelta(days=365))
    ma200 = float(c.tail(200).mean())
    yld = dps12 / p * 100 if p > 0 else 0.0
    tanda = {
        "spesial": bool(dps12 > 0 and (med3 == 0 or dps12 > 2 * med3)),
        "yield_tinggi": yld > 12,
        "siklikal": sektor in SIKLIKAL,
        "harga_turun_20": bool(np.isfinite(p_lalu) and p / p_lalu - 1 < -0.2),
        "di_bawah_ma200": p < ma200,
    }
    return {"t": t, "harga": p, "dps12": dps12, "yield": yld, "beruntun": beruntun, "per_tahun": per_tahun, "bulan": bulan,
            "tanda": tanda, "dv": dv, "med3": med3}


def vl_nilai(s, t):
    x = s[s.index <= t]
    return float(x.iloc[-1]) if len(x) else np.nan


def peluang_trap(tanda):
    j = json_hasil("dividend_trap_ringkas.json")
    if not j:
        return None
    n = sum(bool(tanda.get(k)) for k in ["spesial", "harga_turun_20", "di_bawah_ma200", "siklikal"])
    g = j["tanda"].get(str(min(n, 4)))
    return {"jumlah_tanda": n, "trap": round(g["trap"]) if g else None, "n": g["n"] if g else None, "rata_trap": round(j["trap"])}


@lru_cache(maxsize=2)
def _daftar(hari, mtime):
    db = d.koneksi()
    des = des_ojk.baca()
    syariah = des_ojk.syariah_pada(des, pd.Timestamp(hari))
    info = info_sektor()
    hasil = []
    for k in sorted(syariah):
        m = baca_mentah(k)
        if m is None or len(m) < 250:
            continue
        nilai = float((m["close"] * m["volume"]).tail(20).mean())
        if nilai < NILAI_MIN:
            continue
        sektor, industri = info.get(k, (None, None))
        a = analisis(k, m, sektor)
        if a["dps12"] <= 0 and a["beruntun"] == 0:
            continue
        tf, angka = fundamental_tanda(k, m, a["t"], a["dps12"]) if a["dps12"] > 0 else ({}, {})
        tanda = {**a["tanda"], **tf}
        y = a["per_tahun"]
        hasil.append({
            "kode": k, "nama": nama_dari(db, k), "sektor": sektor, "industri": industri, "harga": a["harga"], "dps12": round(a["dps12"], 1),
            "yield": round(a["yield"], 2), "yield_bersih": round(a["yield"] * (1 - PAJAK), 2), "beruntun": a["beruntun"],
            "dps_tahun": {str(t): round(float(y.get(t, 0)), 1) for t in range(a["t"].year - 5, a["t"].year + 1)},
            "bulan": [b for b, _ in a["bulan"].most_common(3)], "nilai_tx": nilai,
            "terakhir": {"tgl": a["dv"].index[-1].strftime("%Y-%m-%d"), "dps": round(float(a["dv"].iloc[-1]), 1)} if len(a["dv"]) else None,
            "tanda": [x for x, v in tanda.items() if v], "payout": round(angka["payout"], 0) if angka.get("payout") else None,
            "g_laba": round(angka["g_laba"], 1) if angka.get("g_laba") is not None else None, "trap": peluang_trap(tanda),
        })
    return hasil


JEDA_BAYAR_STANDAR = 21
COCOK_HARI = 4


def idx_info():
    return d.koneksi().dividen_idx_info.find_one({"_id": "ringkas"}, {"_id": 0})


def idx_kejadian(kode=None, syarat=None):
    q = {"jenis": "tunai", **({"kode": kode} if kode else {}), **(syarat or {})}
    df = pd.DataFrame(list(d.koneksi().dividen_idx.find(q, {"_id": 0})))
    if df.empty:
        return df
    for k in ("cum", "ex", "dps", "bayar"):
        df[k] = pd.to_datetime(df[k]) if k in df else pd.NaT
    df["ex_ef"] = df["ex"].fillna(df["cum"] + pd.offsets.BDay())
    return df.sort_values("ex_ef")


def jeda_standar():
    i = idx_info()
    return (i or {}).get("cek", {}).get("jeda_bayar_median") or JEDA_BAYAR_STANDAR


def pasangkan(dv, ki):
    hasil = {}
    if ki is None or ki.empty:
        return hasil
    for t in dv.index:
        sel = (ki["ex_ef"] - t).abs()
        j = sel.idxmin()
        if sel[j] <= pd.Timedelta(days=COCOK_HARI):
            hasil[t] = ki.loc[j]
    return hasil


def tgl_bayar(dv, ki, standar):
    pas = pasangkan(dv, ki)
    lag = (ki["bayar"] - ki["ex_ef"]).dt.days.dropna() if ki is not None and not ki.empty else pd.Series(dtype=float)
    jeda = int(lag.median()) if len(lag) else standar
    keluar, resmi = [], 0
    for t in dv.index:
        r = pas.get(t)
        if r is not None and pd.notna(r["bayar"]):
            keluar.append(r["bayar"])
            resmi += 1
        else:
            keluar.append(t + pd.Timedelta(days=jeda))
    return pd.Series(dv.values, index=pd.DatetimeIndex(keluar)), resmi, jeda, pas


def fmt(t):
    return t.strftime("%Y-%m-%d") if t is not None and pd.notna(t) else None


def jadwal():
    hari = pd.Timestamp.today().normalize()
    ki = idx_kejadian(syarat={"$or": [{"cum": {"$gte": (hari - pd.Timedelta(days=7)).to_pydatetime()}},
                                      {"bayar": {"$gte": hari.to_pydatetime()}}]})
    info = idx_info()
    if ki.empty:
        return {"data": [], "info": info}
    syariah = des_ojk.syariah_pada(des_ojk.baca(), hari)
    db = d.koneksi()
    hasil = []
    for _, r in ki.iterrows():
        m = baca_mentah(r["kode"])
        harga = float(m["close"].iloc[-1]) if m is not None and len(m) else None
        per = r.get("per_lembar_idx")
        per = float(per) if per is not None and pd.notna(per) else None
        asal = "IDX" if per else None
        if not per and m is not None and "dividends" in m and pd.notna(r["ex_ef"]):
            dv = m["dividends"].fillna(0)
            dekat = dv[(dv > 0) & (abs((dv.index - r["ex_ef"]).days) <= COCOK_HARI)]
            if len(dekat):
                per, asal = float(dekat.iloc[0]), "Yahoo"
        tahap = "menunggu cum" if pd.notna(r["cum"]) and r["cum"] >= hari else "menunggu bayar" if pd.notna(r["bayar"]) and r["bayar"] >= hari else "selesai"
        hasil.append({"kode": r["kode"], "nama": nama_dari(db, r["kode"]), "syariah": r["kode"] in syariah, "cum": fmt(r["cum"]), "ex": fmt(r["ex_ef"]),
                      "bayar": fmt(r["bayar"]), "per_lembar": round(per, 2) if per else None, "tahun_buku": r.get("tahun_buku") if isinstance(r.get("tahun_buku"), str) else None,
                      "harga": harga, "yield": round(per / harga * 100, 2) if per and harga else None, "tahap": tahap, "asal": asal})
    hasil.sort(key=lambda x: (x["cum"] or x["ex"] or ""))
    return {"data": hasil, "info": info}


BIAYA_EX = 0.6
JENDELA_TERENDAH = 60


def reaksi_ex(m, t, dps):
    if t not in m.index:
        return {}
    i = m.index.get_loc(t)
    if i < 1:
        return {}
    p0 = float(m["close"].iloc[i - 1])
    if p0 <= 0:
        return {}
    c = m["close"].iloc[i:].values.astype(float)
    hasil = {"yield_saat": round(dps / p0 * 100, 2), "h1": round((c[0] / p0 - 1) * 100, 2), "harga_cum": p0, "harga_ex": c[0]}
    if len(c) >= 20:
        hasil["h20"] = round((c[19] / p0 - 1) * 100, 2)
        hasil["total20"] = round(hasil["h20"] + hasil["yield_saat"] * (1 - PAJAK) - BIAYA_EX, 2)
    if len(c) >= 20:
        hasil["harga_h20"] = c[19]
    w = c[:JENDELA_TERENDAH]
    j = int(np.argmin(w))
    turun = bool(w[j] < p0)
    kembali = np.nonzero(c[j:] >= p0)[0] if turun else np.array([])
    hasil.update({"terendah": float(w[j]), "terendah_persen": round((w[j] / p0 - 1) * 100, 2), "hari_terendah": j + 1, "pernah_turun": turun,
                  "pulih": (j + int(kembali[0]) + 1) if len(kembali) else (None if turun else 1),
                  "sekarang_persen": round((c[-1] / p0 - 1) * 100, 2), "hari_sejak": len(c)})
    return hasil


@lru_cache(maxsize=2)
def _trap_yield(mtime):
    return dt.baca_hasil("analisis_dividend_trap")


def riwayat_trap(kode, m, dv):
    ex = []
    for t, v in dv[dv.index >= pd.Timestamp("2015-01-01")].items():
        r = reaksi_ex(m, t, float(v))
        if r.get("h20") is None:
            continue
        total = r["h20"] + r["yield_saat"] * (1 - PAJAK) - BIAYA_EX
        ex.append({"ex": t.strftime("%Y-%m-%d"), "yield": r["yield_saat"], "h1": r["h1"], "h20": r["h20"], "total20": round(total, 2),
                   "pulih": r["pulih"], "trap": bool(total < 0)})
    acuan = (json_hasil("exdate_ringkas.json") or {}).get("semua", {})
    n = len(ex)
    kena = sum(x["trap"] for x in ex)
    persen_kena = kena / n * 100 if n else None
    pulih = [x["pulih"] for x in ex if x["pulih"]]
    if n < 3:
        vonis = "data kurang"
    elif persen_kena >= 65:
        vonis = "sering"
    elif persen_kena <= 40:
        vonis = "jarang"
    else:
        vonis = "kadang"
    ver = dt.versi_hasil("analisis_dividend_trap")
    yld = []
    if ver:
        df = _trap_yield(ver)
        for _, r in df[df["kode"] == kode].sort_values("tahun").iterrows():
            yld.append({"tahun": int(r["tahun"]), "yield": round(float(r["yield"]), 1), "total_12b": round(float(r["total_12b"]), 1),
                        "dividen_berikut": round(float(r["dividen_berikut_pct"]), 0) if pd.notna(r["dividen_berikut_pct"]) else None,
                        "trap": bool(r["trap"]), "rugi": bool(r["rugi"]), "dipotong": bool(r["dipotong"])})
    return {"ex": {"n": n, "kena": kena, "persen": round(persen_kena, 0) if persen_kena is not None else None, "vonis": vonis,
                   "median_total20": round(float(np.median([x["total20"] for x in ex])), 2) if n else None,
                   "median_pulih": int(np.median(pulih)) if pulih else None, "belum_pulih": sum(1 for x in ex if not x["pulih"]),
                   "acuan_persen": acuan.get("rugi_h20"), "kejadian": ex[::-1]},
            "yield": {"n": len(yld), "kena": sum(x["trap"] for x in yld), "kejadian": yld[::-1]}}


def daftar():
    data = _daftar(date.today().isoformat(), dt.versi("harian/_ihsg"))
    return {"data": data, "tanda": TANDA, "trap": json_hasil("dividend_trap_ringkas.json")}


def emiten(kode):
    kode = kode.upper()
    m = baca_mentah(kode)
    if m is None:
        return {"ada": False}
    sektor, industri = info_sektor().get(kode, (None, None))
    a = analisis(kode, m, sektor)
    if not len(a["dv"]):
        return {"ada": True, "pernah": False}
    tf, angka = fundamental_tanda(kode, m, a["t"], a["dps12"]) if a["dps12"] > 0 else ({}, {})
    tanda = {**a["tanda"], **tf}
    lap = vl.laporan(kode)
    sh = vl.saham(kode)
    split = vl.split_dari(m)
    tahun = []
    for y in range(max(2010, a["t"].year - 9), a["t"].year + 1):
        dps = float(a["per_tahun"].get(y, 0))
        akhir = vl_nilai(m["close"], pd.Timestamp(f"{y}-12-31"))
        eps = None
        if not lap.empty and not sh.empty:
            au = lap[(lap["periode"] == "AUDIT") & (lap["tahun"] == y - 1)]
            if len(au):
                r = au.iloc[-1]
                n = vl.saham_pada(sh, pd.Timestamp(f"{y}-06-30"), split)
                if np.isfinite(n) and np.isfinite(r["laba"]):
                    eps = r["laba"] * vl.nilai_kurs(r, pd.Timestamp(f"{y}-06-30")) / n
        tahun.append({"tahun": y, "dps": round(dps, 1), "yield": round(dps / akhir * 100, 2) if dps and akhir else None,
                      "eps_tahun_lalu": round(eps, 1) if eps else None, "payout": round(dps / eps * 100, 0) if eps and eps > 0 and dps else None,
                      "berjalan": y == a["t"].year})
    ki = idx_kejadian(kode)
    pas = pasangkan(a["dv"].tail(12), ki)
    riwayat = []
    for t, v in list(a["dv"].tail(12).items())[::-1]:
        r = pas.get(t)
        riwayat.append({"tgl": t.strftime("%Y-%m-%d"), "dps": round(float(v), 2), "cum": fmt(r["cum"]) if r is not None else None,
                        "bayar": fmt(r["bayar"]) if r is not None else None, "idx": r is not None, **reaksi_ex(m, t, float(v))})
    hari = pd.Timestamp.today().normalize()
    mendatang = []
    if not ki.empty:
        akhir_yahoo = a["dv"].index.max()
        for _, r in ki[(ki["ex_ef"] > akhir_yahoo + pd.Timedelta(days=COCOK_HARI)) | (ki["bayar"] >= hari)].iterrows():
            per = r.get("per_lembar_idx")
            mendatang.append({"cum": fmt(r["cum"]), "ex": fmt(r["ex_ef"]), "bayar": fmt(r["bayar"]),
                              "per_lembar": round(float(per), 2) if per is not None and pd.notna(per) else None,
                              "dihitung": bool(r.get("per_lembar_dihitung")) if pd.notna(r.get("per_lembar_dihitung")) else False})
    lag = (ki["bayar"] - ki["ex_ef"]).dt.days.dropna() if not ki.empty else pd.Series(dtype=float)
    return {
        "ada": True, "pernah": True, "harga": a["harga"], "dps12": round(a["dps12"], 1), "yield": round(a["yield"], 2),
        "yield_bersih": round(a["yield"] * (1 - PAJAK), 2), "beruntun": a["beruntun"], "bulan": [b for b, _ in a["bulan"].most_common(4)],
        "tahun": tahun, "riwayat": riwayat, "tanda": [{"kode": x, "ket": TANDA[x]} for x, v in tanda.items() if v],
        "payout": round(angka["payout"], 0) if angka.get("payout") else None, "trap": peluang_trap(tanda), "sektor": sektor,
        "ringkas_trap": json_hasil("dividend_trap_ringkas.json"), "mendatang": mendatang,
        "jeda_bayar": int(lag.median()) if len(lag) else None, "idx_ada": idx_info() is not None,
        "riwayat_trap": riwayat_trap(kode, m, a["dv"]),
    }


def ringkasan():
    def baca(nama):
        df = dt.baca_hasil(Path(nama).stem)
        if df is None:
            return []
        kol = ["tahun", "parsial", "jumlah", "yield_masuk", "penghasilan", "harga", "total", "biaya", "pembanding_penghasilan", "pembanding_total", "ihsg", "saham"]
        df = df[[k for k in kol if k in df]]
        return json.loads(df.round(2).to_json(orient="records"))
    return {"h17a_dev": baca("hasil_h17a_dev.csv"), "h17a_2021": baca("hasil_h17a_2021.csv"), "h17b": baca("hasil_h17b.csv"),
            "trap": json_hasil("dividend_trap_ringkas.json"), "exdate": json_hasil("exdate_ringkas.json")}


def kalkulator(kode_list):
    info = info_sektor()
    syariah = des_ojk.syariah_pada(des_ojk.baca(), pd.Timestamp.today())
    standar = jeda_standar()
    ada_idx = idx_info() is not None
    hasil = []
    for k in [x.strip().upper() for x in kode_list if x.strip()][:30]:
        m = baca_mentah(k)
        if m is None or not len(m):
            continue
        sektor, _ = info.get(k, (None, None))
        a = analisis(k, m, sektor)
        t = a["t"]
        dv = a["dv"]
        tahun_penuh = [t.year - 3, t.year - 2, t.year - 1]
        per_tahun = a["per_tahun"]
        avg3 = float(np.mean([per_tahun.get(y, 0) for y in tahun_penuh]))
        bulan12 = {b: float(dv[(dv.index > t - pd.Timedelta(days=365)) & (dv.index.month == b)].sum()) for b in range(1, 13)}
        bulan3 = {b: float(dv[(dv.index.year.isin(tahun_penuh)) & (dv.index.month == b)].sum()) / 3 for b in range(1, 13)}
        bayar, resmi, jeda, _ = tgl_bayar(dv, idx_kejadian(k) if ada_idx else None, standar)
        asal = pd.Series(dv.index, index=bayar.index)
        bayar12 = {b: float(bayar[(asal.values > t - pd.Timedelta(days=365)) & (bayar.index.month == b)].sum()) for b in range(1, 13)}
        bayar3 = {b: float(bayar[(asal.dt.year.isin(tahun_penuh).values) & (bayar.index.month == b)].sum()) / 3 for b in range(1, 13)}
        rasio = []
        for y in range(max(2011, t.year - 10), t.year):
            sebelum, kini = per_tahun.get(y - 1, 0), per_tahun.get(y, 0)
            if sebelum > 0:
                rasio.append(kini / sebelum)
        terburuk = min(rasio) if rasio else None
        tf, angka = fundamental_tanda(k, m, t, a["dps12"]) if a["dps12"] > 0 else ({}, {})
        tanda = {**a["tanda"], **tf}
        hasil.append({
            "kode": k, "nama": nama_dari(d.koneksi(), k), "sektor": sektor, "harga": a["harga"], "tgl": t.strftime("%Y-%m-%d"), "syariah": k in syariah,
            "dps12": round(a["dps12"], 2), "dps_avg3": round(avg3, 2), "bulan12": bulan12, "bulan3": bulan3, "bayar12": bayar12, "bayar3": bayar3, "bayar_resmi": resmi, "jumlah_dividen": int(len(dv)),
            "jeda_bayar": jeda, "beruntun": a["beruntun"],
            "terburuk": round(terburuk, 3) if terburuk is not None else None,
            "tahun_terburuk": int(range(max(2011, t.year - 10), t.year)[int(np.argmin(rasio))]) if rasio else None,
            "tanda": [x for x, v in tanda.items() if v], "trap": peluang_trap(tanda),
        })
    return {"data": hasil, "tanda": TANDA, "idx": ada_idx}


def bersih(x):
    if isinstance(x, dict):
        return {k: bersih(v) for k, v in x.items() if k != "_id" or isinstance(v, str)}
    if isinstance(x, list):
        return [bersih(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def paper():
    from backend.paper import dividen_harian as pd_
    db = d.koneksi()
    status = db.paper_dividen_status.find_one({"_id": "status"}, {"_id": 0})
    pilihan = {str(x["_id"]): x for x in db.paper_dividen_pilihan.find()}
    nama = {}
    for p in pilihan.values():
        for s_ in p["saham"]:
            s_["nama"] = nama.setdefault(s_["kode"], nama_dari(db, s_["kode"]))
    posisi = list(db.paper_dividen_posisi.find({}, {"_id": 0}).sort("nilai", -1))
    for p in posisi:
        p["nama"] = nama_dari(db, p["kode"])
    ekuitas = list(db.paper_dividen_ekuitas.find({}, {"_id": 0}).sort("tgl", 1))
    transaksi = list(db.paper_dividen_transaksi.find({}, {"_id": 0}).sort("tgl", -1).limit(200))
    kunci = db.batas_paper.find_one({"_id": pd_.ID_KUNCI})
    hari = pd.Timestamp.today().normalize()
    tunggu = list(db.paper_dividen_transaksi.find({"aksi": "dividen", "bayar": {"$gt": hari.to_pydatetime()}}, {"_id": 0}).sort("bayar", 1))
    return bersih({"status": status, "pratinjau": pilihan.pop("pratinjau", None), "pilihan": sorted(pilihan.values(), key=lambda x: x["tahun"]),
                   "posisi": posisi, "ekuitas": ekuitas, "transaksi": transaksi, "menunggu_cair": tunggu,
                   "aturan": pd_.ATURAN, "dikunci": kunci["dikunci"] if kunci else None})


def pengingat(hari_maju=7):
    hari = pd.Timestamp.today().normalize()
    ki = idx_kejadian(syarat={"cum": {"$gte": hari.to_pydatetime(), "$lte": (hari + pd.Timedelta(days=hari_maju)).to_pydatetime()}})
    db = d.koneksi()
    pegang = {x["kode"] for x in db.paper_dividen_posisi.find({}, {"kode": 1})}
    pr = db.paper_dividen_pilihan.find_one({"_id": "pratinjau"})
    calon = {x["kode"] for x in (pr or {}).get("saham", [])}
    if ki.empty:
        return {"data": [], "hari": hari_maju}
    syariah = des_ojk.syariah_pada(des_ojk.baca(), hari)
    hasil = []
    for _, r in ki.iterrows():
        if r["kode"] not in syariah:
            continue
        per = r.get("per_lembar_idx")
        hasil.append({"kode": r["kode"], "nama": nama_dari(db, r["kode"]), "cum": fmt(r["cum"]), "ex": fmt(r["ex_ef"]), "bayar": fmt(r["bayar"]),
                      "per_lembar": round(float(per), 2) if per is not None and pd.notna(per) else None,
                      "sisa_hari": int((r["cum"] - hari).days), "paper": r["kode"] in pegang, "pratinjau": r["kode"] in calon})
    return {"data": sorted(hasil, key=lambda x: x["cum"]), "hari": hari_maju}
