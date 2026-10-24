from backend.db import data as dt


def ringkas():
    hasil = {}
    for nama in ("bi_rate", "inflasi", "bunga_antarbank"):
        df = dt.baca(f"makro/{nama}")
        if df is None or df.empty:
            continue
        s = df["nilai"].dropna()
        lalu = s[s.index <= s.index[-1] - __import__("pandas").DateOffset(years=1)]
        hasil[nama] = {"nilai": float(s.iloc[-1]), "tgl": s.index[-1].strftime("%Y-%m-%d"),
                       "setahun_lalu": float(lalu.iloc[-1]) if len(lalu) else None,
                       "seri": {"tgl": [t.strftime("%Y-%m-%d") for t in s.index], "nilai": [round(float(v), 3) for v in s]}}
    if "bi_rate" in hasil and "inflasi" in hasil:
        hasil["bunga_riil"] = round(hasil["bi_rate"]["nilai"] - hasil["inflasi"]["nilai"], 2)
    return hasil
