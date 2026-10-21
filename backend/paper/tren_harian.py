import argparse
import logging
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset.swing_target3 import rapikan_index

FILE_TRANSAKSI = "paper_transaksi"
FILE_EKUITAS = "paper_ekuitas"
MULT_ATR = 3.0
MAKS_HARI = 500
MAKS_POSISI = 10
BOBOT = 0.10
LOT = 100
PAJAK_DIVIDEN = 0.10
KOLOM_POSISI = ["ticker", "status", "tgl_sinyal", "tgl_masuk", "harga_masuk", "lot", "atr_sinyal", "stop", "tertinggi", "hari", "dividen_rp"]


def unduh(daftar):
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    hasil = {}
    for i in range(0, len(daftar), 60):
        potong = [t + ".JK" for t in daftar[i:i + 60]]
        mentah = yf.download(potong, period="2y", interval="1d", auto_adjust=False, actions=True,
                             group_by="ticker", threads=True, progress=False)
        for t in potong:
            try:
                df = mentah[t].dropna(subset=["Open", "High", "Low", "Close"]).copy()
            except KeyError:
                continue
            if df.empty:
                continue
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            df = rapikan_index(df)
            dt.tulis(f"harian/{t[:-3]}", df)
            hasil[t[:-3]] = df
        time.sleep(1)
    hilang = sorted(set(daftar) - set(hasil))
    if hilang:
        print(f"{len(hilang)} kode tidak ada di Yahoo (delisting / ganti kode / tidak tercatat), dilewati: {', '.join(hilang)}")
    ihsg = yf.download("^JKSE", period="2y", interval="1d", auto_adjust=True, progress=False)
    if isinstance(ihsg.columns, pd.MultiIndex):
        ihsg.columns = ihsg.columns.get_level_values(0)
    ihsg = rapikan_index(ihsg)["Close"].dropna()
    dt.tulis("harian/_ihsg", ihsg.to_frame("ihsg"))
    return hasil, ihsg


def baca_lokal():
    semua = dt.baca_banyak("harian")
    ihsg = semua.pop("_ihsg")["ihsg"]
    return dict(sorted(semua.items())), ihsg


def siapkan(mentah, ihsg):
    pasar = pd.DataFrame({"ihsg_mom20": (ihsg / ihsg.shift(20) - 1) * 100})
    siap = {}
    for t, df in mentah.items():
        df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
        if len(df) < 260:
            continue
        faktor = df["adj_close"] / df["close"]
        o, h, l, c = df["open"] * faktor, df["high"] * faktor, df["low"] * faktor, df["adj_close"]
        d = pd.DataFrame({
            "open": o, "high": pd.concat([o, h, l, c], axis=1).max(axis=1),
            "low": pd.concat([o, h, l, c], axis=1).min(axis=1), "close": c,
            "volume": df["volume"], "close_mentah": df["close"],
        }, index=df.index)
        x = sc.fitur_ticker(d, pasar.reindex(d.index.union(pasar.index)).ffill())
        x["maks250"] = x["close"].rolling(250).max().shift(1)
        x["sinyal"] = (x["close"] >= x["maks250"]) & x["lolos"]
        x["m_open"], x["m_high"], x["m_low"], x["m_close"] = df["open"], df["high"], df["low"], df["close"]
        x["atr_mentah"] = x["atr"] * df["close"] / c
        x["split"] = df.get("stock_splits", pd.Series(0, index=df.index)).fillna(0)
        x["dividen"] = df.get("dividends", pd.Series(0, index=df.index)).fillna(0)
        siap[t] = x
    return siap


def kalender_bursa(mentah):
    jumlah = pd.Series([t for df in mentah.values() for t in df.index]).value_counts()
    batas = max(10, 0.3 * len(mentah))
    return pd.DatetimeIndex(sorted(jumlah[jumlah >= batas].index))


def biaya_beli(harga):
    return harga * (1 + sc.fraksi(harga) / harga) * (1 + sc.FEE_BELI / 100)


def hasil_jual(harga):
    return harga * (1 - sc.fraksi(harga) / harga) * (1 - sc.FEE_JUAL / 100)


def ke_mongo(v):
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime(v.year, v.month, v.day)
    return kdb.ke_bson(v)


