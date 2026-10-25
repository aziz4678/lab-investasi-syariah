import argparse

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.ingest import fundamental as fd
from backend.research import uji_h13 as h13
from backend.research import uji_tren as ut

MULAI = pd.Timestamp("2020-01-01")
UMUR_MAKS = 200


def sinyal_set():
    non = [k.strip()[:-3] for k in dt.baca_daftar("nonsyariah_kode")]
    hasil = {}
    for nama, siap in [("A non-syariah", h13.siapkan(non)), ("syariah DES", ut.siapkan_holdout())]:
        tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
        hasil[nama] = tr[tr["tgl"] >= MULAI].reset_index(drop=True)
    return hasil


def tandai(tr, df):
    umur, a, b = [], [], []
    for r in tr.itertuples():
        lap = fd.laporan_pada(df, r.ticker, r.tgl)
        umur.append((r.tgl - lap["tgl_publikasi"]).days if lap is not None else np.nan)
        la, lb = fd.lolos_h14(lap)
        a.append(la)
        b.append(lb)
    tr = tr.copy()
    tr["umur_laporan"], tr["h14a"], tr["h14b"] = umur, a, b
    return tr


def cek(tr, nama):
    t = tr.copy()
    t["tahun"] = t["tgl"].dt.year
    t["ada"] = t["umur_laporan"].notna()
    t["segar"] = t["umur_laporan"] <= UMUR_MAKS
    r = t.groupby("tahun").agg(sinyal=("ticker", "size"), ada_laporan=("ada", "mean"), laporan_segar=("segar", "mean"),
                               umur_median=("umur_laporan", "median"), lolos_h14a=("h14a", "mean"), lolos_h14b=("h14b", "mean"))
    for k in ["ada_laporan", "laporan_segar", "lolos_h14a", "lolos_h14b"]:
        r[k] = (r[k] * 100).round(0)
    print(f"\n### {nama}: liputan data (tanpa untung/rugi)")
    print(r.to_string())


def uji(tr, nama, regime):
    akhir = tr["tgl_exit"].max()
    baris = []
    for label, t in [("H11a", tr), ("H14a", tr[tr["h14a"]]), ("H14b", tr[tr["h14b"]])]:
        m = h13.metrik(h13.portofolio(t, False, False, False, regime), MULAI, akhir)
        baris.append({"set": nama, "konfig": label, "sinyal": len(t), "net/trade": round(t["net"].mean(), 2), **m})
    return pd.DataFrame(baris)


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["cek", "uji"])
    a = ap.parse_args()
    df = fd.baca()
    kurang, gagal = fd.lengkap(df)
    if a.mode == "uji" and (kurang or len(gagal) and gagal.sum() > 0.02 * len(df)):
        print(f"DITOLAK: data fundamental belum lengkap (tahun kurang {kurang}, gagal {int(gagal.sum()) if len(gagal) else 0}). "
              "Uji H14 hanya boleh dijalankan sekali dengan data lengkap. Pakai mode 'cek'.")
        return
    sets = {n: tandai(tr, df) for n, tr in sinyal_set().items()}
    if a.mode == "cek":
        for n, tr in sets.items():
            cek(tr, n)
        print(f"\ntahun laporan belum ada: {kurang}. 'laporan_segar' = umur laporan <= {UMUR_MAKS} hari di hari sinyal.")
        return
    regime = h13.regime_ihsg()
    hasil = pd.concat([uji(tr, n, regime) for n, tr in sets.items()])
    print(hasil.to_string(index=False))
    dt.simpan_hasil(f"hasil_h14", hasil.reset_index(drop=True))
    print("\nkeputusan (net/trade DAN MAR lebih tinggi dari H11a di kedua set):")
    for k in ["H14a", "H14b"]:
        ok = all(
            hasil[(hasil.set == s) & (hasil.konfig == k)]["net/trade"].iloc[0] > hasil[(hasil.set == s) & (hasil.konfig == "H11a")]["net/trade"].iloc[0]
            and hasil[(hasil.set == s) & (hasil.konfig == k)]["MAR"].iloc[0] > hasil[(hasil.set == s) & (hasil.konfig == "H11a")]["MAR"].iloc[0]
            for s in sets)
        print(f"  {k}: {'DIADOPSI' if ok else 'tidak'}")


if __name__ == "__main__":
    utama()
