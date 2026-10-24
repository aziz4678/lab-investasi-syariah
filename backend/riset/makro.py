import html
import io
import re
import sys
from datetime import date, datetime

import pandas as pd
from curl_cffi import requests

from backend.db import data as dt

BULAN = {"januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "agustus": 8, "september": 9, "oktober": 10,
         "november": 11, "desember": 12}
SUMBER = {
    "bi_rate": ("https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx", ("01/04/2016", None, "%d/%m/%Y")),
    "inflasi": ("https://www.bi.go.id/id/statistik/indikator/data-inflasi.aspx", ("01/2003", None, "%m/%Y")),
}
FRED = {"bunga_antarbank": "IRSTCI01IDM156N"}


def formulir(t):
    hasil = {}
    for i in re.findall(r"<input[^>]*>", t):
        n = re.search(r'name="([^"]+)"', i)
        v = re.search(r'value="([^"]*)"', i)
        ty = re.search(r'type="([^"]+)"', i)
        if n and (not ty or ty.group(1).lower() in ("hidden", "text")):
            hasil[html.unescape(n.group(1))] = html.unescape(v.group(1)) if v else ""
    return hasil


def unduh_bi(url, mulai, akhir):
    s = requests.Session(impersonate="chrome")
    t = s.get(url, timeout=60).text
    f = formulir(t)
    pre = next(k for k in f if re.search(r"TextBoxDate(Start|From)$", k)).rsplit("$", 1)[0]
    awal = next(k for k in f if k.startswith(pre) and re.search(r"TextBoxDate(Start|From)$", k))
    ujung = next(k for k in f if k.startswith(pre) and re.search(r"TextBoxDate(End|To)$", k))
    g = dict(f)
    g[awal] = g[pre + "$HiddenFieldDateFrom"] = mulai
    g[ujung] = g[pre + "$HiddenFieldDateTo"] = akhir
    g[pre + "$ButtonExport"] = "Unduh"
    r = s.post(url, data=g, timeout=90)
    if "spreadsheet" not in (r.headers.get("content-type") or ""):
        raise RuntimeError(f"BI tidak mengirim Excel untuk {url} ({r.headers.get('content-type')})")
    return r.content


def tanggal_id(s):
    s = str(s).strip().lower()
    m = re.match(r"(\d{1,2})?\s*([a-z]+)\s+(\d{4})", s)
    if not m or m.group(2) not in BULAN:
        return None
    return pd.Timestamp(int(m.group(3)), BULAN[m.group(2)], int(m.group(1) or 1))


def persen(s):
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(s))
    return float(m.group(0).replace(",", ".")) if m else None


def baca_tabel(isi):
    d = pd.read_excel(io.BytesIO(isi), header=None)
    baris = []
    for _, r in d.iterrows():
        nilai = [x for x in r.tolist() if pd.notna(x)]
        tgl = next((tanggal_id(x) for x in nilai if isinstance(x, str) and tanggal_id(x) is not None), None)
        angka = next((persen(x) for x in nilai if isinstance(x, str) and "%" in x), None)
        if tgl is not None and angka is not None:
            baris.append((tgl, angka))
    return pd.DataFrame(baris, columns=["tgl", "nilai"]).drop_duplicates("tgl").set_index("tgl").sort_index()


def fred(seri):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={seri}", impersonate="chrome", timeout=60)
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["tgl", "nilai"]
    d["tgl"] = pd.to_datetime(d["tgl"])
    d["nilai"] = pd.to_numeric(d["nilai"], errors="coerce")
    return d.dropna().set_index("tgl")


def perbarui():
    hari = date.today()
    hasil = {}
    for nama, (url, (mulai, _, fmt)) in SUMBER.items():
        try:
            df = baca_tabel(unduh_bi(url, mulai, hari.strftime(fmt)))
            if df.empty:
                raise RuntimeError("tabel kosong")
            dt.tulis(f"makro/{nama}", df)
            hasil[nama] = df
            print(f"{nama}: {len(df)} titik, {df.index[0]:%Y-%m-%d} s/d {df.index[-1]:%Y-%m-%d}, terakhir {df['nilai'].iloc[-1]}%")
        except Exception as e:
            print(f"{nama}: GAGAL {e}")
    for nama, seri in FRED.items():
        try:
            df = fred(seri)
            dt.tulis(f"makro/{nama}", df)
            print(f"{nama} (FRED {seri}): {len(df)} titik s/d {df.index[-1]:%Y-%m}, terakhir {df['nilai'].iloc[-1]:.2f}%")
        except Exception as e:
            print(f"{nama}: GAGAL {e}")
    dt.db().makro_info.replace_one({"_id": "ringkas"}, {"_id": "ringkas", "diperbarui": datetime.now(),
                                                         **{k: {"terakhir": v.index[-1].to_pydatetime(), "nilai": float(v["nilai"].iloc[-1])} for k, v in hasil.items()}},
                                   upsert=True)


if __name__ == "__main__":
    {"perbarui": perbarui}[sys.argv[1] if len(sys.argv) > 1 else "perbarui"]()
