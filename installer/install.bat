@echo off
rem Installs zzz_soc_coop_fixes.db into coop.addon the same way on every PC (see install.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause
