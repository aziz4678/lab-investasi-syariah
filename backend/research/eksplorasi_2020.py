import contextlib
import io
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt

NAMA_RINGKAS = "eksplorasi_2020_ringkas"
NAMA_LOG = "eksplorasi_2020_log"
MULAI = pd.Timestamp("2020-01-01")
AKHIR = pd.Timestamp("2026-12-31")
KRITERIA_TRADE = {
    "exp": "Bersih/trade > 0", "pemb": "Di atas pembanding acak", "boot": "Bootstrap 90% > 0", "th70": "Tahun positif ≥ 70%",
    "t10": "Tanpa 10 trade terbaik > 0", "t5": "Tanpa 5 saham terbaik > 0", "bh": "CAGR > beli-tahan",
}
CATATAN_UMUM = ("Diuji ulang setelah hasil 2020+ diketahui (Follow Tren sudah lulus di periode ini), ±30 uji dijalankan sekaligus "
                "sehingga 2-3 bisa lulus karena kebetulan, dan data 2020+ sudah terbuka untuk semua hipotesis. "
                "Status hipotesis tidak berubah; bukti berikutnya hanya dari paper trade / uji maju.")
LOG = []


@contextlib.contextmanager
def tanpa_simpan():
    asli = dt.simpan_hasil, dt.hasil_teks
    dt.simpan_hasil = lambda *a, **k: None

    def tolak(*a, **k):
        raise RuntimeError("eksplorasi tidak boleh menulis status uji")

    dt.hasil_teks = tolak
    try:
        yield
    finally:
        dt.simpan_hasil, dt.hasil_teks = asli


