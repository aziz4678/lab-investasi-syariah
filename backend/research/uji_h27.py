import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import isi_backtest as ib
from backend.db import koneksi as d
from backend.research import screener as sc
from backend.research import uji_tren as ut
from backend.research.uji_dividen import bersih, evaluasi
from backend.research.uji_h19 import persentil_bulanan
from backend.research.uji_setup import pembanding

MULT_ATR = 3.0
N_MAKS = 20
PEMBANDING_HARI = 20
PENANDA = d.penanda("holdout_dibuka_h27")


def tambah_ma(x):
    c = x["close"]
    for n in (20, 50, 100, 200):
        x[f"ma{n}"] = c.rolling(n).mean()
    return x


def sinyal(x):
    c, h = x["close"], x["high"]
    tren = (x["ma50"] > x["ma100"]) & (x["ma100"] > x["ma200"]) & (c >= x["ma100"])
    koreksi = c.shift(1) <= x["ma20"].shift(1)
    pantul = (c > x["ma20"]) & (c > h.shift(1))
    return (tren & koreksi & pantul & x["lolos"]).fillna(False).to_numpy(bool)


def simulasi(x, t, s):
    o, c = x["open"].to_numpy(float), x["close"].to_numpy(float)
    atr = x["atr"].to_numpy(float)
    ma50 = x["ma50"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    n = len(x)
    hasil, bebas = [], 0
    for i in np.flatnonzero(s):
        if i < bebas or i + 1 >= n or not np.isfinite(atr[i]):
            continue
        e = o[i + 1]
        stop = e - MULT_ATR * atr[i]
        tertinggi = c[i + 1]
        j = i + 1
        while True:
            kena_stop = c[j] < stop
            kena_ma = j > i + 1 and c[j] < ma50[j]
            if kena_stop or kena_ma:
                sebab = "stop" if kena_stop else "ma50"
                if j + 1 <= n - 1:
                    k, px, alasan = j + 1, o[j + 1], "stop"
                else:
                    k, px, alasan = j, c[j], "akhir_data"
                break
            if j >= i + N_MAKS:
                k, px, alasan, sebab = j, c[j], "waktu", "waktu"
                break
            if j == n - 1:
                k, px, alasan, sebab = j, c[j], "terbuka", "terbuka"
                break
            tertinggi = max(tertinggi, c[j])
            if np.isfinite(atr[j]):
                stop = max(stop, tertinggi - MULT_ATR * atr[j])
            j += 1
        hasil.append({"ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k], "hari": k - i,
                      "stop_pct": MULT_ATR * atr[i] / e * 100, "kotor": (px / e - 1) * 100,
                      "net": bersih(e, px, e * rasio[i + 1], px * rasio[k]), "alasan": alasan, "sebab": sebab})
        bebas = k
    return hasil


def kumpulkan(siap, mulai, akhir):
    semua = []
    for t, x in siap.items():
        semua += simulasi(x, t, sinyal(x))
    tr = pd.DataFrame(semua)
    return tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].reset_index(drop=True)


def h11a(siap, mulai, akhir):
    a = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    return a[(a["tgl"] >= mulai) & (a["tgl"] <= akhir)].reset_index(drop=True)


def ret_contoh(tr, siap, mulai, akhir, mentah):
    pilih = set(ib.simulasi_portofolio(tr, ib.POSISI, ib.CONTOH_SEED).index)
    dok = ib.dokumen_trade("h27", tr, pilih, siap)
    ret, _ = ib.kurva_paper(dok, mulai, akhir, mentah)
    return ret


def tumpang_tindih(tr, a):
    buka = a.groupby("ticker")
    n = 0
    for r in tr.itertuples():
        if r.ticker in buka.groups:
            g = buka.get_group(r.ticker)
            n += bool(((g["tgl"] < r.tgl) & (g["tgl_exit"] > r.tgl)).any())
    return n / len(tr) * 100


