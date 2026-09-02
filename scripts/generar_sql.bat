@echo off
REM ============================================================================
REM  PL_SGE - Regeneracion de los scripts SQL de database/
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Generacion de scripts SQL

echo.
echo  ============================================================================
echo    REGENERACION DE LOS SCRIPTS SQL
echo  ============================================================================
echo.
echo    Se creara una base temporal, se aplicaran las migraciones y la
echo    configuracion inicial, y se volcaran los archivos:
echo.
echo      database\02_esquema.sql
echo      database\03_datos_iniciales.sql
echo      database\04_verificacion.sql
echo.
echo    La base de datos de trabajo no se modifica.
echo.

"%PY%" "%RAIZ%\scripts\generar_sql.py"
endlocal
exit /b 0
