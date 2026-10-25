from functools import lru_cache

import numpy as np
import pandas as pd

from backend.app.services.emiten import baca_mentah
from backend.db import data as dt
from backend.db import koneksi as d
from backend.ingest import des_ojk

R_DDM = 0.11
G_DDM_MAKS = 0.05
PAYOUT_DDM = 40
MOS_MURAH = 20
MOS_AGAK = 5
MOS_MAHAL = -15
TAHUN_BAND = 5
BULAN_MIN = 24
ROE_MIN = 12
DER_MAKS = 1.0
NILAI_MIN = 1e9
SIKLIKAL = {"Energy", "Basic Materials"}
KEUANGAN = {"Financial Services"}
PROPERTI = {"Real Estate"}
ALIRAN = {"laba": "laba_lalu", "pendapatan": "pendapatan_lalu", "arus_kas_operasi": "arus_kas_operasi_lalu", "laba_kotor": "laba_kotor_lalu"}
NAMA_PERIODE = {"TW1": "TW1", "TW2": "TW2", "TW3": "TW3", "AUDIT": "Tahunan"}


def fmt(v, n=0, tanda=False):
    t = f"{v:{'+' if tanda else ''},.{n}f}"
    return t.replace(",", "_").replace(".", ",").replace("_", ".")


def angka(v, n=2):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, n) if np.isfinite(v) else None


@lru_cache(maxsize=2)
def _ksei(mtime):
    df = dt.baca("ksei", kolom=["kode", "tgl", "saham"])
    return df.sort_values("tgl")


@lru_cache(maxsize=2)
def _kurs(mtime):
    return dt.baca("pasar")["usdidr"].dropna()


def saham(kode):
    if not dt.ada("ksei"):
        return pd.Series(dtype=float)
    k = _ksei(dt.versi("ksei"))
    return k[k["kode"] == kode].set_index("tgl")["saham"]


@lru_cache(maxsize=2)
def _konvergensi(mtime):
    return dt.baca_hasil("konvergensi_ringkas")


def konvergensi(mos, harga, wajar, t):
    ver = dt.versi_hasil("konvergensi_ringkas")
    if not ver or mos is None or mos < MOS_MURAH or not wajar:
        return None
    k = _konvergensi(ver)
    gm = "20-35" if mos < 35 else "35-50" if mos < 50 else ">50"
    perlu = (wajar / harga - 1) * 100
    gp = "25-50" if perlu < 50 else "50-100" if perlu < 100 else ">100"
    ih = dt.baca("pasar")["ihsg"].dropna()
    ih = ih[ih.index <= t]
    naik = bool(ih.iloc[-1] > ih.tail(200).mean()) if len(ih) >= 200 else None
    return {
        "periode": k["periode"], "jumlah": k["semua"]["n"], "grup_mos": gm, "mos": k["mos"].get(gm), "semua": k["semua"], "pembanding": k["pembanding"],
        "perlu": round(perlu, 1), "grup_perlu": gp, "perlu_data": k["perlu"].get(gp),
        "ihsg_naik": naik, "ihsg_data": k["ihsg"]["naik" if naik else "turun"] if naik is not None else None, "ihsg_lain": k["ihsg"]["turun" if naik else "naik"] if naik is not None else None,
        "periode_kejadian": k["periode_kejadian"],
    }


def split_dari(m):
    if m is None or "stock_splits" not in m:
        return pd.Series(dtype=float)
    x = m["stock_splits"].fillna(0)
    return x[x > 0]


def saham_pada(sh, t, split):
    x = sh[sh.index <= t]
    if x.empty:
        return np.nan
    return float(x.iloc[-1]) * float(split[split.index > x.index[-1]].prod()) if len(split) else float(x.iloc[-1])


def kurs():
    return _kurs(dt.versi("pasar"))


