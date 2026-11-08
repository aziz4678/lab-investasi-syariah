import argparse
import re
from datetime import date, datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import analisis_profil as apf
from backend.research import uji_h35 as h35

WADAH = {"LK": "lokal", "GL": "global"}
LABEL = {"LK": "RD saham syariah Indonesia", "GL": "RD saham syariah global"}
JUMLAH = {"LK": 3, "GL": 1}
GLOBAL_DISETUJUI = {2233}
MIN_TAHUN = 3
AKTIF_HARI = 14
APLIKASI = ("semua", "bibit", "makmur", "ajaib")
KOLEKSI = "keranjang_pertumbuhan"
KOLEKSI_PANTAU = "keranjang_pertumbuhan_pantau"
NAMA_HASIL = "pertumbuhan"
BENTUK_ULANG_BULAN = 1
AUM_KELUAR_PERSENTIL = 25
AUM_KELUAR_BULAN = 2
LOMPAT = 0.30
MULAI_PRODUK = pd.Period("2016-07", "M")
BATAS_MIN_BELI = {"IDR": 1_000_000, "USD": 100}
BOBOT_LOKAL = 0.5
HORISON = {5: 60, 10: 120}
MIN_PRODUK_GLOBAL = 5
BIAYA_PENGGANTI = 0.02
KATEGORI_LK = ("saham", "indeks", "etf")
KATEGORI_GL = ("global", "indeks", "etf")
BUKAN_SAHAM = re.compile(r"SUKUK|BALANCED|MIXED|INCOME|FIXED|PASAR UANG|MONEY|CAMPURAN|PENDAPATAN", re.I)
REGIONAL = re.compile(r"ASIA|CHINA|ASEAN|INDIA|CAKRA|\bUS\b|S&P 500|SNP 500|AMERIKA|FRANCHISE|\bEM\b|EMERGING", re.I)
SEKTOR = re.compile(r"TECHNOLOGY|TEKNOLOGI|\bTECH\b|HEALTHCARE|KESEHATAN|GOLD", re.I)
ALASAN_SEKTOR = "ditolak: satu sektor, menambah risiko konsentrasi teknologi AS"
TEKNOLOGI = re.compile(r"TECHNOLOGY|TEKNOLOGI|\bTECH\b", re.I)
KRITERIA = {"jumlah": JUMLAH, "min_tahun": MIN_TAHUN, "aktif_hari": AKTIF_HARI, "urut": "biaya termurah, lalu dana kelolaan terbesar",
            "aum": "dana kelolaan >= median produk yang lolos di jenisnya", "platform": "wajib ada di >= 1 aplikasi (Bibit/Makmur/Ajaib); kosong = gugur",
            "bagi_hasil": "hanya tanda bagi hasil tunai Pasardana (RD saham yang rugi tidak dianggap bagi hasil)",
            "global": "hanya RD global luas yang disetujui user (Schroder Global Sharia Equity Fund USD); regional dan satu sektor ditolak",
            "min_beli": "tidak menyaring; ditandai 'cek di aplikasi' bila versi MI > Rp1 jt / US$100",
            "bentuk_ulang": "seluruh keranjang tiap Januari",
            "keluar": [f"NAV tidak terbit > {AKTIF_HARI} hari / bubar", "mulai membagi hasil tunai", "tidak lagi ada di aplikasi",
                       f"lokal: biaya naik di atas biaya produk ke-{JUMLAH['LK']} calon", f"lokal: dana kelolaan < persentil {AUM_KELUAR_PERSENTIL} {AUM_KELUAR_BULAN} bulan berturut-turut"],
            "ganti": "lokal: diganti calon termurah berikutnya; global: TIDAK diganti otomatis, keranjang global kosong + daftar calon pengganti"}


def _daftar():
    from backend.app.services import reksadana as rdn
    return rdn.daftar()["data"]


