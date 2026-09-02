@echo off
REM ============================================================================
REM  PL_SGE - Deteccion del entorno de ejecucion
REM  Uso interno: los demas scripts hacen  call "%~dp0_entorno.bat"
REM
REM  Define:
REM    PY        Interprete de Python a utilizar
REM    PGBIN     Carpeta bin de PostgreSQL (si se encuentra)
REM    RAIZ      Carpeta raiz del proyecto
REM ============================================================================

set "RAIZ=%~dp0.."
pushd "%RAIZ%"
set "RAIZ=%CD%"
popd

REM ---- 1. Interprete de Python -----------------------------------------------
set "PY="

if exist "%RAIZ%\.venv\Scripts\python.exe" (
    set "PY=%RAIZ%\.venv\Scripts\python.exe"
    goto :PY_LISTO
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set "PY=py -3"
    goto :PY_LISTO
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    set "PY=python"
    goto :PY_LISTO
)

echo.
echo  [ERROR] No se encontro Python en el sistema.
echo          Instale Python 3.11 o superior desde https://www.python.org/downloads/
echo          y marque la casilla "Add Python to PATH" durante la instalacion.
echo.
exit /b 1

:PY_LISTO

REM ---- 2. Herramientas de PostgreSQL -----------------------------------------
set "PGBIN="

where psql >nul 2>&1
if %ERRORLEVEL%==0 (
    for /f "delims=" %%i in ('where psql') do set "PGBIN=%%~dpi"
    goto :PG_LISTO
)

for %%V in (18 17 16 15 14) do (
    if exist "%ProgramFiles%\PostgreSQL\%%V\bin\psql.exe" (
        set "PGBIN=%ProgramFiles%\PostgreSQL\%%V\bin\"
        goto :PG_LISTO
    )
)

:PG_LISTO
exit /b 0
