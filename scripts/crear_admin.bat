@echo off
REM ============================================================================
REM  PL_SGE - Crear un usuario administrador adicional
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Nuevo administrador

echo.
echo  ============================================================================
echo    CREAR USUARIO ADMINISTRADOR
echo  ============================================================================
echo.
echo    Se solicitara correo, nombre de usuario y contrasena.
echo    El usuario quedara con el perfil SUPER_ADMIN.
echo.
"%PY%" "%RAIZ%\manage.py" createsuperuser
endlocal
exit /b 0
