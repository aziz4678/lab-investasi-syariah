import pandas as pd

from backend.app.services import portofolio_saya as ps
from backend.app.services.reksadana import bersih

SETORAN = 1_000_000.0
FEE_EMAS = 0.0015
ID_EMAS = "EMAS_RP"
NAMA_EMAS = "Indeks emas rupiah (pengganti XGLD)"
LABEL_PENGGANTI = "Pengganti, bukan produk nyata: ETF emas XGLD baru ada sejak Agu 2026, jadi bagian emas memakai indeks emas dalam rupiah."
CATATAN_DATA = "Harga reksa dana memakai NAV akhir bulan (data resmi OJK), jadi setoran dicatat di akhir bulan. Hanya produk yang punya NAV di seluruh periode yang dipakai; yang tidak punya diganti produk sejenis."
AMBANG_REBALANCE = 0.02
CATATAN_ARAH = "setoran diarahkan ke bagian yang tertinggal"
LABEL_PENGGANTI_RD = "pengganti (data produk asli belum ada di periode ini)"
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
                  "bobot": {"lokal": 0.75, "global": 0.25}, "tanpa_rebalance": True},
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
            if w <= 0:
                continue
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
                              "nominal": float(per), "unit": None, "harga": None, "lot": None, "biaya": 0.0, "catatan": LABEL_PENGGANTI_RD if p.get("pengganti_dari") else "", "kaki": kaki, "dibuat": f"{n:06d}"})
    return hasil


def nilai_per_kaki(unit, seri, emas, tanggal):
    nilai = {}
    for (tipe, kunci, kaki), u in unit.items():
        s = emas if tipe == "etf" else seri.get(int(kunci))
        h = ps.harga_terakhir_sampai(s, tanggal)
        if h:
            nilai[kaki] = nilai.get(kaki, 0.0) + u * h
    return nilai


def bobot_bulan(unit, seri, emas, tanggal, bobot, ambang, setoran=SETORAN):
    nilai = nilai_per_kaki(unit, seri, emas, tanggal)
    total = sum(nilai.values())
    if total <= 0:
        return bobot, False
    selisih = {k: nilai.get(k, 0.0) / total - w for k, w in bobot.items()}
    if max(abs(v) for v in selisih.values()) <= ambang:
        return bobot, False
    kurang = {k: max(0.0, w * (total + setoran) - nilai.get(k, 0.0)) for k, w in bobot.items()}
    jumlah = sum(kurang.values())
    if jumlah <= 0:
        return bobot, False
    if jumlah >= setoran:
        porsi = {k: v / jumlah for k, v in kurang.items()}
    else:
        sisa = setoran - jumlah
        porsi = {k: (kurang[k] + sisa * bobot[k]) / setoran for k in bobot}
    return porsi, True


def bangun_transaksi_dinamis(tanggal_list, keranjang, seri, bobot, emas=None, setoran=SETORAN, lunak=(), ambang=AMBANG_REBALANCE, rebalance=True):
    hasil, unit, n = [], {}, 0
    for tgl in tanggal_list:
        w, diarahkan = bobot_bulan(unit, seri, emas, tgl, bobot, ambang, setoran) if rebalance and unit and tgl not in lunak else (bobot, False)
        for t in bangun_transaksi([tgl], keranjang, seri, w, emas, setoran, lunak):
            n += 1
            t = {**t, "_id": f"c{n:03d}", "dibuat": f"{n:06d}"}
            if diarahkan:
                t["catatan"] = (t["catatan"] + "; " if t["catatan"] else "") + CATATAN_ARAH
            hasil.append(t)
            kaki = t["kaki"]
            if t["tipe_produk"] == "etf":
                unit[("etf", t["produk"], kaki)] = unit.get(("etf", t["produk"], kaki), 0.0) + (t["unit"] or 0.0)
            else:
                harga = ps.harga_pertama_setelah(seri.get(int(t["produk"])), tgl, 7)
                if harga and tgl not in lunak:
                    unit[("rd", t["produk"], kaki)] = unit.get(("rd", t["produk"], kaki), 0.0) + (t["nominal"] - t["biaya"]) / harga
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


def pool_pengganti():
    from backend.research import keranjang_pertumbuhan as kp
    lolos, _, _ = kp.calon()
    return [{"id": int(c["id"]), "nama": c["nama"], "kaki": "lokal" if k == "LK" else "global"} for k in ("LK", "GL") for c in lolos[k]]


def penuh(seri_produk, tanggal_list):
    return seri_produk is not None and len(tanggal_list) > 0 and all(ada_di(seri_produk, t) for t in tanggal_list)


