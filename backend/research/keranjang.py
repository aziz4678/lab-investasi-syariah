import argparse
from datetime import date, datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d
from backend.research import analisis_likuiditas as al

WADAH = {"PT": "pendapatan_tetap", "PU": "pasar_uang"}
LABEL = {"PT": "RD pendapatan tetap syariah", "PU": "RD pasar uang syariah"}
JUMLAH = 5
MIN_TAHUN = 3
NAV_DATAR = 0.01
AKTIF_HARI = 14
APLIKASI = ("semua", "bibit", "ajaib", "makmur")
KOLEKSI = "keranjang_konservatif"
KRITERIA = {"jumlah": JUMLAH, "min_tahun": MIN_TAHUN, "nav_datar": NAV_DATAR, "aktif_hari": AKTIF_HARI,
            "urut": "biaya termurah, lalu dana kelolaan terbesar", "aum": "dana kelolaan >= median produk yang lolos (dicek saat dibentuk)"}


def _daftar():
    from backend.app.services import reksadana as rdn
    return rdn.daftar()["data"]


def _syarat_dasar(x, bagi, batas_aktif):
    alasan = []
    if not x.get("nav_tgl") or pd.Timestamp(x["nav_tgl"]) < batas_aktif or x.get("nav_beku"):
        alasan.append("tidak aktif")
    if (x.get("tahun_data") or 0) < MIN_TAHUN:
        alasan.append(f"riwayat < {MIN_TAHUN} th")
    if int(x["id"]) in bagi or (x.get("cagr_semua") is not None and x["cagr_semua"] < NAV_DATAR * 100):
        alasan.append("bagi hasil tunai")
    if x.get("biaya") is None or x["biaya"] <= 0:
        alasan.append("biaya tidak diketahui")
    return alasan


def calon(data=None):
    data = _daftar() if data is None else data
    bagi = {int(x["_id"]) for x in d.koneksi().rd_produk.find({"Dividend": True}, {"_id": 1})}
    batas_aktif = pd.Timestamp(date.today()) - pd.Timedelta(days=AKTIF_HARI)
    hasil, gagal = {k: [] for k in WADAH}, {}
    for x in data:
        k = next((k for k, v in WADAH.items() if x.get("kategori") == v), None)
        if k is None or x.get("mata_uang") != "IDR":
            continue
        alasan = _syarat_dasar(x, bagi, batas_aktif)
        if alasan:
            gagal[int(x["id"])] = alasan
            continue
        hasil[k].append({"id": int(x["id"]), "nama": x["nama"], "mi": x.get("mi"), "biaya": x["biaya"], "aum": x.get("aum"), "tahun_data": x.get("tahun_data"),
                         "terbit": x.get("terbit"), "platform": [{"kode": p["kode"], "url": p.get("url")} for p in x.get("platform") or []]})
    return hasil, gagal


def bentuk(cl, aplikasi="semua"):
    isi, info = {}, {}
    for k, daftar in cl.items():
        batas = float(np.median([c["aum"] or 0 for c in daftar])) if daftar else 0.0
        besar = [c for c in daftar if (c["aum"] or 0) >= batas]
        if aplikasi != "semua":
            besar = [c for c in besar if any(p["kode"] == aplikasi for p in c["platform"])]
        besar.sort(key=lambda c: (c["biaya"], -(c["aum"] or 0)))
        isi[k] = besar[:JUMLAH]
        info[k] = {"lolos": len(daftar), "aum_besar": len([c for c in daftar if (c["aum"] or 0) >= batas]), "batas_aum": batas,
                   "di_aplikasi": len(besar), "tanpa_platform": sum(1 for c in daftar if not c["platform"])}
    return isi, info


def terbaru(aplikasi="semua", koleksi=None):
    kol = koleksi if koleksi is not None else dt.db()[KOLEKSI]
    return kol.find_one({"aplikasi": aplikasi}, sort=[("dibentuk", -1)])


def periksa(lama, cl, gagal, hari):
    if lama is None:
        return "awal", []
    if hari.month == 1 and lama["dibentuk"].year < hari.year:
        return "januari", []
    lolos = {c["id"] for v in cl.values() for c in v}
    catatan = []
    for k, v in lama["isi"].items():
        for c in v:
            if c["id"] in lolos:
                continue
            sebab = gagal.get(c["id"])
            if sebab is None or "tidak aktif" in sebab:
                catatan.append({"id": c["id"], "nama": c["nama"], "alasan": "bubar / tidak aktif"})
            else:
                catatan.append({"id": c["id"], "nama": c["nama"], "alasan": "gagal saringan: " + ", ".join(sebab)})
    if not catatan:
        return None, []
    return ("bubar" if all(x["alasan"].startswith("bubar") for x in catatan) else "gagal saringan"), catatan


