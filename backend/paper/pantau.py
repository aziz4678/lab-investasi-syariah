import json
import os
import re
import subprocess
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from pymongo import MongoClient

from backend.core.config import ROOT
from backend.db import harga as hg
from backend.db import koneksi as kdb

ID_ZONA = "h11a_v1"
ID_ZONA_H29 = "h29_v1"
BATAS_DD = -45.0
T_BUG = 5
BATAS_CADANGAN = 0.10
DB_REK = "swing_pantau_rek"
K_ZONA, K_POSISI, K_INSIDEN, K_BATAS = "pantau_zona", "pantau_posisi_h11a", "pantau_insiden", "pantau_batas"
ATURAN_PANTAU = [
    f"Bug eksekusi (dikunci 2026-11-07, keputusan user): cek ulang paper menemukan beda di transaksi, posisi, ekuitas, sinyal, atau status (pembulatan nilai JII tidak dihitung), "
    f"atau perbandingan dengan mesin backtest menemukan keputusan berbeda padahal data masukannya sama, dan dalam {T_BUG} hari bursa sesudah hari ditemukan tidak terjelaskan. "
    f"Kalau sampai hari bursa ke-{T_BUG + 1} belum ada penjelasan, syarat GAGAL 'bug eksekusi' H11a/H29 terpenuhi.",
    f"Kelengkapan data (dikunci 2026-11-07): kalau lebih dari {BATAS_CADANGAN * 100:.0f}% hari paper memakai cadangan Yahoo (data IDX resmi belum lengkap), hasil evaluasi diberi catatan.",
    "Zona normal H29 (h29_v1, dikunci 2026-11-07) hanya laporan WASPADA, bukan syarat GAGAL (keputusan user 2026-11-07).",
    "Selisih dengan mesin backtest (u2_v1 untuk H11a, u2_h22_v1 untuk H22/H29, dikunci 2026-11-07): keluar dari p99 / pita p1-p99 historis IDX vs Yahoo = WASPADA DATA, bukan GAGAL; selisih harga di atas p99 hanya dicatat.",
    "Catatan zona harian disimpan sekali per hari dan tidak ditimpa. Hari yang diisi mundur diberi tanda 'isi mundur'.",
]


def db():
    return kdb.koneksi()


def tgl_str(v):
    return str(pd.Timestamp(v).date())


def rugi_beruntun_terpanjang(net):
    terpanjang = jalan = 0
    for x in net:
        jalan = jalan + 1 if x <= 0 else 0
        terpanjang = max(terpanjang, jalan)
    return terpanjang


def zona_h11a(b, modal, nilai, net):
    nilai = np.asarray(nilai, dtype=float)
    puncak = np.maximum.accumulate(np.maximum(nilai, modal))
    ret = (nilai / modal - 1) * 100
    dd = np.minimum.accumulate(nilai / puncak - 1) * 100
    h = len(nilai) - 1
    beruntun = rugi_beruntun_terpanjang(net)
    hasil = {"zona": "belum", "alasan": [], "batas": None, "ret": ret, "dd": dd, "hari": h, "trade": len(net), "beruntun": beruntun}
    if h < 1:
        return hasil
    i = min(h, b["horizon"]) - 1
    k = min(len(net), len(b["beruntun"]["p95"]))
    batas = {"ret_p5": b["return"]["p5"][i], "ret_p1": b["return"]["p1"][i], "dd_p5": b["dd"]["p5"][i], "dd_p1": b["dd"]["p1"][i],
             "beruntun_p95": b["beruntun"]["p95"][k - 1] if k else None, "beruntun_p99": b["beruntun"]["p99"][k - 1] if k else None,
             "ret_p50": b["return"]["p50"][i]}
    r, d_ = float(ret[-1]), float(dd[-1])
    gagal, waspada = [], []
    if h >= 63 and r < batas["ret_p1"]:
        gagal.append(f"return {r:.1f}% di bawah persentil 1 ({batas['ret_p1']:.1f}%)")
    elif h >= 21 and r < batas["ret_p5"]:
        waspada.append(f"return {r:.1f}% di bawah persentil 5 ({batas['ret_p5']:.1f}%)")
    if d_ < batas["dd_p1"]:
        gagal.append(f"drawdown {d_:.1f}% lebih dalam dari persentil 1 ({batas['dd_p1']:.1f}%)")
    elif d_ < batas["dd_p5"]:
        waspada.append(f"drawdown {d_:.1f}% lebih dalam dari persentil 5 ({batas['dd_p5']:.1f}%)")
    if k and beruntun > batas["beruntun_p99"]:
        gagal.append(f"rugi beruntun {beruntun}x melebihi persentil 99 ({batas['beruntun_p99']}x)")
    elif k and beruntun > batas["beruntun_p95"]:
        waspada.append(f"rugi beruntun {beruntun}x melebihi persentil 95 ({batas['beruntun_p95']}x)")
    hasil.update(zona="gagal" if gagal else "waspada" if waspada else "normal", alasan=gagal + waspada, batas=batas)
    return hasil


