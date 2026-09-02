@echo off
REM ============================================================================
REM  PL_SGE - Respaldo de la base de datos
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Respaldo de base de datos

echo.
echo  ============================================================================
echo    RESPALDO DE LA BASE DE DATOS
echo  ============================================================================
echo.
"%PY%" "%RAIZ%\scripts\respaldar_bd.py"
endlocal
exit /b 0
