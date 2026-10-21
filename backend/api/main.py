from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.api import pekerjaan as pk
from backend.db import data as dt
from backend.api import emiten as em
from backend.api import jadwal as jd
from backend.db import cadangan as cd
from backend.api import riset as rs
from backend.api import hipotesis as hps
from backend.api import strategi as st
from backend.api import sumber_data as sd
from backend.api import valuasi as vl
from backend.api import profil as pf
from backend.api import pasar as ps
from backend.api import dividen as dvn
from backend.api import reksadana as rdn
from backend.api import etf as etfn
from backend.api import pengumuman as pgm
from backend.api import orang_dalam as odl
from backend.api import berita as brt
from backend.api import makro as mkr
from backend.api import indeks as idk
from backend.db import koneksi as d

app = FastAPI(title="Lab Syariah API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])
DB = d.koneksi()
pk.bersihkan_yatim()
ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
MULT_ATR = 3.0


def bersih(dok):
    dok.pop("_id", None)
    return dok


@app.get("/api/versi")
def daftar_versi():
    kolom = {"_id": 0, "versi": 1, "label": 1, "cagr": 1, "dd_maks": 1, "win_rate": 1, "trade": 1, "mulai": 1, "akhir": 1}
    return list(DB.backtest_ringkasan.find({}, kolom).sort("versi", 1))


@app.get("/api/ringkasan/{versi}")
def ringkasan(versi: str):
    dok = DB.backtest_ringkasan.find_one({"versi": versi}, {"_id": 0})
    if not dok:
        raise HTTPException(404, f"versi {versi} tidak ada")
    return dok


@app.get("/api/ekuitas/{versi}")
def ekuitas(versi: str):
    return list(DB.backtest_ekuitas.find({"versi": versi}, {"_id": 0, "versi": 0}).sort("bulan", 1))


@app.get("/api/trade/{versi}")
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


@app.get("/api/distribusi/{versi}")
def distribusi(versi: str):
    net = np.array([t["net"] for t in DB.backtest_trade.find({"versi": versi, "dipilih": True}, {"net": 1})])
    if not len(net):
        return []
    tepi = [-100, -30, -20, -15, -10, -5, 0, 5, 10, 20, 50, 100, 10000]
    hit, _ = np.histogram(net, bins=tepi)
    label = ["< -30", "-30..-20", "-20..-15", "-15..-10", "-10..-5", "-5..0", "0..5", "5..10", "10..20", "20..50", "50..100", "> 100"]
    return [{"rentang": l, "jumlah": int(h)} for l, h in zip(label, hit)]


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


@app.get("/api/paper/ringkasan")
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


@app.get("/api/paper/ekuitas")
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


@app.get("/api/paper/transaksi")
def paper_transaksi(batas: int = Query(500, le=5000)):
    return list(DB.paper_transaksi.find({}, {"_id": 0}).sort([("tgl", -1)]).limit(batas))


@app.get("/api/paper/sinyal")
def paper_sinyal(batas: int = Query(30, le=500)):
    return list(DB.paper_sinyal.find({}, {"_id": 0}).sort([("tgl", -1)]).limit(batas))


@app.post("/api/aksi/paper_mulai")
def aksi_paper_mulai(modal: float = Body(100_000_000, embed=True)):
    if DB.paper_status.find_one({"_id": "status"}):
        raise HTTPException(409, "paper trade sudah berjalan; reset dulu kalau mau mulai ulang")
    if not 1_000_000 <= modal <= 100_000_000_000:
        raise HTTPException(422, "modal harus antara Rp1 jt dan Rp100 M")
    id_, baru = pk.mulai("paper_harian", ["--modal", int(modal)])
    return {"id": id_, "baru": baru}


@app.post("/api/aksi/{jenis}")
def aksi(jenis: str):
    if jenis not in pk.PERINTAH:
        raise HTTPException(404, f"aksi {jenis} tidak dikenal")
    if jenis == "paper_harian" and not DB.paper_status.find_one({"_id": "status"}):
        raise HTTPException(409, "paper trade belum dimulai")
    if jenis == "pulihkan":
        raise HTTPException(422, "pakai /api/aksi_pulihkan")
    if jenis == "otomatis":
        raise HTTPException(422, "pakai /api/otomatis/{sumber}")
    try:
        id_, baru = pk.mulai(jenis)
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@app.post("/api/aksi_pulihkan")
def aksi_pulihkan(nama: str = Body(...), konfirmasi: str = Body(...)):
    if konfirmasi != "PULIHKAN":
        raise HTTPException(422, "ketik PULIHKAN untuk konfirmasi")
    if nama not in {b["nama"] for b in cd.daftar()}:
        raise HTTPException(404, "backup tidak ditemukan")
    try:
        id_, baru = pk.mulai("pulihkan", [nama])
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@app.get("/api/cadangan")
def daftar_cadangan():
    return cd.daftar()


@app.get("/api/jadwal")
def status_jadwal():
    return jd.status()


@app.post("/api/aksi_jadwal")
def aksi_jadwal(aktif: bool = Body(..., embed=True)):
    try:
        return jd.pasang() if aktif else jd.lepas()
    except RuntimeError as e:
        raise HTTPException(500, f"gagal mengatur Task Scheduler: {e}")


@app.get("/api/paper/cek")
def paper_cek(batas: int = Query(5, le=50)):
    return [bersih(x) for x in DB.paper_cek.find({}, {"_id": 0}).sort("waktu", -1).limit(batas)]


def rugi_beruntun_terpanjang(net):
    terpanjang = jalan = 0
    for x in net:
        jalan = jalan + 1 if x <= 0 else 0
        terpanjang = max(terpanjang, jalan)
    return terpanjang


@app.get("/api/paper/zona")
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


@app.post("/api/aksi_paper_reset")
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


@app.get("/api/paper/arsip")
def paper_arsip():
    hasil = []
    for s in DB.arsip_paper_status.find({}, {"_id": 0}).sort("diarsip", -1):
        e = list(DB.arsip_paper_ekuitas.find({"sesi": s["sesi"]}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
        hasil.append({"sesi": s["sesi"], "modal_awal": s.get("modal_awal"), "diarsip": s["diarsip"],
                      "mulai": e[0]["tgl"] if e else None, "akhir": e[-1]["tgl"] if e else None, "hari": len(e),
                      "ekuitas_akhir": e[-1]["ekuitas"] if e else None,
                      "trade": DB.arsip_paper_transaksi.count_documents({"sesi": s["sesi"], "aksi": "jual"})})
    return hasil


@app.get("/api/pekerjaan")
def daftar_pekerjaan(batas: int = Query(10, le=100)):
    return pk.terbaru(batas)


@app.get("/api/pekerjaan/{id_}")
def satu_pekerjaan(id_: str):
    p = pk.ambil(id_)
    if not p:
        raise HTTPException(404, "pekerjaan tidak ada")
    return p


@app.get("/api/strategi")
def daftar_strategi():
    return st.semua()


@app.get("/api/chrome_lab")
def chrome_lab_status():
    from backend.riset import chrome_lab
    return chrome_lab.status()


@app.post("/api/chrome_lab/buka")
def chrome_lab_buka():
    from backend.riset import chrome_lab
    try:
        return {"hasil": chrome_lab.buka(), **chrome_lab.status()}
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@app.post("/api/otomatis/{sumber}")
def otomatis(sumber: str):
    s = next((x for x in sd.SUMBER if x["id"] == sumber and x.get("cara") == "browser"), None)
    if not s:
        raise HTTPException(404, "sumber tidak dikenal atau bukan lewat browser")
    try:
        id_, baru = pk.mulai("otomatis", [sumber])
    except pk.Bentrok as e:
        raise HTTPException(409, str(e))
    return {"id": id_, "baru": baru}


@app.get("/api/sumber_data")
def daftar_sumber_data():
    return sd.status()


@app.get("/api/skrip/{nama}", response_class=PlainTextResponse)
def skrip_browser(nama: str):
    isi = sd.skrip(nama)
    if isi is None:
        raise HTTPException(404, "skrip tidak dikenal")
    return isi


@app.get("/api/hipotesis")
def hipotesis():
    return hps.semua()


@app.get("/api/riset")
def riset():
    return {"tahap": rs.TAHAP, "hipotesis": rs.HIPOTESIS, "kriteria": rs.KRITERIA}


@app.get("/api/emiten")
def daftar_emiten():
    return em.daftar()


@app.get("/api/profil/{kode}")
def profil_emiten_info(kode: str):
    return pf.profil(kode)


@app.get("/api/dividen/daftar")
def dividen_daftar():
    return dvn.daftar()


@app.get("/api/logo/ada")
def logo_ada():
    return sorted(x["_id"] for x in dt.db().logo_info.find({"ada": True}, {"_id": 1}))


@app.get("/api/logo/{jenis}/{kunci}")
def logo(jenis: str, kunci: str):
    if jenis not in ("emiten", "mi", "etf", "negara"):
        raise HTTPException(404, "jenis logo tidak dikenal")
    isi, tipe = dt.baca_arsip_jenis(f"logo/{jenis}/{kunci}")
    if isi is None:
        raise HTTPException(404, "logo tidak ada")
    return Response(content=isi, media_type=tipe, headers={"Cache-Control": "public, max-age=604800"})


@app.get("/api/etf/daftar")
def etf_daftar():
    return etfn.daftar()


@app.get("/api/etf/luar")
def etf_luar():
    return etfn.daftar_luar()


@app.get("/api/etf/pilihan")
def etf_pilihan():
    return etfn.pilihan()


@app.get("/api/etf/banding")
def etf_banding(kode: str = Query(...), periode: str = Query("5y"), rupiah: bool = Query(False)):
    return etfn.banding([k.strip().upper() for k in kode.split(",") if k.strip()], periode, rupiah)


@app.get("/api/etf/luar/detail/{kode}")
def etf_luar_detail(kode: str):
    x = etfn.detail_luar(kode.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x


@app.get("/api/etf/luar/intraday/{kode}")
def etf_luar_intraday(kode: str):
    try:
        return ps.intraday_luar(kode.upper().strip())
    except Exception:
        return None


@app.get("/api/etf/luar/grafik/{kode}")
def etf_luar_grafik(kode: str, banding: str = Query("SPY")):
    x = etfn.grafik_luar(kode.upper(), banding.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x


@app.get("/api/etf/grafik/{kode}")
def etf_grafik(kode: str):
    x = etfn.grafik(kode.upper())
    if x is None:
        raise HTTPException(404, "ETF tidak ditemukan")
    return x


@app.get("/api/orang_dalam/{kode}")
def orang_dalam(kode: str, hari: int = 90):
    return odl.detail(kode, min(max(hari, 7), 400))


@app.get("/api/berita/{kode}")
def berita(kode: str):
    return brt.daftar(kode)


@app.get("/api/makro")
def makro():
    return mkr.ringkas()


@app.get("/api/indeks/{kode}")
def indeks_emiten(kode: str):
    return idk.anggota(kode)


@app.get("/api/pengumuman")
def pengumuman_daftar(kode: str | None = None, kategori: str | None = "penting", halaman: int = 0, ukuran: int = 25):
    return pgm.daftar(kode, kategori, max(0, halaman), min(max(ukuran, 5), 100))


@app.get("/api/rd/daftar")
def rd_daftar():
    return rdn.daftar()


@app.get("/api/rd/kategori")
def rd_kategori():
    return rdn.ringkas_kategori()


@app.get("/api/rd/produk/{fid}")
def rd_produk(fid: int):
    x = rdn.detail(fid)
    if x is None:
        raise HTTPException(404, "reksa dana tidak ditemukan")
    return x


@app.get("/api/rd/sukuk")
def rd_sukuk():
    return rdn.sukuk()


@app.get("/api/rd/sukuk/{kode}")
def rd_sukuk_riwayat(kode: str):
    x = rdn.sukuk_riwayat(kode.upper())
    if x is None:
        raise HTTPException(404, "Sukuk tidak ditemukan")
    return x


@app.get("/api/rd/banding")
def rd_banding():
    return rdn.banding()


@app.get("/api/rd/alokasi")
def rd_alokasi(profil: str = Query("moderat"), modal: float = Query(100_000_000, gt=0, le=1e13)):
    return rdn.alokasi(profil, modal)


@app.get("/api/dividen/paper")
def dividen_paper():
    return dvn.paper()


@app.get("/api/dividen/pengingat")
def dividen_pengingat(hari: int = Query(7, ge=1, le=60)):
    return dvn.pengingat(hari)


@app.get("/api/dividen/jadwal")
def dividen_jadwal():
    return dvn.jadwal()


@app.get("/api/dividen/ringkasan")
def dividen_ringkasan():
    return dvn.ringkasan()


@app.get("/api/dividen/kalkulator")
def dividen_kalkulator(kode: str = Query(...)):
    return dvn.kalkulator(kode.split(","))


@app.get("/api/dividen/emiten/{kode}")
def dividen_emiten(kode: str):
    return dvn.emiten(kode)


@app.get("/api/valuasi/{kode}")
def valuasi_emiten(kode: str):
    return vl.hitung(kode)


@app.get("/api/emiten/{kode}")
def profil_emiten(kode: str):
    p = em.profil(kode)
    if p is None:
        raise HTTPException(404, f"Data harga {kode.upper()} tidak ada")
    return p


@app.get("/api/pasar")
def pasar_ringkasan():
    return ps.ringkasan()


@app.get("/api/pasar/intraday")
def pasar_intraday(kode: str | None = None):
    try:
        return ps.intraday(kode.upper().strip() if kode else None)
    except Exception:
        return None


@app.get("/api/paper/langsung")
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


@app.get("/api/status")
def status_data():
    sekarang = datetime.now()
    hasil = {"sekarang": sekarang, "bursa_buka": sekarang.weekday() < 5 and 9 <= sekarang.hour < 16,
             "data_final": not (sekarang.weekday() < 5 and sekarang.hour < 17)}
    h = dt.baca("harian/_ihsg")
    if h is not None:
        ih = h["ihsg"].dropna()
        hasil["harga_terakhir"] = ih.index[-1].to_pydatetime()
        hasil["ihsg"] = float(ih.iloc[-1])
        hasil["ihsg_20h"] = float((ih.iloc[-1] / ih.iloc[-21] - 1) * 100) if len(ih) > 21 else None
        hasil["ihsg_di_atas_ema200"] = bool(ih.iloc[-1] > ih.ewm(span=200, adjust=False).mean().iloc[-1])
    des = DB.des.find_one(sort=[("mulai", -1)])
    if des:
        hasil["des_periode"] = des["kep"]
        hasil["des_mulai"] = des["mulai"]
        hasil["des_saham"] = DB.des.count_documents({"mulai": des["mulai"]})
        hasil["des_perlu_update"] = (sekarang - des["mulai"]).days > 190 or jd.perlu_cek_des(sekarang.date())
    cek_des = DB.penanda.find_one({"_id": "des_cek"})
    hasil["des_dicek"] = cek_des["isi"] if cek_des else None
    cek = DB.paper_cek.find_one(sort=[("waktu", -1)])
    hasil["paper_cek"] = {"waktu": cek["waktu"], "cocok": cek["cocok"], "jumlah_beda": cek["jumlah_beda"], "sampai": cek["sampai"]} if cek else None
    cad = cd.daftar()
    hasil["backup_terakhir"] = cad[0]["waktu"] if cad else None
    try:
        hasil["data_perlu"] = sd.jumlah_perlu()
    except Exception:
        hasil["data_perlu"] = None
    tahun = sorted(DB.fundamental.distinct("tahun", {"ada_angka": True}))
    hasil["fundamental_tahun"] = tahun
    hasil["fundamental_laporan"] = DB.fundamental.count_documents({"ada_angka": True})
    hasil["fundamental_lengkap"] = all(t in tahun for t in range(2019, 2027))
    hasil["pekerjaan"] = pk.terbaru(5)
    p = DB.paper_status.find_one({"_id": "status"}, {"_id": 0})
    hasil["paper_tgl_terakhir"] = p["tgl_terakhir"] if p else None
    return hasil


@app.get("/api/sehat")
def sehat():
    return {"mongo": DB.client.server_info()["version"], "versi": DB.backtest_ringkasan.count_documents({})}


@app.get("/api/build")
def versi_build():
    f = DIST / "index.html"
    return {"build": int(f.stat().st_mtime) if f.exists() else None}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{jalur:path}")
    def spa(jalur: str):
        f = (DIST / jalur).resolve()
        aman = f.is_relative_to(DIST.resolve())
        if jalur and aman and f.is_file() and f.name != "index.html":
            return FileResponse(f)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