def angka_min_beli(teks):
    if teks is None:
        return None, None
    t = str(teks).upper()
    if "TIDAK ADA" in t:
        return 0.0, None
    uang = "USD" if ("USD" in t or "$" in t or "DOLLAR" in t or "DOLAR" in t) else "IDR"
    m = re.search(r"\d[\d.,]*", t)
    if not m:
        return None, uang
    s = m.group(0).rstrip(".,")
    if re.search(r"[.,]\d{1,2}$", s) and not re.search(r"[.,]\d{3}$", s):
        s = s[: s.rfind(".") if s.rfind(".") > s.rfind(",") else s.rfind(",")]
    return float(re.sub(r"[.,]", "", s)), uang


def wadah_dari(x):
    if x.get("mata_uang") == "IDR" and x.get("kategori") in KATEGORI_LK:
        return "LK"
    if x.get("mata_uang") == "USD" and x.get("kategori") in KATEGORI_GL:
        return "GL"
    return None


def alasan_dasar(x, k, bagi, batas_aktif):
    a = []
    if k == "GL":
        if BUKAN_SAHAM.search(x["nama"]):
            a.append("bukan RD saham")
        elif REGIONAL.search(x["nama"]):
            a.append("regional / satu negara, bukan global")
        elif SEKTOR.search(x["nama"]):
            a.append(ALASAN_SEKTOR if TEKNOLOGI.search(x["nama"]) else "ditolak: satu sektor")
    if not x.get("nav_tgl") or pd.Timestamp(x["nav_tgl"]) < batas_aktif or x.get("nav_beku"):
        a.append("tidak aktif")
    if (x.get("tahun_data") or 0) < MIN_TAHUN:
        a.append(f"riwayat < {MIN_TAHUN} th")
    if int(x["id"]) in bagi:
        a.append("bagi hasil tunai")
    if x.get("biaya") is None or x["biaya"] <= 0:
        a.append("biaya tidak diketahui")
    if not x.get("platform"):
        a.append("platform tidak diketahui")
    return a


def ringkas_produk(x, k):
    nilai, uang = angka_min_beli(x.get("min_beli"))
    uang = uang or x.get("mata_uang")
    return {"id": int(x["id"]), "nama": x["nama"], "mi": x.get("mi"), "wadah": k, "kategori": x.get("kategori"), "mata_uang": x.get("mata_uang"),
            "biaya": x.get("biaya"), "aum": x.get("aum"), "tahun_data": x.get("tahun_data"), "risiko_skala": x.get("risiko"),
            "min_beli_mi": x.get("min_beli"), "min_beli_nilai": nilai, "min_beli_uang": uang,
            "cek_aplikasi": bool(nilai is not None and nilai > BATAS_MIN_BELI.get(uang, BATAS_MIN_BELI["IDR"])),
            "platform": [{"kode": p["kode"], "url": p.get("url")} for p in x.get("platform") or []]}


def calon(data=None):
    data = _daftar() if data is None else data
    bagi = {int(x["_id"]) for x in d.koneksi().rd_produk.find({"Dividend": True}, {"_id": 1})}
    batas_aktif = pd.Timestamp(date.today()) - pd.Timedelta(days=AKTIF_HARI)
    lolos, gugur = {k: [] for k in WADAH}, []
    for x in data:
        k = wadah_dari(x)
        if k is None:
            continue
        a = alasan_dasar(x, k, bagi, batas_aktif)
        p = ringkas_produk(x, k)
        if a:
            gugur.append({**p, "alasan": a})
        else:
            lolos[k].append(p)
    batas = {}
    for k, v in lolos.items():
        batas[k] = float(np.median([c["aum"] or 0 for c in v])) if v else 0.0
        kecil = [c for c in v if (c["aum"] or 0) < batas[k]]
        gugur += [{**c, "alasan": ["dana kelolaan < median produk sejenis yang lolos"]} for c in kecil]
        lolos[k] = sorted([c for c in v if (c["aum"] or 0) >= batas[k]], key=lambda c: (c["biaya"], -(c["aum"] or 0)))
    return lolos, gugur, batas


def di_aplikasi(daftar, aplikasi):
    return daftar if aplikasi == "semua" else [c for c in daftar if any(p["kode"] == aplikasi for p in c["platform"])]


