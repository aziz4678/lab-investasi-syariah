import unittest

import pandas as pd

from backend.paper import banding

TGL_SPLIT = "2026-11-12"
KALENDER = list(pd.bdate_range("2026-11-02", "2026-11-30"))
KALENDER_LIBUR = [t for t in KALENDER if t != pd.Timestamp("2026-11-16")]
CATATAN_AALI = [{"ticker": "AALI", "jenis": "split", "tgl": pd.Timestamp(TGL_SPLIT), "rasio": 31 / 30}]


def baris_selisih(keluar_paper, keluar_backtest):
    return {"ticker": "AALI", "tgl_sinyal": "2026-10-21", "status_paper": "jual", "status_backtest": "jual",
            "tgl_masuk_paper": "2026-10-22", "tgl_masuk_backtest": "2026-10-22",
            "tgl_keluar_paper": keluar_paper, "tgl_keluar_backtest": keluar_backtest}


class TesPengecualianSplit(unittest.TestCase):
    def cek(self, baris, catatan=CATATAN_AALI, kalender=KALENDER):
        return banding.dikecualikan_split(baris, catatan, kalender, pd.Timestamp("2026-11-30"))

    def test_dalam_jendela_dikecualikan(self):
        self.assertTrue(self.cek(baris_selisih("2026-11-13", "2026-11-16")))

    def test_di_luar_jendela_tetap_dihitung(self):
        self.assertFalse(self.cek(baris_selisih("2026-11-24", "2026-11-25")))

    def test_sebelum_split_tetap_dihitung(self):
        self.assertFalse(self.cek(baris_selisih("2026-11-10", "2026-11-11")))

    def test_batas_hari_bursa_ke_5(self):
        self.assertTrue(self.cek(baris_selisih("2026-11-19", "2026-11-23")))
        self.assertFalse(self.cek(baris_selisih("2026-11-20", "2026-11-23")))

    def test_libur_tidak_dihitung_sebagai_hari_bursa(self):
        self.assertFalse(self.cek(baris_selisih("2026-11-20", "2026-11-23")))
        self.assertTrue(self.cek(baris_selisih("2026-11-20", "2026-11-23"), kalender=KALENDER_LIBUR))
        self.assertFalse(self.cek(baris_selisih("2026-11-23", "2026-11-24"), kalender=KALENDER_LIBUR))

    def test_ticker_tanpa_split_tidak_dikecualikan(self):
        self.assertFalse(self.cek(baris_selisih("2026-11-13", "2026-11-16"), catatan=[]))
        self.assertFalse(self.cek(baris_selisih("2026-11-13", "2026-11-16"), catatan=None))

    def test_selisih_status_saja_memakai_tanggal_keluar_yang_ada(self):
        baris = baris_selisih(None, "2026-11-13")
        baris["status_paper"] = "aktif"
        self.assertTrue(self.cek(baris))
        baris = baris_selisih(None, "2026-11-26")
        baris["status_paper"] = "aktif"
        self.assertFalse(self.cek(baris))


if __name__ == "__main__":
    unittest.main()
