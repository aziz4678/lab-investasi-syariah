import math
from datetime import date

import numpy as np
import pandas as pd

from backend.app.services.reksadana import bersih

APLIKASI_RD = ("bibit", "ajaib", "makmur")
APLIKASI_ETF = ("stockbit", "ajaib")
APLIKASI_SEMUA = ("bibit", "ajaib", "makmur", "stockbit")
NAMA_APLIKASI = {"bibit": "Bibit", "ajaib": "Ajaib", "makmur": "Makmur", "stockbit": "Stockbit"}
KATA_ETF = "ETF dibeli lewat akun saham (Stockbit/Ajaib); Bibit & Makmur tidak menjual ETF"
FEE_ETF = {"stockbit": 0.0015, "ajaib": None}
LOT = 100
BATAS_PREMIUM = 0.02
HARI_BASI = 3
GLOBAL_DISETUJUI = (2233,)
BAGIAN = {"saham": {"lokal": 0.5, "global": 0.5, "emas": 0.0}, "emas": {"lokal": 0.4, "global": 0.4, "emas": 0.2}}
MODAL_KECIL = 50_000_000
FATWA = {"nomor": "No. 163/DSN-MUI/VIII/2025", "tentang": "ETF Syariah Emas",
         "sumber": ["https://pasardana.id/news/2026/8/10/5-etf-emas-resmi-melantai-ojk-sebut-jadi-quick-win-pasar-bullion",
                    "https://www.cnbcindonesia.com/market/20260812091054-17-758491/cara-beli-etf-emas-lengkap-dengan-tickernya"]}
CATATAN_AKUN_SYARIAH = "Pakai akun saham syariah (RDN syariah) supaya seluruh transaksi sesuai syariah."
LABEL_PREMIUM = "selisih harga vs nilai emas (data kemarin)"


def normal_aplikasi(apps):
    if apps is None:
        return list(APLIKASI_SEMUA)
    if isinstance(apps, str):
        apps = [x for x in apps.split(",") if x]
    urut = [a for a in APLIKASI_SEMUA if a in {str(x).strip().lower() for x in apps}]
    return urut


def aplikasi_rd(apps):
    return [a for a in apps if a in APLIKASI_RD]


def tersedia(produk, apps):
    return [p["kode"] for p in produk.get("platform") or [] if p["kode"] in apps]


def aplikasi_angka(apps):
    rd = aplikasi_rd(apps)
    return rd[0] if len(rd) == 1 else "semua"


def pilih_produk(dasar, pool, apps, jumlah):
    rd = aplikasi_rd(apps)
    cocok = [c for c in dasar if tersedia(c, rd)]
    hilang = [c for c in dasar if not tersedia(c, rd)]
    terpakai = {c["id"] for c in cocok}
    hasil = [{"produk": c, "pengganti_dari": None} for c in cocok]
    sisa = list(hilang)
    for c in pool:
        if len(hasil) >= jumlah or not sisa:
            break
        if c["id"] in terpakai or not tersedia(c, rd):
            continue
        asal = sisa.pop(0)
        hasil.append({"produk": c, "pengganti_dari": asal["nama"]})
        terpakai.add(c["id"])
    return hasil, hilang, sisa


def tetapkan_aplikasi(daftar, apps):
    rd = aplikasi_rd(apps)
    sisa = list(range(len(daftar)))
    hasil = {}
    himpunan = [set(tersedia(c, rd)) for c in daftar]
    while sisa:
        terbaik = max(rd, key=lambda a: (sum(1 for i in sisa if a in himpunan[i]), -rd.index(a)))
        kena = [i for i in sisa if terbaik in himpunan[i]]
        if not kena:
            break
        for i in kena:
            hasil[i] = terbaik
        sisa = [i for i in sisa if i not in kena]
    return hasil


def premium_sejajar(df):
    if df is None or len(df) < 2:
        return None
    ada_nav = np.flatnonzero(df["nav"].notna().to_numpy())
    if not len(ada_nav) or ada_nav[-1] < 1:
        return None
    i = int(ada_nav[-1])
    nav, close = df["nav"].iloc[i], df["close"].iloc[i - 1]
    if not (nav > 0 and pd.notna(close) and close > 0):
        return None
    return float(close / nav - 1)


