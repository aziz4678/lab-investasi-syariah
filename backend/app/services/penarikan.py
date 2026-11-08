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
