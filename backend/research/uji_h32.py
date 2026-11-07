import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from audit import h22_ulang as au
from backend.db import data as dt
from backend.db import harga as hg
from backend.research import uji_h21_h22 as m
from backend.research import uji_h30 as h30

KETERBATASAN = h30.KETERBATASAN
SENS = h30.SENS


def ret_harian(S):
    if "h32_ret" not in S:
        S["h32_ret"] = S["P"]["c"].ffill().pct_change(fill_method=None)
    return S["h32_ret"]


def id_skor(S, t, pret):
    ab = S["akhir_bulan"]
    i = ab.index.get_loc(t.to_period("M"))
    if i < 12 or not len(pret):
        return pd.Series(dtype=float)
    a, b = ab.iloc[i - 12], ab.iloc[i - 1]
    R = ret_harian(S)
    R = R.loc[(R.index > a) & (R.index <= b), list(pret.index)]
    sah = R.notna().sum()
    selisih = (R < 0).sum() - (R > 0).sum()
    return (np.sign(pret) * selisih / sah.where(sah > 0)).astype(float)


def urutan(S, t, calon):
    cache = S.setdefault("h32_urut", {})
    kunci = (t, tuple(calon))
    if kunci in cache:
        return cache[kunci]
    pret = m.momentum(S, t).reindex(calon).dropna()
    n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
    urut_mom = list(pret.sort_values(ascending=False, kind="mergesort").index)
    grup, sisa = urut_mom[:2 * n], urut_mom[2 * n:]
    df = pd.DataFrame({"id": id_skor(S, t, pret.loc[grup]), "pret": pret.loc[grup]}, index=grup)
    df["kosong"] = df["id"].isna()
    df = df.sort_values(["kosong", "id", "pret"], ascending=[True, True, False], kind="mergesort")
    hasil = list(df.index) + sisa
    cache[kunci] = hasil
    return hasil


def jalankan(periode):
    t0 = time.time()
    S = m.susun(periode)
    rf = au.rf_bulanan()
    jadwal = m.jadwal(S)
    print(f"H32 {periode}: {len(S['kode'])} kode, sinyal pertama {jadwal[0][0].date()} eksekusi {jadwal[0][1].date()}, sinyal terakhir {jadwal[-1][0].date()}, {len(jadwal)} rebalance", flush=True)
    jml = []
    for t, _ in jadwal:
        calon = list(m.lolos(S, t, 5e9, 100))
        n = max(10, int(math.floor(0.2 * len(calon) + 0.5)))
        pret = m.momentum(S, t).reindex(calon).dropna()
        grup = list(pret.sort_values(ascending=False, kind="mergesort").index)[:2 * n]
        idg = id_skor(S, t, pret.loc[grup])
        atas = set(list(pret.sort_values(ascending=False, kind="mergesort").index)[:n])
        pilih = set(urutan(S, t, calon)[:n])
        jml.append((len(calon), len(pret), n, len(grup), float(idg.mean()), len(pilih & atas) / max(1, len(pilih))))
    jml = pd.DataFrame(jml, columns=["lolos", "diranking", "n", "kelompok", "id_rata_kelompok", "irisan_sinyal_h22"])
    print(f"  lolos rata-rata {jml['lolos'].mean():.1f}, N {jml['n'].mean():.1f}, kelompok {jml['kelompok'].mean():.1f}, irisan pilihan sinyal dengan H22 {jml['irisan_sinyal_h22'].mean() * 100:.1f}% ({time.time() - t0:.0f} dtk)", flush=True)
    mulai = jadwal[0][1]
    jii = m.pembanding_jii(S, mulai)
    rj = m.bulanan(jii.loc[mulai:])
    cj, thj, vj = au.tanpa_tahun_terbaik(rj)
    kj = {"CAGR": au.cagr_bln(rj), "DD": au.dd_bln(rj), "-tahun terbaik": cj, "tahun terbaik": f"{thj} ({vj:+.0f}%)"}
    hasil = {"periode": periode, "jumlah_saham": {"lolos_rata": round(jml["lolos"].mean(), 1), "diranking_rata": round(jml["diranking"].mean(), 1),
                                                   "n_rata": round(jml["n"].mean(), 1), "kelompok_rata": round(jml["kelompok"].mean(), 1),
                                                   "id_rata_kelompok": round(jml["id_rata_kelompok"].mean(), 3),
                                                   "irisan_sinyal_h22_pct": round(jml["irisan_sinyal_h22"].mean() * 100, 1)},
             "jii": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in kj.items()}}
    seri = {}
    for jenis in ["h32", "h22"]:
        out = {"skenario": {}}
        for nama, ps in SENS:
            h, e, ks, kb, krit = h30.satu(S, jenis, rj, kj, **ps)
            out["skenario"][nama] = {"kriteria": [(a, v, bool(o)) for a, v, o in krit], "lulus": all(o for _, _, o in krit),
                                    "strategi": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in ks.items()},
                                    "bobot_sama": {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in kb.items()}}
            if nama == "dasar":
                sim, inf = h30.info(S, jenis, h, rf)
                out["info"] = inf
                out["per_tahun"] = pd.DataFrame({"strategi": h30.per_tahun(h["r"]), "bobot_sama": h30.per_tahun(e["r"]), "jii": h30.per_tahun(rj)}).round(1).reset_index().rename(columns={"index": "tahun"}).to_dict("records")
                out["kontribusi_bobot_sama"] = h30.kontribusi(e["pos"])
                seri[jenis] = h
            print(f"  {jenis} {nama} selesai ({time.time() - t0:.0f} dtk)", flush=True)
        out["lulus_semua"] = all(v["lulus"] for v in out["skenario"].values())
        hasil[jenis] = out
    j = pd.concat([seri["h32"]["r"].rename("a"), seri["h22"]["r"].rename("b")], axis=1, join="inner").dropna()
    irisan = [len(seri["h32"]["isi"].get(b, set()) & seri["h22"]["isi"].get(b, set())) / len(seri["h32"]["isi"][b])
              for b in j.index if seri["h32"]["isi"].get(b)]
    hasil["h32_vs_h22"] = {"korelasi_bulanan": round(float(j["a"].corr(j["b"])), 2), "irisan_pegangan_pct": round(float(np.mean(irisan)) * 100, 1)}
    hasil["lulus_dev"] = hasil["h32"]["lulus_semua"]
    hasil["versi_data"] = hg.sidik(S["kode"], S["tgl"][0], S["tgl"][-1])
    hasil["keterbatasan_data"] = KETERBATASAN
    hasil = json.loads(json.dumps(hasil, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    dt.simpan_hasil(f"h32_{periode}", hasil)
    print(json.dumps(hasil, ensure_ascii=False, indent=1))
    print(f"SELESAI {time.time() - t0:.0f} dtk", flush=True)
    return hasil


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periode", choices=["dev"], default="dev")
    a = ap.parse_args()
    jalankan(a.periode)


if __name__ == "__main__":
    utama()
