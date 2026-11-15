import unittest

import pandas as pd

from backend.app.services import kenapa_beli as kb
from backend.research import keranjang_pertumbuhan as kp


class TesKondisi(unittest.TestCase):
    def test_ambang(self):
        self.assertEqual(kb.kondisi(-5.1)["kode"], "turun")
        self.assertEqual(kb.kondisi(-5.0)["kode"], "datar")
        self.assertEqual(kb.kondisi(5.0)["kode"], "datar")
        self.assertEqual(kb.kondisi(5.1)["kode"], "naik")
        self.assertEqual(kb.kondisi(None)["kode"], "tidak_ada")

    def test_turun_lebih_tahan_dari_pasar(self):
        k = kb._kalimat("lokal", -20.0, -45.0)
        self.assertIn("bukan karena produknya", k["teks"])
        self.assertIn("-45,0%", k["teks"])
        self.assertFalse(k["peringatan"])

    def test_turun_tertinggal_dari_pasar(self):
        k = kb._kalimat("global", -30.0, -10.0)
        self.assertIn("tertinggal", k["teks"])
        self.assertTrue(k["peringatan"])

    def test_naik_dan_datar(self):
        self.assertIn("jangan ditambah", kb._kalimat("lokal", 12.0, 8.0)["teks"])
        self.assertIn("datar", kb._kalimat("emas", 1.0, 1.0)["teks"])

    def test_konservatif(self):
        self.assertIn("Naik pelan dan stabil", kb._kalimat("pu", 4.5, 4.0)["teks"])
        self.assertIn("Hampir datar", kb._kalimat("pt", -0.5, 1.0)["teks"])
        turun = kb._kalimat("pt", -2.0, 1.0)
        self.assertIn("tidak biasa", turun["teks"])
        self.assertTrue(turun["peringatan"])


class TesRingkasan(unittest.TestCase):
    def kartu(self, ret, kaki="lokal"):
        return kb.susun(kaki, ret, -10.0, None)

    def test_mayoritas_turun_menyebut_pasar(self):
        r = kb.ringkasan([self.kartu(-20), self.kartu(-15), self.kartu(10, "global")])
        self.assertEqual(r["kondisi"], "turun")
        self.assertIn("2 dari 3", r["teks"])
        self.assertIn("pasar saham Indonesia", r["teks"])

    def test_mayoritas_naik(self):
        r = kb.ringkasan([self.kartu(10), self.kartu(12), self.kartu(-8)])
        self.assertEqual(r["kondisi"], "naik")
        self.assertIn("2 dari 3", r["teks"])

    def test_kosong(self):
        self.assertIsNone(kb.ringkasan([]))

    def test_konservatif_tak_biasa(self):
        r = kb.ringkasan([kb.susun("pu", 4.0, 4.0, None), kb.susun("pt", -3.0, 1.0, None)], konservatif=True)
        self.assertEqual(r["kondisi"], "turun")
        self.assertIn("tidak biasa", r["teks"])


class TesHarapan(unittest.TestCase):
    def test_teks_dengan_periode(self):
        h = {"cagr": 8.26, "dd": -35.2, "dari": "Feb 2013", "sampai": "Nov 2026"}
        self.assertEqual(kb.harapan_teks(h), "Rekam jejak (periode Feb 2013–Nov 2026): rata-rata naik 8,3% per tahun, pernah turun sampai 35,2%.")

    def test_hampir_tidak_pernah_turun(self):
        h = {"cagr": 4.7, "dd": 0.0, "dari": "Jan 2018", "sampai": "Nov 2026"}
        self.assertEqual(kb.harapan_teks(h), "Rekam jejak (periode Jan 2018–Nov 2026): rata-rata naik 4,7% per tahun, hampir tidak pernah turun.")

    def test_produk_pendek_pakai_proksi(self):
        m = pd.Series([100.0 * 1.01 ** i for i in range(40)], index=pd.period_range("2023-01", periods=40, freq="M"))
        h = kb.harapan_produk(m, 3.3, "lokal", "NAV produk asli")
        self.assertTrue(h is None or h["sumber"] == "proksi")

    def test_produk_panjang_pakai_produk(self):
        m = pd.Series([100.0 * 1.01 ** i for i in range(72)], index=pd.period_range("2020-01", periods=72, freq="M"))
        h = kb.harapan_produk(m, 6.0, "lokal", "NAV produk asli")
        self.assertEqual(h["sumber"], "produk")
        self.assertAlmostEqual(h["cagr"], (1.01 ** 12 - 1) * 100, places=1)


