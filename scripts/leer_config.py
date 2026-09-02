"""
Imprime la configuracion de la base de datos en formato CLAVE=valor
para que los scripts .bat la carguen con FOR /F.

    python scripts/leer_config.py
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

print(f"DB_NAME={os.environ.get('DB_NAME', 'pl_sge')}")
print(f"DB_USER={os.environ.get('DB_USER', 'postgres')}")
print(f"DB_PASSWORD={os.environ.get('DB_PASSWORD', 'postgres')}")
print(f"DB_HOST={os.environ.get('DB_HOST', 'localhost')}")
print(f"DB_PORT={os.environ.get('DB_PORT', '5432')}")
