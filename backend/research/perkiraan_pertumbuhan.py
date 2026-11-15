import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga
from backend.research import keranjang_pertumbuhan as kp
from backend.research import uji_h35 as h35
from backend.research import uji_h37 as h37

NAMA_HASIL = "perkiraan_pertumbuhan"
VERSI = "2026-11-15b"
JANGKA = tuple(range(1, 21))
BOBOT = {"saham": {"idx": 0.5, "gl": 0.5}, "emas": {"idx": 0.4, "gl": 0.4, "emas": 0.2}}
BIAYA_SETOR_GL = 0.005
BIAYA_REBAL = h35.BIAYA_REBAL
BIAYA_EMAS_CADANGAN = h37.BIAYA_EMAS_TAHUN
MIN_JENDELA = 30
BATAS_PERIODE_BEDA = 5


def biaya_lokal_rata():
    dok = kp.terbaru("semua")
    biaya = [c["biaya"] for c in (dok or {}).get("isi", {}).get("LK", []) if c.get("biaya")]
    return (float(np.mean(biaya)) / 100 if biaya else None), len(biaya)


def seri_bulanan(biaya_lokal, biaya_emas=BIAYA_EMAS_CADANGAN):
    R = h37.seri_h37(biaya_emas)
    j = h35.bulanan(harga.indeks("indeks/JKII")["close"]).loc[h35.AWAL:h35.AKHIR]
    r_j = (j / j.shift(1) - 1).reindex(R.index)
    div = h35.DASAR["div_jii"]
    R = R.copy()
    R["idx"] = (1 + r_j) * (1 + div) ** (1 / 12) * (1 - biaya_lokal) ** (1 / 12) - 1
    if R[["idx", "gl", "emas"]].isna().any().any():
        raise harga.DataTidakAda("ada bulan tanpa return")
    return R[["idx", "gl", "emas"]]


def jalankan(R, bobot, setoran=1.0, biaya_gl=BIAYA_SETOR_GL, biaya_rebal=BIAYA_REBAL, maks=240):
    kaki = list(bobot)
    w = np.array([bobot[k] for k in kaki], dtype=float)
    potong = np.array([1 - biaya_gl if k == "gl" else 1.0 for k in kaki])
    r = R[kaki].to_numpy(dtype=float)
    bulan = np.array([p.month for p in R.index])
    n = len(R)
    nilai, bulanan = [], []
    for s in range(n):
        panjang = min(maks, n - s)
        v = np.zeros(len(w))
        jalur = np.empty(panjang)
        rp = np.empty(panjang)
        for k in range(panjang):
            v = v + setoran * w * potong
            sebelum = v.sum()
            v = v * (1 + r[s + k])
            tot = v.sum()
            rp[k] = tot / sebelum - 1
            if bulan[s + k] == 12:
                jual = np.maximum(0.0, v - w * tot).sum()
                tot -= biaya_rebal * jual
                v = w * tot
            jalur[k] = tot
        nilai.append(jalur)
        bulanan.append(rp)
    return nilai, bulanan


def xirr_bulanan(nilai_akhir, n, setoran=1.0):
    v = np.asarray(nilai_akhir, dtype=float) / setoran
    lo, hi = np.full(v.shape, -0.95), np.full(v.shape, 1.0)

    def f(x):
        a = 1 + x
        kecil = np.abs(x) < 1e-12
        return np.where(kecil, float(n), a * np.expm1(n * np.log1p(x)) / np.where(kecil, 1.0, x))

    for _ in range(200):
        tengah = (lo + hi) / 2
        besar = f(tengah) > v
        hi = np.where(besar, tengah, hi)
        lo = np.where(besar, lo, tengah)
    return (lo + hi) / 2


def xirr_tahunan(nilai_akhir, n, setoran=1.0):
    return (1 + xirr_bulanan(nilai_akhir, n, setoran)) ** 12 - 1


