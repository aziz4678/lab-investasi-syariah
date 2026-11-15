import unittest

import pandas as pd

from backend.paper import mesin_pertumbuhan as mp
from backend.paper import sintetis_pertumbuhan as sp

HARI = sp.hari_kerja("2026-12-01", "2026-12-15")
PRA = [pd.Timestamp("2026-11-27"), pd.Timestamp("2026-11-30")]
SPUS = {"id": "SPUS", "nama": "SPUS", "mu": "USD", "jenis": "spus", "fee": mp.FEE_SPUS}
PRODUK = {"lokal": sp.PRODUK["lokal"], "global": [SPUS]}


class DataSpus(sp.DataSintetis):
    def __init__(self, hari, rd, etf, spus, aum=None):
        super().__init__(hari, rd, etf, aum)
        self.spus_seri = spus

    def rd(self, fid, mu, D):
        if str(fid) == mp.ID_SPUS:
            s = self.spus_seri[self.spus_seri.index <= D]
            return float(s.iloc[-1]) if len(s) else None
        return super().rd(fid, mu, D)

    def tgl_harga_spus(self, D):
        s = self.spus_seri[self.spus_seri.index <= D]
        return (s.index[-1] if len(s) else None), D


def bangun(hari_spus):
    hari = PRA + list(HARI)
    dasar = sp.bangun(hari)
    spus = pd.Series([1_000_000.0 * (1.001 ** i) for i in range(len(hari_spus))], index=pd.DatetimeIndex(hari_spus))
    return DataSpus(hari, dasar.rd_seri, dasar.etf_df, spus, dasar.aum_nilai), spus


def jalankan(hari_spus):
    data, spus = bangun(hari_spus)
    m = mp.Mesin("h35", data, mulai=HARI[0])
    m.st["produk"] = PRODUK
    m.jalan(HARI)
    return m, spus


class TesSpus(unittest.TestCase):
    def test_masuk_memotong_biaya_transaksi(self):
        m, spus = jalankan(PRA + list(HARI))
        t = [x for x in m.transaksi if x["kunci"] == "rd:SPUS" and x["sisi"] == "beli"][0]
        per = 0.5 * mp.MODAL
        self.assertAlmostEqual(t["fee"], per * mp.FEE_SPUS, places=4)
        self.assertAlmostEqual(t["unit"] * t["harga"] + t["fee"], per, places=4)
        self.assertAlmostEqual(m.st["unit"]["rd:SPUS"], per * (1 - mp.FEE_SPUS) / spus.loc[HARI[0]], places=8)

    def test_produk_rd_tanpa_biaya(self):
        m, _ = jalankan(PRA + list(HARI))
        for x in m.transaksi:
            if x["kunci"] != "rd:SPUS":
                self.assertEqual(x["fee"], 0.0)

    def test_harga_kosong_pakai_nilai_terakhir_dan_dicatat(self):
        hari_spus = [h for h in PRA + list(HARI) if h != HARI[2]]
        m, spus = jalankan(hari_spus)
        ffill = [k for k in m.kejadian if k["jenis"] == "harga_spus_ffill"]
        self.assertEqual([k["tgl"] for k in ffill], [HARI[2].strftime("%Y-%m-%d")])
        self.assertEqual(ffill[0]["tgl_spus"], HARI[1].strftime("%Y-%m-%d"))
        ekuitas = {e["tgl"]: e for e in m.ekuitas}
        sebelum, hari_kosong = ekuitas[HARI[1].strftime("%Y-%m-%d")], ekuitas[HARI[2].strftime("%Y-%m-%d")]
        self.assertAlmostEqual(sebelum["global"], hari_kosong["global"], places=4)

    def test_tanpa_data_spus_masuk_ditunda(self):
        data, _ = bangun(PRA + list(HARI))
        data.spus_seri = data.spus_seri.iloc[0:0]
        m = mp.Mesin("h35", data, mulai=HARI[0])
        m.st["produk"] = PRODUK
        m.jalan(HARI)
        self.assertFalse(m.st["aktif"])
        self.assertTrue([k for k in m.kejadian if k["jenis"] == "masuk_ditunda"])

    def test_id_dari_kunci(self):
        self.assertEqual(mp.id_dari_kunci("rd:2233"), 2233)
        self.assertEqual(mp.id_dari_kunci("rd:SPUS"), "SPUS")


if __name__ == "__main__":
    unittest.main()
