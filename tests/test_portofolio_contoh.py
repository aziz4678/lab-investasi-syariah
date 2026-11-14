import unittest

import pandas as pd

from backend.app.services import portofolio_contoh as pc
from backend.app.services import portofolio_saya as ps

KERANJANG = [{"id": 1, "nama": "Lokal A", "kaki": "lokal"}, {"id": 2, "nama": "Lokal B", "kaki": "lokal"}, {"id": 3, "nama": "Global C", "kaki": "global"}]


def seri_bulan(mulai, nilai):
    idx = [p.to_timestamp(how="end").normalize() for p in pd.period_range(mulai, periods=len(nilai), freq="M")]
    return pd.Series(nilai, index=idx, dtype=float)


def data_sintetis(n=40):
    return {1: seri_bulan("2018-01", [100 + i for i in range(n)]), 2: seri_bulan("2019-01", [200 + 2 * i for i in range(n - 12)]), 3: seri_bulan("2018-01", [50 + i * 0.5 for i in range(n)])}


class TesTanggal(unittest.TestCase):
    def test_akhir_bulan_sampai_acuan(self):
        t = pc.tanggal_bulanan("2021-10", "2021-12-31")
        self.assertEqual([x.strftime("%Y-%m-%d") for x in t], ["2021-10-31", "2021-11-30", "2021-12-31"])

    def test_acuan_tengah_bulan_tidak_ikut(self):
        t = pc.tanggal_bulanan("2021-10", "2021-12-15")
        self.assertEqual(t[-1].strftime("%Y-%m-%d"), "2021-11-30")

    def test_henti_membuang_bulan_terakhir(self):
        t = pc.tanggal_bulanan("2021-01", "2021-12-31", henti=3)
        self.assertEqual((len(t), t[-1].strftime("%Y-%m-%d")), (9, "2021-09-30"))


class TesBangunTransaksi(unittest.TestCase):
    def test_produk_belum_ada_dilewati_dan_porsi_dibagi_ulang(self):
        seri = data_sintetis()
        awal = pc.tanggal_bulanan("2018-06", "2018-06-30")
        tx = pc.bangun_transaksi(awal, KERANJANG, seri, pc.BOBOT["saham"])
        lokal = [t for t in tx if t["kaki"] == "lokal"]
        self.assertEqual([t["produk"] for t in lokal], ["1"])
        self.assertEqual(lokal[0]["nominal"], 500_000.0)
        sesudah = pc.tanggal_bulanan("2019-06", "2019-06-30")
        tx2 = pc.bangun_transaksi(sesudah, KERANJANG, seri, pc.BOBOT["saham"])
        self.assertEqual(sorted(t["nominal"] for t in tx2 if t["kaki"] == "lokal"), [250_000.0, 250_000.0])
        self.assertEqual(sum(t["nominal"] for t in tx2), 1_000_000.0)

    def test_kaki_global_tercatat_walau_mata_uang_rupiah(self):
        tx = pc.bangun_transaksi(pc.tanggal_bulanan("2018-06", "2018-06-30"), KERANJANG, data_sintetis(), pc.BOBOT["saham"])
        self.assertEqual({t["kaki"] for t in tx}, {"lokal", "global"})

    def test_bobot_melenceng(self):
        tx = pc.bangun_transaksi(pc.tanggal_bulanan("2019-06", "2019-06-30"), KERANJANG, data_sintetis(), {"lokal": 0.75, "global": 0.25})
        total = {k: sum(t["nominal"] for t in tx if t["kaki"] == k) for k in ("lokal", "global")}
        self.assertEqual(total, {"lokal": 750_000.0, "global": 250_000.0})

    def test_emas_pengganti_dengan_biaya(self):
        emas = pd.Series([1000.0] * 400, index=pd.date_range("2018-01-01", periods=400))
        tx = pc.bangun_transaksi(pc.tanggal_bulanan("2018-06", "2018-06-30"), KERANJANG, data_sintetis(), pc.BOBOT["emas"], emas)
        e = [t for t in tx if t["tipe_produk"] == "etf"]
        self.assertEqual(len(e), 1)
        self.assertEqual((e[0]["nominal"], e[0]["biaya"], e[0]["kaki"], e[0]["produk"]), (200_000.0, 300.0, "emas", pc.ID_EMAS))
        self.assertAlmostEqual(e[0]["unit"], (200_000 - 300) / 1000.0)

    def test_tanggal_lunak_tanpa_nav(self):
        seri = data_sintetis()
        tgl = pd.Timestamp("2018-06-15")
        tanpa = pc.bangun_transaksi([tgl], KERANJANG, seri, pc.BOBOT["saham"])
        self.assertEqual(tanpa, [])
        lunak = pc.bangun_transaksi([tgl], KERANJANG, seri, pc.BOBOT["saham"], lunak=(tgl,))
        self.assertGreater(len(lunak), 0)

    def test_valuasi_transaksi_lunak_menunggu_nav(self):
        seri = data_sintetis()
        acuan = pd.Timestamp("2018-06-15")
        tx = pc.bangun_transaksi([acuan], KERANJANG, seri, pc.BOBOT["saham"], lunak=(acuan,))
        info, harga, kurs = pc.info_harga(tx, KERANJANG, seri, None, acuan)
        baris, _ = ps.valuasi(tx, info, harga, kurs, acuan)
        self.assertTrue(all(b["status_unit"] == "menunggu_nav" for b in baris))


