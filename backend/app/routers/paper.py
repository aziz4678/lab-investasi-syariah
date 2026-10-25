from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Query

from backend.app.jobs import pekerjaan as pk
from backend.app.services import pasar as ps
from backend.db import cadangan as cd
from backend.db import data as dt
from backend.db import koneksi as d

router = APIRouter(prefix="/api")
DB = d.koneksi()
MULT_ATR = 3.0


def bersih(dok):
    dok.pop("_id", None)
    return dok


def harga(ticker):
    x = dt.baca(f"harian/{ticker}", kolom=["close"])
    return None if x is None else x["close"].dropna()


def stat_transaksi():
    tr = list(DB.paper_transaksi.find({}, {"_id": 0}))
    jual = [t for t in tr if t["aksi"] == "jual"]
    net = np.array([t["net_pct"] for t in jual]) if jual else np.array([])
    return {
        "trade_selesai": len(jual), "win_rate": float((net > 0).mean() * 100) if len(net) else None,
        "rata_net": float(net.mean()) if len(net) else None,
        "rata_menang": float(net[net > 0].mean()) if (net > 0).any() else None,
        "rata_kalah": float(net[net <= 0].mean()) if (net <= 0).any() else None,
        "untung_rp": float(sum(t["untung_rp"] or 0 for t in jual)),
        "dividen_rp": float(sum(t["untung_rp"] or 0 for t in tr if t["aksi"] == "dividen")),
        "batal": sum(1 for t in tr if str(t["aksi"]).startswith("batal")),
    }


@router.get("/paper/ringkasan")
def paper_ringkasan():
    status = DB.paper_status.find_one({"_id": "status"}, {"_id": 0})
    if not status:
        return {"mulai": False}
    terakhir = DB.paper_ekuitas.find_one(sort=[("tgl", -1)], projection={"_id": 0})
    pertama = DB.paper_ekuitas.find_one(sort=[("tgl", 1)], projection={"_id": 0})
    posisi = []
    batas = pd.Timestamp(status["tgl_terakhir"]) if status.get("tgl_terakhir") else None
    for p in DB.paper_posisi.find({}, {"_id": 0}):
        h = harga(p["ticker"])
        if h is not None and batas is not None:
            h = h[h.index <= batas]
        close = float(h.iloc[-1]) if h is not None and len(h) else None
        p["close"] = close
        p["tgl_close"] = h.index[-1].to_pydatetime() if h is not None and len(h) else None
        if p["status"] in ("aktif", "jual_besok") and close and p.get("harga_masuk"):
            p["untung_pct"] = (close / p["harga_masuk"] - 1) * 100
            p["jarak_stop_pct"] = (close / p["stop"] - 1) * 100 if p.get("stop") else None
            p["nilai_rp"] = close * p["lot"] * 100
        if p["status"] == "beli_besok" and h is not None and p.get("tgl_sinyal") in h.index:
            c = float(h.loc[p["tgl_sinyal"]])
            p["close_sinyal"] = c
            p["stop_awal_perkiraan"] = c - MULT_ATR * p["atr_sinyal"]
            p["stop_awal_pct"] = -MULT_ATR * p["atr_sinyal"] / c * 100
        posisi.append(p)
    return {
        "mulai": True, "modal_awal": status["modal_awal"], "kas": status["kas"], "tgl_terakhir": status["tgl_terakhir"],
        "tgl_mulai": pertama["tgl"] if pertama else None,
        "ekuitas": terakhir["ekuitas"] if terakhir else status["modal_awal"],
        "return_pct": (terakhir["ekuitas"] / status["modal_awal"] - 1) * 100 if terakhir else 0.0,
        "posisi": sorted(posisi, key=lambda x: ({"jual_besok": 0, "beli_besok": 1, "aktif": 2}.get(x["status"], 3), x["ticker"])),
        **stat_transaksi(),
    }


@router.get("/paper/ekuitas")
def paper_ekuitas():
    e = list(DB.paper_ekuitas.find({}, {"_id": 0}).sort("tgl", 1))
    if not e:
        return []
    h = dt.baca("harian/_ihsg")
    if h is not None:
        ih = h["ihsg"]
        awal = ih[ih.index <= e[0]["tgl"]]
        dasar = float(awal.iloc[-1]) if len(awal) else None
        for x in e:
            s = ih[ih.index <= x["tgl"]]
            x["ihsg"] = float(s.iloc[-1] / dasar * e[0]["ekuitas"]) if dasar and len(s) else None
    puncak = 0
    for x in e:
        puncak = max(puncak, x["ekuitas"])
        x["drawdown"] = (x["ekuitas"] / puncak - 1) * 100
    return e


@router.get("/paper/transaksi")
def paper_transaksi(batas: int = Query(500, le=5000)):
    return list(DB.paper_transaksi.find({}, {"_id": 0}).sort([("tgl", -1)]).limit(batas))


@router.get("/paper/sinyal")
def paper_sinyal(batas: int = Query(30, le=500)):
    return list(DB.paper_sinyal.find({}, {"_id": 0}).sort([("tgl", -1)]).limit(batas))


@router.post("/aksi/paper_mulai")
def aksi_paper_mulai(modal: float = Body(100_000_000, embed=True)):
    if DB.paper_status.find_one({"_id": "status"}):
        raise HTTPException(409, "paper trade sudah berjalan; reset dulu kalau mau mulai ulang")
    if not 1_000_000 <= modal <= 100_000_000_000:
        raise HTTPException(422, "modal harus antara Rp1 jt dan Rp100 M")
    id_, baru = pk.mulai("paper_harian", ["--modal", int(modal)])
    return {"id": id_, "baru": baru}


