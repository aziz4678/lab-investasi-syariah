import re
import sys
from datetime import datetime

import pandas as pd

from backend.core import libur_bursa as lb
from backend.db import koneksi as d
from backend.ingest import etf_emas as ee
from backend.paper import jejak_paper as jp
from backend.paper import ketertinggalan as kt
from backend.paper import mesin_pertumbuhan as mp
from backend.paper import parameter_uji_maju as pu

KOLEKSI = "cek_kesehatan"
MULAI = mp.MULAI
TGL_PILIH = mp.TGL_PILIH
BATAS_AWAL = mp.MULAI + pd.Timedelta(days=pu.HARI_BATAS_AWAL)
KODE = ("h35", "h37")
TELAT_EMAS_MAKS = 2
TELAT_SERI_MAKS = 3
TELAT_SERI_GAGAL = 5
HARI_MASUK_MAKS = 2
HARI_REM = 15
JAM_JADWAL = 17
KRITIS = {"uji_maju_harian", "etf_emas_perbarui", "emas_panjang_perbarui", "rd_perbarui", "pasar_perbarui"}
KET_PENGINGAT = {
    "H11a": "keputusan manual, porsi awal maks 10%, peringatan keras H33 berlaku",
    "H29": "evaluasi 12 bulan, bukan bukti edge",
    "H35": "evaluasi pertama uji maju",
    "H37": "evaluasi pertama uji maju",
}
BULAN = {"jan": 1, "januari": 1, "feb": 2, "februari": 2, "mar": 3, "maret": 3, "apr": 4, "april": 4, "mei": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7,
         "agu": 8, "agt": 8, "agustus": 8, "sep": 9, "sept": 9, "september": 9, "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12}
MULAI_KALENDER = pd.Timestamp("2026-01-01")
HARI_PENGINGAT = 30


def parse_waktu(teks):
    teks = str(teks or "")
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", teks)
    if m:
        t = pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return {"awal": t, "akhir": t, "presisi": "hari", "label": str(t.date())}
    for m in re.finditer(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b", teks):
        bln = BULAN.get(m.group(2).lower())
        if bln:
            t = pd.Timestamp(int(m.group(3)), bln, int(m.group(1)))
            return {"awal": t, "akhir": t, "presisi": "hari", "label": str(t.date())}
    m = re.search(r"\b([A-Za-z]{3,9})(?:/([A-Za-z]{3,9}))?\s+(20\d{2})\b", teks)
    if m:
        b1 = BULAN.get(m.group(1).lower())
        b2 = BULAN.get(m.group(2).lower()) if m.group(2) else b1
        if b1 and b2:
            th = int(m.group(3))
            label = f"{m.group(1)}/{m.group(2)} {th}" if m.group(2) else f"{m.group(1)} {th}"
            return {"awal": pd.Timestamp(th, b1, 1), "akhir": pd.Timestamp(th, b2, 1) + pd.offsets.MonthEnd(0), "presisi": "bulan", "label": label}
    return None


def pengingat_dari_status(db):
    sumber = []
    for kode, koleksi in (("H11a", "batas_paper"), ("H29", "pantau_batas")):
        dok = db[koleksi].find_one({"_id": "h11a_v2" if kode == "H11a" else "h29_v2"}) or {}
        teks = next((x for x in dok.get("keputusan_2027") or [] if "keputusan MANUAL" in x), None)
        sumber.append((kode, f"{koleksi}/{'h11a_v2' if kode == 'H11a' else 'h29_v2'}.keputusan_2027", teks))
    for kode in ("h35", "h37"):
        dok = db[f"paper_{kode}_status"].find_one({"_id": "status"}) or {}
        sumber.append((kode.upper(), f"paper_{kode}_status.evaluasi_pertama", dok.get("evaluasi_pertama")))
    keluar = []
    for kode, asal, teks in sumber:
        w = parse_waktu(teks)
        keluar.append({"kode": kode, "sumber": asal, "teks": teks, **(w or {"awal": None, "akhir": None, "presisi": None, "label": None})})
    return keluar


class Ctx:
    def __init__(self, tgl, kalender=None, sekarang=None, telat_emas=0, langkah=None, pekerjaan=None, seri=None, koleksi=None, pengingat=None, parameter=None, beda_parameter=None, sidik=None, terakhir_proses=None):
        self.tgl = pd.Timestamp(tgl).normalize()
        prm = parameter or {"mulai": MULAI, "tgl_pilih": TGL_PILIH, "batas_awal": BATAS_AWAL}
        self.mulai, self.tgl_pilih, self.batas_awal = prm["mulai"], prm["tgl_pilih"], prm["batas_awal"]
        self.beda_parameter = beda_parameter or []
        self.sidik = sidik
        self.terakhir_proses = terakhir_proses or []
        if kalender is None:
            kalender = lb.hari_bursa_antara(MULAI_KALENDER, self.tgl)
        self.kalender = sorted(pd.Timestamp(x).normalize() for x in kalender)
        self.pengingat = pengingat or []
        self.sekarang = sekarang or datetime.combine(self.tgl.date(), datetime.min.time()).replace(hour=18)
        self.telat_emas = telat_emas
        self.langkah = langkah or []
        self.pekerjaan = pekerjaan or []
        self.seri = seri or {}
        self.koleksi = koleksi or {}

    def bursa(self):
        return self.tgl in set(self.kalender)

    def acuan(self):
        h = [x for x in self.kalender if x <= self.tgl]
        return h[-1] if h else None

    def telat(self, terakhir):
        if terakhir is None:
            return 999
        return len([h for h in self.kalender if pd.Timestamp(terakhir) < h <= self.tgl])

    def hari_ke(self, mulai):
        return len([h for h in self.kalender if mulai <= h <= self.tgl])


def hasil(nama, status, pesan):
    return {"nama_cek": nama, "status": status, "pesan": pesan}


def cek_emas_telat(c):
    n = c.telat_emas
    if n > TELAT_EMAS_MAKS:
        return [hasil("emas_telat", "gagal", f"seri emas pembanding (GC=F) telat {n} hari bursa (> {TELAT_EMAS_MAKS}); selisih paper vs model tidak_valid")]
    return [hasil("emas_telat", "ok", f"seri emas pembanding telat {n} hari bursa")]


def cek_job_jadwal(c):
    if not c.bursa():
        return [hasil("job_jadwal", "ok", "bukan hari bursa, jadwal tidak dicek")]
    if not c.langkah and not c.pekerjaan:
        if c.sekarang.hour < JAM_JADWAL:
            return [hasil("job_jadwal", "ok", "jadwal 17:30 belum jalan")]
        return [hasil("job_jadwal", "gagal", "tidak ada catatan putaran jadwal hari ini")]
    tercatat = {x["jenis"] for x in c.langkah} | {p["jenis"] for p in c.pekerjaan}
    hilang = sorted(KRITIS - tercatat)
    if hilang:
        return [hasil("job_jadwal", "gagal", f"job kritis tidak tercatat di jadwal hari ini: {', '.join(hilang)}")]
    terakhir = {}
    for p in sorted(c.pekerjaan, key=lambda x: str(x.get("mulai"))):
        terakhir[p["jenis"]] = p.get("status")
    for x in c.langkah:
        if x.get("status") in ("gagal", "dilewati"):
            terakhir.setdefault(x["jenis"], x["status"])
    rusak = {j: s for j, s in terakhir.items() if s in ("gagal", "dilewati")}
    kritis = sorted(j for j in rusak if j in KRITIS)
    lain = sorted(j for j in rusak if j not in KRITIS)
    if kritis:
        return [hasil("job_jadwal", "gagal", f"job kritis gagal/dilewati hari ini: {', '.join(kritis)}" + (f"; lainnya: {', '.join(lain)}" if lain else ""))]
    if lain:
        return [hasil("job_jadwal", "peringatan", f"job gagal/dilewati hari ini: {', '.join(lain)}")]
    return [hasil("job_jadwal", "ok", f"{len(terakhir)} job jadwal hari ini tanpa error")]


def cek_seri_data(c):
    lag = {k: c.telat(v) for k, v in c.seri.items()}
    parah = {k: n for k, n in lag.items() if n > TELAT_SERI_GAGAL}
    telat = {k: n for k, n in lag.items() if n > TELAT_SERI_MAKS}
    ringkas = ", ".join(f"{k} {n}" for k, n in sorted(telat.items()))
    if parah:
        return [hasil("seri_data", "gagal", f"seri telat > {TELAT_SERI_GAGAL} hari bursa: {ringkas}")]
    if telat:
        return [hasil("seri_data", "peringatan", f"seri telat > {TELAT_SERI_MAKS} hari bursa: {ringkas}")]
    return [hasil("seri_data", "ok", f"{len(lag)} seri data uji maju segar (telat maks {max(lag.values()) if lag else 0} hari bursa)")]


def cek_parameter_mesin(c):
    if c.beda_parameter:
        return [hasil("parameter_mesin", "gagal", "parameter kode tidak sama dengan status terkunci: " + "; ".join(c.beda_parameter))]
    return [hasil("parameter_mesin", "ok", f"MULAI {c.mulai.date()}, pilih ETF {c.tgl_pilih.date()}, batas awal {c.batas_awal.date()} dibaca dari status terkunci dan sama dengan kode")]


def cek_sidik_paper(c):
    x = c.sidik
    if x is None:
        return [hasil("sidik_paper", "peringatan", "status sidik paper tidak terbaca")]
    if not x.get("snapshot"):
        return [hasil("sidik_paper", "peringatan", "belum ada snapshot sidik paper (job paper_jejak belum pernah jalan)")]
    rusak = list(x.get("live_beda") or []) + [a for a in x.get("anomali") or [] if a not in (x.get("live_beda") or [])]
    if rusak:
        return [hasil("sidik_paper", "gagal", f"dokumen lama koleksi paper append-only berubah/hilang ({len(rusak)}): {'; '.join(rusak[:4])}")]
    if c.bursa() and c.telat(x["snapshot"]) > TELAT_SERI_MAKS:
        return [hasil("sidik_paper", "peringatan", f"snapshot sidik paper terakhir {x['snapshot']} telat {c.telat(x['snapshot'])} hari bursa")]
    return [hasil("sidik_paper", "ok", f"{x['dokumen']} dokumen di {x['koleksi']} koleksi append-only tidak berubah (snapshot {x['snapshot']})")]


def cek_ketertinggalan(c):
    sampai = c.tgl - pd.Timedelta(days=1)
    aliran = []
    for nama, terakhir, mulai in c.terakhir_proses:
        if mulai is not None and c.tgl <= mulai:
            continue
        awal = terakhir if terakhir is not None else (mulai - pd.Timedelta(days=1) if mulai is not None else None)
        aliran.append((nama, kt.hari_tertinggal(c.kalender, awal, sampai) if awal is not None else []))
    if not aliran:
        return []
    jauh = [(n, h) for n, h in aliran if kt.terlalu_jauh(h)]
    if jauh:
        return [hasil("ketertinggalan", "gagal", "; ".join(f"{n} tertinggal {len(h)} hari bursa (> {kt.BATAS_HARI}), tidak diproses otomatis" for n, h in jauh))]
    telat = [(n, h) for n, h in aliran if h]
    if telat:
        return [hasil("ketertinggalan", "peringatan", "; ".join(f"{n} belum memproses {len(h)} hari bursa ({h[0].date()} s/d {h[-1].date()}), akan dikejar berurutan oleh jadwal" for n, h in telat))]
    return [hasil("ketertinggalan", "ok", "paper H11a, H22, dan uji maju H35/H37 sudah memproses semua hari bursa sampai kemarin")]


def cek_belum_mulai(c):
    if c.tgl >= c.mulai:
        return []
    masalah = []
    for k in KODE:
        x = c.koleksi.get(k) or {}
        st = x.get("status")
        if not st:
            masalah.append(f"{k.upper()} status tidak ada")
            continue
        if not st.get("dikunci"):
            masalah.append(f"{k.upper()} aturan tidak terkunci")
        if st.get("aktif"):
            masalah.append(f"{k.upper()} aktif sebelum 1 Des")
        for b, n in (x.get("jumlah") or {}).items():
            if n:
                masalah.append(f"paper_{k}_{b} berisi {n} dokumen")
    if masalah:
        return [hasil("belum_mulai", "gagal", "; ".join(masalah))]
    return [hasil("belum_mulai", "ok", "koleksi paper_h35_* dan paper_h37_* kosong, aktif=False, aturan terkunci")]


def cek_pilih_etf(c):
    if c.tgl < c.tgl_pilih or not c.bursa():
        return []
    st = (c.koleksi.get("h37") or {}).get("status") or {}
    awal = (st.get("mesin") or {}).get("pilih_awal") or {}
    if not awal.get("terpilih"):
        return [hasil("pilih_etf_awal", "gagal", "pilih_awal kosong atau terpilih=None; kaki emas tidak boleh default ke kas")]
    if not st.get("pilih_etf_alasan"):
        return [hasil("pilih_etf_awal", "gagal", f"ETF {awal['terpilih']} terpilih tapi pilih_etf_alasan tidak tercatat")]
    tier = st.get("pilih_etf_tier") or (awal.get("tier"))
    status = "ok" if tier == "normal" else "peringatan"
    return [hasil("pilih_etf_awal", status, f"ETF emas awal {awal['terpilih']} (tingkat {tier}): {st['pilih_etf_alasan'][:120]}")]


def cek_transaksi_pertama(c):
    if not (c.mulai <= c.tgl <= c.batas_awal) or not c.bursa():
        return []
    n = c.hari_ke(c.mulai)
    if n < HARI_MASUK_MAKS:
        return [hasil("transaksi_pertama", "ok", f"hari bursa ke-{n} sejak 1 Des, belum jatuh tempo (maks hari ke-{HARI_MASUK_MAKS})")]
    kosong = [k.upper() for k in KODE if not (c.koleksi.get(k) or {}).get("transaksi")]
    if kosong:
        return [hasil("transaksi_pertama", "gagal", f"hari bursa ke-{n}: belum ada transaksi di {', '.join(kosong)}")]
    return [hasil("transaksi_pertama", "ok", f"transaksi pertama H35 dan H37 sudah masuk (hari bursa ke-{n})")]


def cek_batas_20(c):
    if c.tgl < c.mulai:
        return []
    lebih = []
    n = 0
    for k in KODE:
        for t in (c.koleksi.get(k) or {}).get("transaksi") or []:
            if t.get("kaki") == "emas" and t.get("sisi") == "beli" and not t.get("rebalance"):
                n += 1
                if t.get("pakai_batas") is None or t["pakai_batas"] > 1.0 + 1e-9:
                    lebih.append(f"{k.upper()} {t.get('tgl')} ({t.get('pakai_batas')})")
    if lebih:
        return [hasil("batas_20_persen", "gagal", f"pembelian emas melewati 20% nilai transaksi: {', '.join(lebih[:5])}")]
    return [hasil("batas_20_persen", "ok", f"{n} pembelian emas, semua <= 20% nilai transaksi ETF")]


def cek_rem_15(c):
    if c.tgl < c.mulai:
        return []
    st = (c.koleksi.get("h37") or {}).get("status") or {}
    mesin = st.get("mesin") or {}
    terbuka = [o for o in mesin.get("antrean") or [] if o.get("jenis") == "etf_beli" and o.get("sisa", 0) > 0]
    if not mesin.get("masuk"):
        return [hasil("rem_15_hari", "ok", "H37 belum masuk, rem belum berlaku")]
    if not terbuka:
        return [hasil("rem_15_hari", "ok", "tidak ada order beli emas terbuka")]
    hari = max(o.get("hari", 0) for o in terbuka)
    if hari >= HARI_REM:
        return [hasil("rem_15_hari", "gagal", f"dana emas belum habis di hari ke-{hari} (rem {HARI_REM} hari bursa), sisa Rp{sum(o['sisa'] for o in terbuka):,.0f}")]
    return [hasil("rem_15_hari", "ok", f"order beli emas terbuka hari ke-{hari} dari {HARI_REM}")]


def cek_hari_bolong(c):
    if c.tgl <= c.mulai:
        return []
    ref = c.acuan()
    wajib = [h for h in c.kalender if c.mulai <= h < ref]
    if not wajib:
        return [hasil("hari_bolong", "ok", "belum ada hari yang wajib tercatat")]
    masalah = []
    for k in KODE:
        ada = set((c.koleksi.get(k) or {}).get("ekuitas") or [])
        hilang = [str(h.date()) for h in wajib if str(h.date()) not in ada]
        if hilang:
            masalah.append(f"{k.upper()} bolong {len(hilang)} hari ({', '.join(hilang[:4])})")
    if masalah:
        return [hasil("hari_bolong", "gagal", "; ".join(masalah))]
    return [hasil("hari_bolong", "ok", f"valuasi harian H35 dan H37 lengkap untuk {len(wajib)} hari bursa")]


def cek_pengingat(c):
    keluar = []
    for x in c.pengingat:
        nama = f"pengingat_{x['kode']}"
        if not x.get("awal"):
            keluar.append(hasil(nama, "peringatan", f"{x['kode']}: tanggal evaluasi tidak ditemukan di status terkunci ({x.get('sumber')})"))
            continue
        sisa = (x["awal"] - c.tgl).days
        if c.tgl < x["awal"] - pd.Timedelta(days=HARI_PENGINGAT) or c.tgl > x["akhir"]:
            continue
        ket = KET_PENGINGAT.get(x["kode"], "")
        if x["presisi"] == "hari":
            keluar.append(hasil(nama, "info", f"{x['kode']}: evaluasi {x['label']} ({sisa} hari lagi), {ket}"))
        elif sisa > 0:
            keluar.append(hasil(nama, "info", f"{x['kode']}: evaluasi {x['label']} (mulai {sisa} hari lagi), {ket}"))
        else:
            keluar.append(hasil(nama, "info", f"{x['kode']}: evaluasi {x['label']} (bulan evaluasi berjalan), {ket}"))
    return keluar


def cek_kalender_libur(c):
    kurang = []
    for tahun in (c.tgl.year, c.tgl.year + 1):
        if not lb.tahun_terisi(tahun) and c.tgl >= pd.Timestamp(tahun - 1, 12, 1):
            kurang.append(tahun)
    sementara = [y for y in lb.tahun_sementara() if y >= c.tgl.year and c.tgl >= pd.Timestamp(y - 1, 12, 1)]
    if kurang:
        return [hasil("kalender_libur", "peringatan", f"kalender libur {', '.join(str(x) for x in kurang)} belum diisi (backend/core/libur_bursa.py); cek hari bursa memakai akhir pekan saja untuk tahun itu")]
    if sementara:
        return [hasil("kalender_libur", "info", f"Kalender libur {', '.join(str(y) for y in sementara)} belum diverifikasi ke kalender resmi IDX.")]
    return [hasil("kalender_libur", "ok", f"kalender libur terisi untuk {', '.join(str(y) for y in sorted(lb.LIBUR))}")]


CEK = [cek_parameter_mesin, cek_ketertinggalan, cek_sidik_paper, cek_emas_telat, cek_job_jadwal, cek_seri_data, cek_belum_mulai, cek_pilih_etf, cek_transaksi_pertama, cek_batas_20, cek_rem_15, cek_hari_bolong, cek_pengingat, cek_kalender_libur]


def jalankan_cek(c):
    keluar = []
    for f in CEK:
        try:
            keluar.extend(f(c))
        except Exception as e:
            keluar.append(hasil(f.__name__.replace("cek_", ""), "gagal", f"pemeriksa error: {type(e).__name__}: {str(e)[:120]}"))
    return keluar


def tgl_atau_none(x):
    return pd.Timestamp(x) if x else None


def tgl_terakhir(df):
    return None if df is None or not len(df) else df.index.max()


def bangun_ctx(db, tgl=None, sekarang=None):
    from backend.app.services import sumber_data as sd
    from backend.db import data as dt
    sekarang = sekarang or datetime.now()
    tgl = pd.Timestamp(tgl or sekarang).normalize()
    data = mp.DataNyata()
    try:
        prm = pu.baca(db)
        beda = pu.selisih(prm)
    except Exception as e:
        prm, beda = None, [f"status tidak terbaca: {type(e).__name__}: {str(e)[:100]}"]
    ctx = Ctx(tgl, sekarang=sekarang, pengingat=pengingat_dari_status(db), parameter=prm, beda_parameter=beda)
    try:
        ctx.sidik = jp.status(db, sekarang)
    except Exception:
        ctx.sidik = None
    ctx.telat_emas = ctx.telat(data.emas_usd.index.max())
    seri = {}
    try:
        from backend.paper import uji_maju_pertumbuhan as um
        pr = um.produk_halaman()
        akhir = []
        for k in pr:
            for p in pr[k]:
                s = data.nav(p["id"])
                akhir.append(s.index.max() if len(s) else None)
        seri["NAV RD"] = min([a for a in akhir if a is not None], default=None)
    except Exception:
        seri["NAV RD"] = None
    emas = [tgl_terakhir(df) for k, df in data.etf_df.items() if k in ee.UTAMA]
    seri["ETF emas"] = min([a for a in emas if a is not None], default=None)
    seri["kurs USD"] = data.kurs.index.max() if len(data.kurs) else None
    luar = []
    for k in dt.daftar("etf_luar"):
        luar.append(dt.baca(f"etf_luar/{k}").index.max())
    seri["ETF luar"] = pd.Series(luar).median() if luar else None
    idx = sd.idx_harian_terakhir()
    seri["idx_harian"] = pd.Timestamp(idx) if idx is not None else None
    ctx.seri = seri
    j = db.jadwal_harian.find_one({"_id": str(tgl.date())}) or {}
    ctx.langkah = j.get("langkah") or []
    ctx.pekerjaan = list(db.pekerjaan.find({"oleh": "jadwal", "mulai": {"$gte": datetime.combine(tgl.date(), datetime.min.time())}}, {"jenis": 1, "status": 1, "mulai": 1}))
    koleksi = {}
    for k in KODE:
        koleksi[k] = {
            "status": db[f"paper_{k}_status"].find_one({"_id": "status"}),
            "jumlah": {b: db[f"paper_{k}_{b}"].count_documents({}) for b in ("posisi", "transaksi", "ekuitas", "kejadian")},
            "transaksi": list(db[f"paper_{k}_transaksi"].find({}, {"tgl": 1, "kaki": 1, "sisi": 1, "pakai_batas": 1, "rebalance": 1})),
            "ekuitas": [x["_id"] for x in db[f"paper_{k}_ekuitas"].find({}, {"_id": 1})],
        }
    ctx.koleksi = koleksi
    ctx.terakhir_proses = [("paper H11a", tgl_atau_none((db.paper_status.find_one({"_id": "status"}) or {}).get("tgl_terakhir")), None),
                           ("paper H22", tgl_atau_none((db.paper_h22_status.find_one({"_id": "status"}) or {}).get("tgl_terakhir")), None),
                           ("uji maju H37", tgl_atau_none((((koleksi["h37"]["status"] or {}).get("mesin")) or {}).get("terakhir")), ctx.mulai),
                           ("uji maju H35", tgl_atau_none((((koleksi["h35"]["status"] or {}).get("mesin")) or {}).get("terakhir")), ctx.mulai)]
    return ctx


def simpan(db, tgl, daftar, sumber="manual"):
    for x in daftar:
        t = str(pd.Timestamp(tgl).date())
        db[KOLEKSI].replace_one({"_id": f"{t}|{x['nama_cek']}"}, {"_id": f"{t}|{x['nama_cek']}", "tanggal": t, "dibuat": datetime.now(), "sumber": sumber, **x}, upsert=True)


def sumber_jalan(db):
    p = db.pekerjaan.find_one({"jenis": "cek_kesehatan_uji_maju", "status": "berjalan"}, sort=[("mulai", -1)])
    return "jadwal" if p and p.get("oleh") == "jadwal" else "manual"


def jalan():
    db = d.koneksi()
    ctx = bangun_ctx(db)
    daftar = jalankan_cek(ctx)
    simpan(db, ctx.tgl, daftar, sumber_jalan(db))
    for x in daftar:
        print(f"[{x['status'].upper():10}] {x['nama_cek']}: {x['pesan']}")
    print("SELESAI")


if __name__ == "__main__":
    jalan()
