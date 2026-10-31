from functools import lru_cache

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk
from backend.paper.tren_harian import siapkan

MULT_ATR = 3.0
VERSI_GRAFIK = ["h11a_dev", "h11a_2020"]
PERIODE_RET = [("1 bulan", 21), ("3 bulan", 63), ("6 bulan", 126), ("1 tahun", 250), ("3 tahun", 750)]


def angka(v, n=2):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, n) if np.isfinite(v) else None


def tgl(v):
    return None if v is None or pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d")


def daftar():
    db = d.koneksi()
    kode = sorted(set(dt.daftar("harga")) | {k for k in dt.daftar("harian") if not k.startswith("_")})
    des = des_ojk.baca()
    akhir = des["akhir"].max()
    sekarang = set(des.loc[des["akhir"] >= akhir, "kode"])
    info = {r["ticker"][:-3]: r for r in db.info_saham.find({}, {"_id": 0, "ticker": 1, "sector": 1})}
    nama = {r["kode"]: r.get("nama") for r in db.profil_yahoo.find({}, {"_id": 0, "kode": 1, "nama": 1})}
    nama.update({r["kode"]: r.get("nama") for r in db.profil_idx.find({}, {"_id": 0, "kode": 1, "nama": 1}) if r.get("nama")})
    return [{"kode": k, "syariah": k in sekarang, "sektor": (info.get(k) or {}).get("sector"), "nama": nama.get(k)} for k in kode]


def baca_mentah(kode):
    bagian = [x for x in (dt.baca(f"harga/{kode}"), dt.baca(f"harian/{kode}")) if x is not None]
    if not bagian:
        return None
    df = pd.concat(bagian)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["open", "high", "low", "close"])


def baca_ihsg():
    ihsg = dt.baca("pasar")["ihsg"].dropna()
    h = dt.baca("harian/_ihsg")
    if h is not None:
        ihsg = pd.concat([ihsg, h["ihsg"].dropna()])
        ihsg = ihsg[~ihsg.index.duplicated(keep="last")].sort_index()
    return ihsg


def jalur_stop(x, mulai, akhir, harga_beli, atr_sinyal):
    if mulai not in x.index:
        return {}
    stop = harga_beli - MULT_ATR * atr_sinyal
    tertinggi = np.nan
    hasil = {}
    for t, b in x.loc[mulai:akhir].iterrows():
        hasil[t] = stop
        c = float(b["m_close"])
        if c < stop:
            break
        tertinggi = c if np.isnan(tertinggi) else max(tertinggi, c)
        if np.isfinite(b["atr_mentah"]):
            stop = max(stop, tertinggi - MULT_ATR * float(b["atr_mentah"]))
    return hasil


def ringkas_trade(tr):
    net = np.array([t["net"] for t in tr if t.get("net") is not None], dtype=float)
    if not len(net):
        return {"jumlah": 0}
    return {"jumlah": int(len(net)), "win_rate": angka((net > 0).mean() * 100, 1), "rata": angka(net.mean()),
            "terbaik": angka(net.max()), "terburuk": angka(net.min()), "total": angka((np.prod(1 + net / 100) - 1) * 100, 1)}


def fundamental(db, kode):
    baris = []
    for r in db.fundamental.find({"kode": kode, "ada_angka": True}, {"_id": 0}).sort([("tahun", 1), ("periode", 1)]):
        ek = r.get("ekuitas") or r.get("ekuitas_total")
        baris.append({
            "tahun": r["tahun"], "periode": r["periode"], "tgl_publikasi": tgl(r.get("tgl_publikasi")), "unit": r.get("unit") or "IDR",
            "pendapatan": angka(r.get("pendapatan"), 0), "laba": angka(r.get("laba"), 0),
            "tumbuh_pendapatan": angka((r["pendapatan"] / r["pendapatan_lalu"] - 1) * 100, 1) if r.get("pendapatan") and r.get("pendapatan_lalu") else None,
            "tumbuh_laba": angka((r["laba"] / abs(r["laba_lalu"]) - (1 if r["laba_lalu"] > 0 else -1)) * 100, 1) if r.get("laba") is not None and r.get("laba_lalu") else None,
            "ekuitas": angka(ek, 0), "aset": angka(r.get("aset"), 0), "liabilitas": angka(r.get("liabilitas"), 0),
            "der": angka(r["liabilitas"] / ek, 2) if r.get("liabilitas") is not None and ek else None,
            "arus_kas_operasi": angka(r.get("arus_kas_operasi"), 0), "eps": angka(r.get("eps")),
        })
    return baris


