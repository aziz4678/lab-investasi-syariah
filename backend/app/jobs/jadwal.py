import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from backend.app.jobs import pekerjaan as pk
from backend.core.config import ROOT
from backend.db import koneksi as d

NAMA_TUGAS = "LabInvestasiSyariah"
NAMA_LAMA = ["SwingSyariahPaper"]
JAM = "17:30"
PYTHONW = ROOT / "venv" / "Scripts" / "pythonw.exe"
ARGUMEN = "-m backend.app.jobs.jadwal jalan"


def ps(skrip):
    hasil = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", skrip], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return hasil.returncode, hasil.stdout.strip(), hasil.stderr.strip()


def status(nama=None):
    nama = nama or next((n for n in [NAMA_TUGAS, *NAMA_LAMA] if ada(n)), NAMA_TUGAS)
    kode, keluar, _ = ps(f"""$t = Get-ScheduledTask -TaskName '{nama}' -ErrorAction SilentlyContinue
if ($t) {{ $i = $t | Get-ScheduledTaskInfo
[pscustomobject]@{{ ada = $true; keadaan = [string]$t.State
terakhir = if ($i.LastRunTime -and $i.LastRunTime.Year -gt 2000) {{ $i.LastRunTime.ToString('s') }} else {{ $null }}
hasil = $i.LastTaskResult; berikut = if ($i.NextRunTime) {{ $i.NextRunTime.ToString('s') }} else {{ $null }} }} | ConvertTo-Json -Compress
}} else {{ '{{"ada": false}}' }}""")
    try:
        hasil = json.loads(keluar)
    except json.JSONDecodeError:
        hasil = {"ada": False, "galat": keluar[-300:]}
    hasil["jam"] = JAM
    hasil["nama"] = nama
    return hasil


def ada(nama):
    _, keluar, _ = ps(f"if (Get-ScheduledTask -TaskName '{nama}' -ErrorAction SilentlyContinue) {{ 'ya' }}")
    return keluar == "ya"


def folder_tugas(nama):
    _, keluar, _ = ps(f"(Get-ScheduledTask -TaskName '{nama}' -ErrorAction SilentlyContinue).Actions[0].WorkingDirectory")
    return keluar


def argumen_tugas(nama):
    _, keluar, _ = ps(f"(Get-ScheduledTask -TaskName '{nama}' -ErrorAction SilentlyContinue).Actions[0].Arguments")
    return keluar


def pasang(nama=NAMA_TUGAS):
    for lama in NAMA_LAMA:
        ps(f"Unregister-ScheduledTask -TaskName '{lama}' -Confirm:$false -ErrorAction SilentlyContinue")
    python = PYTHONW if PYTHONW.exists() else Path(sys.executable)
    kode, keluar, galat = ps(f"""$a = New-ScheduledTaskAction -Execute '{python}' -Argument '{ARGUMEN}' -WorkingDirectory '{ROOT}'
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At {JAM}
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName '{nama}' -Action $a -Trigger $t -Settings $s -Description 'Lab Investasi Syariah: perbarui paper trade, cek ulang, backup' -Force | Out-Null""")
    if kode != 0:
        raise RuntimeError(galat[-500:] or keluar[-500:])
    return status(nama)


def lepas():
    for nama in [NAMA_TUGAS, *NAMA_LAMA]:
        ps(f"Unregister-ScheduledTask -TaskName '{nama}' -Confirm:$false -ErrorAction SilentlyContinue")
    return status(NAMA_TUGAS)


def perbaiki():
    terpasang = [n for n in [NAMA_TUGAS, *NAMA_LAMA] if ada(n)]
    if not terpasang:
        print("Perbarui otomatis: mati")
        return
    if terpasang == [NAMA_TUGAS] and Path(folder_tugas(NAMA_TUGAS) or ".").resolve() == ROOT and argumen_tugas(NAMA_TUGAS) == ARGUMEN:
        print(f"Perbarui otomatis: aktif ({NAMA_TUGAS})")
        return
    pasang()
    print(f"Perbarui otomatis: dipasang ulang ke folder {ROOT} ({NAMA_TUGAS})")


def perlu_cek_des(hari_ini=None):
    hari_ini = hari_ini or date.today()
    if not ((hari_ini.month == 5 and hari_ini.day >= 20) or hari_ini.month == 6 or (hari_ini.month == 11 and hari_ini.day >= 20) or hari_ini.month == 12):
        return False
    berikut = date(hari_ini.year, 6, 1) if hari_ini.month in (5, 6) else date(hari_ini.year, 12, 1)
    terbaru = d.koneksi().des.find_one(sort=[("mulai", -1)])
    return not terbaru or terbaru["mulai"].date() < berikut


