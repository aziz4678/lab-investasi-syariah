import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import harga as hg
from backend.db import koneksi
from backend.research import uji_h36 as h36
from backend.research import uji_h40 as h40
from backend.research.uji_h40 import BASE_MAKS, BASE_MIN, BASE_RANGE, FEE_BELI, LOT, MODAL, RS_HARI, RS_MIN_N, RS_PCT, SLIP, VOL_HARI, VOL_X, pc

ATR_STOP, STOP_MAKS, ATR_KEJAR = 2.0, 0.15, 3.0
BOBOT_MAKS = 0.20
RISIKO, SLOT, TAHAN = 0.01, 5, 60
LIKUID, HARGA_MIN = h36.LIKUID, h36.HARGA_MIN
AKHIR_DEV = h40.AKHIR_DEV
PENANDA_BUKA = koneksi.penanda("holdout_dibuka_h41")
ATURAN = {
    "status": "POST-HOC: dibuat setelah hasil dev H40 terlihat (2 trade); H40 tidak diubah",
    "perubahan_dari_h40": ["universe = definisi standar seragam persis (uji_h36.Harga.lolos: nilai rata-rata 20 hari, ATR% 1,5-5, harga, tanpa volume nol 5 hari) + DES + S1/S2/S3",
                           "stop awal = entry - 2 x ATR14 (sampai hari sinyal), skip bila jarak > 15%", "jangan mengejar: skip bila open > base_high + 3 x ATR14", "bobot per posisi maks 20% ekuitas"],
    "entry": "H40: regime JII > MA200, Stage 2, RS126 top 20%, base 25-60 hari berakhir H-1 range <= 25% terpanjang, close > base_high dan volume >= 1,5x rata-rata 50 hari sebelum sinyal, open besok",
    "exit": "low <= stop -> min(stop, open) (termasuk hari entry); close < MA20 -> jual open besok; hari bursa ke-60 setelah entry jual di close; stop tetap",
    "sizing": "risiko 1% ekuitas close kemarin, lot 100, bobot maks 20%, maks 5 posisi, prioritas RS tertinggi",
    "biaya": "fee 0,15% + 0,25% + 1 tick per sisi + slippage 0,2% per sisi (termasuk stop)",
    "varian": "V-B target = entry + (base_high - base_low), stop, 60 hari, tanpa MA20; V-D tanpa filter JII (info)",
    "periode": "dev 26 Nov 2020 - 31 Des 2023; holdout 2024 - Okt 2026 hanya bila dev lolos; Langkah 0: trade dev < 30 -> STOP",
    "lolos": "standar seragam (dasar, S1, S2, S3) + trade dev >= 30 + expectancy > 0R + (korelasi H11a < 0,5 atau Sharpe 50/50 > Sharpe H11a)",
}


class P41(h40.P40):
    def lolos(self, likuid, hmin):
        return h36.Harga.lolos(self, likuid, hmin)

    def komponen(self, likuid=LIKUID, hmin=HARGA_MIN, pakai_jii=True):
        kunci = (likuid, hmin, pakai_jii)
        if kunci in self._h11:
            return self._h11[kunci]
        Cd, Hd, Ld, Vd = self.Cd, self.Hd, self.Ld, self.Vd
        ma = {n: Cd.rolling(n).mean() for n in (20, 50, 100, 200)}
        stage2 = ((Cd > ma[20]) & (ma[20] > ma[50]) & (ma[50] > ma[100]) & (ma[100] > ma[200]) & (ma[200] > ma[200].shift(20))).to_numpy(bool)
        lolos = pd.DataFrame(self.lolos(likuid, hmin), index=self.T, columns=self.kode)
        univ = (self.dasar & lolos).to_numpy(bool)
        r = (Cd / Cd.shift(RS_HARI) - 1).where(pd.DataFrame(univ, index=self.T, columns=self.kode))
        pct = r.rank(axis=1, pct=True)
        rs = ((pct >= RS_PCT) & (r.notna().sum(axis=1) >= RS_MIN_N).to_numpy()[:, None]).to_numpy(bool)
        bh = pd.DataFrame(np.nan, index=self.T, columns=self.kode)
        bl = bh.copy()
        for L in range(BASE_MIN, BASE_MAKS + 1):
            hi = Hd.rolling(L).max().shift(1)
            lo = Ld.rolling(L).min().shift(1)
            ok = ((hi - lo) / hi <= BASE_RANGE) & hi.notna()
            bh = bh.where(~ok, hi)
            bl = bl.where(~ok, lo)
        brk = (Cd > bh).to_numpy(bool)
        vol = (Vd >= VOL_X * Vd.rolling(VOL_HARI).mean().shift(1)).to_numpy(bool)
        reg = np.repeat(self.jii_ok.to_numpy(bool)[:, None], len(self.kode), axis=1) if pakai_jii else np.ones((self.n, len(self.kode)), bool)
        atr = self.ATR / 100 * self.Cf
        tahap = [("universe", univ), ("regime JII", reg), ("stage 2", stage2), ("RS top 20%", rs), ("base valid", bh.notna().to_numpy(bool)), ("close > base_high", brk), ("volume 1,5x", vol)]
        sig = np.ones_like(univ)
        for _, m in tahap:
            sig = sig & m
        sig = sig & np.isfinite(atr)
        out = {"sig": sig, "tahap": tahap, "bh": bh.to_numpy(float), "bl": bl.to_numpy(float), "atr": atr, "pct": pct.to_numpy(float), "ma20": ma[20].to_numpy(float)}
        self._h11[kunci] = out
        return out