def laporan(kode):
    df = pd.DataFrame(list(d.koneksi().fundamental.find({"kode": kode, "ada_angka": True}, {"_id": 0})))
    if df.empty:
        return df
    df = df[df["tgl_publikasi"].notna()].copy()
    df["tgl_publikasi"] = pd.to_datetime(df["tgl_publikasi"])
    for c in ["laba", "pendapatan", "arus_kas_operasi", "laba_kotor", *ALIRAN.values(), "ekuitas", "ekuitas_total", "aset", "liabilitas",
              "kas", "aset_lancar", "liabilitas_lancar"]:
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df else np.nan
    audit = df[df["periode"] == "AUDIT"].set_index("tahun")
    for x, lalu in ALIRAN.items():
        if x not in df:
            df[x] = np.nan
        if lalu not in df:
            df[lalu] = np.nan
        prev = audit[x].reindex(df["tahun"] - 1).to_numpy() if x in audit else np.nan
        df[f"{x}_ttm"] = np.where(df["periode"] == "AUDIT", df[x], df[x] + prev - df[lalu])
    kunci = df.set_index(["tahun", "periode"])
    for x in ALIRAN:
        for n in (1, 3):
            idx = list(zip(df["tahun"] - n, df["periode"]))
            df[f"{x}_ttm_{n}"] = kunci[f"{x}_ttm"].reindex(idx).to_numpy() if not kunci.index.duplicated().any() else np.nan
    return df.sort_values("tgl_publikasi").reset_index(drop=True)


def pada(lap, t):
    x = lap[lap["tgl_publikasi"] <= t]
    return x.iloc[-1] if len(x) else None


def nilai_kurs(r, t):
    if (r.get("unit") or "IDR") != "USD":
        return 1.0
    k = kurs()
    k = k[k.index <= t]
    return float(k.iloc[-1]) if len(k) else np.nan


def riwayat(lap, harga, sh, split=None):
    if lap.empty or harga.empty or sh.empty:
        return pd.DataFrame()
    akhir = harga.index.max()
    bln = harga[harga.index >= akhir - pd.DateOffset(years=TAHUN_BAND)].resample("ME").last().dropna()
    baris = []
    for t, p in bln.items():
        r = pada(lap, t)
        n = saham_pada(sh, t, split if split is not None else pd.Series(dtype=float))
        if r is None or not np.isfinite(n):
            continue
        fx = nilai_kurs(r, t)
        eps = r["laba_ttm"] * fx / n
        bv = r["ekuitas"] * fx / n
        baris.append({"tgl": t, "harga": p, "per": p / eps if eps > 0 else np.nan, "pbv": p / bv if bv > 0 else np.nan})
    return pd.DataFrame(baris).set_index("tgl") if baris else pd.DataFrame()


def band(s, kini):
    s = s.dropna()
    if len(s) < BULAN_MIN or kini is None or not np.isfinite(kini):
        return None
    m, sd = float(s.mean()), float(s.std())
    return {"rata": angka(m), "median": angka(s.median()), "sd": angka(sd), "bawah": angka(m - sd), "atas": angka(m + sd),
            "persentil": angka((s < kini).mean() * 100, 0), "z": angka((kini - m) / sd if sd > 0 else 0), "bulan": len(s)}


def cagr(a, b, tahun):
    if a is None or b is None or not (np.isfinite(a) and np.isfinite(b)) or a <= 0 or b <= 0:
        return None
    return ((a / b) ** (1 / tahun) - 1) * 100


def tumbuh(a, b):
    if not (np.isfinite(a) and np.isfinite(b)) or b == 0:
        return None
    return (a / abs(b) - (1 if b > 0 else -1)) * 100


def sektor_dari(kode):
    i = d.koneksi().info_saham.find_one({"ticker": f"{kode}.JK"}, {"_id": 0, "sector": 1, "industry": 1}) or {}
    return i.get("sector"), i.get("industry")


