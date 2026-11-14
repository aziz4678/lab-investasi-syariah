import re

import pandas as pd

from backend.core import libur_bursa as lb
from backend.paper import mesin_pertumbuhan as mp

BULAN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7, "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12}
HARI_BATAS_AWAL = 9
KODE = ("h35", "h37")


def bulan_tahun(teks):
    m = re.search(r"\b([A-Za-z]{3,9})\s+(20\d{2})\b", str(teks or ""))
    if not m or m.group(1)[:3].lower() not in BULAN:
        raise ValueError(f"bulan/tahun tidak ditemukan di status: {teks!r}")
    return BULAN[m.group(1)[:3].lower()], int(m.group(2))


def hari_bursa_terakhir(bulan, tahun):
    akhir = pd.Timestamp(tahun, bulan, 1) + pd.offsets.MonthEnd(0)
    return lb.hari_bursa_antara(akhir - pd.Timedelta(days=10), akhir)[-1]


def dari_status(st):
    am = st.get("amandemen") or []
    mulai = next((x["mulai"] for x in reversed(am) if x.get("mulai")), None)
    if not mulai:
        raise ValueError("tanggal mulai tidak ada di amandemen status")
    mulai = pd.Timestamp(mulai)
    _, th_rebal = bulan_tahun(st.get("rebalance_pertama"))
    bln, th = bulan_tahun(st.get("pilih_etf_pertama"))
    return {"mulai": mulai, "rebalance_pertama": th_rebal, "tgl_pilih": hari_bursa_terakhir(bln, th), "batas_awal": mulai + pd.Timedelta(days=HARI_BATAS_AWAL)}


def baca(db):
    hasil = {}
    for k in KODE:
        st = db[f"paper_{k}_status"].find_one({"_id": "status"})
        if not st:
            raise RuntimeError(f"paper_{k}_status tidak ada")
        hasil[k] = dari_status(st)
    if hasil["h35"] != hasil["h37"]:
        raise RuntimeError(f"parameter H35 dan H37 di status berbeda: {hasil['h35']} vs {hasil['h37']}")
    return hasil["h37"]


def selisih(p):
    beda = []
    if p["mulai"] != mp.MULAI:
        beda.append(f"MULAI kode {mp.MULAI.date()} != DB {p['mulai'].date()}")
    if p["rebalance_pertama"] != mp.REBALANCE_PERTAMA:
        beda.append(f"REBALANCE_PERTAMA kode {mp.REBALANCE_PERTAMA} != DB {p['rebalance_pertama']}")
    if p["tgl_pilih"] != mp.TGL_PILIH:
        beda.append(f"TGL_PILIH kode {mp.TGL_PILIH.date()} != DB {p['tgl_pilih'].date()}")
    return beda


def verifikasi(db):
    p = baca(db)
    beda = selisih(p)
    if beda:
        raise RuntimeError("parameter uji maju di kode tidak sama dengan status terkunci: " + "; ".join(beda))
    return p
