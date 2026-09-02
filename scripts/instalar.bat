@echo off
REM ============================================================================
REM  PL_SGE - Instalacion completa de la plataforma
REM ============================================================================
setlocal EnableDelayedExpansion
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Instalacion

echo.
echo  ============================================================================
echo    PL_SGE - INSTALACION DE LA PLATAFORMA
echo  ============================================================================
echo.

REM ---------------------------------------------------------------- 1. Python
echo  [1/7] Verificando Python...
%PY% --version
if %ERRORLEVEL% NEQ 0 (
    echo        [ERROR] Python no responde correctamente.
    exit /b 1
)

REM ------------------------------------------------------- 2. Entorno virtual
echo.
echo  [2/7] Preparando el entorno virtual...
if exist "%RAIZ%\.venv\Scripts\python.exe" (
    echo        El entorno virtual ya existe, se reutiliza.
) else (
    %PY% -m venv "%RAIZ%\.venv"
    if !ERRORLEVEL! NEQ 0 (
        echo        [ERROR] No fue posible crear el entorno virtual.
        exit /b 1
    )
    echo        Entorno virtual creado en .venv
)
set "PY=%RAIZ%\.venv\Scripts\python.exe"

REM ---------------------------------------------------------- 3. Dependencias
echo.
echo  [3/7] Instalando dependencias (puede tardar varios minutos)...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install -r "%RAIZ%\requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo        [ERROR] Fallo la instalacion de dependencias.
    exit /b 1
)
echo        Dependencias instaladas.

REM ------------------------------------------------------ 4. Archivo .env
echo.
echo  [4/7] Configurando variables de entorno...
if exist "%RAIZ%\.env" (
    echo        El archivo .env ya existe, se conserva.
) else (
    copy /y "%RAIZ%\.env.example" "%RAIZ%\.env" >nul
    echo        Archivo .env creado a partir de .env.example
    echo        Revise las credenciales de PostgreSQL antes de continuar.
)

REM ------------------------------------------------------- 5. Base de datos
echo.
echo  [5/7] Creando la base de datos PostgreSQL...
"%PY%" "%RAIZ%\scripts\crear_bd.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo        [ERROR] No fue posible preparar la base de datos.
    echo        Verifique que el servicio de PostgreSQL este activo y que las
    echo        credenciales del archivo .env sean correctas.
    exit /b 1
)

REM --------------------------------------------------------- 6. Migraciones
echo.
echo  [6/7] Creando las tablas de la base de datos...
"%PY%" "%RAIZ%\manage.py" migrate --noinput
if %ERRORLEVEL% NEQ 0 (
    echo        [ERROR] Fallaron las migraciones.
    exit /b 1
)

REM ------------------------------------------------------- 7. Inicializacion
echo.
echo  [7/7] Inicializando perfiles, permisos, estructura academica y PAE...
"%PY%" "%RAIZ%\manage.py" initialize_platform
if %ERRORLEVEL% NEQ 0 (
    echo        [ERROR] Fallo la inicializacion de la plataforma.
    exit /b 1
)

echo.
echo  ============================================================================
echo    INSTALACION COMPLETADA
echo  ============================================================================
echo.
echo    Para iniciar la plataforma ejecute:  INICIAR.bat
echo.
echo    Direccion : http://localhost:8000/
echo    Usuario   : admin@datly.local
echo    Contrasena: Admin123*
echo.
echo  ============================================================================
endlocal
exit /b 0
