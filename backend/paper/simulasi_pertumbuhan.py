import sys
from collections import Counter

import numpy as np
import pandas as pd

from backend.paper import mesin_pertumbuhan as mp
from backend.paper import sintetis_pertumbuhan as sp

TELAT_EMAS_MAKS = 2
SPREAD_MODEL = 0.03
BIAYA_TAHUN_MODEL = 0.005
BIAYA_REBAL_MODEL = 0.005


def model_nilai(data, strategi, produk, hari, modal, rebalance_pertama):
    bobot = mp.BOBOT[strategi]
    harga_rd = {}
    for kaki in ("lokal", "global"):
        for p in produk[kaki]:
            s = pd.Series({D: data.rd(p["id"], p["mu"], D) for D in hari}, dtype=float).ffill()
            harga_rd[p["id"]] = s
    emas = pd.Series({D: data.kurs_emas(D) for D in hari}, dtype=float).ffill()
    d0 = hari[0]
    unit = {}
    for kaki in ("lokal", "global"):
        for p in produk[kaki]:
            unit[p["id"]] = bobot[kaki] * modal / len(produk[kaki]) / harga_rd[p["id"]].loc[d0]
    emas_nilai = bobot.get("emas", 0.0) * modal * (1 - SPREAD_MODEL / 2)
    keluar = {}
    sebelumnya = d0
    for D in hari:
        if D != d0:
            rasio = emas.loc[D] / emas.loc[sebelumnya]
            emas_nilai *= rasio * (1 - BIAYA_TAHUN_MODEL) ** ((D - sebelumnya).days / 365)
        rd_nilai = {k: sum(unit[p["id"]] * harga_rd[p["id"]].loc[D] for p in produk[k]) for k in ("lokal", "global")}
        total = sum(rd_nilai.values()) + emas_nilai
        ada = [h for h in hari if h.year == D.year and h.month == 12]
        if D.month == 12 and D.year >= rebalance_pertama and ada and D == ada[-1] and D != d0:
            for kaki in ("lokal", "global"):
                target = bobot[kaki] * total
                for p in produk[kaki]:
                    unit[p["id"]] = target / len(produk[kaki]) / harga_rd[p["id"]].loc[D]
                total -= BIAYA_REBAL_MODEL * abs(rd_nilai[kaki] - target) / 2
            if "emas" in bobot:
                target = bobot["emas"] * total
                total -= SPREAD_MODEL / 2 * abs(emas_nilai - target)
                emas_nilai = bobot["emas"] * total
        keluar[D] = sum(unit[p["id"]] * harga_rd[p["id"]].loc[D] for k in ("lokal", "global") for p in produk[k]) + emas_nilai
        sebelumnya = D
    return pd.Series(keluar)


def ringkas_emas(m):
    beli = [t for t in m.transaksi if t["kaki"] == "emas" and t["sisi"] == "beli"]
    selesai = [k for k in m.kejadian if k["jenis"] == "order_selesai"]
    nilai = sum(t["nilai"] for t in beli)
    prem = sum(t["premium_eksekusi"] * t["nilai"] for t in beli if t["premium_eksekusi"] is not None) / nilai if nilai else None
    prem_k = sum(t["premium_keputusan"] * t["nilai"] for t in beli) / nilai if nilai else None
    pakai = [t["pakai_batas"] for t in beli]
    sisa = sum(o["sisa"] for o in m.st["antrean"] if o["jenis"] == "etf_beli")
    return {"selesai_hari": selesai[0]["hari_order"] if selesai else None, "tgl_selesai": selesai[0]["tgl"] if selesai else None,
            "hari_beli": len({t["tgl"] for t in beli}), "lewati": len([k for k in m.kejadian if k["jenis"] == "lewati_premium"]), "premium_rata": prem, "premium_keputusan_rata": prem_k,
            "pakai_rata": float(np.mean(pakai)) if pakai else None, "pakai_maks": float(np.max(pakai)) if pakai else None, "sisa_belum_beli": sisa,
            "kas": m.st["kas"], "etf": m.st["etf"], "hari_order": max([o["hari"] for o in m.st["antrean"] if o["jenis"] == "etf_beli"], default=None)}


def jalankan_nyata(mulai):
    from backend.paper.uji_maju_pertumbuhan import produk_halaman
    data = mp.DataNyata()
    produk = produk_halaman()
    akhir_rd = min(max(data.nav(p["id"]).index) for k in produk for p in produk[k])
    akhir_etf = max(df.index.max() for df in data.etf_df.values())
    akhir = min(akhir_rd, akhir_etf)
    hari = [h for h in data.hari if pd.Timestamp(mulai) <= h <= akhir]
    hasil = {}
    for s in ("h35", "h37"):
        m = mp.Mesin(s, data, mulai=mulai)
        m.st["produk"] = produk
        m.jalan(hari)
        hasil[s] = m
    return data, produk, hari, hasil


