#!/usr/bin/env bash
# =============================================================================
#  PL_SGE - Carga de datos de demostracion (Linux / macOS)
# =============================================================================
cd "$(dirname "$0")"
PY=".venv/bin/python"
[ -x "$PY" ] || PY=$(command -v python3 || command -v python)

N="${1:-8}"
echo ""
echo "   Cargando datos de demostracion (${N} estudiantes por grupo)..."
echo ""
"$PY" manage.py seed_demo --students-per-group "$N"
