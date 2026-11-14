import unittest

import pandas as pd

from backend.app.services import portofolio_saya as ps
from backend.paper import cek_kesehatan as ck


class FakeKoleksi:
    def __init__(self):
        self.dok = []

    @staticmethod
    def cocok(d, f):
        return all(d.get(k) == v for k, v in (f or {}).items())

    def find(self, f=None, proj=None):
        return [dict(d) for d in self.dok if self.cocok(d, f)]

    def find_one(self, f=None, *a, **k):
        x = self.find(f)
        return x[0] if x else None

    def insert_one(self, d):
        self.dok.append(dict(d))

    def replace_one(self, f, d):
        for i, x in enumerate(self.dok):
            if self.cocok(x, f):
                self.dok[i] = dict(d)
                return

    def delete_one(self, f):
        for i, x in enumerate(self.dok):
            if self.cocok(x, f):
                del self.dok[i]
                return

    def count_documents(self, f):
        return len(self.find(f))


class FakeDb:
    def __init__(self):
        self.k = {}

    def __getitem__(self, nama):
        return self.k.setdefault(nama, FakeKoleksi())


def seri(mulai, nilai):
    return pd.Series(nilai, index=pd.bdate_range(mulai, periods=len(nilai)), dtype=float)


def trx(**x):
    dasar = {"tanggal": "2026-12-01", "jenis": "beli", "tipe_produk": "rd", "produk": "1", "nama": "RD A", "aplikasi": "Bibit", "nominal": 1_000_000.0, "biaya": 0.0, "unit": None, "harga": None, "lot": None,
             "catatan": "", "kaki": None}
    return {**dasar, **x}


class TesXirr(unittest.TestCase):
    def test_sepuluh_persen(self):
        self.assertAlmostEqual(ps.xirr([("2026-01-01", -100.0), ("2027-01-01", 110.0)]), 0.10, places=4)

    def test_dua_arus(self):
        r = ps.xirr([("2026-01-01", -100.0), ("2026-07-02", -100.0), ("2027-01-01", 230.0)])
        self.assertGreater(r, 0.1)
        self.assertLess(r, 0.3)

    def test_tidak_ada_tanda_berbeda(self):
        self.assertIsNone(ps.xirr([("2026-01-01", -100.0), ("2027-01-01", -50.0)]))
        self.assertIsNone(ps.xirr([("2026-01-01", -100.0)]))


class TesUnit(unittest.TestCase):
    def test_rd_dari_nominal(self):
        u = ps.hitung_unit(trx(nominal=1_000_000.0, biaya=5_000.0), 2_000.0)
        self.assertEqual(u["status"], "ok")
        self.assertAlmostEqual(u["unit"], 497.5)

    def test_rd_menunggu_nav_lalu_terisi(self):
        harga = {("rd", "1"): seri("2026-11-02", [1000.0, 1010.0])}
        info = {("rd", "1"): {"mata_uang": "IDR"}}
        kurs = seri("2026-01-01", [15000.0] * 5)
        t = [{**trx(tanggal="2026-12-15"), "_id": "a"}]
        baris, _ = ps.valuasi(t, info, harga, kurs, "2026-12-16")
        self.assertEqual(baris[0]["status_unit"], "menunggu_nav")
        self.assertIsNone(baris[0]["unit_hitung"])
        harga[("rd", "1")] = seri("2026-11-02", [1000.0] * 40)
        baris2, produk = ps.valuasi(t, info, harga, kurs, "2026-12-16")
        self.assertEqual(baris2[0]["status_unit"], "ok")
        self.assertAlmostEqual(baris2[0]["unit_hitung"], 1000.0)
        self.assertAlmostEqual(produk[0]["nilai"], 1_000_000.0)

    def test_nav_dipakai_hari_berikutnya_bila_tanggal_libur(self):
        s = seri("2026-12-01", [1000.0, 1100.0])
        self.assertEqual(ps.harga_pertama_setelah(s, "2026-11-30"), 1000.0)
        self.assertIsNone(ps.harga_pertama_setelah(s, "2026-12-30"))

    def test_etf_lot(self):
        u = ps.hitung_unit(trx(tipe_produk="etf", produk="XGLD", lot=8.0), None)
        self.assertEqual(u["unit"], 800.0)

    def test_usd_dikali_kurs(self):
        info = {("rd", "2"): {"mata_uang": "USD"}}
        harga = {("rd", "2"): seri("2026-12-01", [10.0] * 10)}
        kurs = seri("2026-12-01", [16000.0] * 10)
        t = [{**trx(tanggal="2026-12-01", produk="2", nominal=1_600_000.0), "_id": "a"}]
        baris, produk = ps.valuasi(t, info, harga, kurs, "2026-12-10")
        self.assertAlmostEqual(baris[0]["unit_hitung"], 10.0)
        self.assertAlmostEqual(produk[0]["nilai"], 1_600_000.0)

    def test_jual_mengurangi_unit(self):
        info = {("etf", "XGLD"): {"emas": True}}
        harga = {("etf", "XGLD"): seri("2026-12-01", [250.0] * 5)}
        t = [{**trx(tipe_produk="etf", produk="XGLD", lot=10.0, nominal=250_000.0), "_id": "a"},
             {**trx(tipe_produk="etf", produk="XGLD", jenis="jual", lot=4.0, nominal=100_000.0, tanggal="2026-12-02"), "_id": "b"}]
        _, produk = ps.valuasi(t, info, harga, seri("2026-01-01", [1.0] * 5), "2026-12-05")
        self.assertAlmostEqual(produk[0]["unit"], 600.0)
        self.assertAlmostEqual(produk[0]["nilai"], 150_000.0)
        self.assertEqual(produk[0]["kaki"], "emas")


