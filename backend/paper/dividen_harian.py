import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.api import dividen as dvn
from backend.api.emiten import baca_ihsg
from backend.db import koneksi as d
from backend.riset import des_ojk
from backend.riset import screener as sc
from backend.riset import uji_h17 as h17

MULAI = pd.Timestamp("2027-01-01")
MODAL = 100_000_000
JUMLAH = 10
MAKS_SEKTOR = 3
PAJAK = 0.10
JEDA_BAYAR = 18
ID_KUNCI = "dividen_v1"
ATURAN = {
    "mulai": "2027-01-01", "modal": MODAL, "jumlah": JUMLAH, "maks_per_sektor": MAKS_SEKTOR, "pajak": PAJAK,
    "syarat_bayar_tahun": 3, "min_nilai_transaksi": sc.MIN_VALUE, "harga_min": sc.HARGA_MIN, "min_calon": h17.MIN_CALON,
    "fee_beli": sc.FEE_BELI, "fee_jual": sc.FEE_JUAL, "jeda_bayar_cadangan": JEDA_BAYAR,
    "kriteria": {"penghasilan_min_persen": 4.0, "evaluasi_sampai": "2028-12-31", "dd_maks_lebih_buruk_dari_ihsg": 10.0},
}
KOLEKSI = ["paper_dividen_status", "paper_dividen_posisi", "paper_dividen_transaksi", "paper_dividen_ekuitas", "paper_dividen_pilihan"]


def kunci():
    db = d.koneksi()
    ada = db.batas_paper.find_one({"_id": ID_KUNCI})
    if ada is None:
        db.batas_paper.insert_one({"_id": ID_KUNCI, "aturan": ATURAN, "dikunci": datetime.now()})
        print(f"Aturan uji maju Pemburu Dividen dikunci ({ID_KUNCI}).")
        return
    if ada["aturan"] != ATURAN:
        raise SystemExit(f"Aturan di kode berbeda dengan yang dikunci {ada['dikunci']:%Y-%m-%d}. Uji maju tidak boleh diubah; kembalikan konstanta.")


def sektor_dari():
    return {k: (v[0] or f"?{k}") for k, v in dvn.info_sektor().items()}


def pilih(data, des, sektor, t, tahun):
    _, yld, univ, _ = h17.pilih(data, sorted(des_ojk.syariah_pada(des, t)), t, tahun)
    calon = sorted(yld.items(), key=lambda x: -x[1])
    hasil, per = [], {}
    for k, y in calon:
        s = sektor.get(k, f"?{k}")
        if per.get(s, 0) >= MAKS_SEKTOR:
            continue
        per[s] = per.get(s, 0) + 1
        hasil.append((k, y))
        if len(hasil) >= JUMLAH:
            break
    if len(calon) < h17.MIN_CALON:
        hasil = calon
    return [{"kode": k, "yield": round(y, 2), "sektor": sektor.get(k, "")} for k, y in hasil], len(calon), len(univ)


def biaya(harga, beli):
    return h17.biaya(harga, beli)


def tanggal_bayar(kode, ex, ki_cache):
    if kode not in ki_cache:
        ki_cache[kode] = dvn.idx_kejadian(kode)
    ki = ki_cache[kode]
    if ki is not None and not ki.empty:
        sel = (ki["ex_ef"] - ex).abs()
        j = sel.idxmin()
        if sel[j] <= pd.Timedelta(days=dvn.COCOK_HARI) and pd.notna(ki.loc[j, "bayar"]):
            return ki.loc[j, "bayar"], True
    return ex + pd.Timedelta(days=JEDA_BAYAR), False