def pilih(lolos, aplikasi):
    lk = di_aplikasi(lolos["LK"], aplikasi)[:JUMLAH["LK"]]
    gl_semua = di_aplikasi(lolos["GL"], aplikasi)
    gl = [c for c in gl_semua if c["id"] in GLOBAL_DISETUJUI][:JUMLAH["GL"]]
    return {"LK": lk, "GL": gl}


def calon_pengganti_global(lolos, gugur):
    return ([{**c, "alasan": ["lolos saringan, belum disetujui user"]} for c in lolos["GL"] if c["id"] not in GLOBAL_DISETUJUI] +
            [c for c in gugur if c["wadah"] == "GL" and not any(a.startswith("regional") or a.startswith("ditolak") or a == "bukan RD saham" for a in c["alasan"])])


def info_aplikasi(lolos):
    return {app: {k: len(di_aplikasi(lolos[k], app)) for k in WADAH} | {"GL_disetujui": len([c for c in di_aplikasi(lolos["GL"], app) if c["id"] in GLOBAL_DISETUJUI])}
            for app in APLIKASI}


def terbaru(aplikasi="semua", kol=None):
    kol = kol if kol is not None else dt.db()[KOLEKSI]
    return kol.find_one({"aplikasi": aplikasi}, sort=[("dibentuk", -1)])


def _aum_rendah(pantau, id_, rendah, bulan):
    kunci = str(id_)
    if not rendah:
        pantau.pop(kunci, None)
        return False
    pantau[kunci] = ([b for b in pantau.get(kunci, []) if b != bulan] + [bulan])[-AUM_KELUAR_BULAN:]
    b = pd.Period(bulan, "M")
    return all(str(b - i) in pantau[kunci] for i in range(AUM_KELUAR_BULAN))


def produk_keluar(lama, lolos, gugur, pantau, bulan, semua_lk):
    kini = {c["id"]: c for v in lolos.values() for c in v}
    sebab = {c["id"]: c["alasan"] for c in gugur}
    keluar = []
    segar = di_aplikasi(lolos["LK"], lama["aplikasi"])
    batas_biaya = segar[JUMLAH["LK"] - 1]["biaya"] if len(segar) >= JUMLAH["LK"] else float("inf")
    p_aum = float(np.percentile([c["aum"] or 0 for c in semua_lk], AUM_KELUAR_PERSENTIL)) if semua_lk else 0.0
    for k, isi in lama["isi"].items():
        for c in isi:
            x = kini.get(c["id"])
            s = sebab.get(c["id"]) or []
            alasan = None
            if x is None and (not s or "tidak aktif" in s):
                alasan = f"NAV tidak terbit > {AKTIF_HARI} hari / bubar"
            elif "bagi hasil tunai" in s:
                alasan = "mulai membagi hasil tunai"
            elif "platform tidak diketahui" in s or (x is not None and lama["aplikasi"] != "semua" and not di_aplikasi([x], lama["aplikasi"])):
                alasan = "tidak lagi ditemukan di aplikasi"
            elif k == "LK" and x is not None and x["biaya"] > batas_biaya:
                alasan = f"biaya {x['biaya']:.2f}% di atas produk ke-{JUMLAH['LK']} calon ({batas_biaya:.2f}%)"
            elif k == "LK":
                aum = (x or next((g for g in gugur if g["id"] == c["id"]), {})).get("aum") or 0
                if _aum_rendah(pantau, c["id"], aum < p_aum, bulan):
                    alasan = f"dana kelolaan < persentil {AUM_KELUAR_PERSENTIL} produk yang lolos {AUM_KELUAR_BULAN} bulan berturut-turut"
            elif k == "GL" and x is None and s:
                alasan = "gagal saringan: " + ", ".join(s)
            if alasan:
                keluar.append({"wadah": k, "id": c["id"], "nama": c["nama"], "alasan": alasan})
    return keluar


def ganti(lama, lolos, keluar):
    buang = {x["id"] for x in keluar}
    isi = {k: [c for c in v if c["id"] not in buang] for k, v in lama["isi"].items()}
    masuk = []
    for x in keluar:
        if x["wadah"] != "LK":
            continue
        ada = {c["id"] for c in isi["LK"]} | buang
        baru = next((c for c in di_aplikasi(lolos["LK"], lama["aplikasi"]) if c["id"] not in ada), None)
        if baru is not None:
            isi["LK"].append(baru)
            masuk.append({"wadah": "LK", "id": baru["id"], "nama": baru["nama"], "ganti": x["id"]})
    isi["LK"].sort(key=lambda c: (c["biaya"], -(c["aum"] or 0)))
    return isi, masuk


