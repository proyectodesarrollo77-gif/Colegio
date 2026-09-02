-- ============================================================================
--  PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
--  01 - CREACION DE LA BASE DE DATOS Y DEL ROL DE APLICACION
-- ----------------------------------------------------------------------------
--  Motor        : PostgreSQL 14 o superior
--  Codificacion : UTF8
--
--  Ejecutar CONECTADO A LA BASE 'postgres' con un superusuario:
--
--      psql -U postgres -d postgres -f 01_crear_base_datos.sql
--
--  Este script NO puede ejecutarse dentro de una transaccion porque
--  CREATE DATABASE no lo permite.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. Rol de aplicacion
--    Cambie la contrasena antes de usar en produccion.
-- ----------------------------------------------------------------------------
DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pl_sge_app') THEN
        CREATE ROLE pl_sge_app WITH
            LOGIN
            PASSWORD 'CambieEstaClave2026*'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            CONNECTION LIMIT -1;
        RAISE NOTICE 'Rol pl_sge_app creado.';
    ELSE
        RAISE NOTICE 'El rol pl_sge_app ya existe, se conserva.';
    END IF;
END
$$;


-- ----------------------------------------------------------------------------
-- 2. Base de datos
-- ----------------------------------------------------------------------------
CREATE DATABASE pl_sge
    WITH
    OWNER      = pl_sge_app
    ENCODING   = 'UTF8'
    TEMPLATE   = template0
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE pl_sge IS
    'PL_SGE - Plataforma Web Integral de Gestion Academica Institucional';


-- ----------------------------------------------------------------------------
-- 3. Privilegios
-- ----------------------------------------------------------------------------
GRANT ALL PRIVILEGES ON DATABASE pl_sge TO pl_sge_app;


-- ============================================================================
--  SIGUIENTE PASO
--
--      psql -U postgres -d pl_sge -f 02_esquema.sql
--      psql -U postgres -d pl_sge -f 03_datos_iniciales.sql
--
--  O, de forma equivalente y recomendada, desde la raiz del proyecto:
--
--      python manage.py migrate
--      python manage.py initialize_platform
-- ============================================================================
