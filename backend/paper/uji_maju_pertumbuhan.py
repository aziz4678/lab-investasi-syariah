import sys
from datetime import date, datetime

import pandas as pd

from backend.db import koneksi as d
from backend.ingest import etf_emas as ee
from backend.paper import ketertinggalan as kt
from backend.paper import koreksi_mekanisme as km
from backend.paper import laporan_emas as lem
from backend.paper import mesin_pertumbuhan as mp
from backend.paper import parameter_uji_maju as pu

MODAL = 100_000_000
ATURAN = 'ATURAN UJI MAJU H35 & H37 (dikunci 12 Nov 2026)\n\nUMUM\n- Mulai hari bursa pertama Jan 2027. Modal paper Rp100 jt masing-masing, sekali masuk.\n- Kaki lokal & global = produk yang sama dengan halaman Portofolio Pertumbuhan.\n- Rebalance tiap Desember ke target: H35 50/50, H37 40/40/20.\n- Biaya: komisi broker + pajak jual sesuai konvensi proyek, harga pasar (bukan NAV).\n\nKAKI EMAS (H37)\n1. Pemilihan ETF (per 31 Des 2026, dan setiap rebalance Desember):\n   dari ETF emas syariah dengan AUM >= Rp10 M DAN median nilai transaksi 60 hari >= Rp10 jt,\n   pilih median |premium| 60 hari terendah. Seri: AUM terbesar.\n   (Data sekarang: XGLD. Kode XMES & XBGS wajib diverifikasi sebelum 31 Des.)\n2. Aturan beli/jual emas:\n   - Order per hari maks 20% dari nilai transaksi ETF hari itu (dicicil).\n   - Beli hanya pada hari dengan premium <= +2%. Kalau lebih, hari itu dilewati.\n   - Batas 15 hari bursa: sisa yang belum terbeli dibeli di hari ke-15 di harga mana pun\n     (tetap maks 20% nilai transaksi; sisanya lagi dibeli hari-hari berikutnya), dicatat\n     sebagai kejadian.\n   - Jual saat rebalance: dicicil dengan batas 20% yang sama, tanpa syarat premium.\n   - Dana yang belum terbelanjakan menunggu sebagai kas (tanpa imbal hasil).\n3. Ganti ETF di luar Desember hanya kalau: delisting, AUM < Rp10 M, atau 5 hari bursa\n   berturut tanpa transaksi. Dicatat sebagai kejadian.\n\nYANG DINILAI (uji pelaksanaan, BUKAN bukti edge). Evaluasi pertama Jan 2028.\n1. Selisih return paper vs model backtest periode sama <= 1,5 poin/th (H35 & H37 masing-masing).\n2. Premium bersih emas (rata-rata premium saat beli - rata-rata premium saat jual, tertimbang\n   nilai) <= 1 poin. Selama belum ada jual, laporkan premium saat beli vs premium terkini.\n3. Biaya nyata total vs asumsi backtest (spread 3% pulang-pergi, 0,5%/th): laporkan angkanya.\n4. Laporkan juga: hari tertunda, jumlah kejadian, tracking ETF vs GC=F x kurs.\nGagal 1 atau 2 -> asumsi backtest H37 dinilai terlalu optimistis; H37 tidak dipakai untuk\nuang nyata sampai diuji ulang dengan biaya nyata.\n'
TGL_KUNCI = "2026-11-12"
KONFIG = {
    "h35": {"nama": "Syariah Global 50/50", "bobot": {"lokal": 0.5, "global": 0.5}},
    "h37": {"nama": "Syariah Global + Emas 40/40/20", "bobot": {"lokal": 0.4, "global": 0.4, "emas": 0.2}},
}
BAGIAN = ("posisi", "transaksi", "ekuitas", "kejadian")
INDEKS = {"posisi": [("kaki", 1)], "transaksi": [("tgl", 1), ("kaki", 1)], "ekuitas": [("tgl", 1)], "kejadian": [("tgl", 1)]}


