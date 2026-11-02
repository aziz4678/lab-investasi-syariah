import pandas as pd

from backend.db import koneksi as kdb
from backend.ingest import des_ojk
from backend.paper import h22_harian as h22
from backend.paper import tren_harian as th


def utama():
    db = kdb.koneksi()
    des = des_ojk.baca()
    hari_ini = pd.Timestamp.today().normalize()
    daftar = set(des_ojk.syariah_pada(des, hari_ini))
    daftar |= {p["ticker"] for p in db.paper_posisi.find({}, {"ticker": 1})}
    daftar |= {p["ticker"] for p in db[h22.K_POSISI].find({}, {"ticker": 1})}
    print(f"unduh harga harian Yahoo {len(daftar)} saham untuk paper (koreksi_harga diterapkan)...", flush=True)
    hasil, _ = th.unduh(sorted(daftar))
    print(f"{len(hasil)} saham tersimpan di harian", flush=True)
    h22.unduh_jii()
    print("indeks JII untuk pembanding H29 diperbarui")
    print("SELESAI")


if __name__ == "__main__":
    utama()
