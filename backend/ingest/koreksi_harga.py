import argparse
import io
import json
from datetime import datetime

import numpy as np
import pandas as pd

from backend.core.config import ROOT
from backend.db import data as dt

KOLEKSI = "koreksi_harga"
HARGA = ["open", "high", "low", "close", "adj_close"]
TOL = 0.005
IDX_MULAI = pd.Timestamp("2020-01-01")
AMBANG_CA = 0.02
AMBANG_SEL = 0.05
NAIK, TURUN = 1.36, 0.64
BALIK = 10
RASIO_BERSIH = [2, 3, 4, 5, 10, 20, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20]


def aturan(kode=None):
    q = {"status": "aktif"}
    if kode is not None:
        q["kode"] = kode
    return list(dt.db()[KOLEKSI].find(q))


def _dekat(a, b, tol=TOL):
    return a == a and b == b and b != 0 and abs(a / b - 1) <= tol


def terapkan(df, kode, daftar=None):
    if df is None or df.empty:
        return df, []
    daftar = aturan(kode) if daftar is None else [r for r in daftar if r["kode"] == kode]
    if not daftar:
        return df, []
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if "volume" in df:
        df["volume"] = df["volume"].astype(float)
    catatan = []
    for r in sorted([r for r in daftar if r["jenis"] == "faktor"], key=lambda r: r["ex_date"], reverse=True):
        batas = pd.Timestamp(r["berlaku_sebelum"])
        m = df.index < batas
        if not m.any():
            continue
        acuan = pd.Timestamp(r["acuan"]["tgl"])
        if acuan not in df.index:
            catatan.append(f"{kode} faktor {r['ex_date']}: baris acuan {acuan.date()} tidak ada, tidak diterapkan")
            continue
        v = float(df.at[acuan, "close"])
        if _dekat(v, r["acuan"]["close_asli"]):
            f = float(r["faktor"])
            for k in HARGA:
                if k in df:
                    df.loc[m, k] = df.loc[m, k] * f
            if "volume" in df:
                df.loc[m, "volume"] = df.loc[m, "volume"] / f
        elif _dekat(v, r["acuan"]["close_asli"] * r["faktor"]):
            catatan.append(f"{kode} faktor {r['ex_date']}: sumber sudah menyesuaikan, dilewati")
        else:
            catatan.append(f"{kode} faktor {r['ex_date']}: close acuan {v:g} tidak cocok dengan {r['acuan']['close_asli']:g}, dilewati")
    for r in [r for r in daftar if r["jenis"] == "sel"]:
        t = pd.Timestamp(r["tgl"])
        if t not in df.index:
            continue
        if not _dekat(float(df.at[t, "close"]), r["asli"]["close"]):
            catatan.append(f"{kode} sel {t.date()}: close {df.at[t, 'close']:g} tidak cocok dengan {r['asli']['close']:g}, dilewati")
            continue
        for k, v in r["baru"].items():
            if k in df:
                df.at[t, k] = v
    hapus = []
    for r in [r for r in daftar if r["jenis"] == "hapus_rentang"]:
        m = (df.index >= pd.Timestamp(r["dari"])) & (df.index <= pd.Timestamp(r["sampai"]))
        cocok = m & (df["volume"] == 0) & (np.abs(df["close"] / r["close"] - 1) <= TOL)
        if m.sum() != cocok.sum():
            catatan.append(f"{kode} hapus rentang {r['dari']}..{r['sampai']}: {int(m.sum() - cocok.sum())} baris tidak beku, hanya yang beku dibuang")
        hapus += list(df.index[cocok])
    for r in [r for r in daftar if r["jenis"] == "hapus"]:
        t = pd.Timestamp(r["tgl"])
        if t not in df.index:
            continue
        if _dekat(float(df.at[t, "close"]), r["asli"]["close"]):
            hapus.append(t)
        else:
            catatan.append(f"{kode} hapus {t.date()}: close {df.at[t, 'close']:g} tidak cocok dengan {r['asli']['close']:g}, dilewati")
    if hapus:
        df = df.drop(index=hapus)
    return df, catatan


