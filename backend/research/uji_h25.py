import argparse
import re
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.research import screener as sc

KATA = ["pojk", "peraturan", "remunerasi", "tantiem", "bonus", "mesop", "esop", "msop", "lti", "program", "repo", "repurchase",
        "tabungan saham", "menabung", "hibah", "waris", "kewajiban", "pemenuhan", "hmetd", "right", "konversi", "waran", "dividen",
        "tender", "penjatahan", "ipo", "penawaran umum", "jaminan", "gadai"]
POLA_RUTIN = re.compile("|".join(re.escape(k) for k in KATA))
MIN_NILAI = 1e9
MIN_HARGA = 50
BATAS_BELI = 100e6
TAHAN = 63
FEE_BELI, FEE_JUAL = 0.0015, 0.0025
SEED = 25
N_ACAK = 10_000
MIN_TRADE = 60
DEV = (datetime(2023, 7, 3), datetime(2025, 1, 1))
HOLDOUT_MULAI = datetime(2025, 1, 1)


def arah(jenis, awal):
    return (jenis or "").lower().startswith(awal)


def kejadian(pemegang_besar=False):
    buang = Counter()
    hasil = []
    q = {"$or": [{"orang_dalam": True}, {"orang_dalam": False, "$or": [{"persen_sebelum": {"$gte": 5}}, {"persen_sesudah": {"$gte": 5}}]}]} if pemegang_besar else {"orang_dalam": True}
    for x in dt.db().kepemilikan_lapor.find(q):
        tr = x.get("transaksi") or []
        beli = [t for t in tr if arah(t.get("jenis"), "pembelian") and (t.get("harga") or 0) > 0 and (t.get("jumlah") or 0) > 0]
        if not beli:
            buang["2_tanpa_pembelian"] += 1
            continue
        jual = [t for t in tr if arah(t.get("jenis"), "penjualan")]
        nilai = sum(t["jumlah"] * t["harga"] for t in beli) - sum((t.get("jumlah") or 0) * (t.get("harga") or 0) for t in jual)
        if any(POLA_RUTIN.search((t.get("tujuan") or "").lower()) for t in beli):
            buang["4_rutin"] += 1
            continue
        if all(arah(t.get("jenis"), "pembelian") or arah(t.get("jenis"), "penjualan") for t in tr) and x.get("saham_sebelum") is not None and x.get("saham_sesudah") is not None:
            b = sum(t.get("jumlah") or 0 for t in tr if arah(t.get("jenis"), "pembelian"))
            j = sum(t.get("jumlah") or 0 for t in jual)
            if abs(x["saham_sebelum"] + b - j - x["saham_sesudah"]) > max(1, 0.001 * max(x["saham_sesudah"], 1)):
                buang["5_saldo"] += 1
                continue
        hasil.append({"kode": x["kode"], "tgl": x["tgl"], "nilai": nilai, "jabatan": x.get("jabatan") or "Pemegang ≥5%", "nama": x.get("nama")})
    return sorted(hasil, key=lambda z: z["tgl"]), buang


def siapkan(kode_tambahan=()):
    des = des_ojk.baca()
    kode = set(des["kode"]) | set(kode_tambahan)
    data = sc.baca_harga(kode)
    kal = dt.baca("pasar")["ihsg"].dropna().index
    return des, data, kal


def tabel_harga(data, kal):
    o = pd.DataFrame({k: v["open"] for k, v in data.items()}).reindex(kal)
    c = pd.DataFrame({k: v["close"] for k, v in data.items()}).reindex(kal)
    om = pd.DataFrame({k: v["open"] * v["close_mentah"] / v["close"] for k, v in data.items()}).reindex(kal)
    cm = pd.DataFrame({k: v["close_mentah"] for k, v in data.items()}).reindex(kal)
    vol = pd.DataFrame({k: v["volume"] for k, v in data.items()}).reindex(kal)
    nilai = (cm * vol).rolling(20, min_periods=20).mean()
    nol = (vol == 0).astype(float).rolling(5, min_periods=5).sum()
    lolos = (nilai >= MIN_NILAI) & (cm >= MIN_HARGA) & (nol == 0)
    return {"o": o, "c": c, "om": om, "cm": cm, "lolos": lolos, "c_isi": c.ffill()}


