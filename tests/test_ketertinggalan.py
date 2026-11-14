import copy
import unittest

import numpy as np
import pandas as pd

from backend.paper import ketertinggalan as kt
from backend.paper import sintetis_pertumbuhan as sp

HARI = sp.hari_kerja("2026-12-01", "2027-01-29")
PRA = [pd.Timestamp("2026-11-27"), pd.Timestamp("2026-11-30")]


def data_uji():
    prem = lambda idx: np.where(np.arange(len(idx)) % 4 == 0, 0.03, 0.004)
    etf = {"AAA": sp.seri_etf(PRA + HARI, premium=prem)}
    return sp.bangun(PRA + HARI, etf=etf, rd_naik=0.0003)


def ringkas(m):
    return ([{k: v for k, v in t.items()} for t in m.transaksi], [e for e in m.ekuitas], [k for k in m.kejadian])


class TesKejarKetinggalan(unittest.TestCase):
    def jalan_harian(self, strategi, hari):
        data = data_uji()
        st = None
        semua = [], [], []
        for h in hari:
            m = sp.mesin(strategi, data, HARI[0], state=copy.deepcopy(st)) if st is not None else sp.mesin(strategi, data, HARI[0])
            m.st["produk"] = sp.PRODUK
            m.jalan([h])
            st = m.st
            for a, b in zip(semua, ringkas(m)):
                a.extend(b)
        return semua, st

    def jalan_tertinggal(self, strategi, hari, terlewat):
        data = data_uji()
        st = None
        semua = [], [], []
        i = 0
        while i < len(hari):
            n = terlewat if i == 5 else 1
            blok = hari[i:i + n]
            m = sp.mesin(strategi, data, HARI[0], state=copy.deepcopy(st)) if st is not None else sp.mesin(strategi, data, HARI[0])
            m.st["produk"] = sp.PRODUK
            m.jalan(blok)
            st = m.st
            for a, b in zip(semua, ringkas(m)):
                a.extend(b)
            i += n
        return semua, st

    def cek_identik(self, strategi):
        hari = HARI[:14]
        normal, st1 = self.jalan_harian(strategi, hari)
        terlewat, st2 = self.jalan_tertinggal(strategi, hari, 3)
        self.assertEqual(normal[0], terlewat[0])
        self.assertEqual(normal[1], terlewat[1])
        self.assertEqual(normal[2], terlewat[2])
        self.assertEqual(st1, st2)
        self.assertTrue(normal[0])

    def test_tiga_hari_terlewat_identik_h37(self):
        self.cek_identik("h37")

    def test_tiga_hari_terlewat_identik_h35(self):
        self.cek_identik("h35")

    def test_sepuluh_hari_terlewat_identik(self):
        hari = HARI[:20]
        normal, st1 = self.jalan_harian("h37", hari)
        data = data_uji()
        m = sp.mesin("h37", data, HARI[0])
        m.st["produk"] = sp.PRODUK
        m.jalan(hari[:5])
        st = copy.deepcopy(m.st)
        m2 = sp.mesin("h37", data, HARI[0], state=st)
        m2.jalan(hari[5:15])
        m3 = sp.mesin("h37", data, HARI[0], state=copy.deepcopy(m2.st))
        m3.jalan(hari[15:])
        self.assertEqual(m3.st, st1)


class TesBatas(unittest.TestCase):
    def test_hitung_hari_tertinggal(self):
        h = kt.hari_tertinggal(HARI, pd.Timestamp("2026-12-03"), pd.Timestamp("2026-12-08"))
        self.assertEqual([x.day for x in h], [4, 7, 8])

    def test_batas_tepat_10_boleh_11_ditolak(self):
        h10 = kt.hari_tertinggal(HARI, pd.Timestamp("2026-12-01"), pd.Timestamp("2026-12-15"))
        self.assertEqual(len(h10), 10)
        self.assertFalse(kt.terlalu_jauh(h10))
        h11 = kt.hari_tertinggal(HARI, pd.Timestamp("2026-12-01"), pd.Timestamp("2026-12-16"))
        self.assertTrue(kt.terlalu_jauh(h11))
        self.assertIn("Tidak diproses otomatis", kt.pesan_tolak("uji maju H37", h11))

    def test_belum_pernah_proses_semua_dihitung(self):
        self.assertEqual(len(kt.hari_tertinggal(HARI[:5], None, HARI[4])), 5)


class StubKoleksi:
    def __init__(self, dok):
        self.dok = dok
        self.tulis = 0

    def find_one(self, *a, **k):
        return self.dok

    def update_one(self, *a, **k):
        self.tulis += 1

    def count_documents(self, *a, **k):
        return 0


class StubDb:
    def __init__(self, st):
        self.k = {}
        self.st = st

    def __getitem__(self, nama):
        if nama not in self.k:
            self.k[nama] = StubKoleksi(self.st if nama.endswith("_status") else None)
        return self.k[nama]


class StubData:
    hari = HARI


class TesTolakOtomatis(unittest.TestCase):
    def test_uji_maju_menolak_lebih_dari_10_hari(self):
        from unittest import mock
        from backend.paper import uji_maju_pertumbuhan as um
        st = {"dikunci": True, "aktif": True, "mesin": {"terakhir": "2026-12-01", "pilih_awal": {"terpilih": "AAA"}}, "rebalance_pertama": "Desember 2027",
              "pilih_etf_pertama": "hari bursa terakhir Nov 2026", "amandemen": [{"id": "a1", "mulai": "2026-12-01"}]}
        db = StubDb(st)
        with mock.patch.object(um.d, "koneksi", return_value=db), mock.patch.object(um.mp, "DataNyata", return_value=StubData()):
            with self.assertRaises(SystemExit) as r:
                um.harian("2027-01-05")
        self.assertIn("Tidak diproses otomatis", str(r.exception))
        self.assertIn("H35", str(r.exception))

    def test_uji_maju_tidak_menolak_bila_tepat_di_batas(self):
        from unittest import mock
        from backend.paper import uji_maju_pertumbuhan as um
        st = {"dikunci": True, "aktif": True, "mesin": {"terakhir": "2026-12-04", "pilih_awal": {"terpilih": "AAA"}}, "rebalance_pertama": "Desember 2027",
              "pilih_etf_pertama": "hari bursa terakhir Nov 2026", "amandemen": [{"id": "a1", "mulai": "2026-12-01"}]}
        db = StubDb(st)
        with mock.patch.object(um.d, "koneksi", return_value=db), mock.patch.object(um.mp, "DataNyata", return_value=StubData()):
            try:
                um.harian("2026-12-21")
            except SystemExit as e:
                self.fail(f"ditolak padahal tepat di batas: {e}")
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
