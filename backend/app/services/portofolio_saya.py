import uuid
from datetime import date, datetime

import numpy as np
import pandas as pd

from backend.app.services.reksadana import bersih

KOLEKSI_PORTO = "portofolio_saya"
KOLEKSI_TRX = "transaksi_saya"
KOLEKSI_LOG = "transaksi_saya_log"
TARGET = {"pertumbuhan_saham": {"lokal": 0.5, "global": 0.5}, "pertumbuhan_emas": {"lokal": 0.4, "global": 0.4, "emas": 0.2}, "bebas": {}}
NAMA_TARGET = {"pertumbuhan_saham": "Pertumbuhan: saham 50/50", "pertumbuhan_emas": "Pertumbuhan: saham + emas 40/40/20", "bebas": "Bebas (tanpa target)"}
NAMA_KAKI = {"lokal": "Saham Indonesia", "global": "Saham global", "emas": "Emas", "lainnya": "Lainnya"}
TIPE = ("rd", "etf", "saham")
JENIS = ("beli", "jual")
APLIKASI = ("Bibit", "Ajaib", "Makmur", "Stockbit", "lainnya")
FEE_DEFAULT = {"Stockbit": 0.0015}
LOT = 100
HARI_NAV_MAKS = 7
BASI_HARI_BURSA = 3
MIN_HARI_XIRR = 90
SAMA_DENGAN_TARGET = 0.02


def baru_id():
    return uuid.uuid4().hex


def tgl_teks(x):
    return str(pd.Timestamp(x).date())


def xirr(arus):
    arus = [(pd.Timestamp(t).normalize(), float(v)) for t, v in arus if v]
    if len(arus) < 2 or not any(v < 0 for _, v in arus) or not any(v > 0 for _, v in arus):
        return None
    t0 = min(t for t, _ in arus)
    tahun = np.array([(t - t0).days / 365.0 for t, _ in arus])
    nilai = np.array([v for _, v in arus])

    def f(r):
        return float(np.sum(nilai / (1.0 + r) ** tahun))

    bawah, atas = -0.9999, 100.0
    fb, fa = f(bawah), f(atas)
    if not (np.isfinite(fb) and np.isfinite(fa)) or fb * fa > 0:
        return None
    for _ in range(200):
        tengah = (bawah + atas) / 2
        ft = f(tengah)
        if abs(ft) < 1e-9:
            return tengah
        if fb * ft < 0:
            atas = tengah
        else:
            bawah, fb = tengah, ft
    return (bawah + atas) / 2


def harga_pertama_setelah(seri, tanggal, maks_hari=HARI_NAV_MAKS):
    if seri is None or not len(seri):
        return None
    t = pd.Timestamp(tanggal).normalize()
    sesudah = seri[seri.index >= t]
    if not len(sesudah):
        return None
    if (sesudah.index[0] - t).days > maks_hari:
        return None
    nilai = sesudah.iloc[0]
    return None if pd.isna(nilai) else float(nilai)


def harga_terakhir_sampai(seri, tanggal):
    if seri is None or not len(seri):
        return None
    t = pd.Timestamp(tanggal).normalize()
    sebelum = seri[seri.index <= t].dropna()
    return float(sebelum.iloc[-1]) if len(sebelum) else None


def kaki_dari(tr, info):
    if tr.get("kaki") in NAMA_KAKI:
        return tr["kaki"]
    if tr["tipe_produk"] == "etf":
        return "emas" if info.get("emas") else "lokal"
    if tr["tipe_produk"] == "saham":
        return "lokal"
    return "global" if info.get("mata_uang") == "USD" else "lokal"


def hitung_unit(tr, harga_unit):
    if tr.get("unit"):
        return {"unit": float(tr["unit"]), "status": "ok", "harga_unit": tr.get("harga")}
    if tr["tipe_produk"] in ("etf", "saham") and tr.get("lot"):
        return {"unit": float(tr["lot"]) * LOT, "status": "ok", "harga_unit": tr.get("harga")}
    if tr["tipe_produk"] == "rd":
        if harga_unit is None or harga_unit <= 0:
            return {"unit": None, "status": "menunggu_nav", "harga_unit": None}
        return {"unit": (float(tr["nominal"]) - float(tr.get("biaya") or 0)) / harga_unit, "status": "ok", "harga_unit": harga_unit}
    if tr.get("harga"):
        return {"unit": (float(tr["nominal"]) - float(tr.get("biaya") or 0)) / float(tr["harga"]), "status": "ok", "harga_unit": float(tr["harga"])}
    return {"unit": None, "status": "unit_kosong", "harga_unit": None}