def snapshot(kode):
    m = baca_mentah(kode)
    lap = laporan(kode)
    sh = saham(kode)
    if m is None or lap.empty or sh.empty:
        return None
    t = m.index.max()
    r = pada(lap, t)
    if r is None:
        return None
    p = float(m["close"].iloc[-1])
    fx = nilai_kurs(r, t)
    n = saham_pada(sh, t, split_dari(m))
    eps, bv = r["laba_ttm"] * fx / n, r["ekuitas"] * fx / n
    return {"per": p / eps if eps > 0 else np.nan, "pbv": p / bv if bv > 0 else np.nan,
            "roe": r["laba_ttm"] / r["ekuitas"] * 100 if r["ekuitas"] > 0 else np.nan}


@lru_cache(maxsize=64)
def median_grup(kolom, nilai, hari):
    if not nilai:
        return None
    syariah = des_ojk.syariah_pada(des_ojk.baca(), pd.Timestamp(hari))
    kode = [x["ticker"][:-3] for x in d.koneksi().info_saham.find({kolom: nilai}, {"ticker": 1})]
    data = [s for s in (snapshot(k) for k in kode if k in syariah) if s]
    if len(data) < 4:
        return None
    df = pd.DataFrame(data)
    return {"per": angka(df["per"][df["per"] > 0].median()), "pbv": angka(df["pbv"][df["pbv"] > 0].median()),
            "roe": angka(df["roe"].median(), 1), "jumlah": len(df), "grup": nilai, "jenis": "industri" if kolom == "industry" else "sektor"}


def median_sektor(sektor, industri, hari):
    return median_grup("industry", industri, hari) or median_grup("sector", sektor, hari)


