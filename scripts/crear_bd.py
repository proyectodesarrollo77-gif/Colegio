"""
Crea la base de datos PostgreSQL de PL_SGE si aun no existe.

Lee la configuracion desde el archivo .env o desde las variables de entorno:
    DB_NAME · DB_USER · DB_PASSWORD · DB_HOST · DB_PORT

    python scripts/crear_bd.py
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
        (BASE_DIR / "database").mkdir(exist_ok=True)
        print("       Motor SQLite configurado: no se requiere crear la base.")
        return 0

    name = os.environ.get("DB_NAME", "pl_sge")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")

    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("       [ERROR] Falta el controlador psycopg2. Ejecute:")
        print("               pip install -r requirements.txt")
        return 1

    try:
        connection = psycopg2.connect(
            host=host, port=port, user=user, password=password,
            dbname="postgres", connect_timeout=8,
        )
    except Exception as exc:
        print(f"       [ERROR] No fue posible conectar a PostgreSQL en {host}:{port}")
        print(f"               {str(exc).strip()}")
        print("               Verifique que el servicio este activo y que las")
        print("               credenciales del archivo .env sean correctas.")
        return 1

    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))

    if cursor.fetchone():
        print(f"       La base de datos '{name}' ya existe, se conserva.")
    else:
        cursor.execute(f'CREATE DATABASE "{name}" WITH ENCODING \'UTF8\' TEMPLATE template0')
        print(f"       Base de datos '{name}' creada correctamente.")

    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0].split(",")[0]
    print(f"       Servidor: {version}")

    cursor.close()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
