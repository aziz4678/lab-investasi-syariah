import hashlib
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.api.emiten import baca_mentah
from backend.db import koneksi as d
from backend.paper.tren_harian import BOBOT, PAJAK_DIVIDEN, biaya_beli, hasil_jual

ID = "h11a_v1"
VERSI = "h11a_2020_konservatif"
HORIZON = 500
JALUR = 5000
BLOK = 20
SEED = 20261022
MAKS_TRADE = 80
PERSENTIL = [1, 5, 25, 50, 75, 95, 99]
ATURAN = [
    "Hari dihitung dalam hari bursa sejak paper trade dimulai; return dan drawdown dari ekuitas harian paper (harga pasar).",
    "WASPADA: return di bawah persentil 5 (mulai hari ke-21), atau drawdown terdalam di bawah persentil 5, atau rugi beruntun di atas persentil 95.",
    "GAGAL: return di bawah persentil 1 (mulai hari ke-63), atau drawdown terdalam di bawah persentil 1, atau rugi beruntun di atas persentil 99.",
    "Kalau GAGAL: paper trade H11a dinyatakan gagal, tidak lanjut ke uang asli. Aturan tidak boleh diubah lalu diteruskan; perubahan = hipotesis baru.",
    "Zona dihitung dari backtest 2020-2026 versi konservatif yang optimis. Lolos zona belum membuktikan edge; hanya berarti hasil masih wajar.",
]


def kurva_harian(tr, mulai=None, sampai=None):
    harga, dividen = {}, {}
    for t in tr["ticker"].unique():
        m = baca_mentah(t)
        harga[t] = m["close"] if m is not None else pd.Series(dtype=float)
        dividen[t] = m["dividends"].fillna(0) if m is not None and "dividends" in m else pd.Series(dtype=float)
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    awal = pd.Timestamp(mulai) if mulai is not None else tr["tgl_beli"].min()
    akhir = pd.Timestamp(sampai) if sampai is not None else max(tr["tgl_jual"].max(), tr["tgl_beli"].max())
    hari = ihsg.index[(ihsg.index >= awal) & (ihsg.index <= akhir)]
    beli = {k: v for k, v in tr.groupby("tgl_beli")}
    jual = {k: v for k, v in tr[tr["tgl_jual"].notna()].groupby("tgl_jual")}
    kas, posisi, nilai = 1.0, {}, []
    harga_terakhir = {}
    for tgl in hari:
        for t, s in harga.items():
            if tgl in s.index and np.isfinite(s.at[tgl]):
                harga_terakhir[t] = float(s.at[tgl])
        for i, l in posisi.items():
            dv = dividen[tr.at[i, "ticker"]]
            if tgl in dv.index and dv.at[tgl] > 0:
                kas += l * float(dv.at[tgl]) * (1 - PAJAK_DIVIDEN)
        if tgl in jual:
            for r in jual[tgl].itertuples():
                lembar = posisi.pop(r.Index, 0.0)
                kas += lembar * hasil_jual(r.harga_jual)
        ekuitas = kas + sum(l * harga_terakhir.get(tr.at[i, "ticker"], tr.at[i, "harga_beli"]) for i, l in posisi.items())
        if tgl in beli:
            for r in beli[tgl].itertuples():
                dana = min(BOBOT * ekuitas, kas)
                if dana <= 0:
                    continue
                lembar = dana / biaya_beli(r.harga_beli)
                kas -= dana
                posisi[r.Index] = lembar
        ekuitas = kas + sum(l * harga_terakhir.get(tr.at[i, "ticker"], tr.at[i, "harga_beli"]) for i, l in posisi.items())
        nilai.append(ekuitas)
    return pd.Series(nilai, index=hari)


def bootstrap_kurva(r, rng):
    n = len(r)
    blok = int(np.ceil(HORIZON / BLOK))
    awal = rng.integers(0, n, size=(JALUR, blok))
    idx = (awal[:, :, None] + np.arange(BLOK)[None, None, :]) % n
    jalur = r[idx.reshape(JALUR, -1)[:, :HORIZON]]
    ek = np.cumprod(1 + jalur, axis=1)
    puncak = np.maximum.accumulate(np.maximum(ek, 1.0), axis=1)
    dd = np.minimum.accumulate(ek / puncak - 1, axis=1)
    return (ek - 1) * 100, dd * 100


