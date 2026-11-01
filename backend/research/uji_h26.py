import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import isi_backtest as ib
from backend.research import uji_tren as ut
from backend.research.uji_dividen import bersih

AMBANG = 0.30
M_KETAT = 2.0
SENSITIVITAS = [(0.20, 1.5), (0.20, 2.5), (0.40, 1.5), (0.40, 2.5)]


def simulasi(x, t, sinyal, ambang, m_ketat):
    o, c, h = x["open"].to_numpy(float), x["close"].to_numpy(float), x["high"].to_numpy(float)
    atr = x["atr"].to_numpy(float)
    rasio = (x["close_mentah"] / x["close"]).to_numpy(float)
    n = len(x)
    hasil = []
    bebas = 0
    for i in np.flatnonzero(sinyal):
        if i < bebas or i + 1 >= n or not np.isfinite(atr[i]):
            continue
        e = o[i + 1]
        stop = e - ut.MULT_ATR * atr[i]
        tertinggi = c[i + 1]
        m = ut.MULT_ATR
        kena = False
        j = i + 1
        while True:
            if c[j] < stop:
                if j + 1 <= n - 1:
                    k, px, alasan = j + 1, o[j + 1], "stop"
                else:
                    k, px, alasan = j, c[j], "akhir_data"
                break
            tertinggi = max(tertinggi, c[j])
            if ambang is not None and c[j] >= e * (1 + ambang):
                m, kena = m_ketat, True
            if np.isfinite(atr[j]):
                stop = max(stop, tertinggi - m * atr[j])
            if j - (i + 1) >= ut.MAKS_HARI:
                k, px, alasan = j, c[j], "waktu"
                break
            if j == n - 1:
                k, px, alasan = j, c[j], "terbuka"
                break
            j += 1
        hasil.append({
            "ticker": t, "tgl": x.index[i], "tgl_exit": x.index[k], "hari": k - i,
            "stop_pct": ut.MULT_ATR * atr[i] / e * 100, "kotor": (px / e - 1) * 100,
            "net": bersih(e, px, e * rasio[i + 1], px * rasio[k]), "alasan": alasan,
            "mfe": (h[i + 1:max(k, i + 2)].max() / e - 1) * 100, "kena": kena,
        })
        bebas = k
    return hasil


def kumpulkan(siap, ambang, m_ketat, mulai, akhir):
    semua = []
    for t, x in siap.items():
        s = ((x["close"] >= x["maks250"]) & x["lolos"]).fillna(False).to_numpy(bool)
        semua += simulasi(x, t, s, ambang, m_ketat)
    tr = pd.DataFrame(semua)
    return tr[(tr["tgl"] >= mulai) & (tr["tgl"] <= akhir)].reset_index(drop=True)


def mc(nama, tr, siap, mulai, akhir, mentah):
    u = ib.monte_carlo(nama, tr, siap, mulai, akhir, mentah)
    menang = tr[tr["net"] > 0]
    r = {"cagr": u["cagr"], "dd": u["dd"], "sinyal": int(len(tr)), "win_rate": round(float((tr["net"] > 0).mean() * 100), 1),
         "net": round(float(tr["net"].mean()), 2), "median_net": round(float(tr["net"].median()), 2),
         "rata_menang": round(float(menang["net"].mean()), 2), "rata_kalah": round(float(tr.loc[tr["net"] <= 0, "net"].mean()), 2),
         "hari": round(float(tr["hari"].mean()), 1), "kena_ambang": int(tr["kena"].sum()),
         "bawa_pulang": round(float((menang["kotor"] / menang["mfe"]).median()), 2)}
    print(f"{nama}: CAGR med {r['cagr']['median']} (p5 {r['cagr']['p5']} p95 {r['cagr']['p95']}) DD med {r['dd']['median']} | "
          f"sinyal {r['sinyal']} WR {r['win_rate']} net {r['net']} hari {r['hari']} kena {r['kena_ambang']} bawa pulang {r['bawa_pulang']}", flush=True)
    return r


def tanpa5(tr):
    return tr.drop(tr["net"].nlargest(5).index).reset_index(drop=True)


