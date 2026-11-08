from datetime import date

import pandas as pd

from backend.app.services.reksadana import bersih
from backend.db import data as dt

SUMBER = {"indeks": "indeks JII + saham syariah global (DJIM Titans 100 → MSCI World Islamic), bukan produk",
          "kategori": "rata-rata semua RD saham syariah sejenis, termasuk yang bubar",
          "keranjang": "keranjang produk di halaman ini (bulan sebelum produk ada diisi rata-rata RD sejenis)"}
NAMA_APLIKASI = {"bibit": "Bibit", "makmur": "Makmur", "ajaib": "Ajaib"}
CATATAN_GLOBAL = "Satu produk berisi ratusan saham global; dana disimpan di bank kustodian, bukan di MI."
SETOR_RATA_MIN = 100_000
SETORAN_CONTOH = 1_000_000


def _hasil():
    return dt.baca_hasil("pertumbuhan")


def _sumber(h):
    lbl = (h.get("info_kategori") or {}).get("label_global")
    kat = SUMBER["kategori"] if not lbl else f"Indonesia: rata-rata semua RD saham syariah sejenis (termasuk yang bubar); global: {lbl}"
    return {**SUMBER, "kategori": kat}


def _kinerja():
    from backend.app.services import reksadana as rdn
    return {int(r["id"]): {"ret_1th": r.get("ret_1th"), "cagr_3": r.get("cagr_3_rp"), "cagr_5": r.get("cagr_5_rp"), "turun_terburuk": r.get("turun_terburuk_rp"),
                           "tahun_data": r.get("tahun_data"), "untung_12bln": r.get("untung_12bln")} for r in rdn.daftar()["data"]}


def _kandidat(h, aplikasi):
    return {"indeks": h["jalur"]["indeks"], "kategori": h["jalur"]["kategori"], "keranjang": (h.get("keranjang") or {}).get(aplikasi)}


def _rentang(h, aplikasi, setoran, modal):
    from backend.research import keranjang_pertumbuhan as kp
    kand = _kandidat(h, aplikasi)
    out = {}
    for t in ("5", "10"):
        src = h["pakai"][aplikasi].get(t)
        if not src:
            out[t] = None
            continue
        x = kand[src][t]
        r = kp.ringkas_sip(x, setoran, modal)
        per = h["periode"]["indeks" if src == "indeks" else "kategori"]
        deret = [{"mulai": m, "nilai": modal * g + setoran * f} for m, f, g in zip(x["mulai"], x["f"], x["g"])]
        out[t] = {**r, "sumber": src, "sumber_teks": _sumber(h)[src], "periode": per, "tahun": int(t), "deret": deret}
    return out


def _risiko(skala):
    from backend.app.services.penarikan import label_risiko
    if skala is None:
        return {"risiko": "Tinggi", "risiko_skala": None, "risiko_sumber": "jenis"}
    return {"risiko": label_risiko(skala), "risiko_skala": skala, "risiko_sumber": "resmi"}


def _kartu(c, nilai, catatan=None, kinerja=None):
    return {"kinerja": (kinerja or {}).get(c.get("id")), **{k: c.get(k) for k in ("id", "nama", "mi", "wadah", "kategori", "mata_uang", "biaya", "aum", "tahun_data", "min_beli_mi", "min_beli_nilai",
                                       "min_beli_uang", "cek_aplikasi", "platform")}, "nilai": nilai, "catatan": catatan, **_risiko(c.get("risiko_skala"))}


def _aplikasi_cukup(dok, kecuali=None):
    per = dok.get("per_aplikasi") or {}
    return [NAMA_APLIKASI[a] for a in ("bibit", "makmur", "ajaib") if a != kecuali and per.get(a, {}).get("LK", 0) >= 3 and per.get(a, {}).get("GL_disetujui", 0) >= 1]


