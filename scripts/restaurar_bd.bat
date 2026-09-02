@echo off
REM ============================================================================
REM  PL_SGE - Restauracion de la base de datos
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Restaurar base de datos

echo.
echo  ============================================================================
echo    RESTAURACION DE LA BASE DE DATOS
echo  ============================================================================
echo.
"%PY%" "%RAIZ%\scripts\restaurar_bd.py"
endlocal
exit /b 0
