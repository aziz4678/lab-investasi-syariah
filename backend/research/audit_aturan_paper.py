import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import isi_backtest as ib
from backend.db import koneksi as kdb
from backend.paper import batas_paper as bp
from backend.paper import pantau
from backend.research import ambang_pantau as ap
from backend.research import screener as sc
from backend.research import simulasi_h29 as s29
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

BATAS_DATA = pd.Timestamp("2026-10-30")
MULAI_20 = pd.Timestamp("2020-01-01")
DEV = (pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31"))
MULAI_JENDELA_DEV = pd.Timestamp("2011-01-03")
JALUR = 5000
BLOK = 20
SEED = 20261022
L = 1260
LANGKAH = 5
HORIZON = [63, 125, 250]
SEED_NULL = range(1001, 1201)
SIM_NORMAL = range(1, 101)
JALUR_PER_NULL = 25
MAKS_TRADE = 80
BIAYA_SISI = 0.0020
TARGET = {"gagal": 0.05, "waspada": 0.10}


def db():
    return kdb.koneksi()


def bootstrap(r, n, rng, panjang=L):
    r = np.asarray(r, float)
    k = int(np.ceil(panjang / BLOK))
    awal = rng.integers(0, len(r), size=(n, k))
    idx = (awal[:, :, None] + np.arange(BLOK)[None, None, :]) % len(r)
    return np.cumprod(1 + r[idx.reshape(n, -1)[:, :panjang]], axis=1)


def jendela(v, mulai, panjang, langkah=LANGKAH):
    s = v.to_numpy(float)
    a = np.searchsorted(v.index.to_numpy(), np.datetime64(mulai))
    awal = np.arange(a, len(s) - panjang, langkah)
    idx = awal[:, None] + np.arange(1, panjang + 1)[None, :]
    return s[idx] / s[awal][:, None], v.index[awal], v.index[np.minimum(awal + panjang, len(s) - 1)], awal


def ret_dd(x):
    puncak = np.maximum.accumulate(np.maximum(x, 1.0), axis=1)
    return ((x - 1) * 100).astype(np.float32), (np.minimum.accumulate(x / puncak - 1, axis=1) * 100).astype(np.float32)


def streak_iid(net, n, rng):
    if len(net) == 0:
        return np.zeros((n, MAKS_TRADE), int)
    c = rng.choice(np.asarray(net) <= 0, size=(n, MAKS_TRADE), replace=True)
    out = np.zeros((n, MAKS_TRADE), int)
    jalan = np.zeros(n, int)
    besar = np.zeros(n, int)
    for k in range(MAKS_TRADE):
        jalan = np.where(c[:, k], jalan + 1, 0)
        besar = np.maximum(besar, jalan)
        out[:, k] = besar
    return out


def streak_seq(net):
    out = np.zeros(MAKS_TRADE, int)
    jalan = besar = 0
    for k, x in enumerate(net[:MAKS_TRADE]):
        jalan = jalan + 1 if x <= 0 else 0
        besar = max(besar, jalan)
        out[k] = besar
    if len(net) < MAKS_TRADE:
        out[len(net):] = besar
    return out


class Set:
    def __init__(self, nama, x, streak=None, ntrade=None):
        self.nama, self.x = nama, x
        self.ret, self.dd = ret_dd(x[:, :500]) if x.shape[1] >= 500 else ret_dd(x)
        self.streak, self.ntrade = streak, ntrade

    def trade_t(self, T):
        if self.streak is None:
            return None, None
        if callable(self.ntrade):
            return self.streak(T), self.ntrade(T)
        return self.streak, np.full(len(self.x), int(round(self.ntrade * T)))


def pita_v1(b):
    return {"ret_w": np.array(b["return"]["p5"]), "dd_w": np.array(b["dd"]["p5"]), "ber_w": np.array(b["beruntun"]["p95"]) if "beruntun" in b else None,
            "ret_g": np.array(b["return"]["p1"]) if "p1" in b["return"] else None, "dd_g": np.array(b["dd"]["p1"]) if "p1" in b["dd"] and b.get("gagal", True) else None,
            "ber_g": np.array(b["beruntun"]["p99"]) if "beruntun" in b else None}


def flag(S, T, ret_b, dd_b, ber_b, mulai_ret):
    h = np.arange(1, T + 1)
    f = np.zeros(len(S.x), bool)
    if ret_b is not None:
        f |= ((h >= mulai_ret) & (S.ret[:, :T] < np.asarray(ret_b)[:T])).any(axis=1)
    if dd_b is not None:
        f |= (S.dd[:, :T] < np.asarray(dd_b)[:T]).any(axis=1)
    st, n = S.trade_t(T)
    if ber_b is not None and st is not None:
        k = np.minimum(n, len(ber_b))
        lebih = st[:, :len(ber_b)] > ber_b[None, :]
        ada = lebih & (np.arange(len(ber_b))[None, :] < k[:, None])
        f |= ada.any(axis=1)
    return f


def zona(S, T, p, gagal=True):
    w = flag(S, T, p["ret_w"], p["dd_w"], p["ber_w"], 21)
    g = flag(S, T, p["ret_g"], p["dd_g"], p["ber_g"], 63) if gagal and p.get("ret_g") is not None else np.zeros(len(S.x), bool)
    d45 = (S.dd[:, :T] < pantau.BATAS_DD).any(axis=1)
    return {"waspada": w | g, "gagal": g, "gagal_dd45": g | d45, "dd45": d45, "lolos_h11a": ~(w | g | d45), "lolos_h29": ~d45, "lolos_h29_ketat": ~(w | d45)}


def pct(x):
    return round(float(np.mean(x) * 100), 1)


def pita_simultan(S, q, beruntun=True):
    r = {"ret": np.percentile(S.ret[:, :500], q, axis=0), "dd": np.percentile(S.dd[:, :500], q, axis=0)}
    st, _ = S.trade_t(250)
    r["ber"] = np.percentile(st, 100 - q, axis=0) if beruntun and st is not None else None
    return r


def cari_q(S, target, mulai_ret, beruntun=True, T=250):
    lo, hi = 0.001, 20.0
    for _ in range(40):
        q = (lo + hi) / 2
        b = pita_simultan(S, q, beruntun)
        p = flag(S, T, b["ret"], b["dd"], b["ber"], mulai_ret).mean()
        lo, hi = (q, hi) if p < target else (lo, q)
    q = (lo + hi) / 2
    return q, pita_simultan(S, q, beruntun)


def cari_q_akhir(S, target, T=250):
    lo, hi = 0.001, 20.0
    for _ in range(40):
        q = (lo + hi) / 2
        r, d = np.percentile(S.ret[:, T - 1], q), np.percentile(S.dd[:, T - 1], q)
        p = ((S.ret[:, T - 1] < r) | (S.dd[:, T - 1] < d)).mean()
        lo, hi = (q, hi) if p < target else (lo, q)
    q = (lo + hi) / 2
    return q, float(np.percentile(S.ret[:, T - 1], q)), float(np.percentile(S.dd[:, T - 1], q))


def kena_akhir(S, r, d, T=250):
    return (S.ret[:, T - 1] < r) | (S.dd[:, T - 1] < d)


def ew_biaya(siap, mulai, akhir):
    hari = pd.DatetimeIndex(sorted(set().union(*[x.index for x in siap.values()])))
    hari = hari[(hari >= mulai - pd.Timedelta(days=40)) & (hari <= akhir)]
    C = pd.DataFrame({k: x["close"] for k, x in siap.items()}).reindex(hari).ffill()
    CR = pd.DataFrame({k: x["close_mentah"] for k, x in siap.items()}).reindex(hari).ffill()
    Lo = pd.DataFrame({k: x["lolos"] for k, x in siap.items()}).reindex(hari).fillna(False).astype(bool)
    ab = pd.Series(hari, index=hari).groupby(hari.to_period("M")).max()
    reb = [t for t in ab if t >= mulai - pd.Timedelta(days=40)]
    Cv, CRv, Lv = C.to_numpy(float), CR.to_numpy(float), Lo.to_numpy(bool)
    pos = {t: i for i, t in enumerate(hari)}
    nilai = np.full(len(hari), np.nan)
    v, w, i0 = 1.0, None, None
    for t in reb:
        i = pos[t]
        if w is not None and w.sum() > 0:
            rel = np.where(np.isfinite(Cv[i0:i + 1]) & np.isfinite(Cv[i0])[None, :], Cv[i0:i + 1] / np.where(Cv[i0] > 0, Cv[i0], np.nan), 1.0)
            rel = np.nan_to_num(rel, nan=1.0)
            seg = (w[None, :] * rel).sum(axis=1)
            nilai[i0:i + 1] = v * seg
            v = v * seg[-1]
            wd = w * rel[-1] / seg[-1]
        else:
            wd = np.zeros(Cv.shape[1])
        ok = Lv[i] & np.isfinite(Cv[i]) & (Cv[i] > 0)
        if not ok.any():
            nilai[i] = v
            w, i0 = wd, i
            continue
        wn = np.where(ok, 1.0 / ok.sum(), 0.0)
        c = BIAYA_SISI + np.where(CRv[i] > 0, sc.fraksi(np.nan_to_num(CRv[i], nan=1.0)) / np.where(CRv[i] > 0, CRv[i], 1.0), 0.0)
        v *= 1 - float((np.abs(wn - wd) * c).sum())
        nilai[i] = v
        w, i0 = wn, i
    s = pd.Series(nilai, index=hari).dropna()
    return s[s.index >= mulai - pd.Timedelta(days=40)]


def jii():
    return dt.baca("indeks/JKII")["close"].dropna()


def kurva_h11a(siap, tr, mulai, akhir, seeds):
    mentah = {t: hg.mentah(t) for t in tr["ticker"].unique()}
    dok = ib.dokumen_trade("x", tr, set(), siap)
    out = []
    for seed in seeds:
        pilih = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        ds = [dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)]
        _, h = ib.kurva_paper(ds, mulai, akhir, mentah)
        jual = sorted((pd.Timestamp(x["tgl_jual"]), x["net"]) for x in ds if x["dipilih"] and x["status"] == "selesai")
        out.append((h, jual))
    return out