def jalankan(siap, mulai, akhir, label, kumpul=None, hari_pemb=PEMBANDING_HARI, kode="H27"):
    tr = (kumpul or kumpulkan)(siap, mulai, akhir)
    a = h11a(siap, mulai, akhir)
    akhir_kurva = max(tr["tgl_exit"].max(), a["tgl_exit"].max())
    cagr_bm = ut.benchmark(siap, mulai, akhir)
    print(f"\n##### {kode} {label}: beli-tahan bobot sama {cagr_bm:.1f}%/th", flush=True)
    dasar = pembanding(siap, hari_pemb)
    dasar = dasar[(dasar["tgl"] >= mulai) & (dasar["tgl"] <= akhir)]
    menang, kalah = tr.loc[tr["net"] > 0, "net"], tr.loc[tr["net"] <= 0, "net"]
    pf = menang.sum() / -kalah.sum() if kalah.sum() < 0 else np.inf
    sebab = {k: round(v * 100, 1) for k, v in tr["sebab"].value_counts(normalize=True).items()}
    print(f"trade {len(tr)}, ticker {tr['ticker'].nunique()}, tahan {tr['hari'].mean():.1f} hari, keluar {sebab}, "
          f"winrate {len(menang) / len(tr) * 100:.0f}%, untung {menang.mean():.2f}% vs rugi {kalah.mean():.2f}%, PF {pf:.2f}", flush=True)
    ok16, _ = evaluasi(tr, dasar, f"{kode} {label}", maks=ib.POSISI, kembalikan_bulanan=True)

    mentah = {t: baca_mentah(t) for t in set(tr["ticker"]) | set(a["ticker"])}
    mc_h27 = ib.monte_carlo("h27", tr, siap, mulai, akhir_kurva, mentah)
    mc_a = ib.monte_carlo("h11a", a, siap, mulai, akhir_kurva, mentah)
    c27, d27 = mc_h27["cagr"]["median"], mc_h27["dd"]["median"]
    ca, da = mc_a["cagr"]["median"], mc_a["dd"]["median"]
    r27 = c27 / abs(d27) if d27 else np.nan
    ra = ca / abs(da) if da else np.nan
    p1 = persentil_bulanan(tr, 1)
    k7, k8, k9 = c27 > cagr_bm, p1 > 0, r27 > ra
    print(f"  [{'LULUS' if k7 else 'GAGAL'}] 7. median CAGR {c27}% (p5 {mc_h27['cagr']['p5']} p95 {mc_h27['cagr']['p95']}) vs beli-tahan {cagr_bm:.1f}%")
    print(f"  [{'LULUS' if k8 else 'GAGAL'}] 8. bootstrap bulanan persentil 1: {p1:.2f}%")
    print(f"  [{'LULUS' if k9 else 'GAGAL'}] 9. CAGR/|DD| {c27}/{abs(d27)} = {r27:.2f} vs H11a {ca}/{abs(da)} = {ra:.2f}")
    k1_6 = cek_1_6(tr, dasar)
    lulus = all(k1_6) and k7 and k8 and k9
    skor = sum(k1_6) + k7 + k8 + k9
    print(f"HASIL AKHIR {kode} {label}: {'LULUS' if lulus else 'GAGAL'} ({skor}/9)", flush=True)

    r27c, rac = ret_contoh(tr, siap, mulai, akhir_kurva, mentah), ret_contoh(a, siap, mulai, akhir_kurva, mentah)
    gab = pd.concat([r27c, rac], axis=1).dropna()
    korelasi = float(gab.iloc[:, 0].corr(gab.iloc[:, 1]))
    tumpang = tumpang_tindih(tr, a)
    print(f"laporan: korelasi bulanan dengan H11a (seed 7) {korelasi:.2f}, trade yang sahamnya sedang dipegang H11a {tumpang:.0f}%")
    th = tr.groupby(tr["tgl"].dt.year)["net"].agg(["size", "mean"]).round(2)
    print(th.to_string())

    return {
        "label": label, "cagr_bm": round(float(cagr_bm), 1), "lulus": bool(lulus), "skor": f"{skor}/9",
        "kriteria": [bool(v) for v in k1_6] + [bool(k7), bool(k8), bool(k9)],
        "trade": int(len(tr)), "ticker": int(tr["ticker"].nunique()), "winrate": round(float(len(menang) / len(tr) * 100), 1),
        "net": round(float(tr["net"].mean()), 2), "kotor": round(float(tr["kotor"].mean()), 2), "median_net": round(float(tr["net"].median()), 2),
        "pembanding": round(float(dasar["net"].mean()), 2), "untung": round(float(menang.mean()), 2), "rugi": round(float(kalah.mean()), 2),
        "pf": round(float(pf), 2), "hari": round(float(tr["hari"].mean()), 1), "sebab": sebab,
        "bootstrap_p1_bulanan": round(float(p1), 2), "monte_carlo": mc_h27, "h11a": mc_a,
        "rasio": round(float(r27), 2), "rasio_h11a": round(float(ra), 2), "korelasi_h11a": round(korelasi, 2), "tumpang_h11a": round(tumpang, 1),
        "per_tahun": [{"tahun": int(y), "trade": int(r["size"]), "net": float(r["mean"])} for y, r in th.iterrows()],
        "detail_1_6": detail_1_6(tr, dasar),
    }


def detail_1_6(tr, dasar):

    lo, _ = sc.bootstrap(tr)
    th = tr.groupby(tr["tgl"].dt.year)["net"].mean()
    lima = tr.groupby("ticker")["net"].sum().nlargest(5).index
    return {"exp": round(float(tr["net"].mean()), 2), "pembanding": round(float(dasar["net"].mean()), 2), "bootstrap_lo": round(float(lo), 2),
            "tahun_positif": round(float((th > 0).mean() * 100), 0), "tanpa10": round(float(tr.drop(tr["net"].nlargest(10).index)["net"].mean()), 2),
            "tanpa5_ticker": round(float(tr[~tr["ticker"].isin(lima)]["net"].mean()), 2), "lima": list(lima)}


def cek_1_6(tr, dasar):
    x = detail_1_6(tr, dasar)
    return [x["exp"] > 0, x["exp"] > x["pembanding"], x["bootstrap_lo"] > 0, x["tahun_positif"] >= 70, x["tanpa10"] > 0, x["tanpa5_ticker"] > 0]


def siapkan(periode):
    siap = ut.siapkan_dev() if periode == "dev" else ut.siapkan_holdout()
    return {t: tambah_ma(x) for t, x in siap.items()}


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    p = ap.parse_args().periode
    if p == "dev":
        hasil = jalankan(siapkan("dev"), pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31"), "dev 2010-2019")
        hasil["dibuat"] = datetime.now().isoformat()
        dt.simpan_hasil("h27_dev", hasil)
        return
    dev = dt.baca_hasil("h27_dev")
    if not dev or not dev.get("lulus"):
        raise SystemExit("holdout H27 hanya dibuka kalau dev lulus semua kriteria")
    if PENANDA.exists():
        raise SystemExit(f"holdout H27 sudah pernah dibuka ({PENANDA.read_text().strip()})")
    PENANDA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    siap = siapkan("holdout")
    akhir = max(x.index.max() for x in siap.values())
    hasil = jalankan(siap, pd.Timestamp("2020-01-01"), akhir, "holdout 2020+")
    hasil["dibuat"] = datetime.now().isoformat()
    dt.simpan_hasil("h27_holdout", hasil)


if __name__ == "__main__":
    utama()
