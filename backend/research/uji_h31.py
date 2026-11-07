import argparse
import hashlib
import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi as d

HARI_TH = 252
BULAN_MA = 10
KUNCI_RD = "BNIAM DANA LANCAR SYARIAH|BANK MAYBANK INDONESIA"
DEV = ("2013-06-30", "2019-12-31")
HOLDOUT = ("2019-12-31", "2026-09-30")
DASAR = {"div": 2.5, "exp": 2.0, "kas": "rd", "keluar": 0.007, "masuk": 0.006, "jeda_masuk": 3}
SKENARIO = {
    "dasar": {},
    "6a_dividen_4": {"div": 4.0},
    "6b_expense_1_6": {"exp": 1.6},
    "7_kas_median_rdpu": {"kas": "median"},
    "s1_biaya_2_tick": {"keluar": 0.0115, "masuk": 0.0105},
    "lap_kas_0": {"kas": "nol"},
    "lap_jeda_pencairan_7": {"jeda_masuk": 7},
}
WAJIB_K12 = ["6a_dividen_4", "6b_expense_1_6", "7_kas_median_rdpu", "s1_biaya_2_tick"]


def jii():
    s = hg.indeks("indeks/JKII")["close"].dropna().sort_index()
    s.index = pd.to_datetime(s.index)
    if s.index.max() < pd.Timestamp(HOLDOUT[1]):
        raise hg.DataTidakAda("indeks/JKII belum sampai akhir holdout")
    return s


def nav_rd():
    db = d.koneksi()
    df = pd.DataFrame(list(db.rd_ojk.find({"tipe": "Money Market Fund", "syariah": True, "denominasi": "IDR"},
                                           {"_id": 0, "kunci": 1, "tgl": 1, "nav": 1})))
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    tabel = df.pivot_table(index="tgl", columns="kunci", values="nav", aggfunc="last").sort_index()
    return tabel


def seri_satu(tabel):
    return tabel[KUNCI_RD].dropna()


def seri_median(tabel):
    bulan = pd.period_range(tabel.index.min(), tabel.index.max(), freq="M")
    t = tabel.reindex(bulan)
    r = (t / t.shift(1)).median(axis=1, skipna=True)
    r.iloc[0] = 1.0
    ada = (t.notna() & t.shift(1).notna()).any(axis=1)
    ada.iloc[0] = True
    level = r.where(ada).dropna().cumprod()
    return level


def kas_harian(level, hari):
    level = level.sort_index()
    f = pd.Series(np.nan, index=hari)
    bln_hari = pd.Series(hari.to_period("M"), index=hari)
    titik = list(level.index)
    for a, b in zip(titik[:-1], titik[1:]):
        g = level[b] / level[a]
        pilih = (bln_hari > a) & (bln_hari <= b)
        n = int(pilih.sum())
        if n:
            f[pilih.to_numpy()] = g ** (1 / n)
    return f


def sinyal(c):
    akhir = c.groupby(c.index.to_period("M")).tail(1)
    ma = akhir.rolling(BULAN_MA).mean()
    s = pd.Series(np.where(akhir >= ma, "pasar", "kas"), index=akhir.index.to_period("M"))
    return s.where(ma.notna().to_numpy())


