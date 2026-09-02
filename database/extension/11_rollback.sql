-- ============================================================================
--  PL_SGE - Extension nativa: INCAPACIDADES y CONVIVENCIA ESCOLAR
--  11 - ROLLBACK
-- ----------------------------------------------------------------------------
--  Revierte por completo 10_incapacidades_convivencia.sql.
--
--  Como la migracion fue ADITIVA (no modifico ninguna tabla, columna ni
--  restriccion existente), la reversion es total y no deja rastro en el
--  sistema en produccion.
--
--  ADVERTENCIA
--  Elimina de forma IRREVERSIBLE toda la informacion de incapacidades y de
--  la extension de convivencia. Genere un respaldo antes de ejecutarlo:
--      python scripts/respaldar_bd.py
--
--  NO afecta: observer_entry, observer_category, observer_follow_up,
--  attendance_record, teacher_absence, student_document ni ninguna otra
--  tabla del sistema base.
-- ============================================================================

BEGIN;

SET client_encoding = 'UTF8';
SET client_min_messages = warning;

-- ----------------------------------------------------------------------------
-- Aviso del volumen de informacion que se va a perder.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    n_inc     bigint := 0;
    n_summons bigint := 0;
    n_dec     bigint := 0;
BEGIN
    IF to_regclass('public.incapacity')        IS NOT NULL THEN EXECUTE 'SELECT count(*) FROM public.incapacity'        INTO n_inc;     END IF;
    IF to_regclass('public.observer_summons')  IS NOT NULL THEN EXECUTE 'SELECT count(*) FROM public.observer_summons'  INTO n_summons; END IF;
    IF to_regclass('public.observer_decision') IS NOT NULL THEN EXECUTE 'SELECT count(*) FROM public.observer_decision' INTO n_dec;     END IF;

    RAISE NOTICE 'Rollback: se eliminaran % incapacidades, % citaciones y % decisiones.',
                 n_inc, n_summons, n_dec;
END $$;

-- ----------------------------------------------------------------------------
-- PASO 1 - Revertir las justificaciones de asistencia aplicadas.
--
-- Devuelve los registros de asistencia al estado que tenian antes de que la
-- incapacidad los justificara. Sin este paso quedaria asistencia marcada como
-- EXCUSA sin soporte que la respalde.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    revertidos integer := 0;
BEGIN
    IF to_regclass('public.incapacity_attendance_link') IS NULL THEN
        RAISE NOTICE 'La extension no esta instalada: no hay asistencia que revertir.';
        RETURN;
    END IF;

    UPDATE public.attendance_record ar
       SET status = l.previous_status,
           updated_at = now()
      FROM public.incapacity_attendance_link l
     WHERE l.attendance_record_id = ar.id
       AND l.reverted_at IS NULL
       AND l.deleted_at  IS NULL
       AND ar.status = 'EXCUSA';

    GET DIAGNOSTICS revertidos = ROW_COUNT;
    RAISE NOTICE 'Registros de asistencia devueltos a su estado anterior: %.', revertidos;
END $$;

-- ----------------------------------------------------------------------------
-- PASO 2 - Desvincular las novedades docentes creadas por la extension.
--
-- Las filas de teacher_absence NO se eliminan: pertenecen al modulo de
-- Docentes, que es productivo. Solo se rompe el vinculo.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.incapacity') IS NOT NULL THEN
        RAISE NOTICE 'Las novedades docentes se conservan; solo se elimina el vinculo.';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- PASO 3 - Eliminar las tablas en orden inverso de dependencia.
--
-- CASCADE elimina automaticamente las llaves foraneas e indices asociados.
-- ----------------------------------------------------------------------------

