#!/usr/bin/env bash
# =============================================================================
#  PL_SGE - Instalacion completa de la plataforma (Linux / macOS)
# =============================================================================
set -e
cd "$(dirname "$0")"

echo ""
echo " ============================================================================"
echo "   PL_SGE - INSTALACION DE LA PLATAFORMA"
echo " ============================================================================"
echo ""

echo " [1/7] Verificando Python..."
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  echo "       [ERROR] Python 3.11 o superior no esta instalado."
  exit 1
fi
"$PY" --version

echo ""
echo " [2/7] Preparando el entorno virtual..."
if [ -d ".venv" ]; then
  echo "       El entorno virtual ya existe, se reutiliza."
else
  "$PY" -m venv .venv
  echo "       Entorno virtual creado en .venv"
fi
PY=".venv/bin/python"

echo ""
echo " [3/7] Instalando dependencias..."
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet
echo "       Dependencias instaladas."

echo ""
echo " [4/7] Configurando variables de entorno..."
if [ -f ".env" ]; then
  echo "       El archivo .env ya existe, se conserva."
else
  cp .env.example .env
  echo "       Archivo .env creado a partir de .env.example"
fi

echo ""
echo " [5/7] Creando la base de datos PostgreSQL..."
"$PY" scripts/crear_bd.py

echo ""
echo " [6/7] Creando las tablas..."
"$PY" manage.py migrate --noinput

echo ""
echo " [7/7] Inicializando perfiles, permisos, estructura academica y PAE..."
"$PY" manage.py initialize_platform

echo ""
echo " ============================================================================"
echo "   INSTALACION COMPLETADA"
echo " ============================================================================"
echo ""
echo "   Para iniciar la plataforma ejecute:  ./iniciar.sh"
echo ""
echo "   Direccion : http://localhost:8000/"
echo "   Usuario   : admin@datly.local"
echo "   Contrasena: Admin123*"
echo ""