class TesRingkasan(unittest.TestCase):
    def test_untung_xirr_belum_cukup_data(self):
        produk = [{"nilai": 1_100_000.0}]
        t = [trx(tanggal="2026-12-01", nominal=1_000_000.0, biaya=2000.0)]
        r = ps.ringkasan_total(produk, t, "2026-12-20")
        self.assertAlmostEqual(r["untung"], 100_000.0)
        self.assertAlmostEqual(r["untung_persen"], 0.1)
        self.assertIsNone(r["xirr"])
        self.assertIn("belum cukup", r["xirr_pesan"])
        self.assertEqual(r["biaya"], 2000.0)

    def test_xirr_tampil_setelah_tiga_bulan(self):
        produk = [{"nilai": 1_100_000.0}]
        t = [trx(tanggal="2026-01-01", nominal=1_000_000.0)]
        r = ps.ringkasan_total(produk, t, "2027-01-01")
        self.assertAlmostEqual(r["xirr"], 0.10, places=3)


class TesAlokasi(unittest.TestCase):
    def test_selisih_dan_saran(self):
        r = ps.alokasi_vs_target({"lokal": 700.0, "global": 300.0}, {"lokal": 0.5, "global": 0.5}, True)
        self.assertEqual(r["total"], 1000.0)
        saran = {x["kaki"]: x for x in r["saran"]}
        self.assertEqual(saran["lokal"]["aksi"], "jual")
        self.assertAlmostEqual(saran["lokal"]["nominal"], 200.0)
        self.assertEqual(saran["global"]["aksi"], "beli")
        self.assertTrue(r["desember"])

    def test_seimbang_tanpa_saran(self):
        r = ps.alokasi_vs_target({"lokal": 505.0, "global": 495.0}, {"lokal": 0.5, "global": 0.5}, False)
        self.assertEqual(r["saran"], [])
        self.assertTrue(r["seimbang"])

    def test_tiga_kaki_dan_target_bebas(self):
        r = ps.alokasi_vs_target({"lokal": 400.0, "global": 400.0}, {"lokal": 0.4, "global": 0.4, "emas": 0.2}, False)
        emas = next(x for x in r["kaki"] if x["kaki"] == "emas")
        self.assertAlmostEqual(emas["selisih_rp"], 160.0)
        bebas = ps.alokasi_vs_target({"lokal": 400.0}, {}, False)
        self.assertEqual(bebas["saran"], [])

    def test_simulasi_seri(self):
        s = seri("2026-12-01", [100.0, 100.0, 110.0, 120.0])
        r = ps.simulasi_seri([("2026-12-01", 1000.0)], {"x": s}, {"x": 1.0}, "2026-12-04")
        self.assertAlmostEqual(r["nilai"], 1200.0)