def zona_h29(b, nilai):
    nilai = np.asarray(nilai, dtype=float)
    modal = nilai[0]
    puncak = np.maximum.accumulate(np.maximum(nilai, modal))
    ret = (nilai / modal - 1) * 100
    dd = np.minimum.accumulate(nilai / puncak - 1) * 100
    h = len(nilai) - 1
    hasil = {"zona": "belum", "alasan": [], "batas": None, "ret": ret, "dd": dd, "hari": h}
    if h < 1 or not b:
        return hasil
    i = min(h, b["horizon"]) - 1
    batas = {"ret_p5": b["return"]["p5"][i], "ret_p50": b["return"]["p50"][i], "dd_p5": b["dd"]["p5"][i]}
    r, d_ = float(ret[-1]), float(dd[-1])
    waspada = []
    if h >= 21 and r < batas["ret_p5"]:
        waspada.append(f"return {r:.1f}% di bawah persentil 5 zona H29 ({batas['ret_p5']:.1f}%)")
    if d_ < batas["dd_p5"]:
        waspada.append(f"drawdown {d_:.1f}% lebih dalam dari persentil 5 zona H29 ({batas['dd_p5']:.1f}%)")
    hasil.update(zona="waspada" if waspada else "normal", alasan=waspada, batas=batas)
    return hasil


def hari_paper():
    return [pd.Timestamp(e["tgl"]) for e in db().paper_ekuitas.find({}, {"tgl": 1}).sort("tgl", 1)]


def umur(buka, sampai, kal):
    b, s = pd.Timestamp(buka), pd.Timestamp(sampai)
    return sum(1 for t in kal if b < t <= s)


JII_RE = re.compile(r"'jii': [^,}]+")


def beda_bermakna(sumber, beda):
    keluar = []
    for b in beda or []:
        if sumber == "cek_h22" and b.get("koleksi") == "paper_h22_ekuitas" and JII_RE.sub("", b.get("paper", "")) == JII_RE.sub("", b.get("ulang", "")):
            continue
        keluar.append(b)
    return keluar


def kejadian():
    out = {"cek_h11a": {}, "cek_h22": {}, "banding_h11a": {}, "banding_h22": {}}
    for dok in db().paper_cek.find({}, {"sampai": 1, "waktu": 1, "beda": 1}).sort("waktu", 1):
        out["cek_h11a"][tgl_str(dok["sampai"])] = beda_bermakna("cek_h11a", dok.get("beda"))
    for dok in db().paper_h22_cek.find({}, {"sampai": 1, "waktu": 1, "beda": 1}).sort("waktu", 1):
        out["cek_h22"][tgl_str(dok["sampai"])] = beda_bermakna("cek_h22", dok.get("beda"))
    for dok in db().pantau_banding.find({}, {"strategi": 1, "sampai": 1, "dibuat": 1, "tak_terjelaskan": 1}).sort("dibuat", 1):
        k = {"h11a": "banding_h11a", "h22": "banding_h22"}.get(dok.get("strategi"))
        if k:
            out[k][tgl_str(dok["sampai"])] = dok.get("tak_terjelaskan") or []
    return out