def hari_bursa_lalu(tgl, hari_ini=None):
    hari_ini = pd.Timestamp(hari_ini or date.today())
    return int(np.busday_count(pd.Timestamp(tgl).date(), hari_ini.date()))


def info_lot(nilai, harga):
    per_lot = harga * LOT
    lot = int(math.floor(nilai / per_lot)) if per_lot > 0 else 0
    bulan = math.ceil(per_lot / nilai) if nilai > 0 and lot == 0 else None
    return {"harga_per_lot": per_lot, "lot": lot, "perkiraan": lot * per_lot, "bulan_kumpul": bulan}


def badge_premium(prem):
    if prem is None:
        return {"warna": "abu", "teks": "selisih belum tersedia"}
    if prem <= BATAS_PREMIUM:
        return {"warna": "hijau", "teks": "wajar untuk beli"}
    return {"warna": "kuning", "teks": "agak mahal hari ini, tunda dulu kalau bisa"}


def _kandidat_etf():
    from backend.db import data as dt
    from backend.ingest import etf_emas as ee
    ring = (dt.baca_hasil("etf_emas_ringkas") or {}).get("etf") or {}
    frames = {k: dt.baca(f"{ee.KOLEKSI}/{k}") for k in ring if dt.ada(f"{ee.KOLEKSI}/{k}")}
    return ring, frames


def etf_terpilih():
    from backend.db import koneksi as kdb
    from backend.ingest import etf_emas as ee
    ring, frames = _kandidat_etf()
    st = kdb.koneksi().paper_h37_status.find_one({"_id": "status"}) or {}
    kode = st.get("pilih_etf_awal")
    sumber = "uji maju"
    if not kode:
        sel = ee.pilih_awal(ee.seleksi(frames, {k: r.get("aum") for k, r in ring.items()}, {k: r.get("nama") for k, r in ring.items()}))
        kode, sumber = sel.get("terpilih"), "pilihan hari ini"
    return kode, sumber, ring, frames


def kartu_etf(nilai, apps, hari_ini=None):
    kode, sumber, ring, frames = etf_terpilih()
    ada = [a for a in apps if a in APLIKASI_ETF]
    if not kode or kode not in frames:
        return None, [{"jenis": "etf_kosong", "teks": "Belum ada ETF emas yang memenuhi syarat. Porsi emas ditunda dulu."}]
    df = frames[kode]
    baris = df.dropna(subset=["close"]).iloc[-1]
    tgl = df.dropna(subset=["close"]).index[-1]
    prem = premium_sejajar(df)
    app = None
    if ada:
        app = "ajaib" if "ajaib" in ada and ("stockbit" not in ada) else "stockbit" if "stockbit" in ada else "ajaib"
    lot = info_lot(nilai, float(baris["close"]))
    basi = hari_bursa_lalu(tgl, hari_ini) > HARI_BASI
    kartu = {"tipe": "etf", "kode": kode, "nama": (ring.get(kode) or {}).get("nama", kode), "aplikasi": app, "harga": float(baris["close"]), "tgl_data": str(pd.Timestamp(tgl).date()), "basi": basi,
             "premium": prem, "badge": badge_premium(prem), "label_premium": LABEL_PREMIUM, "nilai": nilai, "sumber_pilihan": sumber, "fee": FEE_ETF.get(app),
             "cara": "Beli manual di jam bursa lewat akun saham, per lot (1 lot = 100 unit). Tidak ada beli rutin otomatis, jadi ulangi tiap bulan.",
             "aturan_premium": "Jangan beli hari ini kalau harga lebih mahal lebih dari 2% dari nilai emasnya; badge di sini memberi tanda.",
             "catatan_syariah": CATATAN_AKUN_SYARIAH, "fatwa": FATWA, "ketersediaan": KATA_ETF, **lot}
    peringatan = []
    if not ada:
        peringatan.append({"jenis": "etf_aplikasi", "teks": "Kaki emas butuh akun saham (Stockbit/Ajaib).", "saran": [NAMA_APLIKASI[a] for a in APLIKASI_ETF]})
    return kartu, peringatan


