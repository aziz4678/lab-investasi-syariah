import unittest

import numpy as np
import pandas as pd

from backend.research import perkiraan_pertumbuhan as pp


def seri(n=60, r=0.01, mulai="2020-01"):
    idx = pd.period_range(mulai, periods=n, freq="M")
    return pd.DataFrame({"idx": r, "gl": r, "emas": r}, index=idx)


def acak(n=96, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2015-01", periods=n, freq="M")
    return pd.DataFrame({"idx": rng.normal(0.008, 0.05, n), "gl": rng.normal(0.009, 0.04, n), "emas": rng.normal(0.006, 0.03, n)}, index=idx)


class TesXirr(unittest.TestCase):
    def test_return_konstan_sama_dengan_returnnya(self):
        for r in (0.01, 0.005, -0.004, 0.0):
            R = seri(36, r)
            nilai, _ = pp.jalankan(R, pp.BOBOT["saham"], biaya_gl=0.0, biaya_rebal=0.0)
            akhir = np.array([nilai[0][35]])
            self.assertAlmostEqual(float(pp.xirr_tahunan(akhir, 36)[0]), (1 + r) ** 12 - 1, places=8)

    def test_xirr_bergantung_pada_setoran_bukan_skala(self):
        R = acak()
        n1, _ = pp.jalankan(R, pp.BOBOT["emas"], setoran=1.0)
        n2, _ = pp.jalankan(R, pp.BOBOT["emas"], setoran=250_000.0)
        a = pp.xirr_tahunan(np.array([n1[0][59]]), 60, 1.0)[0]
        b = pp.xirr_tahunan(np.array([n2[0][59]]), 60, 250_000.0)[0]
        self.assertAlmostEqual(a, b, places=10)


class TesLinear(unittest.TestCase):
    def test_per_rp1_dikali_setoran_sama_dengan_simulasi_langsung(self):
        R = acak()
        for gaya in ("saham", "emas"):
            per1, bul1 = pp.jalankan(R, pp.BOBOT[gaya], setoran=1.0)
            besar, bulb = pp.jalankan(R, pp.BOBOT[gaya], setoran=1_500_000.0)
            for s in (0, 7, 30):
                kali = per1[s] * 1_500_000.0
                self.assertTrue(np.all(np.abs(kali / besar[s] - 1) < 1e-4))
                self.assertTrue(np.allclose(bul1[s], bulb[s], atol=1e-12))

    def test_ringkasan_per_rp1_dikali_setoran(self):
        R = acak()
        nilai1, bul1 = pp.jalankan(R, pp.BOBOT["saham"], setoran=1.0)
        nilaib, bulb = pp.jalankan(R, pp.BOBOT["saham"], setoran=2_000_000.0)
        a = pp.ringkas_jangka(R, nilai1, bul1, 3, 1.0)
        b = pp.ringkas_jangka(R, nilaib, bulb, 3, 2_000_000.0)
        for k in ("median", "terburuk", "terbaik", "total"):
            self.assertLess(abs(a[k] * 2_000_000.0 / b[k] - 1), 1e-4)
        self.assertEqual(a["jendela"], b["jendela"])
        self.assertEqual(a["untung"], b["untung"])
        self.assertAlmostEqual(a["xirr_median"], b["xirr_median"], places=8)


class TesPeriodeTerpisah(unittest.TestCase):
    def test_rumus_dan_peringatan(self):
        R = acak(305)
        nilai, bul = pp.jalankan(R, pp.BOBOT["saham"])
        harap = {1: 25.4, 3: 8.5, 5: 5.1, 10: 2.5, 20: 1.3}
        for t, n in harap.items():
            r = pp.ringkas_jangka(R, nilai, bul, t)
            self.assertEqual(r["periode_terpisah"], n)
            self.assertEqual(r["periode_terpisah"], round(305 / 12 / t, 1))
        terbatas = {t: pp.ringkas_jangka(R, nilai, bul, t)["terbatas"] for t in harap}
        self.assertEqual(terbatas, {1: False, 3: False, 5: False, 10: True, 20: True})

    def test_data_asli_peringatan_10_dan_20_saja(self):
        h = pp.dt.baca_hasil(pp.NAMA_HASIL)
        if h is None or "periode_terpisah" not in h["saham"]["jangka"]["10"]:
            self.skipTest("hasil produksi belum dihitung ulang")
        for gaya in ("saham", "emas"):
            j = h[gaya]["jangka"]
            self.assertEqual([t for t in ("1", "3", "5", "10", "20") if j[t]["terbatas"]], ["10", "20"])


class TesJendela(unittest.TestCase):
    def test_jumlah_jendela_bergulir(self):
        R = acak(96)
        nilai, bul = pp.jalankan(R, pp.BOBOT["saham"])
        r = pp.ringkas_jangka(R, nilai, bul, 5)
        self.assertEqual(r["jendela"], 96 - 60 + 1)
        self.assertIsNone(pp.ringkas_jangka(R, nilai, bul, 9))

    def test_biaya_global_mengurangi_hasil(self):
        R = acak()
        a, _ = pp.jalankan(R, pp.BOBOT["saham"], biaya_gl=0.0, biaya_rebal=0.0)
        b, _ = pp.jalankan(R, pp.BOBOT["saham"], biaya_gl=0.005, biaya_rebal=0.0)
        self.assertLess(b[0][35], a[0][35])

    def test_penurunan_terdalam_negatif(self):
        r = pp.penurunan_terdalam(acak(), pp.BOBOT["saham"])
        self.assertLess(r["dd"], 0)


if __name__ == "__main__":
    unittest.main()
