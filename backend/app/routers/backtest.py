from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from backend.db import koneksi as d

router = APIRouter(prefix="/api")
DB = d.koneksi()


@router.get("/versi")
def daftar_versi():
    kolom = {"_id": 0, "versi": 1, "label": 1, "cagr": 1, "dd_maks": 1, "win_rate": 1, "trade": 1, "mulai": 1, "akhir": 1, "monte_carlo": 1}
    return list(DB.backtest_ringkasan.find({}, kolom).sort("versi", 1))


@router.get("/ringkasan/{versi}")
def ringkasan(versi: str):
    dok = DB.backtest_ringkasan.find_one({"versi": versi}, {"_id": 0})
    if not dok:
        raise HTTPException(404, f"versi {versi} tidak ada")
    return dok


@router.get("/ekuitas/{versi}")
def ekuitas(versi: str):
    return list(DB.backtest_ekuitas.find({"versi": versi}, {"_id": 0, "versi": 0}).sort("bulan", 1))


@router.get("/trade/{versi}")
def trade(versi: str, tahun: int | None = None, ticker: str | None = None, hanya_dipilih: bool = True,
          status: str | None = None, batas: int = Query(5000, le=20000)):
    q = {"versi": versi}
    if hanya_dipilih:
        q["dipilih"] = True
    if ticker:
        q["ticker"] = ticker.upper()
    if status:
        q["status"] = status
    if tahun:
        q["tgl_sinyal"] = {"$gte": datetime(tahun, 1, 1), "$lt": datetime(tahun + 1, 1, 1)}
    return list(DB.backtest_trade.find(q, {"_id": 0, "versi": 0}).sort("tgl_sinyal", 1).limit(batas))


@router.get("/distribusi/{versi}")
def distribusi(versi: str):
    net = np.array([t["net"] for t in DB.backtest_trade.find({"versi": versi, "dipilih": True}, {"net": 1})])
    if not len(net):
        return []
    tepi = [-100, -30, -20, -15, -10, -5, 0, 5, 10, 20, 50, 100, 10000]
    hit, _ = np.histogram(net, bins=tepi)
    label = ["< -30", "-30..-20", "-20..-15", "-15..-10", "-10..-5", "-5..0", "0..5", "5..10", "10..20", "20..50", "50..100", "> 100"]
    return [{"rentang": l, "jumlah": int(h)} for l, h in zip(label, hit)]
