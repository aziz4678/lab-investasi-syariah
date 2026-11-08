from datetime import date

import pandas as pd

from backend.app.services.reksadana import bersih
from backend.db import data as dt

GESER = 0.003
BASI_BULAN = 2


def _bulan(s):
    return pd.Period(s, "M")


def _patokan(dok, tahun):
    for t in (tahun - 1, tahun - 2):
        batas = pd.Period(f"{t}-12", "M")
        x = next((x for x in dok if _bulan(x["periode"]["akhir"]) >= batas), None)
        if x is not None:
            return x, t
    return dok[-1], None


def _aman(x):
    return {p["kode"]: p.get("aman_5") for p in x["portofolio"]}


def hasil():
    dok = list(dt.db()["hasil_penarikan"].find({}, {"_id": 0}).sort("dihitung", 1))
    if not dok:
        return {"ada": False}
    terbaru = dok[-1]
    hari = date.today()
    patokan, tahun_data = _patokan(dok, hari.year)
    akhir = _bulan(terbaru["periode"]["akhir"])
    umur = (pd.Period(hari, "M") - akhir).n
    a_pat, a_baru = _aman(patokan), _aman(terbaru)
    geser = {k: {"patokan": a_pat.get(k), "terbaru": v} for k, v in a_baru.items()
             if v is not None and a_pat.get(k) is not None and abs(v - a_pat[k]) > GESER}
    riwayat = [{"dihitung": x["dihitung"].isoformat(timespec="minutes"), "akhir": x["periode"]["akhir"], "aman_5": _aman(x)} for x in dok[-24:]]

    def siap(x):
        y = dict(x)
        y["dihitung"] = x["dihitung"].isoformat(timespec="minutes")
        return y

    return bersih({"ada": True, "terbaru": siap(terbaru), "patokan": siap(patokan), "patokan_tahun": hari.year,
                   "patokan_data_desember": tahun_data, "umur_bulan": umur, "basi": umur > BASI_BULAN, "geser": geser, "ambang_geser": GESER,
                   "riwayat": riwayat})


KUNCI_SIDIK = ("rd_ojk", "inflasi", "bi_rate", "sbsn_csv", "keranjang")
JEDA_ST_BULAN = 5


def perlu_hitung():
    from backend.research.analisis_penarikan import sidik_input
    akhir = dt.db()["hasil_penarikan"].find_one({}, {"sidik": 1}, sort=[("dihitung", -1)])
    if akhir is None:
        return True, "belum pernah dihitung"
    kini = sidik_input(None)
    beda = [k for k in KUNCI_SIDIK if kini.get(k) != akhir["sidik"].get(k)]
    return bool(beda), ", ".join(f"{k}: {akhir['sidik'].get(k)} -> {kini.get(k)}" for k in beda) or "data sama"


def pengingat_sbn():
    from backend.core.config import ROOT
    from backend.db import koneksi as d
    c = pd.read_csv(ROOT / "data" / "sbsn_ritel.csv", dtype=str).fillna("")
    ada = set(c["seri"])
    pesan = []
    for x in d.koneksi().rd_sukuk.find({"jenis": "SR"}, {"_id": 1}).sort("_id", 1):
        if x["_id"] not in ada:
            pesan.append({"seri": x["_id"], "alasan": "sudah tercatat di Pasardana"})
    st = c[c["jenis"] == "ST"].copy()
    st["tutup"] = pd.to_datetime(st["tgl_penawaran_akhir"])
    terakhir = st.sort_values("tutup").iloc[-1]
    nomor = int(terakhir["seri"][2:5])
    batas = terakhir["tutup"] + pd.DateOffset(months=JEDA_ST_BULAN)
    if pd.Timestamp(date.today()) > batas:
        pesan.append({"seri": f"ST{nomor + 1:03d}", "alasan": f"lebih dari {JEDA_ST_BULAN} bulan sejak {terakhir['seri'][:5]} ditutup ({terakhir['tutup']:%d %b %Y}); perkiraan seri berikutnya"})
    ri = d.koneksi().rd_info.find_one({"_id": "ringkas"}) or {}
    oj, tolak = ri.get("ojk") or {}, ri.get("ojk_peringatan")
    ojk = {"sampai": oj.get("sampai"), "diimpor": oj["diimpor"].isoformat(timespec="minutes") if oj.get("diimpor") else None,
           "peringatan": {"waktu": tolak["waktu"].isoformat(timespec="minutes"), "pesan": tolak["pesan"]} if tolak else None}
    return {"ojk": ojk, "pengingat": pesan, "st_terakhir": terakhir["seri"][:5], "st_tutup": f"{terakhir['tutup']:%Y-%m-%d}", "cek_st_setelah": f"{batas:%Y-%m-%d}",
            "jumlah_seri": len(c)}