def sinyal_acak(p, rng):
    return lambda x: pd.Series(rng.random(len(x)) < p, index=x.index)


def null_acak(siap, mulai, akhir, p, seeds):
    mentah = {t: hg.mentah(t) for t in siap}
    out = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        tr = ut.kumpulkan(siap, sinyal_acak(p, rng))
        tr = tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].reset_index(drop=True)
        tr = ib.konservatif(tr, siap).reset_index(drop=True)
        dok = ib.dokumen_trade("x", tr, set(), siap)
        pilih = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        ds = [dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)]
        _, h = ib.kurva_paper(ds, mulai, min(akhir, tr["tgl_exit"].max()), {t: mentah[t] for t in tr["ticker"].unique()})
        jual = sorted((pd.Timestamp(x["tgl_jual"]), x["net"]) for x in ds if x["dipilih"] and x["status"] == "selesai")
        out.append((h, jual))
        if (seed - SEED_NULL[0] + 1) % 25 == 0:
            print(f"    null acak {seed - SEED_NULL[0] + 1}/{len(seeds)}", flush=True)
    return out


def peluang_sinyal(siap):
    s = sum(int((x["lolos"] & (x["close"] >= x["maks250"])).sum()) for x in siap.values())
    n = sum(int(x["lolos"].sum()) for x in siap.values())
    return s / n