@router.get("/paper/cek")
def paper_cek(batas: int = Query(5, le=50)):
    return [bersih(x) for x in DB.paper_cek.find({}, {"_id": 0}).sort("waktu", -1).limit(batas)]


def rugi_beruntun_terpanjang(net):
    terpanjang = jalan = 0
    for x in net:
        jalan = jalan + 1 if x <= 0 else 0
        terpanjang = max(terpanjang, jalan)
    return terpanjang


@router.get("/paper/zona")
def paper_zona():
    b = DB.batas_paper.find_one({"_id": "h11a_v1"})
    if not b:
        return {"ada": False}
    status = DB.paper_status.find_one({"_id": "status"})
    ek = list(DB.paper_ekuitas.find({}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
    hasil = {"ada": True, "dibuat": b["dibuat"], "sumber": b["sumber"], "aturan": b["aturan"], "horizon": b["horizon"],
             "return": b["return"], "dd": b["dd"], "kurva": b["kurva"], "zona": "belum", "alasan": [], "paper": None}
    if not status or not ek:
        return hasil
    modal = status["modal_awal"]
    nilai = np.array([e["ekuitas"] for e in ek], dtype=float)
    puncak = np.maximum.accumulate(np.maximum(nilai, modal))
    ret = (nilai / modal - 1) * 100
    dd = np.minimum.accumulate(nilai / puncak - 1) * 100
    net = [t["net_pct"] for t in DB.paper_transaksi.find({"aksi": "jual"}, {"net_pct": 1}).sort("tgl", 1)]
    h = len(nilai) - 1
    beruntun = rugi_beruntun_terpanjang(net)
    hasil["paper"] = {"tgl": [e["tgl"].strftime("%Y-%m-%d") for e in ek], "return": np.round(ret, 2).tolist(), "dd": np.round(dd, 2).tolist(),
                      "hari": h, "trade": len(net), "beruntun": beruntun}
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


@router.post("/aksi_paper_reset")
def aksi_paper_reset(konfirmasi: str = Body(..., embed=True)):
    if konfirmasi != "RESET":
        raise HTTPException(422, "ketik RESET untuk konfirmasi")
    if DB.pekerjaan.find_one({"jenis": "paper_harian", "status": "berjalan"}):
        raise HTTPException(409, "pembaruan paper sedang berjalan, tunggu selesai")
    status = DB.paper_status.find_one({"_id": "status"}) or {}
    cd.buat("otomatis sebelum reset paper")
    sesi = status.get("sesi") or datetime.now().strftime("%Y%m%d-%H%M%S")
    sekarang = datetime.now()
    arsip = {}
    for k in ["paper_status", "paper_posisi", "paper_transaksi", "paper_ekuitas", "paper_sinyal"]:
        dok = list(DB[k].find({}, {"_id": 0}))
        if dok:
            DB["arsip_" + k].insert_many([{**x, "sesi": sesi, "diarsip": sekarang} for x in dok])
        arsip[k] = len(dok)
        DB[k].delete_many({})
    return {"sesi": sesi, "diarsip": arsip}


@router.get("/paper/arsip")
def paper_arsip():
    hasil = []
    for s in DB.arsip_paper_status.find({}, {"_id": 0}).sort("diarsip", -1):
        e = list(DB.arsip_paper_ekuitas.find({"sesi": s["sesi"]}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
        hasil.append({"sesi": s["sesi"], "modal_awal": s.get("modal_awal"), "diarsip": s["diarsip"],
                      "mulai": e[0]["tgl"] if e else None, "akhir": e[-1]["tgl"] if e else None, "hari": len(e),
                      "ekuitas_akhir": e[-1]["ekuitas"] if e else None,
                      "trade": DB.arsip_paper_transaksi.count_documents({"sesi": s["sesi"], "aksi": "jual"})})
    return hasil


@router.get("/paper/langsung")
def paper_langsung():
    status = DB.paper_status.find_one({"_id": "status"}, {"_id": 0})
    if not status:
        return {"ada": False}
    posisi = list(DB.paper_posisi.find({}, {"_id": 0, "ticker": 1, "status": 1, "lot": 1, "stop": 1, "harga_masuk": 1}))
    try:
        kini = ps.harga_kini([p["ticker"] for p in posisi])
    except Exception:
        kini = {}
    dipegang = [p for p in posisi if p["status"] in ("aktif", "jual_besok")]
    lengkap = all(p["ticker"] in kini for p in dipegang)
    nilai = sum(kini[p["ticker"]]["harga"] * p["lot"] * 100 for p in dipegang if p["ticker"] in kini)
    sesi = max((x["sesi"] for x in kini.values()), default=None)
    jam = max((x["jam"] for x in kini.values() if x["sesi"] == sesi), default=None)
    out = {}
    for p in posisi:
        x = kini.get(p["ticker"])
        if not x:
            continue
        out[p["ticker"]] = {**x, "di_bawah_stop": bool(p.get("stop") and x["harga"] < p["stop"]),
                            "jarak_stop_pct": (x["harga"] / p["stop"] - 1) * 100 if p.get("stop") else None,
                            "untung_pct": (x["harga"] / p["harga_masuk"] - 1) * 100 if p.get("harga_masuk") and p["status"] != "beli_besok" else None}
    return {"ada": True, "sesi": sesi, "jam": jam, "lengkap": lengkap, "posisi": out,
            "ekuitas": status["kas"] + nilai if lengkap else None, "modal_awal": status["modal_awal"]}