POLA_TAHUN = 3


def _csv_sbn():
    from backend.core.config import ROOT
    c = pd.read_csv(ROOT / "data" / "sbsn_ritel.csv", dtype=str).fillna("")
    c["mulai"] = pd.to_datetime(c["tgl_penawaran_mulai"])
    c["tutup"] = pd.to_datetime(c["tgl_penawaran_akhir"])
    c["dasar"] = c["seri"].str.replace(r"T\d$", "", regex=True)
    return c


def penawaran_berikut():
    c = _csv_sbn()
    hari = pd.Timestamp(date.today())
    buka = c[c["tutup"] >= hari]
    hasil = {"dibuka": None, "perkiraan": []}
    if len(buka):
        g = buka[buka["dasar"] == buka.sort_values("mulai")["dasar"].iloc[0]]
        hasil["dibuka"] = {"seri": g["dasar"].iloc[0], "jenis": g["jenis"].iloc[0], "mulai": f"{g['mulai'].iloc[0]:%Y-%m-%d}", "tutup": f"{g['tutup'].iloc[0]:%Y-%m-%d}",
                           "terbit": g["tgl_terbit"].iloc[0] or None, "sumber": g["sumber"].iloc[0],
                           "varian": [{"seri": r.seri, "tenor": int(r.tenor_th), "jatuh_tempo": r.jatuh_tempo, "kupon": float(r.kupon_awal) / 100,
                                       "jenis_kupon": r.jenis_kupon, "spread": float(r.spread_bi_rate) / 10000 if r.spread_bi_rate else None} for r in g.itertuples()]}
    for jenis in ("SR", "ST"):
        x = c[(c["jenis"] == jenis) & (c["mulai"] >= hari - pd.DateOffset(years=POLA_TAHUN))].drop_duplicates("dasar")
        if x.empty:
            continue
        bulan = sorted(set(x["mulai"].dt.month))
        akhir = c[c["jenis"] == jenis].sort_values("mulai").iloc[-1]
        kandidat = []
        for th in (hari.year, hari.year + 1, hari.year + 2):
            for b in bulan:
                t = pd.Timestamp(year=th, month=b, day=1)
                if t > max(hari, akhir["tutup"]):
                    kandidat.append(t)
        nomor = int(akhir["dasar"][2:])
        varian = c[c["dasar"] == akhir["dasar"]]["tenor_th"].astype(int).tolist()
        hasil["perkiraan"].append({"jenis": jenis, "seri": f"{jenis}{nomor + 1:03d}", "bulan": f"{min(kandidat):%Y-%m}" if kandidat else None,
                                   "pola_bulan": bulan, "tenor": varian, "dasar_pola": f"{len(x)} penawaran {jenis} sejak {hari.year - POLA_TAHUN}"})
    return hasil


def sr_beredar():
    from backend.app.services import reksadana as rdn
    data = [x for x in rdn.sukuk()["data"] if x.get("jenis") == "SR"]
    return sorted([{"kode": x["kode"], "kupon": x.get("kupon"), "jatuh_tempo": x.get("jatuh_tempo"), "sisa_tahun": x.get("sisa_tahun"), "harga": x.get("harga"),
                    "ytm": x.get("ytm"), "ytm_bersih": x.get("ytm_bersih"), "tgl_harga": x.get("tgl_harga")} for x in data], key=lambda x: str(x["jatuh_tempo"]))


