import argparse
import logging
import math
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.ingest import des_ojk
from backend.ingest.final import buang_belum_final
from backend.paper.tren_harian import PAJAK_DIVIDEN, ke_mongo, unduh
from backend.research import uji_h21_h22 as m
from backend.research.swing_target3 import rapikan_index

MULAI = pd.Timestamp("2026-11-01")
MODAL = 100_000_000
LOT = 100
MIN_NILAI = 5e9
MIN_HARGA = 100
JII = "harian_indeks/JII"
K_STATUS, K_POSISI, K_TRANSAKSI, K_EKUITAS, K_REBALANCE = (
    "paper_h22_status", "paper_h22_posisi", "paper_h22_transaksi", "paper_h22_ekuitas", "paper_h22_rebalance")
K_KOREKSI = "paper_h22_koreksi"
KOLOM_POSISI = ["ticker", "lembar", "tgl_masuk", "harga_masuk", "modal_rp", "terima_rp", "dividen_rp"]


def db():
    return kdb.koneksi()


def unduh_jii():
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    x = yf.download("^JKII", period="2y", interval="1d", auto_adjust=True, progress=False)
    if x is None or x.empty:
        return
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = x.columns.get_level_values(0)
    s = buang_belum_final(rapikan_index(x)["Close"].dropna(), "^JKII")
    if len(s):
        dt.tulis(JII, s.to_frame("jii"))


def susun():
    semua = dt.baca_banyak("harian")
    ihsg = semua.pop("_ihsg")["ihsg"].dropna()
    tgl = pd.DatetimeIndex(sorted(ihsg.index))
    data = {}
    for k, df in semua.items():
        if k.startswith("_"):
            continue
        df = df[(df[["open", "high", "low", "close", "adj_close"]] > 0).all(axis=1)]
        if len(df) < 250:
            continue
        f = df["adj_close"] / df["close"]
        nol = pd.Series(0.0, index=df.index)
        data[k] = pd.DataFrame({"o_raw": df["open"], "h_raw": df["high"], "l_raw": df["low"], "c_raw": df["close"],
                                "o": df["open"] * f, "c": df["adj_close"], "v": df["volume"],
                                "div": df["dividends"] if "dividends" in df else nol,
                                "split": df["stock_splits"] if "stock_splits" in df else nol}).reindex(tgl)
    kode = sorted(data)
    P = {kol: pd.DataFrame({k: data[k][kol] for k in kode}, index=tgl)
         for kol in ["o_raw", "h_raw", "l_raw", "c_raw", "o", "c", "v", "div", "split"]}
    for kol in ["v", "div", "split"]:
        P[kol] = P[kol].fillna(0)
    P["c_raw_ff"] = P["c_raw"].ffill()
    P["konversi"] = pd.DataFrame(False, index=tgl, columns=kode)
    nilai = (P["c_raw"] * P["v"]).fillna(0)
    P["med60"] = nilai.rolling(60, min_periods=60).median()
    P["aktif250"] = (P["v"] > 0).astype(float).rolling(250, min_periods=250).mean()
    P["jml_data"] = P["c_raw"].notna().cumsum()
    akhir_bulan = pd.Series(tgl, index=tgl).groupby(tgl.to_period("M")).max()
    return {"tgl": tgl, "P": P, "des": des_ojk.baca(), "kode": kode, "akhir_bulan": akhir_bulan, "periode": "holdout"}


def muat():
    st = db()[K_STATUS].find_one({"_id": "status"}, {"_id": 0})
    pos = {}
    for p in db()[K_POSISI].find({}, {"_id": 0}):
        p["tgl_masuk"] = pd.Timestamp(p["tgl_masuk"])
        pos[p["ticker"]] = p
    return st, pos