def penurunan_terdalam(R, bobot, biaya_rebal=BIAYA_REBAL):
    kaki = list(bobot)
    w = np.array([bobot[k] for k in kaki], dtype=float)
    r = R[kaki].to_numpy(dtype=float)
    v = w.copy()
    nilai = [1.0]
    for i, p in enumerate(R.index):
        v = v * (1 + r[i])
        tot = v.sum()
        if p.month == 12:
            jual = np.maximum(0.0, v - w * tot).sum()
            tot -= biaya_rebal * jual
            v = w * tot
        nilai.append(tot)
    s = pd.Series(nilai, index=[R.index[0] - 1] + list(R.index))
    dd = s / s.cummax() - 1
    return {"dd": float(dd.min()), "lembah": str(dd.idxmin())}


def ringkas_jangka(R, nilai, bulanan, tahun, setoran=1.0):
    n = 12 * tahun
    mulai = [s for s in range(len(R)) if len(nilai[s]) >= n]
    if not mulai:
        return None
    akhir = np.array([nilai[s][n - 1] for s in mulai])
    total = setoran * n
    xirr = xirr_tahunan(akhir, n, setoran)
    median_x = float(np.median(xirr))
    rp = np.concatenate([bulanan[s][:n] for s in mulai])
    i_buruk, i_baik = int(np.argmin(akhir)), int(np.argmax(akhir))
    terpisah = round(len(R) / 12 / tahun, 1)
    return {"tahun": tahun, "jendela": len(mulai), "periode_terpisah": terpisah, "terbatas": terpisah < BATAS_PERIODE_BEDA, "untung": int((akhir > total).sum()), "median": float(np.median(akhir)), "terburuk": float(akhir.min()), "terbaik": float(akhir.max()),
            "total": float(total), "xirr_median": median_x, "per_bulan": float((1 + median_x) ** (1 / 12) - 1),
            "bulanan_p5": float(np.percentile(rp, 5)), "bulanan_p95": float(np.percentile(rp, 95)),
            "mulai_terburuk": str(R.index[mulai[i_buruk]]), "mulai_terbaik": str(R.index[mulai[i_baik]]),
            "data_dari": str(R.index[mulai[0]]), "data_sampai": str(R.index[mulai[-1] + n - 1])}


def sidik():
    biaya, _ = biaya_lokal_rata()
    return {"versi": VERSI, "keranjang": kp.sidik(), "biaya_lokal": None if biaya is None else round(biaya, 6), "h35": str(dt.versi_hasil("h35_hasil"))}


def hitung(cetak=True):
    biaya, jumlah = biaya_lokal_rata()
    if biaya is None:
        raise RuntimeError("keranjang lokal belum ada, tidak ada biaya produk untuk dikurangkan")
    R = seri_bulanan(biaya)
    hasil = {}
    for gaya, bobot in BOBOT.items():
        nilai, bulanan = jalankan(R, bobot)
        hasil[gaya] = {"dd": penurunan_terdalam(R, bobot), "jangka": {str(t): ringkas_jangka(R, nilai, bulanan, t) for t in JANGKA}}
    isi = {"dihitung": datetime.now(), "versi": VERSI, "sidik": sidik(), "periode": [str(R.index[0]), str(R.index[-1])], "biaya_lokal": biaya, "produk_lokal": jumlah,
           "biaya_setor_global": BIAYA_SETOR_GL, "biaya_rebalance": BIAYA_REBAL, "biaya_emas": BIAYA_EMAS_CADANGAN, "dividen_jii": h35.DASAR["div_jii"], "min_jendela": MIN_JENDELA, "batas_periode_beda": BATAS_PERIODE_BEDA, **hasil}
    dt.simpan_hasil(NAMA_HASIL, isi)
    if cetak:
        print(f"perkiraan pertumbuhan: data {isi['periode'][0]} s/d {isi['periode'][1]}, biaya lokal rata-rata {biaya * 100:.2f}%/th ({jumlah} produk)")
    return isi


def perlu_hitung():
    h = dt.baca_hasil(NAMA_HASIL)
    return h is None or h.get("sidik") != sidik()


def utama(bila_perlu=False):
    if bila_perlu and not perlu_hitung():
        print("perkiraan pertumbuhan dilewati: data sama")
        return
    hitung()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bila-perlu", action="store_true")
    utama(ap.parse_args().bila_perlu)