def simulasi(c, kas_f, sk, mulai, akhir, awal_h, bh_sudah, cek_awal=False):
    sig = sinyal(c[c.index <= pd.Timestamp(akhir)])
    sebelum = c[c.index <= pd.Timestamp(mulai)]
    idx = c.index[(c.index > pd.Timestamp(mulai)) & (c.index <= pd.Timestamp(akhir))]
    pasar_hari = (1 + (sk["div"] - sk["exp"]) / 100) ** (1 / HARI_TH)
    v_h = v_b = 1.0
    keadaan = awal_h
    perlu_beli_awal = awal_h == "pasar" and not bh_sudah
    bh_masuk = bh_sudah
    transit = 0
    ek_h, ek_b, di_pasar, tindakan = [], [], [], []
    sebelumnya = sebelum.iloc[-1]
    bulan_lalu = None if cek_awal else idx[0].to_period("M")
    for i, t in enumerate(idx):
        r = c[t] / sebelumnya
        bln = t.to_period("M")
        if bln != bulan_lalu:
            bulan_lalu = bln
            target = sig.get(bln - 1)
            if isinstance(target, str) and target != keadaan and keadaan in ("pasar", "kas"):
                tindakan.append((t, "keluar" if keadaan == "pasar" else "masuk"))
                keadaan = "akan_keluar" if keadaan == "pasar" else "akan_masuk"
        if sk["kas"] == "nol":
            kas_r = 1.0
        else:
            kas_r = kas_f[t]
            if not np.isfinite(kas_r):
                raise hg.DataTidakAda(f"NAV kas tidak ada untuk {t:%Y-%m-%d}")
        pasar_hari_ini = False
        if i == 0 and perlu_beli_awal:
            v_h *= 1 - sk["masuk"]
            pasar_hari_ini = True
        elif keadaan in ("pasar", "akan_keluar"):
            v_h *= r * pasar_hari
            pasar_hari_ini = True
            if keadaan == "akan_keluar":
                v_h *= 1 - sk["keluar"]
                keadaan, transit = "transit_kas", 3
        elif keadaan == "kas":
            v_h *= kas_r
        elif keadaan == "transit_kas":
            transit -= 1
            if transit == 0:
                keadaan = "kas"
        elif keadaan == "akan_masuk":
            keadaan, transit = "transit_pasar", sk["jeda_masuk"]
        elif keadaan == "transit_pasar":
            transit -= 1
            if transit == 0:
                v_h *= 1 - sk["masuk"]
                keadaan = "pasar"
        if bh_masuk:
            v_b *= r * pasar_hari
        else:
            v_b *= 1 - sk["masuk"]
            bh_masuk = True
        ek_h.append(v_h)
        ek_b.append(v_b)
        di_pasar.append(pasar_hari_ini)
        sebelumnya = c[t]
    return (pd.Series(ek_h, index=idx), pd.Series(ek_b, index=idx), tindakan,
            1 - float(np.mean(di_pasar)), keadaan)


def campuran(c, kas_f, sk, mulai, akhir, w):
    idx = c.index[(c.index > pd.Timestamp(mulai)) & (c.index <= pd.Timestamp(akhir))]
    pasar_hari = (1 + (sk["div"] - sk["exp"]) / 100) ** (1 / HARI_TH)
    akhir_bulan = set(pd.Series(idx, index=idx).groupby(idx.to_period("M")).max())
    a, b = w, 1 - w
    out = []
    sebelumnya = c[c.index <= pd.Timestamp(mulai)].iloc[-1]
    for t in idx:
        a *= c[t] / sebelumnya * pasar_hari
        b *= 1.0 if sk["kas"] == "nol" else kas_f[t]
        v = a + b
        if t in akhir_bulan:
            a, b = w * v, (1 - w) * v
        out.append(v)
        sebelumnya = c[t]
    return pd.Series(out, index=idx)


def metrik(e, mulai):
    awal = pd.concat([pd.Series([1.0], index=[pd.Timestamp(mulai)]), e])
    th = (awal.index[-1] - awal.index[0]).days / 365.25
    cagr = (awal.iloc[-1] ** (1 / th) - 1) * 100
    dd = (awal / awal.cummax() - 1).min() * 100
    return float(cagr), float(dd)


def tanpa_tahun_terbaik(e, mulai):
    awal = pd.concat([pd.Series([1.0], index=[pd.Timestamp(mulai)]), e])
    r = awal.pct_change().dropna()
    per_th = (1 + r).groupby(r.index.year).prod() - 1
    terbaik = int(per_th.idxmax())
    th_total = (awal.index[-1] - awal.index[0]).days / 365.25
    sisa = r[r.index.year != terbaik]
    th = th_total * len(sisa) / len(r)
    lv = (1 + sisa).cumprod()
    lv = pd.concat([pd.Series([1.0]), lv.reset_index(drop=True)])
    cagr = (lv.iloc[-1] ** (1 / th) - 1) * 100
    dd = (lv / lv.cummax() - 1).min() * 100
    return float(cagr), float(dd), terbaik


