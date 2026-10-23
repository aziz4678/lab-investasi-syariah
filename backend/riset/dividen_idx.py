import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

ROOT = Path(__file__).resolve().parents[2]
FILE = "idx_dividen_mentah.json"
JENDELA_EX = 7
JENDELA_BAYAR = 60
TOLERANSI_COCOK = 4
LIBUR = pd.offsets.BDay()


def label(ket):
    s = (ket or "").lower()
    m = re.search(r"dividen\s+(tunai|saham)", s)
    jenis = m.group(1) if m else "tunai"
    depan = s[: m.start()] if m else s
    if "cum" in depan:
        return jenis, "cum"
    if re.search(r"\bex\b|ex-", depan):
        return jenis, "ex"
    if "dps" in depan or "recording" in depan or "pencatatan" in depan:
        return jenis, "dps"
    if "bayar" in depan or "pembayaran" in depan or "distribusi" in depan:
        return jenis, "bayar"
    return jenis, "lain:" + depan.replace("tanggal", "").strip()[:40]


def tanggal(x):
    if not x or str(x).startswith("1911") or str(x).startswith("0001"):
        return None
    try:
        return pd.Timestamp(str(x)[:10])
    except ValueError:
        return None


def kelompok(acara):
    hasil = []
    for (kode, jenis), g in acara.groupby(["kode", "jenis"]):
        per = {k: sorted(set(v["tgl"])) for k, v in g.groupby("tahap")}
        pakai = {k: set() for k in per}

        def ambil(tahap, dari, sampai):
            for t in per.get(tahap, []):
                if dari <= t <= sampai and t not in pakai[tahap]:
                    pakai[tahap].add(t)
                    return t
            return None

        for cum in per.get("cum", []):
            pakai["cum"].add(cum)
            ex = ambil("ex", cum, cum + pd.Timedelta(days=JENDELA_EX))
            dps = ambil("dps", cum, cum + pd.Timedelta(days=JENDELA_EX))
            bayar = ambil("bayar", cum, cum + pd.Timedelta(days=JENDELA_BAYAR))
            hasil.append({"kode": kode, "jenis": jenis, "cum": cum, "ex": ex, "dps": dps, "bayar": bayar})
        for ex in per.get("ex", []):
            if ex in pakai["ex"]:
                continue
            pakai["ex"].add(ex)
            dps = ambil("dps", ex, ex + pd.Timedelta(days=JENDELA_EX))
            bayar = ambil("bayar", ex, ex + pd.Timedelta(days=JENDELA_BAYAR))
            hasil.append({"kode": kode, "jenis": jenis, "cum": None, "ex": ex, "dps": dps, "bayar": bayar})
    return hasil


def gabung_profil(kejadian, profil):
    sh_terakhir = {}
    if dt.ada("ksei"):
        k = dt.baca("ksei", kolom=["kode", "tgl", "saham"]).sort_values("tgl")
        sh_terakhir = k.groupby("kode")["saham"].last().to_dict()
    kurs = dt.baca("pasar")["usdidr"].dropna()
    kurs_akhir = float(kurs.iloc[-1]) if len(kurs) else np.nan
    indeks = {(x["kode"], x["cum"]): x for x in kejadian if x["cum"] is not None and x["jenis"] == "tunai"}
    tambah = 0
    for kode, baris in (profil or {}).items():
        for r in baris or []:
            if str(r.get("Jenis", "")).lower() not in ("dt", "tunai", "dividen tunai"):
                continue
            cum = tanggal(r.get("TanggalCum"))
            mu = (r.get("CashDividenTotalMU") or "IDR").strip() or "IDR"
            mu_per = (r.get("CashDividenPerSahamMU") or "IDR").strip() or "IDR"
            total = float(r.get("CashDividenTotal") or 0)
            per = float(r.get("CashDividenPerSaham") or 0)
            if per and mu_per == "USD" and per < 1:
                per *= kurs_akhir
            dari_total = total / sh_terakhir[kode] * (kurs_akhir if mu == "USD" else 1) if total and sh_terakhir.get(kode) else None
            dihitung = not per
            if dari_total and (not per or not 1 / 3 <= per / dari_total <= 3):
                per, dihitung = dari_total, True
            nilai = {"tahun_buku": str(r.get("TahunBuku") or "") or None, "total": total or None, "mata_uang": mu,
                     "per_lembar_idx": round(per, 4) if per else None, "per_lembar_dihitung": dihitung}
            x = indeks.get((kode, cum))
            if x is None:
                x = {"kode": kode, "jenis": "tunai", "cum": cum, "ex": tanggal(r.get("TanggalExRegulerDanNegosiasi")),
                     "dps": tanggal(r.get("TanggalDPS")), "bayar": tanggal(r.get("TanggalPembayaran"))}
                kejadian.append(x)
                indeks[(kode, cum)] = x
                tambah += 1
            for k, t in (("ex", "TanggalExRegulerDanNegosiasi"), ("dps", "TanggalDPS"), ("bayar", "TanggalPembayaran")):
                if x.get(k) is None:
                    x[k] = tanggal(r.get(t))
            x.update(nilai)
    return tambah