def _cakupan(produk):
    himpunan = [{p["kode"] for p in c["platform"]} for c in produk]
    if not himpunan:
        return {"jenis": "kosong", "aplikasi": []}
    sama = set.intersection(*himpunan)
    if sama:
        urut = [a for a in ("bibit", "makmur", "ajaib") if a in sama]
        return {"jenis": "satu", "aplikasi": [NAMA_APLIKASI[a] for a in urut]}
    sisa, pakai = list(range(len(himpunan))), []
    while sisa:
        terbaik = max(("bibit", "makmur", "ajaib"), key=lambda a: sum(1 for i in sisa if a in himpunan[i]))
        pakai.append(terbaik)
        sisa = [i for i in sisa if terbaik not in himpunan[i]]
    return {"jenis": "banyak", "aplikasi": [NAMA_APLIKASI[a] for a in pakai]}


def _giliran(lk, gl):
    urut = []
    for i, c in enumerate(lk):
        urut.append(c)
        if gl:
            urut.append(gl[i % len(gl)])
    return urut


def rencana(setoran=SETORAN_CONTOH, modal_awal=0, aplikasi="semua"):
    from backend.research import keranjang_pertumbuhan as kp
    aplikasi = aplikasi if aplikasi in kp.APLIKASI else "semua"
    h = _hasil()
    dok = kp.terbaru(aplikasi)
    if h is None or dok is None:
        return {"ada": False}
    setoran, modal = max(float(setoran or 0), 0.0), max(float(modal_awal or 0), 0.0)
    lk, gl = dok["isi"]["LK"], dok["isi"]["GL"]
    w = kp.BOBOT_LOKAL
    bagian = {"LK": setoran * w, "GL": setoran * (1 - w)}
    per_lk = bagian["LK"] / len(lk) if lk else 0.0
    per_gl = bagian["GL"] / len(gl) if gl else 0.0
    catatan_gl = CATATAN_GLOBAL if len(gl) == 1 else None
    kin = _kinerja()
    peringatan = []
    if not gl:
        if aplikasi in ("makmur", "ajaib"):
            peringatan.append({"jenis": "global_aplikasi", "teks": "Bagian global belum tersedia di aplikasi ini, gunakan Bibit untuk porsi global.",
                               "saran": _aplikasi_cukup(dok, aplikasi)})
        else:
            peringatan.append({"jenis": "global_kosong", "teks": "Keranjang global kosong karena produk global gagal saringan. Calon pengganti di bawah belum dipilih; keputusan ada di pemilik halaman.",
                               "calon": [{k: c.get(k) for k in ("id", "nama", "mi", "alasan", "platform")} for c in dok.get("pengganti_global") or []
                                         if not any(str(x).startswith("ditolak") for x in c.get("alasan") or [])]})
    if len(lk) < kp.JUMLAH["LK"]:
        peringatan.append({"jenis": "lokal_kurang", "teks": f"Hanya {len(lk)} RD saham syariah Indonesia yang lolos di aplikasi ini.", "saran": _aplikasi_cukup(dok, aplikasi)})
    produk = lk + gl
    rata = bool(produk) and min([per_lk] * len(lk) + [per_gl] * len(gl)) >= SETOR_RATA_MIN
    bulan_ini = pd.Timestamp(date.today()).to_period("M")
    if rata or not produk:
        beli = [_kartu(c, per_lk, None, kin) for c in lk] + [_kartu(c, per_gl, catatan_gl, kin) for c in gl]
        jadwal_setor = None
    else:
        urut = _giliran(lk, gl)
        i0 = (bulan_ini.month - 1) % len(urut)
        jadwal_setor = [{"bulan": str(bulan_ini + j), "id": urut[(i0 + j) % len(urut)]["id"], "nama": urut[(i0 + j) % len(urut)]["nama"], "nilai": setoran}
                        for j in range(len(urut))]
        ini = urut[i0]["id"]
        beli = [_kartu(c, setoran if c["id"] == ini else 0.0, None, kin) for c in lk] + [_kartu(c, setoran if c["id"] == ini else 0.0, catatan_gl, kin) for c in gl]
    awal = None
    if modal > 0:
        awal = {"total": modal, "lokal_per_produk": modal * w / len(lk) if lk else 0.0, "global_per_produk": modal * (1 - w) / len(gl) if gl else 0.0,
                "global_tanpa_produk": modal * (1 - w) if not gl else 0.0}
    cd = h["contoh_desember"]
    nl, ng = setoran * cd["lokal"], setoran * cd["global"]
    tot = nl + ng
    desember = {"tahun": cd["tahun"], "lokal": nl, "global": ng, "total": tot, "target": tot * w, "pindah": abs(nl - tot * w),
                "dari": "lokal" if nl > tot * w else "global", "ke": "global" if nl > tot * w else "lokal", "setoran_total": setoran * cd["setoran_bulan"], "sumber": cd["sumber"]}
    return bersih({"ada": True, "masukan": {"setoran": setoran, "modal_awal": modal, "aplikasi": aplikasi}, "dibentuk": dok["dibentuk"].isoformat(timespec="minutes"),
                   "isi": {"lokal": [_kartu(c, per_lk, None, kin) for c in lk], "global": [_kartu(c, per_gl, catatan_gl, kin) for c in gl]},
                   "bagian": {"lokal": bagian["LK"], "global": bagian["GL"]}, "global_tanpa_produk": bagian["GL"] if not gl else 0.0,
                   "cara_setor": "rata" if rata else "bergiliran", "setor_rata_min": SETOR_RATA_MIN, "beli": beli, "jadwal_setor": jadwal_setor, "awal": awal,
                   "cakupan": _cakupan(produk), "peringatan": peringatan, "desember": desember, "rentang": _rentang(h, aplikasi, setoran, modal)})


