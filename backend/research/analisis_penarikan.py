import argparse
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd

from backend.core.config import ROOT
from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi as d
from backend.research import analisis_likuiditas as al

MULAI_PALING_CEPAT = pd.Period("2016-04", "M")
TARIK = [0.03, 0.04, 0.05, 0.06]
PAJAK = 0.10
DIVIDEN_JII = 0.025
HORIZON = 60
PORTOFOLIO = [("Opsi 1 RD PT/PU 50/50", "rd", 0.0), ("Opsi 2a SBN 30%", "rd", 0.30), ("Opsi 2b SBN 50%", "rd", 0.50),
              ("Opsi 2c SBN 70%", "rd", 0.70), ("Pembanding 54% JII/46% PU", "jii", 0.0)]
KODE = {"Opsi 1 RD PT/PU 50/50": "tanpa_sbn", "Opsi 2a SBN 30%": "sbn30", "Opsi 2b SBN 50%": "sbn50", "Opsi 2c SBN 70%": "sbn70",
        "Pembanding 54% JII/46% PU": "jii_pu"}
TABEL_SIMPAN = [0.01, 0.015, 0.02, 0.025, 0.03]
_CACHE = {}


def bi_rate():
    s = dt.baca("makro/bi_rate")["nilai"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def penawaran():
    c = pd.read_csv(ROOT / "data" / "sbsn_ritel.csv", dtype=str).fillna("")
    c["dasar"] = c["seri"].str.replace(r"T\d$", "", regex=True)
    terbit = pd.to_datetime(c["tgl_terbit"].where(c["tgl_terbit"] != "", None))
    pengganti = pd.to_datetime(c["tgl_penawaran_akhir"]) + pd.Timedelta(days=7)
    c["terbit"] = terbit.fillna(pengganti)
    c["bulan"] = c["terbit"].dt.to_period("M")
    c["jt"] = pd.to_datetime(c["jatuh_tempo"]).dt.to_period("M")
    c["kupon"] = c["kupon_awal"].astype(float) / 100
    c["spread"] = pd.to_numeric(c["spread_bi_rate"], errors="coerce") / 10000
    c["floor"] = pd.to_numeric(c["floor"], errors="coerce") / 100
    return c


def kupon_st(lot, t, bi):
    if np.isnan(lot["spread"]):
        return lot["kupon"]
    bln = t.month
    reset = max(m for m in (2, 5, 8, 11, -1) if m <= bln) if bln >= 2 else -1
    if reset == -1:
        acuan = pd.Timestamp(year=t.year - 1, month=11, day=10)
    else:
        acuan = pd.Timestamp(year=t.year, month=reset, day=10)
    if acuan < lot["terbit"]:
        return lot["kupon"]
    r = bi[bi.index <= acuan]
    return max(lot["floor"], r.iloc[-1] / 100 + lot["spread"]) if len(r) else lot["kupon"]


def return_bulanan(L):
    return (L / L.shift(1) - 1).dropna()


def simulasi(t0, t_akhir, jenis, w_sbn, tarik, r, cpi, sbn, bi):
    bulan = pd.period_range(t0, t_akhir, freq="M")
    rd_pt = rd_pu = jii = parkir = 0.0
    if jenis == "rd":
        rd_pt = rd_pu = (1 - w_sbn) / 2
        parkir = w_sbn
    else:
        jii, rd_pu = 0.54, 0.46
    lot = []
    nominal_tarik = tarik / 12
    acuan_cpi = cpi[t0 - 1]
    riil, terkunci, gagal = [], [], []
    for i, t in enumerate(bulan):
        if i > 0 and i % 12 == 0:
            nominal_tarik *= cpi[t - 1] / cpi[t - 13]
        rd_pt *= 1 + r["PT"][t]
        rd_pu *= 1 + r["PU"][t]
        parkir *= 1 + r["PU"][t]
        jii *= 1 + r["JII"][t] + ((1 + DIVIDEN_JII) ** (1 / 12) - 1)
        kupon = sum(x["nominal"] * kupon_st(x, t, bi) / 12 * (1 - PAJAK) for x in lot if x["bulan"] < t)
        for x in [x for x in lot if x["jt"] == t]:
            parkir += x["nominal"]
        lot = [x for x in lot if x["jt"] != t]
        sisa = nominal_tarik - kupon
        if sisa < 0:
            if jenis == "rd":
                rd_pt += -sisa / 2
                rd_pu += -sisa / 2
            sisa = 0.0
        cair = rd_pt + rd_pu + parkir + jii
        if sisa > cair + 1e-12:
            gagal.append(i)
            rd_pt = rd_pu = parkir = jii = 0.0
        elif sisa > 0:
            f = 1 - sisa / cair
            rd_pt, rd_pu, parkir, jii = rd_pt * f, rd_pu * f, parkir * f, jii * f
        if jenis == "rd" and w_sbn > 0:
            baru = sbn[sbn["bulan"] == t]
            if len(baru):
                nilai_sbn = sum(x["nominal"] for x in lot)
                total = rd_pt + rd_pu + parkir + nilai_sbn
                kurang = max(0.0, w_sbn * total - nilai_sbn)
                dari_parkir = min(parkir, kurang)
                parkir -= dari_parkir
                dari_rd = min(rd_pt + rd_pu, kurang - dari_parkir)
                if rd_pt + rd_pu > 0:
                    f = 1 - dari_rd / (rd_pt + rd_pu)
                    rd_pt, rd_pu = rd_pt * f, rd_pu * f
                beli = dari_parkir + dari_rd
                for _, s in baru.iterrows():
                    lot.append({"nominal": beli / len(baru), "bulan": t, "jt": s["jt"], "kupon": s["kupon"], "spread": s["spread"],
                                "floor": s["floor"], "terbit": s["terbit"]})
        if t.month == 12:
            if jenis == "rd":
                tot = rd_pt + rd_pu
                rd_pt = rd_pu = tot / 2
            else:
                tot = jii + rd_pu
                jii, rd_pu = tot * 0.54, tot * 0.46
        nilai_sbn = sum(x["nominal"] for x in lot)
        total = rd_pt + rd_pu + parkir + jii + nilai_sbn
        riil.append(total / (cpi[t] / acuan_cpi))
        terkunci.append(nilai_sbn / total if total > 0 else 1.0)
    return np.array(riil), np.array(terkunci), gagal


def siapkan():
    h = al.semua_indeks()
    cpi = al.cpi()
    j = hg.indeks("indeks/JKII")["close"].dropna().sort_index()
    j.index = pd.to_datetime(j.index)
    jb = j.resample("ME").last()
    jb.index = jb.index.to_period("M")
    r = {"PT": return_bulanan(h["L"]["PT"]), "PU": return_bulanan(h["L"]["PU"]), "JII": jb.pct_change().dropna()}
    akhir = min(r["PT"].index[-1], r["PU"].index[-1], r["JII"].index[-1], cpi.index[-1])
    mulai = max(MULAI_PALING_CEPAT, r["PT"].index[0], r["PU"].index[0])
    return r, cpi, akhir, mulai


def ringkas(nilai):
    if not len(nilai):
        return "-"
    v = np.array(nilai)
    return f"{np.median(v) * 100:5.1f} {v.min() * 100:5.1f} {np.mean(v >= 1) * 100:4.0f}%"


def evaluasi(jenis, w, tr, ctx):
    kunci_cache = (jenis, w, round(tr, 4))
    if kunci_cache not in _CACHE:
        _CACHE[kunci_cache] = _evaluasi(jenis, w, tr, ctx)
    return _CACHE[kunci_cache]


def _evaluasi(jenis, w, tr, ctx):
    r, cpi, akhir, awal, sbn, bi = ctx
    r3, r5, dd, kunci_rata, kunci_maks = [], [], [], [], []
    per_tahun = {k: [] for k in range(1, HORIZON // 12 + 1)}
    gagal3 = gagal5 = gagal_bln = 0
    for t0 in awal:
        if t0 + 35 > akhir:
            break
        t_akhir = min(akhir, t0 + HORIZON - 1)
        riil, kunci, g = simulasi(t0, t_akhir, jenis, w, tr, r, cpi, sbn, bi)
        r3.append(riil[35])
        for k in per_tahun:
            if len(riil) >= 12 * k:
                per_tahun[k].append(riil[12 * k - 1])
        if len(riil) >= HORIZON:
            r5.append(riil[HORIZON - 1])
            gagal5 += len(g) > 0
        gagal3 += any(i < 36 for i in g)
        gagal_bln += len(g)
        jalur = np.concatenate([[1.0], riil])
        dd.append((jalur / np.maximum.accumulate(jalur) - 1).min())
        kunci_rata.append(kunci.mean())
        kunci_maks.append(kunci.max())
    return {"r3": r3, "r5": r5, "dd": min(dd), "dd_semua": dd, "per_tahun": per_tahun, "gagal3": gagal3, "gagal5": gagal5, "gagal_bln": gagal_bln,
            "kunci_rata": float(np.mean(kunci_rata)), "kunci_maks": max(kunci_maks)}


def lolos(m, h):
    v = np.array(m["r3"] if h == 3 else m["r5"])
    return len(v) > 0 and np.mean(v >= 1) >= 0.8 and m["gagal3" if h == 3 else "gagal5"] == 0


def cari_maks(jenis, w, h, ctx, langkah=0.001, batas=0.03):
    grid = [round(i * langkah, 4) for i in range(int(round(batas / langkah)) + 1)]
    cache = {}

    def ok(i):
        if i not in cache:
            cache[i] = lolos(evaluasi(jenis, w, grid[i], ctx), h)
        return cache[i]

    if not ok(0):
        return None
    if ok(len(grid) - 1):
        return grid[-1]
    lo, hi = 0, len(grid) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if ok(m):
            lo = m
        else:
            hi = m
    return grid[lo]


def cagr_tanpa_tarik(jenis, w, ctx):
    r, cpi, akhir, awal, sbn, bi = ctx
    riil, _, _ = simulasi(awal[0], akhir, jenis, w, 0.0, r, cpi, sbn, bi)
    n = len(riil)
    nominal = riil[-1] * cpi[akhir] / cpi[awal[0] - 1]
    return nominal ** (12 / n) - 1, riil[-1] ** (12 / n) - 1


def sidik_input(akhir):
    db = d.koneksi()
    oj = db.rd_ojk.find_one({}, {"tgl": 1}, sort=[("tgl", -1)])
    inf = dt.baca("makro/inflasi")
    bi = dt.baca("makro/bi_rate")
    csv = (ROOT / "data" / "sbsn_ritel.csv").read_bytes()
    return {"rd_ojk": f"{oj['tgl']:%Y-%m}" if oj else None, "inflasi": f"{pd.Timestamp(inf.index.max()):%Y-%m}",
            "bi_rate": f"{pd.Timestamp(bi.index.max()):%Y-%m-%d}", "sbsn_csv": hashlib.sha256(csv).hexdigest()[:16], "akhir": str(akhir) if akhir is not None else None}


def ringkas_angka(v):
    v = np.array(v)
    return {"median": float(np.median(v)), "terburuk": float(v.min()), "utuh": float(np.mean(v >= 1))} if len(v) else None


def jalur_tahunan(m, tr):
    tahun = [{"tahun": 0, "median": 1.0, "terburuk": 1.0, "n": len(m["r3"])}]
    for k, v in sorted(m["per_tahun"].items()):
        v = np.array(v)
        tahun.append({"tahun": k, "median": float(np.median(v)), "terburuk": float(v.min()), "n": len(v)})
    return {"tarik": tr, "tahun": tahun, "dd_terdalam": float(m["dd"]), "dd_median": float(np.median(m["dd_semua"]))}


def simpan(ctx, mulai, akhir, hasil_cari):
    sbn = ctx[4]
    dok = {"dihitung": datetime.now(), "periode": {"awal": str(mulai), "akhir": str(akhir)}, "sidik": sidik_input(akhir),
           "syarat": "modal riil >= 100% di >= 80% tanggal mulai, tanpa gagal likuiditas; langkah 0,1% antara 0-3%",
           "dividen_jii": DIVIDEN_JII, "pajak_kupon": PAJAK, "n_penawaran_sbn": int(sbn["dasar"].nunique()),
           "n_mulai_3": len([x for x in ctx[3] if x + 35 <= akhir]), "n_mulai_5": len([x for x in ctx[3] if x + 59 <= akhir]), "portofolio": []}
    for nama, jenis, w in PORTOFOLIO:
        c_nom, c_riil = cagr_tanpa_tarik(jenis, w, ctx)
        a3, a5 = hasil_cari[nama]
        tabel = []
        for tr in TABEL_SIMPAN:
            m = evaluasi(jenis, w, tr, ctx)
            tabel.append({"tarik": tr, "riil5": ringkas_angka(m["r5"]), "riil3": ringkas_angka(m["r3"]), "gagal5": m["gagal5"]})
        di5 = evaluasi(jenis, w, a5, ctx) if a5 is not None else None
        tingkat = sorted(set(TABEL_SIMPAN) | ({round(a5, 4)} if a5 is not None else set()))
        jalur = [jalur_tahunan(evaluasi(jenis, w, tr, ctx), tr) for tr in tingkat]
        dok["portofolio"].append({"kode": KODE[nama], "nama": nama, "jenis": jenis, "porsi_sbn": w, "cagr_nominal": c_nom, "cagr_riil": c_riil,
                                  "aman_3": a3, "aman_5": a5, "kunci_rata": evaluasi(jenis, w, TABEL_SIMPAN[0], ctx)["kunci_rata"],
                                  "di_aman_5": ringkas_angka(di5["r5"]) if di5 else None, "tabel": tabel, "jalur": jalur})
    dt.db()["hasil_penarikan"].insert_one(dok)
    print()
    print(f"Disimpan ke {dt.NAMA_DB}.hasil_penarikan ({dok['dihitung']:%Y-%m-%d %H:%M}, data {mulai} s/d {akhir})")


def utama(tarik=TARIK, cari=False, simpan_hasil=False):
    r, cpi, akhir, mulai = siapkan()
    sbn = penawaran()
    bi = bi_rate()
    awal = pd.period_range(mulai, akhir, freq="M")
    ctx = (r, cpi, akhir, awal, sbn, bi)
    n5 = len([t for t in awal if t + 59 <= akhir])
    n3 = len([t for t in awal if t + 35 <= akhir])
    print(f"Data: indeks RD PT & PU tanpa bagi hasil (analisis_likuiditas), JII Yahoo + dividen asumsi {DIVIDEN_JII * 100:.1f}%/th, "
          f"inflasi BPS, BI-Rate, {sbn['dasar'].nunique()} penawaran SBN ritel ({len(sbn)} seri). Tanggal mulai {mulai} s/d {akhir - 36} (3 th, {n3}) / {akhir - 60} (5 th, {n5}).")
    print("Kolom: riil 3th & 5th = median / terburuk / % tanggal mulai >= 100% modal awal; DD = turun riil terdalam dalam 5 th (termasuk efek penarikan, SBN di 100);"
          " gagal = tanggal mulai dengan gagal likuiditas (bulan); kunci = porsi SBN rata-rata / maks.")
    print(f"{'portofolio':27s}{'tarik':>6s} | {'riil 3th med  min  >=100':>24s} | {'riil 5th med  min  >=100':>24s} | {'DD':>6s} | {'gagal':>10s} | {'kunci rata/maks':>15s}")
    hasil = {}
    for nama, jenis, w in PORTOFOLIO:
        for tr in tarik:
            m = evaluasi(jenis, w, tr, ctx)
            hasil[(nama, tr)] = m
            print(f"{nama:27s}{tr * 100:5.1f}% | {ringkas(m['r3']):>24s} | {ringkas(m['r5']):>24s} | {m['dd'] * 100:6.1f} | {m['gagal5']:3d} ({m['gagal_bln']:3d})"
                  f" | {m['kunci_rata'] * 100:6.0f}% {m['kunci_maks'] * 100:5.0f}%")
        print()
    print(f"Tingkat penarikan tertinggi dari daftar yang lolos (modal riil >= 100% di >= 80% tanggal mulai 5 th, tanpa gagal likuiditas):")
    for nama, _, _ in PORTOFOLIO:
        ok = [tr for tr in tarik if lolos(hasil[(nama, tr)], 5)]
        print(f"  {nama}: {f'{max(ok) * 100:.1f}%' if ok else 'tidak ada'}")
    hasil_cari = {}
    if cari or simpan_hasil:
        print()
        print("Tingkat penarikan maksimum yang lolos (langkah 0,1%, 0-3%; syarat sama, horizon 3 th dan 5 th):")
        print(f"{'portofolio':27s}{'3 th':>11s}{'5 th':>11s}")
        for nama, jenis, w in PORTOFOLIO:
            m3, m5 = cari_maks(jenis, w, 3, ctx), cari_maks(jenis, w, 5, ctx)
            hasil_cari[nama] = (m3, m5)
            f = lambda x: "tidak ada" if x is None else f"{x * 100:.1f}%"
            print(f"{nama:27s}{f(m3):>11s}{f(m5):>11s}", flush=True)
    print()
    print("CAGR tanpa penarikan (seluruh periode " + f"{mulai} s/d {akhir}" + "), nominal / riil:")
    for nama, jenis, w in PORTOFOLIO:
        c_nom, c_riil = cagr_tanpa_tarik(jenis, w, ctx)
        print(f"  {nama:27s}{c_nom * 100:6.2f}% / {c_riil * 100:5.2f}%")
    print()
    print("Porsi terkunci rata-rata: " + "; ".join(f"{n} {hasil[(n, tarik[0])]['kunci_rata'] * 100:.0f}%" for n, j, w in PORTOFOLIO if j == "rd"))
    print()
    print("Keterbatasan")
    print("  - Data ±10 tahun (mulai Apr 2016), jendela 5 th tumpang tindih: hanya ±6 jendela yang benar-benar terpisah; indikatif, bukan bukti.")
    print("  - Indeks RD = NAV bulanan bobot sama tanpa biaya beli/jual & tanpa survivorship RD terpilih; SBN dinilai di 100 (tidak mark-to-market), early redemption ST & batas pembelian per orang diabaikan.")
    print("  - Kupon ST direkonstruksi dari BI-Rate tiap 11 Feb/Mei/Agu/Nov + spread (ST010-ST015 spread turunan), kupon dihitung penuh mulai bulan setelah terbit.")
    print(f"  - JII = indeks harga + dividen asumsi {DIVIDEN_JII * 100:.1f}%/th; inflasi BPS YoY dibagi rata per bulan; tanpa pajak selain kupon SBN 10%.")
    if simpan_hasil:
        simpan(ctx, mulai, akhir, hasil_cari)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarik", default=",".join(str(x * 100) for x in TARIK))
    ap.add_argument("--cari", action="store_true")
    ap.add_argument("--simpan", action="store_true")
    a = ap.parse_args()
    utama([float(x) / 100 for x in a.tarik.split(",")], a.cari, a.simpan)
