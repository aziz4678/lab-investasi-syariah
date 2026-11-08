from datetime import date

import pandas as pd

from backend.app.services.reksadana import bersih
from backend.db import data as dt

GESER = 0.003
BASI_BULAN = 2


def _bulan(s):
    return pd.Period(s, "M")


def _patokan(dok, tahun):
    for t in (tahun - 1, tahun - 2):
        batas = pd.Period(f"{t}-12", "M")
        x = next((x for x in dok if _bulan(x["periode"]["akhir"]) >= batas), None)
        if x is not None:
            return x, t
    return dok[-1], None


def _aman(x):
    return {p["kode"]: p.get("aman_5") for p in x["portofolio"]}


def hasil():
    dok = list(dt.db()["hasil_penarikan"].find({}, {"_id": 0}).sort("dihitung", 1))
    if not dok:
        return {"ada": False}
    terbaru = dok[-1]
    hari = date.today()
    patokan, tahun_data = _patokan(dok, hari.year)
    akhir = _bulan(terbaru["periode"]["akhir"])
    umur = (pd.Period(hari, "M") - akhir).n
    a_pat, a_baru = _aman(patokan), _aman(terbaru)
    geser = {k: {"patokan": a_pat.get(k), "terbaru": v} for k, v in a_baru.items()
             if v is not None and a_pat.get(k) is not None and abs(v - a_pat[k]) > GESER}
    riwayat = [{"dihitung": x["dihitung"].isoformat(timespec="minutes"), "akhir": x["periode"]["akhir"], "aman_5": _aman(x)} for x in dok[-24:]]

    def siap(x):
        y = dict(x)
        y["dihitung"] = x["dihitung"].isoformat(timespec="minutes")
        return y

    return bersih({"ada": True, "terbaru": siap(terbaru), "patokan": siap(patokan), "patokan_tahun": hari.year,
                   "patokan_data_desember": tahun_data, "umur_bulan": umur, "basi": umur > BASI_BULAN, "geser": geser, "ambang_geser": GESER,
                   "riwayat": riwayat})


KUNCI_SIDIK = ("rd_ojk", "inflasi", "bi_rate", "sbsn_csv")
JEDA_ST_BULAN = 5


def perlu_hitung():
    from backend.research.analisis_penarikan import sidik_input
    akhir = dt.db()["hasil_penarikan"].find_one({}, {"sidik": 1}, sort=[("dihitung", -1)])
    if akhir is None:
        return True, "belum pernah dihitung"
    kini = sidik_input(None)
    beda = [k for k in KUNCI_SIDIK if kini.get(k) != akhir["sidik"].get(k)]
    return bool(beda), ", ".join(f"{k}: {akhir['sidik'].get(k)} -> {kini.get(k)}" for k in beda) or "data sama"


def pengingat_sbn():
    from backend.core.config import ROOT
    from backend.db import koneksi as d
    c = pd.read_csv(ROOT / "data" / "sbsn_ritel.csv", dtype=str).fillna("")
    ada = set(c["seri"])
    pesan = []
    for x in d.koneksi().rd_sukuk.find({"jenis": "SR"}, {"_id": 1}).sort("_id", 1):
        if x["_id"] not in ada:
            pesan.append({"seri": x["_id"], "alasan": "sudah tercatat di Pasardana"})
    st = c[c["jenis"] == "ST"].copy()
    st["tutup"] = pd.to_datetime(st["tgl_penawaran_akhir"])
    terakhir = st.sort_values("tutup").iloc[-1]
    nomor = int(terakhir["seri"][2:5])
    batas = terakhir["tutup"] + pd.DateOffset(months=JEDA_ST_BULAN)
    if pd.Timestamp(date.today()) > batas:
        pesan.append({"seri": f"ST{nomor + 1:03d}", "alasan": f"lebih dari {JEDA_ST_BULAN} bulan sejak {terakhir['seri'][:5]} ditutup ({terakhir['tutup']:%d %b %Y}); perkiraan seri berikutnya"})
    return {"pengingat": pesan, "st_terakhir": terakhir["seri"][:5], "st_tutup": f"{terakhir['tutup']:%Y-%m-%d}", "cek_st_setelah": f"{batas:%Y-%m-%d}",
            "jumlah_seri": len(c)}


WADAH = {"pendapatan_tetap": "RD pendapatan tetap syariah", "pasar_uang": "RD pasar uang syariah"}
MIN_TAHUN_PRODUK = 3
MAKS_PRODUK = 5
NAV_DATAR = 0.01
NAV_AKTIF_HARI = 14
POLA_TAHUN = 3