def muat_state(modal):
    db = kdb.koneksi()
    kdb.siapkan_indeks(db)
    status = db.paper_status.find_one({"_id": "status"}, {"_id": 0}) or {"modal_awal": modal, "kas": modal, "tgl_terakhir": None, "sesi": datetime.now().strftime("%Y%m%d-%H%M%S")}
    posisi = []
    for p in db.paper_posisi.find({}, {"_id": 0}):
        p = {k: p.get(k) for k in KOLOM_POSISI}
        for k in ["tgl_sinyal", "tgl_masuk"]:
            p[k] = pd.Timestamp(p[k]) if p[k] is not None else pd.NaT
        for k in ["harga_masuk", "atr_sinyal", "stop", "tertinggi", "dividen_rp"]:
            p[k] = np.nan if p[k] is None else float(p[k])
        posisi.append(p)
    return status, posisi


def simpan_state(status, posisi):
    db = kdb.koneksi()
    db.paper_status.replace_one({"_id": "status"}, {"_id": "status", **{k: ke_mongo(v) for k, v in status.items()}}, upsert=True)
    db.paper_posisi.delete_many({})
    if posisi:
        db.paper_posisi.insert_many([{k: ke_mongo(p.get(k)) for k in KOLOM_POSISI} for p in posisi])


KOLOM_TRANSAKSI = ["tgl", "aksi", "ticker", "tgl_sinyal", "tgl_masuk", "harga_masuk", "harga_keluar", "lot", "hari", "net_pct", "untung_rp"]
KOLOM_EKUITAS = ["tgl", "ekuitas", "kas", "posisi"]


def catat(file, baris):
    kolom = KOLOM_EKUITAS if file == FILE_EKUITAS else KOLOM_TRANSAKSI
    if set(baris) - set(kolom):
        raise ValueError(f"kolom tidak dikenal: {set(baris) - set(kolom)}")
    dok = {k: ke_mongo(baris.get(k)) for k in kolom}
    if file == FILE_EKUITAS:
        kdb.koneksi()[file].replace_one({"tgl": dok["tgl"]}, dok, upsert=True)
    else:
        kdb.koneksi()[file].insert_one(dok)


def bar(siap, t, tgl):
    x = siap.get(t)
    if x is None or tgl not in x.index:
        return None
    return x.loc[tgl]


def ekuitas(status, posisi, siap, tgl):
    nilai = status["kas"]
    for p in posisi:
        if p["status"] in ("aktif", "jual_besok"):
            b = bar(siap, p["ticker"], tgl)
            harga = b["m_close"] if b is not None else p["harga_masuk"]
            nilai += p["lot"] * LOT * harga
    return nilai


