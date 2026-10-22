import numpy as np

BATAS_BUBAR = 10e9
AUM_KECIL = 25e9
AUM_BESAR = 1e12
ETF_SEPI = 50e6
ETF_LUAR_KECIL = 50e6
ETF_LUAR_BESAR = 1e9
CATATAN = ("Kesimpulan disusun otomatis dari data historis dengan aturan tetap, dibandingkan dengan produk sekategori. "
           "Kinerja masa lalu tidak menjamin hasil di masa depan, dan belum terbukti bahwa produk unggul tahun ini akan tetap unggul. "
           "Informasi ini bukan nasihat keuangan.")


def pct(v, d=2, tanda=True):
    if v is None:
        return "–"
    s = f"{v:+.{d}f}" if tanda else f"{v:.{d}f}"
    return s.replace(".", ",") + "%"


def uang(v, mu="IDR"):
    if v is None:
        return "–"
    a = abs(v)
    if mu == "IDR":
        for batas, akhiran in ((1e12, " T"), (1e9, " M"), (1e6, " jt")):
            if a >= batas:
                return f"Rp{v / batas:.1f}".replace(".", ",") + akhiran
        return f"Rp{v:,.0f}".replace(",", ".")
    simbol = {"USD": "US$", "GBP": "£", "GBp": "£", "EUR": "€"}.get(mu, mu + " ")
    for batas, akhiran in ((1e9, " miliar"), (1e6, " juta")):
        if a >= batas:
            return f"{simbol}{v / batas:.1f}".replace(".", ",") + akhiran
    return f"{simbol}{v:,.0f}".replace(",", ".")


def persentil(v, nilai, naik_baik=True):
    x = [z for z in nilai if z is not None and np.isfinite(z)]
    if v is None or len(x) < 5:
        return None
    lebih = sum(1 for z in x if (z < v if naik_baik else z > v))
    return lebih / len(x) * 100


def median(nilai):
    x = [z for z in nilai if z is not None and np.isfinite(z)]
    return float(np.median(x)) if x else None


def poin(judul, teks):
    return {"judul": judul, "teks": teks}


def putusan(skor, kritis, kekuatan, kelemahan):
    if skor is None:
        nilai = "Belum dapat dinilai"
    elif skor >= 70:
        nilai = "Bagus"
    elif skor >= 40:
        nilai = "Cukup"
    else:
        nilai = "Kurang"
    if kritis and nilai in ("Bagus", "Cukup"):
        nilai = "Cukup" if nilai == "Bagus" else "Kurang"
    if nilai == "Bagus" and len(kelemahan) >= 2 and len(kelemahan) >= len(kekuatan):
        nilai = "Cukup"
    return nilai, {"Bagus": "naik", "Cukup": "kuning", "Kurang": "turun"}.get(nilai, "netral")


def kalimat(nilai, kekuatan, waspada, kelemahan, dasar):
    awal = {"Bagus": "Secara keseluruhan produk ini tergolong bagus dibandingkan produk sejenis",
            "Cukup": "Secara keseluruhan produk ini tergolong cukup dibandingkan produk sejenis",
            "Kurang": "Secara keseluruhan produk ini tergolong kurang menarik dibandingkan produk sejenis",
            "Belum dapat dinilai": "Data produk ini belum cukup untuk dinilai secara menyeluruh"}[nilai]
    bagian = [f"{awal} ({dasar})."]
    if kekuatan:
        bagian.append("Keunggulan utamanya: " + ", ".join(k["judul"].lower() for k in kekuatan[:3]) + ".")
    if kelemahan:
        bagian.append("Kekurangannya: " + ", ".join(k["judul"].lower() for k in kelemahan[:3]) + ".")
    if not kekuatan and not kelemahan:
        bagian.append("Tidak ada indikator yang menonjol, baik di atas maupun di bawah produk sekategori.")
    if waspada:
        bagian.append(f"Terdapat {len(waspada)} hal yang perlu diperhatikan sebelum membeli.")
    return " ".join(bagian)