def rugi_beruntun(net, rng):
    contoh = rng.choice(net <= 0, size=(JALUR, MAKS_TRADE), replace=True)
    terpanjang = np.zeros((JALUR, MAKS_TRADE), dtype=int)
    jalan = np.zeros(JALUR, dtype=int)
    terbesar = np.zeros(JALUR, dtype=int)
    for k in range(MAKS_TRADE):
        jalan = np.where(contoh[:, k], jalan + 1, 0)
        terbesar = np.maximum(terbesar, jalan)
        terpanjang[:, k] = terbesar
    return terpanjang


def utama():
    db = d.koneksi()
    ada = db.batas_paper.find_one({"_id": ID}, {"dibuat": 1, "sumber": 1})
    if ada:
        print(f"Zona {ID} sudah dikunci sejak {ada['dibuat']}. Tidak dihitung ulang (pra-registrasi).")
        return
    tr = pd.DataFrame(list(db.backtest_trade.find({"versi": VERSI, "dipilih": True}, {"_id": 0})))
    tr["tgl_beli"] = pd.to_datetime(tr["tgl_beli"])
    tr["tgl_jual"] = pd.to_datetime(tr["tgl_jual"])
    tr = tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    ek = kurva_harian(tr)
    bulanan = db.backtest_ekuitas.find_one({"versi": VERSI}, sort=[("bulan", -1)])
    tahun = (ek.index[-1] - ek.index[0]).days / 365.25
    dd_hist = (ek / ek.cummax() - 1).min() * 100
    print(f"kurva harian {ek.index[0].date()} s/d {ek.index[-1].date()}: akhir {ek.iloc[-1]:.2f}x, CAGR {(ek.iloc[-1] ** (1 / tahun) - 1) * 100:.1f}%, "
          f"drawdown terdalam {dd_hist:.1f}% (versi bulanan: {bulanan['ekuitas']:.2f}x)")
    r = ek.pct_change().dropna().to_numpy()
    rng = np.random.default_rng(SEED)
    ret, dd = bootstrap_kurva(r, rng)
    net = tr.loc[tr["status"] == "selesai"].sort_values("tgl_jual")["net"].to_numpy(float)
    beruntun = rugi_beruntun(net, rng)
    dok = {
        "_id": ID, "dibuat": datetime.now(), "sumber": VERSI, "jalur": JALUR, "blok": BLOK, "seed": SEED, "horizon": HORIZON,
        "hash_trade": hashlib.sha1(tr[["ticker", "tgl_beli", "net"]].to_csv().encode()).hexdigest(),
        "kurva": {"akhir": round(float(ek.iloc[-1]), 4), "dd": round(float(dd_hist), 2), "hari": len(ek)},
        "return": {f"p{p}": np.round(np.percentile(ret, p, axis=0), 2).tolist() for p in PERSENTIL},
        "dd": {f"p{p}": np.round(np.percentile(dd, p, axis=0), 2).tolist() for p in [1, 5, 50]},
        "beruntun": {f"p{p}": np.percentile(beruntun, p, axis=0).round().astype(int).tolist() for p in [50, 95, 99]},
        "trade": len(net), "win_rate": round(float((net > 0).mean() * 100), 1),
        "aturan": ATURAN,
    }
    db.batas_paper.insert_one(dok)
    for h in [21, 63, 126, 250, 500]:
        i = h - 1
        print(f"hari ke-{h:3d}: return p1 {dok['return']['p1'][i]:7.1f}%  p5 {dok['return']['p5'][i]:7.1f}%  p50 {dok['return']['p50'][i]:7.1f}%  "
              f"p95 {dok['return']['p95'][i]:7.1f}%  |  drawdown p5 {dok['dd']['p5'][i]:6.1f}%  p1 {dok['dd']['p1'][i]:6.1f}%")
    for k in [10, 20, 40, 80]:
        print(f"{k} trade: rugi beruntun terpanjang p95 {dok['beruntun']['p95'][k - 1]}, p99 {dok['beruntun']['p99'][k - 1]}")
    print(f"\nZona {ID} dikunci di Mongo koleksi batas_paper ({len(net)} trade, win rate {dok['win_rate']}%).")


if __name__ == "__main__":
    utama()
