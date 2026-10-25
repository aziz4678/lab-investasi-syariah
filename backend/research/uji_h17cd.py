import argparse
import types

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_ihsg
from backend.db import data as dt
from backend.ingest import des_ojk
from backend.research import dividen_v1 as dh
from backend.research import screener as sc
from backend.research import uji_h17 as h17

MULAI = pd.Timestamp("2014-01-01")
SAMPAI = pd.Timestamp("2026-10-23")
BATAS_217 = 2019


def kode_non(des, d217):
    return sorted(set(dt.daftar("harga")) - set(des["kode"]) - set(d217))


def tahun_dari(t):
    return (t + pd.Timedelta(days=10)).year


def universe(jenis, des, d217, non):
    def f(_des, t):
        if jenis == "h17c":
            return non
        return sorted(d217) if tahun_dari(t) <= BATAS_217 else sorted(des_ojk.syariah_pada(des, t))
    return f


def pembanding(data, kal, univ_fn, des):
    baris = []
    for th in range(MULAI.year, SAMPAI.year + 1):
        e = kal[kal >= pd.Timestamp(f"{th}-01-01")].min()
        t = kal[kal < e].max()
        x = kal[kal >= pd.Timestamp(f"{th + 1}-01-01")]
        x = x.min() if len(x) else kal[kal <= SAMPAI].max()
        _, _, univ, _ = h17.pilih(data, univ_fn(des, t), t, th)
        hb = [h17.hasil_saham(data[k], e, x) for k in univ]
        hb = [v for v in hb if v]
        baris.append({"tahun": th, "total": np.mean([v["total"] for v in hb]) if hb else np.nan, "universe": len(univ)})
    return pd.DataFrame(baris).set_index("tahun")


def jalankan(jenis, data, kal, des, d217, non, sektor):
    univ_fn = universe(jenis, des, d217, non)
    dh.MULAI = MULAI
    dh.des_ojk = types.SimpleNamespace(syariah_pada=univ_fn)
    lot, transaksi, ekuitas, pilihan, kas, piutang = dh.simulasi(data, des, sektor, kal, SAMPAI)
    dh.des_ojk = des_ojk
    e = pd.DataFrame(ekuitas).set_index("tgl")
    th = pd.DataFrame(dh.ringkas_tahun(transaksi, ekuitas)).set_index("tahun")
    pb = pembanding(data, kal, univ_fn, des)
    ihsg = baca_ihsg()
    ihsg = ihsg[(ihsg.index <= SAMPAI)]
    ih0 = h17.nilai_pada(ihsg, e.index[0] - pd.Timedelta(days=1))
    ih = pd.Series([h17.nilai_pada(ihsg, t) / ih0 for t in e.index], index=e.index)
    lama = (e.index[-1] - (e.index[0] - pd.Timedelta(days=1))).days / 365.25
    cagr = ((e["ekuitas"].iloc[-1] / dh.MODAL) ** (1 / lama) - 1) * 100
    cagr_ih = (ih.iloc[-1] ** (1 / lama) - 1) * 100
    cagr_pb = ((1 + pb["total"] / 100).prod() ** (1 / lama) - 1) * 100
    dd = float((e["ekuitas"] / e["ekuitas"].cummax() - 1).min() * 100)
    dd_ih = float((ih / ih.cummax() - 1).min() * 100)
    penuh = th[th["lengkap"]]
    pb_penuh = pb.loc[penuh.index, "total"]
    ih_th = ih.groupby(ih.index.year).last()
    ih_ret = ih_th / ih_th.shift(1).fillna(1.0) - 1
    rata_ph = float(penuh["penghasilan_persen"].mean())
    porsi_ph3 = float((penuh["penghasilan_persen"] >= 3).mean())
    terburuk, terburuk_pb = float(penuh["total_persen"].min()), float(pb_penuh.min())
    k = {"k1": rata_ph >= 4 and porsi_ph3 >= 0.8, "k2": cagr >= cagr_ih and cagr >= cagr_pb,
         "k3": dd >= dd_ih - 10, "k4": terburuk >= terburuk_pb - 5}
    jml = [len(p["saham"]) for p in pilihan]
    kas_pct = float((e["kas"] / e["ekuitas"]).mean() * 100)
    tabel = pd.DataFrame({"penghasilan": th["penghasilan_persen"], "total": th["total_persen"], "pembanding": pb["total"],
                          "ihsg": ih_ret.reindex(th.index) * 100, "lengkap": th["lengkap"], "universe": pb["universe"]})
    tabel["saham"] = [" ".join(x["kode"] for x in p["saham"]) for p in pilihan]
    tabel["jumlah"] = jml
    ringkas = {"cagr": cagr, "cagr_ihsg": cagr_ih, "cagr_pembanding": cagr_pb, "dd": dd, "dd_ihsg": dd_ih,
               "penghasilan_rata": rata_ph, "porsi_penghasilan_3": porsi_ph3 * 100, "terburuk": terburuk,
               "th_terburuk": int(penuh["total_persen"].idxmin()), "terburuk_pembanding": terburuk_pb,
               "saham_rata": float(np.mean(jml)), "kas_rata": kas_pct, **k}
    return ringkas, tabel, e, ih, transaksi


