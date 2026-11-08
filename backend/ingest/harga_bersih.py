import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi
from backend.ingest import koreksi_harga as kh

KOLEKSI = "harga_bersih_2020"
INFO = "harga_bersih_2020_info"
MULAI = pd.Timestamp("2020-01-02")
BEKU_MIN = 20
FAKTOR_MIN, FAKTOR_MAKS = 0.2, 5.0
RESET_KECIL = 0.10
JENDELA_SPLIT = 10
JENDELA_UMUM_SEBELUM, JENDELA_UMUM_SESUDAH = 60, 5
JENDELA_DIV = 5
TOL_KONTINU = 0.02
COCOK_OPEN = 0.02
KATEGORI_CA = ["split", "hmetd", "aksi", "pencatatan"]
KATEGORI_HENTI = ["delisting", "suspensi"]
BUKAN_DELISTING_SAHAM = ["waran", "treasuri", "pencatatan kembali", "obligasi", "sukuk"]
DELISTING_PASTI = ["delisting saham", "penghapusan pencatatan saham", "pembatalan pencatatan saham", "penghapusan pencatatan efek"]


def _idx():
    i = dt.baca("idx_harian")
    i["tgl"] = pd.to_datetime(i["tgl"])
    i = i[i["tgl"] >= MULAI].sort_values("tgl")
    i["prev_close"] = i.groupby("StockCode")["Close"].shift(1)
    i["prev_volume"] = i.groupby("StockCode")["Volume"].shift(1)
    return {k: g.drop_duplicates("tgl").set_index("tgl") for k, g in i.groupby("StockCode")}


def _pengumuman():
    hasil = {}
    for d in dt.db()["pengumuman"].find({"kategori": {"$in": KATEGORI_CA + KATEGORI_HENTI}, "kode": {"$ne": None}},
                                        {"kode": 1, "tgl": 1, "kategori": 1, "judul": 1}):
        hasil.setdefault(d["kode"], []).append(d)
    return hasil


def _dividen_idx():
    hasil = {}
    for d in koneksi.koneksi()["dividen_idx"].find({"jenis": "tunai", "ex": {"$gte": MULAI.to_pydatetime()}}):
        hasil.setdefault(d["kode"], []).append(d)
    return hasil


def _nilai_idx(d):
    if (d.get("mata_uang") or "IDR").upper() not in ("IDR", "RP"):
        return None
    a, b = d.get("per_lembar_idx"), d.get("per_lembar_dihitung")
    a = float(a) if a and a > 0 else None
    b = float(b) if b and b > 0 else None
    if a and b and max(a, b) / min(a, b) > 3:
        return b
    return a or b


def _faktor(kode, g, y, registry, umum):
    f_all = kh.faktor_idx(g)
    terap, catatan = {}, []
    sp = y["stock_splits"].fillna(0) if y is not None and "stock_splits" in y else None
    yc = y["close"] if y is not None else None
    ex_reg = {pd.Timestamp(r["ex_date"]) for r in registry if r["jenis"] == "faktor"}
    for t, f in f_all.items():
        bukti = []
        if sp is not None:
            dekat = sp[(sp.index >= t - pd.Timedelta(days=JENDELA_SPLIT)) & (sp.index <= t + pd.Timedelta(days=JENDELA_SPLIT)) & (sp > 0)]
            if len(dekat):
                bukti.append("split_yahoo_cocok" if any(abs(np.log(s * f)) < TOL_KONTINU for s in dekat) else "split_yahoo")
        if t in ex_reg:
            bukti.append("registry")
        if yc is not None and t in yc.index:
            sblm = yc[yc.index < t]
            if len(sblm) and sblm.iloc[-1] > 0 and yc[t] > 0 and g.at[t, "Previous"] > 0 and g.at[t, "Close"] > 0:
                ry = np.log(yc[t] / sblm.iloc[-1])
                ri = np.log(g.at[t, "Close"] / g.at[t, "Previous"])
                if abs(ry - ri) < TOL_KONTINU:
                    bukti.append("yahoo_kontinu")
        if any(t - pd.Timedelta(days=JENDELA_UMUM_SEBELUM) <= pd.Timestamp(p["tgl"]).normalize() <= t + pd.Timedelta(days=JENDELA_UMUM_SESUDAH)
               and p["kategori"] in KATEGORI_CA for p in umum):
            bukti.append("pengumuman")
        beku = not (g.at[t, "prev_volume"] > 0)
        if not (FAKTOR_MIN <= f <= FAKTOR_MAKS):
            status = "terap_ekstrem_terkonfirmasi" if {"split_yahoo_cocok", "yahoo_kontinu"} & set(bukti) else "tahan_ekstrem"
        elif bukti:
            status = "terap"
        elif beku or abs(f - 1) < RESET_KECIL:
            status = "tidak_diterapkan_reset_acuan"
        else:
            status = "terap_tanpa_bukti"
        if status.startswith("terap"):
            terap[t] = float(f)
        catatan.append({"tgl": str(t.date()), "faktor": round(float(f), 6), "status": status, "bukti": bukti,
                        "previous": float(g.at[t, "Previous"]), "close_kemarin": float(g.at[t, "prev_close"]), "beku_sebelumnya": bool(beku)})
    return terap, catatan


