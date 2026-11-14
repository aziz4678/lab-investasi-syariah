import unittest

from backend.paper import cek_kesehatan as ck
from backend.paper import jejak_paper as jp


class TesJejak(unittest.TestCase):
    def test_hash_stabil_dan_peka(self):
        a = {"_id": 1, "x": 1.5, "y": [1, 2]}
        self.assertEqual(jp.hash_dok(a), jp.hash_dok({"y": [1, 2], "x": 1.5, "_id": 1}))
        self.assertNotEqual(jp.hash_dok(a), jp.hash_dok({"_id": 1, "x": 1.6, "y": [1, 2]}))

    def test_bandingkan_dokumen_baru_boleh_lama_berubah_atau_hilang_tidak(self):
        lama = {"paper_ekuitas": [["a", "h1"], ["b", "h2"]]}
        self.assertEqual(jp.bandingkan(lama, {"paper_ekuitas": [["a", "h1"], ["b", "h2"], ["c", "h3"]]}), [])
        self.assertEqual(jp.bandingkan(lama, {"paper_ekuitas": [["a", "h1"], ["b", "XX"]]}), ["paper_ekuitas/b berubah"])
        self.assertEqual(jp.bandingkan(lama, {"paper_ekuitas": [["a", "h1"]]}), ["paper_ekuitas/b hilang"])
        self.assertEqual(jp.bandingkan(lama, {}), ["paper_ekuitas/a hilang", "paper_ekuitas/b hilang"])

    def test_bandingkan_tanpa_lama(self):
        self.assertEqual(jp.bandingkan(None, {"x": [["a", "h"]]}), [])

    def test_koleksi_mutable_tidak_dicek(self):
        for c in ("paper_posisi", "paper_status", "paper_h37_posisi", "paper_h35_status", "paper_h22_posisi", "paper_h22_status"):
            self.assertIn(c, jp.BUKAN_APPEND_ONLY)


class TesCekSidik(unittest.TestCase):
    def c(self, sidik):
        return ck.Ctx("2026-11-20", sidik=sidik, kalender=[__import__("pandas").Timestamp("2026-11-19"), __import__("pandas").Timestamp("2026-11-20")])

    def test_ok(self):
        r = ck.cek_sidik_paper(self.c({"snapshot": "2026-11-19", "anomali": [], "live_beda": [], "dokumen": 50, "koleksi": 8}))
        self.assertEqual(r[0]["status"], "ok")

    def test_belum_ada_snapshot_peringatan(self):
        self.assertEqual(ck.cek_sidik_paper(self.c({"snapshot": None, "anomali": [], "live_beda": []}))[0]["status"], "peringatan")

    def test_live_beda_gagal(self):
        r = ck.cek_sidik_paper(self.c({"snapshot": "2026-11-19", "anomali": [], "live_beda": ["paper_ekuitas/x berubah"], "dokumen": 5, "koleksi": 1}))
        self.assertEqual(r[0]["status"], "gagal")

    def test_anomali_lama_tetap_gagal(self):
        r = ck.cek_sidik_paper(self.c({"snapshot": "2026-11-19", "anomali": ["2026-11-18: paper_sinyal/z hilang"], "live_beda": [], "dokumen": 5, "koleksi": 1}))
        self.assertEqual(r[0]["status"], "gagal")

    def test_snapshot_telat_peringatan(self):
        import pandas as pd
        kal = list(pd.bdate_range("2026-11-02", "2026-11-20"))
        c = ck.Ctx("2026-11-20", kalender=kal, sidik={"snapshot": "2026-11-09", "anomali": [], "live_beda": [], "dokumen": 5, "koleksi": 1})
        self.assertEqual(ck.cek_sidik_paper(c)[0]["status"], "peringatan")


if __name__ == "__main__":
    unittest.main()