URUTAN_HARIAN = [
    "1. Unduh Yahoo: DES (musimnya), paper_unduh (harian paper + JII, dikoreksi), harga_perbarui, pasar_perbarui, reksa dana, ETF, makro",
    "2. Ambil idx_harian (Chrome Lab); kalau gagal, langkah berikutnya tetap jalan dengan cadangan Yahoo dan ditandai",
    "3. kualitas_data: perbarui_otomatis (aksi korporasi IDX) + cek_kualitas_data; ADA TEMUAN tidak memblokir paper; lalu koreksi_ekspor (registry ke data/koreksi_harga.jsonl)",
    "4. Paper H11a (paper_harian) + H22 (paper_h22), sumber IDX resmi",
    "5. Cek ulang paper (paper_cek, paper_h22_cek)",
    "6. Sumber data browser lain, tulis ringkasan jadwal_harian, lalu cadangan (+ mingguan cadangan_data, logo); ringkasan dilengkapi lagi setelah cadangan",
]


def jalan_browser(db, kecuali=()):
    from backend.app.services import sumber_data as sd
    for s in [x for x in sd.SUMBER if x.get("otomatis") and x["id"] not in kecuali]:
        sekarang = next((x for x in sd.status() if x["id"] == s["id"]), {})
        if not sekarang.get("perlu"):
            continue
        langkah(db, "otomatis", [s["id"]])


def langkah(db, jenis, argumen=None, catatan=None):
    try:
        id_, _ = pk.mulai(jenis, argumen, tunggu=True, oleh="jadwal")
        st = (pk.ambil(id_) or {}).get("status", "gagal")
    except pk.Bentrok as e:
        waktu = datetime.now()
        label = pk.PERINTAH[jenis][0] if jenis != "otomatis" else f"Ambil otomatis: {argumen[0]}"
        db.pekerjaan.insert_one({"_id": f"lewati-{jenis}-{waktu:%Y%m%d%H%M%S}", "jenis": jenis, "label": label,
                                 "oleh": "jadwal", "status": "gagal", "mulai": waktu, "selesai": waktu, "log": [f"dilewati: {e}"]})
        st = "dilewati"
    if catatan is not None:
        catatan.append({"jenis": jenis, "argumen": argumen, "status": st, "waktu": datetime.now()})
    return st


def idx_hari_ini_ada():
    from backend.app.services import sumber_data as sd
    terakhir = sd.idx_harian_terakhir()
    hari = date.today()
    while hari.weekday() >= 5:
        hari = date.fromordinal(hari.toordinal() - 1)
    return terakhir is not None and terakhir >= hari, terakhir


def jalan():
    db = d.koneksi()
    log = []
    mulai = datetime.now()
    ada_h11a = bool(db.paper_status.find_one({"_id": "status"}))
    ada_h22 = bool(db.paper_h22_status.find_one({"_id": "status"}))
    if perlu_cek_des():
        langkah(db, "des_perbarui", catatan=log)
    if ada_h11a or ada_h22:
        langkah(db, "paper_unduh", catatan=log)
    langkah(db, "harga_perbarui", catatan=log)
    langkah(db, "pasar_perbarui", catatan=log)
    langkah(db, "rd_perbarui", catatan=log)
    from backend.app.services import sumber_data as sd
    if sd.platform_perlu(db):
        langkah(db, "rd_platform_perbarui", catatan=log)
    langkah(db, "etf_perbarui", catatan=log)
    langkah(db, "makro_perbarui", catatan=log)
    st_idx = langkah(db, "otomatis", ["idx_harian"], catatan=log)
    idx_ok, idx_terakhir = idx_hari_ini_ada()
    langkah(db, "kualitas_data", catatan=log)
    langkah(db, "koreksi_ekspor", catatan=log)
    if ada_h11a:
        langkah(db, "paper_harian", ["--tanpa-unduh"], catatan=log)
    if ada_h22:
        langkah(db, "paper_h22", ["--tanpa-unduh"], catatan=log)
    if ada_h11a:
        langkah(db, "paper_cek", catatan=log)
    if ada_h22:
        langkah(db, "paper_h22_cek", catatan=log)
    jalan_browser(db, kecuali={"idx_harian"})

    def tulis():
        db.jadwal_harian.replace_one({"_id": str(date.today())}, {"_id": str(date.today()), "mulai": mulai, "selesai": datetime.now(), "langkah": log,
                                                                  "idx_status": st_idx, "idx_lengkap": idx_ok, "idx_terakhir": str(idx_terakhir) if idx_terakhir else None,
                                                                  "urutan": URUTAN_HARIAN}, upsert=True)

    tulis()
    langkah(db, "cadangan", ["jadwal"], catatan=log)
    from backend.db import cadangan as cd
    if cd.perlu_data():
        langkah(db, "cadangan_data", catatan=log)
        langkah(db, "logo_perbarui", catatan=log)
    tulis()


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else "status"
    if perintah == "jalan":
        jalan()
    elif perintah == "pasang":
        print(json.dumps(pasang(*sys.argv[2:3])))
    elif perintah == "lepas":
        print(json.dumps(lepas()))
    elif perintah == "perbaiki":
        perbaiki()
    else:
        print(json.dumps(status(*sys.argv[2:3])))
