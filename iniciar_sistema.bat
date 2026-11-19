@echo off
chcp 65001 >nul
echo ============================================================================
echo   DFM - SISTEMA DE TRATAMENTO (SECAO 10) E PAINEL DE CUSTOS - SCM MARINHA
echo ============================================================================
cd /d "%~dp0"
start "" "http://127.0.0.1:8082"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8082
pause