def laporan_nyata(mulai):
    data, produk, hari, hasil = jalankan_nyata(mulai)
    m35, m37 = hasil["h35"], hasil["h37"]
    awal, akhir = hari[0], hari[-1]
    print(f"UJI KERING (memori saja, tidak menulis paper_h35_*/paper_h37_*): mulai {mulai}, masuk {m37.st['masuk']}, sampai {akhir.date()}, {len(m37.ekuitas)} hari, ETF {m37.st['etf']}")
    e = ringkas_emas(m37)
    sel = "belum selesai (hari ke-%s, sisa Rp%s)" % (e["hari_order"], f"{e['sisa_belum_beli']:,.0f}") if e["selesai_hari"] is None else f"hari ke-{e['selesai_hari']} ({e['tgl_selesai']})"
    print(f"Pembelian emas selesai: {sel}; hari beli {e['hari_beli']}; hari dilewati karena premium {e['lewati']}")
    fp = lambda v: "-" if v is None else format(v * 100, "+.2f") + "%"
    print(f"Premium rata-rata saat beli (tertimbang nilai): keputusan {fp(e['premium_keputusan_rata'])} (t-1), eksekusi {fp(e['premium_rata'])} (t); sisa kas emas Rp{e['kas']:,.0f}; "
          f"pemakaian batas 20% nilai transaksi: rata {'-' if e['pakai_rata'] is None else format(e['pakai_rata'] * 100, '.0f') + '%'}, maks {'-' if e['pakai_maks'] is None else format(e['pakai_maks'] * 100, '.0f') + '%'}")
    cnt = Counter(k["jenis"] for k in m37.kejadian)
    print(f"Kejadian H37: {sum(cnt.values())} ({', '.join(f'{k} {v}' for k, v in sorted(cnt.items()))}); H35: {len(m35.kejadian)}")
    for s, m in (("H35", m35), ("H37", m37)):
        v = m.ekuitas[-1]["nilai"]
        print(f"Ekuitas {s} {m.ekuitas[-1]['tgl']}: Rp{v:,.0f} ({(v / mp.MODAL - 1) * 100:+.2f}%), kas Rp{m.ekuitas[-1]['kas']:,.0f}")
    telat = data.telat_emas(akhir)
    akhir_emas = min(akhir, data.emas_usd.index.max())
    hari_model = [h for h in hari if h <= akhir_emas and h >= pd.Timestamp(m37.st["masuk"])]
    for s, m in (("H35", m35), ("H37", m37)):
        if telat > TELAT_EMAS_MAKS:
            print(f"Selisih paper vs model {s}: tidak_valid (seri emas pembanding telat {telat} hari bursa > {TELAT_EMAS_MAKS}, terakhir {data.emas_usd.index.max().date()}), tidak dihitung")
            continue
        model = model_nilai(data, s.lower(), produk, hari_model, mp.MODAL, mp.REBALANCE_PERTAMA)
        eq = pd.Series({x["tgl"]: x["nilai"] for x in m.ekuitas})
        D = hari_model[-1]
        r_paper = eq.loc[str(D.date())] / mp.MODAL - 1
        r_model = model.iloc[-1] / mp.MODAL - 1
        print(f"Selisih paper vs model {s} s/d {D.date()} (emas = GC=F futures x kurs, bukan spot; telat {telat} hari bursa): paper {r_paper * 100:+.2f}%, model {r_model * 100:+.2f}%, selisih {(r_paper - r_model) * 100:+.2f} poin ({len(hari_model)} hari, belum setahun)")
    if m37.st["etf"] and telat <= TELAT_EMAS_MAKS:
        kode = m37.st["etf"]
        c = data.etf_df[kode]["close"]
        c = c.loc[(c.index >= hari_model[0]) & (c.index <= hari_model[-1])]
        g0, g1 = data.kurs_emas(c.index[0]), data.kurs_emas(c.index[-1])
        print(f"Tracking {kode} vs GC=F x kurs {c.index[0].date()} - {c.index[-1].date()}: ETF {(c.iloc[-1] / c.iloc[0] - 1) * 100:+.2f}%, emas {(g1 / g0 - 1) * 100:+.2f}%")
    return hasil


def kasus_sintetis():
    hari = sp.hari_kerja("2026-12-01", "2028-01-14")
    data = sp.bangun(hari, rd_naik={1: 0.0006, 2: 0.0006, 3: 0.0001})
    m = sp.mesin("h37", data, hari[0])
    m.jalan(hari)
    r = [k["tgl"] for k in m.kejadian if k["jenis"] == "rebalance"]
    ok = r == ["2027-12-31"] and m.st["masuk"] == "2026-12-01"
    print(f"Kasus sintetis mulai 1 Des 2026: rebalance Des 2026 dilewati, rebalance tercatat di {r}: {'LULUS' if ok else 'GAGAL'}")
    return ok


def jalan(argumen):
    mulai = "2026-11-02"
    if "--mulai" in argumen:
        mulai = argumen[argumen.index("--mulai") + 1]
    laporan_nyata(mulai)
    kasus_sintetis()
    print("SELESAI")


if __name__ == "__main__":
    jalan(sys.argv[1:])