def batas_terbaru(kode, daftar=None):
    daftar = aturan(kode) if daftar is None else [r for r in daftar if r["kode"] == kode]
    tgl = [pd.Timestamp(r["berlaku_sebelum"]) for r in daftar if r["jenis"] == "faktor"]
    return max(tgl) if tgl else None


def idx_resmi():
    i = dt.baca("idx_harian")[["StockCode", "tgl", "Close", "OpenPrice", "High", "Low", "Volume", "Previous"]].copy()
    i["tgl"] = pd.to_datetime(i["tgl"])
    i = i.sort_values("tgl")
    i["prev_close"] = i.groupby("StockCode")["Close"].shift(1)
    return {k: g.drop_duplicates("tgl").set_index("tgl") for k, g in i.groupby("StockCode")}


def faktor_idx(g):
    f = (g["Previous"] / g["prev_close"]).where((g["Previous"] > 0) & (g["prev_close"] > 0))
    return f[(f - 1).abs() > AMBANG_CA].dropna()


def kali_e(index, f):
    E = pd.Series(1.0, index=index)
    for d, v in f.items():
        E[E.index < d] *= v
    return E


def baris_asli(df, t):
    return {k: (float(df.at[t, k]) if k in df and df.at[t, k] == df.at[t, k] else None) for k in HARGA + ["volume"]}


def usulan_pra2020(kode, df):
    hasil = []
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    c = df["close"].to_numpy()
    v = df["volume"].to_numpy()
    idx = df.index
    sp = df["stock_splits"].fillna(0) if "stock_splits" in df else pd.Series(0.0, index=idx)
    adasplit = set(sp[sp > 0].index)
    i = 1
    while i < len(c):
        if idx[i] >= IDX_MULAI:
            break
        r = c[i] / c[i - 1]
        luar_masuk = r > NAIK or r < TURUN
        if (luar_masuk or r > 1.25 or r < 0.8) and c[i - 1] >= 50 and idx[i] not in adasplit:
            pra = c[i - 1]
            for j in range(i + 1, min(i + 1 + BALIK, len(c))):
                keluar = c[j] / c[j - 1]
                kembali = (1 / 1.25 < c[j] / pra < 1.25) if luar_masuk else ((1 / 1.1 < c[j] / pra < 1.1) and (keluar > NAIK or keluar < TURUN))
                if kembali:
                    if idx[j] in adasplit:
                        break
                    bukti = {"close_sebelum": float(pra), "tgl_sebelum": str(idx[i - 1].date()), "close_sesudah": float(c[j]), "tgl_sesudah": str(idx[j].date()),
                             "hari": j - i, "lompatan_masuk": round(float(r), 4), "lompatan_keluar": round(float(keluar), 4),
                             "di_luar_batas": "masuk" if luar_masuk else "keluar"}
                    for q in range(i, j):
                        t = idx[q]
                        asli = baris_asli(df, t)
                        est = pra / c[q]
                        snap = min(RASIO_BERSIH, key=lambda s: abs(np.log(est / s)))
                        if v[q] == 0:
                            rasio_adj = asli["adj_close"] / asli["close"] if asli["adj_close"] else 1.0
                            baru = {"open": float(pra), "high": float(pra), "low": float(pra), "close": float(pra), "adj_close": float(pra * rasio_adj)}
                            hasil.append({"jenis": "sel", "kode": kode, "tgl": str(t.date()), "asli": asli, "baru": baru, "cara": "tanpa_transaksi",
                                          "kategori": "K1", "alasan": "Hari tanpa transaksi (volume 0) dengan harga melompat di luar batas ARA/ARB lalu kembali: diisi close terakhir sebelum lompatan.",
                                          "bukti": bukti})
                        elif abs(np.log(est / snap)) < 0.06:
                            baru = {k: asli[k] * snap for k in HARGA if asli[k] is not None}
                            baru["volume"] = asli["volume"] / snap
                            hasil.append({"jenis": "sel", "kode": kode, "tgl": str(t.date()), "asli": asli, "baru": baru, "cara": f"kali_{snap:g}",
                                          "kategori": "K1", "alasan": f"Harga salah skala ±{1 / snap if snap < 1 else snap:g}x selama {j - i} hari bursa lalu kembali; dikali balik {snap:g} (rasio bersih).",
                                          "bukti": {**bukti, "estimasi_faktor": round(float(est), 4)}})
                        else:
                            hasil.append({"jenis": "hapus", "kode": kode, "tgl": str(t.date()), "asli": asli, "cara": "hapus_baris", "kategori": "K1",
                                          "alasan": "Harga melompat di luar batas ARA/ARB lalu kembali dengan rasio tidak bersih; nilai benar tidak diketahui, baris dibuang (dianggap hari tanpa data).",
                                          "bukti": {**bukti, "estimasi_faktor": round(float(est), 4)}})
                    i = j
                    break
        i += 1
    return hasil


