import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

from bson import json_util

from backend.db import data as dt
from backend.db import koneksi as d

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "backup"
LEWATI = {"pekerjaan"}
SIMPAN_DATA = 2
UMUR_DATA_HARI = 7


def buat(alasan="manual", db=None):
    db = d.koneksi() if db is None else db
    nama = f"{db.name}_{datetime.now():%Y%m%d-%H%M%S}"
    tujuan = FOLDER / nama
    tujuan.mkdir(parents=True)
    ringkas = {}
    for k in sorted(db.list_collection_names()):
        if k in LEWATI:
            continue
        n = 0
        with gzip.open(tujuan / f"{k}.jsonl.gz", "wt", encoding="utf-8") as f:
            for dok in db[k].find():
                f.write(json_util.dumps(dok, json_options=json_util.CANONICAL_JSON_OPTIONS) + "\n")
                n += 1
        ringkas[k] = n
    meta = {"db": db.name, "waktu": datetime.now().isoformat(timespec="seconds"), "alasan": alasan, "koleksi": ringkas}
    (tujuan / "info.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    ukuran = sum(f.stat().st_size for f in tujuan.iterdir())
    print(f"Backup {nama}: {len(ringkas)} koleksi, {sum(ringkas.values()):,} dokumen, {ukuran / 1e6:.1f} MB -> backup/{nama}")
    return nama


def buat_data(alasan="mingguan"):
    nama = buat(alasan, dt.db())
    lama = [p.parent for p in sorted(FOLDER.glob(f"{dt.NAMA_DB}_*/info.json"))][:-SIMPAN_DATA]
    for p in lama:
        import shutil
        shutil.rmtree(p)
        print(f"Backup data lama dihapus (disimpan {SIMPAN_DATA} terakhir): {p.name}")
    return nama


def perlu_data():
    terakhir = sorted(FOLDER.glob(f"{dt.NAMA_DB}_*/info.json"))
    if not terakhir:
        return True
    waktu = datetime.fromisoformat(json.loads(terakhir[-1].read_text(encoding="utf-8"))["waktu"])
    return (datetime.now() - waktu).days >= UMUR_DATA_HARI


def daftar(nama_db=None):
    hasil = []
    nama_db = nama_db or d.koneksi().name
    for p in sorted(FOLDER.glob("*/info.json"), reverse=True):
        info = json.loads(p.read_text(encoding="utf-8"))
        if info.get("db") != nama_db:
            continue
        hasil.append({"nama": p.parent.name, "waktu": info["waktu"], "alasan": info.get("alasan"),
                      "koleksi": len(info["koleksi"]), "dokumen": sum(info["koleksi"].values()),
                      "ukuran_mb": round(sum(f.stat().st_size for f in p.parent.iterdir()) / 1e6, 2)})
    return hasil


def pulihkan(nama):
    sumber = FOLDER / nama
    if not (sumber / "info.json").exists() or sumber.parent != FOLDER:
        raise SystemExit(f"backup {nama} tidak ditemukan")
    info = json.loads((sumber / "info.json").read_text(encoding="utf-8"))
    db = dt.db() if info.get("db") == dt.NAMA_DB else d.koneksi()
    if info.get("db") != db.name:
        raise SystemExit(f"backup {nama} berasal dari db {info.get('db')}, bukan {db.name}")
    print("Membuat backup kondisi sekarang dulu sebelum memulihkan...")
    buat(f"otomatis sebelum pulihkan {nama}", db)
    for f in sorted(sumber.glob("*.jsonl.gz")):
        k = f.name[:-len(".jsonl.gz")]
        with gzip.open(f, "rt", encoding="utf-8") as isi:
            dok = [json_util.loads(b) for b in isi if b.strip()]
        db[k].drop()
        if dok:
            db[k].insert_many(dok)
        print(f"  {k}: {len(dok):,} dokumen")
    if db.name == d.koneksi().name:
        d.siapkan_indeks(db)
    print(f"Selesai memulihkan dari {nama}.")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "pulihkan":
        pulihkan(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "data":
        buat_data(sys.argv[2] if len(sys.argv) > 2 else "mingguan")
    elif len(sys.argv) > 1 and sys.argv[1] == "daftar":
        for b in daftar():
            print(b)
    else:
        buat(sys.argv[2] if len(sys.argv) > 2 else "manual")
