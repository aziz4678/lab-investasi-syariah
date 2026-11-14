import unittest

import numpy as np
import pandas as pd

from backend.paper import mesin_pertumbuhan as mp
from backend.paper import sintetis_pertumbuhan as sp

HARI = sp.hari_kerja("2026-12-01", "2027-01-29")
PRA = [pd.Timestamp("2026-11-27"), pd.Timestamp("2026-11-30")]
HARI_X = PRA + HARI


def jenis(m, j):
    return [k for k in m.kejadian if k["jenis"] == j]


class TesMesin(unittest.TestCase):
    def jalan(self, strategi="h37", hari=HARI, etf=None, aum=None, rd_naik=0.0001, **kw):
        data = sp.bangun(PRA + list(hari), etf=etf, aum=aum, rd_naik=rd_naik)
        m = sp.mesin(strategi, data, hari[0], **kw)
        m.jalan(hari)
        return m, data

    def test_masuk_target_h37_dan_h35(self):
        m, _ = self.jalan("h37", HARI[:1])
        e = m.ekuitas[0]
        self.assertAlmostEqual(e["lokal"], 40e6, delta=1)
        self.assertAlmostEqual(e["global"], 40e6, delta=1)
        self.assertLess(e["kas"] + e["emas"], 20e6)
        self.assertGreater(e["kas"] + e["emas"], 20e6 * 0.995)
        m35, _ = self.jalan("h35", HARI[:1])
        e = m35.ekuitas[0]
        self.assertAlmostEqual(e["lokal"], 50e6, delta=1)
        self.assertAlmostEqual(e["global"], 50e6, delta=1)
        self.assertEqual(m35.st["kas"], 0.0)
        self.assertFalse([t for t in m35.transaksi if t["kaki"] == "emas"])

    def test_idempoten(self):
        m, data = self.jalan("h37")
        n_t, n_k, n_e = len(m.transaksi), len(m.kejadian), len(m.ekuitas)
        m.jalan(HARI)
        self.assertEqual((len(m.transaksi), len(m.kejadian), len(m.ekuitas)), (n_t, n_k, n_e))
        ids = [t["_id"] for t in m.transaksi]
        self.assertEqual(len(ids), len(set(ids)))
        lanjut = sp.mesin("h37", data, HARI[0])
        lanjut.st = m.st
        lanjut.jalan(HARI)
        self.assertEqual(len(lanjut.transaksi), 0)

    def test_batas_20_persen_nilai_transaksi(self):
        m, _ = self.jalan("h37")
        beli = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"]
        self.assertTrue(beli)
        for t in beli:
            self.assertLessEqual(t["nilai"], 0.2 * t["nilai_transaksi_etf"] + 1e-6)
            self.assertLessEqual(t["pakai_batas"], 1.0 + 1e-9)
            self.assertEqual(t["unit"] % mp.LOT, 0)
        self.assertGreaterEqual(len(set(t["tgl"] for t in beli)), 3)
        self.assertEqual(len(jenis(m, "order_selesai")), 1)

    def test_hari_ke_15_membeli_di_harga_mana_pun(self):
        etf = {"AAA": sp.seri_etf(HARI_X, premium=0.05)}
        m, _ = self.jalan("h37", etf=etf)
        beli = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"]
        self.assertEqual(beli[0]["tgl"], str(HARI[14].date()))
        self.assertEqual(beli[0]["hari_order"], 15)
        self.assertEqual(len(jenis(m, "lewati_premium")), 14)
        self.assertTrue(jenis(m, "batas_hari_15"))
        for t in beli:
            self.assertLessEqual(t["pakai_batas"], 1.0 + 1e-9)
        self.assertAlmostEqual(beli[0]["premium"], 0.05)

    def test_premium_di_bawah_batas_beli_hari_pertama(self):
        etf = {"AAA": sp.seri_etf(HARI_X, premium=0.019)}
        m, _ = self.jalan("h37", etf=etf)
        beli = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"]
        self.assertEqual(beli[0]["tgl"], str(HARI[0].date()))
        self.assertFalse(jenis(m, "lewati_premium"))

    def test_data_kosong_tidak_ada_transaksi_emas_dan_tidak_dikarang(self):
        df = sp.seri_etf(HARI_X)
        kosong = [HARI[1], HARI[2]]
        df2 = df.drop(kosong)
        df2.loc[HARI[3], "premium"] = np.nan
        df2 = df2.sort_index()
        m, _ = self.jalan("h37", etf={"AAA": df2})
        tgl_beli = {t["tgl"] for t in m.transaksi if t["kaki"] == "emas"}
        for h in kosong + [HARI[3], HARI[4]]:
            self.assertNotIn(str(h.date()), tgl_beli)
        self.assertEqual(len(jenis(m, "data_kosong_emas")), 4)
        self.assertEqual(m.ekuitas[1]["tgl"], str(HARI[1].date()))

    def test_keputusan_memakai_premium_sejajar_dua_hari_sebelumnya(self):
        prem = lambda idx: np.where(idx <= HARI[2], 0.05, 0.005)
        etf = {"AAA": sp.seri_etf(HARI_X, premium=prem)}
        m, _ = self.jalan("h37", etf=etf)
        tgl_beli = sorted({t["tgl"] for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"})
        self.assertEqual(tgl_beli[0], str(HARI[5].date()))
        for i in range(5):
            self.assertNotIn(str(HARI[i].date()), tgl_beli)
        lewat = [k for k in jenis(m, "lewati_premium") if k["tgl"] == str(HARI[3].date())]
        self.assertEqual(len(lewat), 1)
        self.assertAlmostEqual(lewat[0]["premium_keputusan"], 0.05)
        self.assertEqual(len(jenis(m, "lewati_premium")), 5)
        pertama = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"][0]
        self.assertAlmostEqual(pertama["premium_keputusan"], 0.005)
        self.assertAlmostEqual(pertama["premium_eksekusi"], 0.005)
        self.assertEqual(pertama["premium"], pertama["premium_eksekusi"])

    def test_nav_kemarin_kosong_tidak_beli(self):
        df = sp.seri_etf(HARI_X)
        df.loc[HARI[2], "nav"] = np.nan
        df.loc[HARI[2], "premium"] = np.nan
        df.loc[HARI[1], "premium_sejajar"] = np.nan
        m, _ = self.jalan("h37", etf={"AAA": df})
        tgl_beli = {t["tgl"] for t in m.transaksi if t["kaki"] == "emas"}
        self.assertIn(str(HARI[2].date()), tgl_beli)
        self.assertNotIn(str(HARI[3].date()), tgl_beli)
        kosong = jenis(m, "data_kosong_emas")
        self.assertEqual([k["tgl"] for k in kosong], [str(HARI[3].date())])

    def test_ganti_etf_karena_aum(self):
        etf = {"AAA": sp.seri_etf(HARI_X), "BBB": sp.seri_etf(HARI_X, premium=0.01)}
        m, data = self.jalan("h37", HARI[:3], etf=etf, aum={"AAA": 20e9, "BBB": 20e9})
        self.assertEqual(m.st["etf"], "AAA")
        data.aum_nilai["AAA"] = 5e9
        m.jalan(HARI[:6])
        g = jenis(m, "ganti_etf")
        self.assertEqual(len(g), 1)
        self.assertEqual(m.st["etf"], "BBB")
        self.assertEqual(g[0]["alasan"], "AUM < Rp10 M")
        self.assertTrue(any(o["kunci"] == "etf:BBB" for o in m.st["antrean"]) or any(t["kunci"] == "etf:BBB" for t in m.transaksi))

    def test_ganti_etf_lima_hari_tanpa_transaksi(self):
        vol = lambda idx: np.where((idx >= HARI[10]) & (idx <= HARI[14]), 0.0, 125000.0)
        etf = {"AAA": sp.seri_etf(HARI_X, volume=vol), "BBB": sp.seri_etf(HARI_X)}
        m, _ = self.jalan("h37", HARI[:15], etf=etf, aum={"AAA": 20e9, "BBB": 20e9})
        g = jenis(m, "ganti_etf")
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["tgl"], str(HARI[14].date()))
        self.assertIn("tanpa transaksi", g[0]["alasan"])
        self.assertEqual(m.st["etf"], "BBB")

    def test_ganti_etf_gagal_bila_tidak_ada_pengganti(self):
        etf = {"AAA": sp.seri_etf(HARI_X)}
        m, data = self.jalan("h37", HARI[:2], etf=etf, aum={"AAA": 20e9})
        data.aum_nilai["AAA"] = 5e9
        m.jalan(HARI[:5])
        self.assertEqual(m.st["etf"], "AAA")
        self.assertEqual(len(jenis(m, "ganti_gagal")), 1)

    def test_h35_tidak_ada_emas(self):
        m, _ = self.jalan("h35")
        self.assertFalse([t for t in m.transaksi if t["kaki"] == "emas"])
        self.assertIsNone(m.st["etf"])


class TesRebalance(unittest.TestCase):
    HARI = sp.hari_kerja("2026-12-01", "2028-01-14")
    NAIK = {1: 0.0006, 2: 0.0006, 3: 0.0001}

    def jalan(self, strategi, hari, **kw):
        data = sp.bangun(hari, rd_naik=self.NAIK)
        m = sp.mesin(strategi, data, hari[0], **kw)
        m.jalan(hari)
        return m

    def test_rebalance_pertama_desember_2027_bukan_2026(self):
        m = self.jalan("h35", self.HARI)
        r = jenis(m, "rebalance")
        self.assertEqual([k["tgl"] for k in r], ["2027-12-31"])

    def test_desember_2026_dilewati(self):
        hari = [h for h in self.HARI if h <= pd.Timestamp("2027-01-29")]
        m = self.jalan("h37", hari)
        self.assertFalse(jenis(m, "rebalance"))

    def test_rebalance_dihidupkan_bila_pertama_2026(self):
        hari = [h for h in self.HARI if h <= pd.Timestamp("2027-01-29")]
        m = self.jalan("h37", hari, rebalance_pertama=2026)
        self.assertEqual([k["tgl"] for k in jenis(m, "rebalance")], ["2026-12-31"])

    def test_rebalance_mengembalikan_bobot_h35(self):
        m = self.jalan("h35", self.HARI)
        sebelum = [e for e in m.ekuitas if e["tgl"] == "2027-12-30"][0]
        sesudah = [e for e in m.ekuitas if e["tgl"] == "2027-12-31"][0]
        bobot = lambda e: e["lokal"] / (e["lokal"] + e["global"])
        self.assertGreater(abs(bobot(sebelum) - 0.5), 0.02)
        self.assertAlmostEqual(bobot(sesudah), 0.5, delta=0.005)

    def test_rebalance_h37_menambah_emas_dan_dana_menunggu_jadi_kas(self):
        m = self.jalan("h37", self.HARI)
        akhir = m.ekuitas[-1]
        self.assertAlmostEqual(akhir["emas"] / akhir["nilai"], 0.20, delta=0.01)
        self.assertAlmostEqual(akhir["lokal"] / akhir["nilai"], 0.40, delta=0.01)
        self.assertEqual(len(jenis(m, "rebalance")), 1)
        beli = [t for t in m.transaksi if t["kaki"] == "emas" and t["tgl"] >= "2027-12-31"]
        self.assertTrue(beli)

    def test_rebalance_h37_menjual_emas_dicicil_tanpa_syarat_premium(self):
        hari = self.HARI
        etf = {"AAA": sp.seri_etf(hari, premium=0.08, close=240.0, nilai=30e6)}
        data = sp.bangun(hari, etf=etf, rd_naik=0.0)
        m = sp.mesin("h37", data, hari[0], rebalance_pertama=2026)
        m.jalan([h for h in hari if h <= pd.Timestamp("2026-12-30")])
        m.st["unit"]["etf:AAA"] = m.st["unit"].get("etf:AAA", 0) + 300000
        m.jalan([h for h in hari if h <= pd.Timestamp("2027-02-26")])
        jual = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "jual"]
        self.assertTrue(jual)
        for t in jual:
            self.assertLessEqual(t["pakai_batas"], 1.0 + 1e-9)
            self.assertGreater(t["premium"], mp.PREMIUM_MAKS_BELI)
        self.assertGreaterEqual(len({t["tgl"] for t in jual}), 2)