def pilih_keranjang(keranjang, pool, seri, tanggal_list):
    hasil, terpakai = [], set()
    for kaki in ("lokal", "global"):
        dasar = [p for p in keranjang if p["kaki"] == kaki]
        ada = [p for p in dasar if penuh(seri.get(p["id"]), tanggal_list)]
        hilang = [p for p in dasar if p not in ada]
        for p in ada:
            hasil.append({**p, "pengganti_dari": None})
            terpakai.add(p["id"])
        for p in pool or []:
            if not hilang:
                break
            if p["kaki"] != kaki or p["id"] in terpakai or not penuh(seri.get(p["id"]), tanggal_list):
                continue
            asal = hilang.pop(0)
            hasil.append({**p, "pengganti_dari": asal["nama"]})
            terpakai.add(p["id"])
    return hasil


def hasil_cepat(spec, mulai, acuan, keranjang, seri, emas, pool=None):
    bobot = spec.get("bobot") or BOBOT[spec["gaya"]]
    tanggal = tanggal_bulanan(mulai, acuan, spec.get("henti", 0))
    dipilih = pilih_keranjang(keranjang, pool, seri, tanggal)
    tx = bangun_transaksi_dinamis(tanggal, dipilih, seri, bobot, emas if spec["gaya"] == "emas" else None, rebalance=not spec.get("tanpa_rebalance"))
    info, harga, kurs = info_harga(tx, dipilih, seri, emas, acuan)
    _, produk = ps.valuasi(tx, info, harga, kurs, acuan)
    return ps.ringkasan_total(produk, tx, acuan), tx


def pilih_datar(keranjang, seri, emas, batas_akhir, pool=None):
    terbaik = None
    for awal in pd.period_range(pd.Period("2018-01", "M"), pd.Period(batas_akhir, "M") - MIN_BULAN_DATAR, freq="M"):
        acuan = (awal + MIN_BULAN_DATAR - 1).to_timestamp(how="end").normalize()
        ring, tx = hasil_cepat({"gaya": "saham"}, awal, acuan, keranjang, seri, emas, pool)
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


def pilih_global_jatuh(keranjang, seri, batas_akhir, pool=None):
    kandidat = []
    for awal in pd.period_range(pd.Period("2018-01", "M"), pd.Period(batas_akhir, "M") - MIN_BULAN_GLOBAL, freq="M"):
        t0 = awal.to_timestamp(how="end").normalize()
        t1 = (awal + MIN_BULAN_GLOBAL).to_timestamp(how="end").normalize()
        dipilih = pilih_keranjang(keranjang, pool, seri, tanggal_bulanan(awal, t1))
        lokal = [seri[p["id"]] for p in dipilih if p["kaki"] == "lokal"]
        glob = [seri[p["id"]] for p in dipilih if p["kaki"] == "global"]
        if not lokal or not glob:
            continue
        rg = [x for x in (return_jendela(s, t0, t1) for s in glob) if x is not None]
        rl = [x for x in (return_jendela(s, t0, t1) for s in lokal) if x is not None]
        if rg and rl:
            kandidat.append((sum(rg) / len(rg), sum(rl) / len(rl), awal, t1))
    layak = [k for k in kandidat if k[1] > -0.10] or kandidat
    return min(layak, key=lambda k: k[0]) if layak else None


def tentukan(kunci, keranjang, seri, emas, pool=None):
    spec = dict(SKENARIO[kunci])
    batas = max(s.index.max() for s in seri.values() if len(s)).to_period("M")
    if spec.get("auto") == "datar":
        pilih = pilih_datar(keranjang, seri, emas, batas, pool)
        if pilih is None:
            raise ValueError("data tidak cukup untuk skenario datar")
        _, awal, acuan = pilih
        spec["mulai"], spec["acuan"] = str(awal), str(acuan.date())
    elif spec.get("auto") == "global_jatuh":
        pilih = pilih_global_jatuh(keranjang, seri, batas, pool)
        if pilih is None:
            raise ValueError("data tidak cukup untuk skenario global jatuh")
        rg, rl, awal, akhir = pilih
        spec["mulai"], spec["acuan"] = str(awal), str(akhir.date())
        spec["catatan_periode"] = f"Saham global {rg * 100:+.1f}% dan saham Indonesia {rl * 100:+.1f}% dalam periode ini (rata-rata produk yang dipakai)."
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
    c.portofolio_saya = [{"nama": porto["nama"], "tanggal_setor": porto["tanggal_setor"], "setoran_rutin": porto["setoran_rutin"], "ada_beli_bulan_ini": False, "pengingat_setoran": True}]
    return ck.cek_setoran_bulan_ini(c)[0]


def siapkan_data(db):
    keranjang = keranjang_saat_ini()
    pool = pool_pengganti()
    ids = sorted({p["id"] for p in [*keranjang, *pool]})
    seri = seri_bulanan(db, ids)
    if not seri:
        raise ValueError("data NAV bulanan belum tersedia")
    return keranjang, pool, seri, seri_emas()


