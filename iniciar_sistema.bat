@echo off
chcp 65001 >nul
echo ============================================================================
echo   DFM - SISTEMA DE TRATAMENTO (SECAO 10) E PAINEL DE CUSTOS - SCM MARINHA
echo ============================================================================
cd /d "%~dp0"
if exist ".\.venv\Scripts\python.exe" (
  .\.venv\Scripts\python.exe scripts\iniciar_local.py
) else (
  "%LOCALAPPDATA%\SCM-Confidencial\runtime\portal-venv\Scripts\python.exe" scripts\iniciar_local.py
)
pause
