import hashlib

import numpy as np
import pandas as pd

from backend.db import harga as hg
from backend.db import isi_backtest as ib
from backend.db import koneksi as kdb
from backend.paper import batas_paper as bp
from backend.paper import pantau
from backend.research import ambang_pantau as ap
from backend.research import simulasi_h29 as s29
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

HARI = 250
LANGKAH = 5
BATAS_DATA = pd.Timestamp("2026-10-30")
MULAI = pd.Timestamp("2020-01-01")


def db():
    return kdb.koneksi()


def nilai_jalur(ret, dd, b, gagal=True):
    h = np.arange(1, HARI + 1)
    p5r, p1r = np.array(b["return"]["p5"][:HARI]), np.array(b["return"]["p1"][:HARI])
    p5d = np.array(b["dd"]["p5"][:HARI])
    w = ((h >= 21) & (ret < p5r)) | (dd < p5d)
    out = {"waspada_return": ((h >= 21) & (ret < p5r)).any(axis=1), "waspada_dd": (dd < p5d).any(axis=1)}
    if gagal:
        p1d = np.array(b["dd"]["p1"][:HARI])
        g = ((h >= 63) & (ret < p1r)) | (dd < p1d)
        out.update(gagal_return=((h >= 63) & (ret < p1r)).any(axis=1), gagal_dd=(dd < p1d).any(axis=1), gagal=g.any(axis=1))
        w = w | g
    out["waspada"] = w.any(axis=1)
    out["dd45"] = (dd < pantau.BATAS_DD).any(axis=1)
    return out


def beruntun_jalur(net_list, b, gagal=True):
    p95, p99 = np.array(b["beruntun"]["p95"]), np.array(b["beruntun"]["p99"])
    w = g = False
    jalan = terpanjang = 0
    for k, x in enumerate(net_list[: len(p95)], start=1):
        jalan = jalan + 1 if x <= 0 else 0
        terpanjang = max(terpanjang, jalan)
        w |= terpanjang > p95[k - 1]
        g |= terpanjang > p99[k - 1]
    return w, g


def jendela(h):
    v = h.to_numpy(float)
    awal = np.arange(0, len(v) - HARI, LANGKAH)
    idx = awal[:, None] + np.arange(HARI + 1)[None, :]
    x = v[idx] / v[awal][:, None]
    puncak = np.maximum.accumulate(np.maximum(x, 1.0), axis=1)
    ret = (x[:, 1:] - 1) * 100
    dd = np.minimum.accumulate(x / puncak - 1, axis=1)[:, 1:] * 100
    return awal, ret, dd


def persen(x):
    return round(float(np.mean(x) * 100), 1)


def ringkas(nama, hasil):
    print(f"{nama}: " + ", ".join(f"{k} {persen(v)}%" for k, v in hasil.items()))
    return {k: persen(v) for k, v in hasil.items()}


def h11a_bootstrap(b):
    tr = pd.DataFrame(list(db().backtest_trade.find({"versi": bp.VERSI, "dipilih": True}, {"_id": 0})))
    tr["tgl_beli"] = pd.to_datetime(tr["tgl_beli"])
    tr["tgl_jual"] = pd.to_datetime(tr["tgl_jual"])
    tr = tr.sort_values(["tgl_beli", "ticker"]).reset_index(drop=True)
    sama = hashlib.sha1(tr[["ticker", "tgl_beli", "net"]].to_csv().encode()).hexdigest() == b["hash_trade"]
    ek = bp.kurva_harian(tr)
    rng = np.random.default_rng(bp.SEED)
    ret, dd = bp.bootstrap_kurva(ek.pct_change().dropna().to_numpy(), rng)
    net = tr.loc[tr["status"] == "selesai"].sort_values("tgl_jual")["net"].to_numpy(float)
    beruntun = bp.rugi_beruntun(net, rng)
    hasil = nilai_jalur(ret[:, :HARI], dd[:, :HARI], b)
    n_trade = int(round(len(net) / b["kurva"]["hari"] * HARI))
    k = min(n_trade, beruntun.shape[1])
    bw = (beruntun[:, :k] > np.array(b["beruntun"]["p95"][:k])).any(axis=1)
    bg = (beruntun[:, :k] > np.array(b["beruntun"]["p99"][:k])).any(axis=1)
    hasil.update(waspada_beruntun=bw, gagal_beruntun=bg, waspada_semua=hasil["waspada"] | bw, gagal_semua=hasil["gagal"] | bg | hasil["dd45"])
    return sama, len(ret), n_trade, hasil