def jendela(eh, eb, mulai, akhir, tahun=3, min_hari=500):
    menang, total = 0, 0
    for s in pd.date_range(pd.Timestamp(mulai), pd.Timestamp(akhir), freq="ME"):
        u = s + pd.DateOffset(years=tahun)
        if u > pd.Timestamp(akhir):
            break
        h = eh[(eh.index > s) & (eh.index <= u)]
        b = eb[(eb.index > s) & (eb.index <= u)]
        if len(h) < min_hari:
            continue
        hs = eh[eh.index <= s].iloc[-1] if (eh.index <= s).any() else 1.0
        bs = eb[eb.index <= s].iloc[-1] if (eb.index <= s).any() else 1.0
        ch, dh = metrik(h / hs, s)
        cb, db_ = metrik(b / bs, s)
        total += 1
        if abs(dh) < abs(db_) and ch >= cb - 2:
            menang += 1
    return menang, total


def per_tahun(e, mulai):
    awal = pd.concat([pd.Series([1.0], index=[pd.Timestamp(mulai)]), e])
    th = e.groupby(e.index.year).last()
    r = th / th.shift(1).fillna(1.0) - 1
    return (r * 100).round(2)


def cek_data(c, tabel, mulai, akhir):
    cj = c[(c.index > pd.Timestamp(mulai) - pd.Timedelta(days=400)) & (c.index <= pd.Timestamp(akhir))]
    jarak = cj.index.to_series().diff().dt.days.max()
    lonjak = int((cj.pct_change().abs() > 0.15).sum())
    s = seri_satu(tabel)
    s = s[(s.index >= pd.Timestamp(mulai).to_period("M")) & (s.index <= pd.Timestamp(akhir).to_period("M"))]
    semua = pd.period_range(s.index.min(), s.index.max(), freq="M")
    hilang = [str(x) for x in semua if x not in s.index]
    r = s / s.shift(1) - 1
    return {"jii_jeda_hari_maks": int(jarak), "jii_lonjakan_15pct": lonjak,
            "nav_bulan_hilang": hilang, "nav_lonjakan_1_5pct": int((r.abs() > 0.015).sum()), "nav_turun": int((r < 0).sum()),
            "nav_dari": str(s.index.min()), "nav_sampai": str(s.index.max())}


def sidik_seri(s):
    return hashlib.sha256(pd.util.hash_pandas_object(s.astype(float).round(8), index=True).values.tobytes()).hexdigest()[:16]


def bobot_sama_dev(mulai, akhir):
    from backend.research import uji_h21_h22 as m
    S = m.susun("dev")
    e = m.pembanding_sama(S)
    e.index = pd.to_datetime(e.index)
    dasar = e[e.index <= pd.Timestamp(mulai)].iloc[-1]
    e = e[(e.index > pd.Timestamp(mulai)) & (e.index <= pd.Timestamp(akhir))] / dasar
    return e