def _lari_beku(vol0):
    grup = (vol0 != vol0.shift()).cumsum()
    panjang = vol0.groupby(grup).transform("size")
    beku = vol0 & (panjang >= BEKU_MIN)
    periode = []
    for _, s in beku[beku].groupby(grup[beku]):
        periode.append({"mulai": str(s.index[0].date()), "akhir": str(s.index[-1].date()), "hari": int(len(s))})
    return beku, periode


def _dividen(g, y, close, E, div_idx):
    kejadian = []
    if y is not None and "dividends" in y:
        yd = y["dividends"].fillna(0)
        yd = yd[(yd > 0) & (yd.index >= g.index[0]) & (yd.index <= g.index[-1])]
        yc = y["close"]
        for t, v in yd.items():
            sblm = close.index[close.index < t]
            skala = None
            for s in reversed(sblm[-5:]):
                if s in yc.index and yc[s] > 0:
                    skala = close[s] / yc[s]
                    break
            if skala is None:
                continue
            kejadian.append({"tgl": t, "yahoo_adj": float(v) * skala})
    ex_idx = []
    for d in div_idx:
        ex = pd.Timestamp(d["ex"])
        if ex < g.index[0] or ex > g.index[-1]:
            continue
        ex_idx.append({"tgl": ex, "nilai": _nilai_idx(d)})
    tanpa_nilai = []
    hasil = []
    pakai = set()
    for e in ex_idx:
        dekat = [(abs((k["tgl"] - e["tgl"]).days), i) for i, k in enumerate(kejadian) if i not in pakai and abs((k["tgl"] - e["tgl"]).days) <= JENDELA_DIV]
        hari = g.index[g.index >= e["tgl"]][0]
        e_adj = None if e["nilai"] is None else e["nilai"] * float(E[hari])
        if dekat:
            i = min(dekat)[1]
            pakai.add(i)
            ya = kejadian[i]["yahoo_adj"]
            if e_adj is not None and max(e_adj, ya) / min(e_adj, ya) <= 3:
                hasil.append((hari, e_adj, "idx+yahoo"))
            else:
                hasil.append((hari, ya, "yahoo_tgl_idx"))
        elif e_adj is not None:
            hasil.append((hari, e_adj, "idx"))
        else:
            tanpa_nilai.append(str(e["tgl"].date()))
    for i, k in enumerate(kejadian):
        if i in pakai:
            continue
        hari = g.index[g.index >= k["tgl"]]
        if len(hari):
            hasil.append((hari[0], k["yahoo_adj"], "yahoo"))
    div = pd.Series(0.0, index=g.index)
    sumber = pd.Series("", index=g.index, dtype=object)
    for t, v, s in hasil:
        div[t] += v
        sumber[t] = s if not sumber[t] else sumber[t] + "," + s
    return div, sumber, tanpa_nilai


def satu(kode, g, y, registry, umum, div_idx):
    terap, catatan = _faktor(kode, g, y, registry, umum)
    E = kh.kali_e(g.index, terap)
    close = g["Close"].astype(float) * E
    ada = g["Volume"] > 0
    if y is not None:
        yo, yc = y["open"].reindex(g.index), y["close"].reindex(g.index)
        cocok = (yc > 0) & (np.abs(yc / close - 1) <= COCOK_OPEN)
    else:
        yo = pd.Series(np.nan, index=g.index)
        cocok = pd.Series(False, index=g.index)
    op_idx = (g["OpenPrice"] > 0) & ada
    open_ = pd.Series(np.where(op_idx, g["OpenPrice"].astype(float) * E, np.where(ada & cocok & (yo > 0), yo, close)), index=g.index)
    sumber_open = pd.Series(np.where(op_idx, "idx", np.where(ada & cocok & (yo > 0), "yahoo", np.where(ada, "close_idx", "tanpa_transaksi"))), index=g.index)
    hi = pd.Series(np.where((g["High"] > 0) & ada, g["High"].astype(float) * E, close), index=g.index)
    lo = pd.Series(np.where((g["Low"] > 0) & ada, g["Low"].astype(float) * E, close), index=g.index)
    hi = pd.concat([hi, open_, close], axis=1).max(axis=1)
    lo = pd.concat([lo, open_, close], axis=1).min(axis=1)
    beku, periode_beku = _lari_beku(~ada)
    div, div_sumber, tanpa_nilai = _dividen(g, y, close, E, div_idx)
    df = pd.DataFrame({
        "open": open_, "high": hi, "low": lo, "close": close, "volume": g["Volume"].astype(float) / E,
        "nilai": g["Value"].astype(float), "frekuensi": g["Frequency"].astype(float),
        "close_mentah": g["Close"].astype(float), "faktor": E.astype(float),
        "saham_tercatat": g["ListedShares"].astype(float) / E, "asing_beli": g["ForeignBuy"].astype(float) / E, "asing_jual": g["ForeignSell"].astype(float) / E,
        "dividen": div.astype(float), "dividen_mentah": (div / E).astype(float), "dividen_sumber": div_sumber.astype(str),
        "sumber_open": sumber_open.astype(str), "tanpa_transaksi": (~ada).astype(bool), "beku": beku.astype(bool),
    }, index=g.index)
    df.index.name = "Date"
    return df, catatan, periode_beku, tanpa_nilai