class TesSaringanLokal(unittest.TestCase):
    def produk(self, **x):
        dasar = {"id": 1, "nama": "RD", "mata_uang": "IDR", "kategori": "saham", "nav_tgl": str(pd.Timestamp.today().date()), "nav_beku": False, "tahun_data": 5.0,
                 "biaya": 2.0, "aum": 2e11, "platform": [{"kode": "bibit"}]}
        return {**dasar, **x}

    def alasan(self, selisih=0.05, **x):
        p = self.produk(**x)
        return kp.alasan_dasar(p, "LK", set(), pd.Timestamp.today() - pd.Timedelta(days=14), {1: {"selisih": selisih}})

    def test_lolos(self):
        self.assertEqual(self.alasan(), [])

    def test_aum_kecil(self):
        self.assertTrue(any("dana kelolaan" in a for a in self.alasan(aum=9.9e10)))

    def test_biaya_di_luar_batas(self):
        self.assertTrue(any("tidak wajar" in a for a in self.alasan(biaya=0.02)))
        self.assertTrue(any("tidak wajar" in a for a in self.alasan(biaya=5.01)))
        self.assertTrue(any("tidak wajar" in a for a in self.alasan(biaya=7.26)))
        self.assertEqual(self.alasan(biaya=0.3), [])
        self.assertEqual(self.alasan(biaya=5.0), [])

    def test_tertinggal_dari_jii(self):
        self.assertTrue(any("tertinggal dari JII" in a for a in self.alasan(selisih=-0.01)))
        self.assertTrue(any("tertinggal dari JII" in a for a in self.alasan(selisih=0.0)))

    def test_umur_kurang(self):
        self.assertTrue(any("riwayat" in a for a in self.alasan(tahun_data=2.9)))

    def test_selisih_tidak_bisa_dihitung(self):
        p = self.produk()
        a = kp.alasan_dasar(p, "LK", set(), pd.Timestamp.today() - pd.Timedelta(days=14), {})
        self.assertTrue(any("tidak bisa dihitung" in x for x in a))


class TesPilih(unittest.TestCase):
    def c(self, id_, biaya, *platform):
        return {"id": id_, "biaya": biaya, "aum": 2e11, "platform": [{"kode": p} for p in platform]}

    def test_tiga_termurah_per_aplikasi_dan_spus_hanya_ajaib(self):
        lk = [self.c(1, 2.0, "bibit", "ajaib"), self.c(2, 3.0, "bibit"), self.c(3, 4.0, "bibit", "makmur"), self.c(4, 7.0, "ajaib", "makmur")]
        spus = {"id": "SPUS", "platform": [{"kode": "ajaib"}]}
        lolos = {"LK": lk, "GL": [spus]}
        semua = kp.pilih(lolos, "semua")
        self.assertEqual([c["id"] for c in semua["LK"]], [1, 2, 3])
        self.assertEqual([c["id"] for c in semua["GL"]], ["SPUS"])
        self.assertEqual([c["id"] for c in kp.pilih(lolos, "ajaib")["LK"]], [1, 4])
        self.assertEqual(kp.pilih(lolos, "ajaib")["GL"][0]["id"], "SPUS")
        self.assertEqual(kp.pilih(lolos, "bibit")["GL"], [])
        self.assertEqual(kp.pilih(lolos, "makmur")["GL"], [])


if __name__ == "__main__":
    unittest.main()
