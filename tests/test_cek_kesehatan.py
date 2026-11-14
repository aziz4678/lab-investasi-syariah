import unittest
from datetime import datetime

import pandas as pd

from backend.paper import cek_kesehatan as ck

KAL = list(pd.bdate_range("2026-11-02", "2026-12-31"))
KAL_LIBUR_30 = [x for x in KAL if x != pd.Timestamp("2026-11-30")]


def status_ok(awal=None, aktif=False, alasan="aturan normal"):
    st = {"dikunci": True, "aktif": aktif, "mesin": {"pilih_awal": awal, "antrean": []}}
    if alasan:
        st["pilih_etf_alasan"] = alasan
        st["pilih_etf_tier"] = "normal"
    return st


def koleksi(st35=None, st37=None, jumlah=None, transaksi=None, ekuitas=None):
    nol = {"posisi": 0, "transaksi": 0, "ekuitas": 0, "kejadian": 0}
    return {k: {"status": s if s is not None else status_ok(), "jumlah": jumlah or nol, "transaksi": (transaksi or {}).get(k, []), "ekuitas": (ekuitas or {}).get(k, [])}
            for k, s in (("h35", st35), ("h37", st37))}


def ctx(tgl, kal=KAL, **kw):
    return ck.Ctx(tgl, kal, **kw)


def satu(daftar):
    assert len(daftar) == 1, daftar
    return daftar[0]