def perbarui_insiden():
    kal = hari_paper()
    if not kal:
        return []
    akhir = kal[-1]
    lama = {x["_id"]: x for x in db()[K_INSIDEN].find({})}
    hasil = []
    for sumber, per_hari in kejadian().items():
        buka = None
        for t in sorted(per_hari):
            beda = per_hari[t]
            if beda and buka is None:
                buka = {"_id": f"{sumber}:{t}", "sumber": sumber, "buka": t, "tutup": None, "contoh": [str(x)[:300] for x in beda[:5]], "jumlah": len(beda)}
            elif beda and buka is not None:
                buka["jumlah"] = max(buka["jumlah"], len(beda))
            elif not beda and buka is not None:
                buka["tutup"] = t
                hasil.append(buka)
                buka = None
        if buka is not None:
            hasil.append(buka)
    keluar = []
    for x in hasil:
        p = (lama.get(x["_id"]) or {}).get("penjelasan")
        x["penjelasan"] = p
        selesai = x["tutup"] or akhir
        x["umur_hari_bursa"] = umur(x["buka"], selesai, kal)
        umur_jelas = umur(x["buka"], p["tgl"], kal) if p else None
        if p and umur_jelas <= T_BUG:
            x["status"] = "dijelaskan"
        elif x["umur_hari_bursa"] > T_BUG:
            x["status"] = "bug_eksekusi"
        elif x["tutup"]:
            x["status"] = "selesai"
        else:
            x["status"] = "terbuka"
        x["batas_jelaskan"] = str(kal[min(len(kal) - 1, next((i for i, t in enumerate(kal) if t > pd.Timestamp(x["buka"])), len(kal) - 1) + T_BUG - 1)].date()) \
            if any(t > pd.Timestamp(x["buka"]) for t in kal) else None
        x["diperbarui"] = datetime.now()
        db()[K_INSIDEN].replace_one({"_id": x["_id"]}, x, upsert=True)
        keluar.append(x)
    return keluar


def jelaskan_insiden(id_, alasan):
    x = db()[K_INSIDEN].find_one({"_id": id_})
    if not x:
        raise KeyError(id_)
    db()[K_INSIDEN].update_one({"_id": id_}, {"$set": {"penjelasan": {"alasan": alasan, "waktu": datetime.now(), "tgl": str(datetime.now().date())}}})
    return perbarui_insiden()


def insiden_pada(insiden, sumber_awal, t):
    t = pd.Timestamp(t)
    aktif = []
    for x in insiden:
        if not x["sumber"].endswith(sumber_awal):
            continue
        if pd.Timestamp(x["buka"]) > t or (x["tutup"] and pd.Timestamp(x["tutup"]) <= t):
            continue
        aktif.append(x)
    return aktif


def cadangan_yahoo(bagian, sampai=None):
    q = {"bagian": bagian}
    if sampai is not None:
        q["tgl"] = {"$lte": pd.Timestamp(sampai).to_pydatetime()}
    dok = list(db().paper_sumber.find(q, {"idx_lengkap": 1}))
    if not dok:
        return None
    return float(np.mean([not d.get("idx_lengkap") for d in dok]))