def perbarui(cetak=True, hari=None):
    hari = hari or date.today()
    bulan = str(pd.Period(hari, "M"))
    kol, kol_pantau = dt.db()[KOLEKSI], dt.db()[KOLEKSI_PANTAU]
    lolos, gugur, batas = calon()
    semua_lk = lolos["LK"] + [c for c in gugur if c["wadah"] == "LK" and c["alasan"] == ["dana kelolaan < median produk sejenis yang lolos"]]
    pengganti = calon_pengganti_global(lolos, gugur)
    per_app = info_aplikasi(lolos)
    hasil = {}
    for app in APLIKASI:
        lama = terbaru(app, kol)
        waktu = datetime.now()
        ubah = None
        if lama is None or (hari.month == BENTUK_ULANG_BULAN and lama["penuh"].year < hari.year):
            ubah = {"alasan": "awal" if lama is None else "januari", "catatan": [], "masuk": [], "isi": pilih(lolos, app), "penuh": datetime.combine(hari, waktu.time())}
        else:
            pantau = (kol_pantau.find_one({"_id": app}) or {}).get("aum_rendah", {})
            keluar = produk_keluar(lama, lolos, gugur, pantau, bulan, semua_lk)
            kol_pantau.replace_one({"_id": app}, {"_id": app, "aum_rendah": pantau, "diperbarui": waktu}, upsert=True)
            if keluar:
                isi, masuk = ganti(lama, lolos, keluar)
                ubah = {"alasan": "ganti produk", "catatan": keluar, "masuk": masuk, "isi": isi, "penuh": lama["penuh"]}
        if ubah is None:
            hasil[app] = {"berubah": False, "dok": lama}
            continue
        dok = {"_id": f"{app}_{waktu:%Y%m%d%H%M%S}", "aplikasi": app, "dibentuk": waktu, **ubah, "gugur": gugur, "batas_aum": batas,
               "per_aplikasi": per_app, "pengganti_global": pengganti, "kriteria": KRITERIA, "sebelumnya": lama["_id"] if lama else None}
        kol.insert_one(dok)
        hasil[app] = {"berubah": True, "dok": dok}
    if cetak:
        for app, h in hasil.items():
            x = h["dok"]
            print(f"[{app}] {'BERUBAH (' + x['alasan'] + ')' if h['berubah'] else 'tetap'} · " + " · ".join(f"{WADAH[k]} {len(x['isi'][k])}" for k in WADAH))
            for c in x.get("catatan") or []:
                print(f"    keluar {c['nama']}: {c['alasan']}")
        print("  lolos per aplikasi (lokal / global luas / global disetujui): " + "; ".join(f"{a} {v['LK']}/{v['GL']}/{v['GL_disetujui']}" for a, v in per_app.items()))
    return hasil


def sidik():
    kol = dt.db()[KOLEKSI]
    return "|".join((terbaru(a, kol) or {}).get("_id", "-") for a in APLIKASI)


def seri_rupiah(ids):
    if not ids:
        return {}
    df = pd.DataFrame(list(d.koneksi().rd_ojk.find({"fund": {"$in": ids}}, {"_id": 0, "fund": 1, "tgl": 1, "nab": 1, "unit": 1})))
    if df.empty:
        return {}
    df = df[df["unit"] > 0]
    df["nav"] = df["nab"] / df["unit"]
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    return {int(f): g.sort_values("nab").groupby("tgl")["nav"].last().sort_index() for f, g in df.groupby("fund")}