def simulasi(data, des, sektor, kal, sampai):
    hari = kal[(kal >= MULAI) & (kal <= sampai)]
    kas, lot, piutang = float(MODAL), {}, []
    transaksi, ekuitas, pilihan = [], [], []
    ki_cache = {}
    tahun_rebal = None
    for i, t in enumerate(hari):
        if t.year != tahun_rebal:
            tahun_rebal = t.year
            acuan = kal[kal < t].max()
            pil, n_calon, n_univ = pilih(data, des, sektor, acuan, t.year)
            pilihan.append({"_id": str(t.year), "tahun": t.year, "acuan": acuan.to_pydatetime(), "saham": pil, "calon": n_calon, "universe": n_univ})
            target = {x["kode"] for x in pil}
            for k in sorted(set(lot) - target):
                m = data.get(k)
                px = h17.harga_buka(m, t) if m is not None else np.nan
                if not np.isfinite(px):
                    continue
                nilai = lot[k] * 100 * px
                ongkos = nilai * biaya(px, False)
                kas += nilai - ongkos
                transaksi.append({"tgl": t, "kode": k, "aksi": "jual", "lot": lot.pop(k), "harga": px, "nilai": nilai - ongkos, "biaya": ongkos})
            ek = kas + sum(x["nilai"] for x in piutang) + sum(n * 100 * h17.harga_buka(data[k], t) for k, n in lot.items())
            baru = [x["kode"] for x in pil if x["kode"] not in lot]
            for k in baru:
                px = h17.harga_buka(data[k], t)
                if not (np.isfinite(px) and px > 0):
                    continue
                jatah = min(ek / JUMLAH, kas)
                n = int(jatah // (px * 100 * (1 + biaya(px, True))))
                if n <= 0:
                    continue
                nilai = n * 100 * px
                ongkos = nilai * biaya(px, True)
                kas -= nilai + ongkos
                lot[k] = n
                transaksi.append({"tgl": t, "kode": k, "aksi": "beli", "lot": n, "harga": px, "nilai": -(nilai + ongkos), "biaya": ongkos})
        for k, n in lot.items():
            m = data[k]
            if t in m.index and m.at[t, "dividends"] > 0:
                dps = float(m.at[t, "dividends"])
                bersih = n * 100 * dps * (1 - PAJAK)
                tb, resmi = tanggal_bayar(k, t, ki_cache)
                piutang.append({"kode": k, "nilai": bersih, "bayar": tb})
                transaksi.append({"tgl": t, "kode": k, "aksi": "dividen", "lot": n, "harga": dps, "nilai": bersih, "biaya": n * 100 * dps * PAJAK,
                                  "bayar": tb, "bayar_resmi": resmi})
        for p in [p for p in piutang if p["bayar"] <= t]:
            kas += p["nilai"]
            piutang.remove(p)
            transaksi.append({"tgl": t, "kode": p["kode"], "aksi": "cair", "lot": None, "harga": None, "nilai": p["nilai"], "biaya": 0.0})
        nilai_saham = sum(n * 100 * h17.nilai_pada(data[k]["close"], t) for k, n in lot.items())
        ekuitas.append({"tgl": t, "ekuitas": kas + sum(p["nilai"] for p in piutang) + nilai_saham, "kas": kas,
                        "piutang": sum(p["nilai"] for p in piutang), "saham": nilai_saham})
    return lot, transaksi, ekuitas, pilihan, kas, piutang


def ringkas_tahun(transaksi, ekuitas):
    if not ekuitas:
        return []
    e = pd.DataFrame(ekuitas).set_index("tgl")["ekuitas"]
    tr = pd.DataFrame(transaksi)
    hasil = []
    for th in sorted(set(e.index.year)):
        ey = e[e.index.year == th]
        awal = float(e[e.index < ey.index[0]].iloc[-1]) if (e.index < ey.index[0]).any() else float(MODAL)
        div = float(tr[(tr["aksi"] == "dividen") & (pd.to_datetime(tr["tgl"]).dt.year == th)]["nilai"].sum()) if len(tr) else 0.0
        hasil.append({"tahun": th, "awal": awal, "akhir": float(ey.iloc[-1]), "penghasilan": div, "penghasilan_persen": div / awal * 100,
                      "total_persen": (float(ey.iloc[-1]) / awal - 1) * 100, "lengkap": bool(ey.index[-1].month == 12 and ey.index[-1].day >= 28)})
    return hasil


def jalan():
    kunci()
    db = d.koneksi()
    des = des_ojk.baca()
    kode = sorted(set(des["kode"]))
    print(f"Memuat harga {len(kode)} saham DES...")
    data = h17.muat_harga(kode)
    kal = h17.kalender(data)
    akhir = kal.max()
    sektor = sektor_dari()
    acuan = akhir
    pratinjau, n_calon, n_univ = pilih(data, des, sektor, acuan, acuan.year + 1)
    db.paper_dividen_pilihan.replace_one({"_id": "pratinjau"}, {"_id": "pratinjau", "tahun": acuan.year + 1, "acuan": acuan.to_pydatetime(),
                                                                "saham": pratinjau, "calon": n_calon, "universe": n_univ, "dihitung": datetime.now()}, upsert=True)
    print(f"Pratinjau pilihan {acuan.year + 1} (data s/d {acuan:%Y-%m-%d}, {n_calon} calon dari {n_univ} saham likuid): "
          + ", ".join(f"{x['kode']} {x['yield']}%" for x in pratinjau))
    if akhir < MULAI:
        db.paper_dividen_status.replace_one({"_id": "status"}, {"_id": "status", "tahap": "menunggu", "mulai": MULAI.to_pydatetime(), "modal": MODAL,
                                                                "tgl_terakhir": akhir.to_pydatetime(), "aturan": ID_KUNCI, "diperbarui": datetime.now()}, upsert=True)
        print(f"Uji maju mulai {MULAI:%d %b %Y}. Sampai saat itu yang diperbarui hanya pratinjau.")
        return
    lot, transaksi, ekuitas, pilihan, kas, piutang = simulasi(data, des, sektor, kal, akhir)
    ihsg = baca_ihsg()
    e = pd.DataFrame(ekuitas)
    if len(e):
        dasar = h17.nilai_pada(ihsg, e["tgl"].iloc[0] - pd.Timedelta(days=1))
        e["ihsg"] = [h17.nilai_pada(ihsg, t) / dasar * MODAL for t in e["tgl"]]
        e["dd"] = (e["ekuitas"] / e["ekuitas"].cummax() - 1) * 100
        e["dd_ihsg"] = (e["ihsg"] / e["ihsg"].cummax() - 1) * 100
    posisi = []
    for k, n in lot.items():
        m = data[k]
        beli = [x for x in transaksi if x["kode"] == k and x["aksi"] == "beli"][-1]
        px = h17.nilai_pada(m["close"], akhir)
        div = sum(x["nilai"] for x in transaksi if x["kode"] == k and x["aksi"] == "dividen" and x["tgl"] >= beli["tgl"])
        posisi.append({"_id": k, "kode": k, "lot": n, "tgl_beli": beli["tgl"].to_pydatetime(), "harga_beli": beli["harga"], "harga": px,
                       "nilai": n * 100 * px, "untung_persen": (px / beli["harga"] - 1) * 100, "dividen": div, "sektor": sektor.get(k, "")})
    tahunan = ringkas_tahun(transaksi, ekuitas)
    for nama in KOLEKSI[1:4]:
        db[nama].delete_many({})
    if posisi:
        db.paper_dividen_posisi.insert_many(posisi)
    if transaksi:
        db.paper_dividen_transaksi.insert_many([{k: (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for k, v in x.items()} for x in transaksi])
    if len(e):
        db.paper_dividen_ekuitas.insert_many(d.ke_dokumen(e))
    for p in pilihan:
        db.paper_dividen_pilihan.replace_one({"_id": p["_id"]}, p, upsert=True)
    ek = float(e["ekuitas"].iloc[-1]) if len(e) else float(MODAL)
    status = {"_id": "status", "tahap": "berjalan", "mulai": MULAI.to_pydatetime(), "modal": MODAL, "tgl_terakhir": akhir.to_pydatetime(),
              "ekuitas": ek, "kas": kas, "piutang": sum(p["nilai"] for p in piutang), "penghasilan_total": sum(x["nilai"] for x in transaksi if x["aksi"] == "dividen"),
              "dd": float(e["dd"].min()) if len(e) else 0.0, "dd_ihsg": float(e["dd_ihsg"].min()) if len(e) else 0.0,
              "ihsg": float(e["ihsg"].iloc[-1]) if len(e) else float(MODAL), "tahunan": tahunan, "aturan": ID_KUNCI, "diperbarui": datetime.now()}
    db.paper_dividen_status.replace_one({"_id": "status"}, status, upsert=True)
    print(f"Ekuitas Rp{ek:,.0f} ({(ek / MODAL - 1) * 100:+.2f}%), penghasilan dividen Rp{status['penghasilan_total']:,.0f}, "
          f"{len(posisi)} posisi, data s/d {akhir:%Y-%m-%d}")


if __name__ == "__main__":
    jalan() if len(sys.argv) < 2 else {"jalan": jalan, "kunci": kunci}[sys.argv[1]]()