def set_jendela(nama, kurva_jual, mulai, panjang=250, langkah=LANGKAH):
    xs, sts = [], []
    for h, jual in kurva_jual:
        x, a, z, _ = jendela(h, mulai, panjang, langkah)
        xs.append(x)
        if jual is not None:
            tj = np.array([t.to_datetime64() for t, _ in jual]) if jual else np.array([], "datetime64[ns]")
            nj = np.array([n for _, n in jual], float)
            hi = h.index.to_numpy()
            for i in range(len(a)):
                a_ = a[i].to_datetime64()
                m_ = tj > a_
                sts.append((tj[m_], nj[m_], hi, np.searchsorted(hi, a_)))
    x = np.concatenate(xs).astype(np.float32)
    if not sts:
        return Set(nama, x)
    cache = {}

    def streak(T):
        if T not in cache:
            arr, cnt = np.zeros((len(sts), MAKS_TRADE), int), np.zeros(len(sts), int)
            for i, (tj, nj, hi, s0) in enumerate(sts):
                batas = hi[min(s0 + T, len(hi) - 1)]
                mm = tj <= batas
                arr[i] = streak_seq(nj[mm])
                cnt[i] = int(mm.sum())
            cache[T] = (arr, cnt)
        return cache[T][0]

    def ntrade(T):
        streak(T)
        return cache[T][1]
    return Set(nama, x, streak, ntrade)


