#!/usr/bin/env bash
# =============================================================================
#  PL_SGE - Inicio de la plataforma (Linux / macOS)
# =============================================================================
cd "$(dirname "$0")"

PUERTO="${1:-8000}"

if [ ! -x ".venv/bin/python" ]; then
  echo "   [AVISO] La plataforma aun no ha sido instalada."
  echo "           Ejecute primero:  ./instalar.sh"
  exit 1
fi
PY=".venv/bin/python"

echo ""
echo " ============================================================================"
echo "   PL_SGE - PLATAFORMA DE GESTION ACADEMICA INSTITUCIONAL"
echo " ============================================================================"
echo ""
echo "   Verificando la base de datos..."
"$PY" manage.py migrate --noinput >/dev/null 2>&1 || {
  echo "   [ERROR] No fue posible conectar con la base de datos."
  echo "           Revise la configuracion del archivo .env"
  exit 1
}

echo ""
echo " ----------------------------------------------------------------------------"
echo "   Direccion   : http://localhost:${PUERTO}/"
echo "   Usuario     : admin@datly.local"
echo "   Contrasena  : Admin123*"
echo " ----------------------------------------------------------------------------"
echo ""
echo "   Para detener el servidor presione CTRL + C."
echo ""

(command -v xdg-open >/dev/null && sleep 2 && xdg-open "http://localhost:${PUERTO}/auth/login/" >/dev/null 2>&1 &) 2>/dev/null
(command -v open >/dev/null && sleep 2 && open "http://localhost:${PUERTO}/auth/login/" >/dev/null 2>&1 &) 2>/dev/null

exec "$PY" manage.py runserver "0.0.0.0:${PUERTO}"
