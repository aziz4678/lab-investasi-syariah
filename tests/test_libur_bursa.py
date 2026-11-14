import unittest
from datetime import datetime

import pandas as pd

from backend.app.routers import cek_kesehatan as api
from backend.core import libur_bursa as lb


class TesLibur(unittest.TestCase):
    def test_jumlah_hari_libur_sesuai_kalender_bei(self):
        self.assertEqual(len(lb.LIBUR[2026]), 22)
        self.assertEqual(len(lb.LIBUR[2027]), 20)

    def test_semua_libur_jatuh_di_hari_kerja(self):
        for per in lb.LIBUR.values():
            for t in per:
                self.assertLess(pd.Timestamp(t).weekday(), 5, t)

    def test_tanggal_kunci(self):
        for t in ("2026-12-24", "2026-12-25", "2026-12-31", "2027-02-05", "2027-03-10", "2027-12-31"):
            self.assertIsNotNone(lb.nama_libur(t), t)
            self.assertFalse(lb.hari_bursa(t))
        for t in ("2026-11-30", "2026-12-01", "2027-01-04"):
            self.assertTrue(lb.hari_bursa(t), t)

    def test_akhir_pekan_bukan_hari_bursa(self):
        self.assertFalse(lb.hari_bursa("2026-11-14"))

    def test_hari_bursa_antara_membuang_libur(self):
        h = [str(x.date()) for x in lb.hari_bursa_antara("2026-12-22", "2026-12-28")]
        self.assertEqual(h, ["2026-12-22", "2026-12-23", "2026-12-28"])

    def test_tahun_terisi(self):
        self.assertTrue(lb.tahun_terisi(2026) and lb.tahun_terisi(2027))
        self.assertFalse(lb.tahun_terisi(2028))

    def test_cocok_dengan_data_ihsg_2026(self):
        from backend.db import harga
        ada = set(harga.ihsg().index)
        akhir = max(ada)
        absen = [str(x.date()) for x in pd.bdate_range("2026-01-01", akhir) if x not in ada]
        statis = sorted(t for t in lb.LIBUR[2026] if pd.Timestamp(t) <= akhir)
        self.assertEqual(absen, statis)


class TesEndpoint(unittest.TestCase):
    def test_waktu_cek_terakhir_dan_libur(self):
        r = api.susun([{"tanggal": "2026-11-16", "nama_cek": "a", "status": "ok", "pesan": "x"}], datetime(2026, 11, 16, 17, 46, 3))
        self.assertEqual(r["waktu_cek_terakhir"], "2026-11-16T17:46:03")
        self.assertIn("2026-12-24", r["libur"])
        self.assertIn("2027-12-31", r["libur"])

    def test_kosong_tanpa_waktu(self):
        r = api.susun([], None)
        self.assertIsNone(r["waktu_cek_terakhir"])
        self.assertEqual(r["tertinggi"], "ok")

    def test_tertinggi_gagal(self):
        r = api.susun([{"tanggal": "2026-11-16", "nama_cek": "a", "status": "peringatan", "pesan": "x"},
                       {"tanggal": "2026-11-16", "nama_cek": "b", "status": "gagal", "pesan": "y"}], datetime(2026, 11, 16))
        self.assertEqual(r["tertinggi"], "gagal")


if __name__ == "__main__":
    unittest.main()