def hitung(kode):
    kode = kode.upper()
    m = baca_mentah(kode)
    lap = laporan(kode)
    sh = saham(kode)
    if m is None:
        return {"ada": False, "alasan": "Data harga tidak ada."}
    if lap.empty:
        return {"ada": False, "alasan": "Belum ada laporan keuangan untuk saham ini."}
    if sh.empty:
        return {"ada": False, "alasan": "Jumlah saham beredar (KSEI) tidak ada untuk saham ini."}
    t = m.index.max()
    r = pada(lap, t)
    if r is None:
        return {"ada": False, "alasan": "Belum ada laporan yang terbit."}
    harga = float(m["close"].iloc[-1])
    fx = nilai_kurs(r, t)
    split = split_dari(m)
    n = saham_pada(sh, t, split)
    sektor, industri = sektor_dari(kode)
    bank = sektor in KEUANGAN or (np.isnan(r.get("pendapatan", np.nan)) and np.isnan(r.get("aset_lancar", np.nan)))
    siklikal = sektor in SIKLIKAL

    laba, ekuitas = r["laba_ttm"], r["ekuitas"]
    eps = laba * fx / n
    bvps = ekuitas * fx / n
    mcap = harga * n
    per = harga / eps if eps > 0 else None
    pbv = harga / bvps if bvps > 0 else None
    ps = mcap / (r["pendapatan_ttm"] * fx) if np.isfinite(r["pendapatan_ttm"]) and r["pendapatan_ttm"] > 0 else None
    pcfo = mcap / (r["arus_kas_operasi_ttm"] * fx) if np.isfinite(r["arus_kas_operasi_ttm"]) and r["arus_kas_operasi_ttm"] > 0 else None

    div = m["dividends"].fillna(0) if "dividends" in m else pd.Series(0.0, index=m.index)
    dps = float(div[div.index > t - pd.Timedelta(days=365)].sum())
    tahun_div = [y for y in range(t.year - 3, t.year) if div[div.index.year == y].sum() > 0]
    dy = dps / harga * 100 if dps > 0 else 0.0
    payout = dps / eps * 100 if eps > 0 and dps > 0 else None

    g_laba1 = tumbuh(laba, r["laba_ttm_1"])
    g_laba3 = cagr(laba, r["laba_ttm_3"], 3)
    g_pend1 = tumbuh(r["pendapatan_ttm"], r["pendapatan_ttm_1"])
    g_pend3 = cagr(r["pendapatan_ttm"], r["pendapatan_ttm_3"], 3)
    g_peg = g_laba3 if g_laba3 is not None else g_laba1
    peg = per / g_peg if per and g_peg and g_peg > 0 else None

    roe = laba / ekuitas * 100 if ekuitas > 0 else None
    roa = laba / r["aset"] * 100 if r["aset"] > 0 else None
    der = r["liabilitas"] / r["ekuitas_total"] if r["ekuitas_total"] > 0 else None
    npm = laba / r["pendapatan_ttm"] * 100 if np.isfinite(r["pendapatan_ttm"]) and r["pendapatan_ttm"] > 0 else None
    npm_lalu = r["laba_ttm_1"] / r["pendapatan_ttm_1"] * 100 if np.isfinite(r["pendapatan_ttm_1"]) and r["pendapatan_ttm_1"] > 0 else None
    gpm = r["laba_kotor_ttm"] / r["pendapatan_ttm"] * 100 if np.isfinite(r["laba_kotor_ttm"]) and np.isfinite(r["pendapatan_ttm"]) and r["pendapatan_ttm"] > 0 else None
    cr = r["aset_lancar"] / r["liabilitas_lancar"] if np.isfinite(r.get("aset_lancar", np.nan)) and r.get("liabilitas_lancar", 0) > 0 else None
    cfo = r["arus_kas_operasi_ttm"]
    audit = lap[lap["periode"] == "AUDIT"].sort_values("tahun").tail(3)
    roe_tahun = [{"tahun": int(a.tahun), "roe": angka(a.laba / a.ekuitas * 100, 1)} for a in audit.itertuples() if a.ekuitas > 0]

    rw = riwayat(lap, m["close"], sh, split)
    b_per = band(rw["per"], per) if not rw.empty else None
    b_pbv = band(rw["pbv"], pbv) if not rw.empty else None
    peer = median_sektor(sektor, industri, t.strftime("%Y-%m-%d"))

    metode = []
    if eps > 0 and b_per:
        metode.append({"nama": "PER historis", "nilai": eps * b_per["median"], "rumus": f"EPS TTM Rp{fmt(eps, 0)} × median PER {TAHUN_BAND} th {fmt(b_per['median'], 1)}x",
                       "dipakai": not siklikal and not bank, "catatan": "Tidak dipakai: laba sektor ini ikut siklus harga komoditas" if siklikal else "Tidak dipakai: bank dinilai dengan PBV" if bank else None})
    if bvps > 0 and b_pbv:
        metode.append({"nama": "PBV historis", "nilai": bvps * b_pbv["median"], "rumus": f"BVPS Rp{fmt(bvps, 0)} × median PBV {TAHUN_BAND} th {fmt(b_pbv['median'], 2)}x", "dipakai": True, "catatan": None})
    if eps > 0 and bvps > 0:
        metode.append({"nama": "Graham number", "nilai": (22.5 * eps * bvps) ** 0.5, "rumus": f"√(22,5 × EPS {fmt(eps, 0)} × BVPS {fmt(bvps, 0)})", "dipakai": not bank,
                       "catatan": "Tidak dipakai: rumus Graham tidak cocok untuk bank" if bank else None})
    if peer and peer.get("per") and eps > 0:
        metode.append({"nama": f"PER {peer['jenis']}", "nilai": eps * peer["per"], "rumus": f"EPS TTM Rp{fmt(eps, 0)} × median PER {peer['jumlah']} saham syariah {peer['jenis']} {peer['grup']} {fmt(peer['per'], 1)}x",
                       "dipakai": not siklikal and not bank, "catatan": "Tidak dipakai: laba sektor ini ikut siklus harga komoditas" if siklikal else "Tidak dipakai: bank dinilai dengan PBV" if bank else None})
    if peer and peer.get("pbv") and bvps > 0:
        metode.append({"nama": f"PBV {peer['jenis']}", "nilai": bvps * peer["pbv"], "rumus": f"BVPS Rp{fmt(bvps, 0)} × median PBV {peer['jenis']} {peer['grup']} {fmt(peer['pbv'], 2)}x", "dipakai": True, "catatan": None})
    if len(tahun_div) == 3 and dps > 0:
        g = min(max((g_laba3 or 0) / 100, 0), G_DDM_MAKS)
        metode.append({"nama": "DDM (dividen)", "nilai": dps * (1 + g) / (R_DDM - g),
                       "rumus": f"Dividen Rp{fmt(dps, 0)} × (1+{fmt(g * 100, 1)}%) / ({fmt(R_DDM * 100, 0)}% − {fmt(g * 100, 1)}%)", "dipakai": bool(payout and payout >= PAYOUT_DDM),
                       "catatan": f"Asumsi imbal hasil diminta {fmt(R_DDM * 100, 0)}%/th, pertumbuhan dividen maks {fmt(G_DDM_MAKS * 100, 0)}%"
                                  + ("" if payout and payout >= PAYOUT_DDM else f". Tidak dipakai: payout {fmt(payout or 0, 0)}% < {PAYOUT_DDM}%, sebagian besar laba ditahan")})
    for x in metode:
        x["nilai"] = angka(x["nilai"], 0)
        x["mos"] = angka((x["nilai"] - harga) / x["nilai"] * 100, 1) if x["nilai"] else None
    dipakai = [x["nilai"] for x in metode if x["dipakai"] and x["nilai"]]
    wajar = float(np.median(dipakai)) if dipakai else None
    mos = (wajar - harga) / wajar * 100 if wajar else None
    if laba <= 0:
        vonis = ("rugi", "Tidak bisa dinilai", "Perusahaan rugi 12 bulan terakhir; PER dan Graham tidak berlaku.")
    elif mos is None:
        vonis = ("kurang", "Data kurang", "Riwayat valuasi kurang dari 2 tahun.")
    elif mos >= MOS_MURAH:
        vonis = ("murah", "Undervalue", f"Harga {fmt(mos, 0)}% di bawah nilai wajar (margin of safety ≥ {MOS_MURAH}%).")
    elif mos >= MOS_AGAK:
        vonis = ("agak", "Sedikit di bawah wajar", f"Harga {fmt(mos, 0)}% di bawah nilai wajar, belum mencapai margin of safety {MOS_MURAH}%.")
    elif mos >= MOS_MAHAL:
        vonis = ("wajar", "Wajar", "Harga di sekitar nilai wajar.")
    else:
        vonis = ("mahal", "Overvalue", f"Harga {fmt(-mos, 0)}% di atas nilai wajar.")

    nilai_tx = float((m["close"] * m["volume"]).tail(20).mean())
    ma200 = float(m["close"].tail(200).mean()) if len(m) >= 200 else None
    tinggi52 = float(m["close"].tail(250).max())
    rendah52 = float(m["close"].tail(250).min())
    des = des_ojk.baca()
    syariah = kode in des_ojk.syariah_pada(des, t)

    def cek(label, ok, nilai, syarat, berlaku=True):
        return {"label": label, "ok": None if not berlaku or ok is None else bool(ok), "nilai": nilai, "syarat": syarat}

    kualitas = [
        cek("ROE konsisten", all(x["roe"] is not None and x["roe"] > ROE_MIN for x in roe_tahun) if len(roe_tahun) == 3 else None,
            " · ".join(f"{x['tahun']}: {x['roe']}%" for x in roe_tahun) or "–", f"> {ROE_MIN}% 3 tahun terakhir"),
        cek("Utang", der is not None and der < DER_MAKS if der is not None else None, f"DER {fmt(der, 2)}x" if der is not None else "–", f"< {DER_MAKS:g}x (non-bank)", not bank),
        cek("Kualitas laba", cfo > 0 and cfo >= laba if np.isfinite(cfo) else None, f"arus kas operasi {fmt(cfo / laba, 1)}× laba" if np.isfinite(cfo) and laba > 0 else "–", "positif dan ≥ laba bersih"),
        cek("Pertumbuhan laba", g_laba3 > 0 if g_laba3 is not None else (g_laba1 > 0 if g_laba1 is not None else None),
            f"{fmt(g_laba3, 1, True)}%/th (3 th)" if g_laba3 is not None else f"{fmt(g_laba1, 1, True)}% (1 th)" if g_laba1 is not None else "–", "> 0"),
        cek("Margin laba", npm >= npm_lalu if npm is not None and npm_lalu is not None else None,
            f"{fmt(npm, 1)}% (setahun lalu {fmt(npm_lalu, 1)}%)" if npm is not None and npm_lalu is not None else "–", "stabil atau naik", not bank),
        cek("Likuiditas jangka pendek", cr > 1 if cr is not None else None, f"current ratio {fmt(cr, 2)}x" if cr is not None else "–", "> 1x (non-bank)", not bank),
        cek("Likuid di bursa", nilai_tx >= NILAI_MIN, f"Rp{fmt(nilai_tx / 1e9, 1)} M/hari", "≥ Rp1 M/hari"),
    ]
    berlaku = [k for k in kualitas if k["ok"] is not None]
    skor = sum(k["ok"] for k in berlaku)

    alasan, risiko = [], []
    if b_pbv and b_pbv["z"] is not None:
        posisi = "di bawah" if b_pbv["z"] < -1 else "di atas" if b_pbv["z"] > 1 else "di dalam"
        alasan.append(f"PBV sekarang {fmt(pbv, 2)}x vs rata-rata {TAHUN_BAND} tahun {fmt(b_pbv['rata'], 2)}x ({posisi} band ±1 SD, lebih murah dari {fmt(100 - b_pbv['persentil'], 0)}% riwayatnya).")
    if per and per > 50:
        risiko.append(f"PER {fmt(per, 0)}x sangat tinggi karena laba tipis; PER tidak berarti di sini.")
    if roe is not None and roe > 60:
        risiko.append(f"ROE {fmt(roe, 0)}% sangat tinggi: biasanya karena ekuitas kecil (dividen besar/buyback) atau laba sekali (one-off). Cek laporan.")
    if b_per and per:
        alasan.append(f"PER sekarang {fmt(per, 1)}x vs median {TAHUN_BAND} tahun {fmt(b_per['median'], 1)}x.")
    if peer and per and peer["per"]:
        alasan.append(f"Dibanding {peer['jumlah']} saham syariah {peer['jenis']} {peer['grup']}: PER {fmt(per, 1)}x vs median {fmt(peer['per'], 1)}x, PBV {fmt(pbv, 2)}x vs {fmt(peer['pbv'], 2)}x.")
    if b_pbv and b_pbv["z"] is not None and b_pbv["z"] < -1 and peer and peer.get("pbv") and pbv and pbv > peer["pbv"]:
        risiko.append(f"Murah dibanding riwayatnya sendiri, tapi PBV {fmt(pbv, 2)}x masih di atas median {peer['jenis']} {fmt(peer['pbv'], 2)}x. Rata-rata lama bisa terdongkrak masa euforia.")
    if peg is not None:
        alasan.append(f"PEG {fmt(peg, 2)} ({'< 1, murah relatif ke pertumbuhan laba' if peg < 1 else '≥ 1, harga sudah memperhitungkan pertumbuhan'}).")
    if dy > 0:
        alasan.append(f"Dividend yield {fmt(dy, 1)}% (dividen 12 bulan Rp{fmt(dps, 0)}/saham{f', payout {fmt(payout, 0)}%' if payout else ''}).")
    if g_laba1 is not None and g_laba1 < 0:
        risiko.append(f"Laba 12 bulan terakhir turun {fmt(abs(g_laba1), 0)}% dibanding setahun lalu. Murah bisa karena bisnisnya memburuk (value trap).")
    if np.isfinite(cfo) and cfo <= 0:
        risiko.append("Arus kas operasi negatif: laba belum menjadi uang tunai.")
    if der is not None and not bank and der > 2:
        risiko.append(f"Utang tinggi (DER {fmt(der, 1)}x).")
    if siklikal:
        risiko.append("Sektor komoditas: laba ikut harga komoditas. PER rendah saat laba puncak sering menipu; perhatikan posisi siklus.")
        if g_laba1 is not None and g_laba1 > 50:
            risiko.append("Laba melonjak >50% setahun di sektor siklikal: kemungkinan sedang di puncak siklus.")
    if bank:
        risiko.append("Bank/keuangan: penilaian utama PBV + ROE; DER dan current ratio tidak relevan.")
    if sektor in PROPERTI:
        risiko.append("Properti: idealnya dinilai dengan diskon ke RNAV (nilai aset bersih revaluasi), data itu tidak tersedia di sini.")
    if ma200 and harga < ma200:
        risiko.append(f"Harga di bawah rata-rata 200 hari (Rp{fmt(ma200, 0)}): tren masih turun, bisa makin murah dulu.")
    if harga < tinggi52 * 0.6:
        risiko.append(f"Harga {fmt((1 - harga / tinggi52) * 100, 0)}% di bawah tertinggi 52 minggu. Cari tahu penyebab turunnya: sementara (sentimen) atau struktural.")
    if r["tahun"] < t.year - 1 or (t - r["tgl_publikasi"]).days > 200:
        risiko.append(f"Laporan terakhir sudah lama ({NAMA_PERIODE.get(r['periode'], r['periode'])} {r['tahun']}).")
    if (r.get("unit") or "IDR") == "USD":
        risiko.append(f"Laporan dalam USD, dikonversi kurs Rp{fmt(fx, 0)}. Nilai wajar ikut naik-turun dengan kurs.")

    tren_ok = ma200 is not None and harga >= ma200
    if not syariah:
        sikap = ("hindari", "Di luar batasan", "Saham ini tidak masuk DES terbaru; proyek ini hanya saham syariah.")
    elif vonis[0] in ("rugi", "mahal") or (berlaku and skor <= len(berlaku) / 2):
        sikap = ("hindari", "Hindari dulu", "Valuasi tidak menarik atau kualitas bisnis lemah.")
    elif vonis[0] == "murah" and skor >= len(berlaku) - 1 and tren_ok:
        sikap = ("layak", "Layak dipertimbangkan", "Murah, kualitas bagus, dan tren harga tidak sedang turun.")
    elif vonis[0] in ("murah", "agak") and skor >= len(berlaku) - 2:
        sikap = ("pantau", "Pantau", "Cukup menarik, tapi ada syarat yang belum terpenuhi (tren harga atau kualitas). Tunggu konfirmasi.")
    else:
        sikap = ("pantau", "Pantau", "Belum cukup murah untuk margin of safety yang aman.")

    area = wajar * (1 - MOS_MURAH / 100) if wajar else None
    lk = d.koneksi().lapkeu.find_one({"kode": kode}, sort=[("tgl_publikasi", -1)])
    tgl_lk = f" (laporan terakhir terbit {lk['tgl_publikasi']:%d %b %Y})" if lk else ""
    rencana = None
    if wajar and laba > 0:
        rencana = {
            "area_beli": angka(area, 0), "target": angka(wajar, 0), "potensi": angka((wajar / harga - 1) * 100, 1),
            "harga_di_area": harga <= area,
            "langkah": [
                f"Area beli: ≤ Rp{fmt(area, 0)} (nilai wajar dikurangi margin of safety {MOS_MURAH}%). Harga sekarang Rp{fmt(harga, 0)} "
                + ("sudah di area ini." if harga <= area else f"masih {fmt((harga / area - 1) * 100, 0)}% di atasnya."),
                "Bagi pembelian 2-3 kali supaya tidak membeli semua di satu harga, terutama kalau tren masih turun.",
                "Jangan anggap nilai wajar sebagai target pasti: lihat bagian 'Seberapa sering sampai nilai wajar' di atas untuk peluang dan lamanya secara historis.",
                f"Target: nilai wajar Rp{fmt(wajar, 0)} ({fmt((wajar / harga - 1) * 100, 0, True)}% dari harga sekarang). Jual sebagian/semua saat tercapai, lalu hitung ulang.",
                "Keluar lebih awal kalau tesis rusak: laba TTM turun 2 laporan berturut-turut, ROE < 10%, arus kas operasi negatif, atau saham keluar DES.",
                f"Tinjau ulang setiap laporan kuartal terbit{tgl_lk}.",
                "Ukuran posisi maksimal 10% modal per saham.",
            ],
        }

    hist = [{"tgl": i.strftime("%Y-%m"), "per": angka(x.per), "pbv": angka(x.pbv)} for i, x in rw.iterrows()] if not rw.empty else []
    return {
        "ada": True, "kode": kode, "tgl": t.strftime("%Y-%m-%d"), "harga": harga, "sektor": sektor, "industri": industri, "bank": bool(bank), "siklikal": siklikal,
        "laporan": f"{NAMA_PERIODE.get(r['periode'], r['periode'])} {r['tahun']}", "tgl_laporan": r["tgl_publikasi"].strftime("%Y-%m-%d"), "unit": r.get("unit") or "IDR",
        "kurs": angka(fx, 0), "saham": n, "syariah": syariah,
        "rasio": {"per": angka(per), "pbv": angka(pbv), "ps": angka(ps), "pcfo": angka(pcfo), "peg": angka(peg), "dy": angka(dy), "payout": angka(payout, 0),
                  "ey": angka(eps / harga * 100 if eps > 0 else None), "eps": angka(eps, 1), "bvps": angka(bvps, 0), "dps": angka(dps, 0),
                  "roe": angka(roe, 1), "roa": angka(roa, 1), "der": angka(der), "npm": angka(npm, 1), "gpm": angka(gpm, 1), "cr": angka(cr),
                  "g_laba1": angka(g_laba1, 1), "g_laba3": angka(g_laba3, 1), "g_pend1": angka(g_pend1, 1), "g_pend3": angka(g_pend3, 1),
                  "mcap": angka(mcap, 0)},
        "band": {"per": b_per, "pbv": b_pbv}, "sektor_median": peer, "riwayat": hist,
        "metode": metode, "wajar": angka(wajar, 0), "rentang": [angka(min(dipakai), 0), angka(max(dipakai), 0)] if dipakai else None, "mos": angka(mos, 1),
        "vonis": {"kode": vonis[0], "label": vonis[1], "ket": vonis[2]},
        "kualitas": kualitas, "skor": skor, "skor_maks": len(berlaku),
        "tren": {"ma200": angka(ma200, 0), "di_atas_ma200": tren_ok, "tinggi52": angka(tinggi52, 0), "rendah52": angka(rendah52, 0), "nilai_tx": angka(nilai_tx, 0)},
        "konvergensi": konvergensi(mos, harga, wajar, t),
        "alasan": alasan, "risiko": risiko, "sikap": {"kode": sikap[0], "label": sikap[1], "ket": sikap[2]}, "rencana": rencana,
        "tidak_tersedia": ["EV/EBITDA (butuh utang berbunga dan penyusutan)", "P/FCF dan DCF (butuh belanja modal/capex)", "RNAV untuk properti"],
    }
