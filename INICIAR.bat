@echo off
REM ============================================================================
REM  PL_SGE - Inicio de la plataforma
REM  Uso:  INICIAR.bat [puerto]      (por defecto 8000)
REM ============================================================================
setlocal EnableDelayedExpansion
call "%~dp0scripts\_entorno.bat" || (pause & exit /b 1)
cd /d "%RAIZ%"
title PL_SGE - Servidor en ejecucion
color 0A

set "PUERTO=8000"
if not "%~1"=="" set "PUERTO=%~1"

echo.
echo  ============================================================================
echo    PL_SGE - PLATAFORMA DE GESTION ACADEMICA INSTITUCIONAL
echo  ============================================================================
echo.

REM ---- Verificar que la plataforma este instalada -----------------------------
if not exist "%RAIZ%\.venv\Scripts\python.exe" (
    echo    [AVISO] La plataforma aun no ha sido instalada.
    echo            Ejecute primero:  INSTALAR.bat
    echo.
    pause
    exit /b 1
)

REM ---- Buscar un puerto libre -------------------------------------------------
call :PUERTO_OCUPADO %PUERTO%
if "!OCUPADO!"=="1" (
    echo    [AVISO] El puerto %PUERTO% esta en uso por otra aplicacion.
    echo.
    set "SUGERIDO="
    for %%P in (8010 8020 8080 8090 9000) do (
        if "!SUGERIDO!"=="" (
            call :PUERTO_OCUPADO %%P
            if "!OCUPADO!"=="0" set "SUGERIDO=%%P"
        )
    )
    if "!SUGERIDO!"=="" (
        echo    No se encontro ningun puerto libre entre los habituales.
        pause
        exit /b 1
    )
    echo            Puerto libre disponible: !SUGERIDO!
    echo.
    set /p RESP="            Presione Enter para usar !SUGERIDO! o escriba otro puerto: "
    if "!RESP!"=="" (set "PUERTO=!SUGERIDO!") else (set "PUERTO=!RESP!")
    echo.
)

echo    Verificando la base de datos...
"%PY%" "%RAIZ%\manage.py" migrate --noinput >nul 2>&1
if errorlevel 1 (
    echo.
    echo    [ERROR] No fue posible conectar con la base de datos.
    echo            Revise que el servicio de PostgreSQL este activo y que la
    echo            configuracion del archivo .env sea correcta.
    echo.
    pause
    exit /b 1
)

echo.
echo  ----------------------------------------------------------------------------
echo    Direccion   : http://localhost:!PUERTO!/
echo    Usuario     : admin@datly.local
echo    Contrasena  : Admin123*
echo  ----------------------------------------------------------------------------
echo.
echo    Para detener el servidor presione  CTRL + C  en esta ventana.
echo.
echo  ============================================================================
echo.

start "" http://localhost:!PUERTO!/auth/login/
"%PY%" "%RAIZ%\manage.py" runserver 0.0.0.0:!PUERTO!

echo.
echo    Servidor detenido.
endlocal
pause
exit /b 0


REM ============================================================================
REM  Subrutina: determina si un puerto TCP esta escuchando
REM ============================================================================
:PUERTO_OCUPADO
set "OCUPADO=0"
netstat -ano | findstr /r /c:":%~1 .*LISTENING" >nul 2>&1
if not errorlevel 1 set "OCUPADO=1"
exit /b 0
