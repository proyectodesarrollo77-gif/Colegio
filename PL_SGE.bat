@echo off
REM ============================================================================
REM  PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
REM  Menu principal de administracion
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title PL_SGE - Panel de administracion
color 0B

:MENU
cls
echo.
echo  ============================================================================
echo    PL_SGE - PLATAFORMA DE GESTION ACADEMICA INSTITUCIONAL
echo  ============================================================================
echo.
echo    Carpeta del proyecto : %CD%
echo.
echo  ----------------------------------------------------------------------------
echo    INSTALACION
echo  ----------------------------------------------------------------------------
echo    [1]  Instalar la plataforma            (entorno, dependencias, base de datos)
echo    [2]  Cargar datos de demostracion      (estudiantes, docentes, notas)
echo   [13]  Modulo PAE                        (configuracion, demostracion, pruebas)
echo.
echo  ----------------------------------------------------------------------------
echo    OPERACION
echo  ----------------------------------------------------------------------------
echo    [3]  Iniciar la plataforma             (abre el navegador)
echo    [4]  Detener la plataforma
echo    [5]  Crear usuario administrador
echo.
echo  ----------------------------------------------------------------------------
echo    BASE DE DATOS
echo  ----------------------------------------------------------------------------
echo    [6]  Respaldar base de datos
echo    [7]  Restaurar base de datos
echo    [8]  Reiniciar base de datos           (BORRA TODA LA INFORMACION)
echo.
echo  ----------------------------------------------------------------------------
echo    MANTENIMIENTO
echo  ----------------------------------------------------------------------------
echo    [9]  Verificar la instalacion
echo   [10]  Aplicar migraciones pendientes
echo   [11]  Recolectar archivos estaticos
echo   [12]  Abrir consola de Django
echo   [14]  Regenerar los scripts SQL         (database/02, 03 y 04)
echo.
echo    [0]  Salir
echo.
echo  ============================================================================
set /p opcion="   Seleccione una opcion: "

if "%opcion%"=="1"  call "%~dp0scripts\instalar.bat"        & pause & goto MENU
if "%opcion%"=="2"  call "%~dp0scripts\datos_demo.bat"      & pause & goto MENU
if "%opcion%"=="3"  start "" "%~dp0INICIAR.bat"             & goto MENU
if "%opcion%"=="4"  call "%~dp0scripts\detener.bat"         & pause & goto MENU
if "%opcion%"=="5"  call "%~dp0scripts\crear_admin.bat"     & pause & goto MENU
if "%opcion%"=="6"  call "%~dp0scripts\respaldar_bd.bat"    & pause & goto MENU
if "%opcion%"=="7"  call "%~dp0scripts\restaurar_bd.bat"    & pause & goto MENU
if "%opcion%"=="8"  call "%~dp0scripts\reiniciar_bd.bat"    & pause & goto MENU
if "%opcion%"=="9"  call "%~dp0scripts\verificar.bat"       & pause & goto MENU
if "%opcion%"=="10" call "%~dp0scripts\migrar.bat"          & pause & goto MENU
if "%opcion%"=="11" call "%~dp0scripts\estaticos.bat"       & pause & goto MENU
if "%opcion%"=="12" call "%~dp0scripts\consola.bat"         & goto MENU
if "%opcion%"=="13" call "%~dp0scripts\pae.bat"             & goto MENU
if "%opcion%"=="14" call "%~dp0scripts\generar_sql.bat"     & pause & goto MENU
if "%opcion%"=="0"  goto FIN

echo.
echo    Opcion no valida.
timeout /t 2 >nul
goto MENU

:FIN
endlocal
exit /b 0