def reksadana(x, sekategori, etf=None):
    kat = x.get("kategori_label", "").lower()
    n = len(sekategori)
    pu = x.get("kategori") == "pasar_uang"
    mu = x.get("mata_uang") or "IDR"
    kekuatan, waspada, kelemahan = [], [], []
    kritis = False
    kol = lambda k: [z.get(k) for z in sekategori]

    r1 = x.get("ret_1th")
    p = persentil(r1, kol("ret_1th"))
    m = median(kol("ret_1th"))
    if p is not None and p >= 75:
        kekuatan.append(poin("Imbal hasil 1 tahun tinggi", f"{pct(r1)} dalam 12 bulan terakhir, lebih tinggi dari {p:.0f}% produk {kat} (median {pct(m)})."))
    elif p is not None and p <= 25:
        kelemahan.append(poin("Imbal hasil 1 tahun rendah", f"{pct(r1)} dalam 12 bulan terakhir, hanya lebih baik dari {p:.0f}% produk {kat} (median {pct(m)})."))
    if r1 is not None and r1 < 0:
        waspada.append(poin("Imbal hasil 1 tahun negatif", f"Nilai investasi turun {pct(abs(r1), 2, False)} dalam 12 bulan terakhir." + (" Kondisi ini sejalan dengan penurunan IHSG pada periode yang sama." if x.get("kategori") in ("saham", "indeks", "campuran") else "")))

    cs = x.get("cagr_semua")
    th = x.get("tahun_data")
    if cs is not None and th and th >= 3:
        ps = persentil(cs, [z.get("cagr_semua") for z in sekategori if (z.get("tahun_data") or 0) >= 3])
        ms = median([z.get("cagr_semua") for z in sekategori if (z.get("tahun_data") or 0) >= 3])
        if ps is not None and ps >= 75:
            kekuatan.append(poin("Pertumbuhan jangka panjang kuat", f"CAGR {pct(cs)} per tahun selama {str(th).replace('.', ',')} tahun, di atas {ps:.0f}% produk {kat} yang berumur minimal 3 tahun (median {pct(ms)})."))
        elif ps is not None and ps <= 25:
            kelemahan.append(poin("Pertumbuhan jangka panjang lemah", f"CAGR {pct(cs)} per tahun selama {str(th).replace('.', ',')} tahun, di bawah {100 - ps:.0f}% produk {kat} sejenis (median {pct(ms)})."))
    if th is not None and th < 3:
        waspada.append(poin("Riwayat masih pendek", f"Data kinerja baru {str(th).replace('.', ',')} tahun, sehingga ketahanan produk pada kondisi pasar yang berbeda belum teruji."))

    pj = x.get("panjang") or {}
    if pj.get("tahun_dihitung", 0) >= 5:
        rasio = pj["tahun_naik"] / pj["tahun_dihitung"]
        if rasio >= 0.8:
            kekuatan.append(poin("Konsisten dari tahun ke tahun", f"Imbal hasil positif pada {pj['tahun_naik']} dari {pj['tahun_dihitung']} tahun kalender."))
        elif rasio < 0.5:
            kelemahan.append(poin("Kinerja tahunan tidak konsisten", f"Imbal hasil positif hanya pada {pj['tahun_naik']} dari {pj['tahun_dihitung']} tahun kalender."))

    if not pu:
        dd = x.get("dd")
        pd_ = persentil(dd, kol("dd"))
        md = median(kol("dd"))
        if pd_ is not None and pd_ >= 75:
            kekuatan.append(poin("Penurunan terkendali", f"Max drawdown 1 tahun {pct(dd)}, lebih kecil dari {pd_:.0f}% produk {kat} (median {pct(md)})."))
        elif pd_ is not None and pd_ <= 25:
            kelemahan.append(poin("Penurunan lebih dalam", f"Max drawdown 1 tahun {pct(dd)}, lebih dalam dari {100 - pd_:.0f}% produk {kat} (median {pct(md)})."))
        if pj.get("dd") is not None and pj["dd"] <= -20:
            waspada.append(poin("Pernah turun dalam", f"Sepanjang riwayatnya NAV/Unit pernah turun {pct(abs(pj['dd']), 1, False)} dari titik tertinggi (data akhir bulan). Siapkan horizon investasi panjang."))

    b = x.get("biaya")
    pb = persentil(b, kol("biaya"), naik_baik=False)
    mb = median(kol("biaya"))
    if pb is not None and pb >= 75:
        kekuatan.append(poin("Biaya rendah", f"Expense ratio {pct(b, 2, False)} per tahun, lebih murah dari {pb:.0f}% produk {kat} (median {pct(mb, 2, False)})."))
    elif pb is not None and pb <= 25:
        kelemahan.append(poin("Biaya tinggi", f"Expense ratio {pct(b, 2, False)} per tahun, lebih mahal dari {100 - pb:.0f}% produk {kat} (median {pct(mb, 2, False)}). Biaya ini mengurangi imbal hasil setiap tahun."))
    elif b is None:
        waspada.append(poin("Expense ratio tidak tersedia", "Data biaya tahunan belum dipublikasikan; periksa prospektus atau fund fact sheet."))

    aum = x.get("aum")
    aum_rp = aum * (x.get("aum_mi_kurs") or 0) if mu == "USD" and aum else aum
    if aum_rp:
        if aum_rp >= AUM_BESAR:
            kekuatan.append(poin("Dana kelolaan besar", f"AUM {uang(aum, mu)}, termasuk produk besar sehingga risiko pembubaran kecil."))
        elif aum_rp < BATAS_BUBAR:
            kritis = True
            waspada.append(poin("AUM di bawah batas OJK", f"AUM {uang(aum, mu)}, di bawah Rp10 M. Reksa dana dengan dana kelolaan di bawah Rp10 M selama 120 hari bursa wajib dibubarkan (POJK 23/2016)."))
        elif aum_rp < AUM_KECIL:
            waspada.append(poin("Dana kelolaan kecil", f"AUM {uang(aum, mu)}, relatif dekat dengan batas pembubaran OJK Rp10 M."))
    au = x.get("aum_ubah")
    if au is not None and au <= -20:
        waspada.append(poin("Dana keluar besar", f"AUM turun {pct(abs(au), 1, False)} dibanding bulan sebelumnya, menandakan penarikan dana investor yang signifikan."))

    if x.get("nav_beku"):
        kritis = True
        waspada.append(poin("NAV hampir tidak bergerak", "NAV/Unit hampir tidak pernah berubah, sehingga kinerjanya tidak dapat dinilai dengan wajar."))
    if x.get("nav_lama"):
        kritis = True
        waspada.append(poin("NAV belum diperbarui", f"NAV terakhir tercatat {x.get('nav_tgl')}; data produk ini kemungkinan tidak aktif dipublikasikan."))
    if mu == "USD":
        waspada.append(poin("Risiko nilai tukar", "Produk berdenominasi dolar AS; nilai dalam rupiah ikut naik-turun mengikuti kurs."))
    rs = x.get("risiko")
    if rs is not None and rs >= 7:
        waspada.append(poin("Tingkat risiko tinggi", f"Klasifikasi risiko {int(rs)} dari 9. Sesuai untuk horizon investasi minimal 5 tahun dan toleransi penurunan modal."))
    besar = max((a.get("bobot") or 0 for a in x.get("aset") or []), default=0)
    if besar >= 20:
        nama = next(a["nama"] for a in x["aset"] if (a.get("bobot") or 0) == besar)
        waspada.append(poin("Konsentrasi pada satu efek", f"{nama} mencapai {pct(besar, 1, False)} portofolio, sehingga kinerja sangat bergantung pada satu penerbit."))

    if etf:
        nt = etf.get("nilai_transaksi")
        if nt is not None and nt < ETF_SEPI:
            waspada.append(poin("Likuiditas rendah di bursa", f"Rata-rata transaksi {uang(nt)} per hari (20 hari terakhir). Pembelian atau penjualan dalam jumlah besar dapat sulit dilakukan di harga wajar."))
        elif nt is not None and nt >= 1e9:
            kekuatan.append(poin("Likuid di bursa", f"Rata-rata transaksi {uang(nt)} per hari, mudah dibeli dan dijual."))
        h, nav = etf.get("harga"), x.get("nav")
        if h and nav:
            sel = (h / nav - 1) * 100
            if abs(sel) >= 2:
                waspada.append(poin("Harga bursa menyimpang dari NAV", f"Harga bursa terakhir {h:,.0f} dibanding NAV/Unit {nav:,.2f} ({pct(sel, 1)}). Pastikan harga beli tidak jauh di atas NAV.".replace(",", ".")))

    skor = x.get("skor")
    nilai, nada = putusan(skor, kritis, kekuatan, kelemahan)
    if skor is not None:
        dasar = f"skor {round(skor)} dari 100, peringkat {int(x.get('peringkat') or 0)} dari {int(x.get('jumlah_kategori') or 0)} produk {kat}"
    elif x.get("nav_beku"):
        dasar = "NAV/Unit tidak bergerak sehingga skor tidak dihitung"
    elif (x.get("titik") or 0) < 200:
        dasar = f"riwayat NAV harian baru {x.get('titik') or 0} hari bursa, minimal 200 hari untuk dihitung skornya"
    else:
        dasar = f"produk sekategori yang dapat dibandingkan kurang dari 3; dibandingkan {n} produk {kat}"
    return {"nilai": nilai, "nada": nada, "ringkasan": kalimat(nilai, kekuatan, waspada, kelemahan, dasar),
            "kekuatan": kekuatan, "waspada": waspada, "kelemahan": kelemahan, "catatan": CATATAN}


