import re

from backend.core.config import ROOT

BERKAS = ROOT / "docs" / "RENCANA_SCREENER.md"
NAMA_BERKAS = "docs/RENCANA_SCREENER.md"

_H36 = [("## H3-H6", None), ("## Hasil H3-H6", None)]
_TAHAP3 = ("## Tahap 3", "### H12")
_DIVIDEN = ("## Tesis Pemburu Dividen", None)

BAGIAN = {
    "H0": [("# Rencana screener", "## H1:")],
    "H1": [("## H1:", None), ("## Hasil H1 dan H2", None)],
    "H2": [("## H2:", None), ("## Hasil H1 dan H2", None)],
    "H3": _H36,
    "H4": _H36 + [("## PENGECUALIAN: uji H4", None)],
    "H5": _H36,
    "H6": _H36,
    "H7a": [("## H7:", None), ("## Hasil H7", None)],
    "H7b": [("## H7:", None), ("## Hasil H7", None)],
    "H8": [("## Tahap 2", None)],
    "H9": [("## Tahap 2", None)],
    "H10": [("## Tahap 2", None)],
    "H11a": [_TAHAP3, ("## Batas paper trade H11a", None)],
    "H11b": [_TAHAP3],
    "H12a": [("### H12", None)],
    "H12b": [("### H12", None)],
    "H13": [("## H13", None)],
    "H14a": [("## H14:", None)],
    "H14b": [("## H14:", None)],
    "H15a": [("## H15:", None)],
    "H15b": [("## H15:", None)],
    "H16a": [("## H16:", None)],
    "H16b": [("## H16:", None)],
    "H16c": [("## H16c", None)],
    "H17a": [_DIVIDEN, ("## Uji maju Pemburu Dividen", None)],
    "H17b": [_DIVIDEN],
    "H17c": [("## H17c", None)],
    "H17d": [("## H17c", None)],
    "H18": [("## Reksa Dana & Sukuk", None)],
    "H20": [("## H20:", None)],
    "H21": [("## H21", None)],
    "H22": [("## H21", None)],
    "H23": [("## H23:", None)],
    "H25": [("## H25:", None)],
}
for _k in "abcdefg":
    BAGIAN[f"H19{_k}"] = [("## H19:", None)]

JUDUL = re.compile(r"^(#{1,6})\s+(.*)$")
BUTIR = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
PEMISAH = re.compile(r"^\|?\s*:?-{2,}")

_cache = {"mtime": None, "baris": []}


def _baris():
    m = BERKAS.stat().st_mtime
    if _cache["mtime"] != m:
        _cache["baris"] = BERKAS.read_text(encoding="utf-8").splitlines()
        _cache["mtime"] = m
    return _cache["baris"]


def _sel(teks):
    return [x.strip() for x in teks.strip().strip("|").split("|")]


