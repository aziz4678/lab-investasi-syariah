import io
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd
import requests

from backend.db import data as dt
from backend.ingest.impor_browser import cari

NAMA = "keuangan_idx"
NAMA_PDF = "keuangan_idx_pdf"
FOLDER = "keuangan_idx"
CDX = "http://web.archive.org/cdx/search/cdx"
POLA_CDX = ["idx.co.id/Portals/0/StaticData/Publication/Statistic/*", "idx.co.id/media/*", "idx.co.id/Media/*"]
BULAN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "agt": 8, "agu": 8,
         "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}
RE_TGL = re.compile(r"^[A-Za-z]{3}-\d{2}$")
RE_ANGKA = re.compile(r"^\(?-?[\d,]*\.?\d+\)?$")
RE_S = r"\[[^A-Za-z\]]{0,2}S[^A-Za-z\]]{0,2}\]"
RE_S_LONGGAR = r"\[[^\]]{0,2}S"
RE_CID = re.compile(r"^\(cid:(\d+)\)$")
RE_KODE = re.compile(r"^\s*\d+\s*\.?\s*([A-Z][A-Z0-9]{3})\s+(.+?Tbk\.?)(?=\s|$)")
METRIK = ["assets", "liabilities", "equity", "sales", "ebt", "profit_period", "profit_owner", "eps", "bv", "per", "pbv", "der", "roa", "roe", "npm"]
KOL18 = ["assets", "liabilities", "equity", "sales", "ebt", "profit_period", "profit_owner", "saham_juta", "eps", "bv", "per", "pbv", "der", "roa", "roe", "npm", "bobot_per", "bobot_pbv"]
KOL15 = METRIK
KOL17 = [k for k in KOL18 if k != "profit_owner"]
KOL18_LAMA = ["assets", "liabilities", "equity", "sales", "laba_usaha", "profit_period", "saham_juta", "eps", "bv", "per", "pbv", "der", "roa", "roe", "npm", "opm", "bobot_per", "bobot_pbv"]
FORMAT = {18: KOL18, 17: KOL17, 15: KOL15}
KOLOM = ["bulan", "terbit", "sumber", "kode", "nama_emiten", "syariah", "fs_date", "fye"] + METRIK


def log(t):
    print(t, flush=True)


def daftar_wayback():
    baris = []
    for pola in POLA_CDX:
        r = requests.get(CDX, params={"url": pola, "output": "json", "fl": "original,timestamp", "filter": ["statuscode:200", "mimetype:application/pdf"],
                                      "collapse": "urlkey", "limit": 20000}, timeout=180)
        isi = r.json()
        baris += isi[1:] if isi else []
    calon = {}
    for url, ts in baris:
        f = url.split("/")[-1].lower().replace("%20", " ")
        u = url.lower()
        if "weekly" in u or "/wr" in u or re.search(r"lap|corsec|bond|fixed|fi\.pdf", f):
            continue
        m = re.search(r"(jan|feb|mar|apr|may|mei|jun|jul|aug|agt|sep|oct|okt|nov|dec|des)[a-z]*[ _-]*(20\d\d)", f)
        if not m or not ("monthly" in f or "monthly" in u or "statistic" in f):
            continue
        periode = f"{m.group(2)}-{BULAN[m.group(1)]:02d}"
        terbit = re.match(r"(20\d{6})", f)
        isi = {"periode": periode, "url": url, "ts": ts, "terbit": terbit.group(1) if terbit else None, "rev": "rev" in f}
        lama = calon.get(periode)
        if lama is None or (isi["rev"], isi["ts"]) > (lama["rev"], lama["ts"]):
            calon[periode] = isi
    return sorted(calon.values(), key=lambda x: x["periode"])


