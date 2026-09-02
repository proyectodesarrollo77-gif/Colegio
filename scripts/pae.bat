@echo off
REM ============================================================================
REM  PL_SGE - Programa de Alimentacion Escolar (PAE)
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Modulo PAE

:MENU_PAE
cls
echo.
echo  ============================================================================
echo    PROGRAMA DE ALIMENTACION ESCOLAR
echo  ============================================================================
echo.
echo    [1]  Cargar la configuracion base       (normativa, catalogos, listas)
echo    [2]  Cargar datos de demostracion       (informacion ficticia)
echo    [3]  Recalcular los indicadores
echo    [4]  Ejecutar las pruebas del modulo
echo.
echo    [0]  Volver
echo.
echo  ============================================================================
set /p opcion="   Seleccione una opcion: "

if "%opcion%"=="1" goto CONFIGURACION
if "%opcion%"=="2" goto DEMOSTRACION
if "%opcion%"=="3" goto INDICADORES
if "%opcion%"=="4" goto PRUEBAS
if "%opcion%"=="0" goto FIN
goto MENU_PAE

:CONFIGURACION
echo.
echo    Se cargaran la normativa de referencia, los catalogos parametrizables,
echo    las modalidades, los tipos de complemento y las listas de verificacion.
echo.
"%PY%" "%RAIZ%\manage.py" seed_pae
echo.
pause
goto MENU_PAE

:DEMOSTRACION
echo.
echo    ATENCION: la informacion cargada es ficticia y no corresponde a
echo    organizaciones ni personas reales. Requiere datos academicos previos.
echo.
set /p n="   Beneficiarios a vincular (Enter = 350): "
if "%n%"=="" set "n=350"
echo.
"%PY%" "%RAIZ%\manage.py" seed_pae_demo --beneficiarios %n%
echo.
pause
goto MENU_PAE

:INDICADORES
echo.
"%PY%" "%RAIZ%\manage.py" shell -c "from core.pae import services; from core.pae.models import PaeVigencia; v = PaeVigencia.current(); print('Indicadores calculados:', services.refresh_indicators(v)) if v else print('No hay vigencia PAE configurada.')"
echo.
pause
goto MENU_PAE

:PRUEBAS
echo.
"%PY%" "%RAIZ%\manage.py" test core.pae
echo.
pause
goto MENU_PAE

:FIN
endlocal
exit /b 0
