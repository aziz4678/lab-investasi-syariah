import pandas as pd

from backend.app.services import portofolio_saya as ps
from backend.app.services.reksadana import bersih

SETORAN = 1_000_000.0
FEE_EMAS = 0.0015
ID_EMAS = "EMAS_RP"
NAMA_EMAS = "Indeks emas rupiah (pengganti XGLD)"
LABEL_PENGGANTI = "Pengganti, bukan produk nyata: ETF emas XGLD baru ada sejak Agu 2026, jadi bagian emas memakai indeks emas dalam rupiah."
CATATAN_DATA = "Harga reksa dana memakai NAV akhir bulan (data resmi OJK), jadi setoran dicatat di akhir bulan. Produk yang belum ada saat itu dilewati dan porsinya dibagi ke produk lain di bagian yang sama."
BOBOT = {"saham": {"lokal": 0.5, "global": 0.5}, "emas": {"lokal": 0.4, "global": 0.4, "emas": 0.2}}
PORTO_ID = "contoh"
APLIKASI_RD = "Bibit"
APLIKASI_ETF = "Stockbit"
MIN_BULAN_GLOBAL = 12
MIN_BULAN_DATAR = 24

SKENARIO = {
    "bagus": {"label": "Bagus", "kalimat": "Mulai Apr 2020, dilihat Des 2021: masuk sesudah crash, lalu pasar naik.", "mulai": "2020-04", "acuan": "2021-12-31", "gaya": "saham"},
    "jelek": {"label": "Jelek", "kalimat": "Mulai Jan 2018, dilihat Mar 2020: masuk, lalu kena crash.", "mulai": "2018-01", "acuan": "2020-03-31", "gaya": "saham"},
    "datar": {"label": "Datar", "kalimat": "Dua tahun yang hasilnya mendekati nol; periodenya dipilih otomatis dari data.", "auto": "datar", "gaya": "saham"},
    "global_jatuh": {"label": "Saham global jatuh", "kalimat": "Satu tahun saat saham global turun tajam, sementara saham Indonesia biasa saja; dipilih otomatis dari data.", "auto": "global_jatuh", "gaya": "saham"},
    "melenceng": {"label": "Alokasi melenceng", "kalimat": "Setoran tidak dibagi rata (75% Indonesia, 25% global), dilihat Des 2021: saran menyeimbangkan muncul.", "mulai": "2020-04", "acuan": "2021-12-31", "gaya": "saham",
                  "bobot": {"lokal": 0.75, "global": 0.25}},
    "lupa_setor": {"label": "Lupa setor", "kalimat": "Tiga bulan terakhir tanpa setoran, dilihat Des 2021: pengingat setoran muncul.", "mulai": "2020-04", "acuan": "2021-12-31", "gaya": "saham", "henti": 3},
    "menunggu_nav": {"label": "Menunggu NAV", "kalimat": "Transaksi terakhir 15 Des 2021 belum punya NAV: jumlah unit menunggu.", "mulai": "2020-04", "acuan": "2021-12-15", "gaya": "saham", "tx_akhir": "2021-12-15"},
    "baru_mulai": {"label": "Baru mulai", "kalimat": "Baru dua bulan: hasil per tahun (XIRR) belum cukup data.", "mulai": "2021-11", "acuan": "2022-01-14", "gaya": "saham"},
    "bagus_emas": {"label": "Bagus, dengan emas", "kalimat": "Sama seperti 'Bagus' tapi campuran saham + emas 40/40/20.", "mulai": "2020-04", "acuan": "2021-12-31", "gaya": "emas", "emas": True},
    "jelek_emas": {"label": "Jelek, dengan emas", "kalimat": "Sama seperti 'Jelek' tapi campuran saham + emas 40/40/20: emas menahan saat crash.", "mulai": "2018-01", "acuan": "2020-03-31", "gaya": "emas", "emas": True},
}


def daftar_skenario():
    return [{"kunci": k, "label": v["label"], "kalimat": v["kalimat"], "emas": bool(v.get("emas"))} for k, v in SKENARIO.items()]


