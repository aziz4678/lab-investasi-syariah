import hashlib
from contextlib import contextmanager
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import harga as hg
from backend.db import isi_backtest as ib
from backend.db import koneksi as kdb
from backend.ingest import des_ojk
from backend.ingest import koreksi_harga as kh
from backend.paper import banding as bd
from backend.paper import batas_paper as bp
from backend.paper import pantau
from backend.paper import sumber_idx
from backend.paper.batas_paper import kurva_harian
from backend.research import screener as sc
from backend.research import simulasi_h29 as s29
from backend.research import uji_h21_h22 as m
from backend.research import uji_tren as ut
from backend.research.laporan_bulanan import simulasi_portofolio

MULAI = pd.Timestamp("2020-01-01")
BATAS_DATA_H29 = pd.Timestamp("2026-10-30")
JUMLAH_SIMULASI = 100
HORIZON = 250
LANGKAH = 5
PERSENTIL = [1, 5, 50, 95, 99]
JENDELA = 21


def db():
    return kdb.koneksi()


def data_idx(kode):
    yahoo = hg.banyak(kode)
    resmi = kh.idx_resmi()
    hari = sorted(set().union(*[set(g.index) for g in resmi.values()]))
    aturan = kh.aturan()
    out = {}
    for k, y in yahoo.items():
        d = sumber_idx.satu(k, y, resmi.get(k), aturan)
        g = resmi.get(k)
        if g is not None and not g.empty and len(d):
            y2 = y.sort_index().copy()
            y2.index = pd.to_datetime(y2.index)
            yk, _ = kh.terapkan(y2, k, aturan)
            awal = d.index.min()
            lama = yk[yk.index < awal].assign(sumber="yahoo", sumber_open="yahoo")
            d = pd.concat([lama[[c for c in d.columns if c in lama.columns]], d]).sort_index()
        out[k] = d
    return out, hari


@contextmanager
def ganti_banyak(data):
    asli = sc.hg.banyak
    sc.hg.banyak = lambda kode=None, kolom=None: {k: data[k] for k in (kode if kode is not None else data) if k in data}
    try:
        yield
    finally:
        sc.hg.banyak = asli


def panel_sinyal(siap, hari):
    return pd.DataFrame({t: (x["lolos"] & (x["close"] >= x["maks250"])).reindex(hari).fillna(False).astype(bool) for t, x in siap.items()})


def pct(x, ps=PERSENTIL):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return {f"p{p}": round(float(np.percentile(x, p)), 3) for p in ps} if len(x) else None