def validasi_transaksi(x):
    sisa = dict(x)
    try:
        sisa["tanggal"] = tgl_teks(sisa.get("tanggal"))
    except Exception:
        raise ValueError("tanggal tidak valid")
    if pd.Timestamp(sisa["tanggal"]) > pd.Timestamp(date.today()) + pd.Timedelta(days=1):
        raise ValueError("tanggal tidak boleh di masa depan")
    if sisa.get("jenis") not in JENIS:
        raise ValueError("jenis harus beli atau jual")
    if sisa.get("tipe_produk") not in TIPE:
        raise ValueError("tipe produk harus rd, etf, atau saham")
    sisa["produk"] = str(sisa.get("produk") or "").strip()
    if not sisa["produk"]:
        raise ValueError("produk wajib diisi")
    if sisa.get("aplikasi") not in APLIKASI:
        sisa["aplikasi"] = "lainnya"
    for k in ("nominal", "biaya", "unit", "harga", "lot"):
        v = sisa.get(k)
        if v in (None, ""):
            sisa[k] = None
            continue
        try:
            sisa[k] = float(v)
        except Exception:
            raise ValueError(f"{k} harus angka")
        if sisa[k] < 0:
            raise ValueError(f"{k} tidak boleh negatif")
    sisa["biaya"] = sisa["biaya"] or 0.0
    if sisa["tipe_produk"] in ("etf", "saham"):
        if not (sisa.get("lot") or sisa.get("unit")):
            raise ValueError("isi jumlah lot")
        if not sisa.get("unit") and sisa.get("lot"):
            sisa["unit"] = sisa["lot"] * LOT
        if not sisa.get("nominal") and sisa.get("harga"):
            dasar = sisa["unit"] * sisa["harga"]
            sisa["nominal"] = dasar + sisa["biaya"] if sisa["jenis"] == "beli" else dasar - sisa["biaya"]
    if not sisa.get("nominal") or sisa["nominal"] <= 0:
        raise ValueError("nominal wajib diisi dan lebih dari 0")
    if sisa["tipe_produk"] == "rd" and sisa["biaya"] >= sisa["nominal"]:
        raise ValueError("biaya tidak boleh lebih besar dari nominal")
    sisa["nama"] = str(sisa.get("nama") or sisa["produk"])
    sisa["catatan"] = str(sisa.get("catatan") or "")[:500]
    if sisa.get("kaki") not in NAMA_KAKI:
        sisa["kaki"] = None
    return {k: sisa.get(k) for k in ("portofolio_id", "tanggal", "jenis", "tipe_produk", "produk", "nama", "aplikasi", "nominal", "unit", "harga", "lot", "biaya", "catatan", "kaki")}


def validasi_portofolio(x):
    nama = str(x.get("nama") or "").strip()
    if not nama:
        raise ValueError("nama wajib diisi")
    target = x.get("target") or "pertumbuhan_saham"
    if target not in TARGET:
        raise ValueError("target tidak dikenal")
    try:
        mulai = tgl_teks(x.get("tanggal_mulai") or date.today())
    except Exception:
        raise ValueError("tanggal mulai tidak valid")
    pengingat = bool(x.get("pengingat_setoran", False))
    try:
        setoran = float(x.get("setoran_rutin") or 0)
        hari = int(x.get("tanggal_setor") or 1)
    except Exception:
        raise ValueError("setoran dan tanggal setor harus angka")
    if pengingat:
        if setoran <= 0:
            raise ValueError("isi setoran rutin kalau pengingat setoran dinyalakan")
        if not 1 <= hari <= 28:
            raise ValueError("tanggal setor harus 1 sampai 28")
    else:
        setoran, hari = max(setoran, 0.0), min(max(hari, 1), 28)
    return {"nama": nama, "target": target, "tanggal_mulai": mulai, "pengingat_setoran": pengingat, "setoran_rutin": setoran, "tanggal_setor": hari, "aktif": bool(x.get("aktif", True))}


