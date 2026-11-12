from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import harga as hg
from backend.db import isi_backtest as ib
from backend.db import koneksi as kdb
from backend.paper import h22_harian as h22p
from backend.paper import h29 as h29p
from backend.paper import sumber_idx
from backend.paper import tren_harian as th
from backend.paper.batas_paper import kurva_harian
from backend.research import screener as sc
from backend.research import simulasi_h29 as s29
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

JUMLAH_SIMULASI = 100
TOL = 1e-4
K_BANDING, K_BULANAN = "pantau_banding", "pantau_bulanan"
CATATAN_H11A = [
    "Backtest = mesin uji_tren.simulasi + simulasi_portofolio (versi h11a_2020) pada data riset (koleksi harga, Yahoo yang dikoreksi); paper = mesin tren_harian pada data harian dengan harga IDX resmi.",
    "Replay = trade backtest untuk saham yang sama dengan pilihan paper (sinyal sama), dihitung dengan kurva harian backtest. Selisih paper - replay = efek data dan cara eksekusi, bukan keberuntungan.",
    "Simulasi Monte Carlo = 100 portofolio backtest mulai dari kosong pada hari pertama paper, pilihan acak berbeda tiap seed. Persentil paper = seberapa beruntung pilihan acak paper.",
    "Selisih yang memang diharapkan: backtest memakai lembar pecahan, paper memakai lot 100 lembar; sebelum 2 Nov 2026 paper mengukur posisi dari ekuitas hari itu, backtest dari ekuitas kemarin.",
    "Slippage nyata tidak bisa diukur di paper: paper selalu mengisi di harga pembukaan resmi. Yang diukur adalah selisih harga paper (IDX) dengan harga backtest (Yahoo), dalam persen dan tick.",
]
CATATAN_H22 = [
    "Backtest = mesin uji_h21_h22 + simulasi_h29.rs_simulasi pada data riset, rebalance pertama sama dengan paper; paper = h22_harian pada data harian dengan harga IDX resmi dan koreksi peringkat 30 Okt 2026 (keputusan user).",
    "H29 replay = 50% replay Follow Tren + 50% backtest RS 12-1, dikembalikan ke 50/50 tiap akhir bulan (fungsi gabung simulasi_h29). Monte Carlo H29 memakai 100 simulasi bagian Follow Tren.",
    "Backtest memakai lembar pecahan, paper memakai lot 100 lembar.",
]
LABEL_SPLIT = "beda karena split/bonus (diharapkan), bukan penyimpangan"
JENDELA_SPLIT_HARI = 5
_CACHE = {}


def db():
    return kdb.koneksi()


def split_tercatat():
    hasil = {}
    for c in db().paper_catatan.find({"jenis": "split"}, {"_id": 0}).sort("tgl", 1):
        hasil.setdefault(c["ticker"], []).append(c)
    return hasil


def batas_jendela_split(tgl_split, kalender, hari=JENDELA_SPLIT_HARI):
    awal = pd.Timestamp(tgl_split).normalize()
    k = pd.DatetimeIndex(sorted(pd.Timestamp(x).normalize() for x in kalender))
    letak = int(k.searchsorted(awal))
    if letak + hari < len(k):
        return k[letak + hari]
    return awal + pd.offsets.BDay(hari)


def tanggal_keputusan(baris, sampai):
    hasil = []
    for kunci in ("tgl_masuk", "tgl_keluar"):
        a, b = baris.get(f"{kunci}_paper"), baris.get(f"{kunci}_backtest")
        if a != b:
            hasil += [x for x in (a, b) if x]
    if not hasil:
        hasil = [str(pd.Timestamp(sampai).date())]
    return [pd.Timestamp(x).normalize() for x in hasil]


def dikecualikan_split(baris, catatan_split, kalender, sampai):
    if not catatan_split:
        return False
    tanggal = tanggal_keputusan(baris, sampai)
    for c in catatan_split:
        awal = pd.Timestamp(c["tgl"]).normalize()
        akhir = batas_jendela_split(awal, kalender)
        if any(awal <= t <= akhir for t in tanggal):
            return True
    return False


def r4(v):
    return None if v is None or v != v else round(float(v), 4)


def r2(v):
    return None if v is None or v != v else round(float(v), 2)


def sama(a, b):
    return a is not None and b is not None and a == a and b == b and (abs(a - b) <= TOL * max(1.0, abs(b)))


def siap_backtest(sampai):
    siap = ut.siapkan_holdout()
    return {t: x[x.index <= sampai] for t, x in siap.items()}


