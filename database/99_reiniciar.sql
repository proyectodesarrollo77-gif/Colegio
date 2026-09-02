-- ============================================================================
--  PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
--  99 - REINICIO TOTAL DE LA BASE DE DATOS
-- ----------------------------------------------------------------------------
--  ATENCION: este script ELIMINA de forma irreversible toda la informacion
--  academica, administrativa y de auditoria almacenada en la base pl_sge.
--
--  Ejecutar CONECTADO A LA BASE 'postgres' con un superusuario:
--
--      psql -U postgres -d postgres -f 99_reiniciar.sql
-- ============================================================================


-- 1. Cerrar las conexiones abiertas contra la base.
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'pl_sge'
  AND pid <> pg_backend_pid();


-- 2. Eliminar la base de datos.
DROP DATABASE IF EXISTS pl_sge;


-- 3. Volver a crearla vacia.
CREATE DATABASE pl_sge
    WITH
    OWNER      = pl_sge_app
    ENCODING   = 'UTF8'
    TEMPLATE   = template0
    CONNECTION LIMIT = -1;

GRANT ALL PRIVILEGES ON DATABASE pl_sge TO pl_sge_app;


-- ============================================================================
--  SIGUIENTE PASO
--      psql -U postgres -d pl_sge -f 02_esquema.sql
--      psql -U postgres -d pl_sge -f 03_datos_iniciales.sql
-- ============================================================================
