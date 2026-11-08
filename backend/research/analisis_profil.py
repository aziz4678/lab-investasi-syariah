import numpy as np
import pandas as pd

from backend.db import koneksi as d
from backend.research import analisis_likuiditas as al
from backend.research import analisis_penarikan as ap

TIPE = {"SH": ["Equity Fund"], "CA": ["Mixed Asset Fund"]}
LOMPAT = 0.30
SISA_KONSERVATIF = {"PT": 0.5, "PU": 0.5}
PORSI_SAHAM = {"Moderat": 0.30, "Agresif": 0.60}
REBALANCE_BULAN = 12
PENARIKAN = "proporsional dari semua bagian (profil = satu aset di jalur RD tanpa SBN analisis_penarikan)"
ASUMSI = {"sisa": "RD PT/PU 50/50 tanpa SBN", "rebalance": "tiap akhir Desember ke bobot awal, tanpa ambang", "penarikan": PENARIKAN}


def _bobot(saham):
    return {"SH": saham, **{k: (1 - saham) * w for k, w in SISA_KONSERVATIF.items()}}


PROFIL = [("Konservatif PT/PU 50/50", dict(SISA_KONSERVATIF))] +          [(f"{nama} {saham * 100:.0f}% saham", _bobot(saham)) for nama, saham in PORSI_SAHAM.items()] +          [("RD campuran 100%", {"CA": 1.0})]
JENDELA = 60


def muat():
    db = d.koneksi()
    tipe = {t: k for k, v in TIPE.items() for t in v}
    df = pd.DataFrame(list(db.rd_ojk.find({"syariah": True, "denominasi": "IDR", "tipe": {"$in": list(tipe)}},
                                           {"_id": 0, "kunci": 1, "produk": 1, "tipe": 1, "tgl": 1, "nav": 1, "nab": 1, "fund": 1})))
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    df["kelompok"] = df["tipe"].map(tipe)
    fund = df["fund"].astype("Int64").astype(str)
    df["seri"] = np.where(df["fund"].notna(), "f" + fund, df["kunci"])
    bagi = {int(x["_id"]) for x in db.rd_produk.find({"Dividend": True}, {"_id": 1})}
    return df, bagi


def indeks_baru(cetak=True):
    df, bagi = muat()
    pilih, seri, dobel = al.pilih_seri(df, bagi)
    hasil, periksa = {}, []
    for k in TIPE:
        idx = pilih[(pilih.kelompok == k) & ~pilih.bh_pasardana].index
        R = al.tabel_return(seri, idx)
        ekstrem = R.abs() > LOMPAT
        for s in idx:
            for t, v in R[s][ekstrem[s]].items():
                periksa.append((k, pilih.loc[s, "produk"], str(t), v))
        L, n = al.indeks(R.mask(ekstrem))
        hasil[k] = (L, n, idx)
        if cetak:
            nama = "RD saham syariah" if k == "SH" else "RD campuran syariah"
            print(f"{nama}: {len(idx)} seri dipakai (kelas dobel dikeluarkan bersama tipe lain: {dobel}; bagi hasil tunai Pasardana dikeluarkan "
                  f"{int((pilih[pilih.kelompok == k].bh_pasardana).sum())}); indeks mulai {L.index[1] if L is not None else '-'} (min {al.MIN_PRODUK} produk)")
            th = range(n.index.min().year, n.index.max().year + 1)
            baris = []
            for y in th:
                a = n.get(pd.Period(f"{y}-01", "M"), 0)
                b = n[n.index.year == y].iloc[-1]
                baris.append(f"{y}: {a}->{b}")
            print("  jumlah produk ber-NAV per tahun (Jan -> bulan terakhir): " + ", ".join(baris))
    return hasil, periksa


def gabung(L, bobot):
    mulai = max(L[k].index[0] for k in bobot)
    r = {k: (L[k] / L[k].shift(1) - 1).loc[mulai + 1:] for k in bobot}
    idx = r[next(iter(bobot))].index
    for k in bobot:
        idx = idx.intersection(r[k].index)
    nilai, w = [1.0], dict(bobot)
    for t in idx:
        for k in w:
            w[k] *= 1 + r[k][t]
        nilai.append(sum(w.values()))
        if t.month == REBALANCE_BULAN:
            tot = sum(w.values())
            w = {k: tot * bobot[k] for k in bobot}
    return pd.Series(nilai, index=[mulai] + list(idx))


def ctx_profil(h, Lp, mulai_umum):
    rr, cpi, akhir, mulai = ap.siapkan(h, {"PT": Lp, "PU": Lp})
    mulai = max(mulai, mulai_umum)
    return (rr, cpi, akhir, pd.period_range(mulai, akhir, freq="M"), ap.penawaran(), ap.bi_rate())