def bson(v):
    if isinstance(v, dict):
        return {str(k): bson(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [bson(x) for x in v]
    return ke_mongo(v)


def simpan(st, pos):
    db()[K_STATUS].replace_one({"_id": "status"}, {"_id": "status", **bson(st)}, upsert=True)
    db()[K_POSISI].delete_many({})
    if pos:
        db()[K_POSISI].insert_many([{k: ke_mongo(p.get(k)) for k in KOLOM_POSISI} for p in pos.values()])


def catat(baris):
    db()[K_TRANSAKSI].insert_one({k: ke_mongo(v) for k, v in baris.items()})


def ekuitas_tercatat(tgl):
    x = db()[K_EKUITAS].find_one({"tgl": {"$lte": ke_mongo(pd.Timestamp(tgl).to_pydatetime())}}, sort=[("tgl", -1)])
    return float(x["ekuitas"]) if x else float(MODAL)


def nilai_jii(tgl):
    if not dt.ada(JII):
        return None
    s = dt.baca(JII)["jii"].dropna()
    s = s[s.index <= tgl]
    return float(s.iloc[-1]) if len(s) else None


def koreksi_sinyal(t):
    return {d["ticker"]: d for d in db()[K_KOREKSI].find({"sinyal": pd.Timestamp(t).to_pydatetime()}, {"_id": 0})}


def rencana(S, t, pos):
    P = S["P"]
    calon = list(m.lolos(S, t, MIN_NILAI, MIN_HARGA))
    mom = m.momentum(S, t)
    kor = koreksi_sinyal(t)
    urut_asli = list(mom.reindex(calon).dropna().sort_values(ascending=False, kind="mergesort").index)
    for k, d in kor.items():
        if d.get("momentum_koreksi") is not None:
            mom[k] = d["momentum_koreksi"]
    urut = list(mom.reindex(calon).dropna().sort_values(ascending=False, kind="mergesort").index)
    n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
    no_asli = {k: i + 1 for i, k in enumerate(urut_asli)}
    no_baru = {k: i + 1 for i, k in enumerate(urut)}
    dampak = {"masuk": sorted(set(urut[:n]) - set(urut_asli[:n])), "keluar": sorted(set(urut_asli[:n]) - set(urut[:n])),
              "dihitung_ulang": len(kor), "lama": urut_asli[:n], "baru": urut[:n]} if kor else None
    rank = {k: i + 1 for i, k in enumerate(urut)}
    tetap = sorted([k for k in pos if rank.get(k, 10 ** 9) <= 2 * n], key=lambda k: rank[k])
    jual = [k for k in pos if k not in tetap]
    if len(tetap) > n:
        jual += tetap[n:]
        tetap = tetap[:n]
    baru = [k for k in urut if k not in pos][: max(0, n - len(tetap))]
    return {"sinyal": t, "lolos": len(calon), "n": n, "calon": calon, "tetap": tetap, "jual": jual, "baru": baru,
            "peringkat": [{"ticker": k, "momentum_pct": round(float(mom[k]) * 100, 1)} for k in urut[: 2 * n]],
            "koreksi": [{"ticker": k, "momentum_yahoo_pct": d["momentum_yahoo_pct"],
                         "momentum_koreksi_pct": round(d["momentum_koreksi"] * 100, 1) if d.get("momentum_koreksi") is not None else None,
                         "peringkat_yahoo": no_asli.get(k), "peringkat_koreksi": no_baru.get(k), "penyebab": d.get("penyebab"), "alasan": d.get("alasan")}
                        for k, d in sorted(kor.items(), key=lambda x: no_baru.get(x[0], 10 ** 9)) if no_asli.get(k) != no_baru.get(k)],
            "koreksi_dampak": dampak,
            "harga_sinyal": {k: (float(P["c_raw_ff"].at[t, k]) if k in P["c_raw_ff"].columns else pos[k]["harga_masuk"]) for k in pos}}


def jual_semua(S, k, d, st, pos, alasan):
    P = S["P"]
    p = pos.pop(k)
    harga = float(P["o_raw"].at[d, k])
    terima = p["lembar"] * harga * (1 - m.FEE_JUAL - m.biaya_tick(P, k, d, 1))
    st["kas"] += terima
    total = terima + p["terima_rp"] + p["dividen_rp"]
    catat({"tgl": d, "aksi": "jual", "ticker": k, "alasan": alasan, "lembar": p["lembar"], "harga": harga, "nilai_rp": round(terima),
           "tgl_masuk": p["tgl_masuk"], "harga_masuk": p["harga_masuk"], "net_pct": round((total / p["modal_rp"] - 1) * 100, 2),
           "untung_rp": round(total - p["modal_rp"])})


def ew_rebalance(S, t, d, st, calon):
    P = S["P"]
    ew = st.get("ew") or {"nilai": float(MODAL), "lembar": {}}
    if ew["lembar"]:
        ew["nilai"] = sum(l * (P["o_raw"].at[d, k] if P["o_raw"].at[d, k] > 0 else P["c_raw_ff"].at[d, k]) for k, l in ew["lembar"].items()
                          if P["c_raw_ff"].at[d, k] == P["c_raw_ff"].at[d, k]) + ew.get("kas", 0.0)
    lembar = {}
    for k in calon:
        h = P["o_raw"].at[d, k] if P["o_raw"].at[d, k] > 0 else P["c_raw_ff"].at[d, k]
        if h > 0:
            lembar[k] = float((ew["nilai"] / len(calon)) / h)
    st["ew"] = {"nilai": float(ew["nilai"]), "lembar": lembar, "kas": 0.0}


def ew_harian(S, d, st):
    P = S["P"]
    ew = st.get("ew")
    if not ew or not ew["lembar"]:
        return float(MODAL) if not ew else ew["nilai"]
    for k, l in list(ew["lembar"].items()):
        sp = P["split"].at[d, k]
        if sp and sp > 0 and sp != 1:
            ew["lembar"][k] = l * sp
        if P["div"].at[d, k] > 0:
            ew["kas"] = ew.get("kas", 0.0) + ew["lembar"][k] * float(P["div"].at[d, k])
    return float(sum(l * P["c_raw_ff"].at[d, k] for k, l in ew["lembar"].items() if P["c_raw_ff"].at[d, k] == P["c_raw_ff"].at[d, k]) + ew.get("kas", 0.0))


def proses_hari(S, d, prev, st, pos, log):
    P = S["P"]
    kolom = set(S["kode"])
    for k in sorted(set(pos) - kolom):
        log.append(f"PERINGATAN: data harga {k} tidak ada, posisi tidak bisa diproses hari {d.date()}")
    for k, p in pos.items():
        if k not in kolom:
            continue
        sp = P["split"].at[d, k]
        if sp and sp > 0 and sp != 1:
            p["lembar"] *= float(sp)
            catat({"tgl": d, "aksi": "split", "ticker": k, "lembar": p["lembar"], "rasio": float(sp)})
            log.append(f"{k} split {sp} pada {d.date()}: lembar disesuaikan")
        dv = P["div"].at[d, k]
        if dv > 0:
            x = p["lembar"] * float(dv) * (1 - PAJAK_DIVIDEN)
            st["kas"] += x
            p["dividen_rp"] += x
            catat({"tgl": d, "aksi": "dividen", "ticker": k, "nilai_rp": round(x)})
    tunda_jual = set(st.get("tunda_jual") or [])
    tunda_beli = dict(st.get("tunda_beli") or {})
    if prev is not None and d.to_period("M") != prev.to_period("M"):
        for k, a in tunda_beli.items():
            st["kas"] += a
            catat({"tgl": d, "aksi": "batal_tunda", "ticker": k, "nilai_rp": round(a)})
        tunda_beli = {}
        r = rencana(S, prev, pos)
        dasar = ekuitas_tercatat(prev)
        n = r["n"]
        tunda_jual |= set(r["jual"])
        for k in r["tetap"]:
            w = pos[k]["lembar"] * r["harga_sinyal"][k] / dasar if dasar > 0 else 0
            if w > 2 / n and k in kolom and m.bisa(P, k, d, "jual"):
                target = (dasar / n) / r["harga_sinyal"][k]
                lembar = math.floor((pos[k]["lembar"] - target) / LOT) * LOT
                if lembar > 0:
                    harga = float(P["o_raw"].at[d, k])
                    terima = lembar * harga * (1 - m.FEE_JUAL - m.biaya_tick(P, k, d, 1))
                    pos[k]["lembar"] -= lembar
                    pos[k]["terima_rp"] += terima
                    st["kas"] += terima
                    catat({"tgl": d, "aksi": "pangkas", "ticker": k, "lembar": lembar, "harga": harga, "nilai_rp": round(terima)})
        for k in list(tunda_jual):
            if k in pos and k in kolom and m.bisa(P, k, d, "jual"):
                jual_semua(S, k, d, st, pos, "peringkat turun")
                tunda_jual.discard(k)
            elif k not in pos:
                tunda_jual.discard(k)
        anggaran = min(dasar / n, st["kas"] / len(r["baru"])) if r["baru"] else 0.0
        for k in r["baru"]:
            tunda_beli[k] = anggaran
            st["kas"] -= anggaran
        ew_rebalance(S, prev, d, st, r["calon"])
        db()[K_REBALANCE].replace_one({"eksekusi": ke_mongo(d.to_pydatetime())},
                                      {**{k: ke_mongo(v) for k, v in r.items() if k not in ("calon", "harga_sinyal")},
                                       "eksekusi": d.to_pydatetime(), "ekuitas_dasar": round(dasar), "anggaran_rp": round(anggaran)}, upsert=True)
        log.append(f"rebalance {d.date()} (sinyal {prev.date()}): {r['lolos']} saham lolos, N {n}, beli {len(r['baru'])}, jual {len(r['jual'])}")
    else:
        for k in list(tunda_jual):
            if k in pos and k in kolom and m.bisa(P, k, d, "jual"):
                jual_semua(S, k, d, st, pos, "peringkat turun (tertunda)")
                tunda_jual.discard(k)
            elif k not in pos:
                tunda_jual.discard(k)
    for k in list(tunda_beli):
        if not m.bisa(P, k, d, "beli"):
            continue
        a = tunda_beli.pop(k)
        harga = float(P["o_raw"].at[d, k])
        per = harga * (1 + m.FEE_BELI + m.biaya_tick(P, k, d, 1))
        lembar = math.floor(a / per / LOT) * LOT
        if lembar < LOT:
            st["kas"] += a
            catat({"tgl": d, "aksi": "batal_kas", "ticker": k, "nilai_rp": round(a)})
            continue
        biaya = lembar * per
        st["kas"] += a - biaya
        pos[k] = {"ticker": k, "lembar": float(lembar), "tgl_masuk": d, "harga_masuk": harga, "modal_rp": biaya, "terima_rp": 0.0, "dividen_rp": 0.0}
        catat({"tgl": d, "aksi": "beli", "ticker": k, "lembar": lembar, "harga": harga, "nilai_rp": round(biaya)})
    st["tunda_jual"] = sorted(tunda_jual)
    st["tunda_beli"] = tunda_beli
    nilai = sum(p["lembar"] * (float(P["c_raw_ff"].at[d, k]) if k in kolom and P["c_raw_ff"].at[d, k] == P["c_raw_ff"].at[d, k] else p["harga_masuk"])
                for k, p in pos.items())
    eq = st["kas"] + sum(tunda_beli.values()) + nilai
    db()[K_EKUITAS].replace_one({"tgl": d.to_pydatetime()}, {"tgl": d.to_pydatetime(), "ekuitas": round(eq), "kas": round(st["kas"]),
                                                           "posisi": len(pos), "ew": round(ew_harian(S, d, st)), "jii": nilai_jii(d)}, upsert=True)
    st["tgl_terakhir"] = str(d.date())


def pratinjau(S, st, pos, akhir):
    besok = akhir + pd.offsets.BDay(1)
    if besok.to_period("M") == akhir.to_period("M"):
        st["rencana"] = None
        return
    r = rencana(S, akhir, pos)
    st["rencana"] = {"sinyal": str(akhir.date()), "lolos": r["lolos"], "n": r["n"], "beli": r["baru"], "jual": r["jual"], "tetap": r["tetap"],
                     "peringkat": r["peringkat"], "koreksi": r["koreksi"], "koreksi_dampak": r["koreksi_dampak"], "anggaran_rp": round(min(ekuitas_tercatat(akhir) / r["n"], st["kas"] / len(r["baru"])) if r["baru"] else 0)}


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tanpa-unduh", action="store_true")
    ap.add_argument("--sampai")
    ap.add_argument("--mulai", help="tanggal mulai paper (hanya saat pertama kali; dipakai cek ulang)")
    a = ap.parse_args()
    mulai = pd.Timestamp(a.mulai) if a.mulai else MULAI
    st, pos = muat()
    des = des_ojk.baca()
    hari_ini = pd.Timestamp.today().normalize()
    if not a.tanpa_unduh:
        lain = sorted(set(pos) - des_ojk.syariah_pada(des, hari_ini))
        if lain:
            print(f"unduh harga {len(lain)} saham yang dipegang tapi tidak lagi di DES: {', '.join(lain)}")
            unduh(lain)
        unduh_jii()
    S = susun()
    kal = S["tgl"]
    akhir = kal.max()
    if akhir >= hari_ini and pd.Timestamp.now().hour < 17:
        akhir = kal[kal < hari_ini].max()
        print(f"data hari ini belum final: diproses sampai {akhir.date()}")
    if a.sampai:
        akhir = min(akhir, pd.Timestamp(a.sampai))
    if st is None:
        awal = kal[kal < mulai].max()
        st = {"modal_awal": float(MODAL), "kas": float(MODAL), "tgl_terakhir": str(awal.date()), "mulai": str(mulai.date()),
              "tunda_jual": [], "tunda_beli": {}, "ew": None, "rencana": None, "sesi": datetime.now().strftime("%Y%m%d-%H%M%S")}
        kdb.koneksi()[K_EKUITAS].create_index("tgl", unique=True)
        db()[K_EKUITAS].replace_one({"tgl": awal.to_pydatetime()}, {"tgl": awal.to_pydatetime(), "ekuitas": round(MODAL), "kas": round(MODAL),
                                                                  "posisi": 0, "ew": round(MODAL), "jii": nilai_jii(awal)}, upsert=True)
        print(f"paper H29 bagian H22 dimulai: modal Rp{MODAL:,.0f}, titik awal {awal.date()}, rebalance pertama di open hari bursa pertama {mulai:%B %Y}")
    terakhir = pd.Timestamp(st["tgl_terakhir"])
    hari = kal[(kal > terakhir) & (kal <= akhir)]
    log = []
    prev = terakhir
    for d in hari:
        proses_hari(S, d, prev, st, pos, log)
        prev = d
    pratinjau(S, st, pos, pd.Timestamp(st["tgl_terakhir"]))
    simpan(st, pos)
    for x in log:
        print(x)
    e = db()[K_EKUITAS].find_one(sort=[("tgl", -1)])
    print(f"diproses sampai {st['tgl_terakhir']}: ekuitas Rp{e['ekuitas']:,.0f}, kas Rp{st['kas']:,.0f}, {len(pos)} posisi, "
          f"{len(st['tunda_beli'])} beli tertunda, {len(st['tunda_jual'])} jual tertunda")
    if st.get("rencana"):
        r = st["rencana"]
        print(f"rencana rebalance (sinyal {r['sinyal']}, eksekusi open hari bursa berikutnya): {r['lolos']} saham lolos, N {r['n']}, "
              f"beli {', '.join(r['beli']) or '-'}; jual {', '.join(r['jual']) or '-'}")
    print("SELESAI")


if __name__ == "__main__":
    utama()
