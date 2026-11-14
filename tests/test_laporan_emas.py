import unittest

import numpy as np
import pandas as pd

from backend.paper import laporan_emas as le
from backend.paper import mesin_pertumbuhan as mp
from backend.paper import sintetis_pertumbuhan as sp

HARI = sp.hari_kerja("2026-12-01", "2027-01-29")
PRA = [pd.Timestamp("2026-11-27"), pd.Timestamp("2026-11-30")]


def jalan(premium):
    etf = {"AAA": sp.seri_etf(PRA + HARI, premium=premium)}
    data = sp.bangun(PRA + HARI, etf=etf)
    m = sp.mesin("h37", data, HARI[0])
    m.jalan(HARI)
    return m, data


class TesLaporan(unittest.TestCase):
    def test_premium_dibayar_dan_rem_tercatat(self):
        m, data = jalan(0.05)
        r = le.hitung(m.transaksi, m.ekuitas, data.etf_df, data.hari)
        self.assertTrue(r["pembelian"])
        p = r["pembelian"][0]
        self.assertTrue(p["lewat_rem"])
        self.assertAlmostEqual(p["premium_keputusan"], 0.05)
        self.assertIn("nav_sejajar_keputusan", p)
        self.assertGreater(r["ringkasan"]["lewat_rem"], 0)
        self.assertIsNotNone(r["ringkasan"]["premium_dibayar_tertimbang"])

    def test_pembanding_nav_lebih_tinggi_bila_beli_di_premium(self):
        m, data = jalan(0.03)
        r = le.hitung(m.transaksi, m.ekuitas, data.etf_df, data.hari)
        akhir = r["seri"][-1]
        self.assertLess(akhir["ekuitas"], akhir["ekuitas_kaki_emas_nav"])
        self.assertGreater(r["ringkasan"]["premium_dibayar_tertimbang"], 0.0)

    def test_tanpa_pembelian_pembanding_sama(self):
        r = le.hitung([], [{"tgl": "2026-12-01", "nilai": 100.0, "emas": 0.0}], {}, HARI)
        self.assertEqual(r["seri"][0]["selisih"], 0.0)
        self.assertEqual(r["ringkasan"]["pembelian"], 0)

    def test_nav_sejajar_memakai_hari_berikutnya_dan_perkiraan_di_akhir(self):
        df = pd.DataFrame({"nav": [100.0, 110.0, np.nan]}, index=pd.to_datetime(["2026-12-01", "2026-12-02", "2026-12-03"]))
        hari = list(df.index)
        self.assertEqual(le.nav_sejajar(df, hari, "2026-12-01"), (110.0, False))
        self.assertEqual(le.nav_sejajar(df, hari, "2026-12-02"), (110.0, True))


if __name__ == "__main__":
    unittest.main()