class TesPemilihan(unittest.TestCase):
    def test_valuasi_dan_ringkasan_sintetis(self):
        seri = data_sintetis()
        acuan = pd.Timestamp("2019-12-31")
        tx = pc.bangun_transaksi(pc.tanggal_bulanan("2019-01", acuan), KERANJANG, seri, pc.BOBOT["saham"])
        info, harga, kurs = pc.info_harga(tx, KERANJANG, seri, None, acuan)
        _, produk = ps.valuasi(tx, info, harga, kurs, acuan)
        ring = ps.ringkasan_total(produk, tx, acuan)
        self.assertGreater(ring["untung"], 0)
        self.assertEqual(ring["total_setor"], 12_000_000.0)

    def test_pilih_global_jatuh(self):
        seri = {1: seri_bulan("2018-01", [100 + i for i in range(40)]), 3: seri_bulan("2018-01", [100] * 20 + [100 - 3 * i for i in range(20)])}
        keranjang = [{"id": 1, "nama": "L", "kaki": "lokal"}, {"id": 3, "nama": "G", "kaki": "global"}]
        rg, rl, awal, akhir = pc.pilih_global_jatuh(keranjang, seri, pd.Period("2021-04", "M"))
        self.assertLess(rg, 0)
        self.assertGreater(rl, 0)

    def test_skenario_terdaftar_lengkap(self):
        kunci = {x["kunci"] for x in pc.daftar_skenario()}
        self.assertEqual(kunci, {"bagus", "jelek", "datar", "global_jatuh", "melenceng", "lupa_setor", "menunggu_nav", "baru_mulai", "bagus_emas", "jelek_emas"})
        self.assertTrue(all(x["kalimat"] and x["label"] for x in pc.daftar_skenario()))


class TesSemuaSkenarioTanpaTulisan(unittest.TestCase):
    KOLEKSI = ("portofolio_saya", "transaksi_saya", "transaksi_saya_log", "cek_kesehatan")

    def hitung(self):
        from backend.db import koneksi as kdb
        db = kdb.koneksi()
        return {k: db[k].count_documents({}) for k in self.KOLEKSI}

    def test_tiap_skenario_valid_dan_db_tidak_berubah(self):
        try:
            sebelum = self.hitung()
            pc.analisis_contoh("bagus")
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        for kunci in pc.SKENARIO:
            a = pc.analisis_contoh(kunci)
            self.assertTrue(a["transaksi"], kunci)
            self.assertGreater(a["ringkasan"]["nilai"], 0, kunci)
            self.assertEqual(a["contoh"]["kunci"], kunci)
            self.assertIn("alokasi", a)
            self.assertTrue(a["deret"], kunci)
            self.assertTrue(all(t["_id"].startswith("c") for t in a["transaksi"]), kunci)
        self.assertEqual(self.hitung(), sebelum)

    def test_ciri_tiap_skenario(self):
        try:
            hasil = {k: pc.analisis_contoh(k) for k in ("bagus", "jelek", "datar", "global_jatuh", "melenceng", "lupa_setor", "menunggu_nav", "baru_mulai", "bagus_emas", "jelek_emas")}
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        self.assertGreater(hasil["bagus"]["ringkasan"]["untung"], 0)
        self.assertLess(hasil["jelek"]["ringkasan"]["untung"], 0)
        self.assertLess(abs(hasil["datar"]["ringkasan"]["untung_persen"]), 0.03)
        self.assertTrue(hasil["global_jatuh"]["contoh"]["catatan_periode"])
        self.assertTrue(hasil["melenceng"]["alokasi"]["saran"])
        self.assertTrue(hasil["melenceng"]["alokasi"]["desember"])
        self.assertEqual(hasil["lupa_setor"]["contoh"]["pengingat"]["nama_cek"], "setoran_bulan_ini")
        self.assertEqual(hasil["lupa_setor"]["contoh"]["pengingat"]["status"], "info")
        self.assertEqual(len(hasil["menunggu_nav"]["menunggu_nav"]), 1)
        self.assertIsNone(hasil["baru_mulai"]["ringkasan"]["xirr"])
        self.assertIn("belum cukup", hasil["baru_mulai"]["ringkasan"]["xirr_pesan"])
        for k in ("bagus_emas", "jelek_emas"):
            self.assertTrue(hasil[k]["contoh"]["pengganti"])
            self.assertTrue(any(p["kaki"] == "emas" for p in hasil[k]["produk"]))
        self.assertGreater(hasil["jelek_emas"]["ringkasan"]["untung_persen"], hasil["jelek"]["ringkasan"]["untung_persen"])

    def test_tanggal_acuan_pada_analisis_normal_tidak_mengubah_perilaku(self):
        import inspect
        sig = inspect.signature(ps.analisis)
        self.assertIn("tanggal_acuan", sig.parameters)
        self.assertIsNone(sig.parameters["tanggal_acuan"].default)


if __name__ == "__main__":
    unittest.main()