def u2(siap_y, siap_i, mentah_i, hari_idx):
    akhir = min(max(x.index.max() for x in siap_y.values()), max(x.index.max() for x in siap_i.values()))
    hari = pd.DatetimeIndex([t for t in hari_idx if MULAI <= t <= akhir])
    A, B = panel_sinyal(siap_y, hari), panel_sinyal(siap_i, hari)
    kolom = A.columns.union(B.columns)
    A, B = A.reindex(columns=kolom, fill_value=False), B.reindex(columns=kolom, fill_value=False)
    beda = (A != B).sum(axis=1)
    jumlah = (A | B).sum(axis=1)
    per_jendela = beda.rolling(JENDELA).sum().dropna()
    sinyal = {"hari": len(hari), "mulai": str(hari[0].date()), "akhir": str(hari[-1].date()),
              "hari_ada_beda_pct": round(float((beda > 0).mean() * 100), 2), "ticker_hari_beda": int(beda.sum()), "ticker_hari_sinyal": int(jumlah.sum()),
              "beda_per_hari": pct(beda), "beda_per_21_hari": pct(per_jendela), "beda_per_21_hari_maks": int(per_jendela.max())}

    tr_y = ut.kumpulkan(siap_y, lambda x: x["close"] >= x["maks250"])
    tr_y = tr_y[tr_y["tgl"] >= MULAI].reset_index(drop=True)
    tr_i = ut.kumpulkan(siap_i, lambda x: x["close"] >= x["maks250"])
    tr_i = tr_i[tr_i["tgl"] >= MULAI].reset_index(drop=True)
    ky, ki = tr_y.set_index(["ticker", "tgl"]), tr_i.set_index(["ticker", "tgl"])
    sama = ky.index.intersection(ki.index)
    masuk, keluar_sama, net = [], 0, []
    for t, d in sama:
        hy, _ = ib.harga_pasar(siap_y[t], d, 1, "open")
        hi, _ = ib.harga_pasar(siap_i[t], d, 1, "open")
        masuk.append(abs(hi / hy - 1) * 100 if hy else np.nan)
        keluar_sama += int(ky.at[(t, d), "tgl_exit"] == ki.at[(t, d), "tgl_exit"])
        net.append(ki.at[(t, d), "net"] - ky.at[(t, d), "net"])
    masuk = np.asarray(masuk, float)
    trade = {"trade_yahoo": len(tr_y), "trade_idx": len(tr_i), "sinyal_sama": len(sama), "keluar_sama_pct": round(keluar_sama / max(len(sama), 1) * 100, 2),
             "selisih_masuk_abs_pct": pct(masuk, [50, 95, 99]), "masuk_persis_sama_pct": round(float((masuk < 1e-6).mean() * 100), 2),
             "selisih_net_poin": pct(net)}

    mentah_y = {t: hg.mentah(t) for t in set(tr_y["ticker"])}
    pasangan = []
    for seed in range(1, JUMLAH_SIMULASI + 1):
        pilih = simulasi_portofolio(tr_y, ib.POSISI, seed).to_dict("records")
        rows_a = bd.baris_kurva(pilih, siap_y)
        rows_b = []
        for r in pilih:
            b = bd.satu_trade(siap_i.get(r["ticker"]), r["ticker"], r["tgl"])
            if not b or b.get("tgl_masuk") is None:
                continue
            rows_b.append((r["ticker"], b["tgl_masuk"], b["harga_masuk"], b.get("tgl_keluar", pd.NaT) if b["status"] == "jual" else pd.NaT, b.get("harga_keluar", np.nan)))
        a = kurva_harian(bd.ke_kurva(rows_a), MULAI, akhir, mentah_y)
        b = kurva_harian(bd.ke_kurva(rows_b), MULAI, akhir, {t: mentah_i[t] for t in {x[0] for x in rows_b} if t in mentah_i})
        pasangan.append((a, b))
        if seed % 20 == 0:
            print(f"  U2 replay: {seed}/{JUMLAH_SIMULASI} simulasi", flush=True)
    sebaran, akhir_k = pita(pasangan)
    replay = {"horizon": HORIZON, "langkah": LANGKAH, "simulasi": JUMLAH_SIMULASI, "selisih_poin": sebaran,
              "selisih_akhir_pct": pct(akhir_k), "keterangan": "selisih return (data IDX) - (data Yahoo) untuk portofolio yang sama, dalam poin persen, per lama hari sejak mulai"}
    return {"sinyal": sinyal, "trade": trade, "replay": replay}, pasangan


def pita(pasangan):
    gaps = {h: [] for h in range(1, HORIZON + 1)}
    akhir_k = []
    for a, b in pasangan:
        j = pd.concat([a.rename("a"), b.rename("b")], axis=1).ffill().dropna()
        av, bv = j["a"].to_numpy(), j["b"].to_numpy()
        akhir_k.append((bv[-1] / av[-1] - 1) * 100)
        for h in range(1, HORIZON + 1):
            s = np.arange(0, len(av) - h, LANGKAH)
            gaps[h].append(((bv[s + h] / bv[s]) - (av[s + h] / av[s])) * 100)
    sebaran = {f"p{p}": [] for p in PERSENTIL}
    for h in range(1, HORIZON + 1):
        x = np.concatenate(gaps[h])
        for p in PERSENTIL:
            sebaran[f"p{p}"].append(round(float(np.percentile(x, p)), 3))
    return sebaran, akhir_k


def susun_h22(data=None):
    if data is None:
        return m.susun("holdout")
    with ganti_banyak(data):
        return m.susun("holdout")


