import sys
import numpy as np
import pandas as pd
from backend.db import data as dt

K = [0.0, 0.25, 0.5, 1.0]
LABEL = {0.0: "0,4%", 0.25: "0,6%", 0.5: "0,8%", 1.0: "1,2%"}


def ringkas_trade(tr):
    tr = tr.dropna(subset=["kotor", "net"])
    biaya = (tr["kotor"] - tr["net"]).clip(lower=0.4)
    out = {"n": len(tr), "kotor": tr["kotor"].mean(), "biaya_lama": biaya.mean()}
    rng = np.random.default_rng(7)
    for k in K:
        net = tr["kotor"] - (0.4 + k * (biaya - 0.4))
        idx = rng.integers(0, len(net), (2000, len(net)))
        b5 = np.percentile(net.to_numpy()[idx].mean(1), 5)
        t10 = net.drop(net.nlargest(10).index).mean()
        menang, kalah = net[net > 0].sum(), -net[net <= 0].sum()
        pf = menang / kalah if kalah > 0 else np.inf
        out[k] = (net.mean(), pf, b5, t10)
    return out


def cetak(nama, o):
    print(f"{nama:8} n={o['n']:5} kotor={o['kotor']:+.2f} biaya_model={o['biaya_lama']:.2f}")
    for k in K:
        e, pf, b5, t10 = o[k]
        gerbang = e > 0 and b5 > 0 and t10 > 0
        print(f"   biaya {LABEL[k]}: exp {e:+.2f}% PF {pf:.2f} boot5 {b5:+.2f} tanpa10 {t10:+.2f} gerbang {'LOLOS' if gerbang else 'gagal'}")


print("=== H19a-g (trade tersimpan, dev 2010-2019) ===")
for n in "abcdefg":
    tr = dt.baca_hasil(f"trades_H19{n}_dev")
    cetak("H19" + n, ringkas_trade(tr))

print("\n=== H25 (trade tersimpan) ===")
d = dt.baca_hasil("h25_dev")
t = pd.DataFrame({"kotor": d["kotor"], "net": d["bersih"]})
cetak("H25", ringkas_trade(t))

print("\n=== Agregat dari dokumen (rata-rata kotor per trade) ===")
for nama, kotor, n, net_lama in [("H2", 0.40, 396, -0.77), ("H2 y>=3%", 1.10, 100, -0.09), ("H3", 0.87, 1114, -0.45),
                                  ("H4", 2.60, 425, 1.23), ("H5", 0.23, 5249, -1.03), ("H6", 0.47, 388, -0.81),
                                  ("H27", -0.02, 1005, -1.23), ("H28", -1.20, 29, -2.42)]:
    biaya = kotor - net_lama
    print(f"{nama:9} n={n:5} kotor={kotor:+.2f} biaya_model={biaya:.2f} | " +
          " | ".join(f"{LABEL[k]}: {kotor - (0.4 + k * (biaya - 0.4)):+.2f}" for k in K))

print("\n=== Spread nyata (Bid/Offer penutupan, idx_harian) ===")
df = dt.baca("idx_harian")
df = df[["tgl", "StockCode", "Close", "Value", "Bid", "Offer", "BidVolume", "OfferVolume"]]
df = df[df["tgl"] >= "2020-01-01"]
sc_fr = lambda h: np.select([h < 200, h < 500, h < 2000, h < 5000], [1, 2, 5, 10], 25)
for nama, mulai, akhir in [("12 bln terakhir", "2025-11-01", "2026-11-14"), ("2020-2023", "2020-01-01", "2023-12-31")]:
    x = df[(df["tgl"] >= mulai) & (df["tgl"] <= akhir)].copy()
    med_nilai = x.groupby("StockCode")["Value"].median()
    x["likuid"] = x["StockCode"].map(med_nilai) >= 5e9
    ok = (x["Bid"] > 0) & (x["Offer"] > x["Bid"]) & (x["Close"] > 0)
    y = x[ok].copy()
    mid = (y["Bid"] + y["Offer"]) / 2
    y["spread"] = (y["Offer"] - y["Bid"]) / mid * 100
    y["tick"] = sc_fr(y["Close"].to_numpy()) / y["Close"] * 100
    y["spread_tick"] = (y["Offer"] - y["Bid"]) / sc_fr(y["Close"].to_numpy())
    y["tepat1"] = y["spread_tick"] <= 1.001
    print(f"\n{nama}: saham likuid (median nilai >= Rp5 M) {int((med_nilai >= 5e9).sum())}, non-likuid {int((med_nilai < 5e9).sum())}; baris valid {len(y)}/{len(x)}")
    for g, lab in [(True, "likuid"), (False, "non-likuid")]:
        z = y[y["likuid"] == g]
        print(f"  {lab:10} spread median {z['spread'].median():.2f}% (p25 {z['spread'].quantile(.25):.2f}, p75 {z['spread'].quantile(.75):.2f}) | "
              f"1 tick/harga median {z['tick'].median():.2f}% | spread median {z['spread_tick'].median():.2f} tick | spread=1 tick {z['tepat1'].mean() * 100:.0f}% hari | "
              f"setengah spread {z['spread'].median() / 2:.2f}%")
    lik = y[y["likuid"]]
    lik = lik.assign(b=pd.cut(lik["Close"], [0, 200, 500, 2000, 5000, 1e9], labels=["<200", "200-499", "500-1999", "2000-4999", ">=5000"]))
    print("  likuid per harga: " + " | ".join(f"{b}: {g['spread'].median():.2f}% ({g['spread_tick'].median():.1f} tick, n={len(g)})" for b, g in lik.groupby("b", observed=True)))

sys.stdout.flush()