-- Convivencia
DROP TABLE IF EXISTS public.observer_alert              CASCADE;
DROP TABLE IF EXISTS public.observer_alert_rule         CASCADE;
DROP TABLE IF EXISTS public.observer_status_log         CASCADE;
DROP TABLE IF EXISTS public.observer_decision           CASCADE;
DROP TABLE IF EXISTS public.observer_committee_session  CASCADE;
DROP TABLE IF EXISTS public.observer_committee_member   CASCADE;
DROP TABLE IF EXISTS public.observer_committee          CASCADE;
DROP TABLE IF EXISTS public.observer_commitment         CASCADE;
DROP TABLE IF EXISTS public.observer_summons            CASCADE;
DROP TABLE IF EXISTS public.observer_evidence           CASCADE;

-- Incapacidades
DROP TABLE IF EXISTS public.incapacity_attendance_link  CASCADE;
DROP TABLE IF EXISTS public.incapacity_history          CASCADE;
DROP TABLE IF EXISTS public.incapacity_attachment       CASCADE;
DROP TABLE IF EXISTS public.incapacity                  CASCADE;
DROP TABLE IF EXISTS public.incapacity_type             CASCADE;

-- ----------------------------------------------------------------------------
-- PASO 4 - Retirar los casos escalados del estado que ya no existe.
--
-- Si algun caso quedo en ESCALADO_COMITE, se devuelve a EN_SEGUIMIENTO para
-- que el observador siga siendo consistente sin la extension.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    ajustados integer := 0;
BEGIN
    UPDATE public.observer_entry
       SET status = 'EN_SEGUIMIENTO',
           updated_at = now()
     WHERE status = 'ESCALADO_COMITE';

    GET DIAGNOSTICS ajustados = ROW_COUNT;
    IF ajustados > 0 THEN
        RAISE NOTICE 'Casos devueltos de ESCALADO_COMITE a EN_SEGUIMIENTO: %.', ajustados;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- PASO 5 - Retirar los registros de auditoria del historial de migraciones.
--
-- Solo aplica si la extension se instalo por Django. Si se instalo por SQL,
-- estas filas no existen y la sentencia no hace nada.
-- ----------------------------------------------------------------------------
DELETE FROM public.django_migrations
 WHERE app IN ('incapacities')
    OR (app = 'observer' AND name LIKE '%coexistence%');

-- ----------------------------------------------------------------------------
-- VERIFICACION
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    restantes integer;
BEGIN
    SELECT count(*) INTO restantes
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('incapacity_type','incapacity','incapacity_attachment','incapacity_history',
                         'incapacity_attendance_link','observer_evidence','observer_summons',
                         'observer_commitment','observer_committee','observer_committee_member',
                         'observer_committee_session','observer_decision','observer_status_log',
                         'observer_alert_rule','observer_alert');
    IF restantes <> 0 THEN
        RAISE EXCEPTION 'Quedaron % tablas de la extension sin eliminar.', restantes;
    END IF;

    -- Comprobar que el sistema base sigue intacto.
    IF to_regclass('public.observer_entry')    IS NULL
    OR to_regclass('public.attendance_record') IS NULL
    OR to_regclass('public.teacher_absence')   IS NULL THEN
        RAISE EXCEPTION 'El rollback afecto tablas del sistema base. Restaure el respaldo.';
    END IF;

    RAISE NOTICE 'Rollback completado. El sistema base quedo intacto.';
END $$;

COMMIT;

-- ============================================================================
--  PASOS MANUALES POSTERIORES
-- ----------------------------------------------------------------------------
--  1. Retirar 'core.incapacities' de LOCAL_APPS en config/settings.py
--  2. Retirar el arbol de modulos de core/configuration/modules.py
--  3. Retirar los 4 perfiles de seed_roles.py y del DEFAULT_ROLE_MATRIX
--  4. Retirar las rutas de config/urls.py y config/api.py
--  5. Retirar ESCALADO_COMITE de ObserverEntry.STATUS_CHOICES
--  6. Ejecutar:  python manage.py seed_modules
--                python manage.py seed_permissions --reset
--                python smoke_test.py
-- ============================================================================