def set_bootstrap(nama, kurva_jual, rng, per_kurva=None, n_total=JALUR):
    xs, sts, rate = [], [], []
    per = per_kurva or n_total
    for h, jual in kurva_jual:
        r = h.pct_change().dropna().to_numpy()
        xs.append(bootstrap(r, per, rng))
        if jual is not None:
            net = np.array([n for _, n in jual], float)
            sts.append(streak_iid(net, per, rng))
            rate.append(len(net) / len(h))
    x = np.concatenate(xs)
    if not sts:
        return Set(nama, x)
    st = np.concatenate(sts)
    rt = np.repeat(rate, per)
    return Set(nama, x, lambda T: st, lambda T: np.round(rt * T).astype(int))


def horizon_minimum(normal, nulls):
    hasil = {}
    for nn, nx in nulls.items():
        ketemu = None
        baris = []
        for bln in range(1, 61):
            T = 21 * bln
            a, b = normal(T), nx(T)
            if a is None or b is None or len(a) < 20 or len(b) < 20:
                baris.append({"bulan": bln, "p_null": None})
                continue
            thr = np.percentile(a, 20)
            pn = float((b >= thr).mean())
            baris.append({"bulan": bln, "ambang_return_pct": round(float(thr * 100), 1), "p_null": round(pn * 100, 1), "n_normal": len(a), "n_null": len(b)})
            if ketemu is None and pn <= 0.10:
                ketemu = bln
        hasil[nn] = {"bulan_minimum": ketemu, "per_bulan": [baris[i] for i in (2, 5, 11, 17, 23, 35, 47, 59) if i < len(baris)]}
    return hasil


def akhir_jendela(kurva, mulai):
    seri = [h for h, _ in kurva]

    def f(T):
        out = []
        for h in seri:
            s = h.to_numpy(float)
            a = np.searchsorted(h.index.to_numpy(), np.datetime64(mulai))
            awal = np.arange(a, len(s) - T, LANGKAH)
            if len(awal):
                out.append(s[awal + T] / s[awal] - 1)
        return np.concatenate(out) if out else None
    return f


def akhir_boot(S):
    return lambda T: S.x[:, T - 1] - 1 if S.x.shape[1] >= T else None


def ringkas_set(S, p, gagal, h29=False):
    out = {}
    for T in HORIZON:
        z = zona(S, T, p, gagal)
        out[T] = {"waspada": pct(z["waspada"]), "gagal": pct(z["gagal"]), "dd45": pct(z["dd45"]),
                  "lolos": pct(z["lolos_h29"] if h29 else z["lolos_h11a"])}
        if h29:
            out[T]["lolos_ketat"] = pct(z["lolos_h29_ketat"])
    out["dd45_500"] = pct((S.dd[:, :500] < pantau.BATAS_DD).any(axis=1)) if S.dd.shape[1] >= 500 else None
    return out