def urai(baris):
    blok, para = [], []

    def tutup():
        if para:
            blok.append({"t": "p", "x": " ".join(para)})
            para.clear()

    i = 0
    while i < len(baris):
        s = baris[i]
        if not s.strip():
            tutup()
            i += 1
            continue
        j = JUDUL.match(s)
        if j:
            tutup()
            blok.append({"t": "h", "n": len(j.group(1)), "x": j.group(2).strip()})
            i += 1
            continue
        if s.lstrip().startswith("|"):
            tutup()
            tabel = []
            while i < len(baris) and baris[i].lstrip().startswith("|"):
                if not PEMISAH.match(baris[i].strip()):
                    tabel.append(_sel(baris[i]))
                i += 1
            blok.append({"t": "tabel", "kolom": tabel[0], "baris": tabel[1:]})
            continue
        b = BUTIR.match(s)
        if b:
            tutup()
            penanda = b.group(2)
            blok.append({"t": "li", "n": min(len(b.group(1)) // 2, 2), "m": penanda if penanda[0].isdigit() else None, "x": b.group(3).strip()})
            i += 1
            continue
        if blok and blok[-1]["t"] == "li" and not para and s.startswith(" "):
            blok[-1]["x"] += " " + s.strip()
        else:
            para.append(s.strip())
        i += 1
    tutup()
    return blok


def _potong(baris, mulai, henti):
    awal = next((i for i, s in enumerate(baris) if s.startswith(mulai)), None)
    if awal is None:
        return None
    level = len(JUDUL.match(baris[awal]).group(1))
    akhir = len(baris)
    for i in range(awal + 1, len(baris)):
        j = JUDUL.match(baris[i])
        if not j:
            continue
        if (henti and baris[i].startswith(henti)) or (not henti and len(j.group(1)) <= level):
            akhir = i
            break
    return {"judul": JUDUL.match(baris[awal]).group(2).strip(), "baris": awal + 1, "blok": urai(baris[awal + 1:akhir])}


ISTILAH = {
    "cagr": ("Return per tahun (CAGR)", "Rata-rata pertumbuhan modal per tahun. 10% berarti Rp100 jt menjadi ±Rp110 jt setelah setahun."),
    "dd": ("Penurunan terdalam (max drawdown)", "Turun paling dalam dari puncak modal sebelum pulih. -30% berarti modal Rp100 jt sempat tinggal Rp70 jt."),
    "mar": ("Return per risiko (MAR)", "Return per tahun dibagi penurunan terdalam. Makin besar makin baik: untung lebih banyak untuk tiap persen risiko yang ditanggung."),
    "net": ("Untung bersih per transaksi", "Rata-rata hasil tiap beli-jual setelah dipotong biaya ±1,2%."),
    "trade": ("Jumlah transaksi", "Makin sedikit transaksi, makin besar peluang hasilnya kebetulan: 2-3 transaksi untung besar sudah bisa mengubah rata-rata."),
    "set_a": ("Set A (non-syariah likuid)", "Saham non-syariah yang ramai diperdagangkan. Dipakai sebagai data segar karena belum pernah dipakai menyusun strategi."),
    "des": ("DES (Daftar Efek Syariah)", "Daftar saham syariah dari OJK. Yang dipakai adalah daftar yang berlaku pada tanggal itu, bukan daftar hari ini."),
    "ytd": ("YTD", "Dihitung sejak awal tahun sampai laporan terakhir. Laba YTD kuartal 3 = laba Januari-September."),
}

METRIK = {
    "cagr": {"nama": "Return per tahun", "satuan": "%", "arah": 1},
    "dd": {"nama": "Penurunan terdalam", "satuan": "%", "arah": 1, "ket": "makin dekat 0 makin baik"},
    "mar": {"nama": "Return per risiko (MAR)", "satuan": "", "arah": 1},
    "net": {"nama": "Untung bersih per transaksi", "satuan": "%", "arah": 1},
    "trade": {"nama": "Jumlah transaksi", "satuan": "", "arah": 0, "ket": "bukan menang-kalah, tanda besar-kecilnya sampel"},
}


def m(id_, **nilai):
    return {"id": id_, **METRIK[id_], "nilai": nilai}


AWAM = {
    "H14": {
        "kode": ["H14a", "H14b"],
        "pertanyaan": "Kalau Follow Tren hanya membeli saham yang perusahaannya sedang untung dan labanya tumbuh, apakah hasilnya jadi lebih baik?",
        "jawaban": {
            "H14a": "Tidak. Di saham syariah, saringan laba memotong return dari 30,3% menjadi 14,7% per tahun, dan untung per transaksi ikut turun. Di saham non-syariah memang sedikit membantu, tapi syaratnya harus menang di keduanya.",
            "H14b": "Tidak. Risikonya memang turun (penurunan terdalam -19,9% vs -37,7%), tapi return per tahun turun jauh lebih banyak (12,7% vs 30,3%). Angka bagus di saham non-syariah hanya berasal dari 28 transaksi.",
        },
        "cara": [
            "Ambil semua sinyal beli Follow Tren: saham yang menembus harga tertinggi 1 tahun.",
            "Untuk tiap sinyal, buka laporan keuangan terakhir yang sudah terbit sebelum hari itu, jadi tidak mengintip masa depan.",
            "H14a: sinyal hanya diambil kalau laba tahun berjalan positif dan lebih besar dari periode yang sama tahun lalu. H14b: ditambah syarat pendapatan juga naik.",
            "Jalankan portofolio dengan aturan yang persis sama (maks 10 saham @10%, stop 3×ATR, biaya ±1,2%), lalu bandingkan dengan Follow Tren tanpa saringan.",
        ],
        "pembanding": "Follow Tren biasa (H11a) di data dan periode yang sama. H14 hanya menambah saringan, jadi pertanyaannya: apakah saringan itu membuat strategi lebih baik?",
        "syarat": "Diadopsi hanya kalau untung bersih per transaksi DAN return per risiko (MAR) lebih tinggi dari Follow Tren biasa, di kedua kelompok data. Syarat ini ditulis sebelum uji dijalankan.",
        "pelaku": [
            {"id": "H11a", "nama": "Follow Tren biasa", "pembanding": True},
            {"id": "H14a", "nama": "+ laba tumbuh"},
            {"id": "H14b", "nama": "+ laba & pendapatan tumbuh"},
        ],
        "kelompok": [
            {"nama": "Saham syariah 2020-2026", "ket": "Kelompok yang kita pakai sungguhan. Data ini sudah dipakai menilai Follow Tren, jadi sifatnya pendukung.",
             "metrik": [m("cagr", H11a=30.3, H14a=14.7, H14b=12.7), m("dd", H11a=-37.7, H14a=-25.9, H14b=-19.9),
                        m("mar", H11a=0.80, H14a=0.57, H14b=0.64), m("net", H11a=6.21, H14a=5.85, H14b=6.32),
                        m("trade", H11a=375, H14a=335, H14b=289)]},
            {"nama": "Saham non-syariah 2020-2026 (Set A)", "ket": "Data segar yang belum pernah dipakai: penilaian utama. Bank otomatis tersaring di H14b karena laporannya tidak punya baris pendapatan.",
             "metrik": [m("cagr", H11a=4.0, H14a=4.4, H14b=4.1), m("dd", H11a=-28.1, H14a=-21.3, H14b=-3.4),
                        m("mar", H11a=0.14, H14a=0.21, H14b=1.21), m("net", H11a=2.05, H14a=2.52, H14b=10.25),
                        m("trade", H11a=164, H14a=127, H14b=28)]},
        ],
        "arti": [
            "Saham yang sedang tren kuat sering belum terlihat bagus di laporan keuangan. Saringan laba/pendapatan ikut membuang sebagian saham yang naiknya paling tinggi.",
            "Menurunkan risiko bisa dilakukan lebih murah: separuh modal di Follow Tren biasa, separuh di sukuk/RD ±5%. Hitungan kasar: return sekitar 17 sampai 18% per tahun dengan penurunan terdalam sekitar 19%, lebih baik dari H14b. Ini bukan hasil uji.",
            "Return 4%/th di saham non-syariah (semua versi) masih di bawah reksa dana pasar uang. Kemenangan H14b di sana tidak berarti banyak.",
            "Lapisan Apresiasi modal memang menerima penurunan sampai -40%. Menukar return besar dengan risiko lebih kecil bukan yang dicari di lapisan ini.",
        ],
        "istilah": ["cagr", "dd", "mar", "net", "trade", "set_a", "des", "ytd"],
    },
}

AWAM["H25"] = {
    "kode": ["H25"],
    "pertanyaan": "Kalau direksi atau komisaris membeli saham perusahaannya sendiri dengan uang pribadi (bukan karena wajib atau program rutin), apakah saham itu dalam 3 bulan naik lebih tinggi dari saham syariah lain?",
    "jawaban": "Tidak terbukti. Rata-ratanya memang terlihat bagus (untung bersih +8% per trade, +6% di atas pembanding), tapi lebih dari separuh trade justru kalah dari pasar. Hasil bagus itu datang dari segelintir saham yang melonjak besar di 2024; tanpa 10 trade terbaik, hasilnya -6%.",
    "cara": [
        "Kumpulkan semua laporan transaksi direksi/komisaris di IDX Jul 2023 - Des 2024 (dibaca otomatis dari ±9.000 PDF).",
        "Ambil yang membeli bersih minimal Rp100 juta, buang pembelian wajib/rutin (remunerasi bank, MESOP, tantiem, repo, tabungan saham), dan buang laporan yang angkanya tidak konsisten.",
        "Hanya saham syariah yang cukup ramai (nilai transaksi ≥ Rp1 M/hari). Beli di harga pembukaan sehari setelah laporan terbit di IDX, jual 3 bulan kemudian. Biaya ±1,2%.",
        "Bandingkan dengan rata-rata semua saham syariah likuid yang dibeli di hari yang sama, lalu cek apakah hasilnya tahan kalau beberapa trade terbaik dibuang.",
    ],
    "pembanding": "Rata-rata semua saham syariah likuid di hari yang sama dan jendela 3 bulan yang sama. Jadi yang diukur adalah ikut orang dalam vs beli saham syariah apa saja di hari itu.",
    "syarat": "Lulus kalau minimal 60 trade, untung setelah biaya, mengalahkan pembanding, lebih baik dari 95% pilihan acak, tetap menang di uji bootstrap, tetap menang tanpa 10 trade terbaik dan tanpa 5 emiten terbaik, dan menang di minimal 60% kuartal. Ditulis sebelum harga dilihat.",
    "pelaku": [
        {"id": "H25", "nama": "ikut beli orang dalam"},
        {"id": "Pasar", "nama": "saham syariah likuid hari sama", "pembanding": True},
    ],
    "kelompok": [
        {"nama": "Dev: laporan Jul 2023 - Des 2024", "ket": "98 trade di 64 emiten. Rata-rata bisa ditarik segelintir trade besar; median menunjukkan trade yang biasa.",
         "metrik": [
             {"id": "net", "nama": "Untung bersih rata-rata per trade", "satuan": "%", "arah": 1, "nilai": {"H25": 8.04, "Pasar": 1.97}},
             {"id": "net_median", "nama": "Selisih vs pasar, trade di tengah (median)", "satuan": "%", "arah": 0, "ket": "negatif = trade biasa kalah dari pasar", "nilai": {"H25": -2.81, "Pasar": None}},
             {"id": "net_tanpa10", "nama": "Selisih vs pasar tanpa 10 trade terbaik", "satuan": "%", "arah": 0, "nilai": {"H25": -6.27, "Pasar": None}},
         ]},
        {"nama": "Siapa yang membeli (laporan, bukan bukti)", "ket": "Dilihat setelah hasil dan sampelnya kecil, jadi tidak boleh dijadikan aturan baru tanpa uji baru.",
         "metrik": [
             {"id": "net_direksi", "nama": "Direksi (66 trade): untung bersih", "satuan": "%", "arah": 1, "nilai": {"H25": 1.59, "Pasar": 1.32}},
             {"id": "net_komisaris", "nama": "Komisaris (32 trade): untung bersih", "satuan": "%", "arah": 1, "nilai": {"H25": 21.34, "Pasar": 3.31}},
         ]},
    ],
    "arti": [
        "Ikut membeli setelah direksi/komisaris membeli tidak memberi keunggulan yang bisa diandalkan: 53% trade kalah dari sekadar membeli saham syariah lain di hari yang sama.",
        "Rata-rata +8% datang dari beberapa saham yang melonjak di 2024 (CUAN, PTRO, SSIA, RAJA, LABA). Kalau saat itu kebetulan tidak ikut membeli saham-saham tersebut, hasilnya rugi.",
        "Pembelian oleh komisaris terlihat jauh lebih bagus dari direksi, tapi hanya 32 trade dan kemungkinan berasal dari saham grup yang sama. Itu temuan setelah melihat hasil, jadi bukan bukti.",
        "Data orang dalam tetap berguna sebagai informasi di halaman Emiten, tapi bukan sinyal beli. Sesuai aturan, uji ditutup tanpa varian; data 2025-2026 tidak dibuka.",
    ],
    "istilah": ["net", "trade"],
}

KODE_AWAM = {k: id_ for id_, x in AWAM.items() for k in x["kode"]}


def _awam(kode):
    x = AWAM.get(KODE_AWAM.get(kode))
    if not x:
        return None
    jawab = x["jawaban"]
    return {**{k: v for k, v in x.items() if k not in ("jawaban", "istilah")},
            "jawaban": jawab.get(kode) if isinstance(jawab, dict) else jawab,
            "istilah": [{"id": i, "nama": ISTILAH[i][0], "arti": ISTILAH[i][1]} for i in x.get("istilah", [])]}


def untuk(kode):
    baris = _baris()
    bagian = [x for x in (_potong(baris, m, h) for m, h in BAGIAN.get(kode, [])) if x]
    return {"kode": kode, "berkas": NAMA_BERKAS, "bagian": bagian, "awam": _awam(kode)}