class TesRepo(unittest.TestCase):
    def setUp(self):
        self.db = FakeDb()
        self.repo = ps.Repo(self.db)
        self.pid = self.repo.pastikan_default()[0]["_id"]

    def isian(self, **x):
        return {"portofolio_id": self.pid, "tanggal": "2026-11-02", "jenis": "beli", "tipe_produk": "rd", "produk": "1", "nama": "RD A", "aplikasi": "Bibit", "nominal": "1000000", "biaya": "0", **x}

    def test_default_dibuat_sekali(self):
        self.assertEqual(len(self.repo.pastikan_default()), 1)
        self.assertEqual(self.repo.daftar_portofolio()[0]["nama"], "Pertumbuhan")

    def test_tambah_ubah_hapus_dengan_log(self):
        t = self.repo.tambah(self.isian())
        self.assertEqual(len(self.repo.transaksi(self.pid)), 1)
        self.repo.ubah(t["_id"], self.isian(nominal="2000000"))
        self.assertEqual(self.repo.transaksi(self.pid)[0]["nominal"], 2_000_000.0)
        self.repo.hapus(t["_id"])
        self.assertEqual(self.repo.transaksi(self.pid), [])
        log = self.repo.riwayat(t["_id"])
        self.assertEqual([x["aksi"] for x in log], ["tambah", "ubah", "hapus"])
        self.assertEqual(log[1]["sebelum"]["nominal"], 1_000_000.0)
        self.assertEqual(log[1]["sesudah"]["nominal"], 2_000_000.0)
        self.assertIsNone(log[2]["sesudah"])

    def test_validasi(self):
        with self.assertRaises(ValueError):
            self.repo.tambah(self.isian(nominal="0"))
        with self.assertRaises(ValueError):
            self.repo.tambah(self.isian(jenis="tukar"))
        with self.assertRaises(ValueError):
            self.repo.tambah(self.isian(tanggal="2099-01-01"))
        with self.assertRaises(ValueError):
            self.repo.tambah(self.isian(tipe_produk="etf", produk="XGLD", nominal="100000"))
        with self.assertRaises(KeyError):
            self.repo.tambah({**self.isian(), "portofolio_id": "tidak-ada"})
        with self.assertRaises(KeyError):
            self.repo.hapus("tidak-ada")

    def test_etf_lot_jadi_unit_dan_nominal_dari_harga(self):
        t = self.repo.tambah(self.isian(tipe_produk="etf", produk="XGLD", nominal="", lot="8", harga="240", biaya="288"))
        self.assertEqual(t["unit"], 800.0)
        self.assertAlmostEqual(t["nominal"], 800 * 240 + 288)

    def test_hapus_portofolio_beserta_transaksi_dan_log(self):
        kedua = self.repo.simpan_portofolio({"nama": "Kedua", "target": "bebas"})
        t1 = self.repo.tambah({**self.isian(), "portofolio_id": kedua["_id"]})
        t2 = self.repo.tambah({**self.isian(nominal="500000"), "portofolio_id": kedua["_id"]})
        aman = self.repo.tambah(self.isian())
        hasil = self.repo.hapus_portofolio(kedua["_id"])
        self.assertEqual((hasil["nama"], hasil["transaksi_dihapus"]), ("Kedua", 2))
        self.assertEqual([p["_id"] for p in self.repo.daftar_portofolio()], [self.pid])
        self.assertEqual(self.repo.transaksi(kedua["_id"]), [])
        self.assertEqual(len(self.repo.transaksi(self.pid)), 1)
        for t in (t1, t2):
            self.assertEqual([x["aksi"] for x in self.repo.riwayat(t["_id"])], ["tambah", "hapus"])
        self.assertEqual([x["aksi"] for x in self.repo.riwayat(aman["_id"])], ["tambah"])

    def test_portofolio_terakhir_dan_tidak_ada_tidak_bisa_dihapus(self):
        with self.assertRaises(ValueError):
            self.repo.hapus_portofolio(self.pid)
        self.assertEqual(len(self.repo.daftar_portofolio()), 1)
        self.repo.simpan_portofolio({"nama": "Kedua", "target": "bebas"})
        with self.assertRaises(KeyError):
            self.repo.hapus_portofolio("tidak-ada")

    def test_portofolio_validasi(self):
        with self.assertRaises(ValueError):
            self.repo.simpan_portofolio({"nama": "x", "pengingat_setoran": True, "tanggal_setor": 31, "setoran_rutin": 100000})
        with self.assertRaises(ValueError):
            self.repo.simpan_portofolio({"nama": "x", "pengingat_setoran": True, "setoran_rutin": 0})
        dok = self.repo.simpan_portofolio({"nama": "Emas", "target": "pertumbuhan_emas", "pengingat_setoran": True, "setoran_rutin": 500000, "tanggal_setor": 5})
        self.assertTrue(dok["pengingat_setoran"])
        self.assertEqual(self.repo.simpan_portofolio({"nama": "Emas2", "target": "bebas"}, dok["_id"])["nama"], "Emas2")

    def test_setoran_dan_tanggal_opsional_saat_pengingat_mati(self):
        dok = self.repo.simpan_portofolio({"nama": "Tidak rutin", "target": "bebas"})
        self.assertFalse(dok["pengingat_setoran"])
        dok2 = self.repo.simpan_portofolio({"nama": "Tidak rutin", "target": "bebas", "tanggal_setor": 99, "setoran_rutin": -5})
        self.assertEqual((dok2["tanggal_setor"], dok2["setoran_rutin"]), (28, 0.0))

    def test_default_dan_migrasi_pengingat_mati(self):
        self.assertFalse(self.repo.daftar_portofolio()[0]["pengingat_setoran"])
        db = FakeDb()
        db["portofolio_saya"].insert_one({"_id": "lama", "nama": "Pertumbuhan", "target": "pertumbuhan_saham", "setoran_rutin": 1_000_000.0, "tanggal_setor": 3, "aktif": True})
        repo = ps.Repo(db)
        self.assertEqual(repo.migrasi_pengingat(), 1)
        self.assertFalse(db["portofolio_saya"].find_one({"_id": "lama"})["pengingat_setoran"])
        self.assertEqual(repo.migrasi_pengingat(), 0)
        self.assertEqual(ps.ringkas_untuk_cek(db, "2026-11-20"), [])


