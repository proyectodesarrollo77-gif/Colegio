"""
Restauracion de la base de datos PostgreSQL de PL_SGE.

    python scripts/restaurar_bd.py                  elige el respaldo de forma interactiva
    python scripts/restaurar_bd.py archivo.backup   restaura el archivo indicado
    python scripts/restaurar_bd.py --ultimo         restaura el respaldo mas reciente

ATENCION: la informacion actual de la base se reemplaza por la del respaldo.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "database" / "respaldos"

sys.path.insert(0, str(BASE_DIR / "scripts"))
from respaldar_bd import config, find_tool, human, listar, server_major_version  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Restauracion de la base de datos de PL_SGE")
    parser.add_argument("archivo", nargs="?", help="Nombre del archivo de respaldo")
    parser.add_argument("--ultimo", action="store_true", help="Restaurar el respaldo mas reciente")
    parser.add_argument("--si", action="store_true", help="No solicitar confirmacion")
    args = parser.parse_args()

    cfg = config()
    disponibles = sorted(BACKUP_DIR.glob("*.backup"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not disponibles:
        print("       [ERROR] No hay respaldos en database/respaldos/")
        return 1

    if args.ultimo:
        elegido = disponibles[0]
    elif args.archivo:
        elegido = BACKUP_DIR / args.archivo
        if not elegido.exists():
            print(f"       [ERROR] No se encontro el archivo {elegido}")
            return 1
    else:
        print("       Respaldos disponibles:")
        print("")
        listar()
        print("")
        nombre = input("       Nombre del archivo a restaurar (Enter = el mas reciente): ").strip()
        elegido = BACKUP_DIR / nombre if nombre else disponibles[0]
        if not elegido.exists():
            print(f"       [ERROR] No se encontro el archivo {elegido}")
            return 1

    print("")
    print(f"       Base de datos : {cfg['name']}")
    print(f"       Respaldo      : {elegido.name} ({human(elegido.stat().st_size)})")
    print("")
    print("       ATENCION: la informacion actual sera reemplazada.")

    if not args.si:
        confirmacion = input("       Escriba RESTAURAR para confirmar: ").strip().upper()
        if confirmacion != "RESTAURAR":
            print("       Operacion cancelada.")
            return 0

    pg_restore = find_tool("pg_restore", prefer=server_major_version(cfg))
    if not pg_restore:
        print("       [ERROR] No se encontro pg_restore.")
        return 1

    entorno = os.environ.copy()
    entorno["PGPASSWORD"] = cfg["password"]

    print("")
    print("       Restaurando...")
    resultado = subprocess.run(
        [pg_restore, "-h", cfg["host"], "-p", cfg["port"], "-U", cfg["user"], "-d", cfg["name"],
         "--clean", "--if-exists", "--no-owner", "--no-privileges", str(elegido)],
        env=entorno, capture_output=True, text=True,
    )

    # pg_restore devuelve 1 con advertencias no criticas; se informa sin abortar.
    errores = [l for l in (resultado.stderr or "").splitlines() if "error" in l.lower()]
    if errores:
        print(f"       Se registraron {len(errores)} advertencias durante la restauracion:")
        for linea in errores[:5]:
            print("         " + linea.strip()[:140])

    print("")
    print("       Restauracion finalizada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