def etf_luar(x, semua):
    kelas = x.get("kelas")
    peer = [z for z in semua if z.get("kelas") == kelas and z.get("syariah")]
    nama_kelas = {"saham": "ETF saham syariah", "sukuk": "ETF sukuk", "emas": "ETF emas"}.get(kelas, f"ETF {kelas} syariah")
    mu = x.get("mata_uang") or "USD"
    kekuatan, waspada, kelemahan = [], [], []
    kritis = False
    kol = lambda k: [z.get(k) for z in peer]
    bobot, total = 0.0, 0.0

    def nilai_peringkat(v, k, naik_baik, w):
        nonlocal bobot, total
        p = persentil(v, kol(k), naik_baik)
        if p is not None:
            total += p * w
            bobot += w
        return p

    ck = "cagr_5th" if x.get("cagr_5th") is not None else "cagr_semua"
    lbl = "5 tahun" if ck == "cagr_5th" else f"{str(x.get('tahun_data')).replace('.', ',')} tahun"
    c = x.get(ck)
    p = nilai_peringkat(c, ck, True, 0.4)
    m = median(kol(ck))
    if p is not None and p >= 75:
        kekuatan.append(poin("Pertumbuhan tinggi", f"CAGR {pct(c)} per tahun ({lbl}, dalam {mu}), di atas {p:.0f}% {nama_kelas} pembanding (median {pct(m)})."))
    elif p is not None and p <= 25:
        kelemahan.append(poin("Pertumbuhan rendah", f"CAGR {pct(c)} per tahun ({lbl}), di bawah {100 - p:.0f}% {nama_kelas} pembanding (median {pct(m)})."))

    dd = x.get("dd_2020") if x.get("dd_2020") is not None else x.get("dd_semua")
    p = nilai_peringkat(dd, "dd_2020", True, 0.25)
    if p is not None and p >= 75:
        kekuatan.append(poin("Penurunan terkendali", f"Max drawdown sejak 2020 {pct(dd, 1)}, lebih kecil dari {p:.0f}% pembanding."))
    elif p is not None and p <= 25:
        kelemahan.append(poin("Penurunan lebih dalam", f"Max drawdown sejak 2020 {pct(dd, 1)}, lebih dalam dari {100 - p:.0f}% pembanding."))
    if dd is not None and dd <= -30:
        waspada.append(poin("Pernah turun dalam", f"Harga pernah turun {pct(abs(dd), 1, False)} dari titik tertinggi. Siapkan horizon investasi minimal 5 tahun."))

    b = x.get("biaya")
    p = nilai_peringkat(b, "biaya", False, 0.2)
    mb = median(kol("biaya"))
    if p is not None and p >= 75:
        kekuatan.append(poin("Biaya rendah", f"Expense ratio {pct(b, 2, False)} per tahun, lebih murah dari {p:.0f}% pembanding (median {pct(mb, 2, False)})."))
    elif p is not None and p <= 25:
        kelemahan.append(poin("Biaya tinggi", f"Expense ratio {pct(b, 2, False)} per tahun, lebih mahal dari {100 - p:.0f}% pembanding (median {pct(mb, 2, False)})."))

    aum = x.get("aum")
    nilai_peringkat(aum, "aum", True, 0.15)
    if aum:
        if aum >= ETF_LUAR_BESAR:
            kekuatan.append(poin("Dana kelolaan besar", f"AUM {uang(aum, mu)}, ETF besar dan mapan."))
        elif aum < ETF_LUAR_KECIL:
            waspada.append(poin("Dana kelolaan kecil", f"AUM {uang(aum, mu)}. ETF kecil lebih berisiko ditutup penerbitnya dan umumnya kurang likuid."))

    th = x.get("tahun_data")
    if th is not None and th < 3:
        waspada.append(poin("Riwayat masih pendek", f"Data harga baru {str(th).replace('.', ',')} tahun."))
    sek = x.get("sektor_bobot") or []
    if sek and sek[0]["bobot"] >= 35:
        waspada.append(poin("Terkonsentrasi pada satu sektor", f"Sektor {sek[0]['nama'].lower()} mencapai {pct(sek[0]['bobot'], 1, False)} portofolio."))
    if mu != "IDR":
        waspada.append(poin("Risiko nilai tukar", f"Diperdagangkan dalam {mu}; nilai dalam rupiah ikut naik-turun mengikuti kurs."))
    if x.get("bursa") != "London" and (x.get("dividen_yield12") or 0) > 0:
        waspada.append(poin("Pajak dividen AS", "Dividen dipotong pajak 30% di AS, atau 15% dengan formulir W-8BEN."))

    if not x.get("syariah"):
        kritis = True
        kelemahan.insert(0, poin("Tidak sesuai syariah", "ETF ini tidak memakai saringan syariah; isinya dapat mencakup bank konvensional, asuransi, alkohol, atau usaha lain yang tidak sesuai syariah. Hanya untuk pembanding."))

    skor = total / bobot if bobot >= 0.6 else None
    nilai, nada = putusan(skor, kritis, kekuatan, kelemahan)
    if not x.get("syariah"):
        nilai, nada = "Tidak sesuai syariah", "turun"
    dasar = (f"nilai gabungan {round(skor)} dari 100 dibanding {len(peer)} {nama_kelas}: pertumbuhan 40%, drawdown 25%, biaya 20%, AUM 15%"
             if skor is not None else "data pembanding belum cukup")
    ringkas = kalimat(nilai if nilai in ("Bagus", "Cukup", "Kurang", "Belum dapat dinilai") else "Kurang", kekuatan, waspada, kelemahan, dasar)
    if not x.get("syariah"):
        ringkas = "ETF ini tidak memakai saringan syariah sehingga tidak sesuai dengan tujuan investasi syariah. " + ringkas
    return {"nilai": nilai, "nada": nada, "ringkasan": ringkas, "kekuatan": kekuatan, "waspada": waspada, "kelemahan": kelemahan,
            "catatan": CATATAN + " Nilai gabungan ETF luar negeri bersifat deskriptif dan belum diuji sebagai aturan pemilihan."}
