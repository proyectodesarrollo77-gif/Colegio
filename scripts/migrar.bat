@echo off
REM ============================================================================
REM  PL_SGE - Aplicar migraciones pendientes
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Migraciones

echo.
echo    Generando migraciones nuevas (si las hubiera)...
"%PY%" "%RAIZ%\manage.py" makemigrations
echo.
echo    Aplicando migraciones...
"%PY%" "%RAIZ%\manage.py" migrate --noinput
endlocal
exit /b 0