def evaluasi_kandidat(normal_a, lain, mulai_g=63, beruntun=True):
    out = {}
    for jenis, mulai_ret in (("gagal", mulai_g), ("waspada", 21)):
        q, b = cari_q(normal_a, TARGET[jenis], mulai_ret, beruntun)
        qa, ra, da = cari_q_akhir(normal_a, TARGET[jenis])
        r_i = {nm: pct(flag(S, 250, b["ret"], b["dd"], b["ber"], mulai_ret)) for nm, S in lain.items()}
        r_ii = {nm: pct(kena_akhir(S, ra, da)) for nm, S in lain.items()}
        out[jenis] = {"i": {"q": round(q, 3), "kena": r_i, "ret_250": round(float(b["ret"][249]), 2), "dd_250": round(float(b["dd"][249]), 2),
                            "ret_63": round(float(b["ret"][62]), 2), "dd_63": round(float(b["dd"][62]), 2),
                            "ber_20": int(b["ber"][19]) if b["ber"] is not None else None, "ret": np.round(b["ret"], 2).tolist(), "dd": np.round(b["dd"], 2).tolist(),
                            "ber": b["ber"].astype(int).tolist() if b["ber"] is not None else None},
                     "ii": {"q": round(qa, 3), "ret_250": round(ra, 2), "dd_250": round(da, 2), "kena": r_ii}}
    return out


def keluar_pita(pasangan, lo, hi):
    keluar = []
    for x, y in pasangan:
        j = pd.concat([x.rename("a"), y.rename("b")], axis=1).ffill().dropna()
        av, bv = j["a"].to_numpy(), j["b"].to_numpy()
        for s in range(0, len(av) - 250, LANGKAH):
            g = ((bv[s + 1:s + 251] / bv[s]) - (av[s + 1:s + 251] / av[s])) * 100
            keluar.append(bool(((g < lo[:250]) | (g > hi[:250])).any()))
    return pct(keluar), len(keluar)


def u2_alarm():
    from backend.ingest import des_ojk
    kode = set(des_ojk.baca()["kode"])
    siap_y = ut.siapkan_holdout()
    di, hari_idx = ap.data_idx(kode)
    with ap.ganti_banyak(di):
        siap_i = ut.siapkan_holdout()
    mentah_i = {k: v[["close", "dividends"]] for k, v in di.items()}
    _, pasangan = ap.u2(siap_y, siap_i, mentah_i, hari_idx)
    a = db()[pantau.K_BATAS].find_one({"_id": "u2_v1"})["ambang"]
    b = db()[pantau.K_BATAS].find_one({"_id": "u2_h22_v1"})["ambang"]
    out = {}
    out["h11a_pita_replay_250"], out["h11a_pita_jendela"] = keluar_pita(pasangan, np.array(a["pita_replay"]["p1"]), np.array(a["pita_replay"]["p99"]))
    hari = pd.DatetimeIndex([t for t in hari_idx if t >= MULAI_20])
    A, B = ap.panel_sinyal(siap_y, hari), ap.panel_sinyal(siap_i, hari)
    kol = A.columns.union(B.columns)
    beda = (A.reindex(columns=kol, fill_value=False) != B.reindex(columns=kol, fill_value=False)).sum(axis=1)
    lewat = (beda.rolling(ap.JENDELA).sum() > a["sinyal_per_21_hari"]).to_numpy()
    w = [bool(lewat[s:s + 250].any()) for s in range(0, len(lewat) - 250, LANGKAH)]
    out["h11a_sinyal_250"], out["h11a_sinyal_jendela"] = pct(w), len(w)
    del siap_y, siap_i
    S = ap.susun_h22()
    e_y, _, rk_y = s29.rs_simulasi(S)
    del S
    S = ap.susun_h22(di)
    e_i, _, rk_i = s29.rs_simulasi(S)
    del S
    akhir = min(e_y.index[-1], e_i.index[-1])
    out["h22_pita_250"], out["h22_pita_jendela"] = keluar_pita([(e_y[e_y.index <= akhir], e_i[e_i.index <= akhir])], np.array(b["pita_h22"]["p1"]), np.array(b["pita_h22"]["p99"]))
    p29 = []
    for x, y in pasangan:
        ak = min(akhir, x.index[-1], y.index[-1])
        p29.append((s29.gabung(x, e_y, ak)[0], s29.gabung(y, e_i, ak)[0]))
    out["h29_pita_250"], out["h29_pita_jendela"] = keluar_pita(p29, np.array(b["pita_h29"]["p1"]), np.array(b["pita_h29"]["p99"]))
    by, bi = {pd.Timestamp(x["sinyal"]): x for x in rk_y}, {pd.Timestamp(x["sinyal"]): x for x in rk_i}
    isi = [len((set(by[t]["beli"]) | set(by[t]["tetap"])) ^ (set(bi[t]["beli"]) | set(bi[t]["tetap"]))) for t in sorted(set(by) & set(bi)) if t >= MULAI_20 - pd.Timedelta(days=40)]
    lewat = np.array(isi) > b["isi_rebalance_beda"]
    w = [bool(lewat[s:s + 12].any()) for s in range(0, len(lewat) - 12)]
    out["h22_rebalance_12"], out["h22_rebalance_jendela"], out["h22_rebalance_beda_maks"] = pct(w), len(w), int(max(isi))
    out["catatan"] = "Pita dan ambang dibuat dari data yang sama (in-sample, p1/p99 per hari); jendela 250 hari tiap 5 hari saling tumpang tindih; H22 hanya satu jalur."
    return out