def return_wadah(produk, r_kat):
    ids = [c["id"] for c in produk]
    seri = seri_rupiah(ids)
    R = pd.DataFrame(index=r_kat.index)
    for i in ids:
        s = seri.get(i)
        if s is None or s.empty:
            R[i] = np.nan
            continue
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))
        R[i] = s.pct_change(fill_method=None).reindex(r_kat.index)
    lompat = R.abs() > LOMPAT
    kejadian = [{"id": int(i), "bulan": str(t), "return": float(R.at[t, i])} for i in ids for t in R.index[lompat[i]]]
    R = R.mask(lompat)
    kosong = R.isna()
    r = R.apply(lambda kol: kol.fillna(r_kat)).mean(axis=1) if ids else r_kat
    return r, {"isian": float(kosong.to_numpy().mean()) if ids else 1.0, "isian_produk": {str(i): float(kosong[i].mean()) for i in ids},
               "lompat": kejadian, "tanpa_ojk": [int(i) for i in ids if i not in seri]}


def kategori_lama():
    Lg, _, info = h35.indeks_rd_global()
    baru, _ = apf.indeks_baru(cetak=False)
    Ll = baru["SH"][0]
    a = max(Lg.index[0], Ll.index[0], MULAI_PRODUK - 1)
    b = min(Lg.index[-1], Ll.index[-1])
    R = pd.DataFrame({"LK": (Ll / Ll.shift(1) - 1).loc[a + 1:b], "GL": (Lg / Lg.shift(1) - 1).loc[a + 1:b]})
    return R, info


def global_luas_ojk():
    from backend.research import analisis_likuiditas as al
    db = d.koneksi()
    df = pd.DataFrame(list(db.rd_ojk.find({"syariah": True, "denominasi": "USD", "tipe": {"$in": ["Global Fund", "Equity Fund"]}},
                                          {"_id": 0, "kunci": 1, "produk": 1, "tipe": 1, "tgl": 1, "nab": 1, "unit": 1, "fund": 1})))
    luas = ~df["produk"].str.contains(BUKAN_SAHAM) & ~df["produk"].str.contains(REGIONAL) & ~df["produk"].str.contains(SEKTOR)
    df = df[luas & (df["unit"] > 0)].copy()
    df["nav"] = df["nab"] / df["unit"]
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    df["kelompok"] = "GL"
    df["seri"] = np.where(df["fund"].notna(), "f" + df["fund"].astype("Int64").astype(str), df["kunci"])
    bagi = {int(x["_id"]) for x in db.rd_produk.find({"Dividend": True}, {"_id": 1})}
    pilih, s, _ = al.pilih_seri(df, bagi)
    idx = pilih[~pilih["bh_pasardana"]].index
    R = al.tabel_return(s, idx)
    R = R.mask(R.abs() > LOMPAT)
    return R, sorted(pilih.loc[idx, "produk"].unique()), int((pilih.loc[idx, "selesai"] < pd.Period(date.today(), "M") - 1).sum())


def pengganti_isdw(bulan):
    from backend.db import harga
    x = harga.indeks_luar("gl_msci_world_islamic")["adj_close"].dropna()
    x.index = pd.to_datetime(x.index)
    m = x.resample("ME").last()
    m.index = m.index.to_period("M")
    fx = h35.kurs()
    usd = (m / m.shift(1) - 1).reindex(bulan)
    k = (fx / fx.shift(1) - 1).reindex(bulan)
    return (1 + usd) * (1 + k) * (1 - BIAYA_PENGGANTI) ** (1 / 12) - 1


def kategori():
    baru, _ = apf.indeks_baru(cetak=False)
    Ll = baru["SH"][0]
    Rg, nama, bubar = global_luas_ojk()
    n = Rg.notna().sum(axis=1)
    a = max(Ll.index[0], MULAI_PRODUK - 1)
    b = Ll.index[-1]
    bulan = pd.period_range(a + 1, b, freq="M")
    n = n.reindex(bulan).fillna(0).astype(int)
    pakai_pengganti = bool(n.min() < MIN_PRODUK_GLOBAL)
    if pakai_pengganti:
        r_gl = pengganti_isdw(bulan)
        label = f"indeks MSCI World Islamic (ISDW.L, dalam rupiah) dikurangi biaya {BIAYA_PENGGANTI * 100:.0f}%/th, pengganti karena RD saham syariah global luas hanya {n.min()}-{n.max()} produk per bulan (< {MIN_PRODUK_GLOBAL})"
    else:
        r_gl = Rg.reindex(bulan).mean(axis=1)
        label = "rata-rata RD saham syariah global luas (termasuk yang bubar)"
    R = pd.DataFrame({"LK": (Ll / Ll.shift(1) - 1).reindex(bulan), "GL": r_gl}).dropna()
    info = {"global_luas_produk": nama, "global_luas_bubar": bubar, "global_luas_per_bulan_min": int(n.min()), "global_luas_per_bulan_maks": int(n.max()),
            "pengganti": pakai_pengganti, "label_global": label, "biaya_pengganti": BIAYA_PENGGANTI}
    return R, info