def hari_bursa_lalu(tgl, hari_ini):
    return int(np.busday_count(pd.Timestamp(tgl).date(), pd.Timestamp(hari_ini).date()))


def alokasi_vs_target(nilai_kaki, target, bulan_desember):
    total = sum(nilai_kaki.values())
    kaki = []
    for k in dict.fromkeys([*target.keys(), *nilai_kaki.keys()]):
        nyata = nilai_kaki.get(k, 0.0)
        porsi_nyata = nyata / total if total else 0.0
        porsi_target = target.get(k)
        beda = (porsi_target * total - nyata) if porsi_target is not None else None
        kaki.append({"kaki": k, "nama": NAMA_KAKI.get(k, k), "nilai": nyata, "porsi": porsi_nyata, "target": porsi_target, "selisih_porsi": None if porsi_target is None else porsi_nyata - porsi_target,
                     "selisih_rp": beda})
    saran = []
    if target and total > 0:
        for x in kaki:
            if x["selisih_rp"] is None or abs(x["selisih_porsi"]) < SAMA_DENGAN_TARGET:
                continue
            saran.append({"kaki": x["kaki"], "nama": x["nama"], "aksi": "beli" if x["selisih_rp"] > 0 else "jual", "nominal": abs(x["selisih_rp"])})
    return {"total": total, "kaki": kaki, "saran": saran, "desember": bool(bulan_desember), "seimbang": bool(target) and not saran and total > 0}


def simulasi_seri(arus, seri_per_kaki, bobot, hari_ini):
    nilai = 0.0
    dipakai = 0.0
    for tanggal, nominal in arus:
        for k, w in bobot.items():
            s = seri_per_kaki.get(k)
            awal = harga_pertama_setelah(s, tanggal, 7)
            akhir = harga_terakhir_sampai(s, hari_ini)
            if awal and akhir:
                nilai += nominal * w * akhir / awal
                dipakai += nominal * w
            else:
                nilai += nominal * w
    return {"nilai": nilai, "tercakup": dipakai}


def valuasi(transaksi, info_produk, harga, kurs, hari_ini):
    hari_ini = pd.Timestamp(hari_ini).normalize()
    baris, per_produk = [], {}
    for tr in sorted(transaksi, key=lambda x: (x["tanggal"], x.get("dibuat") or "")):
        info = info_produk.get((tr["tipe_produk"], tr["produk"]), {})
        seri = harga.get((tr["tipe_produk"], tr["produk"]))
        h = harga_pertama_setelah(seri, tr["tanggal"]) if tr["tipe_produk"] == "rd" else None
        if h is not None and info.get("mata_uang") == "USD":
            k = harga_terakhir_sampai(kurs, tr["tanggal"])
            h = h * k if k else None
        u = hitung_unit(tr, h)
        tanda = 1 if tr["jenis"] == "beli" else -1
        kaki = kaki_dari(tr, info)
        b = {**tr, "kaki_hitung": kaki, "unit_hitung": u["unit"], "status_unit": u["status"], "harga_unit_hitung": u["harga_unit"], "tanda": tanda}
        baris.append(b)
        p = per_produk.setdefault((tr["tipe_produk"], tr["produk"]), {"tipe_produk": tr["tipe_produk"], "produk": tr["produk"], "nama": tr.get("nama") or tr["produk"], "kaki": kaki, "unit": 0.0, "beli": 0.0, "jual": 0.0, "biaya": 0.0, "menunggu": 0})
        p["beli" if tanda > 0 else "jual"] += tr["nominal"]
        p["biaya"] += tr.get("biaya") or 0.0
        if u["unit"] is None:
            p["menunggu"] += 1
        else:
            p["unit"] += tanda * u["unit"]
    produk = []
    for (tipe, kunci), p in per_produk.items():
        seri = harga.get((tipe, kunci))
        info = info_produk.get((tipe, kunci), {})
        terakhir = harga_terakhir_sampai(seri, hari_ini)
        tgl_data = None
        if terakhir is not None and seri is not None:
            tgl_data = seri[seri.index <= hari_ini].dropna().index[-1]
            if info.get("mata_uang") == "USD":
                k = harga_terakhir_sampai(kurs, hari_ini)
                terakhir = terakhir * k if k else None
        nilai = p["unit"] * terakhir if terakhir is not None else None
        basi = tgl_data is not None and hari_bursa_lalu(tgl_data, hari_ini) > BASI_HARI_BURSA
        produk.append({**p, "harga_terakhir": terakhir, "tgl_data": None if tgl_data is None else tgl_tgl(tgl_data), "basi": basi, "nilai": nilai, "tanpa_harga": nilai is None and p["unit"] != 0})
    return baris, produk


