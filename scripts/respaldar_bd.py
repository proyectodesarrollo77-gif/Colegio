"""
Respaldo de la base de datos PostgreSQL de PL_SGE.

    python scripts/respaldar_bd.py            genera un respaldo con fecha
    python scripts/respaldar_bd.py --listar   muestra los respaldos existentes

El archivo se guarda en database/respaldos/ en formato comprimido de PostgreSQL
(-Fc), restaurable con pg_restore.
"""
from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "database" / "respaldos"

PG_VERSIONS = ("18", "17", "16", "15", "14")


def load_dotenv():
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def server_major_version(cfg):
    """Version mayor del servidor PostgreSQL, para elegir herramientas compatibles."""
    try:
        import psycopg2

        connection = psycopg2.connect(
            host=cfg["host"], port=cfg["port"], user=cfg["user"],
            password=cfg["password"], dbname="postgres", connect_timeout=5,
        )
        version = connection.server_version  # ej. 160014 -> 16
        connection.close()
        return str(version // 10000)
    except Exception:
        return None


def find_tool(name, prefer=None):
    """
    Localiza pg_dump / pg_restore.

    Prioriza la version que coincide con el servidor: usar pg_restore de una
    version superior genera advertencias por parametros desconocidos.
    """
    from shutil import which

    candidates = []

    if os.name == "nt":
        roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", "")]
        versions = ([prefer] if prefer else []) + [v for v in PG_VERSIONS if v != prefer]
        for version in versions:
            for root in roots:
                if not root:
                    continue
                candidate = Path(root) / "PostgreSQL" / version / "bin" / f"{name}.exe"
                if candidate.exists():
                    candidates.append(str(candidate))
    else:
        versions = ([prefer] if prefer else []) + [v for v in PG_VERSIONS if v != prefer]
        for version in versions:
            for pattern in (f"/usr/lib/postgresql/{version}/bin/{name}",
                            f"/usr/pgsql-{version}/bin/{name}",
                            f"/opt/homebrew/opt/postgresql@{version}/bin/{name}"):
                if Path(pattern).exists():
                    candidates.append(pattern)

    if candidates:
        return candidates[0]

    found = which(name)
    if found:
        return found

    if os.name != "nt":
        for candidate in (f"/usr/bin/{name}", f"/usr/local/bin/{name}", f"/opt/homebrew/bin/{name}"):
            if Path(candidate).exists():
                return candidate
    return None


def config():
    load_dotenv()
    return {
        "name": os.environ.get("DB_NAME", "pl_sge"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "postgres"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
    }


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def listar():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    archivos = sorted(BACKUP_DIR.glob("*.backup"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not archivos:
        print("       No hay respaldos generados todavia.")
        return archivos
    print(f"       {'ARCHIVO':<40}{'TAMANO':>12}   FECHA")
    print("       " + "-" * 74)
    for item in archivos:
        stat = item.stat()
        fecha = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        print(f"       {item.name:<40}{human(stat.st_size):>12}   {fecha}")
    return archivos


def main() -> int:
    parser = argparse.ArgumentParser(description="Respaldo de la base de datos de PL_SGE")
    parser.add_argument("--listar", action="store_true", help="Solo listar los respaldos existentes")
    args = parser.parse_args()

    if args.listar:
        listar()
        return 0

    cfg = config()

    if os.environ.get("DB_ENGINE", "postgresql") == "sqlite":
        import shutil

        origen = BASE_DIR / "database" / "pl_sge.sqlite3"
        if not origen.exists():
            print("       [ERROR] No se encontro la base SQLite.")
            return 1
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = BACKUP_DIR / f"pl_sge_{sello}.sqlite3"
        shutil.copy2(origen, destino)
        print(f"       Respaldo creado: {destino.name} ({human(destino.stat().st_size)})")
        return 0

    pg_dump = find_tool("pg_dump", prefer=server_major_version(cfg))
    if not pg_dump:
        print("       [ERROR] No se encontro pg_dump.")
        print("               Instale PostgreSQL o agregue su carpeta bin al PATH.")
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUP_DIR / f"pl_sge_{sello}.backup"

    print(f"       Base de datos : {cfg['name']}")
    print(f"       Servidor      : {cfg['host']}:{cfg['port']}")
    print(f"       Herramienta   : {pg_dump}")
    print(f"       Archivo       : {destino}")
    print("")
    print("       Generando respaldo...")

    entorno = os.environ.copy()
    entorno["PGPASSWORD"] = cfg["password"]

    resultado = subprocess.run(
        [pg_dump, "-h", cfg["host"], "-p", cfg["port"], "-U", cfg["user"],
         "-d", cfg["name"], "-Fc", "--no-owner", "--no-privileges", "-f", str(destino)],
        env=entorno, capture_output=True, text=True,
    )

    if resultado.returncode != 0:
        print("       [ERROR] Fallo la generacion del respaldo:")
        print("       " + (resultado.stderr or "").strip()[:600])
        if destino.exists():
            destino.unlink()
        return 1

    print(f"       Respaldo creado correctamente ({human(destino.stat().st_size)}).")
    print("")
    print("       Respaldos disponibles:")
    listar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
