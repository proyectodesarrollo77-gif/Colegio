"""
Elimina y vuelve a crear la base de datos de PL_SGE.
ATENCION: la operacion es irreversible.

    python scripts/reiniciar_bd.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


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


def main() -> int:
    load_dotenv()

    if os.environ.get("DB_ENGINE", "postgresql") == "sqlite":
        target = BASE_DIR / "database" / "pl_sge.sqlite3"
        if target.exists():
            target.unlink()
            print(f"       Archivo {target.name} eliminado.")
        return 0

    name = os.environ.get("DB_NAME", "pl_sge")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")

    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    try:
        connection = psycopg2.connect(
            host=host, port=port, user=user, password=password, dbname="postgres", connect_timeout=8
        )
    except Exception as exc:
        print(f"       [ERROR] No fue posible conectar a PostgreSQL: {str(exc).strip()}")
        return 1

    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = %s AND pid <> pg_backend_pid()",
        (name,),
    )
    cursor.execute(f'DROP DATABASE IF EXISTS "{name}"')
    cursor.execute(f'CREATE DATABASE "{name}" WITH ENCODING \'UTF8\' TEMPLATE template0')
    print(f"       Base de datos '{name}' recreada vacia.")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