def faktor_yahoo(kode, df, g):
    hasil = []
    f_all = faktor_idx(g)
    sp = df["stock_splits"].fillna(0) if "stock_splits" in df else pd.Series(0.0, index=df.index)
    kerja = df.copy()
    kerja["volume"] = kerja["volume"].astype(float)
    for ex, f in sorted(f_all.items(), key=lambda x: x[0], reverse=True):
        j = kerja[["close", "volume"]].join(g[["Close", "Volume"]], how="inner")
        j = j[(j["close"] > 0) & (j["Close"] > 0)]
        E = kali_e(j.index, f_all)
        D = np.log(j["close"] / (j["Close"] * E))
        sebelum = D[(D.index < ex) & (j["Volume"] > 0) & (j["volume"] > 0)]
        if len(sebelum) < 3:
            continue
        jendela = []
        for t in reversed(sebelum.index[-60:]):
            if abs(sebelum[t]) < 0.02:
                jendela.append(t)
            else:
                break
        luar = sebelum[sebelum.index < (jendela[-1] if jendela else ex)]
        if len(luar) < 3:
            continue
        lewat = luar.iloc[-min(10, len(luar)):]
        c = float(np.exp(lewat.median()))
        if abs(np.log(c)) < 0.02 or not (np.abs(lewat - np.log(c)) < 0.02).mean() >= 0.8:
            continue
        terap = 1 / c
        luput = abs(np.log(c * f)) < 0.02
        ada_split = bool(((sp.index >= ex - pd.Timedelta(days=10)) & (sp.index <= ex + pd.Timedelta(days=10)) & (sp > 0)).any())
        if not jendela and abs(f - 1) < 0.10 and not ada_split:
            hasil.append({"jenis": "periksa", "kode": kode, "ex_date": str(ex.date()), "faktor_idx": round(float(f), 6), "rasio_yahoo_idx": round(c, 4),
                          "alasan": "Harga acuan IDX berubah < 10% tanpa jendela penyesuaian Yahoo dan tanpa split tercatat: bisa aksi korporasi kecil atau reset harga acuan (mis. saham suspensi). Tidak dikoreksi."})
            continue
        batas = jendela[-1] if jendela else ex
        sblm = kerja.index[kerja.index < batas]
        acuan = sblm[-1]
        sebab = ("tidak disesuaikan Yahoo" if luput else f"disesuaikan Yahoo dengan faktor berbeda dari IDX (Yahoo/IDX {c:.4f} sebelum ex-date)")
        hasil.append({"jenis": "faktor", "kode": kode, "ex_date": str(ex.date()), "faktor": round(terap, 6), "faktor_idx": round(float(f), 6), "berlaku_sebelum": str(batas.date()),
                      "acuan": {"tgl": str(acuan.date()), "close_asli": float(kerja.at[acuan, "close"])}, "kategori": "K2", "luput": bool(luput),
                      "alasan": (f"Aksi korporasi ex-date {ex.date()} (harga acuan IDX {g.at[ex, 'Previous']:g} vs close kemarin {g.at[ex, 'prev_close']:g}, faktor IDX {f:.4f}) "
                                 f"{sebab} untuk baris sebelum {batas.date()}" + (f" (Yahoo hanya menyesuaikan {len(jendela)} hari bursa sebelum ex-date)" if jendela else "") +
                                 f". Semua harga sebelum tanggal itu dikali {terap:.6f} supaya sama dengan close IDX × faktor IDX, volume dibagi."),
                      "bukti": {"previous_idx": float(g.at[ex, "Previous"]), "close_kemarin_idx": float(g.at[ex, "prev_close"]), "hari_jendela_yahoo": len(jendela),
                                "rasio_yahoo_idx_sebelum_jendela": round(c, 4), "split_yahoo_dekat": ada_split}})
        m = kerja.index < batas
        for k in HARGA:
            kerja.loc[m, k] = kerja.loc[m, k] * terap
        kerja.loc[m, "volume"] = kerja.loc[m, "volume"] / terap
    return hasil, kerja


