@echo off
REM ============================================================================
REM  PL_SGE - Carga de datos de demostracion
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Datos de demostracion

echo.
echo  ============================================================================
echo    CARGA DE DATOS DE DEMOSTRACION
echo  ============================================================================
echo.
echo    Se crearan docentes, estudiantes, acudientes, matriculas, asignaciones,
echo    notas, asistencia, agenda, observaciones, enfasis y un proceso electoral.
echo.
set /p n="   Estudiantes por grupo (Enter = 8): "
if "%n%"=="" set "n=8"
echo.

"%PY%" "%RAIZ%\manage.py" seed_demo --students-per-group %n%
endlocal
exit /b 0
