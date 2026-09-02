#!/usr/bin/env bash
# =============================================================================
#  PL_SGE - Respaldo de la base de datos (Linux / macOS)
# =============================================================================
cd "$(dirname "$0")"
PY=".venv/bin/python"
[ -x "$PY" ] || PY=$(command -v python3 || command -v python)
echo ""
echo " ============================================================================"
echo "   RESPALDO DE LA BASE DE DATOS"
echo " ============================================================================"
echo ""
exec "$PY" scripts/respaldar_bd.py "$@"