class TesCekSetoran(unittest.TestCase):
    def ctx(self, tgl, porto):
        c = ck.Ctx(tgl, kalender=list(pd.bdate_range("2026-12-01", "2026-12-31")))
        c.portofolio_saya = porto
        return c

    def test_info_bila_lewat_tiga_hari(self):
        p = [{"nama": "Pertumbuhan", "tanggal_setor": 5, "setoran_rutin": 1_000_000.0, "ada_beli_bulan_ini": False}]
        r = ck.cek_setoran_bulan_ini(self.ctx("2026-12-09", p))
        self.assertEqual((r[0]["nama_cek"], r[0]["status"]), ("setoran_bulan_ini", "info"))
        self.assertIn("Pertumbuhan", r[0]["pesan"])

    def test_ok_bila_belum_jatuh_tempo_atau_sudah_beli(self):
        p = [{"nama": "Pertumbuhan", "tanggal_setor": 5, "setoran_rutin": 1_000_000.0, "ada_beli_bulan_ini": False}]
        self.assertEqual(ck.cek_setoran_bulan_ini(self.ctx("2026-12-08", p))[0]["status"], "ok")
        p[0]["ada_beli_bulan_ini"] = True
        self.assertEqual(ck.cek_setoran_bulan_ini(self.ctx("2026-12-20", p))[0]["status"], "ok")

    def test_pengingat_mati_tidak_menghasilkan_teks_belum_setor(self):
        p = [{"nama": "Tidak rutin", "tanggal_setor": 5, "setoran_rutin": 1_000_000.0, "ada_beli_bulan_ini": False, "pengingat_setoran": False}]
        r = ck.cek_setoran_bulan_ini(self.ctx("2026-12-20", p))
        self.assertEqual((r[0]["nama_cek"], r[0]["status"]), ("setoran_bulan_ini", "ok"))
        self.assertNotIn("Belum ada transaksi", r[0]["pesan"])

    def test_ok_tanpa_setoran_rutin_atau_tanpa_portofolio(self):
        self.assertEqual(ck.cek_setoran_bulan_ini(self.ctx("2026-12-20", []))[0]["status"], "ok")
        p = [{"nama": "x", "tanggal_setor": 1, "setoran_rutin": 0.0, "ada_beli_bulan_ini": False}]
        self.assertEqual(ck.cek_setoran_bulan_ini(self.ctx("2026-12-20", p))[0]["status"], "ok")

    def test_ringkas_untuk_cek(self):
        db = FakeDb()
        repo = ps.Repo(db)
        pid = repo.pastikan_default()[0]["_id"]
        self.assertEqual(ps.ringkas_untuk_cek(db, "2026-11-09"), [])
        repo.simpan_portofolio({"nama": "Pertumbuhan", "pengingat_setoran": True, "setoran_rutin": 1_000_000, "tanggal_setor": 5}, pid)
        self.assertFalse(ps.ringkas_untuk_cek(db, "2026-11-09")[0]["ada_beli_bulan_ini"])
        repo.tambah({"portofolio_id": pid, "tanggal": "2026-11-03", "jenis": "beli", "tipe_produk": "rd", "produk": "1", "nominal": 100000})
        self.assertTrue(ps.ringkas_untuk_cek(db, "2026-11-09")[0]["ada_beli_bulan_ini"])
        self.assertFalse(ps.ringkas_untuk_cek(db, "2026-12-09")[0]["ada_beli_bulan_ini"])