class Pasar:
    def __init__(self, des, data, kal):
        self.des, self.kal = des, kal
        self.t = tabel_harga(data, kal)
        self._univ = {}

    def universe(self, i):
        if i not in self._univ:
            hari = self.kal[i]
            syariah = set(des_ojk.syariah_pada(self.des, hari))
            baris = self.t["lolos"].iloc[i]
            self._univ[i] = sorted(k for k in baris.index[baris.fillna(False).to_numpy()] if k in syariah)
        return self._univ[i]

    def kotor(self, kode, i_masuk, i_keluar):
        o = self.t["o"].iloc[i_masuk]
        c = self.t["c_isi"].iloc[i_keluar]
        k = list(kode) if not isinstance(kode, str) else kode
        return c[k] / o[k] - 1

    def bersih(self, kode, i_masuk, i_keluar, tick=1):
        om = self.t["om"].iloc[i_masuk][kode]
        cm = self.t["cm"].iloc[:i_keluar + 1][kode].dropna().iloc[-1]
        beli = self.t["o"].iloc[i_masuk][kode] * (1 + FEE_BELI + tick * float(sc.fraksi(om)) / om)
        jual = self.t["c_isi"].iloc[i_keluar][kode] * (1 - FEE_JUAL - tick * float(sc.fraksi(cm)) / cm)
        return jual / beli - 1


def trade(pasar, kej, mulai, akhir, tahan=TAHAN, batas=BATAS_BELI, tick=1, harus_selesai=True):
    kal = pasar.kal
    terbuka, hasil, buang = {}, [], Counter()
    for e in kej:
        if not (mulai <= e["tgl"] < akhir) or e["nilai"] < batas:
            continue
        hari = pd.Timestamp(e["tgl"].date())
        i_sinyal = kal.searchsorted(hari, side="right") - 1
        i_masuk = i_sinyal + 1
        i_keluar = i_masuk + tahan - 1
        if i_sinyal < 0 or i_keluar >= len(kal):
            buang["jendela_belum_selesai"] += 1
            continue
        if e["kode"] not in pasar.universe(i_sinyal):
            buang["6_universe"] += 1
            continue
        if e["kode"] in terbuka and i_masuk <= terbuka[e["kode"]]:
            buang["posisi_masih_terbuka"] += 1
            continue
        if pd.isna(pasar.t["o"].iloc[i_masuk].get(e["kode"])):
            buang["tanpa_open_masuk"] += 1
            continue
        terbuka[e["kode"]] = i_keluar
        univ = [k for k in pasar.universe(i_sinyal) if pd.notna(pasar.t["o"].iloc[i_masuk].get(k))]
        pemb = float(pasar.kotor(univ, i_masuk, i_keluar).mean())
        kotor = float(pasar.kotor(e["kode"], i_masuk, i_keluar))
        bersih = float(pasar.bersih(e["kode"], i_masuk, i_keluar, tick))
        hasil.append({"kode": e["kode"], "jabatan": e["jabatan"], "terbit": e["tgl"], "masuk": kal[i_masuk], "keluar": kal[i_keluar],
                      "i_sinyal": i_sinyal, "i_masuk": i_masuk, "i_keluar": i_keluar, "nilai": e["nilai"],
                      "kotor": kotor * 100, "bersih": bersih * 100, "pembanding": pemb * 100, "excess": (bersih - pemb) * 100})
    return pd.DataFrame(hasil), buang