def ex_efektif(x):
    if x.get("ex") is not None:
        return x["ex"]
    return x["cum"] + LIBUR if x.get("cum") is not None else None


def cek_yahoo(kejadian):
    from backend.api.emiten import baca_mentah
    from backend.riset import des_ojk
    des = des_ojk.baca()
    kode_des = set(des["kode"])
    tunai = [x for x in kejadian if x["jenis"] == "tunai" and ex_efektif(x) is not None and x["kode"] in kode_des]
    if not tunai:
        return {}
    awal = min(ex_efektif(x) for x in tunai)
    hari_ini = pd.Timestamp.today().normalize()
    per_kode = {}
    for x in tunai:
        per_kode.setdefault(x["kode"], []).append(x)
    n_idx = cocok_idx = n_yh = cocok_yh = 0
    selisih_nilai = []
    hilang_yahoo, hilang_idx = [], []
    for kode, xs in per_kode.items():
        m = baca_mentah(kode)
        if m is None or "dividends" not in m:
            continue
        dv = m["dividends"].fillna(0)
        dv = dv[dv > 0]
        split = m["stock_splits"].fillna(0) if "stock_splits" in m else pd.Series(dtype=float)
        split = split[split > 0]
        akhir_data = m.index.max()
        ex_idx = []
        for x in xs:
            t = ex_efektif(x)
            if t > akhir_data or t > hari_ini:
                continue
            ex_idx.append(t)
            n_idx += 1
            dekat = dv[(dv.index >= t - pd.Timedelta(days=TOLERANSI_COCOK)) & (dv.index <= t + pd.Timedelta(days=TOLERANSI_COCOK))]
            if len(dekat):
                cocok_idx += 1
                x["yahoo_dps"] = round(float(dekat.iloc[0]), 4)
                x["yahoo_tgl"] = dekat.index[0]
                if x.get("per_lembar_idx"):
                    faktor = float(split[split.index > dekat.index[0]].prod()) if len(split) else 1.0
                    selisih_nilai.append(float(dekat.iloc[0]) * faktor / x["per_lembar_idx"] - 1)
            else:
                hilang_yahoo.append(f"{kode} {t:%Y-%m-%d}")
        for t in dv[(dv.index >= awal) & (dv.index <= hari_ini)].index:
            n_yh += 1
            if any(abs((t - e).days) <= TOLERANSI_COCOK for e in ex_idx):
                cocok_yh += 1
            else:
                hilang_idx.append(f"{kode} {t:%Y-%m-%d}")
    lag = [(x["bayar"] - ex_efektif(x)).days for x in tunai if x.get("bayar") is not None]
    sn = np.array(selisih_nilai)
    return {
        "awal": awal.strftime("%Y-%m-%d"), "kejadian_idx": n_idx, "idx_ada_di_yahoo": cocok_idx,
        "persen_idx_di_yahoo": round(cocok_idx / n_idx * 100, 1) if n_idx else None,
        "dividen_yahoo": n_yh, "yahoo_ada_di_idx": cocok_yh, "persen_yahoo_di_idx": round(cocok_yh / n_yh * 100, 1) if n_yh else None,
        "contoh_tidak_di_yahoo": hilang_yahoo[-15:], "contoh_tidak_di_idx": hilang_idx[-15:],
        "nilai_dibandingkan": int(len(sn)), "nilai_cocok_5persen": int((np.abs(sn) <= 0.05).sum()) if len(sn) else 0,
        "jeda_bayar_median": int(np.median(lag)) if lag else None, "jeda_bayar_p90": int(np.percentile(lag, 90)) if lag else None,
    }