def tahun_terburuk(L, c, mulai):
    T = al.per_tahun(L.loc[mulai - 1:], c)
    y = min(T, key=lambda k: T[k][1])
    return T[y]


def utama():
    h = al.semua_indeks()
    baru, periksa = indeks_baru()
    L = {"PT": h["L"]["PT"], "PU": h["L"]["PU"], "SH": baru["SH"][0], "CA": baru["CA"][0]}
    print(f"\nDaftar periksa lompatan NAV > +/-{LOMPAT * 100:.0f}%/bulan (bulan itu dikeluarkan dari indeks, tidak dibuang diam-diam): {len(periksa)} kejadian")
    for k, prod, t, v in sorted(periksa, key=lambda x: -abs(x[3])):
        print(f"  {k} {t} {v * 100:+.1f}%  {prod}")

    c = al.cpi()
    _, _, akhir, mulai0 = ap.siapkan(h)
    mulai = max([mulai0] + [L[k].index[0] + 1 for k in ("SH", "CA")])
    print(f"\nPeriode portofolio: {mulai} s/d {akhir}. Asumsi: sisa porsi {ASUMSI['sisa']}; rebalance {ASUMSI['rebalance']}; penarikan {ASUMSI['penarikan']}")
    for nama, bobot in PROFIL:
        print(f"  {nama}: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in bobot.items()))
    Lp, baris = {}, []
    for nama, bobot in PROFIL:
        x = gabung(L, bobot)
        x = x.loc[mulai - 1:akhir] / x.loc[mulai - 1]
        Lp[nama] = x
        ap._CACHE.clear()
        ctx = ctx_profil(h, x, mulai)
        a3, a5 = ap.cari_maks("rd", 0.0, 3, ctx), ap.cari_maks("rd", 0.0, 5, ctx)
        nom, riil = ap.cagr_tanpa_tarik("rd", 0.0, ctx)
        m = al.metrik(x, c)
        lab, yn, yr = tahun_terburuk(x, c, mulai)
        nol = ap.evaluasi("rd", 0.0, 0.0, ctx)
        baris.append((nama, nom, riil, m["dd"], m["lembah"], lab, yn, yr, m["pulih"], a3, a5, np.median(nol["r5"]), min(nol["r5"])))
    ap._CACHE.clear()

    f = lambda v: "tidak ada" if v is None else f"{v * 100:.1f}%"
    print("\nprofil                    CAGR nom  riil   turun terdalam (lembah)   tahun terburuk nom/riil      pulih    aman 3th  aman 5th  modal riil 5th tanpa tarik med/terburuk")
    for nama, nom, riil, dd, lembah, lab, yn, yr, pulih, a3, a5, med, bur in baris:
        print(f"{nama:25s}{nom * 100:+7.2f}% {riil * 100:+6.2f}%  {dd * 100:7.1f}% ({lembah})   {lab:17s}{yn * 100:+6.1f}/{yr * 100:+6.1f}%  {pulih:>8s}  {f(a3):>8s}  {f(a5):>8s}  {med * 100:6.1f}% / {bur * 100:5.1f}%")

    K = Lp[PROFIL[0][0]]
    print(f"\n% jendela {JENDELA // 12} th (tanpa penarikan, semua tanggal mulai bulanan) yang modal akhirnya lebih tinggi dari Konservatif:")
    for nama, _ in PROFIL[1:]:
        X = Lp[nama]
        menang = [X[t + JENDELA] / X[t] > K[t + JENDELA] / K[t] for t in X.index if t + JENDELA in X.index]
        print(f"  {nama:25s}{np.mean(menang) * 100:5.0f}%  (n={len(menang)} jendela tumpang tindih, mulai {X.index[0]} s/d {X.index[-1] - JENDELA})")

    print("\nKeterbatasan")
    print("  - Periode 2016-2026 buruk untuk saham Indonesia; hasil sangat bergantung periode (jendela 5 th tumpang tindih, hanya ±2 yang terpisah).")
    print("  - NAV saja (bukan return total), NAV akhir bulan; RD bagi hasil tunai (tanda Pasardana) dikeluarkan; tanpa biaya beli/jual.")
    print("  - RD saham & campuran syariah dikelola aktif oleh MI, bukan indeks; indeks = rata-rata bobot sama semua produk, termasuk yang sudah bubar.")
    print("  - Lompatan > 30% dikeluarkan dari indeks; 13 di antaranya penurunan RD saham Nov 2019 (±31-47%) yang kemungkinan rugi asli, jadi indeks saham cenderung terlalu bagus. Deskriptif, bukan hipotesis.")


if __name__ == "__main__":
    utama()