def status_gabung(zona, dd_maks, aktif, kal, t, cadangan):
    gagal, waspada = [], []
    if zona["zona"] == "gagal":
        gagal += [f"zona {ID_ZONA}: {a}" for a in zona["alasan"]]
    elif zona["zona"] == "waspada":
        waspada += [f"zona {ID_ZONA}: {a}" for a in zona["alasan"]]
    if dd_maks is not None and dd_maks < BATAS_DD:
        gagal.append(f"drawdown {dd_maks:.1f}% lebih dalam dari {BATAS_DD:.0f}%")
    for x in aktif:
        u = umur(x["buka"], t, kal)
        jelas = x.get("penjelasan") and umur(x["buka"], x["penjelasan"]["tgl"], kal) <= T_BUG and pd.Timestamp(x["penjelasan"]["tgl"]) <= pd.Timestamp(t)
        if jelas:
            continue
        if u > T_BUG:
            gagal.append(f"bug eksekusi: {x['sumber']} sejak {x['buka']} belum terjelaskan lebih dari {T_BUG} hari bursa")
        else:
            waspada.append(f"insiden {x['sumber']} sejak {x['buka']} ({u}/{T_BUG} hari bursa)")
    if cadangan is not None and cadangan > BATAS_CADANGAN:
        waspada.append(f"{cadangan * 100:.0f}% hari memakai cadangan Yahoo (batas {BATAS_CADANGAN * 100:.0f}%)")
    return ("gagal" if gagal else "waspada" if waspada else "normal"), gagal + waspada


def banding_terakhir(strategi):
    return db()["pantau_banding"].find_one({"strategi": strategi}, sort=[("sampai", -1)])


def luar_pita(pita, j, nilai):
    i = min(j, len(pita["p1"])) - 1
    lo, hi = pita["p1"][i], pita["p99"][i]
    return (nilai < lo or nilai > hi), lo, hi


def selisih_kurva(kurva, ref, ts):
    if not kurva or ts not in kurva["tgl"]:
        return None, None
    j = kurva["tgl"].index(ts)
    p, r = kurva["paper"][j], kurva[ref][j]
    if j < 1 or p is None or r is None:
        return None, j
    return p - r, j


def data_h11a(t, dok, u2, label="WASPADA DATA"):
    alasan, catatan = [], []
    if not dok or not u2:
        return alasan, catatan
    a = u2["ambang"]
    k = dok["portofolio"]["kurva"]
    ts = tgl_str(t)
    if ts in k["tgl"]:
        j = k["tgl"].index(ts)
        jendela = set(k["tgl"][max(0, j - a["jendela"] + 1): j + 1])
        n = sum(1 for b in dok["sinyal"]["beda"] if b["tgl"] in jendela)
        if n > a["sinyal_per_21_hari"]:
            alasan.append(f"{label}: {n} sinyal beda dengan backtest dalam {a['jendela']} hari bursa terakhir (batas {a['sinyal_per_21_hari']:.0f})")
    g, j = selisih_kurva(k, "replay", ts)
    if g is not None:
        luar, lo, hi = luar_pita(a["pita_replay"], j, g)
        if luar:
            alasan.append(f"{label}: return paper - replay {g:+.2f} poin di luar pita {lo:+.2f} s/d {hi:+.2f} (hari ke-{j})")
    for tr in dok["trade"]:
        for kol, kt in (("selisih_masuk_pct", "tgl_masuk_paper"), ("selisih_keluar_pct", "tgl_keluar_paper")):
            v = tr.get(kol)
            if v is not None and abs(v) > a["harga_masuk_pct"] and tr.get(kt) and tr[kt] <= ts:
                catatan.append(f"{tr['ticker']} {tr[kt]}: harga paper beda {v:+.2f}% dari backtest (di atas p99 {a['harga_masuk_pct']}%)")
    return alasan, catatan