def siap_paper(sampai):
    mentah, ihsg = th.baca_lokal()
    if sumber_idx.AKTIF:
        mentah = sumber_idx.susun(mentah)
    awal = min((df.index.min() for df in mentah.values() if len(df)), default=None)
    siap = th.siapkan(mentah, ihsg, th.tutup_resmi_tanpa_transaksi(awal))
    return {t: x[x.index <= sampai] for t, x in siap.items()}


def nilai(x, t, kol):
    if x is None or t not in x.index:
        return None
    v = x.at[t, kol]
    return None if v != v else float(v)


def rincian_sinyal(t, d, xp, xb):
    p_close, b_close = nilai(xp, d, "m_close"), nilai(xb, d, "close_mentah")
    p_r = nilai(xp, d, "close") / nilai(xp, d, "maks250") if nilai(xp, d, "maks250") else None
    b_r = nilai(xb, d, "close") / nilai(xb, d, "maks250") if nilai(xb, d, "maks250") else None
    p_l = bool(xp.at[d, "lolos"]) if xp is not None and d in xp.index else None
    b_l = bool(xb.at[d, "lolos"]) if xb is not None and d in xb.index else None
    r = {"close_paper": p_close, "close_backtest": b_close, "rasio_paper": r4(p_r), "rasio_backtest": r4(b_r), "lolos_paper": p_l, "lolos_backtest": b_l,
         "nilai20_paper": r2(nilai(xp, d, "value_mentah")), "nilai20_backtest": r2(nilai(xb, d, "value_mentah")),
         "atr_pct_paper": r4(nilai(xp, d, "atr_pct")), "atr_pct_backtest": r4(nilai(xb, d, "atr_pct"))}
    if p_close is None:
        return r, "tidak ada di data paper hari itu", True
    if b_close is None:
        return r, "tidak ada di data backtest hari itu", True
    data_sama = sama(p_close, b_close) and sama(p_r, b_r) and sama(r["nilai20_paper"], r["nilai20_backtest"]) and sama(r["atr_pct_paper"], r["atr_pct_backtest"])
    if p_l != b_l:
        sebab = "filter likuiditas/ATR beda"
    elif not sama(p_close, b_close):
        sebab = f"close beda: paper {p_close:,.0f} vs backtest {b_close:,.0f}"
    else:
        sebab = "jarak ke tertinggi 250 hari beda (riwayat harga beda)"
    return r, sebab, not data_sama


def satu_trade(xb, t, tgl_sinyal):
    if xb is None or tgl_sinyal not in xb.index:
        return None
    i = xb.index.get_loc(tgl_sinyal)
    mask = np.zeros(len(xb), dtype=bool)
    mask[i] = True
    hasil = ut.simulasi(xb, t, mask)
    if not hasil:
        return {"status": "belum_masuk"}
    r = hasil[0]
    beli, tgl_beli = ib.harga_pasar(xb, r["tgl"], 1, "open")
    status = {"stop": "jual", "akhir_data": "jual_besok", "terbuka": "aktif", "waktu": "batas_waktu"}[r["alasan"]]
    out = {"status": status, "tgl_masuk": tgl_beli, "harga_masuk": beli, "stop_awal_pct": float(r["stop_pct"])}
    if status == "jual":
        out["harga_keluar"], _ = ib.harga_pasar(xb, r["tgl_exit"], 0, "open")
        out["tgl_keluar"] = r["tgl_exit"]
        out["net_pct"] = float(r["net"])
    return out


def data_sama_rentang(xp, xb, mulai, akhir):
    if xp is None or xb is None:
        return False
    a = xp.loc[(xp.index >= mulai) & (xp.index <= akhir), ["m_close", "atr_mentah"]]
    b = xb.loc[(xb.index >= mulai) & (xb.index <= akhir)]
    b = pd.DataFrame({"m_close": b["close_mentah"], "atr_mentah": b["atr"] * b["close_mentah"] / b["close"]})
    j = a.join(b, rsuffix="_b", how="outer")
    if j.isna().any().any():
        return False
    return bool(((j["m_close"] / j["m_close_b"] - 1).abs() <= TOL).all() and ((j["atr_mentah"] / j["atr_mentah_b"] - 1).abs() <= 1e-3).all())


def ke_kurva(baris):
    df = pd.DataFrame(baris, columns=["ticker", "tgl_beli", "harga_beli", "tgl_jual", "harga_jual"])
    if df.empty:
        return df
    df["tgl_beli"] = pd.to_datetime(df["tgl_beli"])
    df["tgl_jual"] = pd.to_datetime(df["tgl_jual"])
    return df.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)


