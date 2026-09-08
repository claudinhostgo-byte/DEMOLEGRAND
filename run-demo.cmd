@echo off
setlocal
rem =====================================================================
rem  Demo Legrand + Teknica - Integracion de landings con Dynamics 365
rem  Levanta el sitio maestro, las 4 landings y la API unica de leads.
rem  Requisito: Python 3.8+ (sin librerias externas).
rem =====================================================================
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo.
    echo  No se encontro Python en el PATH. Instalar desde https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
  )
)

start "" http://localhost:8080/
"%PY%" api\lead_api.py
pause
