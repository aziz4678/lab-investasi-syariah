import json
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from backend.db import data as dt
from backend.db import koneksi as d

BUANG = re.compile(r"\b(REKSA ?DANA|RD|PT|TBK)\b")
KATA_SYARIAH = re.compile(r"SYARIAH|SHARIA|SYARI'?AH|SUKUK|AMANAH|ISLAMIC|MUDHARABAH|HAJJ", re.I)


ABAIKAN = {"SYARIAH", "SHARIA", "SYARI", "AH", "RDS", "RDPT", "RDSPT", "BERBASIS", "EFEK", "INDEKS", "DAN", "FUND", "DANA", "MI", "AM", "KELAS",
           "PASAR", "UANG", "TERPROTEKSI", "PENYERTAAN", "TERBATAS"}


def token(s):
    return {t for t in norm(s).replace("BNI AM ", "BNIAM ").split() if t not in ABAIKAN}


def kelas(s):
    m = re.search(r"KELAS ([A-Z0-9]+)", norm(s))
    return m.group(1) if m else None


def cocokkan(df, db):
    nav = pd.DataFrame(list(db.rd_nav.find({}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    nav["tgl"] = pd.to_datetime(nav["tgl"])
    nav = nav.sort_values("tgl")
    akhir = df["tgl"].max()
    aktif = df[df["tgl"] >= akhir - pd.DateOffset(months=3)]
    calon = {k: (token(g["produk"].iloc[-1]), kelas(g["produk"].iloc[-1]), g.set_index("tgl")["nav"]) for k, g in aktif.groupby("kunci")}
    seri_ojk = {k: g.set_index("tgl")["nav"] for k, g in df.groupby("kunci")}
    skor = []
    for p in db.rd_produk.find({}, {"nama": 1}):
        tp, kp = token(p["nama"]), kelas(p["nama"])
        n = nav[nav["fund"] == p["_id"]].set_index("tgl")["nav"]
        if not tp:
            continue
        for k, (tk, kk, _) in calon.items():
            if not tk:
                continue
            mirip = len(tp & tk) / len(tp | tk)
            if mirip < 0.5 or (kp and kk and kp != kk):
                continue
            so = seri_ojk[k]
            titik = []
            for t, v in so.items():
                if n.empty or t < n.index[0] or t > n.index[-1]:
                    continue
                w = n[(n.index <= t) & (n.index > t - pd.Timedelta(days=5))]
                if len(w):
                    titik.append(abs(v / w.iloc[-1] - 1) <= 0.01)
            if len(titik) >= 3:
                setuju = sum(titik) / len(titik)
                if setuju >= 0.8:
                    skor.append((setuju, mirip, p["_id"], k))
            elif mirip == 1 and (kp == kk):
                skor.append((0.5, mirip, p["_id"], k))
    skor.sort(reverse=True)
    hasil, dipakai = {}, set()
    for setuju, mirip, fund, k in skor:
        if fund in dipakai or k in hasil:
            continue
        hasil[k] = fund
        dipakai.add(fund)
    return hasil


def sambung_pendahulu(df, peta):
    seri = {k: g.set_index("tgl")["nav"].sort_index() for k, g in df.groupby("kunci")}
    calon = []
    for k, fund in peta.items():
        lama = re.sub(r" KELAS [A-Z0-9]+(?=\|)", "", k)
        if lama == k or lama not in seri or lama in peta:
            continue
        a, b = seri[lama], seri[k]
        mulai = b.index[0]
        sebelum = a[a.index < mulai]
        if sebelum.empty or (mulai - sebelum.index[-1]).days > 62:
            continue
        loncat = abs(b.iloc[0] / sebelum.iloc[-1] - 1)
        if loncat <= 0.03:
            calon.append((loncat, lama, fund, mulai))
    calon.sort(key=lambda x: x[0])
    hasil = {}
    for loncat, lama, fund, mulai in calon:
        hasil.setdefault(lama, (fund, mulai))
    return hasil


def norm(s):
    s = (s or "").upper().replace("&", " DAN ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = BUANG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def salin(cari):
    baru = []
    terbaru = {}
    for f in cari("ojk_nab_*.json"):
        nama = re.sub(r" \(\d+\)(?=\.json$)", "", f.name)
        terbaru.setdefault(nama, f)
    for nama, f in terbaru.items():
        if dt.waktu_arsip(nama) >= f.stat().st_mtime:
            continue
        try:
            isi = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"LEWATI {f.name}: bukan JSON utuh")
            continue
        if not isinstance(isi, dict) or "bulan" not in isi:
            print(f"LEWATI {f.name}: format tidak dikenal")
            continue
        dt.simpan_arsip(nama, f.read_bytes(), "ojk_nab")
        baru.append(f"{nama} ({sum(len(v) for v in isi['bulan'].values())} baris)")
    print("File baru disimpan ke arsip MongoDB:" if baru else "Tidak ada file ojk_nab_*.json baru di Downloads / folder proyek.")
    for x in baru:
        print("  " + x)


def baca_semua():
    baris = []
    gagal = []
    for nama in dt.daftar_arsip(folder="ojk_nab", awalan="ojk_nab_"):
        isi = dt.baca_arsip_json(nama)
        th = int(isi["tahun"])
        for bl, rows in isi["bulan"].items():
            tgl = (pd.Timestamp(year=th, month=int(bl), day=1) + pd.offsets.MonthEnd(0)).to_pydatetime()
            for mi, bk, produk, tipe, denom, nab, unit in rows:
                baris.append((produk, mi, bk, tipe, denom, tgl, nab, unit))
        gagal += [f"{th}-{b}" for b, c in (isi.get("catatan") or {}).items() if c == "gagal"]
    df = pd.DataFrame(baris, columns=["produk", "mi", "bk", "tipe", "denominasi", "tgl", "nab", "unit"])
    return df, gagal


def bangun():
    df, gagal = baca_semua()
    if df.empty:
        raise SystemExit("Belum ada data OJK. Jalankan script ojk_nab_browser.js lalu impor.")
    df["nama_norm"] = df["produk"].map(norm)
    df["kunci"] = df["nama_norm"] + "|" + df["bk"].map(norm)
    df = df.groupby(["kunci", "tgl"], as_index=False).agg(nama_norm=("nama_norm", "first"), produk=("produk", "first"), mi=("mi", "first"), bk=("bk", "first"), tipe=("tipe", "first"),
                                                         denominasi=("denominasi", "first"), nab=("nab", "sum"), unit=("unit", "sum"))
    df["nav"] = df["nab"] / df["unit"]
    kurs = dt.baca("pasar")["usdidr"].dropna().sort_index()
    usd = df["denominasi"].str.upper().eq("USD")
    if usd.any():
        k = kurs.reindex(pd.DatetimeIndex(df.loc[usd, "tgl"]), method="ffill").to_numpy()
        df.loc[usd, "nav"] = df.loc[usd, "nav"].to_numpy() / k
    db = d.koneksi()
    peta = cocokkan(df, db)
    df["fund"] = df["kunci"].map(peta)
    sambung = sambung_pendahulu(df, peta)
    for lama, (fund, mulai) in sambung.items():
        df.loc[(df["kunci"] == lama) & (df["tgl"] < mulai), "fund"] = fund
    df["syariah"] = df["fund"].notna() | df["produk"].str.contains(KATA_SYARIAH)
    db.rd_ojk.delete_many({})
    dok = [{"_id": f"{r.kunci}_{r.tgl:%Y%m}", "kunci": r.kunci, "produk": r.produk, "mi": r.mi, "bk": r.bk, "tipe": r.tipe, "denominasi": r.denominasi,
            "tgl": r.tgl.to_pydatetime() if hasattr(r.tgl, "to_pydatetime") else r.tgl, "nab": float(r.nab), "unit": float(r.unit), "nav": float(r.nav),
            "fund": int(r.fund) if pd.notna(r.fund) else None, "syariah": bool(r.syariah)} for r in df.itertuples()]
    for i in range(0, len(dok), 5000):
        db.rd_ojk.insert_many(dok[i:i + 5000])
    db.rd_ojk.create_index([("kunci", 1), ("tgl", 1)])
    db.rd_ojk.create_index("fund")

    bulan = df["tgl"].nunique()
    produk = df["kunci"].nunique()
    sy = df[df["syariah"]]
    cocok = df[df["fund"].notna()]["fund"].nunique()
    print(f"\n{len(df)} baris, {bulan} bulan ({df['tgl'].min():%Y-%m} s/d {df['tgl'].max():%Y-%m}), {produk} produk")
    print(f"  syariah (cocok katalog atau nama mengandung syariah/sukuk/sharia): {sy['kunci'].nunique()} produk")
    print(f"  cocok dengan katalog Pasardana: {cocok} dari {db.rd_produk.count_documents({})} reksa dana syariah")
    print(f"  riwayat sebelum pemecahan kelas disambung: {len(sambung)} produk")
    if gagal:
        print(f"  PERINGATAN bulan gagal diambil: {', '.join(gagal)}")
    nav = pd.DataFrame(list(db.rd_nav.find({}, {"_id": 0, "fund": 1, "tgl": 1, "nav": 1})))
    if not nav.empty:
        nav["tgl"] = pd.to_datetime(nav["tgl"])
        banding = []
        for r in df[df["fund"].notna()].itertuples():
            s = nav[(nav["fund"] == r.fund) & (nav["tgl"] <= pd.Timestamp(r.tgl)) & (nav["tgl"] > pd.Timestamp(r.tgl) - pd.Timedelta(days=5))]
            if len(s):
                banding.append(r.nav / s.sort_values("tgl")["nav"].iloc[-1] - 1)
        if banding:
            b = np.abs(np.array(banding))
            print(f"  cek silang NAV OJK vs Pasardana ({len(b)} titik akhir bulan): selisih <= 0,5% di {(b <= 0.005).mean() * 100:.0f}%, median selisih {np.median(b) * 100:.2f}%")
    db.rd_info.update_one({"_id": "ringkas"}, {"$set": {"ojk": {"diimpor": datetime.now(), "baris": len(df), "bulan": int(bulan), "produk": int(produk),
                                                                 "syariah": int(sy["kunci"].nunique()), "cocok": int(cocok),
                                                                 "dari": df["tgl"].min().strftime("%Y-%m"), "sampai": df["tgl"].max().strftime("%Y-%m")}}}, upsert=True)


def impor():
    from backend.ingest.impor_browser import cari
    salin(cari)
    bangun()


if __name__ == "__main__":
    impor() if len(sys.argv) < 2 or sys.argv[1] == "impor" else bangun()
