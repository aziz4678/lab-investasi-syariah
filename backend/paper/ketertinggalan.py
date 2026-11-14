import pandas as pd

BATAS_HARI = 10


def hari_tertinggal(kalender, terakhir, sampai):
    sampai = pd.Timestamp(sampai)
    awal = pd.Timestamp(terakhir) if terakhir is not None else None
    return [pd.Timestamp(h) for h in kalender if (awal is None or pd.Timestamp(h) > awal) and pd.Timestamp(h) <= sampai]


def terlalu_jauh(hari):
    return len(hari) > BATAS_HARI


def pesan_tolak(nama, hari):
    return (f"{nama}: tertinggal {len(hari)} hari bursa ({hari[0].date()} s/d {hari[-1].date()}), melebihi batas {BATAS_HARI}. "
            f"Tidak diproses otomatis; periksa penyebabnya dan putuskan secara manual.")
