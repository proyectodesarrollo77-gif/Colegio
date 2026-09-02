@echo off
REM ============================================================================
REM  PL_SGE - Detener el servidor de la plataforma
REM  Uso:  detener.bat [puerto]     (sin argumento revisa los puertos comunes)
REM ============================================================================
setlocal EnableDelayedExpansion
title PL_SGE - Detener servidor

set "PUERTOS=8000 8010 8020 8080"
if not "%~1"=="" set "PUERTOS=%~1"

echo.
echo    Buscando el servidor de PL_SGE en los puertos: %PUERTOS%
echo.

set "ENCONTRADOS=0"
for %%P in (%PUERTOS%) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
        echo    Puerto %%P  ->  deteniendo proceso PID %%A
        taskkill /PID %%A /T /F >nul 2>&1
        set /a ENCONTRADOS+=1
    )
)

echo.
if "!ENCONTRADOS!"=="0" (
    echo    No hay ningun servidor de PL_SGE en ejecucion.
) else (
    echo    Servidor detenido correctamente (!ENCONTRADOS! proceso^(s^)^).
)
endlocal
exit /b 0
