import os

import numpy as np
import pandas as pd

from backend.ingest import koreksi_harga as kh

AKTIF = os.environ.get("PAPER_SUMBER_IDX", "1") != "0"
COCOK_OPEN = 0.02


def satu(kode, y, g, aturan):
    y = y.sort_index().copy()
    y.index = pd.to_datetime(y.index)
    y, _ = kh.terapkan(y, kode, aturan)
    if g is None or g.empty:
        return y.assign(sumber="yahoo", sumber_open="yahoo")
    f = kh.faktor_idx(g)
    g = g[g.index >= y.index.min()]
    if g.empty:
        return y.assign(sumber="yahoo", sumber_open="yahoo")
    E = kh.kali_e(g.index, f)
    close = g["Close"].astype(float) * E
    ada_trans = g["Volume"] > 0
    yo = y["open"].reindex(g.index)
    yc = y["close"].reindex(g.index)
    yahoo_cocok = (yc > 0) & (np.abs(yc / close - 1) <= COCOK_OPEN)
    op_idx = (g["OpenPrice"] > 0) & ada_trans
    open_ = pd.Series(np.where(op_idx, g["OpenPrice"].astype(float) * E,
                               np.where(ada_trans & yahoo_cocok, yo, close)), index=g.index)
    sumber_open = pd.Series(np.where(op_idx, "idx", np.where(ada_trans & yahoo_cocok, "yahoo", np.where(ada_trans, "close_idx", "tanpa_transaksi"))), index=g.index)
    hi = pd.Series(np.where(g["High"] > 0, g["High"].astype(float) * E, np.nan), index=g.index)
    lo = pd.Series(np.where(g["Low"] > 0, g["Low"].astype(float) * E, np.nan), index=g.index)
    hi = pd.concat([hi, open_, close], axis=1).max(axis=1)
    lo = pd.concat([lo, open_, close], axis=1).min(axis=1)
    rasio = (y["adj_close"] / y["close"]).reindex(g.index.union(y.index)).ffill().bfill().reindex(g.index)
    d = pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "adj_close": close * rasio,
                      "volume": g["Volume"].astype(float) / E,
                      "dividends": y.get("dividends", pd.Series(0.0, index=y.index)).reindex(g.index).fillna(0.0),
                      "stock_splits": y.get("stock_splits", pd.Series(0.0, index=y.index)).reindex(g.index).fillna(0.0),
                      "sumber": "idx", "sumber_open": sumber_open}, index=g.index)
    sisa = y[~y.index.isin(g.index) & (y.index > g.index.max())]
    if len(sisa):
        d = pd.concat([d, sisa.assign(sumber="yahoo", sumber_open="yahoo")[d.columns]])
    return d.sort_index()


def susun(yahoo, resmi=None):
    resmi = kh.idx_resmi() if resmi is None else resmi
    aturan = kh.aturan()
    return {k: satu(k, df, resmi.get(k), aturan) for k, df in yahoo.items()}


def ringkas(data):
    s = pd.concat([df[["sumber", "sumber_open"]] for df in data.values() if "sumber" in df])
    return {"baris": len(s), "sumber": s["sumber"].value_counts().to_dict(), "sumber_open": s["sumber_open"].value_counts().to_dict()}


def catat(db, bagian, data, hari):
    for t in hari:
        t = pd.Timestamp(t)
        baris = [df.loc[t] for df in data.values() if "sumber" in df and t in df.index]
        if not baris:
            continue
        sumber = pd.Series([b["sumber"] for b in baris]).value_counts().to_dict()
        buka = pd.Series([b["sumber_open"] for b in baris]).value_counts().to_dict()
        yahoo = sorted(k for k, df in data.items() if "sumber" in df and t in df.index and df.at[t, "sumber"] == "yahoo")
        db["paper_sumber"].replace_one({"_id": f"{bagian}:{t.date()}"},
                                       {"_id": f"{bagian}:{t.date()}", "bagian": bagian, "tgl": t.to_pydatetime(), "sumber": sumber, "sumber_open": buka,
                                        "idx_lengkap": sumber.get("yahoo", 0) == 0, "saham_yahoo": yahoo[:50]}, upsert=True)