def uji_acak(pasar, df):
    rng = np.random.default_rng(SEED)
    total = np.zeros(N_ACAK)
    for r in df.itertuples():
        univ = [k for k in pasar.universe(r.i_sinyal) if k != r.kode and pd.notna(pasar.t["o"].iloc[r.i_masuk].get(k))]
        g = pasar.kotor(univ, r.i_masuk, r.i_keluar).to_numpy() * 100
        total += rng.choice(g, size=N_ACAK)
    return total / len(df)


def bootstrap(df):
    rng = np.random.default_rng(SEED)
    bulan = df["masuk"].dt.to_period("M")
    grup = [g["excess"].to_numpy() for _, g in df.groupby(bulan)]
    rata = np.empty(N_ACAK)
    for i in range(N_ACAK):
        pilih = rng.integers(0, len(grup), len(grup))
        rata[i] = np.concatenate([grup[j] for j in pilih]).mean()
    return float(np.percentile(rata, 5))


def nilai_kriteria(pasar, df):
    if len(df) == 0:
        return {"n": 0}, {"k1": False}
    acak = uji_acak(pasar, df)
    tanpa10 = df.drop(df["excess"].nlargest(10).index)["excess"].mean() if len(df) > 10 else np.nan
    top5 = df.groupby("kode")["excess"].sum().nlargest(5).index
    tanpa5 = df[~df["kode"].isin(top5)]["excess"].mean()
    kw = df.groupby(df["masuk"].dt.to_period("Q"))["excess"].agg(["mean", "size"])
    kw = kw[kw["size"] >= 5]
    r = {"n": len(df), "emiten": df["kode"].nunique(), "bersih": df["bersih"].mean(), "kotor": df["kotor"].mean(),
         "pembanding": df["pembanding"].mean(), "excess": df["excess"].mean(), "median_excess": df["excess"].median(),
         "menang": float((df["excess"] > 0).mean() * 100), "p95_acak": float(np.percentile(acak, 95)), "median_acak": float(np.median(acak)),
         "p_acak": float((acak >= df["kotor"].mean()).mean()), "boot5": bootstrap(df), "tanpa10": float(tanpa10), "tanpa5": float(tanpa5),
         "kuartal_menang": int((kw["mean"] > 0).sum()), "kuartal_n": int(len(kw)), "top5": list(top5)}
    k = {"k1": r["n"] >= MIN_TRADE, "k2": r["bersih"] > 0, "k3": r["excess"] > 0, "k4": r["kotor"] > r["p95_acak"],
         "k5": r["boot5"] > 0, "k6": r["tanpa10"] > 0, "k7": r["tanpa5"] > 0,
         "k8": r["kuartal_n"] > 0 and r["kuartal_menang"] >= np.ceil(0.6 * r["kuartal_n"])}
    return r, k


def ringkas_saja(df):
    if len(df) == 0:
        return "0 trade"
    return f"{len(df)} trade, bersih {df['bersih'].mean():+.2f}%, pembanding {df['pembanding'].mean():+.2f}%, excess {df['excess'].mean():+.2f}%"


def hitung(periode, pasar, kej, kej_besar):
    mulai, akhir = DEV if periode == "dev" else (HOLDOUT_MULAI, datetime(2100, 1, 1))
    df, buang = trade(pasar, kej, mulai, akhir)
    r, k = nilai_kriteria(pasar, df)
    lap = {}
    for nama, kw in {"tahan_21": {"tahan": 21}, "tahan_126": {"tahan": 126}, "tanpa_batas_nilai": {"batas": 0},
                     "batas_500jt": {"batas": 500e6}, "biaya_2_tick": {"tick": 2}}.items():
        lap[nama] = ringkas_saja(trade(pasar, kej, mulai, akhir, **kw)[0])
    lap["termasuk_pemegang_5persen"] = ringkas_saja(trade(pasar, kej_besar, mulai, akhir)[0])
    for jab in ("Direksi", "Dewan Komisaris"):
        lap[jab] = ringkas_saja(df[df["jabatan"] == jab]) if len(df) else "0 trade"
    return df, buang, r, k, lap


