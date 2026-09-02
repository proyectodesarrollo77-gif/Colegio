@echo off
REM ============================================================================
REM  PL_SGE - Consola interactiva de Django (shell)
REM ============================================================================
setlocal
call "%~dp0_entorno.bat" || exit /b 1
cd /d "%RAIZ%"
title PL_SGE - Consola de Django

echo.
echo    Consola de Django. Ejemplos:
echo.
echo      from core.users.models import User
echo      User.objects.count()
echo.
echo    Escriba exit() para salir.
echo.
"%PY%" "%RAIZ%\manage.py" shell
endlocal
exit /b 0