def unduh(url, ts=None):
    alamat = f"http://web.archive.org/web/{ts}id_/{url}" if ts else url
    for coba in range(1, 6):
        try:
            r = requests.get(alamat, timeout=180)
            if r.ok and r.content[:4] == b"%PDF":
                return r.content
            log(f"  status {r.status_code}, tunggu {30 * coba} dtk (coba {coba}/5)")
        except requests.RequestException as e:
            log(f"  {e.__class__.__name__}, tunggu {30 * coba} dtk (coba {coba}/5)")
        time.sleep(30 * coba)
    return None


def huruf(t):
    m = RE_CID.match(t)
    return chr(int(m.group(1)) + 28) if m else t


def baris_halaman(pg):
    H, W = pg.height, pg.width
    titik = []
    for c in pg.chars:
        tx = huruf(c["text"])
        if c["upright"]:
            titik.append((c["x0"], c["x1"], c["top"], tx, c["size"]))
        elif c["matrix"][1] > 0:
            titik.append((H - c["bottom"], H - c["top"], c["x0"], tx, c["size"]))
        else:
            titik.append((c["top"], c["bottom"], W - c["x1"], tx, c["size"]))
    kelompok = []
    for t in sorted(titik, key=lambda t: t[2]):
        if kelompok and abs(t[2] - kelompok[-1][0]) <= 1.6:
            kelompok[-1][1].append(t)
        else:
            kelompok.append([t[2], [t]])
    hasil = []
    for _, isi in kelompok:
        isi.sort(key=lambda t: t[0])
        kata, kini, mulai, akhir = [], "", None, None
        for u0, u1, _, tx, sz in isi:
            if tx == " " or (akhir is not None and u0 - akhir > 0.22 * sz):
                if kini:
                    kata.append((kini, mulai, akhir))
                kini, mulai = ("", None) if tx == " " else (tx, u0)
            else:
                if not kini:
                    mulai = u0
                kini += tx
            akhir = u1
        if kini:
            kata.append((kini, mulai, akhir))
        hasil.append(kata)
    return hasil


def angka(s):
    s = s.replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    try:
        v = float(s.strip("()"))
    except ValueError:
        return None
    return -v if neg else v


def halaman_keuangan(teks):
    return "Financial Data" in teks or "laicnaniF" in teks or ("ROE" in teks and "PBV" in teks) or ("EOR" in teks and "VBP" in teks)


