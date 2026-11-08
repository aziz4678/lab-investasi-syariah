import csv
from datetime import datetime

import numpy as np
import pandas as pd

from backend.app.services import reksadana as rd
from backend.core.config import ROOT
from backend.db import koneksi as d

BERKAS = ROOT / "data" / "cek_silang_platform.csv"
KOLOM = ["nama", "id_pasardana", "platform", "tgl_nav", "nav", "ret_1b", "ret_3b", "ret_6b", "ret_ytd", "ret_1t", "ret_3t", "ret_5t", "ret_10t", "aum", "catatan"]
JENDELA = [("1b", "ret_1bln", 0.1), ("3b", "ret_3bln", 0.1), ("6b", "ret_6bln", 0.1), ("ytd", "ret_ytd", 0.1), ("1t", "ret_1th", 0.1),
           ("3t", "ret_3t", 0.3), ("5t", "ret_5t", 0.3), ("10t", "ret_10t", 0.3)]


def angka(x):
    x = (x or "").strip().replace("%", "").replace(" ", "")
    if not x or x in ("-", "–"):
        return None
    if "," in x and "." in x:
        x = x.replace(".", "").replace(",", ".") if x.rfind(",") > x.rfind(".") else x.replace(",", "")
    elif "," in x:
        x = x.replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def baca():
    if not BERKAS.exists():
        return []
    with open(BERKAS, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]


def cocokkan(r, data):
    i = angka(r.get("id_pasardana"))
    if i is not None:
        return next((x for x in data if x["id"] == int(i)), None)
    nama = (r.get("nama") or "").strip().lower()
    return next((x for x in data if x["nama"].strip().lower() == nama), None)


def dugaan(k, kin, tgl_app, tgl_pf, usd):
    alasan = []
    if tgl_pf and tgl_app and tgl_pf != tgl_app:
        alasan.append(f"tanggal NAV beda (aplikasi {tgl_app}, platform {tgl_pf})")
    x = (kin or {}).get(k)
    if x and x.get("kira"):
        hari = abs((pd.Timestamp(x["awal"]) - pd.Timestamp(x["target"])).days)
        alasan.append(f"data harian belum ada; patokan akhir bulan OJK {x['awal']}, {hari} hari dari tanggal yang sama ({x['target']})")
        if usd:
            alasan.append("RD dolar: NAV akhir bulan OJK = NAB rupiah ÷ kurs, bisa meleset ±0,2-3%")
    if not alasan:
        alasan.append("tanggal awal atau NAV yang dipakai platform kemungkinan berbeda (mis. hari libur, NAV termasuk dividen)")
    return "; ".join(alasan)