@lru_cache(maxsize=1)
def ksei_semua(mtime):
    df = dt.baca("ksei")
    p = lambda kol: df[kol].sum(axis=1) / df["saham"] * 100
    return pd.DataFrame({
        "kode": df["kode"], "tgl": df["tgl"], "ritel": p(["L_ID"]), "institusi": p(["L_IS", "L_PF", "L_IB", "L_MF"]),
        "korporasi": p(["L_CP"]), "asing": p(["F_total"]), "lainnya": p(["L_SC", "L_FD", "L_OT"]),
        "di_luar": 100 - p(["L_total", "F_total"]),
    }).sort_values(["kode", "tgl"])


def kepemilikan(kode):
    if not dt.ada("ksei"):
        return []
    k = ksei_semua(dt.versi("ksei"))
    k = k[k["kode"] == kode]
    kolom = ["ritel", "institusi", "korporasi", "asing", "lainnya", "di_luar"]
    return [{"tgl": tgl(r.tgl), **{c: angka(getattr(r, c), 2) for c in kolom}} for r in k.itertuples()]


def posisi_paper(db, kode, p):
    status = db.paper_status.find_one({"_id": "status"}, {"_id": 0}) or {}
    h = dt.baca(f"harian/{kode}", kolom=["close"])
    h = None if h is None else h["close"].dropna()
    if h is not None and status.get("tgl_terakhir"):
        h = h[h.index <= pd.Timestamp(status["tgl_terakhir"])]
    close = float(h.iloc[-1]) if h is not None and len(h) else None
    return {"sumber": "paper", "dipilih": True, "tgl_sinyal": tgl(p.get("tgl_sinyal")), "tgl_beli": tgl(p.get("tgl_masuk")),
            "harga_beli": angka(p.get("harga_masuk"), 0), "tgl_jual": None, "harga_jual": None,
            "tgl_akhir_data": tgl(h.index[-1]) if close else None, "harga_akhir": angka(close, 0),
            "hari": p.get("hari"), "net": angka((close / p["harga_masuk"] - 1) * 100) if close else None,
            "status": "terbuka", "status_paper": p.get("status"), "stop_awal_pct": None}