def kurva(df, mulai, sampai, mentah):
    if df.empty:
        hari = hg.ihsg()
        hari = hari.index[(hari.index >= mulai) & (hari.index <= sampai)]
        return pd.Series(1.0, index=hari)
    return kurva_harian(df, mulai, sampai, {t: mentah[t] for t in df["ticker"].unique() if t in mentah})


def baris_kurva(rows, siap):
    out = []
    for r in rows:
        x = siap[r["ticker"]]
        beli, tgl_beli = ib.harga_pasar(x, r["tgl"], 1, "open")
        if r["alasan"] == "stop":
            jual, _ = ib.harga_pasar(x, r["tgl_exit"], 0, "open")
            out.append((r["ticker"], tgl_beli, beli, r["tgl_exit"], jual))
        else:
            out.append((r["ticker"], tgl_beli, beli, pd.NaT, np.nan))
    return out


def persentil(nilai_, sebaran):
    sebaran = np.asarray(sebaran, float)
    if not len(sebaran) or np.ptp(sebaran) < 0.01:
        return None
    return round(float((sebaran <= nilai_).mean() * 100), 1)


def satu_sebaran(sebaran):
    return bool(len(sebaran)) and float(np.ptp(np.asarray(sebaran, float))) < 0.01


def sidik(kode, mulai, sampai):
    kode = sorted(set(kode))
    if not kode:
        return None
    awal = pd.Timestamp(mulai) - pd.Timedelta(days=400)
    return {"harga": hg.sidik(kode, awal, sampai), "harian": hg.sidik(kode, awal, sampai, koleksi="harian")}


def catat_bulanan(strategi, kurva_tgl, seri, sampai, tambahan=None):
    if not kurva_tgl:
        return
    t = pd.DatetimeIndex(pd.to_datetime(kurva_tgl))
    df = pd.DataFrame({k: v for k, v in seri.items()}, index=t)
    bulan_ini = pd.Timestamp(sampai).to_period("M")
    akhir_bln = df.groupby(df.index.to_period("M")).last()
    awal = df.iloc[0]
    for i, (b, baris) in enumerate(akhir_bln.iterrows()):
        if b >= bulan_ini:
            continue
        _id = f"{strategi}:{b}"
        if db()[K_BULANAN].find_one({"_id": _id}):
            continue
        sebelum = akhir_bln.iloc[i - 1] if i else awal
        dok = {"_id": _id, "strategi": strategi, "bulan": str(b), "dibuat": datetime.now(),
               "return_pct": {k: r2((baris[k] / sebelum[k] - 1) * 100) if sebelum[k] and baris[k] == baris[k] else None for k in df.columns},
               "kumulatif_pct": {k: r2((baris[k] / awal[k] - 1) * 100) if awal[k] and baris[k] == baris[k] else None for k in df.columns}}
        if tambahan:
            dok.update(tambahan(b))
        db()[K_BULANAN].insert_one(dok)


