import os
import subprocess
import sys
from datetime import datetime

from backend.db import koneksi as d

BATAS_LOG = 400


def main():
    id_, perintah = sys.argv[1], sys.argv[2:]
    db = d.koneksi()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    try:
        proses = subprocess.Popen(perintah, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                  errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        db.pekerjaan.update_one({"_id": id_}, {"$set": {"pid_anak": proses.pid}})
        for baris in proses.stdout:
            baris = baris.rstrip()
            if baris:
                db.pekerjaan.update_one({"_id": id_}, {"$push": {"log": {"$each": [baris], "$slice": -BATAS_LOG}}})
        kode = proses.wait()
    except Exception as e:
        db.pekerjaan.update_one({"_id": id_}, {"$push": {"log": f"Gagal menjalankan: {e}"}})
        kode = -1
    db.pekerjaan.update_one({"_id": id_}, {"$set": {"status": "selesai" if kode == 0 else "gagal", "kode": kode, "selesai": datetime.now()}})


if __name__ == "__main__":
    main()
