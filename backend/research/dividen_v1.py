import numpy as np
import pandas as pd

from backend.app.services import dividen as dvn
from backend.ingest import des_ojk
from backend.research import screener as sc
from backend.research import uji_h17 as h17

MULAI = pd.Timestamp("2027-01-01")
MODAL = 100_000_000
JUMLAH = 10
MAKS_SEKTOR = 3
PAJAK = 0.10
JEDA_BAYAR = 18
ATURAN = {
    "mulai": "2027-01-01", "modal": MODAL, "jumlah": JUMLAH, "maks_per_sektor": MAKS_SEKTOR, "pajak": PAJAK,
    "syarat_bayar_tahun": 3, "min_nilai_transaksi": sc.MIN_VALUE, "harga_min": sc.HARGA_MIN, "min_calon": h17.MIN_CALON,
    "fee_beli": sc.FEE_BELI, "fee_jual": sc.FEE_JUAL, "jeda_bayar_cadangan": JEDA_BAYAR,
    "kriteria": {"penghasilan_min_persen": 4.0, "evaluasi_sampai": "2028-12-31", "dd_maks_lebih_buruk_dari_ihsg": 10.0},
}


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