def data_h29(t, d11, d22, u2, u22):
    alasan, catatan = data_h11a(t, d11, u2, "WASPADA DATA (bagian Follow Tren)")
    if not d22 or not u22:
        return alasan, catatan
    b = u22["ambang"]
    ts = tgl_str(t)
    reb = [r for r in d22["rebalance"] if r.get("ada_backtest") and r.get("eksekusi") and r["eksekusi"] <= ts]
    if reb:
        r = reb[-1]
        n = sum(1 for x in r["beda"] if not x["penyebab"].startswith("koreksi"))
        if n > b["isi_rebalance_beda"]:
            alasan.append(f"WASPADA DATA: rebalance RS 12-1 sinyal {r['sinyal']} beda {n} saham dengan backtest (batas {b['isi_rebalance_beda']:.0f})")
    for nama, kurva, ref, kp in (("RS 12-1 (H22)", d22["portofolio"]["h22"]["kurva"], "backtest", "pita_h22"),
                                 ("H29", (d22["portofolio"].get("h29") or {}).get("kurva"), "replay", "pita_h29")):
        g, j = selisih_kurva(kurva, ref, ts)
        if g is not None:
            luar, lo, hi = luar_pita(b[kp], j, g)
            if luar:
                alasan.append(f"WASPADA DATA: return paper {nama} - {ref} {g:+.2f} poin di luar pita {lo:+.2f} s/d {hi:+.2f} (hari ke-{j})")
    for tr in d22["trade"]:
        v = tr.get("selisih_pct")
        if v is not None and abs(v) > b["harga_beli_pct"] and tr["tgl"] <= ts:
            catatan.append(f"{tr['ticker']} {tr['tgl']}: harga beli paper beda {v:+.2f}% dari backtest (di atas p99 {b['harga_beli_pct']}%)")
    return alasan, catatan


def gabung_status(status, alasan, tambahan):
    if tambahan and status == "normal":
        status = "waspada"
    return status, alasan + [x for x in tambahan if x not in alasan]