def u2_h22(di, pasangan):
    print("  H22 data Yahoo...", flush=True)
    S = susun_h22()
    e_y, ep_y, rk_y = s29.rs_simulasi(S)
    del S
    print("  H22 data IDX...", flush=True)
    S = susun_h22(di)
    e_i, ep_i, rk_i = s29.rs_simulasi(S)
    del S
    by = {pd.Timestamp(x["sinyal"]): x for x in rk_y}
    bi = {pd.Timestamp(x["sinyal"]): x for x in rk_i}
    isi_beda, top_beda, lolos_beda = [], [], []
    for t in sorted(set(by) & set(bi)):
        if t < MULAI - pd.Timedelta(days=40):
            continue
        a, b = by[t], bi[t]
        isi_beda.append(len((set(a["beli"]) | set(a["tetap"])) ^ (set(b["beli"]) | set(b["tetap"]))))
        top_beda.append(len({k for k, _ in a["peringkat"][: a["n"]]} ^ {k for k, _ in b["peringkat"][: b["n"]]}))
        lolos_beda.append(abs(a["lolos"] - b["lolos"]))
    beli_y = {(e["ticker"], pd.Timestamp(e["beli"])): e["harga_beli"] for e in ep_y}
    harga = [abs(h / beli_y[k] - 1) * 100 for k, h in ((( e["ticker"], pd.Timestamp(e["beli"])), e["harga_beli"]) for e in ep_i) if k in beli_y and beli_y[k]]
    harga = np.asarray(harga, float)
    akhir = min(e_y.index[-1], e_i.index[-1])
    s22, a22 = pita([(e_y[e_y.index <= akhir], e_i[e_i.index <= akhir])])
    print("  H29 gabungan...", flush=True)
    p29 = []
    for a, b in pasangan:
        ak = min(akhir, a.index[-1], b.index[-1])
        p29.append((s29.gabung(a, e_y, ak)[0], s29.gabung(b, e_i, ak)[0]))
    s29_, a29 = pita(p29)
    return {"rebalance": {"jumlah": len(isi_beda), "isi_beda": pct(isi_beda), "isi_beda_maks": int(max(isi_beda)) if isi_beda else None,
                          "isi_beda_nol_pct": round(float(np.mean(np.asarray(isi_beda) == 0) * 100), 1) if isi_beda else None,
                          "top_n_beda": pct(top_beda), "lolos_beda": pct(lolos_beda)},
            "trade": {"beli_yahoo": len(ep_y), "beli_idx": len(ep_i), "beli_sama": int(len(harga)), "selisih_beli_abs_pct": pct(harga, [50, 95, 99]),
                      "beli_persis_sama_pct": round(float((harga < 1e-6).mean() * 100), 2) if len(harga) else None},
            "h22": {"horizon": HORIZON, "langkah": LANGKAH, "selisih_poin": s22, "selisih_akhir_pct": pct(a22),
                    "keterangan": "selisih return H22 (data IDX) - (data Yahoo), mesin rs_simulasi yang sama, satu jalur (H22 tidak acak)"},
            "h29": {"horizon": HORIZON, "langkah": LANGKAH, "simulasi": len(p29), "selisih_poin": s29_, "selisih_akhir_pct": pct(a29),
                    "keterangan": "selisih return H29 (data IDX) - (data Yahoo): bagian Follow Tren 100 simulasi + bagian RS 12-1, gabung 50/50 bulanan"}}


def ambang_h11a(dok):
    rp = dok["replay"]["selisih_poin"]
    return {"sinyal_per_21_hari": dok["sinyal"]["beda_per_21_hari"]["p99"], "jendela": JENDELA, "harga_masuk_pct": dok["trade"]["selisih_masuk_abs_pct"]["p99"],
            "pita_replay": {"p1": rp["p1"], "p99": rp["p99"]}}


def ambang_h22(dok):
    return {"isi_rebalance_beda": dok["rebalance"]["isi_beda"]["p99"], "harga_beli_pct": dok["trade"]["selisih_beli_abs_pct"]["p99"],
            "pita_h22": {"p1": dok["h22"]["selisih_poin"]["p1"], "p99": dok["h22"]["selisih_poin"]["p99"]},
            "pita_h29": {"p1": dok["h29"]["selisih_poin"]["p1"], "p99": dok["h29"]["selisih_poin"]["p99"]}}


def kunci(id_, ambang=None, aturan=None):
    tambah = {"status": "dikunci", "dikunci": datetime.now(), "dikunci_oleh": "keputusan user 2026-11-07"}
    if ambang is not None:
        tambah["ambang"] = ambang
    if aturan is not None:
        tambah["aturan"] = aturan
    r = db()[pantau.K_BATAS].update_one({"_id": id_, "status": "usulan"}, {"$set": tambah})
    print(f"{id_}: {'dikunci' if r.modified_count else 'tidak diubah (sudah dikunci atau tidak ada)'}")