def siapkan():
    db = d.koneksi()
    ada = set(db.list_collection_names())
    hasil = {}
    for kode, k in KONFIG.items():
        for b in BAGIAN:
            nama = f"paper_{kode}_{b}"
            if nama not in ada:
                db.create_collection(nama)
            db[nama].create_index(INDEKS[b])
        status = f"paper_{kode}_status"
        if status not in ada:
            db.create_collection(status)
        if not db[status].find_one({"_id": "status"}):
            db[status].insert_one({"_id": "status", "kode": kode.upper(), "nama": k["nama"], "bobot": k["bobot"], "modal": MODAL,
                                   "aktif": False, "dikunci": False, "draf": True, "mulai_rencana": "hari bursa pertama Jan 2027",
                                   "evaluasi_pertama": "Jan 2028", "dibuat": datetime.now()})
        hasil[kode] = {c: db[c].count_documents({}) for c in [status] + [f"paper_{kode}_{b}" for b in BAGIAN]}
    return hasil


def kunci():
    db = d.koneksi()
    siapkan()
    for kode in KONFIG:
        st = db[f"paper_{kode}_status"]
        if st.find_one({"_id": "status"}).get("dikunci"):
            print(f"{kode.upper()} sudah dikunci, tidak ditimpa.")
            continue
        st.update_one({"_id": "status"}, {"$set": {"dikunci": True, "draf": False, "aktif": False, "tgl_kunci": TGL_KUNCI, "dikunci_pada": datetime.now(),
                                                   "aturan": ATURAN, "aktif_otomatis": "hari bursa pertama Jan 2027"}})
        print(f"{kode.upper()} dikunci {TGL_KUNCI}, aktif=False")
    print(ATURAN)


KOLEKSI_BEKU = "produk_uji_maju_beku"
ID_RESMI = "resmi"
ID_LAMA = "produk_lama"
ID_LAMA_ASAL = "h35_h37"
TGL_BEKU = "2026-11-15"
BAGIAN_LAMA = ("transaksi", "kejadian", "ekuitas")
AWALAN_L25 = "lokal_25"
CATATAN_L25 = "jalur pembanding lokal_25 (info, observasi H38), bukan hasil resmi"
AWALAN_BTC5 = "btc_5"
CATATAN_BTC5 = "jalur pembanding btc_5 (info, H39 lolos), bukan hasil resmi"


def _produk(x):
    if str(x["id"]) == mp.ID_SPUS:
        return {"id": mp.ID_SPUS, "nama": x["nama"], "mu": "USD", "jenis": "spus", "fee": mp.FEE_SPUS}
    return {"id": int(x["id"]), "nama": x["nama"], "mu": x["mata_uang"]}


def produk_langsung():
    from backend.app.services import pertumbuhan as pt
    isi = pt.rencana(1_000_000, 0, "semua")["isi"]
    return {k: [_produk(x) for x in isi[k]] for k in ("lokal", "global")}


def _baca_beku(db, kunci):
    beku = db[KOLEKSI_BEKU].find_one({"_id": kunci})
    return None if not beku else {k: beku[k] for k in ("lokal", "global")}


def produk_halaman():
    db = d.koneksi()
    return _baca_beku(db, ID_RESMI) or _baca_beku(db, ID_LAMA_ASAL) or produk_langsung()


def produk_lama():
    db = d.koneksi()
    return _baca_beku(db, ID_LAMA) or _baca_beku(db, ID_LAMA_ASAL)


def bekukan(db=None):
    db = d.koneksi() if db is None else db
    if db[KOLEKSI_BEKU].find_one({"_id": ID_LAMA_ASAL}):
        return False
    db[KOLEKSI_BEKU].insert_one({"_id": ID_LAMA_ASAL, **produk_langsung(), "dibekukan": datetime.now(),
                                 "alasan": "isi halaman Portofolio Pertumbuhan per 15 Nov 2026 sebelum aturan pemilihan baru; uji maju tidak mengikuti perubahan pemilihan halaman"})
    km.pastikan(db)
    return True


