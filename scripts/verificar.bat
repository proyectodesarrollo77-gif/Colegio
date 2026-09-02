@echo off
REM ============================================================================
REM  PL_SGE - Verificacion integral de la instalacion
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Verificacion

echo.
echo  ============================================================================
echo    VERIFICACION DE LA INSTALACION
echo  ============================================================================
echo.
echo  [1/3] Revision de configuracion de Django...
"%PY%" "%RAIZ%\manage.py" check
echo.
echo  [2/3] Migraciones pendientes...
"%PY%" "%RAIZ%\manage.py" showmigrations --plan | findstr /c:"[ ]" >nul && (
    echo        [AVISO] Existen migraciones pendientes. Ejecute la opcion 10 del menu.
) || (
    echo        Todas las migraciones estan aplicadas.
)
echo.
echo  [3/3] Prueba de humo de paginas y endpoints...
"%PY%" "%RAIZ%\smoke_test.py"
endlocal
exit /b 0