class TesEmas(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(satu(ck.cek_emas_telat(ctx("2026-11-16", telat_emas=2)))["status"], "ok")

    def test_gagal(self):
        self.assertEqual(satu(ck.cek_emas_telat(ctx("2026-11-16", telat_emas=3)))["status"], "gagal")


class TesJob(unittest.TestCase):
    def test_ok(self):
        c = ctx("2026-11-16", langkah=[{"jenis": "uji_maju_harian", "status": "selesai"}], pekerjaan=[{"jenis": "uji_maju_harian", "status": "selesai", "mulai": "1"}])
        self.assertEqual(satu(ck.cek_job_jadwal(c))["status"], "ok")

    def test_job_kritis_gagal(self):
        c = ctx("2026-11-16", pekerjaan=[{"jenis": "emas_panjang_perbarui", "status": "gagal", "mulai": "1"}])
        self.assertEqual(satu(ck.cek_job_jadwal(c))["status"], "gagal")

    def test_job_lain_peringatan(self):
        c = ctx("2026-11-16", pekerjaan=[{"jenis": "logo_perbarui", "status": "gagal", "mulai": "1"}, {"jenis": "uji_maju_harian", "status": "selesai", "mulai": "2"}])
        self.assertEqual(satu(ck.cek_job_jadwal(c))["status"], "peringatan")

    def test_ulang_berhasil_menimpa_gagal(self):
        c = ctx("2026-11-16", pekerjaan=[{"jenis": "uji_maju_harian", "status": "gagal", "mulai": "1"}, {"jenis": "uji_maju_harian", "status": "selesai", "mulai": "2"}])
        self.assertEqual(satu(ck.cek_job_jadwal(c))["status"], "ok")

    def test_tanpa_catatan_sore_gagal_pagi_ok(self):
        self.assertEqual(satu(ck.cek_job_jadwal(ctx("2026-11-16", sekarang=datetime(2026, 11, 16, 18, 0))))["status"], "gagal")
        self.assertEqual(satu(ck.cek_job_jadwal(ctx("2026-11-16", sekarang=datetime(2026, 11, 16, 9, 0))))["status"], "ok")

    def test_bukan_hari_bursa_tidak_dicek(self):
        self.assertEqual(satu(ck.cek_job_jadwal(ctx("2026-11-14")))["status"], "ok")


class TesSeri(unittest.TestCase):
    def test_ok(self):
        c = ctx("2026-11-16", seri={"NAV RD": pd.Timestamp("2026-11-13"), "ETF emas": pd.Timestamp("2026-11-16")})
        self.assertEqual(satu(ck.cek_seri_data(c))["status"], "ok")

    def test_peringatan_telat_4(self):
        c = ctx("2026-11-20", seri={"NAV RD": pd.Timestamp("2026-11-13")})
        self.assertEqual(c.telat(pd.Timestamp("2026-11-13")), 5)
        c2 = ctx("2026-11-19", seri={"NAV RD": pd.Timestamp("2026-11-13")})
        self.assertEqual(satu(ck.cek_seri_data(c2))["status"], "peringatan")

    def test_gagal_telat_6(self):
        c = ctx("2026-11-23", seri={"idx_harian": pd.Timestamp("2026-11-13")})
        self.assertEqual(satu(ck.cek_seri_data(c))["status"], "gagal")

    def test_seri_tanpa_data_gagal(self):
        self.assertEqual(satu(ck.cek_seri_data(ctx("2026-11-16", seri={"kurs USD": None})))["status"], "gagal")


class TesBelumMulai(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(satu(ck.cek_belum_mulai(ctx("2026-11-16", koleksi=koleksi())))["status"], "ok")

    def test_gagal_ada_transaksi(self):
        k = koleksi(jumlah={"posisi": 0, "transaksi": 1, "ekuitas": 0, "kejadian": 0})
        self.assertEqual(satu(ck.cek_belum_mulai(ctx("2026-11-16", koleksi=k)))["status"], "gagal")

    def test_gagal_aktif(self):
        k = koleksi(st35=status_ok(aktif=True))
        self.assertEqual(satu(ck.cek_belum_mulai(ctx("2026-11-16", koleksi=k)))["status"], "gagal")

    def test_gagal_belum_terkunci(self):
        st = status_ok()
        st["dikunci"] = False
        self.assertEqual(satu(ck.cek_belum_mulai(ctx("2026-11-16", koleksi=koleksi(st37=st))))["status"], "gagal")

    def test_tidak_aktif_setelah_mulai(self):
        self.assertEqual(ck.cek_belum_mulai(ctx("2026-12-01", koleksi=koleksi())), [])


class TesPilih(unittest.TestCase):
    def k(self, terpilih="XGLD", alasan="aturan normal"):
        return koleksi(st37=status_ok(awal={"terpilih": terpilih} if terpilih is not None else {"terpilih": None}, alasan=alasan))

    def test_belum_waktunya(self):
        self.assertEqual(ck.cek_pilih_etf(ctx("2026-11-27", koleksi=self.k())), [])

    def test_30_nov_ok(self):
        self.assertEqual(satu(ck.cek_pilih_etf(ctx("2026-11-30", koleksi=self.k())))["status"], "ok")

    def test_30_nov_terpilih_none_gagal(self):
        self.assertEqual(satu(ck.cek_pilih_etf(ctx("2026-11-30", koleksi=self.k(terpilih=None))))["status"], "gagal")

    def test_30_nov_alasan_hilang_gagal(self):
        self.assertEqual(satu(ck.cek_pilih_etf(ctx("2026-11-30", koleksi=self.k(alasan=None))))["status"], "gagal")

    def test_30_nov_libur_dicek_hari_bursa_berikutnya(self):
        self.assertEqual(ck.cek_pilih_etf(ctx("2026-11-30", kal=KAL_LIBUR_30, koleksi=self.k(terpilih=None))), [])
        self.assertEqual(satu(ck.cek_pilih_etf(ctx("2026-12-01", kal=KAL_LIBUR_30, koleksi=self.k(terpilih=None))))["status"], "gagal")
        self.assertEqual(satu(ck.cek_pilih_etf(ctx("2026-12-01", kal=KAL_LIBUR_30, koleksi=self.k())))["status"], "ok")


def trx(tgl, pakai=0.8, kaki="emas", sisi="beli"):
    return {"tgl": tgl, "kaki": kaki, "sisi": sisi, "pakai_batas": pakai}


class TesTransaksi(unittest.TestCase):
    def test_hari_pertama_belum_jatuh_tempo(self):
        self.assertEqual(satu(ck.cek_transaksi_pertama(ctx("2026-12-01", koleksi=koleksi())))["status"], "ok")

    def test_hari_kedua_tanpa_transaksi_gagal(self):
        self.assertEqual(satu(ck.cek_transaksi_pertama(ctx("2026-12-02", koleksi=koleksi())))["status"], "gagal")

    def test_hari_kedua_ada_transaksi_ok(self):
        k = koleksi(transaksi={"h35": [trx("2026-12-01", kaki="lokal")], "h37": [trx("2026-12-01", kaki="lokal")]})
        self.assertEqual(satu(ck.cek_transaksi_pertama(ctx("2026-12-02", koleksi=k)))["status"], "ok")

    def test_hanya_satu_strategi_gagal(self):
        k = koleksi(transaksi={"h37": [trx("2026-12-01", kaki="lokal")]})
        h = satu(ck.cek_transaksi_pertama(ctx("2026-12-02", koleksi=k)))
        self.assertEqual(h["status"], "gagal")
        self.assertIn("H35", h["pesan"])

    def test_di_luar_jendela(self):
        self.assertEqual(ck.cek_transaksi_pertama(ctx("2026-12-11", koleksi=koleksi())), [])
        self.assertEqual(ck.cek_transaksi_pertama(ctx("2026-11-27", koleksi=koleksi())), [])

    def test_batas_20_ok(self):
        k = koleksi(transaksi={"h37": [trx("2026-12-01", 0.99), trx("2026-12-02", 1.0)]})
        self.assertEqual(satu(ck.cek_batas_20(ctx("2026-12-03", koleksi=k)))["status"], "ok")

    def test_batas_20_gagal(self):
        k = koleksi(transaksi={"h37": [trx("2026-12-01", 1.3)]})
        self.assertEqual(satu(ck.cek_batas_20(ctx("2026-12-03", koleksi=k)))["status"], "gagal")

    def test_batas_20_tidak_aktif_sebelum_mulai(self):
        self.assertEqual(ck.cek_batas_20(ctx("2026-11-20", koleksi=koleksi())), [])


class TesRem(unittest.TestCase):
    def k(self, hari=None, sisa=5e6, masuk="2026-12-01"):
        st = status_ok()
        st["mesin"]["masuk"] = masuk
        st["mesin"]["antrean"] = [] if hari is None else [{"jenis": "etf_beli", "hari": hari, "sisa": sisa}]
        return koleksi(st37=st)

    def test_belum_masuk(self):
        self.assertEqual(satu(ck.cek_rem_15(ctx("2026-12-03", koleksi=self.k(masuk=None))))["status"], "ok")

    def test_selesai(self):
        self.assertEqual(satu(ck.cek_rem_15(ctx("2026-12-10", koleksi=self.k())))["status"], "ok")

    def test_masih_dalam_batas(self):
        self.assertEqual(satu(ck.cek_rem_15(ctx("2026-12-10", koleksi=self.k(hari=8))))["status"], "ok")

    def test_lewat_rem_gagal(self):
        self.assertEqual(satu(ck.cek_rem_15(ctx("2026-12-23", koleksi=self.k(hari=15))))["status"], "gagal")


class TesBolong(unittest.TestCase):
    def ek(self, hari):
        return {"h35": list(hari), "h37": list(hari)}

    def test_lengkap_ok(self):
        wajib = [str(h.date()) for h in KAL if pd.Timestamp("2026-12-01") <= h < pd.Timestamp("2026-12-04")]
        self.assertEqual(satu(ck.cek_hari_bolong(ctx("2026-12-04", koleksi=koleksi(ekuitas=self.ek(wajib)))))["status"], "ok")

    def test_bolong_gagal(self):
        k = koleksi(ekuitas={"h35": ["2026-12-01", "2026-12-03"], "h37": ["2026-12-01", "2026-12-02", "2026-12-03"]})
        h = satu(ck.cek_hari_bolong(ctx("2026-12-04", koleksi=k)))
        self.assertEqual(h["status"], "gagal")
        self.assertIn("H35 bolong 1", h["pesan"])

    def test_akhir_pekan_memakai_hari_bursa_terakhir(self):
        wajib = [str(h.date()) for h in KAL if pd.Timestamp("2026-12-01") <= h < pd.Timestamp("2026-12-04")]
        self.assertEqual(satu(ck.cek_hari_bolong(ctx("2026-12-05", koleksi=koleksi(ekuitas=self.ek(wajib)))))["status"], "ok")

    def test_hari_mulai_belum_dicek(self):
        self.assertEqual(ck.cek_hari_bolong(ctx("2026-12-01", koleksi=koleksi())), [])


class TesPengingat(unittest.TestCase):
    def test_dalam_30_hari(self):
        h = ck.cek_pengingat(ctx("2027-09-25"))
        self.assertEqual([x["nama_cek"] for x in h], ["pengingat_H11a"])
        self.assertEqual(h[0]["status"], "info")

    def test_di_luar_jendela(self):
        self.assertEqual(ck.cek_pengingat(ctx("2027-08-01")), [])

    def test_tiga_pengingat(self):
        self.assertEqual([x["nama_cek"] for x in ck.cek_pengingat(ctx("2027-12-20"))], ["pengingat_H35_H37"])
        self.assertEqual([x["nama_cek"] for x in ck.cek_pengingat(ctx("2027-10-15"))], ["pengingat_H11a", "pengingat_H29"])


class TesRunner(unittest.TestCase):
    def test_pemeriksa_error_dilaporkan_gagal(self):
        def rusak(c):
            raise ValueError("data rusak")
        asli = ck.CEK
        ck.CEK = [rusak]
        try:
            h = ck.jalankan_cek(ctx("2026-11-16"))
        finally:
            ck.CEK = asli
        self.assertEqual(satu(h)["status"], "gagal")
        self.assertIn("pemeriksa error", h[0]["pesan"])

    def test_jalankan_semua_tanpa_menulis(self):
        c = ctx("2026-11-16", telat_emas=0, seri={"NAV RD": pd.Timestamp("2026-11-16")}, koleksi=koleksi(),
                langkah=[{"jenis": "uji_maju_harian", "status": "selesai"}], pekerjaan=[{"jenis": "uji_maju_harian", "status": "selesai", "mulai": "1"}])
        nama = {x["nama_cek"]: x["status"] for x in ck.jalankan_cek(c)}
        self.assertEqual(nama, {"emas_telat": "ok", "job_jadwal": "ok", "seri_data": "ok", "belum_mulai": "ok"})


if __name__ == "__main__":
    unittest.main()
