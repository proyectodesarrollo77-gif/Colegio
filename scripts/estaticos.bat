@echo off
REM ============================================================================
REM  PL_SGE - Recoleccion de archivos estaticos para produccion
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Archivos estaticos

echo.
echo    Recolectando archivos estaticos en la carpeta staticfiles...
echo.
set "DJANGO_DEBUG=False"
"%PY%" "%RAIZ%\manage.py" collectstatic --noinput
endlocal
exit /b 0