def bekukan_resmi(db=None):
    db = d.koneksi() if db is None else db
    if db[KOLEKSI_BEKU].find_one({"_id": ID_RESMI}):
        return False
    lama = db[KOLEKSI_BEKU].find_one({"_id": ID_LAMA_ASAL})
    if lama is None:
        raise RuntimeError("snapshot lama belum ada, jalankan bekukan() dulu")
    if not db[KOLEKSI_BEKU].find_one({"_id": ID_LAMA}):
        db[KOLEKSI_BEKU].insert_one({**{k: v for k, v in lama.items() if k != "_id"}, "_id": ID_LAMA, "salinan_dari": ID_LAMA_ASAL, "tgl": TGL_BEKU,
                                     "catatan": "jalur pembanding, dihitung paralel, bukan hasil resmi"})
    kini = produk_langsung()
    from backend.app.services import belanja as bl
    kode_emas = bl.etf_terpilih()[0]
    db[KOLEKSI_BEKU].insert_one({"_id": ID_RESMI, **kini, "tgl": TGL_BEKU, "dibekukan": datetime.now(), "emas_halaman": kode_emas,
                                 "catatan_emas": "kaki emas tidak dibekukan di sini: ETF dipilih aturan uji maju terkunci (hari bursa terakhir Nov 2026)",
                                 "alasan": "produk uji maju = produk halaman Portofolio Pertumbuhan semua per 15 Nov 2026, beku sampai evaluasi Jan 2028"})
    km.pastikan(db)
    return True


def simpan(db, kode, m):
    for nama, daftar in (("transaksi", m.transaksi), ("kejadian", m.kejadian), ("ekuitas", m.ekuitas)):
        for x in daftar:
            db[f"paper_{kode}_{nama}"].replace_one({"_id": x["_id"]}, x, upsert=True)
    for kunci, u in m.st["unit"].items():
        kaki = "emas" if kunci.startswith("etf:") else next((k for k, p in m.produk_semua() if f"rd:{p['id']}" == kunci), None)
        db[f"paper_{kode}_posisi"].replace_one({"_id": kunci}, {"_id": kunci, "kaki": kaki, "unit": u, "diubah": datetime.now()}, upsert=True)
    db[f"paper_{kode}_posisi"].replace_one({"_id": "kas"}, {"_id": "kas", "kaki": "kas", "unit": m.st["kas"], "diubah": datetime.now()}, upsert=True)
    pilih = {"mesin": m.st, "aktif": bool(m.st["aktif"]), "terakhir_diproses": m.st["terakhir"], "etf_emas": m.st["etf"]}
    db[f"paper_{kode}_status"].update_one({"_id": "status"}, {"$set": pilih})


def simpan_jalur(db, awalan, catatan, kode, m):
    for nama in BAGIAN_LAMA:
        for x in getattr(m, nama):
            db[f"{awalan}_{nama}"].replace_one({"_id": f"{kode}|{x['_id']}"}, {**x, "_id": f"{kode}|{x['_id']}", "kode": kode}, upsert=True)
    db[f"{awalan}_status"].replace_one({"_id": kode}, {"_id": kode, "mesin": m.st, "aktif": bool(m.st["aktif"]), "terakhir_diproses": m.st["terakhir"], "diubah": datetime.now(),
                                                    "bobot": m.bobot, "catatan": catatan}, upsert=True)


def simpan_lama(db, kode, m):
    simpan_jalur(db, "produk_lama", "jalur pembanding produk_lama, bukan hasil resmi", kode, m)


def produk_lokal_25():
    return produk_halaman()


def jalankan_jalur(db, data, prm, sekarang, st_resmi, awalan, catatan, produk_fn, bobot=None):
    for kode in KONFIG:
        dok = db[f"{awalan}_status"].find_one({"_id": kode}) or {}
        st = dok.get("mesin") or mp.keadaan_baru()
        if kode == "h37" and not (st["pilih_awal"] or {}).get("terpilih"):
            st["pilih_awal"] = st_resmi[kode]["pilih_awal"]
        if sekarang <= prm["mulai"]:
            db[f"{awalan}_status"].replace_one({"_id": kode}, {"_id": kode, "mesin": st, "aktif": False, "diubah": datetime.now(), "bobot": (bobot or {}).get(kode), "catatan": catatan}, upsert=True)
            continue
        if st["produk"] is None:
            st["produk"] = produk_fn()
        m = mp.Mesin(kode, data, state=st, mulai=prm["mulai"], rebalance_pertama=prm["rebalance_pertama"], bobot=None if bobot is None else bobot[kode])
        m.jalan([x for x in data.hari if x < sekarang and x >= prm["mulai"] and (not st["terakhir"] or x > pd.Timestamp(st["terakhir"]))])
        simpan_jalur(db, awalan, catatan, kode, m)
        print(f"{kode.upper()} {awalan} (pembanding): {len(m.transaksi)} transaksi, {len(m.kejadian)} kejadian, {len(m.ekuitas)} hari baru, terakhir {st['terakhir']}")