class TesMasuk(unittest.TestCase):
    def test_masuk_ditunda_bila_harga_rd_kosong(self):
        data = sp.bangun(HARI[:5])
        data.rd_seri[3] = data.rd_seri[3].drop(HARI[0])
        m = sp.mesin("h35", data, HARI[0])
        m.jalan(HARI[:3])
        self.assertTrue(jenis(m, "masuk_ditunda"))
        self.assertEqual(m.st["masuk"], str(HARI[1].date()))

    def test_mulai_tanggal_tertentu(self):
        data = sp.bangun(HARI[:5])
        m = sp.mesin("h37", data, "2026-12-03")
        m.jalan(HARI[:5])
        self.assertEqual(m.st["masuk"], "2026-12-03")
        self.assertEqual(len(m.ekuitas), 3)

    def test_premium_naif_lama_hanya_dicatat(self):
        etf = {"AAA": sp.seri_etf(HARI_X, premium=0.005)}
        data = sp.bangun(PRA + list(HARI), etf=etf)
        m = sp.mesin("h37", data, HARI[0])
        m.jalan(HARI)
        pertama = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"][0]
        self.assertIn("premium_keputusan_naif", pertama)

    def test_pilih_awal_normal_bila_ada_data_60_hari(self):
        from backend.ingest import etf_emas as ee
        kand = [{"kode": "A", "aum": 20e9, "nilai_median": 30e6, "premium_mutlak_median": 0.01, "hari_data": 60, "hari_premium": 60, "lolos": True, "alasan": []},
                {"kode": "B", "aum": 30e9, "nilai_median": 30e6, "premium_mutlak_median": 0.005, "hari_data": 20, "hari_premium": 20, "lolos": True, "alasan": []}]
        r = ee.pilih_awal({"kandidat": kand, "hari": 60, "terpilih": "A"})
        self.assertEqual((r["terpilih"], r["tier"]), ("A", "normal"))

    def test_pilih_awal_fallback_riwayat_terpanjang_bukan_kas(self):
        from backend.ingest import etf_emas as ee
        kand = [{"kode": "A", "aum": 20e9, "nilai_median": 30e6, "premium_mutlak_median": 0.01, "hari_data": 14, "hari_premium": 13, "lolos": True, "alasan": []},
                {"kode": "B", "aum": 18e9, "nilai_median": 26e6, "premium_mutlak_median": 0.012, "hari_data": 20, "hari_premium": 19, "lolos": True, "alasan": []},
                {"kode": "C", "aum": 5e9, "nilai_median": 14e6, "premium_mutlak_median": 0.02, "hari_data": 60, "hari_premium": 60, "lolos": False, "alasan": ["AUM < Rp10 M"]}]
        r = ee.pilih_awal({"kandidat": kand, "hari": 60, "terpilih": "A"})
        self.assertEqual((r["terpilih"], r["tier"]), ("B", "riwayat_terpanjang"))
        self.assertIn("a2", r["alasan_pilih"])

    def test_pilih_awal_tanpa_yang_lolos_tetap_memilih_etf(self):
        from backend.ingest import etf_emas as ee
        kand = [{"kode": "C", "aum": 5e9, "nilai_median": 14e6, "premium_mutlak_median": 0.02, "hari_data": 60, "hari_premium": 60, "lolos": False, "alasan": ["AUM < Rp10 M"]},
                {"kode": "D", "aum": 1e9, "nilai_median": 0.0, "premium_mutlak_median": 0.07, "hari_data": 13, "hari_premium": 13, "lolos": False, "alasan": ["AUM < Rp10 M"]}]
        r = ee.pilih_awal({"kandidat": kand, "hari": 60, "terpilih": None})
        self.assertEqual((r["terpilih"], r["tier"]), ("C", "riwayat_terpanjang_tanpa_filter"))
    def test_telat_emas_dihitung_dalam_hari_bursa(self):
        d = mp.DataNyata.__new__(mp.DataNyata)
        d.hari = [pd.Timestamp(x) for x in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06")]
        d.emas_usd = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-11-02", "2026-11-03"]))
        self.assertEqual(d.telat_emas(pd.Timestamp("2026-11-03")), 0)
        self.assertEqual(d.telat_emas(pd.Timestamp("2026-11-05")), 2)
        self.assertEqual(d.telat_emas(pd.Timestamp("2026-11-06")), 3)

if __name__ == "__main__":
    unittest.main()
