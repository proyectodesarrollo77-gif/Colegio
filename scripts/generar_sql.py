"""
Regenera los scripts SQL distribuidos en database/.

    python scripts/generar_sql.py

Construye una base temporal desde cero con las migraciones de Django y los
comandos de inicializacion, y vuelca de ahi:

    database/02_esquema.sql        estructura completa
    database/03_datos_iniciales.sql  configuracion base (sin datos de demo)
    database/04_verificacion.sql   consulta de comprobacion

De este modo los scripts SQL y las migraciones nunca quedan desfasados: se
generan siempre de una base recien migrada, no de la base de desarrollo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
TEMP_DB = "pl_sge_generacion_sql"

sys.path.insert(0, str(BASE_DIR / "scripts"))
from respaldar_bd import config, find_tool, server_major_version  # noqa: E402

# Tablas cuya informacion se distribuye como configuracion inicial.
DATA_TABLES = [
    "django_content_type",
    "django_migrations",
    "auth_permission",
    "users_role",
    "users_module",
    "users_role_permission",
    "users_user",
    "users_preference",
    "institution",
    "institution_campus",
    "institution_shift",
    "configuration_report_header",
    "configuration_grade_decimal",
    "configuration_parameter",
    "academic_school_year",
    "academic_period",
    "academic_grading_scale",
    "academic_grading_scale_level",
    "academic_valuation_dimension",
    "academic_education_level",
    "academic_grade",
    "academic_group",
    "academic_area",
    "academic_subject",
    "academic_subject_grades",
    "academic_coexistence_item",
    "observer_category",
    "report_definition",
    # --- Configuracion del PAE ---
    "pae_normativa",
    "pae_catalogo",
    "pae_modalidad",
    "pae_tipo_complemento",
    "pae_vigencia",
    "pae_lista_verificacion",
    "pae_lista_item",
]

HEADER = """-- ============================================================================
--  PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
--  {title}
-- ----------------------------------------------------------------------------
--  Motor        : PostgreSQL 14 o superior
--  Codificacion : UTF8
--  Generado     : {date}
--  {note}
-- ============================================================================
"""


def run(command, env=None, check=True):
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"[ERROR] Fallo: {' '.join(str(c) for c in command[:3])} ...")
    return result


def psql_admin(cfg, sql):
    """Ejecuta una sentencia en la base 'postgres' (crear / eliminar base)."""
    import psycopg2

    connection = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], dbname="postgres",
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(sql)
    connection.close()


def build_temp_database(cfg):
    print(f"  Creando base temporal {TEMP_DB} ...")
    psql_admin(cfg, f'DROP DATABASE IF EXISTS "{TEMP_DB}"')
    psql_admin(cfg, f"CREATE DATABASE \"{TEMP_DB}\" WITH ENCODING 'UTF8' TEMPLATE template0")

    env = os.environ.copy()
    env["DB_NAME"] = TEMP_DB
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"

    for label, arguments in (
        ("migraciones", ["migrate", "--no-input"]),
        ("inicializacion", ["initialize_platform"]),
        ("configuracion del PAE", ["seed_pae", "--sin-vigencia"]),
    ):
        print(f"  Aplicando {label} ...")
        run([sys.executable, str(BASE_DIR / "manage.py"), *arguments], env=env)


def counts(cfg):
    import psycopg2

    connection = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], dbname=TEMP_DB,
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        )
        tables = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM pg_indexes WHERE schemaname='public'")
        indexes = cursor.fetchone()[0]
        cursor.execute(
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'"
        )
        foreign_keys = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM users_module")
        modules = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM users_role")
        roles = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM users_role_permission")
        permissions = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM pae_catalogo")
        catalogs = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM information_schema.tables "
                       "WHERE table_schema='public' AND table_name LIKE 'pae\\_%'")
        pae_tables = cursor.fetchone()[0]
    connection.close()
    return {
        "tables": tables, "indexes": indexes, "foreign_keys": foreign_keys,
        "modules": modules, "roles": roles, "permissions": permissions,
        "catalogs": catalogs, "pae_tables": pae_tables,
    }


def clean_dump(text):
    """Quita las lineas de version y de propietario que ensucian el diff."""
    lines = []
    for line in text.splitlines():
        if line.startswith("-- Dumped ") or line.startswith("-- PostgreSQL database dump"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def dump_schema(cfg, pg_dump, env, today):
    print("  Volcando el esquema ...")
    result = run([
        pg_dump, "-h", cfg["host"], "-p", str(cfg["port"]), "-U", cfg["user"],
        "-d", TEMP_DB, "--schema-only", "--no-owner", "--no-privileges", "--no-comments",
    ], env=env)

    header = HEADER.format(
        title="02 - ESQUEMA COMPLETO (tablas, indices, llaves foraneas y restricciones)",
        date=today,
        note="Ejecutar sobre la base pl_sge ya creada (ver 01_crear_base_datos.sql)",
    )
    (DATABASE_DIR / "02_esquema.sql").write_text(header + "\n" + clean_dump(result.stdout), encoding="utf-8")


def dump_data(cfg, pg_dump, env, today):
    print("  Volcando los datos iniciales ...")
    arguments = [
        pg_dump, "-h", cfg["host"], "-p", str(cfg["port"]), "-U", cfg["user"],
        "-d", TEMP_DB, "--data-only", "--no-owner", "--no-privileges",
        "--column-inserts", "--no-comments",
    ]
    for table in DATA_TABLES:
        arguments += ["-t", f"public.{table}"]
    result = run(arguments, env=env)

    header = HEADER.format(
        title="03 - DATOS INICIALES (perfiles, modulos, permisos, institucion, academico, PAE)",
        date=today,
        note="Incluye el usuario Super Admin: admin@datly.local / Admin123*",
    )
    body = (
        "\n-- Se desactivan temporalmente los disparadores para evitar conflictos de\n"
        "-- orden entre llaves foraneas circulares (users_user <-> created_by_id).\n"
        "SET session_replication_role = 'replica';\n\n"
        + clean_dump(result.stdout)
        + "\nSET session_replication_role = 'origin';\n"
    )
    (DATABASE_DIR / "03_datos_iniciales.sql").write_text(header + body, encoding="utf-8")


def write_verification(today, totals):
    print("  Escribiendo la consulta de verificacion ...")
    header = HEADER.format(
        title="04 - VERIFICACION DE LA INSTALACION",
        date=today,
        note="Ejecutar sobre la base pl_sge: compara lo instalado con lo esperado",
    )
    content = f"""{header}