def profil(kode):
    kode = kode.upper().strip()
    db = d.koneksi()
    mentah = baca_mentah(kode)
    if mentah is None:
        return None
    ihsg = baca_ihsg()
    x = siapkan({kode: mentah}, ihsg).get(kode)

    trades = []
    for t in db.backtest_trade.find({"ticker": kode, "versi": {"$in": VERSI_GRAFIK + ["h11a_2020_konservatif"]}}, {"_id": 0}).sort("tgl_beli", 1):
        terbuka = t.get("status") == "terbuka"
        trades.append({"sumber": t["versi"], "dipilih": bool(t.get("dipilih", True)), "tgl_sinyal": tgl(t.get("tgl_sinyal")),
                       "tgl_beli": tgl(t.get("tgl_beli")), "harga_beli": angka(t.get("harga_beli"), 0),
                       "tgl_jual": None if terbuka else tgl(t.get("tgl_jual")), "harga_jual": None if terbuka else angka(t.get("harga_jual"), 0),
                       "tgl_akhir_data": tgl(t.get("tgl_jual")) if terbuka else None, "harga_akhir": angka(t.get("harga_jual"), 0) if terbuka else None,
                       "hari": t.get("hari"), "net": angka(t.get("net")), "status": t.get("status"),
                       "stop_awal_pct": angka(t.get("stop_awal_pct"), 1)})
    for t in db.paper_transaksi.find({"ticker": kode, "aksi": "jual"}, {"_id": 0}):
        trades.append({"sumber": "paper", "dipilih": True, "tgl_sinyal": tgl(t.get("tgl_sinyal")), "tgl_beli": tgl(t.get("tgl_masuk")),
                       "harga_beli": angka(t.get("harga_masuk"), 0), "tgl_jual": tgl(t.get("tgl")), "harga_jual": angka(t.get("harga_keluar"), 0),
                       "hari": t.get("hari"), "net": angka(t.get("net_pct")), "status": "selesai", "stop_awal_pct": None})
    paper_pos = db.paper_posisi.find_one({"ticker": kode}, {"_id": 0})
    if paper_pos and paper_pos.get("status") in ("aktif", "jual_besok") and paper_pos.get("harga_masuk"):
        trades.append(posisi_paper(db, kode, paper_pos))

    stop = {}
    if x is not None:
        for t in trades:
            if t["sumber"] not in VERSI_GRAFIK or not t["dipilih"] or not t["tgl_beli"]:
                continue
            ts = pd.Timestamp(t["tgl_sinyal"])
            atr = float(x.at[ts, "atr_mentah"]) if ts in x.index else np.nan
            if np.isfinite(atr):
                stop.update(jalur_stop(x, pd.Timestamp(t["tgl_beli"]), pd.Timestamp(t["tgl_jual"] or x.index[-1]), t["harga_beli"], atr))
        if paper_pos and paper_pos.get("tgl_masuk") and paper_pos.get("harga_masuk"):
            stop.update(jalur_stop(x, pd.Timestamp(paper_pos["tgl_masuk"]), x.index[-1], paper_pos["harga_masuk"], paper_pos["atr_sinyal"]))

    c = mentah["close"]
    maks_m = (x["maks250"] * x["m_close"] / x["close"]) if x is not None else pd.Series(np.nan, index=c.index)
    grafik = {
        "tgl": [t.strftime("%Y-%m-%d") for t in c.index],
        "open": [angka(v, 0) for v in mentah["open"]],
        "high": [angka(v, 0) for v in mentah["high"]],
        "low": [angka(v, 0) for v in mentah["low"]],
        "close": [angka(v, 0) for v in c],
        "volume": [angka(v, 0) for v in mentah["volume"]],
        "ihsg": [angka(v, 2) for v in ihsg.reindex(c.index).ffill()],
        "maks250": [angka(v, 0) for v in maks_m.reindex(c.index)],
        "stop": [angka(stop.get(t), 0) for t in c.index],
    }

    des = des_ojk.baca()
    riwayat = des[des["kode"] == kode].sort_values("mulai")
    periode_syariah = [{"mulai": tgl(r.mulai), "akhir": tgl(r.akhir), "kep": r.kep} for r in riwayat.itertuples()]
    akhir_des = des["akhir"].max()
    syariah_kini = bool(((riwayat["akhir"] >= akhir_des)).any())

    kini = None
    if x is not None and len(x):
        b = x.iloc[-1]
        cl = float(b["m_close"])
        mk = float(maks_m.iloc[-1]) if np.isfinite(maks_m.iloc[-1]) else None
        atr = float(b["atr_mentah"]) if np.isfinite(b["atr_mentah"]) else None
        kini = {
            "tgl": tgl(x.index[-1]), "close": angka(cl, 0), "maks250": angka(mk, 0),
            "jarak_maks": angka((cl / mk - 1) * 100, 1) if mk else None,
            "atr": angka(atr, 0), "atr_pct": angka(atr / cl * 100, 1) if atr else None,
            "stop_jika_beli": angka(cl - MULT_ATR * atr, 0) if atr else None,
            "stop_jika_beli_pct": angka(-MULT_ATR * atr / cl * 100, 1) if atr else None,
            "nilai_transaksi": angka(b.get("value_mentah"), 0), "likuid": bool(b.get("lolos")),
            "sinyal": bool(b.get("sinyal")) and syariah_kini,
        }

    ret = []
    ih = ihsg.reindex(c.index).ffill()
    for nama, n in PERIODE_RET:
        if len(c) > n:
            ret.append({"periode": nama, "saham": angka((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100, 1),
                        "ihsg": angka((ih.iloc[-1] / ih.iloc[-1 - n] - 1) * 100, 1)})

    info = db.info_saham.find_one({"ticker": f"{kode}.JK"}, {"_id": 0}) or {}
    lapkeu = [{"tahun": r["tahun"], "periode": r["periode"], "tgl": tgl(r.get("tgl_publikasi")), "jeda": r.get("jeda_hari")}
              for r in db.lapkeu.find({"kode": kode}, {"_id": 0}).sort("tgl_publikasi", -1).limit(8)]
    utama = [t for t in trades if t["sumber"] in ("h11a_dev", "h11a_2020") and t["dipilih"] and t["status"] == "selesai"]

    return {
        "kode": kode, "syariah_kini": syariah_kini, "periode_syariah": periode_syariah,
        "info": {k: info.get(k) for k in ["sector", "industry", "marketCap", "trailingPE", "priceToBook", "returnOnEquity", "debtToEquity", "dividendYield"]},
        "kini": kini, "return": ret, "grafik": grafik, "trade": trades, "ringkasan_trade": ringkas_trade(utama),
        "sinyal_tidak_dipilih": sum(1 for t in trades if t["sumber"] in VERSI_GRAFIK and not t["dipilih"]),
        "paper_posisi": {k: (tgl(v) if k.startswith("tgl") else v) for k, v in paper_pos.items()} if paper_pos else None,
        "fundamental": fundamental(db, kode), "lapkeu": lapkeu, "kepemilikan": kepemilikan(kode),
    }