def sel_idx(kode, df, kerja, g):
    hasil = []
    f_all = faktor_idx(g)
    j = kerja.join(g[["Close", "OpenPrice", "High", "Low", "Volume"]], how="inner")
    j = j[(j["close"] > 0) & (j["Close"] > 0)]
    if j.empty:
        return hasil
    E = kali_e(j.index, f_all)
    D = j["close"] / (j["Close"] * E)
    baik = (np.abs(np.log(D)) < 0.02) & (j["volume"] > 0)
    Dlok = D.where(baik).rolling(21, center=True, min_periods=1).median().ffill().bfill().fillna(1.0)
    salah = (np.abs(np.log(D / Dlok)) > np.log(1 + AMBANG_SEL)) | ((j["volume"] == 0) & (j["Volume"] > 0) & (np.abs(np.log(D / Dlok)) > 0.005))
    for t in j.index[salah]:
        skala = float(E[t] * Dlok[t])
        asli_kerja = baris_asli(kerja, t)
        cl = float(j.at[t, "Close"]) * skala
        op = float(j.at[t, "OpenPrice"]) * skala if j.at[t, "OpenPrice"] > 0 else (asli_kerja["open"] * cl / asli_kerja["close"] if j.at[t, "volume"] > 0 else cl)
        hi = float(j.at[t, "High"]) * skala if j.at[t, "High"] > 0 else max(op, cl)
        lo = float(j.at[t, "Low"]) * skala if j.at[t, "Low"] > 0 else min(op, cl)
        rasio_adj = asli_kerja["adj_close"] / asli_kerja["close"] if asli_kerja["adj_close"] else 1.0
        baru = {"open": op, "high": max(hi, op, cl), "low": min(lo, op, cl), "close": cl, "adj_close": cl * rasio_adj, "volume": float(j.at[t, "Volume"]) / skala}
        jenis_salah = "bar basi (volume Yahoo 0, IDX ada transaksi)" if (j.at[t, "volume"] == 0 and j.at[t, "Volume"] > 0) else "close Yahoo menyimpang dari close IDX"
        hasil.append({"jenis": "sel", "kode": kode, "tgl": str(t.date()), "asli": asli_kerja, "asli_yahoo": baris_asli(df, t), "baru": baru, "cara": "idx",
                      "kategori": "K3" if "basi" in jenis_salah else "K4",
                      "alasan": f"{jenis_salah} {D[t]:.4f}x; diganti data resmi IDX (close {j.at[t, 'Close']:g}, open {j.at[t, 'OpenPrice']:g}, volume {j.at[t, 'Volume']:g}) × faktor penyesuaian {skala:.6f}.",
                      "bukti": {"idx_close": float(j.at[t, "Close"]), "idx_open": float(j.at[t, "OpenPrice"]), "idx_volume": float(j.at[t, "Volume"]),
                                "yahoo_close": float(df.at[t, "close"]), "yahoo_volume": float(df.at[t, "volume"]), "faktor_ca": float(E[t]), "rasio_lokal": float(Dlok[t])}})
    return hasil