def tgl_tgl(x):
    return str(pd.Timestamp(x).date())


def ringkasan_total(produk, transaksi, hari_ini):
    nilai = sum(p["nilai"] or 0.0 for p in produk)
    beli = sum(t["nominal"] for t in transaksi if t["jenis"] == "beli")
    jual = sum(t["nominal"] for t in transaksi if t["jenis"] == "jual")
    biaya = sum(t.get("biaya") or 0.0 for t in transaksi)
    setor = beli - jual
    untung = nilai - setor
    hasil = {"nilai": nilai, "total_beli": beli, "total_jual": jual, "total_setor": setor, "untung": untung, "untung_persen": untung / beli if beli else None, "biaya": biaya}
    arus = [(t["tanggal"], -t["nominal"] if t["jenis"] == "beli" else t["nominal"]) for t in transaksi]
    pertama = min((pd.Timestamp(t["tanggal"]) for t in transaksi), default=None)
    umur = (pd.Timestamp(hari_ini).normalize() - pertama).days if pertama is not None else 0
    hasil["umur_hari"] = int(umur)
    if pertama is not None and umur >= MIN_HARI_XIRR and nilai > 0:
        hasil["xirr"] = xirr([*arus, (hari_ini, nilai)])
        hasil["xirr_pesan"] = None
    else:
        hasil["xirr"] = None
        hasil["xirr_pesan"] = "belum cukup data (butuh minimal 3 bulan sejak transaksi pertama)"
    return hasil


def deret_waktu(baris, harga, kurs, info_produk, hari_ini):
    if not baris:
        return []
    awal = pd.Timestamp(min(b["tanggal"] for b in baris)).normalize()
    hari_ini = pd.Timestamp(hari_ini).normalize()
    titik = sorted({*pd.date_range(awal, hari_ini, freq="7D"), hari_ini, *[pd.Timestamp(b["tanggal"]) for b in baris]})
    keluar = []
    for t in titik:
        setor, unit, biaya_dasar = 0.0, {}, {}
        for b in baris:
            if pd.Timestamp(b["tanggal"]) > t:
                continue
            setor += b["tanda"] * b["nominal"]
            kunci = (b["tipe_produk"], b["produk"])
            if b["unit_hitung"] is not None:
                unit[kunci] = unit.get(kunci, 0.0) + b["tanda"] * b["unit_hitung"]
                biaya_dasar[kunci] = biaya_dasar.get(kunci, 0.0) + b["tanda"] * b["nominal"]
            else:
                biaya_dasar[kunci] = biaya_dasar.get(kunci, 0.0) + b["tanda"] * b["nominal"]
        nilai = 0.0
        for kunci, biaya in biaya_dasar.items():
            h = harga_terakhir_sampai(harga.get(kunci), t)
            u = unit.get(kunci)
            if h is not None and u is not None:
                if info_produk.get(kunci, {}).get("mata_uang") == "USD":
                    k = harga_terakhir_sampai(kurs, t)
                    h = h * k if k else None
            nilai += u * h if (h is not None and u is not None) else biaya
        keluar.append({"tgl": tgl_tgl(t), "nilai": nilai, "setor": setor})
    return keluar


