-- ============================================================================
--  PL_SGE - Plataforma Web Integral de Gestion Academica Institucional
--  04 - VERIFICACION DE LA INSTALACION
-- ----------------------------------------------------------------------------
--  Motor        : PostgreSQL 14 o superior
--  Codificacion : UTF8
--  Generado     : 2026-08-27
--  Ejecutar sobre la base pl_sge: compara lo instalado con lo esperado
-- ============================================================================

\echo '== Estructura =='
SELECT 'Tablas'          AS elemento,
       count(*)          AS instalado,
       157  AS esperado
  FROM information_schema.tables
 WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'Indices', count(*), 1593
  FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 'Llaves foraneas', count(*), 785
  FROM information_schema.table_constraints
 WHERE constraint_schema = 'public' AND constraint_type = 'FOREIGN KEY'
UNION ALL
SELECT 'Tablas del PAE', count(*), 39
  FROM information_schema.tables
 WHERE table_schema = 'public' AND table_name LIKE 'pae\_%';

\echo '== Configuracion =='
SELECT 'Perfiles'                AS elemento, count(*) AS instalado, 14 AS esperado FROM users_role
UNION ALL
SELECT 'Modulos',                count(*), 128     FROM users_module
UNION ALL
SELECT 'Permisos por perfil',    count(*), 671 FROM users_role_permission
UNION ALL
SELECT 'Catalogos del PAE',      count(*), 85    FROM pae_catalogo
UNION ALL
SELECT 'Instituciones',          count(*), 1                       FROM institution
UNION ALL
SELECT 'Usuarios',               count(*), 1                       FROM users_user;

\echo '== Super Admin =='
SELECT u.email, r.code AS perfil, u.is_active AS activo
  FROM users_user u JOIN users_role r ON r.id = u.role_id;
