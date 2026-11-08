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