class Repo:
    def __init__(self, db=None):
        if db is None:
            from backend.db import koneksi as kdb
            db = kdb.koneksi()
        self.db = db

    def daftar_portofolio(self):
        return list(self.db[KOLEKSI_PORTO].find({}))

    def migrasi_pengingat(self):
        diubah = 0
        for p in self.db[KOLEKSI_PORTO].find({}):
            if "pengingat_setoran" not in p:
                self.db[KOLEKSI_PORTO].replace_one({"_id": p["_id"]}, {**p, "pengingat_setoran": False})
                diubah += 1
        return diubah

    def pastikan_default(self):
        if self.db[KOLEKSI_PORTO].find_one({}) is None:
            self.db[KOLEKSI_PORTO].insert_one({"_id": baru_id(), "nama": "Pertumbuhan", "target": "pertumbuhan_saham", "tanggal_mulai": tgl_teks(date.today()), "pengingat_setoran": False,
                                               "setoran_rutin": 0.0, "tanggal_setor": 1, "aktif": True, "dibuat": datetime.now()})
        self.migrasi_pengingat()
        return self.daftar_portofolio()

    def simpan_portofolio(self, data, pid=None):
        v = validasi_portofolio(data)
        if pid is None:
            dok = {"_id": baru_id(), **v, "dibuat": datetime.now()}
            self.db[KOLEKSI_PORTO].insert_one(dok)
            return dok
        lama = self.db[KOLEKSI_PORTO].find_one({"_id": pid})
        if lama is None:
            raise KeyError("portofolio tidak ditemukan")
        self.db[KOLEKSI_PORTO].replace_one({"_id": pid}, {**lama, **v, "diubah": datetime.now()})
        return {**lama, **v}

    def transaksi(self, pid):
        return sorted(self.db[KOLEKSI_TRX].find({"portofolio_id": pid}), key=lambda x: (x["tanggal"], str(x.get("dibuat"))))

    def log(self, tid, aksi, sebelum, sesudah):
        self.db[KOLEKSI_LOG].insert_one({"_id": baru_id(), "transaksi_id": tid, "waktu": datetime.now(), "aksi": aksi, "sebelum": sebelum, "sesudah": sesudah})

    def tambah(self, data):
        if self.db[KOLEKSI_PORTO].find_one({"_id": data.get("portofolio_id")}) is None:
            raise KeyError("portofolio tidak ditemukan")
        v = validasi_transaksi(data)
        dok = {"_id": baru_id(), **v, "dibuat": datetime.now()}
        self.db[KOLEKSI_TRX].insert_one(dok)
        self.log(dok["_id"], "tambah", None, {k: x for k, x in dok.items() if k != "_id"})
        return dok

    def ubah(self, tid, data):
        lama = self.db[KOLEKSI_TRX].find_one({"_id": tid})
        if lama is None:
            raise KeyError("transaksi tidak ditemukan")
        v = validasi_transaksi({**data, "portofolio_id": lama["portofolio_id"]})
        baru = {**lama, **v, "diubah": datetime.now()}
        self.db[KOLEKSI_TRX].replace_one({"_id": tid}, baru)
        self.log(tid, "ubah", {k: x for k, x in lama.items() if k != "_id"}, {k: x for k, x in baru.items() if k != "_id"})
        return baru

    def hapus(self, tid):
        lama = self.db[KOLEKSI_TRX].find_one({"_id": tid})
        if lama is None:
            raise KeyError("transaksi tidak ditemukan")
        self.db[KOLEKSI_TRX].delete_one({"_id": tid})
        self.log(tid, "hapus", {k: x for k, x in lama.items() if k != "_id"}, None)
        return lama

    def riwayat(self, tid):
        return sorted(self.db[KOLEKSI_LOG].find({"transaksi_id": tid}), key=lambda x: x["waktu"])

    def hapus_portofolio(self, pid):
        porto = self.db[KOLEKSI_PORTO].find_one({"_id": pid})
        if porto is None:
            raise KeyError("portofolio tidak ditemukan")
        if len(self.daftar_portofolio()) <= 1:
            raise ValueError("minimal harus ada satu portofolio; ubah saja pengaturannya kalau mau memulai dari awal")
        transaksi = self.transaksi(pid)
        for t in transaksi:
            self.db[KOLEKSI_TRX].delete_one({"_id": t["_id"]})
            self.log(t["_id"], "hapus", {k: x for k, x in t.items() if k != "_id"}, None)
        self.db[KOLEKSI_PORTO].delete_one({"_id": pid})
        return {"nama": porto["nama"], "transaksi_dihapus": len(transaksi)}


