import unittest

import pandas as pd

from backend.paper import cek_kesehatan as ck
from backend.paper import mesin_pertumbuhan as mp
from backend.paper import parameter_uji_maju as pu

STATUS = {"amandemen": [{"id": "a1", "mulai": "2026-12-01"}, {"id": "a2", "mulai": "2026-12-01"}], "rebalance_pertama": "Desember 2027", "pilih_etf_pertama": "hari bursa terakhir Nov 2026"}


class FakeKoleksi:
    def __init__(self, dok):
        self.dok = dok

    def find_one(self, _):
        return self.dok


class FakeDb:
    def __init__(self, h35, h37):
        self.k = {"paper_h35_status": FakeKoleksi(h35), "paper_h37_status": FakeKoleksi(h37)}

    def __getitem__(self, nama):
        return self.k[nama]


class TesParameter(unittest.TestCase):
    def test_dari_status_sama_dengan_kode(self):
        p = pu.dari_status(STATUS)
        self.assertEqual(p["mulai"], mp.MULAI)
        self.assertEqual(p["rebalance_pertama"], mp.REBALANCE_PERTAMA)
        self.assertEqual(p["tgl_pilih"], mp.TGL_PILIH)
        self.assertEqual(p["batas_awal"], pd.Timestamp("2026-12-10"))
        self.assertEqual(pu.selisih(p), [])

    def test_verifikasi_lulus_bila_sama(self):
        self.assertEqual(pu.verifikasi(FakeDb(STATUS, STATUS))["mulai"], mp.MULAI)

    def test_verifikasi_error_bila_mulai_beda(self):
        beda = dict(STATUS, amandemen=[{"id": "a1", "mulai": "2027-01-04"}])
        with self.assertRaises(RuntimeError):
            pu.verifikasi(FakeDb(beda, beda))

    def test_verifikasi_error_bila_rebalance_beda(self):
        beda = dict(STATUS, rebalance_pertama="Desember 2026")
        with self.assertRaises(RuntimeError):
            pu.verifikasi(FakeDb(beda, beda))

    def test_verifikasi_error_bila_h35_h37_berbeda(self):
        beda = dict(STATUS, rebalance_pertama="Desember 2026")
        with self.assertRaises(RuntimeError):
            pu.verifikasi(FakeDb(STATUS, beda))

    def test_status_tak_terbaca_error(self):
        with self.assertRaises(ValueError):
            pu.dari_status({"amandemen": [{"mulai": "2026-12-01"}]})

    def test_cek_parameter_mesin_gagal_bila_beda(self):
        c = ck.Ctx("2026-11-20", beda_parameter=["MULAI kode 2026-12-01 != DB 2027-01-04"])
        self.assertEqual(ck.cek_parameter_mesin(c)[0]["status"], "gagal")
        self.assertEqual(ck.cek_parameter_mesin(ck.Ctx("2026-11-20"))[0]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