def jalankan(periode, ew=True):
    c = jii()
    tabel = nav_rd()
    level = {"rd": seri_satu(tabel), "median": seri_median(tabel)}
    mulai, akhir = DEV if periode == "dev" else HOLDOUT
    mulai_t = c[c.index <= pd.Timestamp(mulai)].index[-1]
    hari = c.index[(c.index > mulai_t) & (c.index <= pd.Timestamp(akhir))]
    kas = {k: kas_harian(v, hari) for k, v in level.items()}
    data = cek_data(c, tabel, mulai, akhir)
    sig = sinyal(c)
    hasil = {}
    for nama, ubah in SKENARIO.items():
        sk = {**DASAR, **ubah}
        kf = kas["median" if sk["kas"] == "median" else "rd"]
        if periode == "dev":
            awal_h, bh_sudah = sig.get(mulai_t.to_period("M")), False
        else:
            kf0 = kas_harian(level["median" if sk["kas"] == "median" else "rd"],
                             c.index[(c.index > c[c.index <= pd.Timestamp(DEV[0])].index[-1]) & (c.index <= pd.Timestamp(DEV[1]))])
            _, _, _, _, pos = simulasi(c, kf0, sk, c[c.index <= pd.Timestamp(DEV[0])].index[-1], DEV[1],
                                       sig.get(c[c.index <= pd.Timestamp(DEV[0])].index[-1].to_period("M")), False)
            awal_h = "pasar" if pos in ("pasar", "akan_keluar", "transit_pasar") else "kas"
            bh_sudah = True
        eh, eb, tindakan, kas_pct, _ = simulasi(c, kf, sk, mulai_t, akhir, awal_h, bh_sudah, cek_awal=periode == "holdout")
        ch, dh = metrik(eh, mulai_t)
        cb, db_ = metrik(eb, mulai_t)
        th = (eh.index[-1] - mulai_t).days / 365.25
        h = {"cagr": ch, "dd": dh, "cagr_bh": cb, "dd_bh": db_, "pindah": len(tindakan), "pindah_th": len(tindakan) / th,
             "kas_pct": kas_pct * 100, "awal": awal_h,
             "k1": abs(dh) <= abs(db_) * 2 / 3, "k2": ch >= cb - 2}
        if nama == "dasar":
            w = 1 - kas_pct
            em = campuran(c, kf, sk, mulai_t, akhir, w)
            cm, dm = metrik(em, mulai_t)
            m_, n_ = jendela(eh, eb, mulai_t, akhir)
            ct, dt_, tt = tanpa_tahun_terbaik(eh, mulai_t)
            cbt, dbt, tbt = tanpa_tahun_terbaik(eb, mulai_t)
            h.update({"porsi_campuran": w * 100, "cagr_campuran": cm, "dd_campuran": dm,
                      "k3": abs(dh) < abs(dm) and ch >= cm - 1, "k4": h["pindah_th"] <= 3,
                      "jendela_menang": m_, "jendela_total": n_, "jendela_pct": m_ / n_ * 100 if n_ else None,
                      "k5": bool(n_) and m_ / n_ >= 0.6,
                      "tanpa_terbaik": {"cagr": ct, "dd": dt_, "tahun": tt, "cagr_bh": cbt, "dd_bh": dbt, "tahun_bh": tbt,
                                        "lulus": abs(dt_) <= abs(dbt) * 2 / 3 and ct >= cbt - 2},
                      "per_tahun": pd.DataFrame({"H31": per_tahun(eh, mulai_t), "beli_tahan": per_tahun(eb, mulai_t),
                                                 "campuran": per_tahun(em, mulai_t)}).rename_axis("tahun").reset_index().to_dict("records"),
                      "tindakan": [(t.strftime("%Y-%m-%d"), j) for t, j in tindakan],
                      "kurva": {"tgl": [x.strftime("%Y-%m-%d") for x in eh.index[::5]], "H31": [round(float(x), 4) for x in eh.values[::5]],
                                "beli_tahan": [round(float(x), 4) for x in eb.values[::5]], "campuran": [round(float(x), 4) for x in em.values[::5]]}})
        hasil[nama] = h
    da = hasil["dasar"]
    kriteria = [("1. DD <= 2/3 DD beli-tahan", f"{da['dd']:.1f}% vs batas {da['dd_bh'] * 2 / 3:.1f}% (BH {da['dd_bh']:.1f}%)", da["k1"]),
                ("2. CAGR >= BH - 2", f"{da['cagr']:.2f}% vs batas {da['cagr_bh'] - 2:.2f}% (BH {da['cagr_bh']:.2f}%)", da["k2"]),
                ("3. timing vs campuran tetap", f"porsi JII {da['porsi_campuran']:.0f}%: DD {da['dd']:.1f}% vs {da['dd_campuran']:.1f}%, CAGR {da['cagr']:.2f}% vs batas {da['cagr_campuran'] - 1:.2f}%", da["k3"]),
                ("4. pindah <= 3/th", f"{da['pindah_th']:.2f}/th ({da['pindah']}x)", da["k4"]),
                ("5. jendela 3 th >= 60%", f"{da['jendela_pct']:.0f}% dari {da['jendela_total']}" if da["jendela_total"] else "0 jendela", da["k5"])]
    for nama in WAJIB_K12:
        h = hasil[nama]
        kriteria.append((nama, f"DD {h['dd']:.1f}% vs {h['dd_bh'] * 2 / 3:.1f}% | CAGR {h['cagr']:.2f}% vs {h['cagr_bh'] - 2:.2f}%", h["k1"] and h["k2"]))
    tt = da["tanpa_terbaik"]
    kriteria.append(("tanpa tahun terbaik", f"H31 tanpa {tt['tahun']}: CAGR {tt['cagr']:.2f}%, DD {tt['dd']:.1f}% | BH tanpa {tt['tahun_bh']}: CAGR {tt['cagr_bh']:.2f}%, DD {tt['dd_bh']:.1f}%", tt["lulus"]))
    lulus = all(o for _, _, o in kriteria)
    lap = {}
    if ew and periode == "dev":
        e = bobot_sama_dev(mulai_t, akhir)
        ce, de = metrik(e, mulai_t)
        lap["bobot_sama"] = {"cagr": ce, "dd": de}
    versi_data = {"jii": {"sumber": "indeks/JKII", "versi": dt.versi("indeks/JKII"), "sidik_close": sidik_seri(c[c.index <= pd.Timestamp(akhir)]),
                          "dari": c.index[0].strftime("%Y-%m-%d"), "sampai": min(c.index[-1], pd.Timestamp(akhir)).strftime("%Y-%m-%d")},
                  "nav": {"sumber": "swing.rd_ojk", "kunci": KUNCI_RD, "sidik_rd": sidik_seri(level["rd"].astype(float).set_axis(level["rd"].index.astype(str))),
                          "sidik_median": sidik_seri(level["median"].astype(float).set_axis(level["median"].index.astype(str))),
                          "produk_rdpu": int(tabel.shape[1])},
                  "cek_data": data, **hg.status_koreksi()}
    out = {"periode": periode, "mulai": mulai_t.strftime("%Y-%m-%d"), "akhir": hari[-1].strftime("%Y-%m-%d"),
           "kriteria": kriteria, "lulus": lulus, "skenario": hasil, "laporan": lap, "versi_data": versi_data, "dibuat": datetime.now()}
    out = json.loads(json.dumps(out, default=lambda x: x.isoformat() if hasattr(x, "isoformat") else (bool(x) if isinstance(x, np.bool_) else float(x))))
    dt.simpan_hasil(f"h31_{periode}", out)
    return out