def u3(siap_y):
    S = m.susun("holdout")
    e22, _, _ = s29.rs_simulasi(S)
    del S
    siap_y = {t: x[x.index <= BATAS_DATA_H29] for t, x in siap_y.items()}
    tr = ut.kumpulkan(siap_y, lambda x: x["close"] >= x["maks250"])
    tr = tr[tr["tgl"] >= MULAI].reset_index(drop=True)
    a11 = tr["tgl_exit"].max()
    mentah = {t: hg.mentah(t) for t in tr["ticker"].unique()}
    dok = ib.dokumen_trade("h29_2020", tr, set(), siap_y)
    pilih = set(simulasi_portofolio(tr, ib.POSISI, s29.CONTOH_SEED).index)
    _, e11 = ib.kurva_paper([dict(x, dipilih=i in pilih) for i, x in zip(tr.index, dok)], MULAI, a11, mentah)
    v, _, _ = s29.gabung(e11, e22, min(e22.index[-1], a11))
    rk = db().backtest_ringkasan.find_one({"versi": "h29_2020"}, {"monte_carlo": 1, "dd_maks": 1, "cagr": 1})
    tahun = (v.index[-1] - v.index[0]).days / 365.25
    cek = {"dd_kurva": round(s29.dd_harian(v), 2), "dd_ringkasan": rk["dd_maks"] if rk else None,
           "cagr_kurva": round(float((v.iloc[-1] ** (1 / tahun) - 1) * 100), 2), "cagr_ringkasan": rk["cagr"] if rk else None}
    r = v.pct_change().dropna().to_numpy()
    rng = np.random.default_rng(bp.SEED)
    ret, dd = bp.bootstrap_kurva(r, rng)
    return {"_id": pantau.ID_ZONA_H29, "status": "usulan", "dibuat": datetime.now(), "sumber": "h29_2020 contoh seed 7 (kurva harian, data s/d 30 Okt 2026 seperti backtest tersimpan)",
            "jalur": bp.JALUR, "blok": bp.BLOK, "seed": bp.SEED, "horizon": bp.HORIZON,
            "hash_kurva": hashlib.sha1(v.round(8).to_csv().encode()).hexdigest(), "kurva": {"mulai": str(v.index[0].date()), "akhir": str(v.index[-1].date()), "hari": len(v), **cek},
            "return": {f"p{p}": np.round(np.percentile(ret, p, axis=0), 2).tolist() for p in [1, 5, 25, 50, 75, 95, 99]},
            "dd": {f"p{p}": np.round(np.percentile(dd, p, axis=0), 2).tolist() for p in [1, 5, 50]},
            "aturan": ["WASPADA (laporan saja, bukan syarat GAGAL): return paper H29 di bawah persentil 5 mulai hari ke-21, atau drawdown terdalam di bawah persentil 5.",
                       "Dihitung dengan cara yang sama dengan zona h11a_v1: bootstrap blok 20 hari, 5.000 jalur, dari kurva harian backtest h29_2020 contoh seed 7."]}


def simpan(dok):
    lama = db()[pantau.K_BATAS].find_one({"_id": dok["_id"]}, {"status": 1})
    if lama and lama.get("status") == "dikunci":
        print(f"{dok['_id']} sudah dikunci, tidak ditimpa")
        return
    db()[pantau.K_BATAS].replace_one({"_id": dok["_id"]}, dok, upsert=True)