def akhir_bulan(periode):
    return pd.Period(periode, "M").to_timestamp(how="end").normalize()


def tanggal_bulanan(mulai, acuan, henti=0):
    acuan = pd.Timestamp(acuan).normalize()
    semua = [p.to_timestamp(how="end").normalize() for p in pd.period_range(pd.Period(mulai, "M"), pd.Period(acuan, "M"), freq="M")]
    semua = [t for t in semua if t <= acuan]
    return semua[: len(semua) - henti] if henti else semua


def seri_bulanan(db, ids):
    df = pd.DataFrame(list(db.rd_ojk.find({"fund": {"$in": [*ids, *[str(i) for i in ids]]}}, {"_id": 0, "fund": 1, "tgl": 1, "nab": 1, "unit": 1})))
    if df.empty:
        return {}
    df = df[df["unit"] > 0].copy()
    df["nav"] = df["nab"] / df["unit"]
    df["bulan"] = pd.to_datetime(df["tgl"]).dt.to_period("M")
    hasil = {}
    for f, g in df.groupby("fund"):
        s = g.sort_values("nab").groupby("bulan")["nav"].last().sort_index()
        s.index = [p.to_timestamp(how="end").normalize() for p in s.index]
        hasil[int(f)] = s.astype(float)
    return hasil


def seri_emas():
    return ps._seri_proxy().get("emas", pd.Series(dtype=float))


def keranjang_saat_ini():
    from backend.app.services import belanja as bl
    b = bl.pertumbuhan(None, SETORAN, 0, "saham")
    return [{"id": int(p["id"]), "nama": p["nama"], "kaki": p["kaki"]} for g in b.get("grup", []) for p in g["produk"] if p.get("tipe") == "rd"]


def ada_di(seri, tanggal):
    return seri is not None and tanggal in seri.index and pd.notna(seri.loc[tanggal])


def sudah_ada(seri, tanggal, lunak):
    if seri is None or not len(seri):
        return False
    return seri.index.min() <= tanggal if tanggal in lunak else ada_di(seri, tanggal)


def bangun_transaksi(tanggal_list, keranjang, seri, bobot, emas=None, setoran=SETORAN, lunak=()):
    hasil = []
    n = 0
    for tgl in tanggal_list:
        for kaki, w in bobot.items():
            if kaki == "emas":
                if emas is None:
                    continue
                harga = ps.harga_pertama_setelah(emas, tgl, 7)
                if not harga:
                    continue
                nominal = round(setoran * w)
                biaya = round(nominal * FEE_EMAS)
                n += 1
                hasil.append({"_id": f"c{n:03d}", "portofolio_id": PORTO_ID, "tanggal": ps.tgl_teks(tgl), "jenis": "beli", "tipe_produk": "etf", "produk": ID_EMAS, "nama": NAMA_EMAS, "aplikasi": APLIKASI_ETF,
                              "nominal": float(nominal), "unit": (nominal - biaya) / harga, "harga": None, "lot": None, "biaya": float(biaya), "catatan": "pengganti XGLD", "kaki": "emas", "dibuat": f"{n:06d}"})
                continue
            ada = [p for p in keranjang if p["kaki"] == kaki and sudah_ada(seri.get(p["id"]), tgl, lunak)]
            if not ada:
                continue
            per = round(setoran * w / len(ada))
            for p in ada:
                n += 1
                hasil.append({"_id": f"c{n:03d}", "portofolio_id": PORTO_ID, "tanggal": ps.tgl_teks(tgl), "jenis": "beli", "tipe_produk": "rd", "produk": str(p["id"]), "nama": p["nama"], "aplikasi": APLIKASI_RD,
                              "nominal": float(per), "unit": None, "harga": None, "lot": None, "biaya": 0.0, "catatan": "", "kaki": kaki, "dibuat": f"{n:06d}"})
    return hasil


