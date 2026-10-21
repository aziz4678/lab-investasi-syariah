@echo off
setlocal
cd /d "%~dp0"
title Lab Investasi
if "%PORT%"=="" set PORT=8765
set URL=http://127.0.0.1:%PORT%

if not exist "venv\Scripts\python.exe" (
  echo venv tidak ditemukan di %~dp0venv
  pause
  exit /b 1
)

sc query MongoDB | find "RUNNING" >nul
if errorlevel 1 (
  echo MongoDB belum jalan, mencoba menyalakan...
  net start MongoDB >nul 2>&1
  sc query MongoDB | find "RUNNING" >nul
  if errorlevel 1 (
    echo Gagal menyalakan MongoDB. Klik kanan jalankan.bat lalu "Run as administrator", atau nyalakan service MongoDB.
    pause
    exit /b 1
  )
)

if not exist "frontend\dist\index.html" (
  echo Tampilan belum dibangun, membangun frontend...
  pushd frontend
  call npm run build
  popd
)

venv\Scripts\python.exe -m backend.api.jadwal perbaiki

netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul
if not errorlevel 1 (
  echo Server sudah jalan di %URL%
  if not "%NO_BROWSER%"=="1" start "" %URL%
  exit /b 0
)

echo Menjalankan Lab Investasi di %URL%
echo Tutup jendela ini untuk menghentikan server.
if not "%NO_BROWSER%"=="1" start "" cmd /c "timeout /t 4 /nobreak >nul & start %URL%"
echo Kode backend berubah = server memuat ulang sendiri.
venv\Scripts\python.exe -m uvicorn backend.api.main:app --port %PORT% --reload --reload-dir backend
pause