def _seri_rd(db, fid):
    x = pd.DataFrame(list(db.rd_nav.find({"fund": {"$in": [fid, str(fid)]}}, {"_id": 0})))
    if x.empty:
        return pd.Series(dtype=float)
    x["tgl"] = pd.to_datetime(x["tgl"])
    return x.set_index("tgl")["nav"].astype(float).sort_index()


def _seri_pasar(tipe, kode, ada_emas):
    from backend.db import data as dt
    from backend.db import harga as hg
    if tipe == "etf":
        for nama in (f"etf_emas/{kode}", f"etf/{kode}"):
            if dt.ada(nama):
                return dt.baca(nama)["close"].dropna().astype(float)
        return pd.Series(dtype=float)
    try:
        return hg.saham(kode)["close"].dropna().astype(float)
    except Exception:
        return pd.Series(dtype=float)


def info_dan_harga(transaksi, db=None):
    from backend.app.services import reksadana as rdn
    from backend.db import data as dt
    from backend.db import koneksi as kdb
    from backend.ingest import etf_emas as ee
    db = db if db is not None else kdb.koneksi()
    daftar = {str(x["id"]): x for x in rdn.daftar()["data"]}
    emas = set((dt.baca_hasil("etf_emas_ringkas") or {}).get("etf") or {})
    info, harga = {}, {}
    for tr in transaksi:
        kunci = (tr["tipe_produk"], tr["produk"])
        if kunci in info:
            continue
        if tr["tipe_produk"] == "rd":
            x = daftar.get(str(tr["produk"]), {})
            info[kunci] = {"mata_uang": x.get("mata_uang", "IDR"), "nama": x.get("nama")}
            harga[kunci] = _seri_rd(db, int(tr["produk"]) if str(tr["produk"]).isdigit() else tr["produk"])
        else:
            info[kunci] = {"emas": tr["produk"] in emas or tr["produk"] in ee.UTAMA, "mata_uang": "IDR"}
            harga[kunci] = _seri_pasar(tr["tipe_produk"], tr["produk"], info[kunci]["emas"])
    kurs = dt.baca("kurs/USD")["close"].dropna().astype(float) if dt.ada("kurs/USD") else pd.Series(dtype=float)
    return info, harga, kurs


def _seri_proxy():
    from backend.db import data as dt
    kurs = dt.baca("kurs/USD")["close"].dropna().astype(float)

    def ke_rupiah(s):
        k = kurs.reindex(s.index.union(kurs.index)).ffill().reindex(s.index)
        return (s * k).dropna()

    hasil = {}
    if dt.ada("indeks/JKII"):
        hasil["lokal"] = dt.baca("indeks/JKII")["close"].dropna().astype(float)
    if dt.ada("indeks_luar/gl_msci_world_islamic"):
        hasil["global"] = ke_rupiah(dt.baca("indeks_luar/gl_msci_world_islamic")["close"].dropna().astype(float))
    if dt.ada("pasar_panjang/emas_usd"):
        hasil["emas"] = ke_rupiah(dt.baca("pasar_panjang/emas_usd")["close"].dropna().astype(float))
    return hasil


