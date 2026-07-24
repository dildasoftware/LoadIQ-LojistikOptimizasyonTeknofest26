@echo off
cd /d "%~dp0.."
start http://localhost:8000/stage2_gelismis_cozum/dashboard/LoadIQ_Dashboard.html
py -m http.server 8000