def catat_zona():
    from backend.paper import h29

    b = db().batas_paper.find_one({"_id": ID_ZONA})
    st = db().paper_status.find_one({"_id": "status"})
    if not b or not st:
        return 0
    ek = list(db().paper_ekuitas.find({}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
    jual = [(pd.Timestamp(t["tgl"]), t["net_pct"]) for t in db().paper_transaksi.find({"aksi": "jual"}, {"tgl": 1, "net_pct": 1}).sort("tgl", 1)]
    kal = [pd.Timestamp(e["tgl"]) for e in ek]
    insiden = list(db()[K_INSIDEN].find({}))
    u2 = db()[K_BATAS].find_one({"_id": "u2_v1", "status": "dikunci"})
    u22 = db()[K_BATAS].find_one({"_id": "u2_h22_v1", "status": "dikunci"})
    d11, d22 = banding_terakhir("h11a"), banding_terakhir("h22")
    lama_semua = {x["_id"]: x for x in db()[K_ZONA].find({})}
    sekarang = datetime.now()
    akhir = kal[-1] if kal else None
    baru = 0
    nilai = [e["ekuitas"] for e in ek]
    for j, t in enumerate(kal):
        _id = f"h11a:{t.date()}"
        lama = lama_semua.get(_id)
        dat, cat = data_h11a(t, d11, u2)
        if lama:
            if u2 and not lama.get("u2_dicek"):
                status, alasan = gabung_status(lama["status"], lama["alasan"], dat)
                db()[K_ZONA].update_one({"_id": _id}, {"$set": {"status": status, "alasan": alasan, "data_alasan": dat, "catatan_data": cat,
                                                               "u2_dicek": True, "u2_isi_mundur": True}})
            continue
        z = zona_h11a(b, st["modal_awal"], nilai[: j + 1], [n for tj, n in jual if tj <= t])
        dd_maks = float(z["dd"][-1])
        status, alasan = status_gabung(z, dd_maks, insiden_pada(insiden, "h11a", t), kal, t, cadangan_yahoo("h11a", t))
        status, alasan = gabung_status(status, alasan, dat)
        db()[K_ZONA].insert_one({"_id": _id, "strategi": "h11a", "tgl": t.to_pydatetime(), "hari": z["hari"], "zona": z["zona"], "zona_alasan": z["alasan"],
                                 "batas": z["batas"], "return_pct": round(float(z["ret"][-1]), 2), "dd_maks_pct": round(dd_maks, 2),
                                 "trade": z["trade"], "beruntun": z["beruntun"], "status": status, "alasan": alasan,
                                 "data_alasan": dat, "catatan_data": cat, "u2_dicek": bool(u2),
                                 "dicatat": sekarang, "isi_mundur": t != akhir})
        baru += 1
    data = h29.seri() or []
    bz = db()[K_BATAS].find_one({"_id": ID_ZONA_H29, "status": "dikunci"})
    kal22 = [pd.Timestamp(r["tgl"]) for r in data]
    akhir22 = kal22[-1] if kal22 else None
    for j, t in enumerate(kal22):
        _id = f"h29:{t.date()}"
        lama = lama_semua.get(_id)
        x = np.array([r["h29"] for r in data[: j + 1]], float)
        z = zona_h29(bz, x)
        if not bz:
            z["zona"] = "tanpa_zona"
        zona_alasan = [f"zona {ID_ZONA_H29} (laporan): {a}" for a in z["alasan"]]
        dat, cat = data_h29(t, d11, d22, u2, u22)
        if lama:
            ubah = {}
            status, alasan = lama["status"], lama["alasan"]
            if bz and lama.get("zona") in (None, "tanpa_zona"):
                status, alasan = gabung_status(status, alasan, zona_alasan)
                ubah.update(zona=z["zona"], zona_alasan=z["alasan"], batas=z["batas"], zona_isi_mundur=True)
            if (u2 or u22) and not lama.get("u2_dicek"):
                status, alasan = gabung_status(status, alasan, dat)
                ubah.update(data_alasan=dat, catatan_data=cat, u2_dicek=True, u2_isi_mundur=True)
            if ubah:
                db()[K_ZONA].update_one({"_id": _id}, {"$set": {**ubah, "status": status, "alasan": alasan}})
            continue
        dd_maks = float(z["dd"][-1])
        aktif = insiden_pada(insiden, "h11a", t) + insiden_pada(insiden, "h22", t)
        status, alasan = status_gabung({"zona": "normal", "alasan": []}, dd_maks, aktif, kal, t,
                                       max([c for c in (cadangan_yahoo("h11a", t), cadangan_yahoo("h22", t)) if c is not None], default=None))
        status, alasan = gabung_status(status, alasan, zona_alasan + dat)
        db()[K_ZONA].insert_one({"_id": _id, "strategi": "h29", "tgl": t.to_pydatetime(), "hari": z["hari"], "zona": z["zona"], "zona_alasan": z["alasan"],
                                 "batas": z["batas"], "return_pct": round(float(z["ret"][-1]), 2), "dd_maks_pct": round(dd_maks, 2), "status": status,
                                 "alasan": alasan, "data_alasan": dat, "catatan_data": cat, "u2_dicek": bool(u2 or u22),
                                 "dicatat": sekarang, "isi_mundur": t != akhir22})
        baru += 1
    return baru


def baris_posisi(p, tgl, close, sumber):
    stop = p.get("stop")
    hm = p.get("harga_masuk")
    ok = lambda v: v is not None and v == v
    return {"_id": f"{tgl}:{p['ticker']}", "tgl": pd.Timestamp(tgl).to_pydatetime(), "ticker": p["ticker"], "status": p.get("status"),
            "tgl_sinyal": kdb.ke_bson(p.get("tgl_sinyal")), "tgl_masuk": kdb.ke_bson(p.get("tgl_masuk")) if ok(p.get("tgl_masuk")) else None,
            "harga_masuk": float(hm) if ok(hm) else None, "lot": int(p.get("lot") or 0), "atr_sinyal": float(p["atr_sinyal"]) if ok(p.get("atr_sinyal")) else None,
            "stop": float(stop) if ok(stop) else None, "tertinggi": float(p["tertinggi"]) if ok(p.get("tertinggi")) else None, "hari": int(p.get("hari") or 0),
            "close": float(close) if ok(close) else None,
            "jarak_stop_pct": round((close / stop - 1) * 100, 2) if ok(close) and ok(stop) and stop else None,
            "untung_pct": round((close / hm - 1) * 100, 2) if ok(close) and ok(hm) and p.get("status") != "beli_besok" else None,
            "sumber": sumber, "dicatat": datetime.now()}


def catat_posisi():
    st = db().paper_status.find_one({"_id": "status"})
    if not st or not st.get("tgl_terakhir"):
        return 0
    tgl = st["tgl_terakhir"]
    pos = list(db().paper_posisi.find({}, {"_id": 0}))
    if not pos or db()[K_POSISI].find_one({"tgl": pd.Timestamp(tgl).to_pydatetime()}):
        return 0
    data = hg.paper({p["ticker"]: hg.harian(p["ticker"]) for p in pos if hg.harian(p["ticker"]) is not None})
    t = pd.Timestamp(tgl)
    baru = 0
    for p in pos:
        df = data.get(p["ticker"])
        close = float(df.at[t, "close"]) if df is not None and t in df.index else None
        db()[K_POSISI].replace_one({"_id": f"{tgl}:{p['ticker']}"}, baris_posisi(p, tgl, close, "snapshot"), upsert=True)
        baru += 1
    return baru


def rek_anak(modal, mulai, sampai):
    from backend.ingest import des_ojk
    from backend.paper import sumber_idx
    from backend.paper import tren_harian as th

    des = des_ojk.baca()
    status, posisi = th.muat_state(modal)
    mentah, ihsg = th.baca_lokal()
    if sumber_idx.AKTIF:
        mentah = sumber_idx.susun(mentah)
    awal_data = min((df.index.min() for df in mentah.values() if len(df)), default=None)
    siap = th.siapkan(mentah, ihsg, th.tutup_resmi_tanpa_transaksi(awal_data))
    kal = th.kalender_bursa(mentah)
    hari = kal[(kal >= pd.Timestamp(mulai)) & (kal <= pd.Timestamp(sampai))]
    keluar = []
    for tgl in hari:
        th.proses_hari(tgl, siap, des, status, posisi, [])
        for p in posisi:
            b = th.bar(siap, p["ticker"], tgl)
            close = float(b["m_close"]) if b is not None else None
            keluar.append(baris_posisi(dict(p), str(tgl.date()), close, "rekonstruksi"))
    th.simpan_state(status, posisi)
    db()["rek_posisi"].insert_many(keluar) if keluar else None


def rapikan(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, dict):
        return {k: rapikan(x) for k, x in v.items()}
    if isinstance(v, list):
        return [rapikan(x) for x in v]
    return v


def rekonstruksi():
    prod = db()
    if prod.name == DB_REK:
        raise SystemExit("jalankan dari db produksi")
    st = prod.paper_status.find_one({"_id": "status"})
    pertama = prod.paper_ekuitas.find_one(sort=[("tgl", 1)])
    if not st or not pertama:
        return 0
    ada = {pd.Timestamp(t) for t in prod[K_POSISI].distinct("tgl")}
    kal = hari_paper()
    if all(t in ada for t in kal):
        return 0
    klien = MongoClient(os.environ.get("SWING_MONGO_URI", "mongodb://localhost:27017"))
    klien.drop_database(DB_REK)
    rek = klien[DB_REK]
    rek.des.insert_many(list(prod.des.find({}, {"_id": 0})))
    env = {**os.environ, "SWING_MONGO_DB": DB_REK, "PYTHONIOENCODING": "utf-8"}
    hasil = subprocess.run([sys.executable, "-m", "backend.paper.pantau", "rek_anak", str(st["modal_awal"]), str(pertama["tgl"].date()), st["tgl_terakhir"]],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        if hasil.returncode != 0:
            print(hasil.stdout[-1500:], hasil.stderr[-1500:])
            raise RuntimeError("rekonstruksi jejak posisi gagal")
        a = sorted((rapikan({k: v for k, v in p.items() if k != "_id"}) for p in prod.paper_posisi.find({})), key=lambda x: x["ticker"])
        b = sorted((rapikan({k: v for k, v in p.items() if k != "_id"}) for p in rek.paper_posisi.find({})), key=lambda x: x["ticker"])
        ea = [rapikan({k: v for k, v in e.items() if k != "_id"}) for e in prod.paper_ekuitas.find({}).sort("tgl", 1)]
        eb = [rapikan({k: v for k, v in e.items() if k != "_id"}) for e in rek.paper_ekuitas.find({}).sort("tgl", 1)]
        if a != b or ea != eb:
            print("rekonstruksi TIDAK identik dengan paper tersimpan; jejak mundur tidak ditulis")
            return 0
        baru = 0
        for x in rek["rek_posisi"].find({}):
            if pd.Timestamp(x["tgl"]) in ada:
                continue
            prod[K_POSISI].replace_one({"_id": x["_id"]}, x, upsert=True)
            baru += 1
        return baru
    finally:
        klien.drop_database(DB_REK)


def keadaan():
    z = {s: list(db()[K_ZONA].find({"strategi": s}, {"_id": 0}).sort("tgl", 1)) for s in ("h11a", "h29")}
    out = {}
    for s, xs in z.items():
        pertama = lambda st: next((tgl_str(x["tgl"]) for x in xs if x["status"] == st), None)
        out[s] = {"hari": len(xs), "terakhir": xs[-1] if xs else None, "pernah_waspada": pertama("waspada"), "pernah_gagal": pertama("gagal"),
                  "riwayat": [{"tgl": tgl_str(x["tgl"]), "status": x["status"], "zona": x.get("zona"), "alasan": x.get("alasan"),
                               "return_pct": x.get("return_pct"), "dd_maks_pct": x.get("dd_maks_pct"), "isi_mundur": x.get("isi_mundur")} for x in xs]}
    out["insiden"] = list(db()[K_INSIDEN].find({}).sort("buka", -1))
    out["cadangan"] = {"h11a": cadangan_yahoo("h11a"), "h22": cadangan_yahoo("h22"), "batas": BATAS_CADANGAN}
    out["aturan"] = ATURAN_PANTAU
    out["t_bug"] = T_BUG
    return out


def harian():
    from backend.paper import banding

    print("1. jejak posisi H11a")
    n = catat_posisi()
    print(f"   snapshot hari ini: {n} posisi")
    try:
        n = rekonstruksi()
        print(f"   isi mundur (rekonstruksi, dicek identik): {n} baris")
    except Exception as e:
        print(f"   rekonstruksi gagal: {e}")
    print("2. bandingkan dengan mesin backtest")
    for nama, fungsi in (("H11a", banding.h11a), ("H22/H29", banding.h22)):
        try:
            r = fungsi()
            print(f"   {nama}: {r}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"   {nama}: GAGAL dihitung ({e})")
    print("3. insiden")
    ins = perbarui_insiden()
    for x in ins:
        print(f"   {x['_id']}: {x['status']} ({x['umur_hari_bursa']} hari bursa)")
    if not ins:
        print("   tidak ada")
    print("4. catatan zona harian (aturan lama h11a_v1 / h29_v1, pembanding)")
    print(f"   baru: {catat_zona()}")
    from backend.paper import aturan_v2
    print("5. catatan status aturan v2 (h11a_v2 / h29_v2)")
    print(f"   baru: {aturan_v2.catat()}")
    k = keadaan()
    for s in ("h11a", "h29"):
        t = k[s]["terakhir"]
        if t:
            print(f"   {s.upper()} {tgl_str(t['tgl'])}: {t['status'].upper()} {'; '.join(t['alasan']) or ''} | pernah waspada {k[s]['pernah_waspada'] or '-'}, pernah gagal {k[s]['pernah_gagal'] or '-'}")
    print("SELESAI")


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else "harian"
    if perintah == "rek_anak":
        rek_anak(float(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif perintah == "zona":
        from backend.paper import aturan_v2
        perbarui_insiden()
        print(catat_zona(), aturan_v2.catat())
    elif perintah == "posisi":
        print(catat_posisi(), rekonstruksi())
    else:
        harian()