def konservatif():
    h = hasil()
    from backend.research.analisis_profil import NAMA_HASIL
    return bersih({**h, "penawaran": penawaran_berikut(), "sr": sr_beredar(), "profil": dt.baca_hasil(NAMA_HASIL)})


OPSI = ("tanpa_sbn", "sbn30", "sbn50", "sbn70")
PAJAK_KUPON = 0.10


def _nilai_aman(p):
    return -1.0 if p is None or p.get("aman_5") is None else p["aman_5"]


def _dok_rencana(aplikasi):
    h = hasil()
    if not h.get("ada"):
        return None, None
    for kunci in ("patokan", "terbaru"):
        x = h[kunci]
        if (x.get("keranjang") or {}).get(aplikasi):
            return h, x
    return h, h["terbaru"]


def skenario(dok, kode, aplikasi):
    kat = next((p for p in dok["portofolio"] if p["kode"] == kode), None)
    kr = (dok.get("keranjang") or {}).get(aplikasi)
    krp = next((p for p in kr["portofolio"] if p["kode"] == kode), None) if kr else None
    if krp is not None and _nilai_aman(krp) < _nilai_aman(kat):
        return "keranjang", krp, kr.get("rata_rata")
    return "kategori", kat, dok.get("rata_rata")


def _varian_sbn(pen):
    c = _csv_sbn()
    if pen.get("dibuka"):
        x = pen["dibuka"]
        return {"status": "dibuka", "seri": x["seri"], "jenis": x["jenis"], "mulai": x["mulai"], "tutup": x["tutup"], "terbit": x["terbit"], "sumber": x["sumber"],
                "varian": [{"seri": v["seri"], "tenor": v["tenor"], "jatuh_tempo": v["jatuh_tempo"], "kupon": v["kupon"], "kupon_perkiraan": False,
                            "jenis_kupon": v["jenis_kupon"]} for v in x["varian"]]}
    calon = sorted([x for x in pen.get("perkiraan") or [] if x.get("bulan")], key=lambda x: x["bulan"])
    if not calon:
        return None
    x = calon[0]
    lalu = c[c["jenis"] == x["jenis"]].sort_values("mulai")
    akhir = lalu[lalu["dasar"] == lalu["dasar"].iloc[-1]] if len(lalu) else lalu
    kupon = {int(r.tenor_th): float(r.kupon_awal) / 100 for r in akhir.itertuples()}
    bulan = pd.Period(x["bulan"], "M")
    return {"status": "perkiraan", "seri": x["seri"], "jenis": x["jenis"], "bulan": x["bulan"], "terbit": None,
            "varian": [{"seri": f"{x['seri']}T{t}", "tenor": t, "jatuh_tempo": str(bulan + 12 * t), "kupon": kupon.get(t), "kupon_perkiraan": True,
                        "jenis_kupon": None} for t in x["tenor"]]}


def _bulan_terbit(sbn):
    if sbn is None:
        return None
    if sbn.get("terbit"):
        return pd.Period(sbn["terbit"], "M")
    if sbn.get("tutup"):
        return (pd.Timestamp(sbn["tutup"]) + pd.Timedelta(days=7)).to_period("M")
    return pd.Period(sbn["bulan"], "M")


RISIKO_JENIS = {"pt": "Sedang", "pu": "Rendah", "darurat": "Rendah"}


def label_risiko(skala):
    return "Rendah" if skala <= 3 else "Sedang" if skala <= 6 else "Tinggi"


def _risiko(c, wadah, skala):
    nilai = skala.get(c["id"])
    if nilai is not None:
        return {"risiko": label_risiko(nilai), "risiko_skala": nilai, "risiko_sumber": "resmi"}
    return {"risiko": RISIKO_JENIS[wadah], "risiko_skala": None, "risiko_sumber": "jenis"}


def _kartu(c, wadah, nilai, total, skala):
    return {"id": c["id"], "nama": c["nama"], "mi": c.get("mi"), "wadah": wadah, "biaya": c.get("biaya"), "aum": c.get("aum"), "tahun_data": c.get("tahun_data"),
            "platform": c.get("platform") or [], "nilai": nilai, "porsi": nilai / total if total else None, **_risiko(c, wadah, skala)}