def potong(seri, acuan):
    acuan = pd.Timestamp(acuan)
    return {k: v[v.index <= acuan] for k, v in seri.items()}


def info_harga(transaksi, keranjang, seri, emas, acuan):
    info, harga = {}, {}
    nama = {str(p["id"]): p["nama"] for p in keranjang}
    for t in transaksi:
        kunci = (t["tipe_produk"], t["produk"])
        if kunci in info:
            continue
        if t["tipe_produk"] == "rd":
            info[kunci] = {"mata_uang": "IDR", "nama": nama.get(t["produk"])}
            harga[kunci] = potong(seri, acuan).get(int(t["produk"]), pd.Series(dtype=float))
        else:
            info[kunci] = {"emas": True, "mata_uang": "IDR"}
            harga[kunci] = emas[emas.index <= pd.Timestamp(acuan)] if emas is not None else pd.Series(dtype=float)
    return info, harga, pd.Series(dtype=float)


def hasil_cepat(spec, mulai, acuan, keranjang, seri, emas):
    bobot = spec.get("bobot") or BOBOT[spec["gaya"]]
    tanggal = tanggal_bulanan(mulai, acuan, spec.get("henti", 0))
    tx = bangun_transaksi(tanggal, keranjang, seri, bobot, emas if spec["gaya"] == "emas" else None)
    info, harga, kurs = info_harga(tx, keranjang, seri, emas, acuan)
    _, produk = ps.valuasi(tx, info, harga, kurs, acuan)
    return ps.ringkasan_total(produk, tx, acuan), tx


def pilih_datar(keranjang, seri, emas, batas_akhir):
    terbaik = None
    for awal in pd.period_range(pd.Period("2018-01", "M"), pd.Period(batas_akhir, "M") - MIN_BULAN_DATAR, freq="M"):
        acuan = (awal + MIN_BULAN_DATAR - 1).to_timestamp(how="end").normalize()
        ring, tx = hasil_cepat({"gaya": "saham"}, awal, acuan, keranjang, seri, emas)
        if ring["untung_persen"] is None:
            continue
        jarak = abs(ring["untung_persen"])
        if terbaik is None or jarak < terbaik[0]:
            terbaik = (jarak, awal, acuan)
    return terbaik


def return_jendela(s, awal, akhir):
    a = ps.harga_pertama_setelah(s, awal, 7)
    b = ps.harga_terakhir_sampai(s, akhir)
    return None if not a or not b else b / a - 1


def pilih_global_jatuh(keranjang, seri, batas_akhir):
    lokal = [seri[p["id"]] for p in keranjang if p["kaki"] == "lokal" and p["id"] in seri]
    glob = [seri[p["id"]] for p in keranjang if p["kaki"] == "global" and p["id"] in seri]
    if not lokal or not glob:
        return None
    kandidat = []
    for awal in pd.period_range(pd.Period("2018-01", "M"), pd.Period(batas_akhir, "M") - MIN_BULAN_GLOBAL, freq="M"):
        t0 = awal.to_timestamp(how="end").normalize()
        t1 = (awal + MIN_BULAN_GLOBAL).to_timestamp(how="end").normalize()
        rg = [return_jendela(s, t0, t1) for s in glob]
        rl = [return_jendela(s, t0, t1) for s in lokal]
        rg, rl = [x for x in rg if x is not None], [x for x in rl if x is not None]
        if rg and rl:
            kandidat.append((sum(rg) / len(rg), sum(rl) / len(rl), awal, t1))
    layak = [k for k in kandidat if k[1] > -0.10] or kandidat
    return min(layak, key=lambda k: k[0]) if layak else None