def sip(R, w=BOBOT_LOKAL, n=120, biaya=0.0):
    a = R[["LK", "GL"]].to_numpy()
    bulan = np.array([p.month for p in R.index])
    f, g, mulai = [], [], []
    for s in range(len(R) - n + 1):
        v = np.zeros(2)
        u = np.array([w, 1 - w])
        for t in range(s, s + n):
            v += np.array([w, 1 - w])
            v *= 1 + a[t]
            u *= 1 + a[t]
            if bulan[t] == 12 and t != s + n - 1 and 0 < w < 1:
                for x in (v, u):
                    tot = x.sum()
                    c = biaya * (abs(x[0] - w * tot))
                    x[:] = np.array([w, 1 - w]) * (tot - c)
        f.append(float(v.sum()))
        g.append(float(u.sum()))
        mulai.append(str(R.index[s]))
    return {"f": f, "g": g, "mulai": mulai, "n": n}


def ringkas_sip(x, setoran=1.0, modal=0.0):
    if not x or not x["f"]:
        return None
    nilai = modal * np.array(x["g"]) + setoran * np.array(x["f"])
    total = modal + setoran * x["n"]
    i_buruk, i_baik = int(np.argmin(nilai)), int(np.argmax(nilai))
    return {"median": float(np.median(nilai)), "terburuk": float(nilai[i_buruk]), "terbaik": float(nilai[i_baik]), "total": float(total),
            "untung": float(np.mean(nilai > total)), "n_mulai": len(nilai), "mulai_terburuk": x["mulai"][i_buruk], "mulai_terbaik": x["mulai"][i_baik],
            "mulai_awal": x["mulai"][0], "mulai_akhir": x["mulai"][-1]}


def kalimat_dekade(h):
    j = h["jalur1"]
    c, lk, gl = j["50/50"], j["100% IDX"], j["100% global"]
    dek = list(c["dekade"])
    buruk_lk = min(dek, key=lambda k: lk["dekade"][k])
    buruk_gl = min(dek, key=lambda k: gl["dekade"][k])
    teks = []
    if buruk_lk != buruk_gl:
        teks.append(f"Dekade terburuk Indonesia ({buruk_lk}) bukan dekade terburuk global ({buruk_gl}): saat yang satu lesu, yang lain cenderung tumbuh.")
    else:
        teks.append(f"Indonesia dan global sama-sama paling lemah di {buruk_lk}.")
    if c["j_buruk"] > 0:
        teks.append("Campuran 50/50 tidak pernah rugi dalam periode 10 tahun mana pun"
                    + (f", sedangkan 100% Indonesia pernah" if lk["j_buruk"] < 0 else "") + ".")
    elif c["j_buruk"] > lk["j_buruk"]:
        teks.append("Periode 10 tahun terburuk campuran 50/50 lebih ringan dari 100% Indonesia.")
    return {"teks": " ".join(teks), "sumber": "di data indeks Jun 2001 – Okt 2026 (JII + dividen, DJIM Titans 100 → MSCI World Islamic, dalam rupiah)",
            "buruk_lokal": buruk_lk, "buruk_global": buruk_gl, "j_buruk": {"lokal": lk["j_buruk"], "campuran": c["j_buruk"], "global": gl["j_buruk"]}}


def rem_min(kandidat, horison):
    ada = {k: v for k, v in kandidat.items() if v is not None and v.get(horison) and v[horison]["f"]}
    if not ada:
        return None
    return min(ada, key=lambda k: float(np.median(ada[k][horison]["f"])))