def tangkap(fungsi, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        hasil = fungsi(*a, **k)
    LOG.append(buf.getvalue())
    return hasil, buf.getvalue()


def skor_cetak(teks, pola=r"=>.*\((\d+)/(\d+)\)"):
    m = re.findall(pola, teks)
    return (int(m[-1][0]), int(m[-1][1])) if m else (None, None)


def pct(v, tanda=True, d=2):
    if v is None or not np.isfinite(v):
        return "–"
    return (f"{v:+.{d}f}%" if tanda else f"{v:.{d}f}%").replace(".", ",")


def potong(df):
    return df[(df["tgl"] >= MULAI) & (df["tgl"] <= AKHIR)].copy()


def nilai_trade(kode, tr, dasar, bm, maks=10):
    from backend.research import screener as sc
    from backend.research.laporan_bulanan import ringkas_bulanan
    tr, dasar = potong(tr), potong(dasar)
    if tr.empty:
        return {"kode": kode, "jenis": "trade", "lulus": "0/7", "lulus_semua": False, "metrik": [["Trade", "0"]], "gagal_di": ["tidak ada trade"]}
    lo, _ = sc.bootstrap(tr)
    th = tr.groupby(tr["tgl"].dt.year)["net"].mean()
    tanpa10 = tr.drop(tr["net"].nlargest(10).index)["net"].mean()
    lima = tr.groupby("ticker")["net"].sum().nlargest(5).index
    tanpa5 = tr[~tr["ticker"].isin(lima)]["net"].mean()
    with contextlib.redirect_stdout(io.StringIO()):
        b = ringkas_bulanan(tr, maks)
    cagr = b.get("cagr", np.nan)
    k = {"exp": tr["net"].mean() > 0, "pemb": tr["net"].mean() > dasar["net"].mean(), "boot": lo > 0, "th70": (th > 0).mean() >= 0.7,
         "t10": tanpa10 > 0, "t5": tanpa5 > 0, "bh": cagr > bm}
    return {"kode": kode, "jenis": "trade", "lulus": f"{sum(k.values())}/{len(k)}", "lulus_semua": all(k.values()),
            "gagal_di": [KRITERIA_TRADE[n] for n, v in k.items() if not v],
            "angka": {"trade": int(len(tr)), "kotor": float(tr["kotor"].mean()), "net": float(tr["net"].mean()), "tanpa10": float(tanpa10),
                      "cagr": float(cagr), "dd": float(b.get("dd", np.nan)), "bh": float(bm), "tahun_positif": f"{int((th > 0).sum())}/{len(th)}"},
            "metrik": [["Trade", f"{len(tr):,}".replace(",", ".")], ["Kotor/trade", pct(tr["kotor"].mean())], ["Bersih/trade", pct(tr["net"].mean())],
                       ["Tanpa 10 terbaik", pct(tanpa10)], ["CAGR (1 undian)", pct(cagr, d=1)], ["DD (1 undian)", pct(b.get("dd", np.nan), d=1)],
                       ["Beli-tahan", pct(bm, d=1)]]}


def dividen_event(siap):
    from backend.research.uji_dividen import bersih
    ev = []
    for t, x in siap.items():
        m = dt.baca(f"harga/{t}").reindex(x.index)
        if "dividends" not in m:
            continue
        div = m["dividends"].fillna(0).to_numpy(float)
        o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
        rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
        lolos = x["lolos"].to_numpy(bool)
        for k in np.flatnonzero(div > 0):
            i = k - 6
            if i < 0 or not lolos[i]:
                continue
            e, xk = o[k - 5], c[k - 1]
            ev.append({"ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k - 1], "kotor": (xk / e - 1) * 100,
                       "net": bersih(e, xk, e * rasio[k - 5], xk * rasio[k - 1])})
    return pd.DataFrame(ev)


def hari_dipegang(tr):
    s = set()
    for r in tr.itertuples():
        for d in pd.bdate_range(r.tgl, r.tgl_exit):
            s.add((r.ticker, d))
    return s


def per_trade():
    from backend.research import screener as sc
    from backend.research import uji_asing as ua
    from backend.research import uji_h19 as h19
    from backend.research import uji_setup as us
    from backend.research import uji_tahap2 as t2
    from backend.research import uji_tren as ut
    hasil = {}
    print("menyiapkan universe DES historis 2018+ ...", flush=True)
    siap = h19.siapkan("holdout")
    for x in siap.values():
        ut.tambah_fitur(x)
        x["mom3"] = (x["close"] / x["close"].shift(3) - 1) * 100
    ut.tambah_peringkat_mom(siap)
    bm = ut.benchmark(siap, MULAI, AKHIR)
    kalender = dt.baca("pasar")["ihsg"].dropna().index
    p4, p5, p10, p20 = (us.pembanding(siap, h) for h in (4, 5, 10, 20))
    h4 = lambda x: (x["kontraksi"].shift(1) < 0.8) & (x["close"] > x["high20"]) & (x["vol_rasio"] >= 2)
    print("H2-H6 ...", flush=True)
    hasil["H2"] = nilai_trade("H2", dividen_event(siap), p4, bm, 5)
    hasil["H3"] = nilai_trade("H3", us.sinyal_tahan(siap, lambda x: (x["ema20"] > x["ema50"]) & (x["close"] > x["ema50"]) & (x["mom3"] <= -5), 10), p10, bm, 5)
    hasil["H4"] = nilai_trade("H4", us.sinyal_tahan(siap, h4, 10), p10, bm, 5)
    hasil["H5"] = nilai_trade("H5", us.sinyal_tanggal(siap, us.pasangan_bulan(kalender)), p4, bm, 5)
    with contextlib.redirect_stdout(io.StringIO()):
        lb = us.pasangan_lebaran(kalender)
    hasil["H6"] = nilai_trade("H6", us.sinyal_tanggal(siap, lb), p5, bm, 5)
    print("H11-H12 ...", flush=True)
    atr = lambda x: x["atr"] / x["close"] * 100 <= 3.5
    tr_a = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    tr_b = ut.kumpulkan(siap, lambda x: (x["pct_mom"] > 0.9) & (x["close"] > x["ema200"]))
    acuan = nilai_trade("H11a", tr_a, p20, bm)
    hasil["H11b"] = nilai_trade("H11b", tr_b, p20, bm)
    ha, hb = hari_dipegang(potong(tr_a)), hari_dipegang(potong(tr_b))
    sama = len(ha & hb)
    hasil["H11b"]["catatan"] = (f"{sama / len(ha) * 100:.0f}% hari-saham Follow Tren juga dipegang H11b ({sama / len(hb) * 100:.0f}% dari H11b); "
                                f"pemenang terbesar sama. Follow Tren di mesin yang sama: bersih/trade {pct(acuan['angka']['net'])}, tanpa 10 terbaik {pct(acuan['angka']['tanpa10'])}. "
                                f"CAGR di sini dari laporan bulanan satu undian, jadi bisa bergeser beberapa poin. Gagal di dev 2010-2019.")
    hasil["H12a"] = nilai_trade("H12a", ut.kumpulkan(siap, lambda x: (x["close"] >= x["maks250"]) & atr(x)), p20, bm)
    hasil["H12b"] = nilai_trade("H12b", ut.kumpulkan(siap, lambda x: (x["close"] >= x["maks250"]) & atr(x) & (x["close_mentah"] >= 200)), p20, bm)
    print("H19 ...", flush=True)
    for nama in ["H19a", "H19b", "H19c", "H19d", "H19e", "H19f", "H19g"]:
        semua, p = [], None
        for t, x in siap.items():
            s, keluar, n_maks, p = h19.sinyal(nama, x)
            s = (s & x["lolos"]).fillna(False).to_numpy(bool)
            semua += h19.simulasi_bsjp(x, t, s) if nama == "H19g" else h19.simulasi(x, t, s, keluar, n_maks)
        dasar = h19.pembanding_bsjp(siap) if nama == "H19g" else us.pembanding(siap, p)
        hasil[nama] = nilai_trade(nama, pd.DataFrame(semua), dasar, bm)
    print("H7-H10 (data IDX) ...", flush=True)
    with contextlib.redirect_stdout(io.StringIO()):
        s2, ihsg = t2.siapkan()
        ua.tempel_asing(s2, ua.baca_idx())
        t2.tambah_imbalance(s2)
        t2.tambah_lapkeu(s2, ihsg)
    q5, q10 = us.pembanding(s2, 5), us.pembanding(s2, 10)
    hasil["H7a"] = nilai_trade("H7a", us.sinyal_tahan(s2, lambda x: x["pct_asing"] > 0.9, 10), q10, bm, 5)
    hasil["H7b"] = nilai_trade("H7b", us.sinyal_tahan(s2, lambda x: h4(x) & (x["akum5"] > 0), 10), q10, bm, 5)
    hasil["H8"] = nilai_trade("H8", us.sinyal_tahan(s2, lambda x: x["sinyal_lapkeu"], 10), q10, bm, 5)
    hasil["H9"] = nilai_trade("H9", us.sinyal_tahan(s2, lambda x: (x["idx_NonRegularValue"] >= 0.5 * x["idx_Value"].rolling(20).mean())
                                                    & (x["idx_NonRegularValue"] / x["idx_NonRegularVolume"] >= x["idx_Close"] * 1.02), 10), q10, bm, 5)
    hasil["H10"] = nilai_trade("H10", us.sinyal_tahan(s2, lambda x: x["pct_imbalance"] > 0.9, 5), q5, bm, 5)
    print("H0-H1 (screener, universe 217) ...", flush=True)
    tp_asli, sl_asli = sc.TP, sc.SL
    try:
        for kode, tp, sl in [("H0", 3.0, 3.0), ("H1", 8.0, 4.0)]:
            sc.TP, sc.SL = tp, sl
            with contextlib.redirect_stdout(io.StringIO()):
                p = sc.walk_forward(sc.bangun_panel())
            p = p[p["tgl"] >= MULAI].dropna(subset=["skor", "menang"]).copy()
            p["desil"] = np.ceil(p.groupby("tgl")["skor"].rank(pct=True) * 10).clip(1, 10).astype(int)
            tr = sc.simulasi(p[p["desil"] == 10])
            hasil[kode] = nilai_trade(kode, tr, p, bm, 5)
            hasil[kode]["catatan"] = f"Peluang TP duluan: semua {p['menang'].mean() * 100:.1f}%, desil teratas {tr['menang'].mean() * 100:.1f}%. Universe 217 saham (daftar hari ini)."
    finally:
        sc.TP, sc.SL = tp_asli, sl_asli
    return hasil, bm, acuan


def h20():
    from backend.research import uji_h20 as m
    dev, hold = m.DEV, m.HOLDOUT
    m.DEV, m.HOLDOUT = ("2001-04-30", "2019-12-31"), ("2020-01-01", "2026-10-23")
    try:
        lulus, teks = tangkap(m.jalankan, "holdout")
    finally:
        m.DEV, m.HOLDOUT = dev, hold
    baris = re.search(r"^dasar\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%", teks, re.M)
    ch, dh, cb, db = (float(x) for x in baris.groups())
    lulus_n = len(re.findall(r"\[LULUS\]", teks))
    total = len(re.findall(r"\[(LULUS|GAGAL)\]", teks))
    return {"kode": "H20", "jenis": "portofolio", "lulus": f"{lulus_n}/{total}", "lulus_semua": bool(lulus), "gagal_di": [],
            "angka": {"cagr": ch, "dd": dh, "cagr_bh": cb, "dd_bh": db},
            "metrik": [["CAGR", pct(ch, d=1)], ["DD", pct(dh, d=1)], ["JII beli-tahan", pct(cb, d=1)], ["DD JII", pct(db, d=1)]],
            "catatan": f"Lulus kriteria relatif, tapi secara absolut rugi {pct(ch, d=1)}/th karena JII sendiri {pct(cb, d=1)}/th; kalah jauh dari RD pasar uang (±4%/th)."}


def h17():
    from backend.ingest import des_ojk
    from backend.research import screener as sc
    from backend.research import uji_h17 as m
    des = des_ojk.baca()
    daftar217 = sc.daftar_syariah()
    with contextlib.redirect_stdout(io.StringIO()):
        data = m.muat_harga(sorted(set(des["kode"]) | set(daftar217)))
    df = m.simulasi(data, des, daftar217, 2020, 2026)
    lulus, teks = tangkap(m.nilai_h17a, df, "H17a 2020-2026", True)
    n, t = skor_cetak(teks)
    cagr, cagr_b = m.ringkas(df), m.ringkas(df, "pembanding_total")
    penuh = df[~df["parsial"]]
    top = pd.Series([s for x in df["saham"] for s in str(x).split()]).value_counts().head(4)
    return {"kode": "H17a", "jenis": "portofolio", "lulus": f"{n}/{t}", "lulus_semua": bool(lulus), "gagal_di": [],
            "angka": {"cagr": float(cagr), "cagr_pembanding": float(cagr_b), "yield": float(penuh["penghasilan"].mean()), "terburuk": float(df["total"].min())},
            "metrik": [["CAGR", pct(cagr, d=1)], ["Pembanding", pct(cagr_b, d=1)], ["Yield penghasilan", pct(penuh["penghasilan"].mean(), False, 1)],
                       ["Tahun terburuk", pct(df["total"].min(), d=1)]],
            "catatan": f"Paling sering dipegang: {', '.join(f'{k} ({v}x)' for k, v in top.items())}. Didorong boom batu bara 2021-2025; di dev 2015 rugi -39% dengan saham serupa."}


def h15():
    from backend.ingest import des_ojk
    from backend.research import uji_h13 as h13
    from backend.research import uji_h15 as m
    des = des_ojk.baca()
    ks = m.baca_ksei()
    with contextlib.redirect_stdout(io.StringIO()):
        siap = h13.siapkan(sorted(set(des["kode"])))
    h = m.simulasi_a(siap, ks, "2020-01-01", "2026-12-31", des=des)
    lulus, teks = tangkap(m.nilai_a, h, "2020-2026", True)
    n, t = skor_cetak(teks)
    return {"kode": "H15a", "jenis": "portofolio", "lulus": f"{n}/{t}", "lulus_semua": bool(lulus), "gagal_di": [],
            "angka": {"selisih_bulan": float(h["selisih"].mean())},
            "metrik": [["Selisih vs pasar", pct(h["selisih"].mean()) + "/bln"], ["Desil atas bersih", pct(h["atas_bersih"].mean()) + "/bln"], ["Bulan", str(len(h))]]}


def h16():
    from backend.db import koneksi as d
    from backend.ingest import des_ojk
    from backend.research import uji_h13 as h13
    from backend.research import uji_h16 as m
    des = des_ojk.baca()
    kode = sorted(set(des["kode"]) & set(d.koneksi().fundamental.distinct("kode")))
    periode = ("2021-04", "2026-09")
    akhir_bulan = list(pd.date_range(m.MULAI_PANEL, pd.Period(periode[1], "M").to_timestamp(how="end").normalize(), freq="ME"))
    with contextlib.redirect_stdout(io.StringIO()):
        siap = h13.siapkan(kode)
        panel = m.bangun_panel(kode, akhir_bulan, des)
    h = m.simulasi(siap, panel, des, *periode)
    hasil = {}
    for kode_h, g, banding in [("H16a", "undervalue", None), ("H16b", "layak", None), ("H16c", "berkualitas", "undervalue")]:
        lulus, teks = tangkap(m.nilai, h, g, "2021-04..2026-09", True, banding)
        n, t = skor_cetak(teks)
        sel = (h[f"{g}_bersih"] - h["pembanding"]).where(h[f"n_{g}"] > 0, -h["pembanding"])
        hasil[kode_h] = {"kode": kode_h, "jenis": "portofolio", "lulus": f"{n}/{t}", "lulus_semua": bool(lulus), "gagal_di": [],
                         "angka": {"selisih_bulan": float(sel.mean()), "isi": float(h[f"n_{g}"].mean())},
                         "metrik": [["Selisih vs pasar", pct(sel.mean()) + "/bln"], ["Isi rata-rata", f"{h[f'n_{g}'].mean():.1f} saham".replace(".", ",")],
                                    ["Periode", "Apr 2021 – Sep 2026"]],
                         "catatan": "Data fundamental baru ada sejak 2019, jadi periode mulai Apr 2021."}
    return hasil


def h2122():
    from backend.research import uji_h21_h22 as m
    hasil_m, _ = tangkap(m.jalankan, "holdout")
    hasil = {}
    for jenis, kode in (("h21", "H21"), ("h22", "H22")):
        x = hasil_m[jenis]
        dasar = sum(1 for k in x["kriteria"] if k[2])
        sens = sum(1 for v in x["sensitivitas"].values() if v.get("lulus"))
        s, b, j = x["strategi"], x["bobot_sama"], x["jii"]
        hasil[kode] = {"kode": kode, "jenis": "portofolio", "lulus": f"{dasar}/{len(x['kriteria'])} + sensitivitas {sens}/{len(x['sensitivitas'])}",
                       "lulus_semua": bool(x["lulus"]), "gagal_di": [k[0] for k in x["kriteria"] if not k[2]],
                       "angka": {"cagr": float(s["cagr"]), "dd": float(s["dd"]), "cagr_bobot_sama": float(b["cagr"]), "cagr_jii": float(j["cagr"])},
                       "metrik": [["CAGR", pct(float(s["cagr"]), d=1)], ["DD", pct(float(s["dd"]), d=1)], ["Bobot sama", pct(float(b["cagr"]), d=1)],
                                  ["JII", pct(float(j["cagr"]), d=1)]]}
    return hasil


def bersih_json(o):
    if isinstance(o, dict):
        return {str(k): bersih_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [bersih_json(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def utama():
    LOG.clear()
    with tanpa_simpan():
        hasil, bm, acuan = per_trade()
        print("H20 ...", flush=True)
        hasil["H20"] = h20()
        print("H17a ...", flush=True)
        hasil["H17a"] = h17()
        print("H15a ...", flush=True)
        hasil["H15a"] = h15()
        print("H16 ...", flush=True)
        hasil.update(h16())
        print("H21/H22 ...", flush=True)
        hasil.update(h2122())
    jii = dt.baca("indeks/JKII")["close"]
    jii = jii[(jii.index >= "2019-12-31") & (jii.index <= "2026-10-23")]
    th = (jii.index[-1] - jii.index[0]).days / 365.25
    ringkas = {
        "dibuat": datetime.now().isoformat(timespec="minutes"), "judul": "Eksplorasi 2020+ (Okt 2026) — bukan bukti",
        "periode": f"{MULAI.date()} s/d data terakhir", "universe": "Saham syariah menurut DES OJK pada tanggalnya; biaya sama (±1,2% pulang-pergi)",
        "beli_tahan": round(float(bm), 2), "jii_cagr": round(float((jii.iloc[-1] / jii.iloc[0]) ** (1 / th) - 1) * 100, 2),
        "acuan_follow_tren": acuan["angka"], "catatan": CATATAN_UMUM,
        "lulus": sorted(k for k, v in hasil.items() if v.get("lulus_semua")), "hasil": hasil,
    }
    dt.simpan_hasil(NAMA_RINGKAS, bersih_json(ringkas))
    dt.simpan_hasil(NAMA_LOG, "\n".join(LOG))
    print(f"\nSELESAI. {len(hasil)} hipotesis dieksplorasi ulang di 2020+. Lulus semua kriteria (bukan bukti): {', '.join(ringkas['lulus']) or '-'}")
    for k in sorted(hasil, key=lambda x: (len(x), x)):
        v = hasil[k]
        print(f"  {k:5s} {v['lulus']:>28s}  " + " | ".join(f"{a} {b}" for a, b in v["metrik"][:4]))
    print(f"disimpan: hasil_riset/{NAMA_RINGKAS}, hasil_riset/{NAMA_LOG}")


if __name__ == "__main__":
    utama()