def pembanding(transaksi, target_kode, nilai_sekarang, hari_ini, db=None):
    from backend.db import koneksi as kdb
    db = db if db is not None else kdb.koneksi()
    arus = [(t["tanggal"], t["nominal"] if t["jenis"] == "beli" else -t["nominal"]) for t in transaksi]
    out = {"campuran": None, "uji_maju": None}
    bobot = TARGET.get(target_kode) or {}
    if bobot and arus:
        try:
            s = simulasi_seri(arus, _seri_proxy(), bobot, hari_ini)
            if s["tercakup"] > 0:
                out["campuran"] = {"nilai": s["nilai"], "selisih": nilai_sekarang - s["nilai"], "label": "Kalau setoran yang sama masuk ke campuran target (indeks harga: JII, saham syariah global, emas; tanpa dividen dan biaya; setoran terbaru yang belum punya data indeks dihitung sebesar nominalnya)", "cakupan": s["tercakup"] / sum(abs(a) for _, a in arus)}
        except Exception as e:
            out["campuran"] = {"galat": f"{type(e).__name__}: {str(e)[:80]}"}
    for kode, kunci in (("h35", "Uji maju H35"), ("h37", "Uji maju H37")):
        dok = list(db[f"paper_{kode}_ekuitas"].find({}, {"tgl": 1, "nilai": 1}))
        if not dok or not arus:
            continue
        deret = pd.Series({pd.Timestamp(x["tgl"]): float(x["nilai"]) for x in dok}).sort_index()
        modal = deret.iloc[0]
        indeks = deret / modal
        s = simulasi_seri(arus, {"x": indeks}, {"x": 1.0}, hari_ini)
        if s["tercakup"] > 0:
            out["uji_maju"] = out["uji_maju"] or []
            out["uji_maju"].append({"kode": kode.upper(), "nama": kunci, "nilai": s["nilai"], "selisih": nilai_sekarang - s["nilai"], "cakupan": s["tercakup"] / sum(abs(a) for _, a in arus)})
    return out


def analisis(pid, hari_ini=None, db=None, repo=None, tanggal_acuan=None):
    repo = repo or Repo(db)
    porto = repo.db[KOLEKSI_PORTO].find_one({"_id": pid})
    if porto is None:
        raise KeyError("portofolio tidak ditemukan")
    return analisis_dari(porto, repo.transaksi(pid), tanggal_acuan or hari_ini, repo.db)


def analisis_dari(porto, transaksi, hari_ini=None, db=None, info=None, harga=None, kurs=None):
    hari_ini = pd.Timestamp(hari_ini or date.today()).normalize()
    if info is None:
        info, harga, kurs = info_dan_harga(transaksi, db)
    baris, produk = valuasi(transaksi, info, harga, kurs, hari_ini)
    total = ringkasan_total(produk, transaksi, hari_ini)
    nilai_kaki = {}
    for p in produk:
        nilai_kaki[p["kaki"]] = nilai_kaki.get(p["kaki"], 0.0) + (p["nilai"] or 0.0)
    target = TARGET.get(porto["target"], {})
    alok = alokasi_vs_target(nilai_kaki, target, hari_ini.month == 12)
    return bersih({"portofolio": porto, "nama_target": NAMA_TARGET.get(porto["target"]), "ringkasan": total, "produk": produk, "alokasi": alok, "transaksi": baris,
                   "menunggu_nav": [b["_id"] for b in baris if b["status_unit"] == "menunggu_nav"], "deret": deret_waktu(baris, harga, kurs, info, hari_ini),
                   "pembanding": pembanding(transaksi, porto["target"], total["nilai"], hari_ini, db), "hari_ini": tgl_tgl(hari_ini)})


def ada_beli_bulan_ini(db, pid, hari_ini):
    awal = tgl_teks(pd.Timestamp(hari_ini).replace(day=1))
    return any(x.get("jenis") == "beli" and x.get("tanggal", "") >= awal for x in db[KOLEKSI_TRX].find({"portofolio_id": pid}))


def ringkas_untuk_cek(db, hari_ini):
    hasil = []
    for p in db[KOLEKSI_PORTO].find({"aktif": True}):
        if not p.get("pengingat_setoran", False):
            continue
        hasil.append({"id": p["_id"], "nama": p["nama"], "setoran_rutin": p.get("setoran_rutin") or 0.0, "tanggal_setor": p.get("tanggal_setor") or 1,
                      "pengingat_setoran": True, "ada_beli_bulan_ini": ada_beli_bulan_ini(db, p["_id"], hari_ini)})
    return hasil


