@echo off
REM ============================================================================
REM  PL_SGE - Reinicio total de la base de datos
REM  ATENCION: elimina de forma irreversible toda la informacion.
REM ============================================================================
setlocal EnableDelayedExpansion
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Reiniciar base de datos
color 0C

echo.
echo  ============================================================================
echo    REINICIO TOTAL DE LA BASE DE DATOS
echo  ============================================================================
echo.
echo    ATENCION
echo.
echo    Se eliminaran de forma IRREVERSIBLE todos los estudiantes, docentes,
echo    matriculas, notas, boletines, observaciones y registros de auditoria.
echo.
echo    Se recomienda generar un respaldo antes de continuar (opcion 6 del menu).
echo.
set /p CONF="   Escriba BORRAR para confirmar: "
if /i not "!CONF!"=="BORRAR" (
    echo.
    echo    Operacion cancelada.
    exit /b 0
)

echo.
echo    Eliminando y recreando la base de datos...
"%PY%" "%RAIZ%\scripts\reiniciar_bd.py"
if errorlevel 1 exit /b 1

echo.
echo    Recreando las tablas...
"%PY%" "%RAIZ%\manage.py" migrate --noinput

echo.
echo    Inicializando la plataforma...
"%PY%" "%RAIZ%\manage.py" initialize_platform
endlocal
exit /b 0