def rencana(modal=1_000_000_000, pengeluaran=10_000_000, darurat=6, opsi="sbn50", aplikasi="semua"):
    from backend.research import keranjang as kr
    aplikasi = aplikasi if aplikasi in kr.APLIKASI else "semua"
    opsi = opsi if opsi in OPSI else "sbn50"
    h, dok = _dok_rencana(aplikasi)
    if dok is None:
        return {"ada": False}
    kini = kr.terbaru(aplikasi)
    if kini is None:
        kr.perbarui(cetak=False)
        kini = kr.terbaru(aplikasi)
    isi = kini["isi"]
    pakai, port, rata = skenario(dok, opsi, aplikasi)
    hari = pd.Timestamp(date.today())
    bulan_ini = hari.to_period("M")

    modal, pengeluaran, darurat = max(float(modal), 0.0), max(float(pengeluaran), 0.0), max(int(darurat), 0)
    nilai_darurat = min(pengeluaran * darurat, modal)
    sisa = modal - nilai_darurat
    w = port["porsi_sbn"]
    nilai_sbn = sisa * w
    nilai_rd = sisa - nilai_sbn
    aman = port.get("aman_5")
    penghasilan = sisa * aman / 12 if aman is not None else None

    pu, pt = isi.get("PU", []), isi.get("PT", [])
    from backend.app.services import reksadana as rdn
    skala = {int(x["id"]): float(x["risiko"]) for x in rdn.daftar()["data"] if x.get("risiko") is not None}
    darurat_produk = []
    if pu and nilai_darurat > 0:
        murah = pu[0]
        besar = max([c for c in pu if c["id"] != murah["id"]] or [murah], key=lambda c: c.get("aum") or 0)
        pilih = [murah] if besar["id"] == murah["id"] else [murah, besar]
        darurat_produk = [_kartu(c, "darurat", nilai_darurat / len(pilih), modal, skala) for c in pilih]
    belanja_pt = [_kartu(c, "pt", nilai_rd / 2 / len(pt), modal, skala) for c in pt] if pt else []
    belanja_pu = [_kartu(c, "pu", nilai_rd / 2 / len(pu), modal, skala) for c in pu] if pu else []

    sbn = _varian_sbn(penawaran_berikut()) if w > 0 else None
    kupon_bulan = 0.0
    if sbn:
        for v in sbn["varian"]:
            v["nilai"] = nilai_sbn / len(sbn["varian"])
            v["kupon_bersih_bulan"] = v["nilai"] * v["kupon"] * (1 - PAJAK_KUPON) / 12 if v["kupon"] is not None else None
        kupon_bulan = sum(v["kupon_bersih_bulan"] or 0 for v in sbn["varian"])
        terbit = _bulan_terbit(sbn)
        sbn["kupon_mulai"] = str(terbit + 1) if terbit is not None else None
        sbn["kupon_bersih_bulan"] = kupon_bulan
        sbn["parkir_di"] = {"id": pu[0]["id"], "nama": pu[0]["nama"]} if pu else None
        sbn["cair_paling_awal"] = min(v["jatuh_tempo"] for v in sbn["varian"])

    def jual(t):
        if penghasilan is None or not pu:
            return None
        terbit = _bulan_terbit(sbn)
        kupon = kupon_bulan if sbn and terbit is not None and t > terbit else 0.0
        kurang = penghasilan - kupon
        c = pu[(t.year * 12 + t.month - 1) % len(pu)]
        return {"bulan": str(t), "produk": {"id": c["id"], "nama": c["nama"], "mi": c.get("mi")}, "kupon": kupon,
                "jual": max(kurang, 0.0), "lebih": max(-kurang, 0.0)}

    desember = None
    if rata and penghasilan is not None and nilai_rd > 0:
        jual_th = max(penghasilan - kupon_bulan, 0.0) * 12
        lebih_th = max(kupon_bulan - penghasilan, 0.0) * 12
        a = nilai_rd / 2 * (1 + rata["PT"]) + lebih_th / 2
        b = nilai_rd / 2 * (1 + rata["PU"]) - jual_th + lebih_th / 2
        geser = (a - b) / 2
        desember = {"pt_sebelum": a, "pu_sebelum": b, "pindah": abs(geser), "dari": "pt" if geser > 0 else "pu", "ke": "pu" if geser > 0 else "pt",
                    "rata_pt": rata["PT"], "rata_pu": rata["PU"], "tahun": int(hari.year)}

    ringkas_opsi = []
    for k in OPSI:
        s, p, _ = skenario(dok, k, aplikasi)
        ringkas_opsi.append({"kode": k, "skenario": s, "aman_5": p.get("aman_5"), "porsi_sbn": p["porsi_sbn"],
                             "penghasilan": sisa * p["aman_5"] / 12 if p.get("aman_5") is not None else None})

    kr_dok = (dok.get("keranjang") or {}).get(aplikasi) or {}
    banding = []
    for p in dok["portofolio"]:
        kp = next((x for x in kr_dok.get("portofolio", []) if x["kode"] == p["kode"]), None)
        banding.append({"kode": p["kode"], "nama": p["nama"], "kategori": {k: p.get(k) for k in ("aman_3", "aman_5", "cagr_riil", "cagr_nominal")},
                        "keranjang": {k: kp.get(k) for k in ("aman_3", "aman_5", "cagr_riil", "cagr_nominal")} if kp else None,
                        "dipakai": skenario(dok, p["kode"], aplikasi)[0] if p["kode"] in OPSI else None})

    tanpa_platform = {k: sum(1 for c in v if not c.get("platform")) for k, v in isi.items()}
    return bersih({
        "ada": True, "dihitung": dok["dihitung"], "periode": dok["periode"], "n_mulai_5": dok.get("n_mulai_5"), "patokan": dok is h["patokan"],
        "masukan": {"modal": modal, "pengeluaran": pengeluaran, "darurat": darurat, "opsi": opsi, "aplikasi": aplikasi},
        "skenario": pakai, "portofolio": port, "aman": aman, "penghasilan": penghasilan, "sisa": sisa,
        "dana_darurat": nilai_darurat, "darurat_kurang": pengeluaran * darurat > modal, "terkunci": nilai_sbn, "terkunci_porsi": nilai_sbn / modal if modal else 0.0,
        "belanja": {"darurat": darurat_produk, "pt": belanja_pt, "pu": belanja_pu}, "sbn": sbn,
        "bulanan": [jual(bulan_ini), jual(bulan_ini + 1)], "desember": desember, "opsi": ringkas_opsi,
        "keranjang": {"id": kini["_id"], "dibentuk": kini["dibentuk"], "alasan": kini["alasan"], "info": kini["info"], "kriteria": kini["kriteria"],
                      "sama_dengan_hitungan": kr_dok.get("id_keranjang") == kini["_id"], "isian": {k: v.get("isian") for k, v in (kr_dok.get("info") or {}).items()},
                      "id_hitungan": kr_dok.get("id_keranjang"), "tanpa_platform": tanpa_platform},
        "banding": banding,
    })