\\echo '== Estructura =='
SELECT 'Tablas'          AS elemento,
       count(*)          AS instalado,
       {totals['tables']}  AS esperado
  FROM information_schema.tables
 WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'Indices', count(*), {totals['indexes']}
  FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 'Llaves foraneas', count(*), {totals['foreign_keys']}
  FROM information_schema.table_constraints
 WHERE constraint_schema = 'public' AND constraint_type = 'FOREIGN KEY'
UNION ALL
SELECT 'Tablas del PAE', count(*), {totals['pae_tables']}
  FROM information_schema.tables
 WHERE table_schema = 'public' AND table_name LIKE 'pae\\_%';

\\echo '== Configuracion =='
SELECT 'Perfiles'                AS elemento, count(*) AS instalado, {totals['roles']} AS esperado FROM users_role
UNION ALL
SELECT 'Modulos',                count(*), {totals['modules']}     FROM users_module
UNION ALL
SELECT 'Permisos por perfil',    count(*), {totals['permissions']} FROM users_role_permission
UNION ALL
SELECT 'Catalogos del PAE',      count(*), {totals['catalogs']}    FROM pae_catalogo
UNION ALL
SELECT 'Instituciones',          count(*), 1                       FROM institution
UNION ALL
SELECT 'Usuarios',               count(*), 1                       FROM users_user;

\\echo '== Super Admin =='
SELECT u.email, r.code AS perfil, u.is_active AS activo
  FROM users_user u JOIN users_role r ON r.id = u.role_id;
"""
    (DATABASE_DIR / "04_verificacion.sql").write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenera los scripts SQL de PL_SGE")
    parser.add_argument("--conservar", action="store_true", help="No elimina la base temporal")
    args = parser.parse_args()

    cfg = config()
    pg_dump = find_tool("pg_dump", prefer=server_major_version(cfg))
    if not pg_dump:
        print("[ERROR] No se encontro pg_dump.")
        return 1

    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["password"]
    today = dt.date.today().isoformat()

    print("PL_SGE - Generacion de los scripts SQL")
    try:
        build_temp_database(cfg)
        totals = counts(cfg)
        dump_schema(cfg, pg_dump, env, today)
        dump_data(cfg, pg_dump, env, today)
        write_verification(today, totals)
    finally:
        if not args.conservar:
            print("  Eliminando la base temporal ...")
            psql_admin(cfg, f'DROP DATABASE IF EXISTS "{TEMP_DB}"')

    print("")
    print(f"  Tablas: {totals['tables']} ({totals['pae_tables']} del PAE)")
    print(f"  Indices: {totals['indexes']} | Llaves foraneas: {totals['foreign_keys']}")
    print(f"  Perfiles: {totals['roles']} | Modulos: {totals['modules']} | "
          f"Permisos: {totals['permissions']} | Catalogos PAE: {totals['catalogs']}")
    print("")
    print("Scripts actualizados en database/: 02_esquema.sql, 03_datos_iniciales.sql, 04_verificacion.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