class TesAnalisisTanpaSetoranRutin(unittest.TestCase):
    def test_analisa_lengkap_walau_setoran_dan_tanggal_kosong(self):
        seri_rd = seri("2026-01-30", [1000.0 + 5 * i for i in range(300)])
        harga = {("rd", "1"): seri_rd, ("rd", "2"): seri("2026-01-30", [2000.0 + 4 * i for i in range(300)])}
        info = {("rd", "1"): {"mata_uang": "IDR", "nama": "RD A"}, ("rd", "2"): {"mata_uang": "IDR", "nama": "RD B"}}
        tx = [{**trx(tanggal="2026-02-02", produk="1", nama="RD A", kaki="lokal"), "_id": "a", "dibuat": "1"},
              {**trx(tanggal="2026-02-02", produk="2", nama="RD B", kaki="global"), "_id": "b", "dibuat": "2"},
              {**trx(tanggal="2026-05-04", produk="1", nama="RD A", kaki="lokal", nominal=500_000.0), "_id": "c", "dibuat": "3"}]
        porto = {"_id": "x", "nama": "Tidak rutin", "target": "pertumbuhan_saham", "tanggal_mulai": "2026-02-01", "pengingat_setoran": False, "setoran_rutin": None, "tanggal_setor": None, "aktif": True}
        a = ps.analisis_dari(porto, tx, "2026-10-20", FakeDb(), info, harga, seri("2026-01-01", [1.0] * 5))
        self.assertGreater(a["ringkasan"]["nilai"], 0)
        self.assertIsNotNone(a["ringkasan"]["xirr"])
        self.assertEqual(a["ringkasan"]["total_setor"], 2_500_000.0)
        self.assertGreater(len(a["deret"]), 5)
        self.assertEqual({k["kaki"] for k in a["alokasi"]["kaki"]}, {"lokal", "global"})
        self.assertIn("campuran", a["pembanding"])
        self.assertEqual(len(a["produk"]), 2)

    def test_hasil_sama_dengan_dan_tanpa_pengingat(self):
        seri_rd = seri("2026-01-30", [1000.0 + 5 * i for i in range(300)])
        harga = {("rd", "1"): seri_rd}
        info = {("rd", "1"): {"mata_uang": "IDR", "nama": "RD A"}}
        tx = [{**trx(tanggal="2026-02-02", produk="1", nama="RD A", kaki="lokal"), "_id": "a", "dibuat": "1"}]
        dasar = {"_id": "x", "nama": "P", "target": "bebas", "tanggal_mulai": "2026-02-01", "aktif": True}
        k1 = ps.analisis_dari({**dasar, "pengingat_setoran": False, "setoran_rutin": None, "tanggal_setor": None}, tx, "2026-10-20", FakeDb(), info, harga, seri("2026-01-01", [1.0] * 5))
        k2 = ps.analisis_dari({**dasar, "pengingat_setoran": True, "setoran_rutin": 1_000_000.0, "tanggal_setor": 3}, tx, "2026-10-20", FakeDb(), info, harga, seri("2026-01-01", [1.0] * 5))
        self.assertEqual(k1["ringkasan"], k2["ringkasan"])
        self.assertEqual(k1["deret"], k2["deret"])
        self.assertEqual(k1["alokasi"], k2["alokasi"])


if __name__ == "__main__":
    unittest.main()