def cari_produk(q="", batas=30, db=None):
    from backend.app.services import belanja as bl
    from backend.app.services import reksadana as rdn
    from backend.db import data as dt
    from backend.db import koneksi as kdb
    from backend.ingest import etf_emas as ee
    db = db if db is not None else kdb.koneksi()
    q = str(q or "").strip().lower()
    prioritas = set()
    try:
        for g in bl.pertumbuhan(None, 1_000_000, 0, "saham").get("grup", []):
            prioritas |= {str(p["id"]) for p in g["produk"] if p.get("tipe") == "rd"}
    except Exception:
        prioritas = set()
    hasil = []
    for x in rdn.daftar()["data"]:
        hasil.append({"tipe_produk": "rd", "produk": str(x["id"]), "nama": x["nama"], "mata_uang": x.get("mata_uang"), "kategori": x.get("kategori"), "prioritas": str(x["id"]) in prioritas,
                      "platform": [p["kode"] for p in x.get("platform") or []]})
    emas = set((dt.baca_hasil("etf_emas_ringkas") or {}).get("etf") or {})
    for e in db.rd_etf.find({}):
        kode = e.get("kode")
        if kode:
            hasil.append({"tipe_produk": "etf", "produk": kode, "nama": f"{kode} · {e.get('nama')}", "mata_uang": "IDR", "kategori": "etf emas" if kode in emas else "etf", "prioritas": kode in ee.UTAMA, "platform": []})
    for t in dt.baca_daftar("syariah_tickers"):
        kode = str(t).removesuffix(".JK")
        hasil.append({"tipe_produk": "saham", "produk": kode, "nama": kode, "mata_uang": "IDR", "kategori": "saham", "prioritas": False, "platform": []})
    if q:
        hasil = [x for x in hasil if q in x["nama"].lower() or q in str(x["produk"]).lower()]
    hasil.sort(key=lambda x: (not x["prioritas"], x["tipe_produk"] != "rd", x["nama"]))
    return bersih(hasil[:batas])


def isi_dari_belanja(pid, apps=None, hari_ini=None, db=None, repo=None, setoran=None):
    from backend.app.services import belanja as bl
    repo = repo or Repo(db)
    porto = repo.db[KOLEKSI_PORTO].find_one({"_id": pid})
    if porto is None:
        raise KeyError("portofolio tidak ditemukan")
    gaya = "emas" if porto["target"] == "pertumbuhan_emas" else "saham"
    setoran = float(setoran or porto.get("setoran_rutin") or 0.0)
    if setoran <= 0:
        return {"ada": False, "alasan": "Isi nominal setoran bulan ini dulu supaya daftar belanja bisa dihitung.", "draf": []}
    b = bl.pertumbuhan(apps, setoran, 0, gaya, hari_ini)
    if not b.get("ada"):
        return {"ada": False, "alasan": "Daftar belanja belum tersedia.", "draf": []}
    tanggal = tgl_teks(hari_ini or date.today())
    draf = []
    for g in b["grup"]:
        for p in g["produk"]:
            if not p.get("nilai"):
                continue
            if p["tipe"] == "etf":
                if not p.get("lot"):
                    continue
                fee = (p.get("fee") or FEE_DEFAULT.get(g["nama"], 0.0)) or 0.0
                dasar = p["lot"] * LOT * p["harga"]
                draf.append({"portofolio_id": pid, "tanggal": tanggal, "jenis": "beli", "tipe_produk": "etf", "produk": p["kode"], "nama": f"{p['kode']} · {p['nama']}", "aplikasi": g["nama"],
                             "lot": p["lot"], "harga": p["harga"], "biaya": round(dasar * fee), "nominal": round(dasar * (1 + fee)), "catatan": "dari daftar belanja"})
            else:
                draf.append({"portofolio_id": pid, "tanggal": tanggal, "jenis": "beli", "tipe_produk": "rd", "produk": str(p["id"]), "nama": p["nama"], "aplikasi": g["nama"],
                             "nominal": round(p["nilai"]), "biaya": 0, "catatan": "dari daftar belanja"})
    return bersih({"ada": True, "draf": draf, "peringatan": b.get("peringatan", [])})
