import pandas as pd

PASAR = {
    "idx": ("Asia/Jakarta", 17, 0),
    "as": ("America/New_York", 17, 0),
    "london": ("Europe/London", 17, 0),
    "24jam": ("Asia/Jakarta", 24, 0),
}


def pasar_dari_simbol(simbol):
    s = str(simbol).upper()
    if s.endswith(".JK") or s.startswith("^JK"):
        return "idx"
    if s.endswith("=X") or s.endswith("=F"):
        return "24jam"
    if s.endswith(".L"):
        return "london"
    return "as"


def batas_final(pasar, sekarang=None):
    zona, jam, menit = PASAR[pasar]
    kini = pd.Timestamp(sekarang).tz_localize(zona) if sekarang is not None else pd.Timestamp.now(tz=zona)
    hari = pd.Timestamp(kini.date())
    return hari if (kini.hour, kini.minute) < (jam, menit) else hari + pd.Timedelta(days=1)


def buang_belum_final(df, simbol, sekarang=None):
    if df is None or df.empty:
        return df
    return df[(df.index < batas_final(pasar_dari_simbol(simbol), sekarang)) & (df.index.weekday < 5)]