def _saham_delisting(p):
    j = p["judul"].lower()
    return p["kategori"] == "delisting" and not any(x in j for x in BUKAN_DELISTING_SAHAM)


def _pasti_delisting(umum):
    return [{"tgl": p["tgl"], "judul": p["judul"], "id": p["_id"]} for p in sorted(umum, key=lambda p: p["tgl"])
            if _saham_delisting(p) and any(x in p["judul"].lower() for x in DELISTING_PASTI)]


def _alasan_henti(umum, akhir):
    cocok = [p for p in umum if _saham_delisting(p) and pd.Timestamp(p["tgl"]) <= akhir + pd.Timedelta(days=60)]
    if not cocok:
        cocok = [p for p in umum if p["kategori"] in KATEGORI_HENTI and pd.Timestamp(p["tgl"]) <= akhir + pd.Timedelta(days=60)]
    if not cocok:
        return None
    p = max(cocok, key=lambda p: p["tgl"])
    return {"tgl": p["tgl"], "kategori": p["kategori"], "judul": p["judul"], "id": p["_id"]}


def validasi(hasil, yahoo):
    beda = []
    per_kode = {}
    for k, df in hasil.items():
        y = yahoo.get(k)
        if y is None:
            continue
        j = pd.DataFrame({"b": df["close"], "y": y["close"].reindex(df.index)}).dropna()
        j = j[(j["b"] > 0) & (j["y"] > 0)]
        if len(j) < 3:
            continue
        d = (j["b"].pct_change() - j["y"].pct_change()).dropna().abs()
        beda.append(d.values)
        per_kode[k] = {"hari": int(len(d)), "median": float(d.median()), "p99": float(d.quantile(0.99)), "maks": float(d.max()), "hari_beda_1pct": int((d > 0.01).sum())}
    semua = np.concatenate(beda) if beda else np.array([])
    terburuk = sorted(per_kode.items(), key=lambda x: -x[1]["hari_beda_1pct"])[:15]
    return {"kode": len(per_kode), "hari_saham": int(len(semua)), "median": float(np.median(semua)), "p99": float(np.quantile(semua, 0.99)),
            "p999": float(np.quantile(semua, 0.999)), "persen_beda_1pct": float((semua > 0.01).mean() * 100), "persen_identik": float((semua < 1e-9).mean() * 100),
            "terburuk": [{"kode": k, **v} for k, v in terburuk]}


