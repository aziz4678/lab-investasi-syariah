import unittest
from unittest import mock

import pandas as pd

from backend.app.services import belanja as bl


def produk(id_, nama, platform, **x):
    return {"id": id_, "nama": nama, "platform": [{"kode": p, "url": None} for p in platform], **x}


DASAR = [produk(1, "A", ["bibit", "ajaib"]), produk(2, "B", ["bibit"]), produk(3, "C", ["bibit", "makmur"])]
POOL = DASAR + [produk(4, "D", ["ajaib"]), produk(5, "E", ["makmur"]), produk(6, "F", ["ajaib", "makmur"])]


class TesAplikasi(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(bl.normal_aplikasi(None), ["bibit", "ajaib", "makmur", "stockbit"])
        self.assertEqual(bl.normal_aplikasi("Makmur,bibit,xx"), ["bibit", "makmur"])
        self.assertEqual(bl.normal_aplikasi(""), [])

    def test_aplikasi_angka(self):
        self.assertEqual(bl.aplikasi_angka(["bibit"]), "bibit")
        self.assertEqual(bl.aplikasi_angka(["bibit", "stockbit"]), "bibit")
        self.assertEqual(bl.aplikasi_angka(["bibit", "ajaib"]), "semua")
        self.assertEqual(bl.aplikasi_angka(["stockbit"]), "semua")


class TesPilihProduk(unittest.TestCase):
    def test_semua_aplikasi_sama_dengan_dasar(self):
        hasil, hilang, sisa = bl.pilih_produk(DASAR, POOL, ["bibit", "ajaib", "makmur", "stockbit"], 3)
        self.assertEqual([x["produk"]["id"] for x in hasil], [1, 2, 3])
        self.assertTrue(all(x["pengganti_dari"] is None for x in hasil))
        self.assertEqual(hilang, [])

    def test_filter_satu_aplikasi_dengan_pengganti(self):
        hasil, hilang, _ = bl.pilih_produk(DASAR, POOL, ["ajaib"], 3)
        self.assertEqual([x["produk"]["id"] for x in hasil], [1, 4, 6])
        self.assertEqual([x["pengganti_dari"] for x in hasil], [None, "B", "C"])
        self.assertEqual([c["id"] for c in hilang], [2, 3])

    def test_tidak_ada_pengganti(self):
        pool = [produk(1, "A", ["bibit"]), produk(2, "B", ["bibit"])]
        hasil, hilang, sisa = bl.pilih_produk(pool, pool, ["makmur"], 2)
        self.assertEqual(hasil, [])
        self.assertEqual(len(hilang), 2)

    def test_pengganti_sebagian(self):
        pool = DASAR + [produk(9, "Z", ["makmur"])]
        hasil, _, sisa = bl.pilih_produk(DASAR, pool, ["makmur"], 3)
        self.assertEqual([x["produk"]["id"] for x in hasil], [3, 9])
        self.assertEqual(hasil[1]["pengganti_dari"], "A")
        self.assertEqual(len(sisa), 1)

    def test_stockbit_saja_tanpa_rd(self):
        hasil, hilang, _ = bl.pilih_produk(DASAR, POOL, ["stockbit"], 3)
        self.assertEqual(hasil, [])

    def test_tetapkan_aplikasi_sedikit_aplikasi(self):
        peta = bl.tetapkan_aplikasi(DASAR, ["bibit", "ajaib", "makmur"])
        self.assertEqual(set(peta.values()), {"bibit"})
        peta2 = bl.tetapkan_aplikasi([produk(1, "A", ["ajaib"]), produk(2, "B", ["makmur"])], ["bibit", "ajaib", "makmur"])
        self.assertEqual(peta2, {0: "ajaib", 1: "makmur"})


class TesEtf(unittest.TestCase):
    def frame(self, close, nav):
        return pd.DataFrame({"close": close, "nav": nav, "volume": 1.0, "nilai": 1e7}, index=pd.bdate_range("2026-11-02", periods=len(close)))

    def test_premium_sejajar_nav_hari_terakhir_belum_ada(self):
        df = self.frame([100, 102, 104, 106], [100, 100, 100, float("nan")])
        self.assertAlmostEqual(bl.premium_sejajar(df), 102 / 100 - 1)

    def test_premium_sejajar_nav_lengkap(self):
        df = self.frame([100, 102, 104], [100, 100, 100])
        self.assertAlmostEqual(bl.premium_sejajar(df), 102 / 100 - 1)

    def test_premium_tanpa_nav(self):
        self.assertIsNone(bl.premium_sejajar(self.frame([100, 101], [float("nan")] * 2)))

    def test_badge(self):
        self.assertEqual(bl.badge_premium(0.01)["warna"], "hijau")
        self.assertEqual(bl.badge_premium(0.02)["warna"], "hijau")
        self.assertEqual(bl.badge_premium(0.0319)["warna"], "kuning")
        self.assertEqual(bl.badge_premium(None)["warna"], "abu")

    def test_lot(self):
        x = bl.info_lot(200_000, 240.0)
        self.assertEqual((x["lot"], x["harga_per_lot"], x["perkiraan"]), (8, 24000.0, 192000.0))
        y = bl.info_lot(10_000, 240.0)
        self.assertEqual((y["lot"], y["bulan_kumpul"]), (0, 3))

    def kartu(self, apps, close, nav, hari_ini="2026-11-06"):
        df = self.frame(close, nav)
        ring = {"XGLD": {"nama": "ETF Emas", "aum": 2e10}}
        with mock.patch.object(bl, "etf_terpilih", return_value=("XGLD", "uji maju", ring, {"XGLD": df})):
            return bl.kartu_etf(200_000, apps, hari_ini=hari_ini)

    def test_tanpa_stockbit_ajaib(self):
        kartu, per = self.kartu(["bibit", "makmur"], [100] * 4, [100] * 4)
        self.assertIsNone(kartu["aplikasi"])
        self.assertEqual(per[0]["jenis"], "etf_aplikasi")
        self.assertIn("akun saham", per[0]["teks"])

    def test_aplikasi_etf(self):
        self.assertEqual(self.kartu(["stockbit"], [100] * 4, [100] * 4)[0]["aplikasi"], "stockbit")
        self.assertEqual(self.kartu(["ajaib", "bibit"], [100] * 4, [100] * 4)[0]["aplikasi"], "ajaib")
        self.assertEqual(self.kartu(["ajaib", "stockbit"], [100] * 4, [100] * 4)[0]["aplikasi"], "stockbit")

    def test_premium_lebih_dari_dua_persen(self):
        kartu, per = self.kartu(["stockbit"], [100, 103, 103, 103], [100, 100, 100, 100])
        self.assertAlmostEqual(kartu["premium"], 0.03)
        self.assertEqual(kartu["badge"]["warna"], "kuning")
        self.assertEqual(per, [])
        self.assertEqual(kartu["fee"], 0.0015)

    def test_data_basi(self):
        self.assertTrue(self.kartu(["stockbit"], [100] * 3, [100] * 3, "2026-11-20")[0]["basi"])
        self.assertFalse(self.kartu(["stockbit"], [100] * 3, [100] * 3, "2026-11-05")[0]["basi"])


class TesMinBeli(unittest.TestCase):
    def test_melebihi_porsi(self):
        class FakePt:
            @staticmethod
            def _kartu(c, nilai, catatan, kin):
                return {"id": c["id"], "nama": c["nama"], "nilai": nilai}

        class FakeDb:
            class rd_platform:
                @staticmethod
                def find_one(_):
                    return {"nama": "Nama Di App"}

        c = produk(1, "A", ["bibit"], min_beli_nilai=1_000_000.0, min_beli_uang="IDR")
        k = bl._kartu_rd(FakePt, c, 200_000, 1_000_000, {}, None, "bibit", FakeDb)
        self.assertTrue(k["min_beli_melebihi"])
        self.assertEqual(k["cari_di_aplikasi"], "Nama Di App")
        self.assertIn("manajer investasi", k["min_beli_teks"])
        k2 = bl._kartu_rd(FakePt, c, 2_000_000, 1_000_000, {}, None, "bibit", FakeDb)
        self.assertFalse(k2["min_beli_melebihi"])


class TesMinBeliMataUang(unittest.TestCase):
    def test_parser_ikut_mata_uang_produk(self):
        usd = bl.parse_min_beli("10.000", "USD")
        self.assertEqual((usd["nilai"], usd["uang"], usd["tampil"]), (10000.0, "USD", "US$10.000"))
        idr = bl.parse_min_beli("Rp 10.000", "IDR")
        self.assertEqual((idr["nilai"], idr["uang"], idr["tampil"]), (10000.0, "IDR", "Rp10.000"))
        tanpa = bl.parse_min_beli("10.000", None)
        self.assertEqual(tanpa["uang"], "IDR")

    def test_penanda_eksplisit_menang_atas_mata_uang_produk(self):
        self.assertEqual(bl.parse_min_beli("USD 100", "IDR")["uang"], "USD")
        self.assertEqual(bl.parse_min_beli("Rp. 100.000", "USD")["uang"], "IDR")

    def test_tidak_ada_batas_dan_kosong(self):
        self.assertEqual(bl.parse_min_beli("tidak ada batas", "IDR")["tampil"], "tanpa batas")
        self.assertIsNone(bl.parse_min_beli(None, "IDR")["nilai"])
        self.assertIsNone(bl.parse_min_beli("", "USD")["tampil"])

    def test_info_produk_usd_dikonversi_kurs(self):
        c = {"min_beli_mi": "10.000", "mata_uang": "USD"}
        x = bl.info_min_beli(c, 500_000.0, 16_000.0)
        self.assertEqual(x["min_beli_tampil"], "US$10.000")
        self.assertEqual(x["min_beli_uang"], "USD")
        self.assertAlmostEqual(x["min_beli_idr"], 160_000_000.0)
        self.assertTrue(x["min_beli_melebihi"])
        self.assertIn("manajer investasi", x["min_beli_teks"])

    def test_info_produk_usd_cukup_bila_porsi_besar(self):
        c = {"min_beli_mi": "100", "mata_uang": "USD"}
        self.assertFalse(bl.info_min_beli(c, 5_000_000.0, 16_000.0)["min_beli_melebihi"])
        self.assertTrue(bl.info_min_beli(c, 1_000_000.0, 16_000.0)["min_beli_melebihi"])

    def test_info_produk_idr(self):
        c = {"min_beli_mi": "Rp 100.000", "mata_uang": "IDR"}
        self.assertEqual(bl.info_min_beli(c, 167_000.0)["min_beli_tampil"], "Rp100.000")
        self.assertFalse(bl.info_min_beli(c, 167_000.0)["min_beli_melebihi"])
        self.assertTrue(bl.info_min_beli(c, 50_000.0)["min_beli_melebihi"])

    def test_usd_tanpa_kurs_tidak_memperingatkan_sembarangan(self):
        x = bl.info_min_beli({"min_beli_mi": "10.000", "mata_uang": "USD"}, 500_000.0, None)
        self.assertIsNone(x["min_beli_idr"])
        self.assertFalse(x["min_beli_melebihi"])
        self.assertEqual(x["min_beli_tampil"], "US$10.000")


class TesCacheBelanja(unittest.TestCase):
    def setUp(self):
        bl.kosongkan_cache()

    def test_hitung_sekali_untuk_argumen_dan_versi_sama(self):
        n = []
        with mock.patch.object(bl, "versi_data", return_value=("v1",)):
            a = bl.dari_cache("x", (1,), lambda: n.append(1) or {"a": 1})
            b = bl.dari_cache("x", (1,), lambda: n.append(1) or {"a": 2})
        self.assertEqual(len(n), 1)
        self.assertIs(a, b)

    def test_invalidasi_saat_versi_data_berubah(self):
        n = []
        with mock.patch.object(bl, "versi_data", return_value=("v1",)):
            bl.dari_cache("x", (1,), lambda: n.append(1) or 1)
        with mock.patch.object(bl, "versi_data", return_value=("v2",)):
            bl.dari_cache("x", (1,), lambda: n.append(1) or 2)
        self.assertEqual(len(n), 2)

    def test_argumen_beda_dihitung_terpisah_dan_batas_ukuran(self):
        n = []
        with mock.patch.object(bl, "versi_data", return_value=("v1",)):
            for i in range(bl.CACHE_MAKS + 10):
                bl.dari_cache("x", (i,), lambda i=i: n.append(i) or i)
        self.assertEqual(len(n), bl.CACHE_MAKS + 10)
        self.assertLessEqual(len(bl.CACHE), bl.CACHE_MAKS)

    def test_pembungkus_menormalkan_aplikasi(self):
        with mock.patch.object(bl, "versi_data", return_value=("v1",)), mock.patch.object(bl, "pertumbuhan", side_effect=lambda *a: {"p": a}) as f:
            bl.pertumbuhan_cache("bibit,ajaib", 1_000_000, 0, "saham")
            bl.pertumbuhan_cache(["ajaib", "bibit"], 1_000_000.0, 0.0, "saham")
        self.assertEqual(f.call_count, 1)


class TesKunciUjiMaju(unittest.TestCase):
    def test_produk_halaman_tidak_berubah_oleh_lapisan_belanja(self):
        from backend.paper import uji_maju_pertumbuhan as um
        try:
            sebelum = um.produk_halaman()
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        for apps in (None, "bibit", "makmur", "ajaib,makmur", "stockbit", ""):
            for gaya in ("saham", "emas"):
                bl.pertumbuhan(apps, 1_000_000, 0, gaya)
            bl.konservatif(apps, 1_000_000_000, 10_000_000, 6, "sbn50")
            bl.konservatif(apps, 30_000_000, 5_000_000, 6, "tanpa_sbn")
        self.assertEqual(um.produk_halaman(), sebelum)

    def test_semua_aplikasi_sama_dengan_produk_halaman(self):
        from backend.paper import uji_maju_pertumbuhan as um
        try:
            ph = um.produk_halaman()
            r = bl.pertumbuhan(None, 1_000_000, 0, "saham")
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        tampil = [p for g in r["grup"] for p in g["produk"] if p["tipe"] == "rd"]
        self.assertEqual(sorted(p["id"] for p in tampil if p["kaki"] == "lokal"), sorted(x["id"] for x in ph["lokal"]))
        self.assertEqual(sorted(p["id"] for p in tampil if p["kaki"] == "global"), sorted(x["id"] for x in ph["global"]))


if __name__ == "__main__":
    unittest.main()
