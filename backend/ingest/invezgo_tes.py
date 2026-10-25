import json
import os
import sys

import pandas as pd
import requests

from backend.db import data as dt

BASIS = "https://api.invezgo.com"


def panggil(sesi, path, **param):
    r = sesi.get(BASIS + path, params=param, timeout=60)
    nama = (path.strip("/").replace("/", "_") + "_" + "_".join(f"{k}{v}" for k, v in param.items()))[:150]
    try:
        isi = r.json()
    except ValueError:
        isi = {"teks": r.text[:500]}
    dt.simpan_arsip(f"invezgo_{nama}.json", json.dumps(isi), "invezgo")
    if r.status_code != 200:
        print(f"  {r.status_code} {path} -> {isi.get('message') if isinstance(isi, dict) else isi}")
        return None
    return isi


def ringkas_inventory(isi, label):
    if not isi:
        return
    harga = pd.DataFrame(isi.get("price") or [])
    broker = isi.get("broker") or []
    if harga.empty:
        print(f"  {label}: harga kosong, broker {len(broker)}")
        return
    hari_broker = sorted({d["date"] for b in broker for d in b["data"]})
    print(f"  {label}: harga {len(harga)} hari ({harga['date'].min()} s/d {harga['date'].max()}) | "
          f"{len(broker)} broker | hari broker {len(hari_broker)} ({hari_broker[0] if hari_broker else '-'} s/d {hari_broker[-1] if hari_broker else '-'})")
    if broker:
        b = broker[0]
        nilai = [d["value"] for d in b["data"]][:6]
        print(f"    contoh {b['broker']} ({b['name']}): 6 nilai pertama {nilai}")


def utama():
    kunci = os.environ.get("INVEZGO_KEY")
    if not kunci:
        print("set dulu API key: di PowerShell jalankan  $env:INVEZGO_KEY=\"isi_key\"  lalu jalankan script ini lagi")
        sys.exit(1)
    sesi = requests.Session()
    sesi.headers["Authorization"] = f"Bearer {kunci}"

    print("1. riwayat terlama broker inventory (BBRI, investor all, nilai, reguler):")
    for dari, ke in [("2016-01-01", "2016-01-31"), ("2018-01-01", "2018-01-31"), ("2020-01-01", "2020-01-31")]:
        ringkas_inventory(panggil(sesi, "/analysis/inventory-chart/stock/BBRI", **{"from": dari, "to": ke},
                                  scope="val", investor="all", market="RG", limit=50), f"{dari[:7]}")

    print("2. rentang panjang dalam satu request (BBRI 2023 setahun penuh):")
    ringkas_inventory(panggil(sesi, "/analysis/inventory-chart/stock/BBRI", **{"from": "2023-01-01", "to": "2023-12-31"},
                              scope="val", investor="all", market="RG", limit=50), "2023")

    print("3. arti nilai inventory (harian atau kumulatif): bandingkan dengan summary 2 hari:")
    for tgl in ["2023-03-01", "2023-03-02"]:
        s = panggil(sesi, "/analysis/summary/stock/BBRI", **{"from": tgl, "to": tgl}, investor="all", market="RG")
        if s:
            top = sorted(s, key=lambda x: -abs(float(x["net_value"])))[:3]
            print(f"  {tgl}: " + ", ".join(f"{x['code']} net {float(x['net_value']) / 1e9:.1f} M" for x in top))

    print("4. laporan keuangan kuartalan (BBRI, laba rugi, 40 kuartal):")
    lk = panggil(sesi, "/analysis/financial-statement/BBRI", statement="IS", type="Q", limit=40)
    if lk and lk.get("columns"):
        kol = [c["label"] for c in lk["columns"]]
        print(f"  {len(kol)} kuartal: {kol[-1]} s/d {kol[0]} | {len(lk.get('rows') or [])} baris akun")

    print(f"\nrespons mentah tersimpan di arsip MongoDB (folder invezgo, 8 request terpakai)")


if __name__ == "__main__":
    utama()