def analisis_contoh(kunci, db=None, data=None):
    from backend.db import koneksi as kdb
    if kunci not in SKENARIO:
        raise KeyError("skenario tidak dikenal")
    db = db if db is not None else kdb.koneksi()
    keranjang, pool, seri, emas = data if data is not None else siapkan_data(db)
    spec = tentukan(kunci, keranjang, seri, emas, pool)
    acuan = pd.Timestamp(spec["acuan"]).normalize()
    bobot = spec.get("bobot") or BOBOT[spec["gaya"]]
    tanggal = tanggal_bulanan(spec["mulai"], acuan, spec.get("henti", 0))
    dipilih = pilih_keranjang(keranjang, pool, seri, tanggal)
    lunak = ()
    if spec.get("tx_akhir"):
        akhir = pd.Timestamp(spec["tx_akhir"]).normalize()
        tanggal = [*tanggal, akhir]
        lunak = (akhir,)
    tx = bangun_transaksi_dinamis(tanggal, dipilih, seri, bobot, emas if spec["gaya"] == "emas" else None, lunak=lunak, rebalance=not spec.get("tanpa_rebalance"))
    if lunak:
        akhir_tx = [t for t in tx if t["tanggal"] == ps.tgl_teks(lunak[0])]
        tx = [t for t in tx if t not in akhir_tx] + [{**akhir_tx[0], "nominal": SETORAN}]
    info, harga, kurs = info_harga(tx, dipilih, seri, emas, acuan)
    target = "pertumbuhan_emas" if spec["gaya"] == "emas" else "pertumbuhan_saham"
    porto = {"_id": PORTO_ID, "nama": f"Contoh: {spec['label']}", "target": target, "tanggal_mulai": ps.tgl_teks(akhir_bulan(spec["mulai"])), "setoran_rutin": SETORAN, "tanggal_setor": 3,
             "pengingat_setoran": bool(spec.get("henti")), "aktif": True}
    hasil = ps.analisis_dari(porto, tx, acuan, db, info, harga, kurs)
    pengganti = {str(p["id"]): p["pengganti_dari"] for p in dipilih if p.get("pengganti_dari")}
    for p in hasil["produk"]:
        p["basi"] = False
        if p["produk"] in pengganti:
            p["pengganti_dari"] = pengganti[p["produk"]]
            p["catatan_pengganti"] = LABEL_PENGGANTI_RD
    catatan = [CATATAN_DATA]
    diarahkan = len({t["tanggal"] for t in tx if CATATAN_ARAH in (t.get("catatan") or "")})
    if diarahkan:
        catatan.append(f"Di {diarahkan} bulan setoran diarahkan penuh ke bagian yang tertinggal (rebalance alami, saat selisih dari target lebih dari {AMBANG_REBALANCE * 100:.0f} poin).")
    for kaki in ("lokal", "global"):
        if bobot.get(kaki) and not any(p["kaki"] == kaki for p in dipilih):
            catatan.append(f"Tidak ada produk bagian {ps.NAMA_KAKI[kaki].lower()} yang punya NAV di seluruh periode; porsi itu dilewati.")
    contoh = {"kunci": kunci, "label": spec["label"], "kalimat": spec["kalimat"], "periode": teks_periode(spec), "acuan": ps.tgl_teks(acuan), "catatan": catatan,
              "pengganti": LABEL_PENGGANTI if spec.get("emas") else None, "catatan_periode": spec.get("catatan_periode"), "pengingat": None,
              "pengganti_rd": [{"nama": p["nama"], "pengganti_dari": p["pengganti_dari"], "label": LABEL_PENGGANTI_RD} for p in dipilih if p.get("pengganti_dari")]}
    if spec.get("henti"):
        contoh["pengingat"] = pengingat_contoh(spec, porto, acuan)
    hasil["contoh"] = contoh
    return bersih(hasil)


def laporan_alokasi(db=None):
    from backend.db import koneksi as kdb
    db = db if db is not None else kdb.koneksi()
    data = siapkan_data(db)
    baris = []
    for kunci in SKENARIO:
        a = analisis_contoh(kunci, db, data)
        kaki = {k["kaki"]: k for k in a["alokasi"]["kaki"]}
        selisih = max((abs(k["selisih_porsi"]) for k in kaki.values() if k["selisih_porsi"] is not None), default=0.0)
        baris.append({"kunci": kunci, "periode": a["contoh"]["periode"], "porsi": {k: round(v["porsi"] * 100, 1) for k, v in kaki.items()},
                      "target": {k: round((v["target"] or 0) * 100, 1) for k, v in kaki.items()}, "selisih_maks_poin": round(selisih * 100, 1),
                      "pengganti": [p["nama"] + " <- " + p["pengganti_dari"] for p in a["contoh"]["pengganti_rd"]]})
    return baris