def kurva(R, biaya=0.0):
    out = {}
    for nm, w in (("lokal", 1.0), ("campuran", BOBOT_LOKAL), ("global", 0.0)):
        V, _ = h35.porto(R.rename(columns={"LK": "idx", "GL": "gl"}), w, biaya)
        out[nm] = V
    bulan = [str(b) for b in out["campuran"].index]
    dd = {nm: (V / V.cummax() - 1) for nm, V in out.items()}
    tahun = {}
    for nm, V in out.items():
        akhir = V.groupby([p.year for p in V.index]).last()
        awal = akhir.shift(1)
        awal.iloc[0] = V.iloc[0]
        tahun[nm] = {str(y): float(akhir[y] / awal[y] - 1) for y in akhir.index}
    return {"bulan": bulan, "nilai": {nm: [float(x) for x in V] for nm, V in out.items()}, "turun": {nm: [float(x) for x in s] for nm, s in dd.items()},
            "per_tahun": tahun, "tahun_sebagian": {"awal": bulan[1], "akhir": bulan[-1]}}


def hitung(cetak=True):
    hasil_h35 = dt.baca_hasil("h35_hasil")
    lama = dt.baca_hasil(NAMA_HASIL)
    Ri = h35.seri(h35.DASAR).rename(columns={"idx": "LK", "gl": "GL"})
    Rk, info_kat = kategori()
    Rl, info_lama = kategori_lama()
    jalur = {"indeks": {str(t): sip(Ri, n=n, biaya=h35.BIAYA_REBAL) for t, n in HORISON.items()},
             "kategori": {str(t): sip(Rk, n=n) for t, n in HORISON.items()}}
    pembanding = {"indeks": {f"{nm}": {str(t): sip(Ri, w=w, n=n, biaya=h35.BIAYA_REBAL) for t, n in HORISON.items()} for nm, w in (("lokal", 1.0), ("global", 0.0))},
                  "kategori": {f"{nm}": {str(t): sip(Rk, w=w, n=n) for t, n in HORISON.items()} for nm, w in (("lokal", 1.0), ("global", 0.0))}}
    versi_lama = {"label": "kategori global lama = semua RD saham syariah USD termasuk regional Asia/China/ASEAN/India dan sektor",
                  "sip": {t: ringkas_sip(sip(Rl, n=n), 1_000_000) for t, n in (("5", 60), ("10", 120))},
                  "sumber_pakai_lama": (lama or {}).get("pakai", {}).get("semua")}
    keranjang, isian, kurva_keranjang = {}, {}, None
    for app in APLIKASI:
        dok = terbaru(app)
        if dok is None or not dok["isi"]["LK"] or not dok["isi"]["GL"]:
            keranjang[app], isian[app] = None, None
            continue
        r_lk, i_lk = return_wadah(dok["isi"]["LK"], Rk["LK"])
        r_gl, i_gl = return_wadah(dok["isi"]["GL"], Rk["GL"])
        Rb = pd.DataFrame({"LK": r_lk, "GL": r_gl})
        keranjang[app] = {str(t): sip(Rb, n=n) for t, n in HORISON.items()}
        isian[app] = {"LK": i_lk, "GL": i_gl, "dok": dok["_id"]}
        if app == "semua":
            kurva_keranjang = kurva(Rb)
    pakai = {}
    for app in APLIKASI:
        pakai[app] = {"5": rem_min({"keranjang": keranjang[app], "kategori": jalur["kategori"]}, "5"),
                      "10": rem_min({"indeks": jalur["indeks"], "kategori": jalur["kategori"], "keranjang": keranjang[app]}, "10")}
    periode = {"indeks": [str(Ri.index[0]), str(Ri.index[-1])], "kategori": [str(Rk.index[0]), str(Rk.index[-1])]}
    isi = {"dihitung": datetime.now(), "periode": periode, "jalur": jalur, "pembanding": pembanding, "keranjang": keranjang, "isian": isian, "pakai": pakai,
           "info_kategori": info_kat, "info_kategori_lama": {k: v for k, v in info_lama.items() if k != "periksa"}, "versi_lama": versi_lama,
           "kurva": {"indeks": kurva(Ri, h35.BIAYA_REBAL), "kategori": kurva(Rk), "keranjang": kurva_keranjang},
           "indeks_h35": {nm: {x: hasil_h35["jalur1"][nm][x] for x in ("cagr", "dd", "pulih", "sejak_puncak", "j_buruk", "j_baik", "j_menang", "dekade", "mar")}
                          for nm in ("100% IDX", "70/30", "50/50", "100% global")},
           "kriteria_h35": hasil_h35["kriteria"], "k4_h35": hasil_h35["k4"], "varian_h35": {k: v["kriteria"] for k, v in hasil_h35["varian"].items()},
           "pecah_h35": hasil_h35["pecah"], "korelasi_h35": hasil_h35["korelasi"], "dekade": kalimat_dekade(hasil_h35),
           "contoh_desember": contoh_desember(Rk), "sidik": sidik_input()}
    dt.simpan_hasil(NAMA_HASIL, isi)
    if cetak:
        print(f"kategori global: {info_kat['label_global']}; RD global luas {len(info_kat['global_luas_produk'])} seri ({info_kat['global_luas_bubar']} bubar)")
        for app in APLIKASI:
            for t in ("5", "10"):
                src = pakai[app][t]
                kandidat = {"indeks": jalur["indeks"], "kategori": jalur["kategori"], "keranjang": keranjang[app]}
                r = ringkas_sip(kandidat[src][t], 1_000_000) if src else None
                if r:
                    print(f"[{app}] SIP {t} th Rp1 jt/bln: sumber {src} ({r['n_mulai']} tanggal mulai) median Rp{r['median'] / 1e6:.1f} jt, terburuk Rp{r['terburuk'] / 1e6:.1f} jt "
                          f"(mulai {r['mulai_terburuk']}), terbaik Rp{r['terbaik'] / 1e6:.1f} jt, untung {r['untung'] * 100:.0f}% (setor Rp{r['total'] / 1e6:.0f} jt)")
            if isian[app]:
                print(f"    isian kategori: lokal {isian[app]['LK']['isian'] * 100:.1f}%, global {isian[app]['GL']['isian'] * 100:.1f}%")
        for t, r in versi_lama["sip"].items():
            print(f"versi lama kategori {t} th: median Rp{r['median'] / 1e6:.1f} jt, terburuk Rp{r['terburuk'] / 1e6:.1f} jt, untung {r['untung'] * 100:.0f}% ({r['n_mulai']} tanggal mulai)")
    return isi