def perbarui(cetak=True, hari=None):
    hari = hari or date.today()
    kol = dt.db()[KOLEKSI]
    cl, gagal = calon()
    hasil = {}
    for app in APLIKASI:
        lama = terbaru(app, kol)
        alasan, catatan = periksa(lama, cl, gagal, hari)
        if alasan is None:
            hasil[app] = {"berubah": False, "dok": lama}
            continue
        isi, info = bentuk(cl, app)
        waktu = datetime.now()
        dok = {"_id": f"{app}_{waktu:%Y%m%d%H%M%S}", "aplikasi": app, "dibentuk": waktu, "alasan": alasan, "catatan": catatan,
               "isi": isi, "info": info, "kriteria": KRITERIA, "sebelumnya": lama["_id"] if lama else None}
        kol.insert_one(dok)
        hasil[app] = {"berubah": True, "dok": dok}
    if cetak:
        for app, h in hasil.items():
            x = h["dok"]
            print(f"[{app}] {'DIBENTUK ULANG (' + x['alasan'] + ')' if h['berubah'] else 'tetap'} · dibentuk {x['dibentuk']:%Y-%m-%d} · "
                  + " · ".join(f"{k} {len(x['isi'][k])} produk" for k in WADAH))
            for c in x.get("catatan") or []:
                print(f"    {c['nama']}: {c['alasan']}")
        semua = hasil["semua"]["dok"]
        for k in WADAH:
            print(f"  {LABEL[k]}: {semua['info'][k]['lolos']} lolos, {semua['info'][k]['aum_besar']} AUM >= median, "
                  f"{semua['info'][k]['tanpa_platform']} tanpa data aplikasi")
            for c in semua["isi"][k]:
                print(f"    {c['nama']} · biaya {c['biaya']:.2f}% · {', '.join(p['kode'] for p in c['platform']) or 'tanpa data aplikasi'}")
    return hasil


def sidik():
    kol = dt.db()[KOLEKSI]
    return "|".join((terbaru(a, kol) or {}).get("_id", "-") for a in APLIKASI)


def seri_produk(ids):
    if not ids:
        return {}
    df = pd.DataFrame(list(d.koneksi().rd_ojk.find({"fund": {"$in": ids}, "denominasi": "IDR"}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1, "nab": 1})))
    if df.empty:
        return {}
    df["tgl"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    return {int(f): g.sort_values("nab").groupby("tgl")["nav"].last().sort_index() for f, g in df.groupby("fund")}


def indeks_wadah(produk, k, L_kat, dari):
    rk = (L_kat / L_kat.shift(1) - 1).dropna()
    ids = [c["id"] for c in produk]
    seri = seri_produk(ids)
    R = pd.DataFrame(index=rk.index)
    for i in ids:
        s = seri.get(i)
        if s is None or s.empty:
            R[i] = np.nan
            continue
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))
        R[i] = s.pct_change(fill_method=None).reindex(rk.index)
    lompat = R.abs() > al.LOMPAT[k]
    kejadian = [{"id": int(i), "bulan": str(t), "return": float(R.at[t, i])} for i in ids for t in R.index[lompat[i]]]
    R = R.mask(lompat)
    kosong = R.isna()
    if ids:
        R = R.apply(lambda kol: kol.fillna(rk))
        r = R.mean(axis=1)
    else:
        r = rk
    level = pd.concat([pd.Series([1.0], index=[L_kat.index[0]]), (1 + r).cumprod()])
    jendela = kosong.loc[dari:] if ids else None
    isian = float(jendela.to_numpy().mean()) if ids and jendela.size else 1.0
    per_produk = {str(i): float(jendela[i].mean()) for i in ids} if ids else {}
    return level, {"isian": isian, "isian_produk": per_produk, "lompat": kejadian, "tanpa_ojk": [int(i) for i in ids if i not in seri]}


def indeks(isi, L_kat, dari):
    L, info = {}, {}
    for k in WADAH:
        L[k], info[k] = indeks_wadah(isi.get(k, []), k, L_kat[k], dari)
    return L, info


def utama():
    hasil = perbarui()
    h = al.semua_indeks()
    dari = pd.Period("2016-04", "M")
    L, info = indeks(hasil["semua"]["dok"]["isi"], h["L"], dari)
    for k in WADAH:
        print(f"  indeks keranjang {k}: isian kategori sejak {dari} {info[k]['isian'] * 100:.1f}%, lompatan ekstrem {len(info[k]['lompat'])}, "
              f"tanpa data OJK {len(info[k]['tanpa_ojk'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("perintah", nargs="?", default="perbarui")
    a = ap.parse_args()
    utama()