class Buku41(h40.Buku):
    def beli(self, i, k, stop, pct, eq_ref):
        P = self.P
        c = P.ki[k]
        f = P.F[i, c]
        raw = P.O[i, c] / f
        px = (raw + h40.h3_tick(raw) * self.n_tick) * (1 + self.slip)
        satuan = px * (1 + FEE_BELI)
        per = satuan - stop / f
        if per <= 0:
            return False
        maks_kas = int(self.kas / satuan // LOT) * LOT
        maks_bobot = int(BOBOT_MAKS * eq_ref / satuan // LOT) * LOT
        lembar_raw = min(int(RISIKO * eq_ref / per // LOT) * LOT, maks_kas, maks_bobot)
        if lembar_raw < LOT:
            return False
        uang = lembar_raw * satuan
        self.kas -= uang
        self.pegang[k] = {"lembar": lembar_raw / f, "biaya": uang, "i": i, "tgl": P.T[i], "terima": 0.0, "risiko": lembar_raw * per, "pct": pct, "hari": 0, "stop": stop}
        return True


def strategi(P, mode="utama", n_tick=1, likuid=LIKUID, hmin=HARGA_MIN, buang=frozenset(), pakai_jii=True):
    S = P.komponen(likuid, hmin, pakai_jii)
    sig, bh, bl, atr, pct, ma20 = S["sig"], S["bh"], S["bl"], S["atr"], S["pct"], S["ma20"]
    if buang:
        sig = sig.copy()
        sig[:, [P.ki[k] for k in buang if k in P.ki]] = False
    B = Buku41(P, n_tick, SLIP)
    flag, target = set(), {}
    hit = {"sinyal": 0, "sudah_dipegang": 0, "tak_bisa": 0, "kejar": 0, "stop_jauh": 0, "slot_penuh": 0, "lot_kurang": 0, "dibeli": 0}
    per_tahun = {}
    for i in range(P.i0, P.n):
        B.awal_hari(i)
        akhir = i == P.n - 1
        for k in sorted(flag & set(B.pegang), key=lambda z: B.pegang[z]["i"]):
            if B.bisa(i, k):
                B.jual(i, k, P.O[i, P.ki[k]], "ma20")
                flag.discard(k)
        flag &= set(B.pegang)
        if not akhir and i > P.i0 and sig[i - 1].any():
            d = i - 1
            kand = np.flatnonzero(sig[d])
            kand = kand[np.argsort(-np.nan_to_num(pct[d, kand]))]
            for c in kand:
                k = P.kode[c]
                if P.T[i] <= AKHIR_DEV + pd.Timedelta(days=3):
                    hit["sinyal"] += 1
                if k in B.pegang:
                    hit["sudah_dipegang"] += 1
                    continue
                if not B.bisa(i, k):
                    hit["tak_bisa"] += 1
                    continue
                e = P.O[i, c]
                if e > bh[d, c] + ATR_KEJAR * atr[d, c]:
                    hit["kejar"] += 1
                    continue
                s = e - ATR_STOP * atr[d, c]
                if not (s < e) or (e - s) / e > STOP_MAKS:
                    hit["stop_jauh"] += 1
                    continue
                if len(B.pegang) >= SLOT:
                    hit["slot_penuh"] += 1
                    continue
                if B.beli(i, k, s, pct[d, c], B.eq[i - 1]):
                    hit["dibeli"] += 1
                    flag.discard(k)
                    B.pegang[k]["i"] = i
                    target[k] = e + (bh[d, c] - bl[d, c])
                    B.pegang[k]["sebagian"] = False
                    per_tahun[P.T[i].year] = per_tahun.get(P.T[i].year, 0) + 1
                else:
                    hit["lot_kurang"] += 1
        for k in sorted(B.pegang):
            c = P.ki[k]
            h = B.pegang[k]
            if not P.ada[i, c] or P.TT[i, c]:
                continue
            o, lo, hi = P.O[i, c], P.Lw[i, c], P.H[i, c]
            if mode == "B" and o >= target[k]:
                B.jual(i, k, o, "target")
            elif lo <= h["stop"]:
                B.jual(i, k, min(h["stop"], o), "stop")
            elif mode == "B" and hi >= target[k]:
                B.jual(i, k, target[k], "target")
        for k in sorted(B.pegang):
            if i - B.pegang[k]["i"] >= TAHAN and B.bisa(i, k):
                B.jual(i, k, P.C[i, P.ki[k]], "waktu")
        if not akhir:
            if mode != "B":
                for k in B.pegang:
                    c = P.ki[k]
                    if P.ada[i, c] and P.C[i, c] < ma20[i, c]:
                        flag.add(k)
            B.tutup_hari(i)
        else:
            B.akhir(i)
    return {"eq": B.eq, "trades": pd.DataFrame(B.trades), "laba": B.laba, "expo": B.expo, "hit": hit, "per_tahun": per_tahun}


def seragam(P, jii_m, ew_cache, cfg):
    kw = {"n_tick": cfg["ntick"], "likuid": cfg["likuid"], "hmin": cfg["hmin"]}
    h = strategi(P, "utama", **kw)
    mh = h36.metrik(P, h)
    kunci = (cfg["likuid"], cfg["hmin"])
    me = h36.metrik(P, ew_cache(kunci, frozenset()))
    ew = ew_cache(kunci, frozenset())
    top_h = sorted(h["laba"], key=lambda k: -h["laba"][k])
    top_e = sorted(ew["laba"], key=lambda k: -ew["laba"][k])
    k = {"1_vs_ew": mh["cagr"] > me["cagr"], "2_vs_jii": mh["cagr"] > jii_m["cagr"]}
    out = {"cagr": mh["cagr"], "dd": mh["dd"], "ew": me["cagr"], "jii": jii_m["cagr"], "trade": int(len(h["trades"]))}
    for m in (5, 10):
        hm = h36.metrik(P, strategi(P, "utama", buang=frozenset(top_h[:m]), **kw))
        em = h36.metrik(P, ew_cache(kunci, frozenset(top_e[:m])))
        out[f"tanpa{m}"] = (hm["cagr"], em["cagr"])
        k[f"{3 if m == 5 else 4}_tanpa{m}"] = hm["cagr"] > em["cagr"]
    a, b, c = h36.tanpa_terbaik(mh["twr"]), h36.tanpa_terbaik(me["twr"]), h36.tanpa_terbaik(jii_m["twr"])
    out["tanpa_tahun"] = (a, b, c)
    k["5_tanpa_tahun"] = bool(a > b and a > c)
    out["kriteria"] = {x: bool(v) for x, v in k.items()}
    out["lulus"] = all(k.values())
    return out, h, mh


def langkah0():
    P = P41(h40.SAMPAI_DEV, h40.WARM)
    S = P.komponen()
    i1 = int(np.searchsorted(P.T.values, np.datetime64(AKHIR_DEV), side="right"))
    print(f"[langkah 0] dev {P.T[P.i0].date()} s/d {AKHIR_DEV.date()}, {i1 - P.i0} hari bursa, indikator valid sejak hari ke-{h40.WARM}")
    sisa = None
    print("corong hari-saham (berurutan, kumulatif):")
    for nama, m in S["tahap"]:
        sisa = m[P.i0:i1] if sisa is None else sisa & m[P.i0:i1]
        print(f"  {nama:<18} {int(sisa.sum()):>8}")
    print(f"  {'ATR valid (sinyal awal)':<18} {int(S['sig'][P.i0:i1].sum()):>8}")
    h = strategi(P, "utama")
    tr = h["trades"]
    print("corong eksekusi (hari-saham sinyal -> trade):", h["hit"])
    ke = {int(y): int(v) for y, v in h["per_tahun"].items()}
    print("trade per tahun (tanggal entry):", ke, "| total trade selesai:", len(tr))
    n_dev = len(tr[tr["beli"] <= AKHIR_DEV]) if len(tr) else 0
    ok = n_dev >= 30
    print(f"trade dev = {n_dev} -> {'LANJUT' if ok else 'STOP (< 30), dev tidak dijalankan, tunggu keputusan user'}")
    dt.simpan_hasil("h41_langkah0", {"dibuat": datetime.now().isoformat(timespec="seconds"), "trade_dev": n_dev, "lanjut": bool(ok), "corong": {k: int(v) for k, v in h["hit"].items()}, "per_tahun": {str(a): b for a, b in ke.items()}})
    return ok


def utama(periode="dev"):
    P = P41(h40.SAMPAI_DEV if periode == "dev" else None, h40.WARM if periode == "dev" else 0)
    if periode == "holdout":
        P.i0 = int(np.searchsorted(P.T.values, np.datetime64("2024-01-01"), side="left"))
    print(f"[{periode}] sim {P.T[P.i0].date()} s/d {P.T[-1].date()} ({P.n - P.i0} hari)", flush=True)
    jii_m = h36.metrik(P, h36.jii_total(P))
    cache = {}

    def ew_cache(kunci, buang):
        if (kunci, buang) not in cache:
            cache[(kunci, buang)] = h36.bobot_sama(P, kunci[0], kunci[1], buang)
        return cache[(kunci, buang)]

    me = h36.metrik(P, ew_cache((LIKUID, HARGA_MIN), frozenset()))
    h11, seeds = h40.h11a_median(P)
    r11 = h40.rincian(P, h11)
    rh11 = h40.harian(P, h11)
    hasil = {}
    pertama = None
    for nama, ubah in {"utama": {}, "S1_2tick": {"ntick": 2}, "S2_rp20m": {"likuid": 20e9}, "S3_rp200": {"hmin": 200}}.items():
        cfg = {"ntick": 1, "likuid": LIKUID, "hmin": HARGA_MIN, **ubah}
        r, h, mh = seragam(P, jii_m, ew_cache, cfg)
        hasil[nama] = r
        if nama == "utama":
            pertama = (r, h, mh)
        print(f"{nama}: CAGR {pc(r['cagr'])}% vs EW {pc(r['ew'])}% JII {pc(r['jii'])}% | trade {r['trade']} | tanpa5 {pc(r['tanpa5'][0])} vs {pc(r['tanpa5'][1])} | tanpa10 {pc(r['tanpa10'][0])} vs {pc(r['tanpa10'][1])} | tahun {[pc(x) for x in r['tanpa_tahun']]} | {r['kriteria']}", flush=True)
    r, h, mh = pertama
    ru = h40.rincian(P, h)
    rhu = h40.harian(P, h)
    kor = float(rhu.corr(rh11))
    comb = 0.5 * rhu + 0.5 * rh11
    sh_comb = float(comb.mean() / comb.std() * np.sqrt(252)) if comb.std() > 0 else np.nan
    info = {}
    for nama, kw in (("V-B", {"mode": "B"}), ("V-D", {"pakai_jii": False})):
        hv = strategi(P, **kw)
        info[nama] = (h40.rincian(P, hv), float(h40.harian(P, hv).corr(rh11)))
    print(f"\n===== H41 {periode} | {P.T[P.i0].date()} s/d {P.T[-1].date()} =====")
    print(h40.baris("UTAMA", ru, kor))
    for nama, (rv, kv) in info.items():
        print(h40.baris(nama + " (info)", rv, kv))
    print(h40.baris("H11a (mesin)", r11, 1.0))
    ej = lambda m, n: f"{n:<12} CAGR {pc(m['cagr'])}% | DD {pc(m['dd'])}% | Sharpe {m['sharpe']:.2f} | korelasi H11a {float(m['_r'].corr(rh11)):.2f}"
    jr = pd.Series(h36.jii_total(P)["eq"][P.i0:], index=P.T[P.i0:]).pct_change().fillna(0.0)
    er = pd.Series(ew_cache((LIKUID, HARGA_MIN), frozenset())["eq"][P.i0:], index=P.T[P.i0:]).pct_change().fillna(0.0)
    print(ej({**jii_m, "_r": jr}, "JII B&H"))
    print(ej({**me, "_r": er}, "EW syariah"))
    print(f"Sharpe 50/50 (H41+H11a) {sh_comb:.2f} vs H11a {r11['sharpe']:.2f} | korelasi harian {kor:.2f}")
    print(f"eksekusi: {h['hit']} | trade per tahun {h['per_tahun']}")
    print("alasan exit:", h["trades"]["alasan"].value_counts().to_dict() if len(h["trades"]) else {})
    print("per tahun H41/EW/JII:", {int(y): (pc(mh["twr"].get(y)), pc(me["twr"].get(y)), pc(jii_m["twr"].get(y))) for y in mh["twr"].index})
    print("5 penyumbang laba:", [(k, round(float(v) / 1e6, 1)) for k, v in sorted(h["laba"].items(), key=lambda x: -x[1])[:5]])
    standar = all(v["lulus"] for v in hasil.values())
    syarat = {"trade>=30": ru["n"] >= 30 if periode == "dev" else True, "expectancy>0R": bool(ru.get("expect", -1) > 0), "tambah_nilai": bool(kor < 0.5 or sh_comb > r11["sharpe"])}
    lulus = bool(standar and all(syarat.values()))
    print("\nkriteria:")
    for nama, v in hasil.items():
        print(f"  standar {nama}: {'LULUS' if v['lulus'] else 'GAGAL'} {[x for x, y in v['kriteria'].items() if not y]}")
    for nama, v in syarat.items():
        print(f"  {nama}: {'LULUS' if v else 'GAGAL'}")
    print(f"VONIS {periode.upper()}: {'LOLOS' if lulus else 'GAGAL'}")
    versi = hg.sidik(P.kode, mulai=h36.MULAI, akhir=P.T[-1], koleksi="harga_bersih_2020", kolom=("open", "close", "dividen", "saham_tercatat"))
    simpan = {"dibuat": datetime.now().isoformat(timespec="seconds"), "periode": periode, "lulus": lulus, "standar": bool(standar), "syarat": {k: bool(v) for k, v in syarat.items()},
              "utama": {k: (pc(v) if k in ("cagr", "dd") else v) for k, v in ru.items() if k != "twr"}, "korelasi_h11a": kor, "sharpe_50_50": sh_comb,
              "h11a": {k: (pc(v) if k in ("cagr", "dd") else v) for k, v in r11.items() if k != "twr"},
              "varian_seragam": {k: {"cagr": pc(v["cagr"]), "ew": pc(v["ew"]), "jii": pc(v["jii"]), "trade": v["trade"], "kriteria": v["kriteria"], "lulus": v["lulus"]} for k, v in hasil.items()},
              "varian_info": {k: {x: (pc(y) if x in ("cagr", "dd") else y) for x, y in v[0].items() if x != "twr"} for k, v in info.items()},
              "versi_data": {**versi, "keterbatasan": "dev efektif mulai 26 Nov 2020; survivorship ditutup 2020+; DES point-in-time; H11a = mesin sama (lot 100, median 5 seed)"}}
    dt.simpan_hasil(f"h41_{periode}", json.loads(json.dumps(simpan, default=str)))
    print("SELESAI")
    return lulus


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "kunci":
        if dt.baca_hasil("h41_aturan"):
            raise SystemExit("aturan sudah dikunci")
        dt.simpan_hasil("h41_aturan", {"dikunci": datetime.now().isoformat(timespec="seconds"), **ATURAN})
        print("aturan dikunci")
    elif arg == "langkah0":
        langkah0()
    elif arg == "dev":
        l0 = dt.baca_hasil("h41_langkah0")
        if not l0 or not l0.get("lanjut"):
            raise SystemExit("dev tidak dijalankan: langkah 0 belum lolos")
        utama("dev")
    elif arg == "holdout":
        dev = dt.baca_hasil("h41_dev")
        if not dev or not dev.get("lulus"):
            raise SystemExit("holdout tidak dibuka: dev belum lolos")
        if PENANDA_BUKA.exists():
            raise SystemExit("holdout H41 sudah dibuka")
        PENANDA_BUKA.write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n")
        utama("holdout")
    else:
        raise SystemExit("pakai: kunci | langkah0 | dev | holdout")