def cetak(o):
    print(f"\n##### H31 {o['periode'].upper()} {o['mulai']} s/d {o['akhir']}")
    print("cek data:", o["versi_data"]["cek_data"])
    print(f"{'skenario':24s} {'awal':>5s} {'CAGR':>7s} {'DD':>7s} {'CAGR BH':>8s} {'DD BH':>7s} {'pindah/th':>9s} {'% kas':>6s} k1 k2")
    for n, h in o["skenario"].items():
        print(f"{n:24s} {h['awal']:>5s} {h['cagr']:6.2f}% {h['dd']:6.1f}% {h['cagr_bh']:7.2f}% {h['dd_bh']:6.1f}% {h['pindah_th']:9.2f} {h['kas_pct']:5.0f}%  "
              f"{'Y' if h['k1'] else '-'}  {'Y' if h['k2'] else '-'}")
    print()
    for a, v, ok in o["kriteria"]:
        print(f"  [{'LULUS' if ok else 'GAGAL'}] {a}: {v}")
    if o["laporan"]:
        print("laporan bobot sama:", {k: round(v, 2) for k, v in o["laporan"]["bobot_sama"].items()})
    da = o["skenario"]["dasar"]
    print("\nper tahun:")
    for r in da["per_tahun"]:
        print("  ", r)
    print("perpindahan:", ", ".join(f"{t[:7]} {j}" for t, j in da["tindakan"]))
    print(f"\nHASIL AKHIR H31 {o['periode'].upper()}: {'LULUS' if o['lulus'] else 'GAGAL'}")


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    a = ap.parse_args()
    if a.periode == "holdout":
        dev = dt.baca_hasil("h31_dev")
        if not dev or not dev.get("lulus"):
            raise SystemExit("holdout H31 hanya boleh dibuka kalau dev lulus semua")
        penanda = d.penanda("holdout_dibuka_h31")
        if penanda.exists():
            raise SystemExit(f"holdout H31 sudah pernah dibuka ({penanda.read_text().strip()})")
        penanda.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    cetak(jalankan(a.periode))


if __name__ == "__main__":
    utama()