def h11a():
    st = db().paper_status.find_one({"_id": "status"})
    pertama = db().paper_ekuitas.find_one(sort=[("tgl", 1)])
    if not st or not pertama:
        return "paper H11a belum mulai"
    mulai, sampai = pd.Timestamp(pertama["tgl"]), pd.Timestamp(st["tgl_terakhir"])
    modal = float(st["modal_awal"])
    sb, sp = siap_backtest(sampai), siap_paper(sampai)
    akhir_riset = max((x.index.max() for x in sb.values() if len(x)), default=None)
    ek = list(db().paper_ekuitas.find({}, {"_id": 0}).sort("tgl", 1))
    kal = [pd.Timestamp(e["tgl"]) for e in ek]
    sinyal_p = {pd.Timestamp(s["tgl"]): s for s in db().paper_sinyal.find({}, {"_id": 0})}
    snap = {}
    for x in db()["pantau_posisi_h11a"].find({}, {"tgl": 1, "ticker": 1}):
        snap.setdefault(pd.Timestamp(x["tgl"]), set()).add(x["ticker"])
    beda, hari_sama, tak = [], 0, []
    for d in kal:
        s = sinyal_p.get(d) or {}
        dipegang = snap.get(d, set()) - set(s.get("terpilih") or [])
        kb = {t for t, x in sb.items() if d in x.index and bool(x.at[d, "lolos"]) and x.at[d, "close"] >= x.at[d, "maks250"]} - dipegang
        kp = set(s.get("kandidat") or [])
        selisih = sorted(kb ^ kp)
        if not selisih:
            hari_sama += 1
        for t in selisih:
            r, sebab, terjelaskan = rincian_sinyal(t, d, sp.get(t), sb.get(t))
            b = {"tgl": str(d.date()), "ticker": t, "hanya_di": "paper" if t in kp else "backtest", "penyebab": sebab, "terjelaskan": terjelaskan, **r}
            beda.append(b)
            if not terjelaskan:
                tak.append({"jenis": "sinyal", "tgl": b["tgl"], "ticker": t, "hanya_di": b["hanya_di"]})

    trade_p = []
    for x in db().paper_transaksi.find({"aksi": "jual"}, {"_id": 0}):
        trade_p.append({"ticker": x["ticker"], "tgl_sinyal": pd.Timestamp(x["tgl_sinyal"]), "tgl_masuk": pd.Timestamp(x["tgl_masuk"]), "harga_masuk": x["harga_masuk"],
                        "status": "jual", "tgl_keluar": pd.Timestamp(x["tgl"]), "harga_keluar": x["harga_keluar"], "net_pct": x["net_pct"], "lot": x["lot"]})
    for x in db().paper_posisi.find({}, {"_id": 0}):
        trade_p.append({"ticker": x["ticker"], "tgl_sinyal": pd.Timestamp(x["tgl_sinyal"]), "status": x["status"], "lot": x.get("lot"),
                        "tgl_masuk": pd.Timestamp(x["tgl_masuk"]) if x.get("tgl_masuk") else None, "harga_masuk": x.get("harga_masuk"),
                        "stop": x.get("stop"), "atr_sinyal": x.get("atr_sinyal")})
    for x in db().paper_transaksi.find({"aksi": {"$in": ["batal_ARA", "batal_kas"]}}, {"_id": 0}):
        trade_p.append({"ticker": x["ticker"], "tgl_sinyal": pd.Timestamp(x["tgl_sinyal"]), "status": x["aksi"]})
    trade, replay_rows = [], []
    split_ticker = split_tercatat()
    for p in sorted(trade_p, key=lambda z: (z["tgl_sinyal"], z["ticker"])):
        b = satu_trade(sb.get(p["ticker"]), p["ticker"], p["tgl_sinyal"])
        baris = {"ticker": p["ticker"], "tgl_sinyal": str(p["tgl_sinyal"].date()), "status_paper": p["status"], "status_backtest": b["status"] if b else "tidak_ada",
                 "tgl_masuk_paper": str(p["tgl_masuk"].date()) if p.get("tgl_masuk") is not None else None,
                 "tgl_masuk_backtest": str(b["tgl_masuk"].date()) if b and b.get("tgl_masuk") is not None else None,
                 "harga_masuk_paper": r2(p.get("harga_masuk")), "harga_masuk_backtest": r2(b.get("harga_masuk")) if b else None, "lot": p.get("lot")}
        if b and p.get("harga_masuk") and b.get("harga_masuk"):
            baris["selisih_masuk_pct"] = r4((p["harga_masuk"] / b["harga_masuk"] - 1) * 100)
            baris["selisih_masuk_tick"] = r2((p["harga_masuk"] - b["harga_masuk"]) / float(sc.fraksi(b["harga_masuk"])))
        if b and p.get("atr_sinyal") and p.get("harga_masuk"):
            baris["stop_awal_pct_paper"] = r2(th.MULT_ATR * p["atr_sinyal"] / p["harga_masuk"] * 100)
            baris["stop_awal_pct_backtest"] = r2(b.get("stop_awal_pct"))
        if p["status"] == "jual" or (b and b["status"] == "jual"):
            baris.update(tgl_keluar_paper=str(p["tgl_keluar"].date()) if p.get("tgl_keluar") is not None else None,
                         tgl_keluar_backtest=str(b["tgl_keluar"].date()) if b and b.get("tgl_keluar") is not None else None,
                         harga_keluar_paper=r2(p.get("harga_keluar")), harga_keluar_backtest=r2(b.get("harga_keluar")) if b else None,
                         net_paper=r2(p.get("net_pct")), net_backtest=r2(b.get("net_pct")) if b else None)
            if p.get("harga_keluar") and b and b.get("harga_keluar"):
                baris["selisih_keluar_pct"] = r4((p["harga_keluar"] / b["harga_keluar"] - 1) * 100)
                baris["selisih_keluar_tick"] = r2((p["harga_keluar"] - b["harga_keluar"]) / float(sc.fraksi(b["harga_keluar"])))
        st_p = {"aktif": "aktif", "jual_besok": "jual_besok", "jual": "jual"}.get(p["status"], p["status"])
        cocok = (b is not None and (st_p == b["status"] or (st_p == "beli_besok" and b["status"] == "belum_masuk"))
                 and baris.get("tgl_masuk_paper") == baris.get("tgl_masuk_backtest") and baris.get("tgl_keluar_paper") == baris.get("tgl_keluar_backtest"))
        baris["keputusan_sama"] = bool(cocok)
        if not cocok and p.get("tgl_masuk") is not None:
            baris["data_sama"] = data_sama_rentang(sp.get(p["ticker"]), sb.get(p["ticker"]), p["tgl_masuk"], sampai)
            if dikecualikan_split(baris, split_ticker.get(p["ticker"]), kal, sampai):
                baris["catatan"] = LABEL_SPLIT
            elif baris["data_sama"] and p["status"] not in ("batal_ARA", "batal_kas"):
                tak.append({"jenis": "trade", "tgl": baris["tgl_sinyal"], "ticker": p["ticker"], "paper": st_p, "backtest": b["status"] if b else None})
        trade.append(baris)
        if b and b.get("tgl_masuk") is not None and p["status"] in ("aktif", "jual_besok", "jual"):
            replay_rows.append((p["ticker"], b["tgl_masuk"], b["harga_masuk"], b.get("tgl_keluar", pd.NaT) if b["status"] == "jual" else pd.NaT,
                                b.get("harga_keluar", np.nan)))

    tr_all = ut.kumpulkan(sb, lambda x, m0=mulai: (x["close"] >= x["maks250"]) & (x.index >= m0))
    perlu = {r[0] for r in replay_rows} | (set(tr_all["ticker"]) if not tr_all.empty else set())
    mentah = {t: hg.mentah(t) for t in perlu}
    replay = kurva(ke_kurva(replay_rows), mulai, sampai, mentah)
    mc, mc_kurva = [], []
    for seed in range(1, JUMLAH_SIMULASI + 1):
        if tr_all.empty:
            k = kurva(ke_kurva([]), mulai, sampai, mentah)
        else:
            pilih = simulasi_portofolio(tr_all, ib.POSISI, seed)
            k = kurva(ke_kurva(baris_kurva(pilih.to_dict("records"), sb)), mulai, sampai, mentah)
        mc_kurva.append(k)
        mc.append(float(k.iloc[-1] - 1) * 100)
    paper = pd.Series([e["ekuitas"] / modal for e in ek], index=kal)
    idx = paper.index
    rep = replay.reindex(idx).ffill()
    mk = pd.concat([k.reindex(idx).ffill() for k in mc_kurva], axis=1)
    dd = lambda s: float((s / np.maximum(s.cummax(), 1.0) - 1).min() * 100)
    ret_p = float(paper.iloc[-1] - 1) * 100
    ret_r = float(rep.iloc[-1] - 1) * 100 if rep.notna().any() else None
    porto = {"return_paper": r2(ret_p), "return_replay": r2(ret_r), "selisih_replay": r2(ret_p - ret_r) if ret_r is not None else None,
             "dd_paper": r2(dd(paper)), "dd_replay": r2(dd(rep.dropna())) if rep.notna().any() else None,
             "mc": {"median": r2(np.median(mc)), "p5": r2(np.percentile(mc, 5)), "p95": r2(np.percentile(mc, 95)),
                    "persentil_paper": persentil(ret_p, mc), "semua_sama": satu_sebaran(mc), "dd_median": r2(np.median([dd(k) for k in mc_kurva]))},
             "kurva": {"tgl": [str(t.date()) for t in idx], "paper": [r2((v - 1) * 100) for v in paper], "replay": [r2((v - 1) * 100) for v in rep],
                       "mc_p5": [r2((v - 1) * 100) for v in mk.quantile(0.05, axis=1)], "mc_median": [r2((v - 1) * 100) for v in mk.median(axis=1)],
                       "mc_p95": [r2((v - 1) * 100) for v in mk.quantile(0.95, axis=1)]}}
    _CACHE["h11a"] = {"replay": replay, "mc": mc_kurva, "sampai": sampai}
    harga_p = [t for t in trade if t.get("selisih_masuk_pct") is not None]
    catatan = list(CATATAN_H11A)
    for t, daftar in split_ticker.items():
        bagian = ", ".join("x%.4f pada %s" % (c["rasio"], c["tgl"].date()) for c in daftar)
        catatan.append(f"{t} melewati split/bonus ({bagian}): selisih keputusan dalam {JENDELA_SPLIT_HARI} hari bursa sesudah tanggal split dikecualikan ({LABEL_SPLIT}); di luar jendela itu tetap dihitung tak terjelaskan.")
    if akhir_riset is not None and akhir_riset < sampai:
        catatan.insert(0, f"Data riset (harga) baru sampai {akhir_riset.date()}, paper sampai {sampai.date()}: hari sesudahnya belum bisa dibandingkan.")
    terlibat = {t["ticker"] for t in trade} | {b["ticker"] for b in beda}
    dok = {"_id": f"h11a:{sampai.date()}", "strategi": "h11a", "mulai": str(mulai.date()), "sampai": str(sampai.date()), "dibuat": datetime.now(),
           "akhir_riset": str(akhir_riset.date()) if akhir_riset is not None else None,
           "sinyal": {"hari": len(kal), "hari_sama": hari_sama, "ticker_hari_beda": len(beda), "beda": beda},
           "trade": trade, "ringkas_trade": {"jumlah": len(trade), "keputusan_sama": sum(t["keputusan_sama"] for t in trade),
                                             "selisih_masuk_rata_pct": r4(np.mean([abs(t["selisih_masuk_pct"]) for t in harga_p])) if harga_p else None,
                                             "selisih_masuk_rata_tick": r2(np.mean([abs(t["selisih_masuk_tick"]) for t in harga_p])) if harga_p else None},
           "portofolio": porto, "tak_terjelaskan": tak, "catatan": catatan, "versi_data": sidik(terlibat, mulai, sampai)}
    db()[K_BANDING].replace_one({"_id": dok["_id"]}, dok, upsert=True)
    k = porto["kurva"]
    catat_bulanan("h11a", k["tgl"], {"paper": [1 + v / 100 for v in k["paper"]], "replay": [1 + v / 100 if v is not None else np.nan for v in k["replay"]],
                                     "mc_median": [1 + v / 100 for v in k["mc_median"]]}, sampai,
                  lambda b: {"sinyal_beda": sum(1 for x in beda if pd.Timestamp(x["tgl"]).to_period("M") == b),
                             "hari": sum(1 for t in kal if t.to_period("M") == b)})
    return (f"{hari_sama}/{len(kal)} hari sinyal sama, {len(beda)} beda; trade sama {dok['ringkas_trade']['keputusan_sama']}/{len(trade)}; "
            f"paper {porto['return_paper']}% vs replay {porto['return_replay']}% (selisih {porto['selisih_replay']}), "
            f"Monte Carlo median {porto['mc']['median']}% (paper di persentil {porto['mc']['persentil_paper']}); tak terjelaskan {len(tak)}")


