import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.db.harga import mentah as baca_mentah

DB = d.koneksi()
BATAS_KAS = 0.005


def _bulan_periode(tahun, bulan):
    if bulan:
        return [f"{tahun}-{bulan:02d}"]
    return [f"{tahun}-{m:02d}" for m in range(1, 13)]


def _tgl(x):
    return pd.Timestamp(x).normalize() if x is not None else None


def _kalender():
    return dt.baca("pasar")["ihsg"].dropna().index


def _close(seri, tgl):
    if seri is None or not len(seri):
        return None
    s = seri[seri.index <= tgl].dropna()
    return float(s.iloc[-1]) if len(s) else None


def rincian(versi, tahun, bulan=None):
    ek = list(DB.backtest_ekuitas.find({"versi": versi}, {"_id": 0, "bulan": 1, "return": 1, "ekuitas": 1}).sort("bulan", 1))
    peta = {e["bulan"]: e for e in ek}
    kunci = [b for b in _bulan_periode(tahun, bulan) if b in peta]
    if not kunci:
        return {"ada": False}
    awal_b, akhir_b = kunci[0], kunci[-1]
    sebelum = [e["ekuitas"] for e in ek if e["bulan"] < awal_b]
    ek_awal = float(sebelum[-1]) if sebelum else 1.0
    ek_akhir = float(peta[akhir_b]["ekuitas"])
    heatmap = float(peta[awal_b]["return"]) if bulan else (ek_akhir / ek_awal - 1) * 100
    heatmap_tampil = float(peta[awal_b]["return"]) if bulan else None
    kal = _kalender()
    awal_tgl = pd.Timestamp(f"{awal_b}-01")
    akhir_tgl = pd.Timestamp(f"{akhir_b}-01") + pd.offsets.MonthEnd(0)
    hari_awal = kal[kal < awal_tgl]
    batas_awal = hari_awal[-1] if len(hari_awal) else None
    hari_akhir = kal[kal <= akhir_tgl]
    batas_akhir = hari_akhir[-1] if len(hari_akhir) else akhir_tgl

    trade = list(DB.backtest_trade.find({"versi": versi, "dipilih": True}, {"_id": 0, "versi": 0}).sort("tgl_beli", 1))
    baris, selesai = [], []
    cache = {}
    for t in trade:
        beli, jual = _tgl(t["tgl_beli"]), _tgl(t.get("tgl_jual")) if t["status"] != "terbuka" else None
        if jual is not None and jual < awal_tgl:
            continue
        if beli > akhir_tgl:
            continue
        pnl = t.get("pnl") or {}
        s = sum(v for b, v in pnl.items() if awal_b <= b <= akhir_b)
        dibeli = beli >= awal_tgl
        dijual = jual is not None and jual <= akhir_tgl
        if t["ticker"] not in cache:
            cache[t["ticker"]] = baca_mentah(t["ticker"])
        m = cache[t["ticker"]]
        seri = m["close"] if m is not None else None
        c_awal = _close(seri, batas_awal) if batas_awal is not None else None
        c_akhir = _close(seri, batas_akhir)
        harga_awal = float(t["harga_beli"]) if dibeli or c_awal is None else c_awal
        harga_akhir = float(t["harga_jual"]) if dijual else c_akhir
        baris.append({"ticker": t["ticker"], "bagian": t.get("bagian"), "dibeli": bool(dibeli), "dijual": bool(dijual), "tgl_beli": str(beli.date()),
                      "tgl_jual": str(jual.date()) if jual is not None else None, "harga_awal": harga_awal, "harga_akhir": harga_akhir,
                      "sumbangan_pct": s / ek_awal * 100, "harga_beli": t["harga_beli"], "harga_jual": t.get("harga_jual"), "hari": t.get("hari"), "net": t["net"],
                      "terbuka": t["status"] == "terbuka"})
        if dijual and awal_tgl <= jual <= akhir_tgl:
            selesai.append({"ticker": t["ticker"], "bagian": t.get("bagian"), "tgl_beli": str(beli.date()), "harga_beli": t["harga_beli"], "tgl_jual": str(jual.date()),
                            "harga_jual": t["harga_jual"], "hari": t.get("hari"), "net": t["net"]})
    baris.sort(key=lambda x: -x["sumbangan_pct"])
    selesai.sort(key=lambda x: (x["tgl_jual"], x["ticker"]))
    jumlah = sum(x["sumbangan_pct"] for x in baris)
    sisa = heatmap - jumlah
    return {"ada": True, "versi": versi, "tahun": tahun, "bulan": bulan, "periode": f"{awal_b}" if bulan else str(tahun), "awal": str(awal_tgl.date()), "akhir": str(akhir_tgl.date()),
            "batas_awal": str(batas_awal.date()) if batas_awal is not None else None, "batas_akhir": str(batas_akhir.date()), "ekuitas_awal": ek_awal,
            "heatmap_pct": heatmap, "heatmap_tampil_pct": heatmap_tampil, "posisi": baris, "kas_lain_pct": sisa if abs(sisa) >= BATAS_KAS else 0.0,
            "kas_lain_ada": abs(sisa) >= BATAS_KAS, "total_pct": jumlah + (sisa if abs(sisa) >= BATAS_KAS else 0.0), "selisih_pct": sisa if abs(sisa) < BATAS_KAS else 0.0,
            "selesai": selesai}