def bersih_nama(s):
    s = re.sub(r"\[S\]|\(Persero\)|PT\.?|Tbk\.?|[^A-Za-z0-9 ]", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def baris_mentah(pg):
    keluar = []
    for kata in baris_halaman(pg):
        teks = [k[0] for k in kata]
        j = next((k for k, w in enumerate(teks) if RE_TGL.match(w) and w[:3].lower() in BULAN), None)
        if j is None or j == 0:
            continue
        sisa = kata[j + 1:]
        fye = None
        if sisa and sisa[0][0][:3].lower() in BULAN and not RE_TGL.match(sisa[0][0]):
            fye = sisa[0][0]
            sisa = sisa[1:]
        nilai = [(angka(w), (a + b) / 2) for w, a, b in sisa if RE_ANGKA.match(w)]
        keluar.append({"nama": " ".join(teks[:j]), "fs": teks[j], "fye": fye, "nilai": nilai})
    return keluar


def baca_pdf(isi):
    import pdfplumber
    hasil, kode_nama = [], {}
    with pdfplumber.open(io.BytesIO(isi)) as pdf:
        for pg in pdf.pages:
            teks = pg.extract_text() or ""
            if not halaman_keuangan(teks):
                for ln in teks.splitlines():
                    m = RE_KODE.match(ln)
                    if m:
                        kode_nama.setdefault(bersih_nama(m.group(2)), m.group(1))
                continue
            rows = baris_mentah(pg)
            if not rows:
                continue
            hitung = Counter(len(r["nilai"]) for r in rows)
            n = next((m for m, _ in hitung.most_common() if m in FORMAT), None)
            if n is None:
                continue
            kol = KOL18_LAMA if n == 18 and ("OPM" in teks or "MPO" in teks) else FORMAT[n]
            penuh = [r for r in rows if len(r["nilai"]) == len(kol)]
            if len(penuh) < 3:
                continue
            pusat = np.median(np.array([[u for _, u in r["nilai"]] for r in penuh]), axis=0)
            for r in rows:
                isi_baris = dict.fromkeys(kol)
                if len(r["nilai"]) == len(kol):
                    isi_baris.update({k: v for k, (v, _) in zip(kol, r["nilai"])})
                else:
                    pakai = set()
                    for v, u in r["nilai"]:
                        jarak = np.abs(pusat - u)
                        idx = next((i for i in np.argsort(jarak) if i not in pakai), None)
                        if idx is None or jarak[idx] > 12:
                            continue
                        pakai.add(idx)
                        isi_baris[kol[idx]] = v
                hasil.append({"nama_asli": r["nama"], "fs": r["fs"], "fye": r["fye"], **isi_baris})
    df = pd.DataFrame(hasil)
    if df.empty:
        return df
    df["syariah"] = df["nama_asli"].str.contains(RE_S_LONGGAR, regex=True)
    if "profit_owner" not in df or df["profit_owner"].isna().all():
        df["profit_owner"] = df.get("profit_period")
    df["profit_owner"] = df["profit_owner"].fillna(df["profit_period"])
    pola = r"^\s*(?:([A-Z][A-Z0-9]{3})\s+)?\d+\s*\.?\s*(?:([A-Z][A-Z0-9]{3})\s+)?"
    kd = df["nama_asli"].str.extract(pola)
    df["kode"] = kd[1].fillna(kd[0])
    df["nama"] = df["nama_asli"].str.replace(pola, "", regex=True).str.replace(RE_S + r"|\*\)", " ", regex=True).str.strip()
    tanpa = df["kode"].isna()
    df.loc[tanpa, "kode"] = df.loc[tanpa, "nama"].map(lambda s: kode_nama.get(bersih_nama(s)))
    df["fs_date"] = pd.to_datetime(df["fs"], format="%b-%y", errors="coerce") + pd.offsets.MonthEnd(0)
    df["_k"] = df["kode"].fillna("~" + df["nama"].map(bersih_nama))
    return df.drop_duplicates("_k").drop(columns="_k").reset_index(drop=True)


def ke_baku(df, bulan, terbit, sumber):
    out = pd.DataFrame({"bulan": bulan, "terbit": pd.Timestamp(terbit), "sumber": sumber, "kode": df["kode"], "nama_emiten": df["nama"],
                        "syariah": df["syariah"].astype(bool), "fs_date": df["fs_date"], "fye": df["fye"]})
    for k in METRIK:
        out[k] = pd.to_numeric(df[k], errors="coerce") if k in df else np.nan
    for k in ("per", "pbv", "der", "roa", "roe", "npm"):
        out.loc[out[k].abs() > 1e5, k] = np.nan
    return out


def terbit_dari(periode, terbit):
    if terbit:
        return datetime.strptime(terbit, "%Y%m%d")
    return pd.Timestamp(periode + "-01") + pd.offsets.MonthEnd(1) + pd.Timedelta(days=15)


def pdf_tersimpan():
    lama = dt.baca(NAMA_PDF) if dt.ada(NAMA_PDF) else None
    return lama if lama is not None else pd.DataFrame(columns=KOLOM + ["link"])


def simpan_pdf(potong, lama):
    if not potong:
        return lama
    semua = pd.concat([lama] + potong, ignore_index=True)
    semua["_k"] = semua["kode"].fillna("~" + semua["nama_emiten"].map(bersih_nama))
    semua = semua.drop_duplicates(["bulan", "_k"], keep="last").drop(columns="_k").sort_values(["bulan", "nama_emiten"]).reset_index(drop=True)
    dt.tulis(NAMA_PDF, semua)
    return semua


def proses_wayback(sampai="2021-12"):
    lama = pdf_tersimpan()
    sudah = set(lama["bulan"].unique())
    daftar = [x for x in daftar_wayback() if x["periode"] <= sampai and x["periode"] not in sudah]
    log(f"Wayback: {len(daftar)} laporan bulanan baru untuk dibaca (s/d {sampai}, {len(sudah)} bulan sudah ada)")
    potong, laporan = [], []
    for i, x in enumerate(daftar, 1):
        isi = unduh(x["url"], x["ts"])
        if isi is None:
            log(f"  {i}/{len(daftar)} {x['periode']}: gagal diunduh")
            continue
        df = baca_pdf(isi)
        ok = df["kode"].notna() if len(df) else pd.Series(dtype=bool)
        laporan.append({"periode": x["periode"], "baris": int(len(df)), "berkode": int(ok.sum()), "url": x["url"]})
        if len(df):
            baku = ke_baku(df, x["periode"], terbit_dari(x["periode"], x["terbit"]), "pdf")
            baku["link"] = f"https://web.archive.org/web/{x['ts']}/{x['url']}"
            potong.append(baku)
        log(f"  {i}/{len(daftar)} {x['periode']}: {len(df)} baris, {int(ok.sum())} berkode, {int(df['syariah'].sum()) if len(df) else 0} syariah ({len(isi) // 1024} KB)")
        if len(potong) >= 5:
            lama = simpan_pdf(potong, lama)
            potong = []
        time.sleep(15)
    simpan_pdf(potong, lama)
    return laporan


def proses_unduhan():
    lama = pdf_tersimpan()
    potong = []
    for f in cari("idx_statistik_*.pdf"):
        m = re.search(r"(20\d\d)-?(\d\d)", f.name)
        if not m:
            continue
        p = f"{m.group(1)}-{m.group(2)}"
        df = baca_pdf(f.read_bytes())
        ok = df["kode"].notna() if len(df) else pd.Series(dtype=bool)
        if len(df):
            baku = ke_baku(df, p, terbit_dari(p, None), "pdf")
            baku["link"] = f"idx.co.id: {f.name}"
            potong.append(baku)
        log(f"{f.name}: {len(df)} baris, {int(ok.sum())} berkode")
    simpan_pdf(potong, lama)


def impor_api():
    berkas = cari("idx_rasio_*.json")
    if not berkas:
        log("Tidak ada file idx_rasio_*.json di Downloads.")
        return pd.DataFrame(columns=KOLOM)
    potong = []
    for f in berkas:
        for b in json.loads(f.read_text(encoding="utf-8")):
            a = pd.DataFrame(b["data"], columns=b["kolom"])
            df = pd.DataFrame({"kode": a["code"].str.strip().str.upper(), "nama": a["stockName"], "syariah": a["sharia"].eq("S"),
                               "fs_date": pd.to_datetime(a["fsDate"], errors="coerce"), "fye": a["fiscalYearEnd"],
                               "assets": a["assets"], "liabilities": a["liabilities"], "equity": a["equity"], "sales": a["sales"], "ebt": a["ebt"],
                               "profit_period": a["profitPeriod"], "profit_owner": a["profitAttrOwner"], "eps": a["eps"], "bv": a["bookValue"],
                               "per": a["per"], "pbv": a["priceBV"], "der": a["deRatio"], "roa": a["roa"] * 100, "roe": a["roe"] * 100, "npm": a["npm"] * 100})
            potong.append(ke_baku(df, b["bulan"], terbit_dari(b["bulan"], None), "api"))
        dt.simpan_arsip(f"{FOLDER}/api/{f.name}", f.read_bytes(), FOLDER)
        log(f"{f.name} dibaca")
    return pd.concat(potong, ignore_index=True)


def kamus_kode(*tabel):
    import difflib
    pasangan = pd.concat([t[["kode", "nama_emiten"]] for t in tabel], ignore_index=True).dropna()
    pasangan["n"] = pasangan["nama_emiten"].map(bersih_nama)
    pasangan = pasangan[pasangan["n"].str.len() > 2]
    tepat = pasangan.drop_duplicates("n", keep="last").set_index("n")["kode"].to_dict()
    kunci = list(tepat)

    def cari_kode(nama):
        n = bersih_nama(nama)
        if n in tepat:
            return tepat[n]
        mirip = difflib.get_close_matches(n, kunci, n=1, cutoff=0.9)
        return tepat[mirip[0]] if mirip else None
    return cari_kode


def tandai_curiga(df):
    d = df.sort_values(["kode", "bulan"]).copy()
    a = d["assets"].where(d["assets"] > 0)
    med = a.groupby(d["kode"]).transform(lambda x: x.rolling(5, center=True, min_periods=3).median())
    r = a / med
    d["curiga"] = (r > 10) | (r < 0.1)
    return d.sort_values(["bulan", "kode"]).reset_index(drop=True)


def gabung(sampai="2021-12", unduh=True):
    if unduh:
        proses_wayback(sampai)
    proses_unduhan()
    pdf = pdf_tersimpan()
    pdf["syariah"] = pdf["syariah"].astype(bool) | pdf["nama_emiten"].fillna("").str.contains(RE_S_LONGGAR, regex=True)
    pdf["nama_emiten"] = pdf["nama_emiten"].fillna("").str.replace(RE_S, " ", regex=True).str.strip()
    api = impor_api()
    cari_kode = kamus_kode(api, pdf)
    tanpa = pdf["kode"].isna()
    pdf.loc[tanpa, "kode"] = pdf.loc[tanpa, "nama_emiten"].map(cari_kode)
    log(f"Kode dari kamus nama: {int(pdf.loc[tanpa, 'kode'].notna().sum())} dari {int(tanpa.sum())} baris tanpa kode; sisa tanpa kode {int(pdf['kode'].isna().sum())}")
    pdf = pdf[pdf["kode"].notna()]
    api = api[api.groupby("bulan")["kode"].transform("size") >= 300]
    semua = pd.concat([api, pdf.drop(columns=["link"], errors="ignore")], ignore_index=True)
    semua["prioritas"] = semua["sumber"].map({"api": 0, "pdf": 1})
    semua = semua.sort_values(["bulan", "kode", "prioritas"]).drop_duplicates(["bulan", "kode"]).drop(columns="prioritas").reset_index(drop=True)
    semua = tandai_curiga(semua)
    log(f"Ditandai curiga (aset melonjak >10x dari median sekitarnya): {int(semua['curiga'].sum())} baris")
    dt.tulis(NAMA, semua)
    ringkas = semua.groupby(semua["bulan"].str[:4]).agg(bulan=("bulan", "nunique"), emiten=("kode", "nunique"))
    log("Per tahun:\n" + ringkas.to_string())
    log(f"Total {len(semua)} baris, {semua['bulan'].nunique()} bulan, {semua['kode'].nunique()} kode, {semua['bulan'].min()} s/d {semua['bulan'].max()}")
    dt.db().keuangan_idx_info.replace_one({"_id": "ringkas"}, {
        "_id": "ringkas", "diimpor": datetime.now(), "baris": int(len(semua)), "bulan": int(semua["bulan"].nunique()), "kode": int(semua["kode"].nunique()),
        "dari": semua["bulan"].min(), "sampai": semua["bulan"].max(), "api_sampai": api["bulan"].max() if len(api) else None,
        "bulan_pdf": sorted(pdf["bulan"].unique().tolist())}, upsert=True)


def info():
    return dt.db().keuangan_idx_info.find_one({"_id": "ringkas"})


def bulan_berikut_api():
    i = info()
    if not i or not i.get("api_sampai"):
        return "2021-01"
    p = pd.Period(i["api_sampai"], "M") + 1
    return str(p)


def tahun_pdf_kurang():
    i = info() or {}
    ada = set(i.get("bulan_pdf") or [])
    return [y for y in (2020,) if sum(1 for b in ada if b.startswith(str(y))) < 12]


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else "gabung"
    {"gabung": gabung, "gabung_lokal": lambda: gabung(unduh=False), "wayback": proses_wayback, "unduhan": proses_unduhan}[perintah]()