def bangun():
    resmi = _idx()
    akhir_data = max(g.index.max() for g in resmi.values())
    yahoo = {k: v.set_axis(pd.to_datetime(v.index)) for k, v in hg.banyak(kolom=["open", "close", "dividends", "stock_splits"]).items()}
    registry = kh.aturan()
    reg_per = {}
    for r in registry:
        reg_per.setdefault(r["kode"], []).append(r)
    umum = _pengumuman()
    div_idx = _dividen_idx()
    des = set(koneksi.koneksi()["des"].distinct("kode"))
    hasil, info = {}, []
    for n, (k, g) in enumerate(sorted(resmi.items()), 1):
        y = yahoo.get(k)
        df, catatan, beku, tanpa_nilai = satu(k, g, y, reg_per.get(k, []), umum.get(k, []), div_idx.get(k, []))
        hasil[k] = df
        terakhir = df.index[-1]
        ada = df[~df["tanpa_transaksi"]]
        transaksi_terakhir = ada.index[-1] if len(ada) else None
        delisting = terakhir < akhir_data
        beku_akhir = bool(df["beku"].iloc[-1])
        pasti = _pasti_delisting(umum.get(k, []))
        if delisting:
            status = "delisting"
        elif beku_akhir and pasti:
            status = "suspensi_diumumkan_delisting"
        elif beku_akhir:
            status = "suspensi_di_akhir"
        else:
            status = "aktif"
        info.append({
            "_id": k, "kode": k, "status": status, "mulai": df.index[0].to_pydatetime(), "akhir": terakhir.to_pydatetime(),
            "transaksi_terakhir": transaksi_terakhir.to_pydatetime() if transaksi_terakhir is not None else None,
            "close_terakhir_mentah": float(df["close_mentah"].iloc[-1]),
            "alasan_henti": _alasan_henti(umum.get(k, []), terakhir) if status != "aktif" else None,
            "pengumuman_delisting": pasti, "ada_di_harga_yahoo": y is not None, "pernah_des": k in des, "baris": int(len(df)),
            "hari_tanpa_transaksi": int(df["tanpa_transaksi"].sum()), "periode_beku": beku,
            "faktor": catatan, "faktor_diterapkan": sum(1 for c in catatan if c["status"].startswith("terap")),
            "faktor_tidak_diterapkan": [c for c in catatan if not c["status"].startswith("terap")],
            "dividen_kejadian": int((df["dividen"] > 0).sum()), "dividen_idx_tanpa_nilai": tanpa_nilai,
            "diperbarui": datetime.now(),
        })
        if n % 100 == 0:
            print(f"  {n}/{len(resmi)} kode", flush=True)
    print("menyimpan ...", flush=True)
    for k, df in hasil.items():
        dt.tulis(f"{KOLEKSI}/{k}", df)
    lama = set(dt.daftar(KOLEKSI)) - set(hasil)
    for k in lama:
        dt.hapus(f"{KOLEKSI}/{k}")
    c = dt.db()[INFO]
    c.delete_many({})
    c.insert_many(info)
    val = validasi(hasil, yahoo)
    st = pd.Series([x["status"] for x in info]).value_counts().to_dict()
    fk = pd.Series([c["status"] for x in info for c in x["faktor"]]).value_counts().to_dict()
    ringkas = {
        "_id": "_ringkasan", "dibuat": datetime.now(), "mulai": str(MULAI.date()), "akhir": str(akhir_data.date()),
        "kode": len(hasil), "status": st, "tidak_ada_di_harga_yahoo": sorted(k for k in hasil if k not in yahoo),
        "des_tanpa_idx": sorted(k for k in des if k not in hasil),
        "faktor": fk, "beku_kode": sum(1 for x in info if x["periode_beku"]),
        "dividen_kejadian": int(sum(x["dividen_kejadian"] for x in info)), "dividen_idx_tanpa_nilai": int(sum(len(x["dividen_idx_tanpa_nilai"]) for x in info)),
        "sumber_open": pd.concat([d["sumber_open"] for d in hasil.values()]).value_counts().to_dict(),
        "dividen_sumber": pd.concat([d["dividen_sumber"][d["dividen_sumber"] != ""] for d in hasil.values()]).value_counts().to_dict(),
        "validasi_vs_yahoo": val, "sidik": hg.sidik(list(hasil), koleksi=KOLEKSI, kolom=("open", "high", "low", "close", "volume", "dividen")),
    }
    c.insert_one(ringkas)
    return ringkas


def cetak(r):
    v = r["validasi_vs_yahoo"]
    print(f"harga_bersih_2020: {r['kode']} kode, {r['mulai']} s/d {r['akhir']}")
    print(f"  status: {r['status']}")
    print(f"  tidak ada di harga Yahoo: {len(r['tidak_ada_di_harga_yahoo'])}; DES tanpa data IDX: {len(r['des_tanpa_idx'])}")
    print(f"  faktor aksi korporasi: {r['faktor']}")
    print(f"  kode dengan periode beku (>= {BEKU_MIN} hari tanpa transaksi): {r['beku_kode']}")
    print(f"  dividen: {r['dividen_kejadian']} kejadian, dividen IDX tanpa nilai: {r['dividen_idx_tanpa_nilai']}")
    print(f"  sumber open: {r['sumber_open']}")
    print(f"  sumber dividen: {r['dividen_sumber']}")
    print(f"  validasi vs harga Yahoo ({v['kode']} kode, {v['hari_saham']} hari-saham): |selisih return| median {v['median']:.6f}, p99 {v['p99']:.4f}, "
          f"p99.9 {v['p999']:.4f}, beda > 1% {v['persen_beda_1pct']:.2f}%, identik {v['persen_identik']:.1f}%")
    print(f"  sidik: {r['sidik']['sidik']}")
    print("SELESAI")


def utama():
    perintah = sys.argv[1] if len(sys.argv) > 1 else "bangun"
    if perintah == "bangun":
        cetak(bangun())
    elif perintah == "ringkas":
        cetak(dt.db()[INFO].find_one({"_id": "_ringkasan"}))


if __name__ == "__main__":
    utama()