def kurva_mc(versi_konservatif, siap, seeds):
    tr = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    tr = tr[tr["tgl"] >= MULAI].reset_index(drop=True)
    if versi_konservatif:
        tr = ib.konservatif(tr, siap).reset_index(drop=True)
    akhir = tr["tgl_exit"].max()
    mentah = {t: hg.mentah(t) for t in tr["ticker"].unique()}
    dok = ib.dokumen_trade("x", tr, set(), siap)
    keluar = []
    for seed in seeds:
        pilih = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        ds = [dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)]
        _, h = ib.kurva_paper(ds, MULAI, akhir, mentah)
        jual = sorted(((pd.Timestamp(x["tgl_jual"]), x["net"]) for x in ds if x["dipilih"] and x["status"] == "selesai"))
        keluar.append((h, jual))
    return keluar


def h11a_mc(b, siap):
    gab = {}
    for h, jual in kurva_mc(True, siap, range(1, 101)):
        awal, ret, dd = jendela(h)
        r = nilai_jalur(ret, dd, b)
        bw, bg = [], []
        for s in awal:
            a, z = h.index[s], h.index[s + HARI]
            w, g = beruntun_jalur([n for t, n in jual if a < t <= z], b)
            bw.append(w)
            bg.append(g)
        r.update(waspada_beruntun=np.array(bw), gagal_beruntun=np.array(bg))
        r["waspada_semua"] = r["waspada"] | r["waspada_beruntun"]
        r["gagal_semua"] = r["gagal"] | r["gagal_beruntun"] | r["dd45"]
        for k, v in r.items():
            gab.setdefault(k, []).append(v)
    return {k: np.concatenate(v) for k, v in gab.items()}


def h29_semua(bz, siap):
    S = m.susun("holdout")
    e22, _, _ = s29.rs_simulasi(S)
    del S
    z = ap.u3(siap)
    sama = z["hash_kurva"] == bz["hash_kurva"]
    rng = np.random.default_rng(bp.SEED)
    siap_b = {t: x[x.index <= BATAS_DATA] for t, x in siap.items()}
    tr = ut.kumpulkan(siap_b, lambda x: x["close"] >= x["maks250"])
    tr = tr[tr["tgl"] >= MULAI].reset_index(drop=True)
    a11 = tr["tgl_exit"].max()
    mentah = {t: hg.mentah(t) for t in tr["ticker"].unique()}
    dok = ib.dokumen_trade("x", tr, set(), siap_b)
    pilih = set(simulasi_portofolio(tr, ib.POSISI, s29.CONTOH_SEED).index)
    _, e11 = ib.kurva_paper([dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)], MULAI, a11, mentah)
    v, _, _ = s29.gabung(e11, e22, min(e22.index[-1], a11))
    ret, dd = bp.bootstrap_kurva(v.pct_change().dropna().to_numpy(), rng)
    boot = nilai_jalur(ret[:, :HARI], dd[:, :HARI], bz, gagal=False)
    gab = {}
    for seed in range(1, 101):
        p = set(simulasi_portofolio(tr, ib.POSISI, seed).index)
        _, e = ib.kurva_paper([dict(x, dipilih=i in p) for i, x in zip(tr.index, dok)], MULAI, a11, mentah)
        vv, _, _ = s29.gabung(e, e22, min(e22.index[-1], a11))
        _, r_, d_ = jendela(vv)
        for k, x in nilai_jalur(r_, d_, bz, gagal=False).items():
            gab.setdefault(k, []).append(x)
    return sama, boot, {k: np.concatenate(x) for k, x in gab.items()}


def utama():
    b = db().batas_paper.find_one({"_id": pantau.ID_ZONA})
    bz = db()[pantau.K_BATAS].find_one({"_id": pantau.ID_ZONA_H29, "status": "dikunci"})
    sama, n, n_trade, boot = h11a_bootstrap(b)
    print(f"H11a bootstrap ({n} jalur, trade backtest sama dengan saat zona dibuat: {sama}, ±{n_trade} trade selesai per 250 hari)")
    ringkas("  h11a_v1 bootstrap", boot)
    siap = ut.siapkan_holdout()
    siap = {t: x[x.index <= BATAS_DATA] for t, x in siap.items()}
    mc = h11a_mc(b, siap)
    print(f"H11a 100 simulasi Monte Carlo konservatif, jendela 250 hari mulai tiap {LANGKAH} hari: {len(mc['waspada'])} jendela")
    ringkas("  h11a_v1 Monte Carlo", mc)
    sama29, boot29, mc29 = h29_semua(bz, siap)
    print(f"H29 bootstrap (kurva sama dengan h29_v1: {sama29})")
    ringkas("  h29_v1 bootstrap", boot29)
    print(f"H29 100 simulasi Monte Carlo, {len(mc29['waspada'])} jendela")
    ringkas("  h29_v1 Monte Carlo", mc29)
    print("SELESAI")


if __name__ == "__main__":
    utama()