def susun_s(awal, sampai):
    lama = m.PERIODE
    m.PERIODE = {**lama, "holdout": {"data": ("2010-01-01", str(sampai.date())), "sinyal_awal": str(awal.date()), "akhir": str(sampai.date())}}
    try:
        return m.susun("holdout")
    finally:
        m.PERIODE = lama


def h22():
    st = db()[h22p.K_STATUS].find_one({"_id": "status"})
    reb_p = list(db()[h22p.K_REBALANCE].find({}, {"_id": 0}).sort("sinyal", 1))
    if not st or not reb_p:
        return "paper H22 belum mulai"
    sampai = pd.Timestamp(st["tgl_terakhir"])
    awal = pd.Timestamp(reb_p[0]["sinyal"])
    S = susun_s(awal, sampai)
    e22, ep, rekap = s29.rs_simulasi(S)
    akhir_riset = S["tgl"].max()
    del S
    rb_b = {pd.Timestamp(x["sinyal"]): x for x in rekap}
    kor = {}
    for x in db()[h22p.K_KOREKSI].find({}, {"_id": 0, "sinyal": 1, "ticker": 1, "peringkat_yahoo": 1, "peringkat_koreksi": 1}):
        if x.get("peringkat_yahoo") != x.get("peringkat_koreksi"):
            kor.setdefault(pd.Timestamp(x["sinyal"]), set()).add(x["ticker"])
    rebalance, tak = [], []
    for p in reb_p:
        t = pd.Timestamp(p["sinyal"])
        b = rb_b.get(t)
        if b is None:
            rebalance.append({"sinyal": str(t.date()), "ada_backtest": False})
            continue
        isi_p, isi_b = set(p.get("baru") or []) | set(p.get("tetap") or []), set(b["beli"]) | set(b["tetap"])
        pk_p = [(x["ticker"], x["momentum_pct"]) for x in p.get("peringkat") or []]
        pk_b = [tuple(x) for x in b["peringkat"]]
        mom_b, mom_p = dict(pk_b), dict(pk_p)
        no_b, no_p = {k: i + 1 for i, (k, _) in enumerate(pk_b)}, {k: i + 1 for i, (k, _) in enumerate(pk_p)}
        rinci = []
        for k in sorted(isi_p ^ isi_b):
            sebab = "koreksi peringkat paper 30 Okt 2026 (keputusan user)" if k in kor.get(t, set()) else (
                "momentum beda" if (k in mom_b and k in mom_p and abs(mom_b[k] - mom_p[k]) > 0.05) else "peringkat bergeser karena saham lain")
            rinci.append({"ticker": k, "hanya_di": "paper" if k in isi_p else "backtest", "peringkat_paper": no_p.get(k), "peringkat_backtest": no_b.get(k),
                          "momentum_paper": mom_p.get(k), "momentum_backtest": mom_b.get(k), "penyebab": sebab})
        data_sama = p.get("lolos") == b["lolos"] and pk_p == pk_b and not kor.get(t)
        if data_sama and isi_p != isi_b:
            tak.append({"jenis": "rebalance", "tgl": str(t.date())})
        rebalance.append({"sinyal": str(t.date()), "eksekusi": str(pd.Timestamp(p["eksekusi"]).date()), "ada_backtest": True,
                          "lolos_paper": p.get("lolos"), "lolos_backtest": b["lolos"], "n_paper": p.get("n"), "n_backtest": b["n"],
                          "isi_sama": isi_p == isi_b, "jumlah_isi": len(isi_p), "irisan": len(isi_p & isi_b),
                          "peringkat_sama": sum(1 for a, c in zip(pk_p, pk_b) if a[0] == c[0]), "peringkat_n": len(pk_p), "beda": rinci,
                          "koreksi_paper": sorted(kor.get(t, set()))})
    beli_b = {(e["ticker"], pd.Timestamp(e["beli"])): e for e in ep}
    trade = []
    for x in db()[h22p.K_TRANSAKSI].find({"aksi": "beli"}, {"_id": 0}).sort("tgl", 1):
        b = beli_b.get((x["ticker"], pd.Timestamp(x["tgl"])))
        hb = b["harga_beli"] if b else None
        trade.append({"ticker": x["ticker"], "tgl": str(pd.Timestamp(x["tgl"]).date()), "harga_paper": r2(x["harga"]), "harga_backtest": r2(hb),
                      "ada_backtest": b is not None, "lembar": x.get("lembar"),
                      "selisih_pct": r4((x["harga"] / hb - 1) * 100) if hb else None,
                      "selisih_tick": r2((x["harga"] - hb) / float(sc.fraksi(hb))) if hb else None})
    ek = list(db()[h22p.K_EKUITAS].find({}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
    idx = pd.DatetimeIndex([pd.Timestamp(e["tgl"]) for e in ek])
    paper22 = pd.Series([e["ekuitas"] / h22p.MODAL for e in ek], index=idx)
    bt22 = pd.concat([pd.Series([1.0], index=[idx[0]]), e22[e22.index > idx[0]]]).reindex(idx).ffill()
    seri29 = h29p.seri() or []
    paper29 = pd.Series([r["h29"] / h22p.MODAL for r in seri29], index=pd.DatetimeIndex([pd.Timestamp(r["tgl"]) for r in seri29]))
    if "h11a" not in _CACHE or _CACHE["h11a"]["sampai"] < sampai:
        h11a()
    c = _CACHE["h11a"]
    e22n = e22[e22.index <= sampai]
    gab = lambda e11: s29.gabung(e11, e22n, sampai)[0]
    pad = lambda s: pd.concat([pd.Series([1.0], index=[paper29.index[0]]), s[s.index > paper29.index[0]]]).reindex(paper29.index).ffill()
    rep29 = pad(gab(c["replay"])) if len(e22n) else None
    mc29 = [pad(gab(k)) for k in c["mc"]] if len(e22n) else []
    dd = lambda s: float((s / np.maximum(s.cummax(), 1.0) - 1).min() * 100)
    ret = lambda s: float(s.iloc[-1] - 1) * 100
    mc_akhir = [ret(k) for k in mc29]
    mk = pd.concat(mc29, axis=1) if mc29 else None
    porto = {"h22": {"return_paper": r2(ret(paper22)), "return_backtest": r2(ret(bt22)), "selisih": r2(ret(paper22) - ret(bt22)),
                     "dd_paper": r2(dd(paper22)), "dd_backtest": r2(dd(bt22)),
                     "kurva": {"tgl": [str(t.date()) for t in idx], "paper": [r2((v - 1) * 100) for v in paper22], "backtest": [r2((v - 1) * 100) for v in bt22]}},
             "h29": None}
    if rep29 is not None and len(paper29):
        porto["h29"] = {"return_paper": r2(ret(paper29)), "return_replay": r2(ret(rep29)), "selisih_replay": r2(ret(paper29) - ret(rep29)),
                        "dd_paper": r2(dd(paper29)), "dd_replay": r2(dd(rep29)),
                        "mc": {"median": r2(np.median(mc_akhir)), "p5": r2(np.percentile(mc_akhir, 5)), "p95": r2(np.percentile(mc_akhir, 95)),
                               "persentil_paper": persentil(ret(paper29), mc_akhir), "semua_sama": satu_sebaran(mc_akhir)},
                        "kurva": {"tgl": [str(t.date()) for t in paper29.index], "paper": [r2((v - 1) * 100) for v in paper29],
                                  "replay": [r2((v - 1) * 100) for v in rep29], "mc_p5": [r2((v - 1) * 100) for v in mk.quantile(0.05, axis=1)],
                                  "mc_median": [r2((v - 1) * 100) for v in mk.median(axis=1)], "mc_p95": [r2((v - 1) * 100) for v in mk.quantile(0.95, axis=1)]}}
    catatan = list(CATATAN_H22)
    if akhir_riset < sampai:
        catatan.insert(0, f"Data riset baru sampai {akhir_riset.date()}, paper sampai {sampai.date()}.")
    terlibat = {t["ticker"] for t in trade} | {x["ticker"] for r in rebalance for x in r.get("beda", [])}
    dok = {"_id": f"h22:{sampai.date()}", "strategi": "h22", "mulai": str(idx[0].date()), "sampai": str(sampai.date()), "dibuat": datetime.now(),
           "akhir_riset": str(akhir_riset.date()), "rebalance": rebalance, "trade": trade,
           "ringkas_trade": {"jumlah": len(trade), "ada_backtest": sum(t["ada_backtest"] for t in trade),
                             "selisih_rata_pct": r4(np.mean([abs(t["selisih_pct"]) for t in trade if t["selisih_pct"] is not None])) if any(t["selisih_pct"] is not None for t in trade) else None,
                             "selisih_rata_tick": r2(np.mean([abs(t["selisih_tick"]) for t in trade if t["selisih_tick"] is not None])) if any(t["selisih_tick"] is not None for t in trade) else None},
           "portofolio": porto, "tak_terjelaskan": tak, "catatan": catatan, "versi_data": sidik(terlibat, idx[0], sampai)}
    db()[K_BANDING].replace_one({"_id": dok["_id"]}, dok, upsert=True)
    k = porto["h22"]["kurva"]
    catat_bulanan("h22", k["tgl"], {"paper": [1 + v / 100 for v in k["paper"]], "backtest": [1 + v / 100 for v in k["backtest"]]}, sampai)
    if porto["h29"]:
        k = porto["h29"]["kurva"]
        catat_bulanan("h29", k["tgl"], {"paper": [1 + v / 100 for v in k["paper"]], "replay": [1 + v / 100 for v in k["replay"]],
                                        "mc_median": [1 + v / 100 for v in k["mc_median"]]}, sampai)
    r0 = rebalance[-1]
    h29s = porto["h29"] or {}
    return (f"rebalance {r0['sinyal']}: isi sama {r0.get('isi_sama')} ({r0.get('irisan')}/{r0.get('jumlah_isi')}), lolos {r0.get('lolos_paper')} vs {r0.get('lolos_backtest')}; "
            f"H22 paper {porto['h22']['return_paper']}% vs backtest {porto['h22']['return_backtest']}%; "
            f"H29 paper {h29s.get('return_paper')}% vs replay {h29s.get('return_replay')}% (persentil Monte Carlo {(h29s.get('mc') or {}).get('persentil_paper')}); tak terjelaskan {len(tak)}")
