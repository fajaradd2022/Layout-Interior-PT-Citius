@echo off
title Backend Dashboard Layout Interior - PT Citius
cd /d "%~dp0"
python server.py
if errorlevel 1 (
  echo.
  echo Gagal menjalankan. Pastikan Python 3 dan PyMuPDF terpasang:  pip install pymupdf
  pause
)