def beku_pra2020(k, kerja, sel):
    pra = kerja[kerja.index < IDX_MULAI]
    pasca = kerja[kerja.index >= IDX_MULAI]
    if pra.empty or pasca.empty:
        return []
    t0 = pasca.index[0]
    s0 = [r for r in sel if r["tgl"] == str(t0.date())]
    if not s0 or pasca["volume"].iloc[0] != 0:
        return []
    v = float(pra["close"].iloc[-1])
    beku = (pra["volume"] == 0) & (np.abs(pra["close"] / v - 1) <= 1e-9)
    if not beku.iloc[-1]:
        return []
    putus = (~beku)[::-1].cumsum()[::-1]
    run = pra.index[beku & (putus == 0)]
    if len(run) < 5 or abs(float(pasca["close"].iloc[0]) / v - 1) > 1e-9:
        return []
    return [{"jenis": "hapus_rentang", "kode": k, "dari": str(run[0].date()), "sampai": str(run[-1].date()), "close": v, "jumlah": len(run), "cara": "hapus_beku",
             "kategori": "K3",
             "alasan": (f"Harga Yahoo beku di {v:g} dengan volume 0 selama {len(run)} hari bursa ({run[0].date()} s/d {run[-1].date()}) dan berlanjut ke 2020, "
                        f"padahal data resmi IDX 2020 menunjukkan harga lain ({s0[0]['bukti']['idx_close']:g}). Baris beku dianggap tanpa data."),
             "bukti": {"idx_close_hari_pertama_2020": s0[0]["bukti"]["idx_close"], "idx_volume_hari_pertama_2020": s0[0]["bukti"]["idx_volume"],
                       "transaksi_terakhir_yahoo": str(pra.index[pra["volume"] > 0].max().date()) if (pra["volume"] > 0).any() else None}}]


def usulan(kode_daftar=None):
    resmi = idx_resmi()
    kode_daftar = kode_daftar or dt.daftar("harga")
    semua = []
    for k, df in dt.baca_banyak("harga", sorted(kode_daftar)).items():
        df = df.sort_index().copy()
        df.index = pd.to_datetime(df.index)
        df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
        kerja = df
        if k in resmi:
            fk, kerja = faktor_yahoo(k, df, resmi[k])
            semua += fk
        semua += usulan_pra2020(k, kerja)
        if k in resmi:
            sel = sel_idx(k, df, kerja, resmi[k])
            semua += sel
            semua += beku_pra2020(k, kerja, sel)
    for r in semua:
        r["_id"] = f"{r['jenis']}:{r['kode']}:{r.get('tgl') or r.get('ex_date') or r.get('dari')}"
        r["status"] = "aktif" if r["jenis"] != "periksa" else "periksa"
        r["berlaku"] = ["harga"]
    return semua


def arsipkan(kode_daftar, label):
    for k, df in dt.baca_banyak("harga", sorted(kode_daftar)).items():
        buf = io.BytesIO()
        df.to_csv(buf)
        dt.simpan_arsip(f"harga_asli/{label}/{k}.csv", buf.getvalue(), folder="harga_asli")


def simpan(daftar, disetujui):
    c = dt.db()[KOLEKSI]
    sekarang = datetime.now()
    for r in daftar:
        c.replace_one({"_id": r["_id"]}, {**r, "disetujui": disetujui, "dibuat": sekarang}, upsert=True)


def terapkan_db(kode_daftar, koleksi="harga"):
    log = []
    for k in sorted(kode_daftar):
        df = dt.baca(f"{koleksi}/{k}")
        if df is None:
            continue
        baru, cat = terapkan(df, k)
        log += cat
        dt.tulis(f"{koleksi}/{k}", baru)
    return log


FAKTOR_EKSTREM = (0.2, 5.0)


def nilai_baru(r):
    if r["jenis"] != "faktor":
        return "tahan", "bukan aksi korporasi (sel/hapus data); diputuskan user"
    f = r["faktor_idx"]
    if not (FAKTOR_EKSTREM[0] <= f <= FAKTOR_EKSTREM[1]):
        return "tahan", f"faktor IDX ekstrem ({f:.4f})"
    if not r.get("luput", False):
        return "tahan", f"Yahoo menyesuaikan dengan faktor lain (Yahoo/IDX {r['bukti']['rasio_yahoo_idx_sebelum_jendela']})"
    if r["bukti"].get("split_yahoo_dekat"):
        df = dt.baca(f"harga/{r['kode']}")
        df.index = pd.to_datetime(df.index)
        ex = pd.Timestamp(r["ex_date"])
        sp = df["stock_splits"][(df.index >= ex - pd.Timedelta(days=10)) & (df.index <= ex + pd.Timedelta(days=10))]
        sp = sp[sp > 0]
        if len(sp) and abs(np.log(float(sp.iloc[0]) * f)) > 0.05:
            return "tahan", f"split Yahoo {float(sp.iloc[0]):g} tidak cocok dengan faktor IDX {f:.4f}"
    return "aktif", "otomatis: faktor resmi IDX (Previous / close kemarin)"


