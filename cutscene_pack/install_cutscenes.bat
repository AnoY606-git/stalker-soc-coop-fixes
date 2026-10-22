@echo off
rem Installs the Shadow of COOP cutscene pack (original SoC movies) into the xrMPE patches folder (see install_cutscenes.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_cutscenes.ps1" %*
pause