TARIK_MAKS = 0.30
_KONTEKS = {}


def _konteks(skenario_pakai, aplikasi):
    from backend.research import analisis_likuiditas as al
    from backend.research import analisis_penarikan as ap
    from backend.research import keranjang as kr
    akhir_hitung = dt.db()["hasil_penarikan"].find_one({}, {"dihitung": 1}, sort=[("dihitung", -1)])
    kunci = (skenario_pakai, aplikasi if skenario_pakai == "keranjang" else None, akhir_hitung["dihitung"] if akhir_hitung else None)
    if kunci not in _KONTEKS:
        _KONTEKS.clear()
        h = al.semua_indeks()
        L = None
        if skenario_pakai == "keranjang":
            _, _, _, mulai = ap.siapkan(h)
            L, _ = kr.indeks(kr.terbaru(aplikasi)["isi"], h["L"], mulai)
        r, cpi, akhir, mulai = ap.siapkan(h, L)
        _KONTEKS[kunci] = (r, cpi, akhir, mulai, ap.penawaran(), ap.bi_rate())
    return _KONTEKS[kunci]


def simulasi(modal=1_000_000_000, opsi="sbn50", tarik=None, mulai=None, aplikasi="semua"):
    from backend.research import analisis_penarikan as ap
    from backend.research import keranjang as kr
    aplikasi = aplikasi if aplikasi in kr.APLIKASI else "semua"
    opsi = opsi if opsi in OPSI else "sbn50"
    h, dok = _dok_rencana(aplikasi)
    if dok is None:
        return {"ada": False}
    pakai, port, _ = skenario(dok, opsi, aplikasi)
    r, cpi, akhir, awal_data, sbn, bi = _konteks(pakai, aplikasi)
    pilihan = [str(awal_data)] + [f"{y}-01" for y in range(awal_data.year + 1, akhir.year) if pd.Period(f"{y}-01", "M") + 11 <= akhir]
    t0 = pd.Period(mulai, "M") if mulai else pd.Period(pilihan[0], "M")
    t0 = min(max(t0, awal_data), akhir - 11)
    tarik = port.get("aman_5") if tarik is None else min(max(float(tarik), 0.0), TARIK_MAKS)
    tarik = tarik or 0.0
    riil, terkunci, gagal = ap.simulasi(t0, akhir, "rd", port["porsi_sbn"], tarik, r, cpi, sbn, bi)
    acuan = cpi[t0 - 1]
    bulan = pd.period_range(t0, akhir, freq="M")
    habis = int(gagal[0]) if gagal else None
    nominal_tarik = tarik / 12
    seri, total_ambil = [], 0.0
    for i, t in enumerate(bulan):
        if i > 0 and i % 12 == 0:
            nominal_tarik *= cpi[t - 1] / cpi[t - 13]
        nilai = float(riil[i] * cpi[t] / acuan * modal)
        if habis is None or i < habis:
            ambil = nominal_tarik * modal
        elif i == habis:
            ambil = float(riil[i - 1] * cpi[t - 1] / acuan * modal) if i > 0 else modal
        else:
            ambil = 0.0
        total_ambil += ambil
        seri.append({"bulan": str(t), "nilai": nilai, "daya_beli": float(riil[i] * modal), "ambil": ambil, "total_ambil": total_ambil,
                     "terkunci": float(terkunci[i])})
    per_tahun = []
    for y in sorted({int(x["bulan"][:4]) for x in seri}):
        b = [x for x in seri if x["bulan"].startswith(str(y))]
        per_tahun.append({"tahun": y, "bulan": len(b), "ambil_bulan": max(x["ambil"] for x in b), "ambil_tahun": sum(x["ambil"] for x in b),
                          "nilai": b[-1]["nilai"], "daya_beli": b[-1]["daya_beli"], "total_ambil": b[-1]["total_ambil"]})
    terendah = min(range(len(seri)), key=lambda i: seri[i]["daya_beli"])
    return bersih({
        "ada": True, "skenario": pakai, "opsi": opsi, "porsi_sbn": port["porsi_sbn"], "aman_5": port.get("aman_5"), "modal": float(modal), "tarik": tarik,
        "mulai": str(t0), "akhir": str(akhir), "pilihan_mulai": pilihan, "inflasi": float(cpi[akhir] / acuan - 1),
        "ringkas": {"bulan": len(seri), "total_ambil": total_ambil, "nilai_akhir": seri[-1]["nilai"], "daya_beli_akhir": seri[-1]["daya_beli"],
                    "terendah": {"bulan": seri[terendah]["bulan"], "daya_beli": seri[terendah]["daya_beli"]},
                    "ambil_awal": seri[0]["ambil"], "ambil_akhir": seri[habis - 1]["ambil"] if habis else seri[-1]["ambil"],
                    "habis": seri[habis]["bulan"] if habis is not None else None},
        "seri": seri, "per_tahun": per_tahun,
    })
