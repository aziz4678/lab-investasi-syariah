from functools import lru_cache

import pandas as pd

from backend.db import data as dt

BATAS_BUNGA = 0.25
BATAS_PEER = 2
BATAS_MELAMBAT = 1.5
RASIO_MELAMBAT = 0.25
PERISTIWA = {
    2008: ({"saham_id", "saham_global", "komoditas"}, "Krisis keuangan global (Lehman Brothers bangkrut): saham di seluruh dunia anjlok lebih dari 40%."),
    2011: ({"saham_global"}, "Krisis utang Eropa dan turunnya peringkat utang AS membuat pasar saham dunia bergejolak."),
    2013: ({"bunga", "saham_id", "kurs"}, "Taper tantrum: The Fed memberi sinyal mengurangi stimulus, dana asing keluar dari negara berkembang, rupiah melemah, harga sukuk/obligasi dan saham Indonesia turun."),
    2015: ({"saham_id", "komoditas", "kurs"}, "Harga komoditas jatuh dan ekonomi China melambat (yuan didevaluasi); rupiah melemah dan saham Indonesia turun."),
    2018: ({"bunga", "saham_id", "saham_global", "kurs", "bunga_global"}, "The Fed menaikkan suku bunga 4 kali dan perang dagang AS–China memanas; rupiah melemah, BI menaikkan BI-Rate berkali-kali sehingga harga sukuk/obligasi turun, dan saham dunia anjlok di akhir tahun."),
    2020: ({"saham_id", "saham_global", "komoditas"}, "Pandemi Covid-19: pasar saham dunia jatuh tajam pada Februari–Maret, lalu pulih sebagian."),
    2022: ({"bunga", "bunga_global", "saham_global"}, "Inflasi tinggi; The Fed menaikkan suku bunga paling cepat dalam 40 tahun. Saham (terutama teknologi) dan obligasi dunia turun bersamaan, BI juga menaikkan BI-Rate."),
}
FAKTOR_RD = {
    "pasar_uang": {"bunga"}, "pendapatan_tetap": {"bunga"}, "terproteksi": {"bunga"}, "campuran": {"bunga", "saham_id"},
    "saham": {"saham_id"}, "indeks": {"saham_id"}, "etf": {"saham_id"}, "global": {"saham_global"}, "penyertaan_terbatas": {"bunga"},
}
FAKTOR_ETF = {"saham": {"saham_global", "kurs"}, "obligasi": {"bunga_global", "kurs"}, "sukuk": {"bunga_global", "kurs"},
              "emas": {"komoditas", "kurs"}, "komoditas": {"komoditas", "kurs"}, "properti": {"saham_global", "bunga_global", "kurs"}}
WASPADA = {
    "bunga": ("Suku bunga naik", "Saat BI-Rate/bunga naik, harga sukuk di dalam reksa dana turun sementara."),
    "bunga_global": ("Suku bunga AS naik", "Saat The Fed menaikkan bunga, harga obligasi/sukuk dunia dan saham bervaluasi tinggi cenderung turun."),
    "saham_id": ("Pasar saham Indonesia turun", "Produk ini ikut turun bila indeks saham syariah (JII) turun."),
    "saham_global": ("Pasar saham dunia turun", "Produk ini ikut turun saat saham AS/dunia (terutama teknologi) jatuh."),
    "kurs": ("Rupiah menguat", "Hasil dalam rupiah berkurang saat rupiah menguat, walau nilainya naik dalam dolar."),
    "komoditas": ("Harga emas/komoditas turun", "Nilainya mengikuti harga emas atau komoditas dunia."),
}


def akhir_tahun(s):
    s = s.dropna()
    return s.groupby(s.index.year).last()


@lru_cache(maxsize=1)
def _pasar(kunci):
    p = dt.baca("pasar")
    jii = dt.baca("indeks/JKII")["close"]
    bunga = dt.baca("makro/bunga_antarbank")["nilai"]
    ret = lambda s: (akhir_tahun(s).pct_change() * 100).dropna()
    return {"jii": ret(jii), "sp500": ret(p["sp500"]), "emas": ret(p["emas"]), "kurs": ret(p["usdidr"]),
            "bunga": akhir_tahun(bunga), "bunga_ubah": akhir_tahun(bunga).diff().dropna()}


def pasar():
    return _pasar(str(dt.versi("pasar")))