def lapor(jenis, r, tabel):
    nama = {"h17c": "H17c uji silang NON-SYARIAH (bukti utama)", "h17d": "H17d SYARIAH historis (pelengkap, pasca hasil)"}[jenis]
    print(f"\n##### {nama} | {MULAI:%Y-%m-%d} s/d {SAMPAI:%Y-%m-%d}")
    t = tabel.copy()
    t.index = [f"{i}{'' if l else '*'}" for i, l in zip(t.index, t["lengkap"])]
    print(t.drop(columns=["lengkap"]).round(1).to_string())
    print(f"CAGR {r['cagr']:.2f}% | IHSG {r['cagr_ihsg']:.2f}% | bobot sama {r['cagr_pembanding']:.2f}% | DD {r['dd']:.1f}% vs IHSG {r['dd_ihsg']:.1f}% | "
          f"saham rata-rata {r['saham_rata']:.1f} | kas rata-rata {r['kas_rata']:.1f}%")
    print(f"  [{'LULUS' if r['k1'] else 'GAGAL'}] 1. penghasilan rata-rata {r['penghasilan_rata']:.2f}% (>= 4) dan >= 3% di {r['porsi_penghasilan_3']:.0f}% tahun (>= 80)")
    print(f"  [{'LULUS' if r['k2'] else 'GAGAL'}] 2. CAGR {r['cagr']:.2f}% >= IHSG {r['cagr_ihsg']:.2f}% dan >= bobot sama {r['cagr_pembanding']:.2f}%")
    print(f"  [{'LULUS' if r['k3'] else 'GAGAL'}] 3. DD {r['dd']:.1f}% >= IHSG {r['dd_ihsg']:.1f}% - 10 = {r['dd_ihsg'] - 10:.1f}%")
    print(f"  [{'LULUS' if r['k4'] else 'GAGAL'}] 4. tahun terburuk {r['terburuk']:.1f}% ({r['th_terburuk']}) >= pembanding {r['terburuk_pembanding']:.1f}% - 5")
    lulus = all(r[x] for x in ("k1", "k2", "k3", "k4"))
    print(f"=> {jenis.upper()}: {'LULUS' if lulus else 'GAGAL'} ({sum(r[x] for x in ('k1', 'k2', 'k3', 'k4'))}/4)")
    return lulus


def simpan(jenis, r, tabel, e, ih):
    dt.simpan_hasil(f"{jenis}_ringkas", pd.DataFrame([{k: (bool(v) if isinstance(v, (bool, np.bool_)) else v) for k, v in r.items()}]))
    tb = tabel.copy()
    tb.index.name = "tahun"
    dt.simpan_hasil(f"{jenis}_tahun", tb.reset_index())
    bln = pd.DataFrame({"strategi": e["ekuitas"] / dh.MODAL, "ihsg": ih}).resample("ME").last()
    bln.index = bln.index.strftime("%Y-%m")
    dt.simpan_hasil(f"{jenis}_kurva", bln.reset_index(names="bulan"))


def siapkan():
    des = des_ojk.baca()
    d217 = sc.daftar_syariah()
    non = kode_non(des, d217)
    kode = sorted(set(des["kode"]) | set(d217) | set(non))
    print(f"memuat harga & dividen {len(kode)} kode ({len(non)} non-syariah)...")
    data = h17.muat_harga(kode)
    kal = h17.kalender(data)
    return data, kal, des, d217, [k for k in non if k in data], dh.sektor_dari()


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("uji", choices=["h17c", "h17d", "semua"])
    a = ap.parse_args()
    data, kal, des, d217, non, sektor = siapkan()
    for jenis in (["h17c", "h17d"] if a.uji == "semua" else [a.uji]):
        r, tabel, e, ih, _ = jalankan(jenis, data, kal, des, d217, non, sektor)
        lapor(jenis, r, tabel)
        simpan(jenis, r, tabel, e, ih)


if __name__ == "__main__":
    utama()