def dasar():
    from backend.research import keranjang_pertumbuhan as kp
    h = _hasil()
    if h is None:
        return {"ada": False}
    dok = kp.terbaru("semua")
    sip = {}
    for jalur, isi in (("indeks", h["jalur"]["indeks"]), ("kategori", h["jalur"]["kategori"]), ("keranjang", (h.get("keranjang") or {}).get("semua"))):
        if isi:
            sip[jalur] = {t: kp.ringkas_sip(isi[t], SETORAN_CONTOH) for t in ("5", "10")}
    for jalur, isi in h["pembanding"].items():
        for nm, v in isi.items():
            sip[f"{jalur}_{nm}"] = {t: kp.ringkas_sip(v[t], SETORAN_CONTOH) for t in ("5", "10")}
    gugur = sorted(dok.get("gugur") or [], key=lambda c: (c["wadah"], c["nama"])) if dok else []
    return bersih({"ada": True, "dihitung": h["dihitung"].isoformat(timespec="minutes"), "periode": h["periode"], "indeks": h["indeks_h35"], "kriteria": h["kriteria_h35"],
                   "k4": h["k4_h35"], "varian": h["varian_h35"], "pecah": h["pecah_h35"], "dekade": h["dekade"], "isian": h["isian"], "pakai": h["pakai"],
                   "info_kategori": h["info_kategori"], "sip": sip, "setoran_contoh": SETORAN_CONTOH, "sumber": _sumber(h),
                   "kurva": h.get("kurva"), "versi_lama": h.get("versi_lama"), "korelasi": h.get("korelasi_h35"), "contoh_desember": h.get("contoh_desember"),
                   "keranjang": None if dok is None else {"dibentuk": dok["dibentuk"].isoformat(timespec="minutes"), "alasan": dok["alasan"], "kriteria": dok["kriteria"],
                                                          "per_aplikasi": dok.get("per_aplikasi"), "gugur": [{k: c.get(k) for k in ("id", "nama", "wadah", "alasan", "platform", "biaya")} for c in gugur],
                                                          "pengganti_global": [{k: c.get(k) for k in ("id", "nama", "alasan")} for c in dok.get("pengganti_global") or []
                                                                             if not any(str(x).startswith("ditolak") for x in c.get("alasan") or [])]}})
