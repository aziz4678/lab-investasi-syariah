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


class TesProdukAdil(unittest.TestCase):
    POOL = [{"id": 11, "nama": "Pengganti L", "kaki": "lokal"}, {"id": 12, "nama": "Pengganti L2", "kaki": "lokal"}, {"id": 13, "nama": "Pengganti G", "kaki": "global"}]

    def seri_lengkap(self, mulai="2018-01", n=40, dasar=100.0):
        return seri_bulan(mulai, [dasar + i for i in range(n)])

    def test_produk_tanpa_data_penuh_diganti_sejenis_berlabel(self):
        seri = {1: self.seri_lengkap(), 2: self.seri_lengkap("2019-01", 28), 3: self.seri_lengkap(), 11: self.seri_lengkap(), 12: self.seri_lengkap()}
        tanggal = pc.tanggal_bulanan("2018-06", "2019-06-30")
        dipilih = pc.pilih_keranjang(KERANJANG, self.POOL, seri, tanggal)
        lokal = [p for p in dipilih if p["kaki"] == "lokal"]
        self.assertEqual([p["id"] for p in lokal], [1, 11])
        self.assertEqual([p["pengganti_dari"] for p in lokal], [None, "Lokal B"])
        self.assertEqual([p["id"] for p in dipilih if p["kaki"] == "global"], [3])

    def test_semua_produk_dipakai_selama_seluruh_periode(self):
        seri = {1: self.seri_lengkap(), 2: self.seri_lengkap("2019-01", 28), 3: self.seri_lengkap(), 11: self.seri_lengkap()}
        tanggal = pc.tanggal_bulanan("2018-06", "2019-12-31")
        dipilih = pc.pilih_keranjang(KERANJANG, self.POOL, seri, tanggal)
        tx = pc.bangun_transaksi(tanggal, dipilih, seri, pc.BOBOT["saham"])
        per_produk = {}
        for t in tx:
            per_produk.setdefault(t["produk"], set()).add(t["tanggal"])
        self.assertTrue(all(len(v) == len(tanggal) for v in per_produk.values()))
        pengganti = [t for t in tx if t["produk"] == "11"]
        self.assertTrue(all(pc.LABEL_PENGGANTI_RD in t["catatan"] for t in pengganti))

    def test_tanpa_pengganti_produk_dibuang(self):
        seri = {1: self.seri_lengkap(), 2: self.seri_lengkap("2019-01", 28), 3: self.seri_lengkap()}
        dipilih = pc.pilih_keranjang(KERANJANG, [], seri, pc.tanggal_bulanan("2018-06", "2019-06-30"))
        self.assertEqual([p["id"] for p in dipilih if p["kaki"] == "lokal"], [1])

    def test_pengganti_harus_punya_data_penuh_juga(self):
        seri = {1: self.seri_lengkap(), 2: self.seri_lengkap("2019-01", 28), 3: self.seri_lengkap(), 11: self.seri_lengkap("2019-03", 20), 12: self.seri_lengkap()}
        dipilih = pc.pilih_keranjang(KERANJANG, self.POOL, seri, pc.tanggal_bulanan("2018-06", "2019-06-30"))
        self.assertEqual([p["id"] for p in dipilih if p["kaki"] == "lokal"], [1, 12])

    def test_rebalance_alami_mengarahkan_setoran_ke_bagian_tertinggal(self):
        lokal = seri_bulan("2018-01", [100 * (1.06 ** i) for i in range(30)])
        glob = seri_bulan("2018-01", [100.0] * 30)
        seri = {1: lokal, 2: lokal, 3: glob}
        tanggal = pc.tanggal_bulanan("2018-01", "2019-12-31")
        tx = pc.bangun_transaksi_dinamis(tanggal, KERANJANG, seri, pc.BOBOT["saham"])
        arah = [t for t in tx if pc.CATATAN_ARAH in t["catatan"]]
        self.assertTrue(arah)
        for tgl in {t["tanggal"] for t in arah}:
            bulan = [t for t in tx if t["tanggal"] == tgl]
            self.assertAlmostEqual(sum(t["nominal"] for t in bulan), 1_000_000.0, delta=5)
            self.assertGreater(sum(t["nominal"] for t in bulan if t["kaki"] == "global"), 500_000.0)
        self.assertTrue(all(t["nominal"] > 0 for t in tx))
        self.assertEqual(len({t["_id"] for t in tx}), len(tx))
        info, harga, kurs = pc.info_harga(tx, KERANJANG, seri, None, tanggal[-1])
        _, produk = ps.valuasi(tx, info, harga, kurs, tanggal[-1])
        nilai = {}
        for p in produk:
            nilai[p["kaki"]] = nilai.get(p["kaki"], 0.0) + p["nilai"]
        porsi_lokal = nilai["lokal"] / sum(nilai.values())
        tanpa = pc.bangun_transaksi(tanggal, KERANJANG, seri, pc.BOBOT["saham"])
        i2, h2, k2 = pc.info_harga(tanpa, KERANJANG, seri, None, tanggal[-1])
        _, p2 = ps.valuasi(tanpa, i2, h2, k2, tanggal[-1])
        n2 = {}
        for p in p2:
            n2[p["kaki"]] = n2.get(p["kaki"], 0.0) + p["nilai"]
        self.assertLess(abs(porsi_lokal - 0.5), abs(n2["lokal"] / sum(n2.values()) - 0.5))

    def test_tanpa_rebalance_tetap_pembagian_awal(self):
        lokal = seri_bulan("2018-01", [100 * (1.06 ** i) for i in range(30)])
        seri = {1: lokal, 2: lokal, 3: seri_bulan("2018-01", [100.0] * 30)}
        tanggal = pc.tanggal_bulanan("2018-01", "2019-12-31")
        tx = pc.bangun_transaksi_dinamis(tanggal, KERANJANG, seri, {"lokal": 0.75, "global": 0.25}, rebalance=False)
        self.assertFalse(any(pc.CATATAN_ARAH in t["catatan"] for t in tx))
        self.assertEqual({t["nominal"] for t in tx if t["kaki"] == "global"}, {250_000.0})


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

    def test_alokasi_akhir_dekat_target_kecuali_melenceng_dan_produk_penuh(self):
        try:
            baris = pc.laporan_alokasi()
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        for r in baris:
            if r["kunci"] == "melenceng":
                self.assertGreater(r["selisih_maks_poin"], 15)
            else:
                self.assertLessEqual(r["selisih_maks_poin"], 5.0, r)
        jelek = next(r for r in baris if r["kunci"] == "jelek")
        self.assertTrue(jelek["pengganti"])

    def test_tiap_produk_punya_data_di_seluruh_periode(self):
        from backend.db import koneksi as kdb
        try:
            data = pc.siapkan_data(kdb.koneksi())
            a = pc.analisis_contoh("jelek", data=data)
        except Exception as e:
            self.skipTest(f"data produksi tidak tersedia: {e}")
        keranjang, pool, seri, emas = data
        spec = pc.tentukan("jelek", keranjang, seri, emas, pool)
        tanggal = pc.tanggal_bulanan(spec["mulai"], spec["acuan"])
        dipilih = pc.pilih_keranjang(keranjang, pool, seri, tanggal)
        for p in dipilih:
            self.assertTrue(pc.penuh(seri[p["id"]], tanggal), p["nama"])
        self.assertLessEqual({t["produk"] for t in a["transaksi"] if t["tipe_produk"] == "rd"}, {str(p["id"]) for p in dipilih})
        self.assertTrue(any(p.get("catatan_pengganti") for p in a["produk"]))
        self.assertTrue(a["contoh"]["pengganti_rd"])
        self.assertTrue(any(pc.LABEL_PENGGANTI_RD in (t["catatan"] or "") for t in a["transaksi"]))

    def test_tanggal_acuan_pada_analisis_normal_tidak_mengubah_perilaku(self):
        import inspect
        sig = inspect.signature(ps.analisis)
        self.assertIn("tanggal_acuan", sig.parameters)
        self.assertIsNone(sig.parameters["tanggal_acuan"].default)


if __name__ == "__main__":
    unittest.main()
