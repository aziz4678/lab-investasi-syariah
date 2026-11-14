import sys
from datetime import datetime

import pandas as pd

from backend.db import koneksi as d
from backend.ingest import etf_emas as ee
from backend.paper import mesin_pertumbuhan as mp

KOLEKSI = "cek_kesehatan"
MULAI = mp.MULAI
TGL_PILIH = pd.Timestamp("2026-11-30")
BATAS_AWAL = pd.Timestamp("2026-12-10")
KODE = ("h35", "h37")
TELAT_EMAS_MAKS = 2
TELAT_SERI_MAKS = 3
TELAT_SERI_GAGAL = 5
HARI_MASUK_MAKS = 2
HARI_REM = 15
JAM_JADWAL = 17
KRITIS = {"uji_maju_harian", "etf_emas_perbarui", "emas_panjang_perbarui", "rd_perbarui", "pasar_perbarui"}
PENGINGAT = [
    ("H11a", "2027-10-21", "keputusan manual Okt 2027, porsi awal maks 10%, peringatan keras H33 berlaku"),
    ("H29", "2027-11-01", "evaluasi 12 bulan, bukan bukti edge"),
    ("H35_H37", "2028-01-14", "evaluasi pertama uji maju (13 bulan data)"),
]
HARI_PENGINGAT = 30


class Ctx:
    def __init__(self, tgl, kalender, sekarang=None, telat_emas=0, langkah=None, pekerjaan=None, seri=None, koleksi=None):
        self.tgl = pd.Timestamp(tgl).normalize()
        self.kalender = sorted(pd.Timestamp(x).normalize() for x in kalender)
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


def cek_belum_mulai(c):
    if c.tgl >= MULAI:
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
    if c.tgl < TGL_PILIH or not c.bursa():
        return []
    st = (c.koleksi.get("h37") or {}).get("status") or {}
    awal = (st.get("mesin") or {}).get("pilih_awal") or {}
    if not awal.get("terpilih"):
        return [hasil("pilih_etf_awal", "gagal", "pilih_awal kosong atau terpilih=None; kaki emas tidak boleh default ke kas")]
    if not st.get("pilih_etf_alasan"):
        return [hasil("pilih_etf_awal", "gagal", f"ETF {awal['terpilih']} terpilih tapi pilih_etf_alasan tidak tercatat")]
    return [hasil("pilih_etf_awal", "ok", f"ETF emas awal {awal['terpilih']} ({st.get('pilih_etf_tier')}): {st['pilih_etf_alasan'][:120]}")]


def cek_transaksi_pertama(c):
    if not (MULAI <= c.tgl <= BATAS_AWAL) or not c.bursa():
        return []
    n = c.hari_ke(MULAI)
    if n < HARI_MASUK_MAKS:
        return [hasil("transaksi_pertama", "ok", f"hari bursa ke-{n} sejak 1 Des, belum jatuh tempo (maks hari ke-{HARI_MASUK_MAKS})")]
    kosong = [k.upper() for k in KODE if not (c.koleksi.get(k) or {}).get("transaksi")]
    if kosong:
        return [hasil("transaksi_pertama", "gagal", f"hari bursa ke-{n}: belum ada transaksi di {', '.join(kosong)}")]
    return [hasil("transaksi_pertama", "ok", f"transaksi pertama H35 dan H37 sudah masuk (hari bursa ke-{n})")]


def cek_batas_20(c):
    if c.tgl < MULAI:
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
    if c.tgl < MULAI:
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
    if c.tgl <= MULAI:
        return []
    ref = c.acuan()
    wajib = [h for h in c.kalender if MULAI <= h < ref]
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
    for kode, tgl, ket in PENGINGAT:
        sisa = (pd.Timestamp(tgl) - c.tgl).days
        if 0 <= sisa <= HARI_PENGINGAT:
            keluar.append(hasil(f"pengingat_{kode}", "info", f"{kode}: evaluasi {tgl} ({sisa} hari lagi), {ket}"))
    return keluar


CEK = [cek_emas_telat, cek_job_jadwal, cek_seri_data, cek_belum_mulai, cek_pilih_etf, cek_transaksi_pertama, cek_batas_20, cek_rem_15, cek_hari_bolong, cek_pengingat]


def jalankan_cek(c):
    keluar = []
    for f in CEK:
        try:
            keluar.extend(f(c))
        except Exception as e:
            keluar.append(hasil(f.__name__.replace("cek_", ""), "gagal", f"pemeriksa error: {type(e).__name__}: {str(e)[:120]}"))
    return keluar


def tgl_terakhir(df):
    return None if df is None or not len(df) else df.index.max()


def bangun_ctx(db, tgl=None, sekarang=None):
    from backend.app.services import sumber_data as sd
    from backend.db import data as dt
    sekarang = sekarang or datetime.now()
    tgl = pd.Timestamp(tgl or sekarang).normalize()
    data = mp.DataNyata()
    ctx = Ctx(tgl, data.hari, sekarang=sekarang)
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
    return ctx


def simpan(db, tgl, daftar):
    for x in daftar:
        t = str(pd.Timestamp(tgl).date())
        db[KOLEKSI].replace_one({"_id": f"{t}|{x['nama_cek']}"}, {"_id": f"{t}|{x['nama_cek']}", "tanggal": t, "dibuat": datetime.now(), **x}, upsert=True)


def jalan():
    db = d.koneksi()
    ctx = bangun_ctx(db)
    daftar = jalankan_cek(ctx)
    simpan(db, ctx.tgl, daftar)
    for x in daftar:
        print(f"[{x['status'].upper():10}] {x['nama_cek']}: {x['pesan']}")
    print("SELESAI")


if __name__ == "__main__":
    jalan()
