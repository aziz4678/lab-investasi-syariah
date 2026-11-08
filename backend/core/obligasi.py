import pandas as pd

FREK = {"M": 12, "Q": 4, "S": 2, "A": 1}


def frek(x):
    if x.get("frek_kupon"):
        return x["frek_kupon"]
    return {"SR": 12, "PBS": 2}.get(x.get("jenis"))


def isi(x):
    f = frek(x)
    if not f or x.get("harga") is None:
        return x
    tgl = x.get("tgl_harga") or x.get("data_tgl")
    x.setdefault("ytm_pasardana", x.get("ytm"))
    x["ytm"] = ytm(x["harga"], x.get("kupon"), x.get("jatuh_tempo"), tgl, f)
    x["ytm_bersih"] = ytm_bersih(x["harga"], x.get("kupon"), x.get("jatuh_tempo"), tgl, f)
    x["tgl_harga"] = tgl
    return x


def jadwal(jatuh_tempo, tgl, frek):
    bulan = 12 // frek
    akhir = pd.Timestamp(jatuh_tempo).normalize()
    t = pd.Timestamp(tgl).normalize()
    tanggal = [akhir]
    while tanggal[-1] > t:
        tanggal.append(akhir - pd.DateOffset(months=bulan * len(tanggal)))
    sebelum = tanggal[-1]
    sesudah = sorted(x for x in tanggal if x > t)
    return sebelum, sesudah


def ytm(harga, kupon, jatuh_tempo, tgl, frek):
    if harga is None or kupon is None or jatuh_tempo is None or tgl is None or not frek or harga <= 0:
        return None
    if pd.Timestamp(jatuh_tempo) <= pd.Timestamp(tgl):
        return None
    sebelum, sesudah = jadwal(jatuh_tempo, tgl, frek)
    c = kupon * 100 / frek
    periode = (sesudah[0] - sebelum).days
    f = (sesudah[0] - pd.Timestamp(tgl).normalize()).days / periode
    kotor = harga + c * (1 - f)
    arus = [c] * len(sesudah)
    arus[-1] += 100

    def nilai(y):
        return sum(a / (1 + y / frek) ** (f + k) for k, a in enumerate(arus))

    lo, hi = -0.5, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        if nilai(m) > kotor:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def ytm_bersih(harga, kupon, jatuh_tempo, tgl, frek, pajak=0.10):
    if kupon is None:
        return None
    return ytm(harga, kupon * (1 - pajak), jatuh_tempo, tgl, frek)