def perbarui_otomatis(tulis=True):
    c = dt.db()[KOLEKSI]
    ada = {d["_id"] for d in c.find({}, {"_id": 1})}
    baru = [r for r in usulan() if r["_id"] not in ada and r["jenis"] != "periksa"]
    hasil = {"waktu": datetime.now(), "aktif": [], "tahan": []}
    for r in baru:
        st, alasan = nilai_baru(r)
        r["status"] = st
        r["keputusan"] = alasan
        hasil[st].append({"_id": r["_id"], "kode": r["kode"], "jenis": r["jenis"], "keputusan": alasan})
    if tulis and baru:
        simpan(baru, "otomatis " + datetime.now().strftime("%Y-%m-%d"))
        aktif = [r for r in baru if r["status"] == "aktif"]
        for k in sorted({r["kode"] for r in aktif}):
            df = dt.baca(f"harga/{k}")
            if df is None:
                continue
            buf = io.BytesIO()
            df.to_csv(buf)
            dt.simpan_arsip(f"harga_asli/{datetime.now():%Y-%m-%d}/{k}.csv", buf.getvalue(), folder="harga_asli")
            df2, _ = terapkan(df, k, aktif)
            dt.tulis(f"harga/{k}", df2)
    if tulis:
        dt.db()["koreksi_harga_log"].insert_one({**hasil, "jumlah_aktif": len(hasil["aktif"]), "jumlah_tahan": len(hasil["tahan"])})
    return hasil


BERKAS = ROOT / "data" / "koreksi_harga.jsonl"


def _ke_teks(v):
    if isinstance(v, datetime):
        return {"$tgl": v.isoformat(timespec="seconds")}
    if isinstance(v, dict):
        return {k: _ke_teks(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_ke_teks(x) for x in v]
    if isinstance(v, float):
        return round(v, 8)
    if isinstance(v, np.generic):
        return _ke_teks(v.item())
    return v


def _dari_teks(v):
    if isinstance(v, dict):
        if set(v) == {"$tgl"}:
            return datetime.fromisoformat(v["$tgl"])
        return {k: _dari_teks(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_dari_teks(x) for x in v]
    return v


def ekspor(berkas=BERKAS):
    docs = sorted(dt.db()[KOLEKSI].find({}), key=lambda d: str(d["_id"]))
    berkas.parent.mkdir(parents=True, exist_ok=True)
    with open(berkas, "w", encoding="utf-8", newline=chr(10)) as f:
        for d in docs:
            f.write(json.dumps(_ke_teks(d), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + chr(10))
    hitung = pd.Series([d.get("status") for d in docs]).value_counts().to_dict()
    print(f"ekspor {len(docs)} aturan ke {berkas.relative_to(ROOT)} ({berkas.stat().st_size / 1e6:.1f} MB): {hitung}")
    return len(docs)


def impor(berkas=BERKAS):
    c = dt.db()[KOLEKSI]
    n = 0
    with open(berkas, encoding="utf-8") as f:
        for baris in f:
            if baris.strip():
                d = _dari_teks(json.loads(baris))
                c.replace_one({"_id": d["_id"]}, d, upsert=True)
                n += 1
    print(f"impor {n} aturan dari {berkas.relative_to(ROOT)} ke {dt.NAMA_DB}.{KOLEKSI} (data harga tidak diubah; koreksi berlaku lagi di unduhan berikutnya)")
    return n


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("aksi", choices=["ringkas", "ekspor", "impor"])
    a = ap.parse_args()
    if a.aksi == "ekspor":
        ekspor()
        print("SELESAI")
        return
    if a.aksi == "impor":
        impor()
        print("SELESAI")
        return
    d = pd.DataFrame(aturan())
    print(json.dumps(d.groupby(["jenis", "kategori"]).size().to_dict() if len(d) else {}, default=str))


if __name__ == "__main__":
    utama()
