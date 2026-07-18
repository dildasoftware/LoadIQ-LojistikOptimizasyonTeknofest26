@echo off
cd /d "%~dp0.."
start http://localhost:8000/stage2_gelismis_cozum/dashboard/index.html
py -m http.server 8000
