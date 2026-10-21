import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from backend.api import pekerjaan as pk
from backend.db import koneksi as d

ROOT = Path(__file__).resolve().parents[2]
NAMA_TUGAS = "LabInvestasiSyariah"
NAMA_LAMA = ["SwingSyariahPaper"]
JAM = "17:30"
PYTHONW = ROOT / "venv" / "Scripts" / "pythonw.exe"


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


def pasang(nama=NAMA_TUGAS):
    for lama in NAMA_LAMA:
        ps(f"Unregister-ScheduledTask -TaskName '{lama}' -Confirm:$false -ErrorAction SilentlyContinue")
    python = PYTHONW if PYTHONW.exists() else Path(sys.executable)
    kode, keluar, galat = ps(f"""$a = New-ScheduledTaskAction -Execute '{python}' -Argument '-m backend.api.jadwal jalan' -WorkingDirectory '{ROOT}'
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
    if terpasang == [NAMA_TUGAS] and Path(folder_tugas(NAMA_TUGAS) or ".").resolve() == ROOT:
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


def jalan_browser(db):
    from backend.api import sumber_data as sd
    for s in [x for x in sd.SUMBER if x.get("otomatis")]:
        sekarang = next((x for x in sd.status() if x["id"] == s["id"]), {})
        if not sekarang.get("perlu"):
            continue
        try:
            pk.mulai("otomatis", [s["id"]], tunggu=True, oleh="jadwal")
        except pk.Bentrok as e:
            waktu = datetime.now()
            db.pekerjaan.insert_one({"_id": f"lewati-otomatis-{s['id']}-{waktu:%Y%m%d%H%M%S}", "jenis": "otomatis", "label": f"Ambil otomatis: {s['nama']}",
                                     "oleh": "jadwal", "status": "gagal", "mulai": waktu, "selesai": waktu, "log": [f"dilewati: {e}"]})


def jalan():
    db = d.koneksi()
    urutan = []
    if perlu_cek_des():
        urutan.append("des_perbarui")
    if db.paper_status.find_one({"_id": "status"}):
        urutan += ["paper_harian", "paper_cek"]
    urutan.append("paper_dividen")
    urutan.append("rd_perbarui")
    urutan.append("etf_perbarui")
    urutan.append("makro_perbarui")
    urutan.append("browser")
    urutan.append("cadangan")
    from backend.db import cadangan as cd
    if cd.perlu_data():
        urutan.append("cadangan_data")
        urutan.append("logo_perbarui")
    for jenis in urutan:
        if jenis == "browser":
            jalan_browser(db)
            continue
        argumen = ["jadwal"] if jenis == "cadangan" else None
        try:
            pk.mulai(jenis, argumen, tunggu=True, oleh="jadwal")
        except pk.Bentrok as e:
            sekarang = datetime.now()
            db.pekerjaan.insert_one({"_id": f"lewati-{jenis}-{sekarang:%Y%m%d%H%M%S}", "jenis": jenis, "label": pk.PERINTAH[jenis][0],
                                     "oleh": "jadwal", "status": "gagal", "mulai": sekarang, "selesai": sekarang, "log": [f"dilewati: {e}"]})


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