def h22_kurva(periode):
    S = m.susun(periode)
    e22, _, _ = s29.rs_simulasi(S)
    del S
    return e22


def jalankan(bagian):
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    b = db().batas_paper.find_one({"_id": pantau.ID_ZONA})
    bz = db()[pantau.K_BATAS].find_one({"_id": pantau.ID_ZONA_H29, "status": "dikunci"})
    p11, p29 = pita_v1(b), {"ret_w": np.array(bz["return"]["p5"]), "dd_w": np.array(bz["dd"]["p5"]), "ber_w": None, "ret_g": None, "dd_g": None, "ber_g": None}
    hasil = dt.baca_hasil("audit_aturan_paper") or {}

    print("H11a normal (a): kurva h11a_2020_konservatif seed 7 dari trade tersimpan", flush=True)
    tr = pd.DataFrame(list(db().backtest_trade.find({"versi": bp.VERSI, "dipilih": True}, {"_id": 0})))
    tr["tgl_beli"], tr["tgl_jual"] = pd.to_datetime(tr["tgl_beli"]), pd.to_datetime(tr["tgl_jual"])
    tr = tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    ek = bp.kurva_harian(tr)
    jual_a = [(pd.Timestamp(t), n) for t, n in zip(tr.loc[tr["status"] == "selesai", "tgl_jual"], tr.loc[tr["status"] == "selesai", "net"])]
    N11a = set_bootstrap("H11a normal (a)", [(ek, sorted(jual_a))], rng)

    print("H11a normal (b): 100 simulasi dev konservatif", flush=True)
    siap_d = ut.siapkan_dev()
    trd = ut.kumpulkan(siap_d, lambda x: x["close"] >= x["maks250"])
    trd = trd[(trd["tgl"] >= DEV[0]) & (trd["tgl"] <= DEV[1])].reset_index(drop=True)
    trd = ib.konservatif(trd, siap_d).reset_index(drop=True)
    kd = kurva_h11a(siap_d, trd, DEV[0], DEV[1], SIM_NORMAL)
    N11b = set_jendela("H11a normal (b)", kd, MULAI_JENDELA_DEV)
    dd500_b = pct(np.concatenate([(lambda x: (ret_dd(x)[1] < pantau.BATAS_DD).any(axis=1))(jendela(h, MULAI_JENDELA_DEV, 500)[0]) for h, _ in kd]))

    print("H29 normal (a): kurva h29_v1", flush=True)
    siap_h = ut.siapkan_holdout()
    siap_h = {t: x[x.index <= BATAS_DATA] for t, x in siap_h.items()}
    e22h = h22_kurva("holdout")
    trh = ut.kumpulkan(siap_h, lambda x: x["close"] >= x["maks250"])
    trh = trh[trh["tgl"] >= MULAI_20].reset_index(drop=True)
    kh = kurva_h11a(siap_h, trh, MULAI_20, trh["tgl_exit"].max(), [s29.CONTOH_SEED])
    v29, _, _ = s29.gabung(kh[0][0], e22h, min(e22h.index[-1], trh["tgl_exit"].max()))
    sama29 = hashlib.sha1(v29.round(8).to_csv().encode()).hexdigest() == bz["hash_kurva"]
    print(f"  kurva H29 sama dengan h29_v1: {sama29}", flush=True)
    N29a = set_bootstrap("H29 normal (a)", [(v29, None)], rng)

    print("H29 normal (b): dev 50/50", flush=True)
    e22d = h22_kurva("dev")
    k29d = [(s29.gabung(h, e22d, min(e22d.index[-1], DEV[1]))[0], None) for h, _ in kd]
    N29b = set_jendela("H29 normal (b)", k29d, e22d.index[0] + pd.Timedelta(days=1))

    print("null (1) bobot sama dan (2) JII", flush=True)
    ew_h = ew_biaya(siap_h, MULAI_20, BATAS_DATA)
    ew_d = ew_biaya(siap_d, DEV[0], DEV[1])
    j = jii()
    jh, jd = j[(j.index >= MULAI_20) & (j.index <= BATAS_DATA)], j[(j.index >= DEV[0]) & (j.index <= DEV[1])]
    N1a = set_bootstrap("null 1 (a)", [(ew_h[ew_h.index >= MULAI_20], None)], rng)
    N2a = set_bootstrap("null 2 (a)", [(jh, None)], rng)
    N1b = set_jendela("null 1 (b)", [(ew_d, None)], MULAI_JENDELA_DEV)
    N2b = set_jendela("null 2 (b)", [(jd, None)], MULAI_JENDELA_DEV)

    print("null (3) pilihan acak, 200 simulasi per periode", flush=True)
    sh_k = {t: x for t, x in siap_h.items()}
    p_h, p_d = peluang_sinyal(sh_k), peluang_sinyal(siap_d)
    a3h = null_acak(sh_k, MULAI_20, BATAS_DATA, p_h, SEED_NULL)
    a3d = null_acak(siap_d, DEV[0], DEV[1], p_d, SEED_NULL)
    N3a = set_bootstrap("null 3 (a)", a3h, rng, per_kurva=JALUR_PER_NULL)
    N3b = set_jendela("null 3 (b)", a3d, MULAI_JENDELA_DEV, langkah=10)
    g29h = [(s29.gabung(h, ew_h, min(ew_h.index[-1], h.index[-1]))[0], None) for h, _ in a3h]
    g29d = [(s29.gabung(h, ew_d, min(ew_d.index[-1], h.index[-1]))[0], None) for h, _ in a3d]
    N29n_a = set_bootstrap("H29 null (a)", g29h, rng, per_kurva=JALUR_PER_NULL)
    N29n_b = set_jendela("H29 null (b)", g29d, e22d.index[0] + pd.Timedelta(days=1), langkah=10)
    dd500_29b = pct(np.concatenate([(lambda x: (ret_dd(x)[1] < pantau.BATAS_DD).any(axis=1))(jendela(h, e22d.index[0] + pd.Timedelta(days=1), 500)[0]) for h, _ in k29d]))

    print(f"evaluasi ({time.time() - t0:.0f} dtk)", flush=True)
    h11 = {"normal_a": ringkas_set(N11a, p11, True), "normal_b": ringkas_set(N11b, p11, True),
           "null1_a": ringkas_set(N1a, p11, True), "null2_a": ringkas_set(N2a, p11, True), "null3_a": ringkas_set(N3a, p11, True),
           "null1_b": ringkas_set(N1b, p11, True), "null2_b": ringkas_set(N2b, p11, True), "null3_b": ringkas_set(N3b, p11, True)}
    h29 = {"normal_a": ringkas_set(N29a, p29, False, True), "normal_b": ringkas_set(N29b, p29, False, True),
           "null_a": ringkas_set(N29n_a, p29, False, True), "null_b": ringkas_set(N29n_b, p29, False, True)}
    kand11 = evaluasi_kandidat(N11a, {"normal_a": N11a, "normal_b": N11b, "null1_a": N1a, "null2_a": N2a, "null3_a": N3a,
                                       "null1_b": N1b, "null2_b": N2b, "null3_b": N3b})
    kand29 = evaluasi_kandidat(N29a, {"normal_a": N29a, "normal_b": N29b, "null_a": N29n_a, "null_b": N29n_b}, beruntun=False)
    kand11_l = {"waspada_dan_gagal_i": {}}
    for nm, S in {"normal_a": N11a, "normal_b": N11b, "null1_a": N1a, "null2_a": N2a, "null3_a": N3a, "null1_b": N1b, "null2_b": N2b, "null3_b": N3b}.items():
        bw, bg = kand11["waspada"]["i"], kand11["gagal"]["i"]
        w = flag(S, 250, np.array(bw["ret"]), np.array(bw["dd"]), np.array(bw["ber"]), 21)
        g = flag(S, 250, np.array(bg["ret"]), np.array(bg["dd"]), np.array(bg["ber"]), 63)
        d45 = (S.dd[:, :250] < pantau.BATAS_DD).any(axis=1)
        kand11_l["waspada_dan_gagal_i"][nm] = pct(~(w | g | d45))
        ra, da = kand11["waspada"]["ii"]["ret_250"], kand11["waspada"]["ii"]["dd_250"]
        kand11_l.setdefault("posisi_akhir_ii", {})[nm] = pct(~(kena_akhir(S, ra, da) | d45))
    tmin11 = {"a": horizon_minimum(akhir_boot(N11a), {"null1": akhir_boot(N1a), "null2": akhir_boot(N2a), "null3": akhir_boot(N3a)}),
              "b": horizon_minimum(akhir_jendela(kd, MULAI_JENDELA_DEV), {"null1": akhir_jendela([(ew_d, None)], MULAI_JENDELA_DEV),
                                                                           "null2": akhir_jendela([(jd, None)], MULAI_JENDELA_DEV),
                                                                           "null3": akhir_jendela(a3d, MULAI_JENDELA_DEV)})}
    tmin29 = {"a": horizon_minimum(akhir_boot(N29a), {"null": akhir_boot(N29n_a)}),
              "b": horizon_minimum(akhir_jendela(k29d, e22d.index[0] + pd.Timedelta(days=1)), {"null": akhir_jendela(g29d, e22d.index[0] + pd.Timedelta(days=1))})}
    info = {"h29_kurva_sama_v1": bool(sama29), "dd45_500_normal_b": {"h11a": dd500_b, "h29": dd500_29b}, "p_sinyal_acak": {"2020+": p_h, "dev": p_d},
            "jalur": {s.nama: len(s.x) for s in (N11a, N11b, N29a, N29b, N1a, N2a, N3a, N1b, N2b, N3b, N29n_a, N29n_b)},
            "cagr_null": {"ew_2020": float((ew_h.iloc[-1] / ew_h[ew_h.index >= MULAI_20].iloc[0]) ** (365.25 / (ew_h.index[-1] - MULAI_20).days) - 1) * 100,
                          "ew_dev": float((ew_d.iloc[-1] / ew_d.iloc[0]) ** (365.25 / (ew_d.index[-1] - ew_d.index[0]).days) - 1) * 100,
                          "acak_2020_median": float(np.median([(h.iloc[-1] / h.iloc[0]) ** (365.25 / (h.index[-1] - h.index[0]).days) - 1 for h, _ in a3h]) * 100),
                          "acak_dev_median": float(np.median([(h.iloc[-1] / h.iloc[0]) ** (365.25 / (h.index[-1] - h.index[0]).days) - 1 for h, _ in a3d]) * 100)}}
    hasil.update({"h11a": h11, "h29": h29, "kandidat_h11a": kand11, "kandidat_h29": kand29, "lolos_kandidat_h11a": kand11_l,
                  "horizon_minimum_h11a": tmin11, "horizon_minimum_h29": tmin29, "info": info, "dijalankan": pd.Timestamp.now().isoformat(timespec="seconds")})
    if "u2" in bagian:
        print("U2: alarm palsu dari riwayat IDX vs Yahoo", flush=True)
        hasil["u2"] = u2_alarm()
    dt.simpan_hasil("audit_aturan_paper", json.loads(json.dumps(hasil, default=lambda v: v.item() if hasattr(v, "item") else str(v))))
    print(f"SELESAI ({time.time() - t0:.0f} dtk)", flush=True)


def utama():
    a = argparse.ArgumentParser()
    a.add_argument("--u2", action="store_true")
    x = a.parse_args()
    jalankan({"u2"} if x.u2 else set())


if __name__ == "__main__":
    utama()