def _nama_di_aplikasi(db, fid, app):
    x = db.rd_platform.find_one({"_id": f"{app}|{fid}"}) or {}
    return x.get("nama")


def _kartu_rd(pt, c, nilai, total, kin, pengganti, app, db, catatan=None):
    k = pt._kartu(c, nilai, catatan, kin)
    return {**k, "tipe": "rd", "aplikasi": app, "cari_di_aplikasi": _nama_di_aplikasi(db, c["id"], app) or c["nama"], "pengganti_dari": pengganti,
            "porsi": nilai / total if total else None,
            "min_beli_teks": "minimal dari manajer investasi, cek di aplikasi",
            "min_beli_melebihi": bool(c.get("min_beli_nilai") and c.get("min_beli_uang") == "IDR" and nilai > 0 and c["min_beli_nilai"] > nilai),
            "tersedia_di": tersedia(c, APLIKASI_RD)}


def _kelompok(kartu, apps):
    per = {}
    for k in kartu:
        per.setdefault(k["aplikasi"], []).append(k)
    urut = [a for a in APLIKASI_SEMUA if a in per]
    return [{"aplikasi": a, "nama": NAMA_APLIKASI[a], "total": sum(x["nilai"] for x in per[a]), "produk": per[a]} for a in urut]


def pertumbuhan(apps=None, setoran=1_000_000, modal_awal=0, gaya="saham", hari_ini=None):
    from backend.app.services import pertumbuhan as pt
    from backend.db import data as dt
    from backend.db import koneksi as kdb
    from backend.research import keranjang_pertumbuhan as kp
    apps = normal_aplikasi(apps)
    gaya = gaya if gaya in BAGIAN else "saham"
    dok = kp.terbaru("semua")
    if dok is None:
        return {"ada": False}
    lolos, _, _ = kp.calon()
    setoran = max(float(setoran or 0), 0.0)
    modal_awal = max(float(modal_awal or 0), 0.0)
    w = BAGIAN[gaya]
    kin = pt._kinerja()
    db = kdb.koneksi()
    peringatan = []
    dasar_lk = dok["isi"]["LK"]
    jumlah_lk = kp.JUMLAH["LK"]
    hasil_lk, hilang_lk, sisa_hilang = pilih_produk(dasar_lk, lolos["LK"], apps, jumlah_lk)
    terpilih_lk = [x["produk"] for x in hasil_lk]
    pengganti_lk = [x["pengganti_dari"] for x in hasil_lk]
    rd = aplikasi_rd(apps)
    if not rd:
        peringatan.append({"jenis": "tanpa_rd", "teks": "Produk reksa dana kategori ini tidak tersedia di aplikasimu, butuh aplikasi: Bibit, Ajaib, atau Makmur.", "saran": [NAMA_APLIKASI[a] for a in APLIKASI_RD]})
    elif len(terpilih_lk) < jumlah_lk:
        butuh = [NAMA_APLIKASI[a] for a in APLIKASI_RD if a not in rd and len(pilih_produk(dasar_lk, lolos["LK"], [*apps, a], jumlah_lk)[0]) > len(terpilih_lk)]
        peringatan.append({"jenis": "lokal_kurang", "teks": f"Hanya {len(terpilih_lk)} dari {jumlah_lk} RD saham syariah Indonesia yang tersedia di aplikasimu." + (f" Produk kategori ini yang lain butuh aplikasi: {', '.join(butuh)}." if butuh else ""),
                           "saran": butuh})
    dasar_gl = dok["isi"]["GL"]
    gl = [c for c in dasar_gl if c["id"] in GLOBAL_DISETUJUI and tersedia(c, rd)]
    if not gl and rd:
        ref = next((c for c in lolos["GL"] if c["id"] in GLOBAL_DISETUJUI), None) or (dasar_gl[0] if dasar_gl else None)
        butuh = [NAMA_APLIKASI[p["kode"]] for p in (ref or {}).get("platform") or []] or ["Bibit"]
        peringatan.append({"jenis": "global_aplikasi", "teks": f"Produk global tidak tersedia di aplikasimu, butuh Bibit. Produk global tidak diganti otomatis.", "saran": butuh})
    bagian = {k: setoran * v for k, v in w.items()}
    per_lk = bagian["lokal"] / len(terpilih_lk) if terpilih_lk else 0.0
    per_gl = bagian["global"] / len(gl) if gl else 0.0
    rata = bool(terpilih_lk or gl) and min([per_lk] * len(terpilih_lk) + [per_gl] * len(gl)) >= pt.SETOR_RATA_MIN
    nilai_lk = {c["id"]: per_lk for c in terpilih_lk}
    nilai_gl = {c["id"]: per_gl for c in gl}
    if not rata and (terpilih_lk or gl):
        urut = pt._giliran(terpilih_lk, gl)
        bulan_ini = pd.Timestamp(hari_ini or date.today()).to_period("M")
        ini = urut[(bulan_ini.month - 1) % len(urut)]["id"]
        nilai_lk = {c["id"]: (setoran * (w["lokal"] + w["global"]) if c["id"] == ini else 0.0) for c in terpilih_lk}
        nilai_gl = {c["id"]: (setoran * (w["lokal"] + w["global"]) if c["id"] == ini else 0.0) for c in gl}
    semua = [(c, nilai_lk[c["id"]], pengganti_lk[i], "lokal") for i, c in enumerate(terpilih_lk)] + [(c, nilai_gl[c["id"]], None, "global") for c in gl]
    peta = tetapkan_aplikasi([x[0] for x in semua], apps)
    kartu = []
    for i, (c, nilai, pengganti, kaki) in enumerate(semua):
        app = peta.get(i)
        if app is None:
            continue
        catatan = pt.CATATAN_GLOBAL if kaki == "global" else None
        k = _kartu_rd(pt, c, nilai, setoran, kin, pengganti, app, db, catatan)
        kartu.append({**k, "kaki": kaki})
    etf = None
    if w["emas"] > 0:
        etf, per = kartu_etf(bagian["emas"], apps, hari_ini)
        peringatan += per
    grup = _kelompok(kartu, apps)
    if etf and etf["aplikasi"]:
        grup.append({"aplikasi": etf["aplikasi"], "nama": NAMA_APLIKASI[etf["aplikasi"]], "total": etf["nilai"], "produk": [etf]})
        urut = {a: i for i, a in enumerate(APLIKASI_SEMUA)}
        grup.sort(key=lambda g: urut[g["aplikasi"]])
        gabung = {}
        for g in grup:
            if g["aplikasi"] in gabung:
                gabung[g["aplikasi"]]["produk"] += g["produk"]
                gabung[g["aplikasi"]]["total"] += g["total"]
            else:
                gabung[g["aplikasi"]] = g
        grup = list(gabung.values())
    awal = None
    if modal_awal > 0:
        awal = {"total": modal_awal, "lokal_per_produk": modal_awal * w["lokal"] / len(terpilih_lk) if terpilih_lk else 0.0,
                "global_per_produk": modal_awal * w["global"] / len(gl) if gl else 0.0, "emas": modal_awal * w["emas"]}
    return bersih({"ada": True, "masukan": {"apps": apps, "setoran": setoran, "modal_awal": modal_awal, "gaya": gaya}, "app_angka": aplikasi_angka(apps), "bagian": bagian,
                   "rata": rata, "grup": grup, "peringatan": peringatan, "etf": etf, "awal": awal, "dibentuk": dok["dibentuk"].isoformat(timespec="minutes") if hasattr(dok["dibentuk"], "isoformat") else str(dok["dibentuk"])})