def cek_sama(siap, mulai, akhir):
    a = ut.kumpulkan(siap, lambda x: x["close"] >= x["maks250"])
    a = a[(a["tgl"] >= mulai) & (a["tgl"] <= akhir)].reset_index(drop=True)
    b = kumpulkan(siap, None, None, mulai, akhir)
    if len(a) != len(b) or not np.allclose(a["net"].to_numpy(), b["net"].to_numpy()) or not (a["tgl_exit"].to_numpy() == b["tgl_exit"].to_numpy()).all():
        raise RuntimeError("simulasi H26 tanpa ambang tidak sama dengan uji_tren.simulasi")
    print(f"cek: tanpa ambang identik dengan H11a ({len(a)} sinyal)", flush=True)


def utama():
    hasil = {"dibuat": pd.Timestamp.now().isoformat(), "ambang": AMBANG, "m_ketat": M_KETAT}

    siap = ut.siapkan_dev()
    mulai, akhir = pd.Timestamp("2010-01-01"), pd.Timestamp("2019-12-31")
    cek_sama(siap, mulai, akhir)
    a = kumpulkan(siap, None, None, mulai, akhir)
    b = kumpulkan(siap, AMBANG, M_KETAT, mulai, akhir)
    mentah = {t: baca_mentah(t) for t in set(a["ticker"]) | set(b["ticker"])}
    dev = {"h11a": mc("dev H11a", a, siap, mulai, akhir, mentah), "h26": mc("dev H26", b, siap, mulai, akhir, mentah),
           "h11a_tanpa5": mc("dev H11a tanpa 5", tanpa5(a), siap, mulai, akhir, mentah),
           "h26_tanpa5": mc("dev H26 tanpa 5", tanpa5(b), siap, mulai, akhir, mentah), "sensitivitas": []}
    for amb, m in SENSITIVITAS:
        s = kumpulkan(siap, amb, m, mulai, akhir)
        for t in set(s["ticker"]) - set(mentah):
            mentah[t] = baca_mentah(t)
        dev["sensitivitas"].append({"ambang": amb, "m": m, **mc(f"dev +{amb:.0%} {m}xATR", s, siap, mulai, akhir, mentah)})
    hasil["dev"] = dev

    siap = ut.siapkan_holdout()
    mulai = pd.Timestamp("2020-01-01")
    akhir = max(x.index.max() for x in siap.values())
    a = kumpulkan(siap, None, None, mulai, akhir)
    b = kumpulkan(siap, AMBANG, M_KETAT, mulai, akhir)
    akhir = max(a["tgl_exit"].max(), b["tgl_exit"].max())
    mentah = {t: baca_mentah(t) for t in set(a["ticker"]) | set(b["ticker"])}
    hasil["baru"] = {"h11a": mc("2020+ H11a", a, siap, mulai, akhir, mentah), "h26": mc("2020+ H26", b, siap, mulai, akhir, mentah)}

    d, n = hasil["dev"], hasil["baru"]
    med = lambda r: r["cagr"]["median"]
    sens_ok = sum(med(s) >= med(d["h11a"]) for s in d["sensitivitas"])
    krit = [
        (med(d["h26"]) >= med(d["h11a"]) + 1, f"{med(d['h26'])}% vs {med(d['h11a'])}% + 1"),
        (d["h26"]["dd"]["median"] >= d["h11a"]["dd"]["median"] - 2, f"{d['h26']['dd']['median']}% vs {d['h11a']['dd']['median']}%"),
        (med(n["h26"]) >= med(n["h11a"]), f"{med(n['h26'])}% vs {med(n['h11a'])}%"),
        (med(d["h26_tanpa5"]) >= med(d["h11a_tanpa5"]), f"{med(d['h26_tanpa5'])}% vs {med(d['h11a_tanpa5'])}%"),
        (sens_ok >= 3, f"{sens_ok} dari 4"),
    ]
    hasil["kriteria"] = [{"ok": bool(o), "nilai": v} for o, v in krit]
    hasil["lulus"] = all(o for o, _ in krit)
    for i, (o, v) in enumerate(krit, 1):
        print(f"  [{'LULUS' if o else 'GAGAL'}] {i}. {v}")
    print(f"HASIL AKHIR H26: {'LULUS' if hasil['lulus'] else 'GAGAL'} ({sum(o for o, _ in krit)}/5)")
    dt.simpan_hasil("h26_hasil", hasil)


if __name__ == "__main__":
    utama()