def koma(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def tanda_angka(v, d=1):
    return ("+" if v > 0 else "") + koma(v, d) + "%"


def alasan_tahun(th, ret, faktor, baris, ps, rp=None, sebelum=None, normal=None):
    a, dipakai = [], set()
    if sebelum is not None and normal is not None and ret >= 0 and sebelum >= max(normal * 1.5, normal + 3):
        a.append({"jenis": "normal", "teks": f"Tahun sebelumnya hasilnya luar biasa tinggi ({tanda_angka(sebelum)}, biasanya ±{koma(normal)}%). Setelah tahun yang sangat bagus, hasil sering kembali ke normal."})
    if th in PERISTIWA and PERISTIWA[th][0] & faktor:
        a.append({"jenis": "peristiwa", "teks": PERISTIWA[th][1]})
        dipakai |= PERISTIWA[th][0] & faktor
    if {"bunga"} & faktor and th in ps["bunga_ubah"].index:
        d = float(ps["bunga_ubah"][th])
        if abs(d) >= BATAS_BUNGA:
            awal, akhir = float(ps["bunga"].get(th - 1, float("nan"))), float(ps["bunga"][th])
            if d > 0:
                a.append({"jenis": "bunga", "teks": f"Suku bunga naik {koma(d, 2)} poin (bunga antarbank {koma(awal, 2)}% → {koma(akhir, 2)}%). Saat bunga naik, harga sukuk yang sudah dimiliki turun."})
                dipakai.add("bunga")
            elif ret >= 0:
                a.append({"jenis": "bunga", "teks": f"Suku bunga turun {koma(-d, 2)} poin (bunga antarbank {koma(awal, 2)}% → {koma(akhir, 2)}%), sehingga imbal hasil deposito/sukuk baru ikut mengecil."})
                dipakai.add("bunga_turun")
    if "saham_id" in faktor and th in ps["jii"].index:
        a.append({"jenis": "pasar", "teks": f"Indeks saham syariah JII tahun itu {tanda_angka(float(ps['jii'][th]))}."})
        if ps["jii"][th] < 0:
            dipakai.add("saham_id")
    if "saham_global" in faktor and th in ps["sp500"].index:
        a.append({"jenis": "pasar", "teks": f"Indeks saham AS (S&P 500) tahun itu {tanda_angka(float(ps['sp500'][th]))} dalam dolar."})
        if ps["sp500"][th] < 0:
            dipakai.add("saham_global")
    if "komoditas" in faktor and th in ps["emas"].index:
        a.append({"jenis": "pasar", "teks": f"Harga emas dunia tahun itu {tanda_angka(float(ps['emas'][th]))} dalam dolar."})
        if ps["emas"][th] < 0:
            dipakai.add("komoditas")
    if "kurs" in faktor and rp is not None and th in ps["kurs"].index:
        k = float(ps["kurs"][th])
        if k <= -2:
            a.append({"jenis": "kurs", "teks": f"Rupiah menguat {koma(-k)}% terhadap dolar, sehingga hasil dalam rupiah lebih kecil dari hasil dalam dolar."})
            dipakai.add("kurs")
        elif k >= 2:
            a.append({"jenis": "kurs", "teks": f"Rupiah melemah {koma(k)}% terhadap dolar, sehingga hasil dalam rupiah lebih besar dari hasil dalam dolar."})
    med = baris.get("kategori")
    if med is not None:
        if ret < med - BATAS_PEER:
            a.append({"jenis": "peer", "teks": f"Lebih buruk dari RD sejenis (nilai tengah {tanda_angka(med)}): sebagian penyebabnya pilihan isi portofolio manajer investasi, bukan pasar saja."})
            dipakai.add("peer")
        elif ret > med + BATAS_PEER:
            a.append({"jenis": "peer", "teks": f"Masih lebih baik dari RD sejenis (nilai tengah {tanda_angka(med)}); tahun itu memang berat untuk produk sejenis."})
        else:
            a.append({"jenis": "peer", "teks": f"Sejalan dengan RD sejenis (nilai tengah {tanda_angka(med)}), jadi penyebab utamanya kondisi pasar, bukan produk ini saja."})
    if not a:
        a.append({"jenis": "lain", "teks": "Penyebab pastinya tidak terlihat dari data pasar; cek fund fact sheet bulan-bulan di tahun itu."})
    return a, dipakai


def analisis(per_tahun, faktor, kolom="ret", kolom_rp=None):
    ps = pasar()
    baris = sorted(per_tahun, key=lambda x: x["tahun"])
    catatan, sumber = [], {}
    semua = [b.get(kolom_rp) if kolom_rp and b.get(kolom_rp) is not None else b.get(kolom) for b in baris if not b.get("berjalan")]
    semua = sorted(v for v in semua if v is not None)
    tengah = float(pd.Series(semua).median()) if len(semua) >= 3 else None
    normal = tengah if tengah is not None and tengah > 0 else None
    sebelum = None
    for b in baris:
        v = b.get(kolom_rp) if kolom_rp and b.get(kolom_rp) is not None else b.get(kolom)
        if v is None:
            continue
        jenis = None
        if v < 0:
            jenis = "rugi"
        elif sebelum is not None and not b.get("berjalan") and sebelum - v >= max(BATAS_MELAMBAT, abs(sebelum) * RASIO_MELAMBAT):
            jenis = "melambat"
        if jenis:
            alasan, dipakai = alasan_tahun(b["tahun"], v, faktor, b, ps, b.get(kolom_rp) if kolom_rp else None, sebelum if jenis == "melambat" else None, normal)
            b["tanda"] = jenis
            catatan.append({"tahun": b["tahun"], "jenis": jenis, "ret": v, "sebelum": sebelum, "berjalan": bool(b.get("berjalan")), "alasan": alasan})
            for f in dipakai:
                sumber.setdefault(f, []).append(b["tahun"])
        if not b.get("berjalan"):
            sebelum = v
    lengkap = [b for b in baris if not b.get("berjalan") and (b.get(kolom_rp) if kolom_rp and b.get(kolom_rp) is not None else b.get(kolom)) is not None]
    nilai = [(b["tahun"], b.get(kolom_rp) if kolom_rp and b.get(kolom_rp) is not None else b.get(kolom)) for b in lengkap]
    beruntun = 0
    for i in range(len(nilai) - 1, 0, -1):
        if nilai[i][1] < nilai[i - 1][1]:
            beruntun += 1
        else:
            break
    tren = {"tahun": [t for t, _ in nilai[-beruntun - 1:]], "jumlah": beruntun} if beruntun >= 2 else None
    waspada = []
    for f, th in sumber.items():
        if f in WASPADA:
            judul, isi = WASPADA[f]
            waspada.append({"kode": f, "judul": judul, "teks": f"{isi} Pernah terjadi: {', '.join(str(t) for t in sorted(set(th)))}."})
    if "peer" in sumber:
        th = ", ".join(str(t) for t in sorted(set(sumber["peer"])))
        waspada.append({"kode": "peer", "judul": "Pernah jauh tertinggal dari produk sejenis", "teks": f"Tahun {th} hasilnya jauh di bawah RD sejenis. Perhatikan perubahan strategi atau manajer investasinya."})
    if tren:
        waspada.append({"kode": "tren", "judul": f"Hasil menurun {tren['jumlah']} tahun berturut-turut",
                        "teks": f"Hasil tahunan terus mengecil sejak {tren['tahun'][0]} ({tren['tahun'][0]}–{tren['tahun'][-1]}). Bisa karena kondisi pasar atau produknya; bandingkan dengan produk sejenis."})
    return {"catatan": catatan, "waspada": waspada, "tren": tren}


MAKS_KEJADIAN = 5


def posisi(s, dekat=-2.0):
    s = s[s > 0].dropna()
    if len(s) < 13:
        return None
    puncak = s.cummax()
    dd = s / puncak - 1
    kini = float(dd.iloc[-1] * 100)
    tgl_puncak = s[: s.index[-1]][s == puncak.iloc[-1]].index[-1]
    dasar = {"turun_kini": kini, "puncak": tgl_puncak.strftime("%Y-%m-%d"), "bulan_sejak": round((s.index[-1] - tgl_puncak).days / 30.44, 1),
             "sampai": s.index[-1].strftime("%Y-%m-%d"), "dekat_puncak": kini > dekat}
    if dasar["dekat_puncak"]:
        return dasar
    episode, mulai = [], None
    for t, v in dd.items():
        if v < 0 and mulai is None:
            mulai = t
        elif v >= 0 and mulai is not None:
            episode.append((mulai, t))
            mulai = None
    kejadian = []
    batas = kini / 100
    for a, b in episode:
        bagian = dd[(dd.index >= a) & (dd.index < b)]
        lewat = bagian[bagian <= batas]
        if lewat.empty:
            continue
        t0 = lewat.index[0]
        t12 = t0 + pd.DateOffset(years=1)
        kejadian.append({"tahun": int(t0.year), "tanggal": t0.strftime("%Y-%m-%d"), "terdalam": float(bagian.min() * 100),
                         "bulan_pulih": round((b - t0).days / 30.44, 1),
                         "ret_12": float((s.asof(t12) / s[t0] - 1) * 100) if t12 <= s.index[-1] else None})
    r12 = [k["ret_12"] for k in kejadian if k["ret_12"] is not None]
    pulih = [k["bulan_pulih"] for k in kejadian]
    dasar.update({"kejadian": sorted(kejadian, key=lambda k: k["terdalam"])[:MAKS_KEJADIAN], "n": len(kejadian),
                  "median_pulih": float(pd.Series(pulih).median()) if pulih else None,
                  "median_ret_12": float(pd.Series(r12).median()) if r12 else None,
                  "naik_12": sum(1 for v in r12 if v > 0), "n_12": len(r12)})
    return dasar
