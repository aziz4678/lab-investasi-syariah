import math

import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.db import koneksi as d
from backend.ingest import etf_emas as ee

MODAL = 100_000_000
MULAI = pd.Timestamp("2026-12-01")
REBALANCE_PERTAMA = 2027
BATAS_NILAI = 0.20
PREMIUM_MAKS_BELI = 0.02
HARI_BATAS = 15
HARI_TANPA_TRANSAKSI = 5
HARI_HILANG = 20
FEE_BELI = 0.0015
FEE_JUAL = 0.0025
TICK = 1.0
LOT = 100
TAK_HINGGA = 1e18
BOBOT = {"h35": {"lokal": 0.5, "global": 0.5}, "h37": {"lokal": 0.4, "global": 0.4, "emas": 0.2}}
URUT_ORDER = {"etf_jual": 0, "etf_beli": 1, "rd_beli": 2}


def ada(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def tgl(x):
    return pd.Timestamp(x).strftime("%Y-%m-%d")


def keadaan_baru():
    return {"aktif": False, "masuk": None, "kas": 0.0, "unit": {}, "etf": None, "antrean": [], "produk": None, "tanpa_trx": 0, "hilang": 0, "terakhir": None,
            "harga_terakhir": {}, "pilih_awal": None, "rebalance_tunda": None, "gagal_ganti": None, "nomor_order": 0}


class DataNyata:
    def __init__(self):
        ring = (dt.baca_hasil("etf_emas_ringkas") or {}).get("etf") or {}
        self.nama = {k: r["nama"] for k, r in ring.items()}
        self.etf_df = {k: dt.baca(f"{ee.KOLEKSI}/{k}") for k in ring if dt.ada(f"{ee.KOLEKSI}/{k}")}
        self.aum_akhir = {k: r.get("aum") for k, r in ring.items()}
        self.hari = list(harga.ihsg().index)
        self.kurs = harga.indeks("kurs/USD")["close"].dropna().sort_index()
        self.emas_usd = harga.indeks("pasar_panjang/emas_usd")["close"].dropna().sort_index()
        self.db = d.koneksi()
        self.cache_nav = {}

    def nav(self, fid):
        if fid not in self.cache_nav:
            x = pd.DataFrame(list(self.db.rd_nav.find({"fund": {"$in": [fid, str(fid)]}}, {"_id": 0})))
            if x.empty:
                self.cache_nav[fid] = pd.Series(dtype=float)
            else:
                x["tgl"] = pd.to_datetime(x["tgl"])
                self.cache_nav[fid] = x.set_index("tgl")["nav"].astype(float).sort_index()
        return self.cache_nav[fid]

    def rd(self, fid, mu, D):
        s = self.nav(fid)
        if D not in s.index:
            return None
        p = float(s.loc[D])
        if mu == "USD":
            k = self.kurs.loc[:D]
            if not len(k):
                return None
            p *= float(k.iloc[-1])
        return p

    def etf(self, kode, D):
        df = self.etf_df.get(kode)
        if df is None or D not in df.index:
            return None
        r = df.loc[D]
        g = lambda k: float(r[k]) if ada(r.get(k)) else None
        return {"close": g("close"), "volume": g("volume"), "nilai": g("nilai"), "nav": g("nav"), "premium": g("premium")}

    def aum(self, kode, D):
        df = self.etf_df.get(kode)
        if df is not None and "aum" in df:
            x = df.loc[:D, "aum"].dropna()
            if len(x):
                return float(x.iloc[-1])
        return self.aum_akhir.get(kode)

    def frames(self):
        return self.etf_df

    def kurs_emas(self, D):
        e = self.emas_usd.loc[:D]
        k = self.kurs.loc[:D]
        return float(e.iloc[-1] * k.iloc[-1]) if len(e) and len(k) else None


class Mesin:
    def __init__(self, strategi, data, state=None, mulai=MULAI, rebalance_pertama=REBALANCE_PERTAMA, modal=MODAL):
        self.strategi = strategi
        self.bobot = BOBOT[strategi]
        self.data = data
        self.mulai = pd.Timestamp(mulai)
        self.rp = rebalance_pertama
        self.modal = modal
        self.st = state if state is not None else keadaan_baru()
        self.transaksi = []
        self.kejadian = []
        self.ekuitas = []
        self.hitung_id = {}

    def nomor(self, kunci):
        self.hitung_id[kunci] = self.hitung_id.get(kunci, 0) + 1
        return self.hitung_id[kunci]

    def cat(self, D, jenis, teks, **x):
        n = self.nomor(f"k|{tgl(D)}|{jenis}")
        self.kejadian.append({"_id": f"{tgl(D)}|{jenis}|{n}", "tgl": tgl(D), "jenis": jenis, "teks": teks, **x})

    def trx(self, D, kaki, kunci, sisi, unit, harga_, fee, **x):
        n = self.nomor(f"t|{tgl(D)}|{kunci}|{sisi}")
        self.transaksi.append({"_id": f"{tgl(D)}|{kunci}|{sisi}|{n}", "tgl": tgl(D), "kaki": kaki, "kunci": kunci, "sisi": sisi, "unit": unit, "harga": harga_,
                               "nilai": unit * harga_, "fee": fee, **x})

    def produk_semua(self):
        return [("lokal", p) for p in self.st["produk"]["lokal"]] + [("global", p) for p in self.st["produk"]["global"]]

    def harga_rd(self, p, D):
        v = self.data.rd(p["id"], p["mu"], D)
        if ada(v):
            self.st["harga_terakhir"][f"rd:{p['id']}"] = v
            return v
        return None

    def semua_harga_rd(self, D):
        return all(self.harga_rd(p, D) is not None for _, p in self.produk_semua())

    def harga_nilai(self, kunci, D):
        if kunci.startswith("rd:"):
            fid = int(kunci[3:])
            p = next(x for _, x in self.produk_semua() if x["id"] == fid)
            v = self.harga_rd(p, D)
        else:
            row = self.data.etf(kunci[4:], D)
            v = row["close"] if row and ada(row["close"]) else None
            if v is not None:
                self.st["harga_terakhir"][kunci] = v
        return v if v is not None else self.st["harga_terakhir"].get(kunci)

    def nilai_kaki(self, D):
        out = {"lokal": 0.0, "global": 0.0, "emas": 0.0}
        for kaki, p in self.produk_semua():
            k = f"rd:{p['id']}"
            if self.st["unit"].get(k):
                out[kaki] += self.st["unit"][k] * (self.harga_nilai(k, D) or 0)
        for k, u in self.st["unit"].items():
            if k.startswith("etf:") and u:
                out["emas"] += u * (self.harga_nilai(k, D) or 0)
        return out

    def total(self, D):
        return sum(self.nilai_kaki(D).values()) + self.st["kas"]

    def akhir_bulan(self, D, bulan):
        if D.month != bulan:
            return False
        hari = [h for h in self.data.hari if h.year == D.year and h.month == bulan]
        return bool(hari) and D == hari[-1]

    def sebelum(self, D):
        h = [x for x in self.data.hari if x < D]
        return h[-1] if h else None

    def pilih_etf(self, sampai, kecuali=()):
        return ee.seleksi(self.data.frames(), {k: self.data.aum(k, sampai) for k in self.data.frames()}, getattr(self.data, "nama", {}), sampai=sampai, kecuali=kecuali)

    def masuk(self, D):
        st = self.st
        if not self.semua_harga_rd(D):
            self.cat(D, "masuk_ditunda", "harga RD belum lengkap, masuk ditunda")
            return False
        if "emas" in self.bobot and st["etf"] is None:
            awal = st["pilih_awal"] or self.pilih_etf(self.sebelum(D) or D)
            if not awal.get("terpilih"):
                self.cat(D, "pilih_gagal", "tidak ada ETF emas yang memenuhi syarat, masuk ditunda")
                return False
            st["etf"] = awal["terpilih"]
        for kaki in ("lokal", "global"):
            daftar = st["produk"][kaki]
            per = self.bobot[kaki] * self.modal / len(daftar)
            for p in daftar:
                pr = self.harga_rd(p, D)
                st["unit"][f"rd:{p['id']}"] = per / pr
                self.trx(D, kaki, f"rd:{p['id']}", "beli", per / pr, pr, 0.0, nama=p["nama"], masuk=True)
        if "emas" in self.bobot:
            st["kas"] = self.bobot["emas"] * self.modal
            self.buat_order("etf_beli", f"etf:{st['etf']}", st["kas"], D, kaki="emas")
        st["aktif"] = True
        st["masuk"] = tgl(D)
        self.cat(D, "masuk", f"modal Rp{self.modal:,.0f} masuk ke target", etf=st["etf"])
        return True

    def buat_order(self, jenis, kunci, sisa, D, kaki):
        self.st["nomor_order"] += 1
        self.st["antrean"].append({"id": self.st["nomor_order"], "jenis": jenis, "kunci": kunci, "kaki": kaki, "sisa": float(sisa), "hari": 0, "lewati": 0, "mulai": tgl(D)})

    def cadangan_order_beli(self):
        return sum(o["sisa"] for o in self.st["antrean"] if o["jenis"] == "etf_beli")

    def jalankan_antrean(self, D):
        for o in sorted(list(self.st["antrean"]), key=lambda x: (URUT_ORDER[x["jenis"]], x["id"])):
            if o["jenis"] == "rd_beli":
                self.order_rd(D, o)
            else:
                self.order_etf(D, o)

    def hapus(self, o):
        self.st["antrean"] = [x for x in self.st["antrean"] if x["id"] != o["id"]]

    def order_rd(self, D, o):
        st = self.st
        fid = int(o["kunci"][3:])
        p = next(x for _, x in self.produk_semua() if x["id"] == fid)
        pr = self.harga_rd(p, D)
        if pr is None:
            self.cat(D, "data_kosong_rd", f"harga RD {fid} kosong, order ditunda", kunci=o["kunci"])
            return
        bebas = max(0.0, st["kas"] - self.cadangan_order_beli())
        jumlah = min(o["sisa"], bebas)
        if jumlah <= 1:
            return
        st["unit"][o["kunci"]] = st["unit"].get(o["kunci"], 0.0) + jumlah / pr
        st["kas"] -= jumlah
        o["sisa"] -= jumlah
        self.trx(D, o["kaki"], o["kunci"], "beli", jumlah / pr, pr, 0.0, nama=p["nama"], rebalance=True)
        if o["sisa"] < 1:
            self.hapus(o)

    def order_etf(self, D, o):
        st = self.st
        kode = o["kunci"][4:]
        o["hari"] += 1
        row = self.data.etf(kode, D)
        beli = o["jenis"] == "etf_beli"
        lengkap = row and all(ada(row[k]) for k in ("close", "volume", "nilai")) and (not beli or ada(row["premium"]))
        if not lengkap:
            self.cat(D, "data_kosong_emas", f"data {kode} kosong/tak lengkap, tidak ada transaksi emas hari ini", kode=kode, hari_order=o["hari"])
            return
        if row["volume"] <= 0:
            self.cat(D, "tanpa_transaksi_emas", f"{kode} tanpa transaksi hari ini", kode=kode, hari_order=o["hari"])
            return
        cap = BATAS_NILAI * row["nilai"]
        if beli:
            prem = row["premium"]
            paksa = o["hari"] >= HARI_BATAS
            if prem > PREMIUM_MAKS_BELI and not paksa:
                o["lewati"] += 1
                self.cat(D, "lewati_premium", f"premium {prem * 100:+.2f}% > +2%, hari dilewati", kode=kode, premium=prem, hari_order=o["hari"])
                return
            harga_ = row["close"] + TICK
            per_lot = harga_ * LOT * (1 + FEE_BELI)
            dana = min(o["sisa"], st["kas"])
            lot = int(min(dana, cap) // per_lot)
            if lot <= 0:
                if dana < per_lot:
                    self.cat(D, "order_selesai_sisa", f"sisa Rp{dana:,.0f} kurang dari satu lot, order ditutup", kode=kode, hari_order=o["hari"], sisa=dana)
                    self.hapus(o)
                else:
                    self.cat(D, "batas_nilai_terlalu_kecil", "20% nilai transaksi kurang dari satu lot", kode=kode, hari_order=o["hari"])
                return
            unit = lot * LOT
            biaya = unit * harga_
            fee = biaya * FEE_BELI
            st["kas"] -= biaya + fee
            st["unit"][o["kunci"]] = st["unit"].get(o["kunci"], 0.0) + unit
            o["sisa"] -= biaya + fee
            self.trx(D, "emas", o["kunci"], "beli", unit, harga_, fee, premium=prem, hari_order=o["hari"], nilai_transaksi_etf=row["nilai"], batas=cap, pakai_batas=biaya / cap)
            if paksa and prem > PREMIUM_MAKS_BELI:
                self.cat(D, "batas_hari_15", f"hari ke-{o['hari']}: beli di premium {prem * 100:+.2f}% karena batas hari", kode=kode, premium=prem)
            if o["sisa"] < per_lot or st["kas"] < per_lot:
                self.cat(D, "order_selesai", f"pembelian emas selesai hari ke-{o['hari']}", kode=kode, hari_order=o["hari"], lewati_premium=o["lewati"])
                self.hapus(o)
            return
        harga_ = row["close"] - TICK
        pos = st["unit"].get(o["kunci"], 0.0)
        if pos <= 0:
            self.hapus(o)
            return
        per_lot = harga_ * LOT
        lot_cap = int(cap // per_lot)
        lot_butuh = 10 ** 9 if o["sisa"] >= TAK_HINGGA / 2 else int(math.ceil(min(o["sisa"], cap) / per_lot))
        lot_pos = int(math.ceil(pos / LOT))
        lot = min(lot_cap, lot_butuh, lot_pos)
        if lot <= 0:
            self.cat(D, "batas_nilai_terlalu_kecil", "20% nilai transaksi kurang dari satu lot, jual ditunda", kode=kode, hari_order=o["hari"])
            return
        unit = min(pos, lot * LOT)
        hasil = unit * harga_
        fee = hasil * FEE_JUAL
        st["kas"] += hasil - fee
        st["unit"][o["kunci"]] = pos - unit
        o["sisa"] -= hasil
        self.trx(D, "emas", o["kunci"], "jual", unit, harga_, fee, premium=row["premium"] if ada(row["premium"]) else None, hari_order=o["hari"],
                 nilai_transaksi_etf=row["nilai"], batas=cap, pakai_batas=hasil / cap)
        if st["unit"][o["kunci"]] <= 0 or o["sisa"] <= 0:
            self.cat(D, "jual_selesai", f"penjualan emas selesai hari ke-{o['hari']}", kode=kode, hari_order=o["hari"])
            self.hapus(o)

    def alihkan(self, D, baru, target_beli, alasan, lama):
        st = self.st
        tunda = sum(o["sisa"] for o in st["antrean"] if o["jenis"] == "etf_beli" and o["kunci"] == f"etf:{lama}")
        st["antrean"] = [o for o in st["antrean"] if not (o["jenis"] == "etf_beli" and o["kunci"] == f"etf:{lama}")]
        if st["unit"].get(f"etf:{lama}", 0) > 0:
            self.buat_order("etf_jual", f"etf:{lama}", TAK_HINGGA, D, kaki="emas")
        self.buat_order("etf_beli", f"etf:{baru}", max(target_beli, tunda), D, kaki="emas")
        st["etf"] = baru
        st["tanpa_trx"] = 0
        st["hilang"] = 0
        self.cat(D, "ganti_etf", f"ETF emas diganti {lama} -> {baru}: {alasan}", lama=lama, baru=baru, alasan=alasan)

    def cek_ganti(self, D):
        st = self.st
        if "emas" not in self.bobot or not st["etf"]:
            return
        kode = st["etf"]
        row = self.data.etf(kode, D)
        if row is None:
            st["hilang"] += 1
        else:
            st["hilang"] = 0
            if ada(row["volume"]):
                st["tanpa_trx"] = st["tanpa_trx"] + 1 if row["volume"] <= 0 else 0
        alasan = None
        if st["tanpa_trx"] >= HARI_TANPA_TRANSAKSI:
            alasan = f"{HARI_TANPA_TRANSAKSI} hari bursa berturut tanpa transaksi"
        a = self.data.aum(kode, D)
        if ada(a) and a < ee.MIN_AUM:
            alasan = "AUM < Rp10 M"
        if st["hilang"] >= HARI_HILANG:
            alasan = f"delisting (tidak ada data {HARI_HILANG} hari bursa)"
        if not alasan:
            st["gagal_ganti"] = None
            return
        sel = self.pilih_etf(D, kecuali=(kode,))
        if not sel["terpilih"]:
            if st["gagal_ganti"] != alasan:
                self.cat(D, "ganti_gagal", f"harus ganti ETF ({alasan}) tetapi tidak ada pengganti yang memenuhi syarat", alasan=alasan)
                st["gagal_ganti"] = alasan
            return
        sisa_beli = sum(o["sisa"] for o in st["antrean"] if o["jenis"] == "etf_beli")
        nilai_lama = st["unit"].get(f"etf:{kode}", 0.0) * (self.harga_nilai(f"etf:{kode}", D) or 0)
        self.alihkan(D, sel["terpilih"], nilai_lama + sisa_beli, alasan, kode)
        st["gagal_ganti"] = None

    def perlu_rebalance(self, D):
        st = self.st
        if st["rebalance_tunda"] is not None:
            return True
        return bool(self.akhir_bulan(D, 12) and D.year >= self.rp and st["masuk"] and pd.Timestamp(st["masuk"]) < D)

    def rebalance(self, D):
        st = self.st
        if not self.semua_harga_rd(D):
            st["rebalance_tunda"] = tgl(D)
            self.cat(D, "rebalance_ditunda", "harga RD belum lengkap, rebalance dicoba lagi")
            return
        st["rebalance_tunda"] = None
        total = self.total(D)
        nilai = self.nilai_kaki(D)
        rinci = {}
        for kaki in ("lokal", "global"):
            target = self.bobot[kaki] * total
            sekarang = nilai[kaki]
            daftar = st["produk"][kaki]
            rinci[kaki] = {"sekarang": sekarang, "target": target}
            if sekarang > target:
                frac = (sekarang - target) / sekarang
                for p in daftar:
                    k = f"rd:{p['id']}"
                    jual = st["unit"][k] * frac
                    pr = self.harga_rd(p, D)
                    st["unit"][k] -= jual
                    st["kas"] += jual * pr
                    self.trx(D, kaki, k, "jual", jual, pr, 0.0, nama=p["nama"], rebalance=True)
            elif sekarang < target:
                for p in daftar:
                    self.buat_order("rd_beli", f"rd:{p['id']}", (target - sekarang) / len(daftar), D, kaki=kaki)
        if "emas" in self.bobot:
            target = self.bobot["emas"] * total
            kode = st["etf"]
            sekarang = nilai["emas"]
            rinci["emas"] = {"sekarang": sekarang, "target": target}
            sel = self.pilih_etf(D)
            baru = sel["terpilih"]
            if baru and baru != kode:
                self.alihkan(D, baru, target, "pilih ulang ETF saat rebalance Desember", kode)
            elif sekarang > target:
                self.buat_order("etf_jual", f"etf:{kode}", sekarang - target, D, kaki="emas")
            elif sekarang < target:
                self.buat_order("etf_beli", f"etf:{kode}", target - sekarang, D, kaki="emas")
        self.cat(D, "rebalance", f"rebalance Desember {D.year} ke target", total=total, rinci=rinci)

    def catat_ekuitas(self, D):
        n = self.nilai_kaki(D)
        self.ekuitas.append({"_id": tgl(D), "tgl": tgl(D), "nilai": sum(n.values()) + self.st["kas"], "kas": self.st["kas"], **n, "etf": self.st["etf"]})

    def proses(self, D):
        D = pd.Timestamp(D)
        st = self.st
        if st["terakhir"] and D <= pd.Timestamp(st["terakhir"]):
            return
        if D < self.mulai:
            return
        if not st["aktif"]:
            self.masuk(D)
        if st["aktif"]:
            if self.perlu_rebalance(D):
                self.rebalance(D)
            self.jalankan_antrean(D)
            self.cek_ganti(D)
            self.catat_ekuitas(D)
        st["terakhir"] = tgl(D)

    def jalan(self, hari):
        for D in hari:
            self.proses(D)