def contoh_produk():
    from backend.app.services import reksadana as rdn
    from backend.db import koneksi as d
    bagi = {int(x["_id"]) for x in d.koneksi().rd_produk.find({"Dividend": True}, {"_id": 1})}
    batas_aktif = pd.Timestamp(date.today()) - pd.Timedelta(days=NAV_AKTIF_HARI)
    hasil = {}
    for kat, label in WADAH.items():
        calon = []
        for x in rdn.daftar()["data"]:
            if x.get("kategori") != kat or x.get("mata_uang") != "IDR":
                continue
            alasan = []
            if not x.get("nav_tgl") or pd.Timestamp(x["nav_tgl"]) < batas_aktif or x.get("nav_beku"):
                alasan.append("tidak aktif")
            if (x.get("tahun_data") or 0) < MIN_TAHUN_PRODUK:
                alasan.append("riwayat < 3 th")
            if int(x["id"]) in bagi or (x.get("cagr_semua") is not None and x["cagr_semua"] < NAV_DATAR * 100):
                alasan.append("bagi hasil tunai")
            if x.get("biaya") is None or x["biaya"] <= 0:
                alasan.append("biaya tidak diketahui")
            if alasan:
                continue
            calon.append({"id": x["id"], "nama": x["nama"], "mi": x.get("mi"), "biaya": x["biaya"], "aum": x.get("aum"), "tahun_data": x.get("tahun_data"),
                          "terbit": x.get("terbit"), "platform": [p["kode"] for p in x.get("platform") or []]})
        batas_aum = float(pd.Series([c["aum"] or 0 for c in calon]).median()) if calon else 0.0
        besar = [c for c in calon if (c["aum"] or 0) >= batas_aum]
        besar.sort(key=lambda c: (c["biaya"], -(c["aum"] or 0)))
        hasil[kat] = {"label": label, "jumlah_lolos": len(calon), "jumlah_aum_besar": len(besar), "batas_aum": batas_aum, "produk": besar[:MAKS_PRODUK]}
    return hasil


def _csv_sbn():
    from backend.core.config import ROOT
    c = pd.read_csv(ROOT / "data" / "sbsn_ritel.csv", dtype=str).fillna("")
    c["mulai"] = pd.to_datetime(c["tgl_penawaran_mulai"])
    c["tutup"] = pd.to_datetime(c["tgl_penawaran_akhir"])
    c["dasar"] = c["seri"].str.replace(r"T\d$", "", regex=True)
    return c


def penawaran_berikut():
    c = _csv_sbn()
    hari = pd.Timestamp(date.today())
    buka = c[c["tutup"] >= hari]
    hasil = {"dibuka": None, "perkiraan": []}
    if len(buka):
        g = buka[buka["dasar"] == buka.sort_values("mulai")["dasar"].iloc[0]]
        hasil["dibuka"] = {"seri": g["dasar"].iloc[0], "jenis": g["jenis"].iloc[0], "mulai": f"{g['mulai'].iloc[0]:%Y-%m-%d}", "tutup": f"{g['tutup'].iloc[0]:%Y-%m-%d}",
                           "terbit": g["tgl_terbit"].iloc[0] or None, "sumber": g["sumber"].iloc[0],
                           "varian": [{"seri": r.seri, "tenor": int(r.tenor_th), "jatuh_tempo": r.jatuh_tempo, "kupon": float(r.kupon_awal) / 100,
                                       "jenis_kupon": r.jenis_kupon, "spread": float(r.spread_bi_rate) / 10000 if r.spread_bi_rate else None} for r in g.itertuples()]}
    for jenis in ("SR", "ST"):
        x = c[(c["jenis"] == jenis) & (c["mulai"] >= hari - pd.DateOffset(years=POLA_TAHUN))].drop_duplicates("dasar")
        if x.empty:
            continue
        bulan = sorted(set(x["mulai"].dt.month))
        akhir = c[c["jenis"] == jenis].sort_values("mulai").iloc[-1]
        kandidat = []
        for th in (hari.year, hari.year + 1, hari.year + 2):
            for b in bulan:
                t = pd.Timestamp(year=th, month=b, day=1)
                if t > max(hari, akhir["tutup"]):
                    kandidat.append(t)
        nomor = int(akhir["dasar"][2:])
        varian = c[c["dasar"] == akhir["dasar"]]["tenor_th"].astype(int).tolist()
        hasil["perkiraan"].append({"jenis": jenis, "seri": f"{jenis}{nomor + 1:03d}", "bulan": f"{min(kandidat):%Y-%m}" if kandidat else None,
                                   "pola_bulan": bulan, "tenor": varian, "dasar_pola": f"{len(x)} penawaran {jenis} sejak {hari.year - POLA_TAHUN}"})
    return hasil


def sr_beredar():
    from backend.app.services import reksadana as rdn
    data = [x for x in rdn.sukuk()["data"] if x.get("jenis") == "SR"]
    return sorted([{"kode": x["kode"], "kupon": x.get("kupon"), "jatuh_tempo": x.get("jatuh_tempo"), "sisa_tahun": x.get("sisa_tahun"), "harga": x.get("harga"),
                    "ytm": x.get("ytm"), "ytm_bersih": x.get("ytm_bersih"), "tgl_harga": x.get("tgl_harga")} for x in data], key=lambda x: str(x["jatuh_tempo"]))


def konservatif():
    h = hasil()
    return bersih({**h, "penawaran": penawaran_berikut(), "sr": sr_beredar(), "produk": contoh_produk(),
                   "kriteria_produk": {"min_tahun": MIN_TAHUN_PRODUK, "maks": MAKS_PRODUK, "nav_datar": NAV_DATAR, "aktif_hari": NAV_AKTIF_HARI}})