def proses_hari(tgl, siap, des, status, posisi, peringatan):
    sisa = []
    for p in posisi:
        b = bar(siap, p["ticker"], tgl)
        if b is None:
            sisa.append(p)
            continue
        if b["split"] and p["status"] != "beli_besok":
            peringatan.append(f"{p['ticker']} split {b['split']} pada {tgl.date()}: harga dan stop posisi perlu dicek manual")
        if p["status"] in ("aktif", "jual_besok") and b["dividen"] > 0:
            dv = float(b["dividen"]) * LOT * p["lot"] * (1 - PAJAK_DIVIDEN)
            status["kas"] += dv
            p["dividen_rp"] = (0 if pd.isna(p.get("dividen_rp")) else p["dividen_rp"]) + dv
            catat(FILE_TRANSAKSI, {"ticker": p["ticker"], "tgl_sinyal": p["tgl_sinyal"], "aksi": "dividen", "tgl": tgl.date(), "untung_rp": round(dv)})
        if p["status"] == "beli_besok":
            prev = siap[p["ticker"]]["m_close"].shift(1).get(tgl)
            if b["m_high"] == b["m_low"] and b["m_open"] > prev:
                catat(FILE_TRANSAKSI, {"ticker": p["ticker"], "tgl_sinyal": p["tgl_sinyal"], "aksi": "batal_ARA", "tgl": tgl.date()})
                continue
            modal_posisi = BOBOT * ekuitas(status, posisi, siap, tgl)
            per_lot = biaya_beli(b["m_open"]) * LOT
            lot = int(min(modal_posisi, status["kas"]) // per_lot)
            if lot < 1:
                catat(FILE_TRANSAKSI, {"ticker": p["ticker"], "tgl_sinyal": p["tgl_sinyal"], "aksi": "batal_kas", "tgl": tgl.date()})
                continue
            status["kas"] -= lot * per_lot
            p.update(status="aktif", tgl_masuk=tgl, harga_masuk=float(b["m_open"]), lot=lot,
                     stop=float(b["m_open"] - MULT_ATR * p["atr_sinyal"]), tertinggi=np.nan, hari=0, dividen_rp=0.0)
        elif p["status"] == "jual_besok":
            if b["m_high"] == b["m_low"]:
                sisa.append(p)
                continue
            uang = hasil_jual(b["m_open"]) * LOT * p["lot"]
            status["kas"] += uang
            uang += 0 if pd.isna(p.get("dividen_rp")) else p["dividen_rp"]
            modal = biaya_beli(p["harga_masuk"]) * LOT * p["lot"]
            catat(FILE_TRANSAKSI, {"ticker": p["ticker"], "tgl_sinyal": p["tgl_sinyal"], "aksi": "jual", "tgl_masuk": p["tgl_masuk"],
                                   "harga_masuk": p["harga_masuk"], "tgl": tgl.date(), "harga_keluar": float(b["m_open"]),
                                   "lot": p["lot"], "hari": p["hari"], "net_pct": round((uang / modal - 1) * 100, 2),
                                   "untung_rp": round(uang - modal)})
            continue
        if p["status"] == "aktif":
            p["hari"] += 1
            c = float(b["m_close"])
            if c < p["stop"]:
                p["status"] = "jual_besok"
            else:
                p["tertinggi"] = c if pd.isna(p["tertinggi"]) else max(p["tertinggi"], c)
                if np.isfinite(b["atr_mentah"]):
                    p["stop"] = max(p["stop"], p["tertinggi"] - MULT_ATR * float(b["atr_mentah"]))
                if p["hari"] > MAKS_HARI:
                    p["status"] = "jual_besok"
        sisa.append(p)
    posisi[:] = sisa

    syariah = des_ojk.syariah_pada(des, tgl)
    dipegang = {p["ticker"] for p in posisi}
    kandidat = sorted(t for t, x in siap.items() if t in syariah and t not in dipegang
                      and tgl in x.index and bool(x.at[tgl, "sinyal"]))
    slot = MAKS_POSISI - len(posisi)
    rng = np.random.default_rng(int(tgl.strftime("%Y%m%d")))
    terpilih = [str(x) for x in rng.permutation(kandidat)[:max(slot, 0)]] if kandidat else []
    for t in terpilih:
        posisi.append({"ticker": t, "status": "beli_besok", "tgl_sinyal": tgl, "tgl_masuk": pd.NaT, "harga_masuk": np.nan,
                       "lot": 0, "atr_sinyal": float(siap[t].at[tgl, "atr_mentah"]), "stop": np.nan, "tertinggi": np.nan, "hari": 0, "dividen_rp": 0.0})
    status["tgl_terakhir"] = str(tgl.date())
    kdb.koneksi().paper_sinyal.replace_one({"tgl": tgl.to_pydatetime()}, {"tgl": tgl.to_pydatetime(), "kandidat": kandidat, "terpilih": terpilih}, upsert=True)
    nilai = ekuitas(status, posisi, siap, tgl)
    catat(FILE_EKUITAS, {"tgl": tgl.date(), "ekuitas": round(nilai), "kas": round(status["kas"]),
                         "posisi": sum(p["status"] != "beli_besok" for p in posisi)})
    return kandidat, terpilih


def laporan(tgl, siap, kandidat, terpilih, status, posisi):
    print(f"\n================ {tgl.date()} ================")
    nilai = ekuitas(status, posisi, siap, tgl)
    print(f"ekuitas paper Rp{nilai:,.0f} ({(nilai / status['modal_awal'] - 1) * 100:+.1f}% dari modal awal) | kas Rp{status['kas']:,.0f}")

    beli = [p for p in posisi if p["status"] == "beli_besok"]
    jual = [p for p in posisi if p["status"] == "jual_besok"]
    print("\nAKSI BESOK (di harga open):")
    for p in jual:
        print(f"  JUAL {p['ticker']} ({p['lot']} lot) - close {siap[p['ticker']].at[tgl, 'm_close']:.0f} tembus stop {p['stop']:.0f}")
    for p in beli:
        c = siap[p["ticker"]].at[tgl, "m_close"]
        print(f"  BELI {p['ticker']} - close {c:.0f}, perkiraan stop awal {c - MULT_ATR * p['atr_sinyal']:.0f} "
              f"(-{MULT_ATR * p['atr_sinyal'] / c * 100:.1f}%)")
    if not beli and not jual:
        print("  tidak ada")

    aktif = [p for p in posisi if p["status"] == "aktif"]
    if aktif:
        print("\nPOSISI AKTIF:")
        baris = []
        for p in aktif:
            c = siap[p["ticker"]].at[tgl, "m_close"] if tgl in siap[p["ticker"]].index else np.nan
            baris.append({"ticker": p["ticker"], "masuk": pd.Timestamp(p["tgl_masuk"]).date(), "harga_masuk": p["harga_masuk"],
                          "close": c, "untung_%": round((c / p["harga_masuk"] - 1) * 100, 1), "stop": round(p["stop"]),
                          "jarak_stop_%": round((c / p["stop"] - 1) * 100, 1), "hari": p["hari"], "lot": p["lot"]})
        print(pd.DataFrame(baris).to_string(index=False))

    print(f"\nSINYAL HARI INI ({len(kandidat)} saham syariah tembus harga tertinggi 52 minggu): {', '.join(kandidat) if kandidat else '-'}")
    if kandidat and len(terpilih) < len(kandidat):
        print(f"  slot cuma {len(terpilih)}, dipilih acak sesuai aturan: {', '.join(terpilih) if terpilih else '-'}")

    tr = kdb.baca_df(FILE_TRANSAKSI)
    if not tr.empty:
        dv = tr.loc[tr["aksi"] == "dividen", "untung_rp"].sum()
        tr = tr[tr["aksi"] == "jual"]
        if len(tr):
            print(f"\nTRADE SELESAI: {len(tr)} | menang {(tr['net_pct'] > 0).mean() * 100:.0f}% | rata2 {tr['net_pct'].mean():.2f}% | "
                  f"total Rp{tr['untung_rp'].sum():,.0f} (termasuk dividen; dividen total diterima Rp{dv:,.0f})")


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modal", type=float, default=100_000_000)
    ap.add_argument("--mulai", help="mulai paper trade dari tanggal ini (hanya saat pertama kali)")
    ap.add_argument("--tanpa-unduh", action="store_true")
    ap.add_argument("--sampai", help="proses paling jauh sampai tanggal ini (dipakai cek ulang)")
    a = ap.parse_args()

    des = des_ojk.baca()
    hari_ini = pd.Timestamp.today().normalize()
    sekarang = des_ojk.syariah_pada(des, hari_ini)
    status, posisi = muat_state(a.modal)
    daftar = sorted(sekarang | {p["ticker"] for p in posisi})
    terbaru = des["mulai"].max()
    if (hari_ini - terbaru).days > 190:
        print(f"PERINGATAN: DES terakhir berlaku {terbaru.date()}. Periode baru (1 Jun / 1 Des) mungkin sudah terbit, perbarui des_ojk.py")

    if a.tanpa_unduh:
        mentah, ihsg = baca_lokal()
    else:
        print(f"unduh harga {len(daftar)} saham syariah (DES {terbaru.date()})...")
        mentah, ihsg = unduh(daftar)
    siap = siapkan(mentah, ihsg)
    kalender = kalender_bursa(mentah)
    akhir = kalender.max()
    if akhir >= hari_ini and pd.Timestamp.now().hour < 17:
        akhir = kalender[kalender < hari_ini].max()
        print(f"Bursa hari ini belum tutup / data belum final: diproses sampai {akhir.date()}. Perbarui lagi setelah jam 17:00 WIB.")
    elif akhir < hari_ini and pd.Timestamp.now().hour >= 17 and hari_ini.weekday() < 5:
        print(f"PERINGATAN: data terakhir {akhir.date()}, data hari ini belum ada di yfinance. Jalankan lagi nanti.")

    if a.sampai:
        akhir = min(akhir, pd.Timestamp(a.sampai))

    if status["tgl_terakhir"] is None:
        awal = pd.Timestamp(a.mulai) if a.mulai else akhir
    else:
        awal = pd.Timestamp(status["tgl_terakhir"]) + pd.Timedelta(days=1)
    hari = kalender[(kalender >= awal) & (kalender <= akhir)]
    peringatan = []
    kandidat, terpilih = [], []
    for tgl in hari:
        kandidat, terpilih = proses_hari(tgl, siap, des, status, posisi, peringatan)
    simpan_state(status, posisi)
    if status["tgl_terakhir"] is None:
        print("Belum ada hari bursa yang bisa diproses.")
        return
    if not len(hari):
        print(f"sudah diproses sampai {status['tgl_terakhir']}, tidak ada hari baru")
        tgl = pd.Timestamp(status["tgl_terakhir"])
        s = kdb.koneksi().paper_sinyal.find_one({"tgl": tgl.to_pydatetime()})
        if s:
            kandidat, terpilih = s["kandidat"], s["terpilih"]
    for w in peringatan:
        print("PERINGATAN:", w)
    laporan(pd.Timestamp(status["tgl_terakhir"]), siap, kandidat, terpilih, status, posisi)
    print("\nbukan nasihat keuangan. Paper trade: catat, bandingkan dengan backtest, jangan ubah aturan.")


if __name__ == "__main__":
    utama()
