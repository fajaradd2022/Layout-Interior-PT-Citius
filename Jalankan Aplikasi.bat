@echo off
title Dashboard Layout Interior - PT Citius
cd /d "%~dp0"
echo [1/2] Menjalankan backend (SQLite) di http://localhost:8800 ...
start "Backend Layout Interior" cmd /k "cd /d "%~dp0backend" && python server.py"
echo [2/2] Menjalankan frontend Next.js di http://localhost:3000 ...
cd /d "%~dp0dashboard-layout-interior"
if not exist node_modules (
  echo node_modules belum ada, menjalankan npm install ...
  call npm install
)
start "" http://localhost:3000
call npm run dev
pause