def ke_dok(x):
    dok = {k: (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for k, v in x.items()}
    kunci = (x["cum"] or x["ex"]).strftime("%Y%m%d")
    dok["_id"] = f"{x['kode']}_{x['jenis']}_{kunci}"
    return dok


def impor(f):
    isi = json.loads(Path(f).read_text(encoding="utf-8")) if Path(f).exists() else dt.baca_arsip_json(str(f))
    mentah = isi.get("acara") or []
    if not mentah:
        raise SystemExit(f"{Path(f).name}: tidak ada acara dividen, format tidak dikenal")
    baris = []
    for a in mentah:
        t = tanggal(a.get("tgl"))
        if t is None or not a.get("kode"):
            continue
        jenis, tahap = label(a.get("ket"))
        baris.append({"kode": str(a["kode"]).strip().upper(), "jenis": jenis, "tahap": tahap, "tgl": t})
    acara = pd.DataFrame(baris)
    hitung = Counter(acara["tahap"])
    print(f"{len(acara)} acara dividen dari kalender IDX ({isi.get('bulan_awal')} s/d {isi.get('bulan_akhir')})")
    print("  per tahap: " + ", ".join(f"{k} {v}" for k, v in hitung.most_common()))
    if isi.get("gagal"):
        print(f"  PERINGATAN: {len(isi['gagal'])} bulan gagal diambil: {', '.join(isi['gagal'][:12])}")
    kejadian = kelompok(acara[~acara["tahap"].str.startswith("lain")])
    tambah = gabung_profil(kejadian, isi.get("profil"))
    print(f"{len(kejadian)} kejadian dividen ({sum(1 for x in kejadian if x['jenis'] == 'tunai')} tunai), {tambah} tambahan dari profil emiten")
    lengkap = sum(1 for x in kejadian if x["cum"] is not None and x["bayar"] is not None)
    print(f"  dengan cum + tanggal bayar: {lengkap}")
    cek = cek_yahoo(kejadian)
    db = d.koneksi()
    db.dividen_idx.delete_many({})
    db.dividen_idx.insert_many([ke_dok(x) for x in kejadian])
    db.dividen_idx.create_index([("kode", 1), ("ex", 1)])
    db.dividen_idx.create_index("bayar")
    db.dividen_idx_info.replace_one({"_id": "ringkas"}, {"_id": "ringkas", "diimpor": datetime.now(), "file": Path(f).name,
                                                        "bulan_awal": isi.get("bulan_awal"), "bulan_akhir": isi.get("bulan_akhir"),
                                                        "acara": len(acara), "kejadian": len(kejadian), "gagal": isi.get("gagal") or [],
                                                        "cek": cek}, upsert=True)
    if cek:
        print("\nCocokkan dengan Yahoo (saham pernah syariah, sejak", cek["awal"] + "):")
        print(f"  dividen IDX yang ada di Yahoo: {cek['idx_ada_di_yahoo']}/{cek['kejadian_idx']} ({cek['persen_idx_di_yahoo']}%)")
        print(f"  dividen Yahoo yang ada di IDX: {cek['yahoo_ada_di_idx']}/{cek['dividen_yahoo']} ({cek['persen_yahoo_di_idx']}%)")
        if cek["nilai_dibandingkan"]:
            print(f"  nilai per lembar cocok (selisih <= 5%): {cek['nilai_cocok_5persen']}/{cek['nilai_dibandingkan']}")
        print(f"  jeda ex-date ke pembayaran: median {cek['jeda_bayar_median']} hari, 90% <= {cek['jeda_bayar_p90']} hari")
        if cek["contoh_tidak_di_yahoo"]:
            print("  contoh ada di IDX tapi tidak di Yahoo: " + ", ".join(cek["contoh_tidak_di_yahoo"][-8:]))
        if cek["contoh_tidak_di_idx"]:
            print("  contoh ada di Yahoo tapi tidak di IDX: " + ", ".join(cek["contoh_tidak_di_idx"][-8:]))
    lain = {k: v for k, v in hitung.items() if k.startswith("lain")}
    if lain:
        print("  label tidak dikenal (diabaikan): " + ", ".join(f"{k[5:]} ({v})" for k, v in lain.items()))
    print(f"\nSelesai: koleksi dividen_idx berisi {len(kejadian)} kejadian")


if __name__ == "__main__":
    impor(sys.argv[1] if len(sys.argv) > 1 else FILE)