def tentukan(kunci, keranjang, seri, emas):
    spec = dict(SKENARIO[kunci])
    batas = max(s.index.max() for s in seri.values() if len(s)).to_period("M")
    if spec.get("auto") == "datar":
        pilih = pilih_datar(keranjang, seri, emas, batas)
        if pilih is None:
            raise ValueError("data tidak cukup untuk skenario datar")
        _, awal, acuan = pilih
        spec["mulai"], spec["acuan"] = str(awal), str(acuan.date())
    elif spec.get("auto") == "global_jatuh":
        pilih = pilih_global_jatuh(keranjang, seri, batas)
        if pilih is None:
            raise ValueError("data tidak cukup untuk skenario global jatuh")
        rg, rl, awal, akhir = pilih
        spec["mulai"], spec["acuan"] = str(awal), str(akhir.date())
        spec["catatan_periode"] = f"Saham global {rg * 100:+.1f}% dan saham Indonesia {rl * 100:+.1f}% dalam periode ini (rata-rata produk di keranjang)."
    return spec


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def bulan_teks(t):
    t = pd.Timestamp(t)
    return f"{BULAN[t.month - 1]} {t.year}"


def teks_periode(spec):
    return f"{bulan_teks(akhir_bulan(spec['mulai']))} – {bulan_teks(spec['acuan'])}"


def pengingat_contoh(spec, porto, acuan):
    from backend.paper import cek_kesehatan as ck
    c = ck.Ctx(acuan, kalender=[pd.Timestamp(acuan)])
    c.portofolio_saya = [{"nama": porto["nama"], "tanggal_setor": porto["tanggal_setor"], "setoran_rutin": porto["setoran_rutin"], "ada_beli_bulan_ini": False}]
    return ck.cek_setoran_bulan_ini(c)[0]


def analisis_contoh(kunci, db=None):
    from backend.db import koneksi as kdb
    if kunci not in SKENARIO:
        raise KeyError("skenario tidak dikenal")
    db = db if db is not None else kdb.koneksi()
    keranjang = keranjang_saat_ini()
    seri = seri_bulanan(db, [p["id"] for p in keranjang])
    if not seri:
        raise ValueError("data NAV bulanan belum tersedia")
    emas = seri_emas()
    spec = tentukan(kunci, keranjang, seri, emas)
    acuan = pd.Timestamp(spec["acuan"]).normalize()
    bobot = spec.get("bobot") or BOBOT[spec["gaya"]]
    tanggal = tanggal_bulanan(spec["mulai"], acuan, spec.get("henti", 0))
    lunak = ()
    if spec.get("tx_akhir"):
        akhir = pd.Timestamp(spec["tx_akhir"]).normalize()
        tanggal = [*tanggal, akhir]
        lunak = (akhir,)
    tx = bangun_transaksi(tanggal, keranjang, seri, bobot, emas if spec["gaya"] == "emas" else None, lunak=lunak)
    if lunak:
        akhir_tx = [t for t in tx if t["tanggal"] == ps.tgl_teks(lunak[0])]
        tx = [t for t in tx if t not in akhir_tx] + [{**akhir_tx[0], "nominal": SETORAN}]
    info, harga, kurs = info_harga(tx, keranjang, seri, emas, acuan)
    target = "pertumbuhan_emas" if spec["gaya"] == "emas" else "pertumbuhan_saham"
    porto = {"_id": PORTO_ID, "nama": f"Contoh: {spec['label']}", "target": target, "tanggal_mulai": ps.tgl_teks(akhir_bulan(spec["mulai"])), "setoran_rutin": SETORAN, "tanggal_setor": 3, "aktif": True}
    hasil = ps.analisis_dari(porto, tx, acuan, db, info, harga, kurs)
    for p in hasil["produk"]:
        p["basi"] = False
    contoh = {"kunci": kunci, "label": spec["label"], "kalimat": spec["kalimat"], "periode": teks_periode(spec), "acuan": ps.tgl_teks(acuan), "catatan": [CATATAN_DATA],
              "pengganti": LABEL_PENGGANTI if spec.get("emas") else None, "catatan_periode": spec.get("catatan_periode"), "pengingat": None}
    if spec.get("henti"):
        contoh["pengingat"] = pengingat_contoh(spec, porto, acuan)
    hasil["contoh"] = contoh
    return bersih(hasil)