TEKS_K = ["1. trade >= 60", "2. bersih > 0", "3. excess bersih > 0", "4. kotor > p95 acak", "5. bootstrap 5% > 0",
          "6. tanpa 10 terbaik > 0", "7. tanpa 5 emiten > 0", "8. kuartal menang >= 60%"]


def lapor(periode, df, buang, buang_awal, r, k, lap):
    print(f"\n=== H25 {periode.upper()} ===")
    print(f"dibuang (laporan): {dict(buang_awal)} | dibuang (kejadian): {dict(buang)}")
    if r["n"] == 0:
        print("tidak ada trade")
        return False
    print(f"{r['n']} trade, {r['emiten']} emiten, menang vs pembanding {r['menang']:.0f}%")
    nilai = [f"{r['n']}", f"{r['bersih']:+.2f}%", f"{r['excess']:+.2f}% (pembanding {r['pembanding']:+.2f}%, median excess {r['median_excess']:+.2f}%)",
             f"kotor {r['kotor']:+.2f}% vs p95 {r['p95_acak']:+.2f}% (median acak {r['median_acak']:+.2f}%, p {r['p_acak']:.3f})",
             f"{r['boot5']:+.2f}%", f"{r['tanpa10']:+.2f}%", f"{r['tanpa5']:+.2f}% (tanpa {', '.join(r['top5'])})",
             f"{r['kuartal_menang']}/{r['kuartal_n']}"]
    for i, (t, v) in enumerate(zip(TEKS_K, nilai)):
        print(f"  [{'LULUS' if k[f'k{i + 1}'] else 'GAGAL'}] {t}: {v}")
    print("\n(laporan)")
    for n_, v in lap.items():
        print(f"  {n_}: {v}")
    kw = df.groupby(df["masuk"].dt.to_period("Q")).agg(n=("excess", "size"), excess=("excess", "mean"), bersih=("bersih", "mean"))
    print("\nPer kuartal masuk:\n" + kw.round(2).to_string())
    lulus = all(k.values())
    print(f"\nHASIL AKHIR H25 {periode.upper()}: {'LULUS' if lulus else 'GAGAL'} ({sum(k.values())}/8)")
    return lulus


def simpan(periode, df, r, k, lap):
    t = df.drop(columns=["i_sinyal", "i_masuk", "i_keluar"]).copy()
    for c in ("terbit", "masuk", "keluar"):
        t[c] = pd.to_datetime(t[c]).dt.strftime("%Y-%m-%d")
    dt.simpan_hasil(f"h25_{periode}", t)
    dt.simpan_hasil(f"h25_{periode}_ringkas", {"ringkas": {a: (float(b) if isinstance(b, (np.floating, float)) else b) for a, b in r.items()},
                                                "kriteria": {a: bool(b) for a, b in k.items()}, "laporan": lap})


def jalankan(periode, pasar=None, kej=None, tulis=True):
    kej_dalam, buang_awal = kejadian() if kej is None else kej
    kej_besar, _ = kejadian(True) if kej is None else kej
    pasar = pasar or Pasar(*siapkan({e["kode"] for e in kej_besar}))
    df, buang, r, k, lap = hitung(periode, pasar, kej_dalam, kej_besar)
    lulus = lapor(periode, df, buang, buang_awal, r, k, lap)
    if tulis and len(df):
        simpan(periode, df, r, k, lap)
    return lulus


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev", "holdout"], default="dev")
    a = ap.parse_args()
    if a.periode == "holdout":
        penanda = d.penanda("holdout_dibuka_h25")
        if penanda.exists():
            raise SystemExit(f"holdout H25 sudah pernah dibuka ({penanda.read_text().strip()})")
        dev = dt.baca_hasil("h25_dev_ringkas")
        if not dev or not all(dev["kriteria"].values()):
            raise SystemExit("holdout H25 hanya boleh dibuka kalau dev lulus semua kriteria")
        penanda.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