def konservatif(apps=None, modal=1_000_000_000, pengeluaran=10_000_000, darurat=6, opsi="sbn50", hari_ini=None):
    from backend.app.services import penarikan as pn
    from backend.app.services import reksadana as rdn
    from backend.db import koneksi as kdb
    from backend.research import keranjang as kr
    from backend.app.services import pertumbuhan as pt
    apps = normal_aplikasi(apps)
    r = pn.rencana(modal, pengeluaran, darurat, opsi, aplikasi_angka(apps))
    if not r.get("ada"):
        return {"ada": False}
    modal = r["masukan"]["modal"]
    rd = aplikasi_rd(apps)
    cl, _ = kr.calon()
    dok = kr.terbaru("semua")
    db = kdb.koneksi()
    skala = {int(x["id"]): float(x["risiko"]) for x in rdn.daftar()["data"] if x.get("risiko") is not None}
    peringatan = []
    if not rd:
        return bersih({"ada": True, "rencana": r, "grup": [], "peringatan": [{"jenis": "tanpa_rd", "teks": "Produk reksa dana tidak tersedia di aplikasimu, butuh aplikasi: Bibit, Ajaib, atau Makmur.",
                                                                           "saran": [NAMA_APLIKASI[a] for a in APLIKASI_RD]}], "modal_kecil": modal < MODAL_KECIL})
    urut_pool = {k: kr.urutan(cl[k])[0] for k in ("PU", "PT")}
    pilih = {}
    for k in ("PU", "PT"):
        hasil, hilang, sisa = pilih_produk(dok["isi"][k], urut_pool[k], apps, kr.JUMLAH)
        pilih[k] = [(x["produk"], x["pengganti_dari"]) for x in hasil]
        if len(pilih[k]) < kr.JUMLAH:
            butuh = [NAMA_APLIKASI[a] for a in APLIKASI_RD if a not in rd and len(pilih_produk(dok["isi"][k], urut_pool[k], [*apps, a], kr.JUMLAH)[0]) > len(pilih[k])]
            nama = "RD pasar uang" if k == "PU" else "RD pendapatan tetap"
            if not pilih[k]:
                peringatan.append({"jenis": "kategori_kosong", "teks": f"Produk {nama} tidak tersedia di aplikasimu, butuh aplikasi: {', '.join(butuh) or 'Bibit, Ajaib, atau Makmur'}.", "saran": butuh})
            else:
                peringatan.append({"jenis": "kategori_kurang", "teks": f"Hanya {len(pilih[k])} dari {kr.JUMLAH} {nama} yang tersedia di aplikasimu." + (f" Yang lain butuh aplikasi: {', '.join(butuh)}." if butuh else ""), "saran": butuh})
    pu = pilih["PU"]
    kartu = []
    kecil = modal < MODAL_KECIL
    nilai_rd = r["sisa"] - r["terkunci"]
    if kecil:
        isi = pu[:2]
        for c, peng in isi:
            kartu.append(("darurat", c, modal / len(isi), peng))
    else:
        if pu and r["dana_darurat"] > 0:
            murah = pu[0][0]
            besar = max([c for c, _ in pu if c["id"] != murah["id"]] or [murah], key=lambda c: c.get("aum") or 0)
            dar = [murah] if besar["id"] == murah["id"] else [murah, besar]
            asal = {c["id"]: p for c, p in pu}
            kartu += [("darurat", c, r["dana_darurat"] / len(dar), asal.get(c["id"])) for c in dar]
        if pilih["PT"]:
            kartu += [("pt", c, nilai_rd / 2 / len(pilih["PT"]), p) for c, p in pilih["PT"]]
        if pu:
            kartu += [("pu", c, nilai_rd / 2 / len(pu), p) for c, p in pu]
    daftar = [x[1] for x in kartu]
    peta = tetapkan_aplikasi(daftar, apps)
    rd_kartu = []
    for i, (wadah, c, nilai, peng) in enumerate(kartu):
        app = peta.get(i)
        if app is None:
            continue
        k = pn._kartu(c, wadah, nilai, modal, skala)
        rd_kartu.append({**k, "tipe": "rd", "aplikasi": app, "kaki": wadah, "cari_di_aplikasi": _nama_di_aplikasi(db, c["id"], app) or c["nama"], "pengganti_dari": peng,
                         "min_beli_teks": "minimal dari manajer investasi, cek di aplikasi", "tersedia_di": tersedia(c, APLIKASI_RD)})
    grup = _kelompok(rd_kartu, apps)
    sbn = None if kecil else r.get("sbn")
    return bersih({"ada": True, "rencana": r, "grup": grup, "peringatan": peringatan, "sbn": sbn, "modal_kecil": kecil,
                   "label_modal_kecil": "Modal masih kecil — pakai sebagai dana darurat dulu; penghasilan rutin baru berarti di modal besar." if kecil else None,
                   "masukan": {"apps": apps, "modal": modal}})