def contoh_desember(Rk):
    tahun = Rk.index[-1].year - 1 if Rk.index[-1].month < 12 else Rk.index[-1].year
    x = Rk.loc[pd.Period(f"{tahun}-01", "M"):pd.Period(f"{tahun}-12", "M")]
    v = np.zeros(2)
    for _, r in x.iterrows():
        v += np.array([BOBOT_LOKAL, 1 - BOBOT_LOKAL])
        v *= 1 + r[["LK", "GL"]].to_numpy()
    return {"tahun": tahun, "lokal": float(v[0]), "global": float(v[1]), "setoran_bulan": len(x), "sumber": "rata-rata RD sejenis"}


def sidik_input():
    db = d.koneksi()
    oj = db.rd_ojk.find_one({}, {"tgl": 1}, sort=[("tgl", -1)])
    return {"keranjang": sidik(), "rd_ojk": f"{oj['tgl']:%Y-%m}" if oj else None, "h35": str(dt.versi_hasil("h35_hasil"))}


def perlu_hitung():
    h = dt.baca_hasil(NAMA_HASIL)
    if not h:
        return True, "belum pernah dihitung"
    kini = sidik_input()
    beda = [k for k in ("keranjang", "rd_ojk", "h35") if kini.get(k) != (h.get("sidik") or {}).get(k)]
    return bool(beda), ", ".join(beda) or "data sama"


def utama(bila_perlu=False):
    perbarui()
    perlu, alasan = perlu_hitung()
    if bila_perlu and not perlu:
        print(f"hitung dilewati: {alasan}")
        return
    hitung()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bila-perlu", action="store_true")
    utama(ap.parse_args().bila_perlu)
