import numpy as np
import pandas as pd

from backend.core.config import ROOT
from backend.db import data as dt
from backend.db import harga as hg
from backend.research import analisis_likuiditas as al

MULAI_PALING_CEPAT = pd.Period("2016-04", "M")
TARIK = [0.03, 0.04, 0.05, 0.06]
PAJAK = 0.10
DIVIDEN_JII = 0.025
HORIZON = 60
PORTOFOLIO = [("Opsi 1 RD PT/PU 50/50", "rd", 0.0), ("Opsi 2a SBN 30%", "rd", 0.30), ("Opsi 2b SBN 50%", "rd", 0.50),
              ("Opsi 2c SBN 70%", "rd", 0.70), ("Pembanding 54% JII/46% PU", "jii", 0.0)]


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
    riil, terkunci, gagal = [], [], 0
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
            gagal += 1
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


def utama():
    r, cpi, akhir, mulai = siapkan()
    sbn = penawaran()
    bi = bi_rate()
    awal = pd.period_range(mulai, akhir, freq="M")
    print(f"Data: indeks RD PT & PU tanpa bagi hasil (analisis_likuiditas), JII Yahoo + dividen asumsi {DIVIDEN_JII * 100:.1f}%/th, "
          f"inflasi BPS, BI-Rate, {sbn['dasar'].nunique()} penawaran SBN ritel ({len(sbn)} seri). Tanggal mulai {mulai} s/d {akhir - 36} (3 th) / {akhir - 60} (5 th).")
    print("Kolom: riil 3th & 5th = median / terburuk / % tanggal mulai >= 100% modal awal; DD = turun riil terdalam dalam 5 th (termasuk efek penarikan, SBN di 100);"
          " gagal = tanggal mulai dengan gagal likuiditas (bulan); kunci = porsi SBN rata-rata / maks.")
    print(f"{'portofolio':27s}{'tarik':>6s} | {'riil 3th med  min  >=100':>24s} | {'riil 5th med  min  >=100':>24s} | {'DD':>6s} | {'gagal':>10s} | {'kunci rata/maks':>15s}")
    lulus = {}
    for nama, jenis, w in PORTOFOLIO:
        for tr in TARIK:
            r3, r5, dd, gagal_mulai, gagal_bln, kunci_rata, kunci_maks = [], [], [], 0, 0, [], []
            for t0 in awal:
                if t0 + 35 > akhir:
                    break
                t_akhir = min(akhir, t0 + HORIZON - 1)
                riil, kunci, g = simulasi(t0, t_akhir, jenis, w, tr, r, cpi, sbn, bi)
                r3.append(riil[35])
                if len(riil) >= HORIZON:
                    r5.append(riil[HORIZON - 1])
                jalur = np.concatenate([[1.0], riil])
                dd.append((jalur / np.maximum.accumulate(jalur) - 1).min())
                gagal_mulai += g > 0
                gagal_bln += g
                kunci_rata.append(kunci.mean())
                kunci_maks.append(kunci.max())
            ddmin = min(dd) * 100
            print(f"{nama:27s}{tr * 100:5.0f}% | {ringkas(r3):>24s} | {ringkas(r5):>24s} | {ddmin:6.1f} | {gagal_mulai:3d} ({gagal_bln:3d})"
                  f" | {np.mean(kunci_rata) * 100:6.0f}% {max(kunci_maks) * 100:5.0f}%")
            if len(r5) and np.mean(np.array(r5) >= 1) >= 0.8 and gagal_mulai == 0:
                lulus[nama] = tr
        print()
    print(f"Tingkat penarikan tertinggi dengan modal riil >= 100% di >= 80% tanggal mulai (5 th) dan tanpa gagal likuiditas "
          f"({len([t for t in awal if t + 59 <= akhir])} tanggal mulai):")
    for nama, _, _ in PORTOFOLIO:
        print(f"  {nama}: {f'{lulus[nama] * 100:.0f}%' if nama in lulus else 'tidak ada (bahkan 3%)'}")
    print("\nKeterbatasan")
    print("  - Data ±10 tahun (mulai Apr 2016), jendela 5 th tumpang tindih: hanya ±6 jendela yang benar-benar terpisah; indikatif, bukan bukti.")
    print("  - Indeks RD = NAV bulanan bobot sama tanpa biaya beli/jual & tanpa survivorship RD terpilih; SBN dinilai di 100 (tidak mark-to-market), early redemption ST & batas pembelian per orang diabaikan.")
    print("  - Kupon ST direkonstruksi dari BI-Rate tiap 11 Feb/Mei/Agu/Nov + spread (ST010-ST015 spread turunan), kupon dihitung penuh mulai bulan setelah terbit.")
    print(f"  - JII = indeks harga + dividen asumsi {DIVIDEN_JII * 100:.1f}%/th; inflasi BPS YoY dibagi rata per bulan; tanpa pajak selain kupon SBN 10%.")


if __name__ == "__main__":
    utama()