def utama():
    des = des_ojk.baca()
    kode = set(des["kode"])
    print("menyiapkan data backtest (Yahoo riset)...", flush=True)
    siap_y = ut.siapkan_holdout()
    print("menyiapkan data yang sama dengan harga IDX resmi sejak 2020...", flush=True)
    di, hari_idx = data_idx(kode)
    with ganti_banyak(di):
        siap_i = ut.siapkan_holdout()
    mentah_i = {k: v[["close", "dividends"]] for k, v in di.items()}
    print("U2: sebaran selisih IDX vs Yahoo...", flush=True)
    hasil, pasangan = u2(siap_y, siap_i, mentah_i, hari_idx)
    simpan({"_id": "u2_v1", "status": "usulan", "dibuat": datetime.now(), **hasil,
            "versi_data": {"harga": hg.sidik(kode, "2018-01-01"), "idx_harian_hari": hasil["sinyal"]["hari"]},
            "catatan": ["Data IDX: close/open/high/low ringkasan perdagangan IDX resmi × faktor aksi korporasi (cara paper), sebelum 2020 memakai Yahoo yang sama.",
                        "Hanya mengukur efek sumber data. Paper juga berbeda karena lot 100 lembar dan cara mengukur posisi sebelum 2 Nov 2026; itu tidak masuk sebaran ini.",
                        "Sinyal historis tidak mengecualikan saham yang sedang dipegang (paper mengecualikan), jadi angka historis sedikit lebih longgar."]})
    s, t, rp = hasil["sinyal"], hasil["trade"], hasil["replay"]
    print(f"  sinyal: {s['hari']} hari, {s['hari_ada_beda_pct']}% hari ada beda; beda per 21 hari {s['beda_per_21_hari']} (maks {s['beda_per_21_hari_maks']}) dari {s['ticker_hari_sinyal']} ticker-hari sinyal")
    print(f"  trade: {t['sinyal_sama']} sinyal sama dari {t['trade_yahoo']}/{t['trade_idx']}; harga masuk persis sama {t['masuk_persis_sama_pct']}%, selisih {t['selisih_masuk_abs_pct']}; keluar sama {t['keluar_sama_pct']}%")
    for h in (21, 63, 126, 250):
        print(f"  replay hari ke-{h}: " + ", ".join(f"{k} {v[h - 1]:+.2f}" for k, v in rp["selisih_poin"].items()))
    if not (db()[pantau.K_BATAS].find_one({"_id": pantau.ID_ZONA_H29}) or {}).get("status") == "dikunci":
        print("U3: zona H29...", flush=True)
        z = u3(siap_y)
        simpan(z)
        print(f"  kurva {z['kurva']}")
        for h in (21, 63, 126, 250, 500):
            i = h - 1
            print(f"  hari ke-{h}: return p1 {z['return']['p1'][i]:.1f} p5 {z['return']['p5'][i]:.1f} p50 {z['return']['p50'][i]:.1f} | dd p5 {z['dd']['p5'][i]:.1f} p1 {z['dd']['p1'][i]:.1f}")
    del siap_y, siap_i
    if (db()[pantau.K_BATAS].find_one({"_id": "u2_h22_v1"}) or {}).get("status") != "dikunci":
        print("U2 H22/H29: sebaran selisih IDX vs Yahoo...", flush=True)
        h = u2_h22(di, pasangan)
        dok = {"_id": "u2_h22_v1", "status": "usulan", "dibuat": datetime.now(), **h,
               "versi_data": {"harga": hg.sidik(kode, "2018-01-01")},
               "catatan": ["Data IDX: cara yang sama dengan u2_v1 (harga IDX resmi × faktor aksi korporasi sejak 2020, sebelumnya Yahoo).",
                           "Hanya efek sumber data; lot 100 lembar dan koreksi peringkat paper 30 Okt 2026 tidak masuk sebaran.",
                           "Metode sama dengan u2_v1 (p99 / pita p1-p99), dikunci langsung atas keputusan user 2026-11-07."]}
        simpan(dok)
        kunci("u2_h22_v1", ambang_h22(dok), ATURAN_U2_H22)
        r = h["rebalance"]
        print(f"  rebalance: {r['jumlah']} kali, isi beda {r['isi_beda']} (maks {r['isi_beda_maks']}, {r['isi_beda_nol_pct']}% identik); top N beda {r['top_n_beda']}")
        print(f"  beli: {h['trade']['beli_sama']} sama dari {h['trade']['beli_yahoo']}/{h['trade']['beli_idx']}, persis sama {h['trade']['beli_persis_sama_pct']}%, selisih {h['trade']['selisih_beli_abs_pct']}")
        for nama in ("h22", "h29"):
            for hh in (21, 63, 126, 250):
                print(f"  {nama} hari ke-{hh}: " + ", ".join(f"{k} {v[hh - 1]:+.2f}" for k, v in h[nama]["selisih_poin"].items()))
    print("SELESAI")


ATURAN_U2_H11A = [
    "WASPADA DATA H11a (dikunci 2026-11-07, keputusan user): lebih dari 3 ticker-hari sinyal beda dengan mesin backtest dalam 21 hari bursa terakhir (p99 historis IDX vs Yahoo 2020-2026).",
    "WASPADA DATA H11a: return paper - replay keluar dari pita p1-p99 historis untuk lama hari yang sama (hari > 250 memakai pita hari ke-250).",
    "Selisih harga masuk/keluar per trade di atas p99 historis (0,18%) hanya dicatat, tidak memicu WASPADA.",
    "WASPADA DATA bukan syarat GAGAL. Kalau penyebabnya tidak terjelaskan data, masuk aturan bug eksekusi (5 hari bursa).",
]
ATURAN_U2_H22 = [
    "WASPADA DATA H29 (dikunci 2026-11-07, keputusan user, metode sama dengan u2_v1): jumlah saham isi rebalance RS 12-1 yang beda dengan mesin backtest melebihi p99 historis.",
    "WASPADA DATA H29: return paper H22 - backtest, atau paper H29 - replay, keluar dari pita p1-p99 historis untuk lama hari yang sama.",
    "Selisih harga beli per saham di atas p99 historis hanya dicatat. WASPADA DATA bukan syarat GAGAL; tidak terjelaskan → aturan bug eksekusi.",
    "Paper RS 12-1 memakai koreksi peringkat 30 Okt 2026 (keputusan user); saham yang beda karena koreksi itu tidak dihitung sebagai beda.",
]


if __name__ == "__main__":
    utama()