def jalankan_lama(db, data, prm, sekarang, st_resmi):
    jalankan_jalur(db, data, prm, sekarang, st_resmi, "produk_lama", "jalur pembanding produk_lama, bukan hasil resmi", produk_lama)


def jalankan_lokal_25(db, data, prm, sekarang, st_resmi):
    jalankan_jalur(db, data, prm, sekarang, st_resmi, AWALAN_L25, CATATAN_L25, produk_lokal_25, mp.BOBOT_LOKAL_25)


def jalankan_btc_5(db, data, prm, sekarang, st_resmi):
    jalankan_jalur(db, data, prm, sekarang, st_resmi, AWALAN_BTC5, CATATAN_BTC5, produk_halaman, mp.BOBOT_BTC_5)


def harian(hari_ini=None):
    db = d.koneksi()
    sekarang = pd.Timestamp(hari_ini or date.today()).normalize()
    dok = {k: db[f"paper_{k}_status"].find_one({"_id": "status"}) for k in KONFIG}
    if not all(x and x.get("dikunci") for x in dok.values()):
        print("aturan belum dikunci, tidak melakukan apa-apa")
        return
    prm = pu.verifikasi(db)
    km.pastikan(db)
    if sekarang < prm["mulai"] - pd.Timedelta(days=1):
        print(f"{sekarang:%Y-%m-%d}: belum waktunya (pilih ETF emas di hari bursa terakhir Nov 2026, mesin aktif {prm["mulai"]:%Y-%m-%d})")
        return
    data = mp.DataNyata()
    for kode in KONFIG:
        st0 = dok[kode].get("mesin") or {}
        akhir0 = pd.Timestamp(st0["terakhir"]) if st0.get("terakhir") else prm["mulai"] - pd.Timedelta(days=1)
        tunggakan = kt.hari_tertinggal([x for x in data.hari if x >= prm["mulai"]], akhir0, sekarang - pd.Timedelta(days=1))
        if kt.terlalu_jauh(tunggakan):
            raise SystemExit(kt.pesan_tolak(f"uji maju {kode.upper()}", tunggakan))
    st_resmi = {}
    for kode in KONFIG:
        st = dok[kode].get("mesin") or mp.keadaan_baru()
        st_resmi[kode] = st
        if kode == "h37" and (st["pilih_awal"] is None or not st["pilih_awal"].get("terpilih")):
            sel = ee.pilih_awal(ee.seleksi(data.frames(), {k: data.aum(k, prm["tgl_pilih"]) for k in data.frames()}, data.nama, sampai=prm["tgl_pilih"]))
            sel["dibuat"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            st["pilih_awal"] = sel
            db[f"paper_{kode}_status"].update_one({"_id": "status"}, {"$set": {"pilih_etf_awal": sel["terpilih"], "pilih_etf_tier": sel["tier"], "pilih_etf_alasan": sel["alasan_pilih"]}})
            print(f"{kode.upper()} pilih ETF emas awal: {sel['terpilih']} ({sel['tier']}): {sel['alasan_pilih']}")
        if sekarang <= prm["mulai"]:
            db[f"paper_{kode}_status"].update_one({"_id": "status"}, {"$set": {"mesin": st}})
            continue
        if st["produk"] is None:
            st["produk"] = produk_halaman()
        m = mp.Mesin(kode, data, state=st, mulai=prm["mulai"], rebalance_pertama=prm["rebalance_pertama"])
        m.jalan([x for x in data.hari if x < sekarang and x >= prm["mulai"] and (not st["terakhir"] or x > pd.Timestamp(st["terakhir"]))])
        simpan(db, kode, m)
        if kode == "h37":
            try:
                print("laporan emas H37:", lem.simpan(db, data))
            except Exception as e:
                print(f"laporan emas H37 gagal: {type(e).__name__}: {e}")
        print(f"{kode.upper()}: {len(m.transaksi)} transaksi, {len(m.kejadian)} kejadian, {len(m.ekuitas)} hari baru, terakhir {st['terakhir']}")
    try:
        jalankan_lama(db, data, prm, sekarang, st_resmi)
    except Exception as e:
        print(f"jalur pembanding produk_lama gagal (tidak memengaruhi hasil resmi): {type(e).__name__}: {e}")
    try:
        jalankan_lokal_25(db, data, prm, sekarang, st_resmi)
    except Exception as e:
        print(f"jalur pembanding lokal_25 gagal (tidak memengaruhi hasil resmi): {type(e).__name__}: {e}")
    try:
        jalankan_btc_5(db, data, prm, sekarang, st_resmi)
    except Exception as e:
        print(f"jalur pembanding btc_5 gagal (tidak memengaruhi hasil resmi): {type(e).__name__}: {e}")


AMANDEMEN_1 = {"id": "a1", "tgl": "2026-11-12", "mulai": "2026-12-01",
               "teks": "Tanggal mulai diubah dari hari bursa pertama Jan 2027 menjadi hari bursa pertama Des 2026 (1 Des 2026). Alasan: produk nyata sudah tersedia, menambah data uji maju. "
                       "Dibuat sebelum ada transaksi atau hasil uji maju apa pun. Aturan lain tidak berubah. Rebalance Desember 2026 dilewati (baru masuk); rebalance pertama Desember 2027. "
                       "Pemilihan ETF emas pertama: per hari bursa terakhir Nov 2026 (bukan 31 Des). Evaluasi pertama tetap Jan 2028 (13 bulan data). "
                       "Setelah amandemen ini teks aturan tidak boleh diubah lagi; hasil uji kering (simulasi mulai 2 Nov) hanya untuk memperbaiki bug mesin, bukan mengubah aturan."}


AMANDEMEN_2 = {"id": "a2", "tgl": "2026-11-14", "mulai": "2026-12-01",
               "teks": "Amandemen a2 (hanya mekanisme eksekusi dan data; bobot, strategi, batas 20% nilai transaksi, batas premium +2%, rem 15 hari tidak berubah). "
                       "(a) Premium keputusan beli emas = premium sejajar: close ETF dua hari bursa sebelum hari eksekusi (T-2) dibanding NAV berlabel T-1, yaitu NAV yang mencerminkan hari harga yang sama "
                       "(NAV berlabel T mencerminkan emas T-1 dan baru terbit setelah penutupan T, sehingga NAV berlabel T tidak dipakai untuk keputusan hari T: itu look-ahead). Batas tetap +2%. "
                       "Premium naif lama (close T-1 / NAV berlabel T-1) hanya dicatat sebagai premium_keputusan_naif. "
                       "(b) Batas order 20% nilai transaksi ETF dan rem 15 hari tetap. "
                       "(c) Pemilihan ETF emas awal (hari bursa terakhir Nov 2026): aturan normal bila ada kandidat lolos AUM dan nilai transaksi dengan data premium 60 hari; bila tidak ada, dipilih ETF emas syariah "
                       "lolos filter dengan riwayat data premium terpanjang; bila tidak ada yang lolos filter, riwayat terpanjang tanpa filter. Kaki emas tidak pernah default ke kas. Alasan dicatat di status (pilih_etf_*). "
                       "Pemilihan awal yang gagal diulang tiap hari, tidak macet. "
                       "(d) Data: seri emas GC=F (pasar_panjang/emas_usd, futures bukan spot) masuk jadwal harian; bila seri pembanding model telat lebih dari 2 hari bursa, selisih paper vs model ditandai tidak_valid dan tidak dihitung. "
                       "DITOLAK: batas premium dinamis median 20 hari + 1 poin (mengubah semantik aturan, bukan sekadar mekanisme eksekusi). "
                       "Alasan: investigasi XGLD 2026-11-14 (NAV terlambat satu hari, premium ±1,4% rata-rata dan 40% hari di atas +2%, likuiditas median Rp26 jt/hari, seri emas pembanding berhenti 6 Nov). "
                       "Dibuat sebelum ada transaksi atau hasil uji maju apa pun."}


AMANDEMEN_3 = {"id": "a3", "tgl": "2026-11-15",
               "teks": "Amandemen a3 (hanya instrumen eksekusi; porsi, rebalance Desember, jadwal evaluasi, standar lulus, batas premium, rem 15 hari tidak berubah). "
                       "(a) Produk kaki lokal dan global = produk halaman Portofolio Pertumbuhan 'semua' per 15 Nov 2026, dibekukan sebagai snapshot sampai evaluasi Jan 2028 "
                       "(perubahan halaman setelah 1 Des 2026 tidak masuk uji maju): lokal BNP Paribas Pesona Syariah, Manulife Syariah Sektoral Amanah Kelas A, Sucorinvest Sharia Equity Fund Kelas A; "
                       "global SPUS (ETF saham AS syariah). Kaki emas tetap dipilih aturan terkunci. Frasa 'produk yang sama dengan halaman' di teks aturan digantikan: produk dibekukan per 15 Nov 2026. "
                       "Snapshot lama (BRI Indeks Syariah, BNP Paribas Pesona Syariah, Manulife Syariah Sektoral Amanah Kelas A, Schroder Global Sharia Equity Fund USD) tidak dihapus dan dihitung paralel "
                       "sebagai jalur pembanding produk_lama (koleksi produk_lama_*), bukan hasil resmi. "
                       "(b) Harga SPUS = Close + 70% dividen (pajak 30%) dikali USDIDR terakhir; bila harga SPUS atau kurs hari itu kosong dipakai nilai terakhir dan dicatat sebagai kejadian harga_spus_ffill. "
                       "Biaya transaksi SPUS 0,5% per transaksi (beli dan jual). "
                       "Alasan: instrumen eksekusi diganti ke produk yang benar-benar dibeli user; pilihan itu diputuskan dari data 2020-2026 (uji SPUS vs Schroder, aturan pemilihan lokal), bukan dari data uji maju. "
                       "Dibuat sebelum ada transaksi atau hasil uji maju apa pun (uji maju mulai 1 Des 2026)."}


def amandemen():
    db = d.koneksi()
    for kode in KONFIG:
        st = db[f"paper_{kode}_status"]
        for am in (AMANDEMEN_1, AMANDEMEN_2, AMANDEMEN_3):
            dok = st.find_one({"_id": "status"})
            if any(a.get("id") == am["id"] for a in dok.get("amandemen") or []):
                print(f"{kode.upper()} amandemen {am['id']} sudah tercatat.")
                continue
            if db[f"paper_{kode}_transaksi"].count_documents({}) or db[f"paper_{kode}_posisi"].count_documents({}):
                raise SystemExit(f"{kode.upper()} sudah ada transaksi/posisi, amandemen pra-mulai ditolak")
            perintah = {"$push": {"amandemen": {**am, "dicatat": datetime.now()}}}
            if am["id"] == "a1":
                perintah["$set"] = {"mulai_rencana": "hari bursa pertama Des 2026 (1 Des 2026)", "aktif_otomatis": "hari bursa pertama Des 2026 (1 Des 2026)",
                                    "rebalance_pertama": "Desember 2027", "pilih_etf_pertama": "hari bursa terakhir Nov 2026"}
            st.update_one({"_id": "status"}, perintah)
            print(f"{kode.upper()} amandemen {am['id']} dicatat")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "siapkan":
        for kode, isi in siapkan().items():
            print(kode, isi)
        print("SELESAI")
    elif len(sys.argv) > 1 and sys.argv[1] == "harian":
        harian()
        print("SELESAI")
    elif len(sys.argv) > 1 and sys.argv[1] == "simulasi":
        from backend.paper import simulasi_pertumbuhan as sim
        sim.jalan(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "amandemen":
        amandemen()
        print("SELESAI")
    elif len(sys.argv) > 1 and sys.argv[1] == "kunci":
        kunci()
        print("SELESAI")
    else:
        raise SystemExit("pakai: siapkan | kunci | amandemen | harian | simulasi --mulai YYYY-MM-DD")