def jalan():
    db = d.koneksi()
    data = rd._daftar(rd.versi())
    sebelum = (db.rd_cek_platform.find_one({"_id": "sebelum"}) or {}).get("produk", {})
    n = rd.nav()
    oj = pd.DataFrame(list(db.rd_ojk.find({"fund": {"$ne": None}}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    oj = {f: g.assign(tgl=pd.to_datetime(g["tgl"])).set_index("tgl")["nav"].astype(float).sort_index() for f, g in oj.groupby("fund")} if not oj.empty else {}

    perubahan = {}
    for x in data:
        s = sebelum.get(str(x["id"]))
        if not s:
            continue
        for k, f, _ in JENDELA:
            a, b = s.get(f), x.get(f)
            if a is not None and b is not None:
                perubahan.setdefault(k, []).append(b - a)
    ringkas_semua = {k: {"produk": len(v), "median_abs": float(np.median(np.abs(v))), "p90_abs": float(np.percentile(np.abs(v), 90)),
                         "maks_abs": float(np.max(np.abs(v)))} for k, v in perubahan.items()}

    baris, periksa = [], []
    for r in baca():
        x = cocokkan(r, data)
        if not x:
            baris.append({"nama": r.get("nama"), "platform": r.get("platform"), "galat": "produk tidak ditemukan (isi id_pasardana)"})
            continue
        s = sebelum.get(str(x["id"]), {})
        usd = x["mata_uang"] == "USD"
        kin = rd.kinerja(n[x["id"]].dropna() if x["id"] in n.columns else pd.Series(dtype=float), oj.get(x["id"]), usd)
        tgl_pf = (r.get("tgl_nav") or "").strip()[:10] or None
        nav_pf = angka(r.get("nav"))
        hasil = {"id": x["id"], "nama": x["nama"], "platform": r.get("platform"), "catatan": r.get("catatan"), "mata_uang": x["mata_uang"],
                 "nav": {"platform": nav_pf, "tgl_platform": tgl_pf, "sebelum": s.get("nav"), "tgl_sebelum": s.get("nav_tgl"),
                         "sesudah": x.get("nav"), "tgl_sesudah": x.get("nav_tgl"),
                         "sama_tgl": tgl_pf == x.get("nav_tgl") if tgl_pf else None,
                         "sama_nilai": abs(nav_pf / x["nav"] - 1) < 1e-6 if nav_pf and x.get("nav") else None},
                 "jendela": []}
        for k, f, tol in JENDELA:
            pf = angka(r.get(f"ret_{k}"))
            if pf is None:
                continue
            a = s.get(f)
            b = x.get(f)
            j = {"k": k, "platform": pf, "sebelum": a, "sesudah": b, "toleransi": tol,
                 "selisih_sebelum": None if a is None else a - pf, "selisih_sesudah": None if b is None else b - pf,
                 "kira": bool((kin.get(k) or {}).get("kira")), "awal": (kin.get(k) or {}).get("awal")}
            j["lolos"] = j["selisih_sesudah"] is not None and abs(j["selisih_sesudah"]) <= tol + 1e-9
            if not j["lolos"]:
                j["dugaan"] = "angka aplikasi kosong (riwayat belum cukup)" if b is None else dugaan(k, kin, x.get("nav_tgl"), tgl_pf, usd)
                periksa.append({"id": x["id"], "nama": x["nama"], "jendela": k, "platform": pf, "aplikasi": b, "selisih": j["selisih_sesudah"], "dugaan": j["dugaan"]})
            hasil["jendela"].append(j)
        aum_pf = angka(r.get("aum"))
        if aum_pf:
            hasil["aum"] = {"platform": aum_pf, "sebelum": s.get("aum"), "tgl_sebelum": s.get("aum_tgl"), "kelas": x.get("aum"),
                            "semua_kelas": x.get("aum_total"), "tgl": x.get("aum_tgl"),
                            "selisih_kelas_pct": (x["aum"] / aum_pf - 1) * 100 if x.get("aum") else None,
                            "selisih_total_pct": (x["aum_total"] / aum_pf - 1) * 100 if x.get("aum_total") else None}
        baris.append(hasil)

    doc = {"_id": "hasil", "dibuat": datetime.now(), "berkas": str(BERKAS.relative_to(ROOT)), "baris": baris, "periksa": periksa,
           "semua_produk": ringkas_semua, "ada_sebelum": bool(sebelum),
           "sebelum_dibuat": (db.rd_cek_platform.find_one({"_id": "sebelum"}, {"dibuat": 1}) or {}).get("dibuat")}
    db.rd_cek_platform.replace_one({"_id": "hasil"}, rd.bersih(doc), upsert=True)

    print(f"{len(baris)} baris di {BERKAS.name}; {len(periksa)} angka di luar toleransi")
    for k, v in ringkas_semua.items():
        print(f"  semua produk {k}: {v['produk']} produk, perubahan median {v['median_abs']:.3f} poin, p90 {v['p90_abs']:.3f}, maks {v['maks_abs']:.2f}")
    for h in baris:
        if h.get("galat"):
            print(f"  {h['nama']}: {h['galat']}")
            continue
        nv = h["nav"]
        print(f"  {h['nama']}: NAV platform {nv['platform']} ({nv['tgl_platform']}) | sebelum {nv['sebelum']} ({nv['tgl_sebelum']}) | sesudah {nv['sesudah']} ({nv['tgl_sesudah']})")
        for j in h["jendela"]:
            f = lambda v: "–" if v is None else f"{v:+.2f}"
            print(f"    {j['k']:>3}: platform {j['platform']:+.2f} | sebelum {f(j['sebelum'])} (selisih {f(j['selisih_sebelum'])}) | sesudah {f(j['sesudah'])} (selisih {f(j['selisih_sesudah'])}) {'OK' if j['lolos'] else 'PERIKSA'}")
        if h.get("aum"):
            a = h["aum"]
            print(f"    AUM: platform {a['platform']:,.0f} | kelas {a['kelas'] or 0:,.0f} ({a['selisih_kelas_pct'] or 0:+.2f}%) | semua kelas {a['semua_kelas'] or 0:,.0f} | per {a['tgl']}")
    for p in periksa:
        print(f"  PERIKSA {p['nama']} {p['jendela']}: {p['dugaan']}")


if __name__ == "__main__":
    jalan()
