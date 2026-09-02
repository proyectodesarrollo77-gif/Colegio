"""
Inicializa PL_SGE lista para operar:

    python manage.py initialize_platform

  * Perfiles institucionales y modulos
  * Matriz de permisos por defecto
  * Usuario Super Admin (admin@datly.local / Admin123*)
  * Institucion, sedes y jornadas base
  * Ano lectivo con periodos, escala valorativa y desempenos
  * Niveles educativos, grados, grupos, areas y asignaturas
  * Parametros del sistema, encabezado de reportes y catalogo de reportes
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from config.permissions import invalidate_permission_cache

SUPER_ADMIN = {
    "email": "admin@datly.local",
    "username": "admin",
    "first_name": "Super",
    "last_name": "Admin",
    "password": "Admin123*",
}

LEVELS = [
    ("PRE", "Preescolar", True, "CUALITATIVA", 1),
    ("BPR", "Basica Primaria", False, "CUANTITATIVA", 2),
    ("BSE", "Basica Secundaria", False, "CUANTITATIVA", 3),
    ("MED", "Media", False, "CUANTITATIVA", 4),
]

GRADES = [
    ("PRE", "T", "Transicion", 0, 5, 6, False),
    ("BPR", "1", "Primero", 1, 6, 7, False),
    ("BPR", "2", "Segundo", 2, 7, 8, False),
    ("BPR", "3", "Tercero", 3, 8, 9, False),
    ("BPR", "4", "Cuarto", 4, 9, 10, False),
    ("BPR", "5", "Quinto", 5, 10, 11, False),
    ("BSE", "6", "Sexto", 6, 11, 12, False),
    ("BSE", "7", "Septimo", 7, 12, 13, False),
    ("BSE", "8", "Octavo", 8, 13, 14, False),
    ("BSE", "9", "Noveno", 9, 14, 15, False),
    ("MED", "10", "Decimo", 10, 15, 16, False),
    ("MED", "11", "Once", 11, 16, 18, True),
]

AREAS = [
    ("MAT", "Matematicas", "#4F46E5"),
    ("LEN", "Humanidades - Lengua Castellana", "#0EA5E9"),
    ("ING", "Humanidades - Idioma Extranjero", "#14B8A6"),
    ("CNA", "Ciencias Naturales y Educacion Ambiental", "#10B981"),
    ("CSO", "Ciencias Sociales", "#F59E0B"),
    ("EFI", "Educacion Fisica, Recreacion y Deportes", "#EF4444"),
    ("ART", "Educacion Artistica y Cultural", "#A855F7"),
    ("ETI", "Educacion Etica y en Valores Humanos", "#EC4899"),
    ("REL", "Educacion Religiosa", "#6366F1"),
    ("TEC", "Tecnologia e Informatica", "#0284C7"),
]

SUBJECTS = [
    ("MAT", "MAT01", "Matematicas", 5, False),
    ("MAT", "GEO01", "Geometria", 1, False),
    ("MAT", "EST01", "Estadistica", 1, False),
    ("LEN", "LEN01", "Lengua Castellana", 4, False),
    ("LEN", "LEC01", "Plan Lector", 1, False),
    ("ING", "ING01", "Ingles", 4, True),
    ("CNA", "BIO01", "Biologia", 3, False),
    ("CNA", "QUI01", "Quimica", 2, False),
    ("CNA", "FIS01", "Fisica", 2, False),
    ("CSO", "SOC01", "Ciencias Sociales", 4, False),
    ("CSO", "POL01", "Ciencias Politicas y Economicas", 1, False),
    ("EFI", "EFI01", "Educacion Fisica", 2, False),
    ("ART", "ART01", "Artistica", 2, False),
    ("ETI", "ETI01", "Etica y Valores", 1, False),
    ("REL", "REL01", "Educacion Religiosa", 1, False),
    ("TEC", "TEC01", "Tecnologia e Informatica", 2, False),
]

DIMENSIONS = [
    ("COG", "Cognitiva", Decimal("40.00"), 1),
    ("PRO", "Procedimental", Decimal("40.00"), 2),
    ("ACT", "Actitudinal", Decimal("20.00"), 3),
]

PERFORMANCE_LEVELS = [
    ("SUP", "Superior", "Desempeno Superior", Decimal("4.60"), Decimal("5.00"), "#059669", True, 1),
    ("ALT", "Alto", "Desempeno Alto", Decimal("4.00"), Decimal("4.59"), "#0EA5E9", True, 2),
    ("BAS", "Basico", "Desempeno Basico", Decimal("3.00"), Decimal("3.99"), "#F59E0B", True, 3),
    ("BAJ", "Bajo", "Desempeno Bajo", Decimal("1.00"), Decimal("2.99"), "#EF4444", False, 4),
]

COEXISTENCE = [
    ("COM", "Comportamiento en clase", "COMPORTAMIENTO"),
    ("PUN", "Puntualidad y asistencia", "PUNTUALIDAD"),
    ("PRE", "Presentacion personal", "PRESENTACION"),
    ("RES", "Responsabilidad academica", "RESPONSABILIDAD"),
    ("CON", "Convivencia y respeto", "CONVIVENCIA"),
]

OBSERVER_CATEGORIES = [
    ("T1", "Situacion tipo I", "TIPO_I", "#F59E0B", False, False, "Art. 40"),
    ("T2", "Situacion tipo II", "TIPO_II", "#EF4444", True, True, "Art. 41"),
    ("T3", "Situacion tipo III", "TIPO_III", "#991B1B", True, True, "Art. 42"),
    ("REC", "Reconocimiento positivo", "POSITIVA", "#10B981", False, False, ""),
    ("ACA", "Seguimiento academico", "ACADEMICA", "#0EA5E9", False, False, ""),
    ("INF", "Anotacion informativa", "INFORMATIVA", "#667085", False, False, ""),
]

PARAMETERS = [
    ("INSTITUTION_SHORT_NAME", "Nombre corto institucional", "", "STRING", "General"),
    ("GRADE_DECIMALS", "Decimales de nota", "1", "INT", "Academico"),
    ("PASSING_GRADE", "Nota aprobatoria", "3.00", "DECIMAL", "Academico"),
    ("MAX_FAILED_SUBJECTS", "Maximo de asignaturas perdidas para promocion", "2", "INT", "Academico"),
    ("ENROLLMENT_OPEN", "Matriculas abiertas", "true", "BOOL", "Academico"),
    ("SESSION_TIMEOUT_MINUTES", "Minutos de inactividad antes de cerrar sesion", "60", "INT", "Seguridad"),
    ("FORCE_2FA_STAFF", "Exigir 2FA al personal administrativo", "false", "BOOL", "Seguridad"),
    ("NOTIFY_GUARDIANS_OBSERVER", "Notificar acudientes al crear observaciones", "true", "BOOL", "Notificaciones"),
    ("NOTIFY_GRADES_PUBLISHED", "Notificar publicacion de boletines", "true", "BOOL", "Notificaciones"),
    ("CERTIFICATE_PREFIX", "Prefijo de consecutivo de certificados", "CE", "STRING", "Documentos"),
]

REPORTS = [
    ("STUDENTS_LIST", "Listado de estudiantes", "ADMINISTRATIVO", "Poblacion estudiantil con datos de contacto y estado.", "graduation-cap"),
    ("ENROLLMENT_LIST", "Listado de matriculas", "ADMINISTRATIVO", "Matriculas del ano lectivo por grupo y estado.", "clipboard-check"),
    ("GRADES_SHEET", "Planilla de notas", "ACADEMICO", "Notas por asignatura, periodo y grupo.", "clipboard-check"),
    ("REPORT_CARDS", "Boletines de periodo", "ACADEMICO", "Boletines consolidados por grupo y periodo.", "file-text"),
    ("PROMOTION_RESULTS", "Resultados de promocion", "ACADEMICO", "Promocion, puestos y cuadro de honor.", "award"),
    ("RECOVERY_RESULTS", "Resultados de recuperacion", "ACADEMICO", "Nivelaciones y habilitaciones evaluadas.", "refresh"),
    ("ACADEMIC_STATISTICS", "Estadisticas academicas", "ESTADISTICO", "Promedios por area, periodo y desempeno.", "bar-chart"),
    ("ATTENDANCE_SUMMARY", "Consolidado de asistencia", "ASISTENCIA", "Inasistencias y porcentaje de asistencia.", "calendar-check"),
    ("OBSERVER_ENTRIES", "Reporte del observador", "CONVIVENCIA", "Anotaciones disciplinarias por tipificacion.", "eye"),
    ("TEACHERS_LIST", "Planta docente", "ADMINISTRATIVO", "Docentes, vinculacion y carga academica.", "presentation"),
    ("USERS_LIST", "Usuarios de la plataforma", "ADMINISTRATIVO", "Cuentas, perfiles y estado de acceso.", "users"),
    ("CERTIFICATES", "Certificados emitidos", "ADMINISTRATIVO", "Historial de certificados y constancias.", "file-text"),
    ("EMPHASIS_ENROLLMENT", "Matriculas de enfasis", "ADMINISTRATIVO", "Inscripciones por enfasis y disciplina.", "target"),
    ("AUDIT_LOG", "Bitacora de auditoria", "ADMINISTRATIVO", "Trazabilidad completa de operaciones.", "shield-check"),
]


class Command(BaseCommand):
    help = "Inicializa la plataforma con perfiles, permisos, institucion y estructura academica"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=timezone.localdate().year,
                            help="Ano lectivo a crear (por defecto el ano en curso).")
        parser.add_argument("--groups-per-grade", type=int, default=2,
                            help="Cantidad de grupos a crear por grado.")
        parser.add_argument("--skip-academic", action="store_true",
                            help="No crear la estructura academica de ejemplo.")
        parser.add_argument("--skip-pae", action="store_true",
                            help="No cargar la configuracion del Programa de Alimentacion Escolar.")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("PL_SGE - Inicializacion de la plataforma"))

        call_command("seed_roles")
        call_command("seed_modules")
        call_command("seed_permissions")

        institution = self._institution()
        admin = self._super_admin(institution)
        self._parameters(institution)
        self._reports()
        self._observer_categories()

        if not options["skip_academic"]:
            year = self._school_year(institution, options["year"])
            self._periods(year)
            scale = self._scale(year)
            self._dimensions(year)
            self._coexistence(year)
            self._report_header(institution)
            self._grade_config(year)
            levels = self._levels(institution)
            grades = self._grades(levels)
            self._groups(year, grades, options["groups_per_grade"])
            areas = self._areas(year)
            self._subjects(areas, grades)
            self.stdout.write(f"  Escala valorativa: {scale.name}")

        # La configuracion del PAE se carga despues del ano lectivo: la
        # vigencia del programa se apoya en el (no crea un calendario propio).
        if not options["skip_pae"]:
            call_command("seed_pae", sin_vigencia=options["skip_academic"])

        invalidate_permission_cache()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Plataforma inicializada correctamente."))
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  Acceso Super Administrador"))
        self.stdout.write(f"    URL       : /auth/login/")
        self.stdout.write(f"    Usuario   : {admin.email}")
        self.stdout.write(f"    Contrasena: {SUPER_ADMIN['password']}")
        self.stdout.write("")

    # ------------------------------------------------------------------
    # Bloques de inicializacion
    # ------------------------------------------------------------------
    def _institution(self):
        from core.institutions.models import Campus, Institution, Shift

        # La plataforma admite varias instituciones. Este comando NO debe crear
        # una nueva cuando ya hay alguna: adopta la predeterminada y trabaja
        # sobre ella. Buscarla por un codigo fijo duplicaba la institucion en
        # cuanto el usuario le cambiaba el codigo DANE, y la duplicada se
        # quedaba con la marca de predeterminada.
        institution = (
            Institution.objects.filter(is_default=True).first()
            or Institution.objects.filter(code="000000000000").first()
            or Institution.objects.order_by("id").first()
        )
        created = institution is None
        if created:
            institution = Institution.objects.create(
                code="000000000000",
                name="Institucion Educativa Datly",
                short_name="IE Datly",
                nit="900000000-1",
                resolution="Resolucion de aprobacion No. 0000 de 2020",
                nature="PRIVADA",
                calendar="A",
                department="Cundinamarca",
                city="Bogota D.C.",
                address="Calle 100 No. 10 - 20",
                phone="(601) 000 0000",
                email="contacto@datly.local",
                rector_name="Nombre del Rector",
                secretary_name="Nombre de la Secretaria",
                motto="Educacion con proposito",
                is_default=True,
            )
        Campus.objects.get_or_create(
            institution=institution,
            code="SEDE-A",
            defaults={"name": "Sede Principal", "address": institution.address, "is_main": True},
        )
        for code, name, start, end, order in [
            ("MAN", "Manana", dt.time(6, 30), dt.time(12, 30), 1),
            ("TAR", "Tarde", dt.time(12, 30), dt.time(18, 0), 2),
            ("UNI", "Unica", dt.time(7, 0), dt.time(15, 0), 3),
        ]:
            Shift.objects.get_or_create(
                institution=institution,
                code=code,
                defaults={"name": name, "start_time": start, "end_time": end, "order": order},
            )
        self.stdout.write(f"  Institucion: {institution.name} ({'creada' if created else 'existente'})")
        return institution

    def _super_admin(self, institution):
        from core.users.models import Role, User

        role = Role.objects.get(code=Role.SUPER_ADMIN)
        user = User.objects.filter(email=SUPER_ADMIN["email"]).first()
        if user is None:
            user = User(
                email=SUPER_ADMIN["email"],
                username=SUPER_ADMIN["username"],
                first_name=SUPER_ADMIN["first_name"],
                last_name=SUPER_ADMIN["last_name"],
                role=role,
                institution=institution,
                is_staff=True,
                is_superuser=True,
                is_active=True,
                email_verified=True,
                must_change_password=False,
            )
            user.set_password(SUPER_ADMIN["password"])
            user.save()
            self.stdout.write("  Super Admin: creado")
        else:
            user.role = role
            # Solo se le asigna institucion si aun no tiene: reasignarla movia
            # al administrador a otra institucion al reejecutar el comando.
            if user.institution_id is None:
                user.institution = institution
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.email_verified = True
            user.save()
            self.stdout.write("  Super Admin: actualizado")
        return user

    def _parameters(self, institution=None):
        from core.configuration.models import SystemParameter

        for key, label, value, value_type, group in PARAMETERS:
            if key == "INSTITUTION_SHORT_NAME" and institution is not None:
                value = institution.short_name or institution.name
            SystemParameter.objects.get_or_create(
                key=key,
                defaults={"label": label, "value": value, "value_type": value_type, "group": group},
            )
        self.stdout.write(f"  Parametros del sistema: {SystemParameter.objects.count()}")

    def _reports(self):
        from core.reports.models import ReportDefinition

        for order, (code, name, category, description, icon) in enumerate(REPORTS, start=1):
            ReportDefinition.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "description": description,
                    "icon": icon,
                    "order": order,
                    "default_output": "XLSX",
                    "allowed_outputs": ["XLSX", "CSV", "PDF"],
                    "required_module": f"reports.{category.lower()[:11]}",
                },
            )
        self.stdout.write(f"  Catalogo de reportes: {ReportDefinition.objects.count()}")

    def _observer_categories(self):
        from core.observer.models import ObservationCategory

        for order, (code, name, severity, color, guardian, commitment, article) in enumerate(
            OBSERVER_CATEGORIES, start=1
        ):
            ObservationCategory.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "severity": severity,
                    "color": color,
                    "requires_guardian": guardian,
                    "requires_commitment": commitment,
                    "manual_article": article,
                    "order": order,
                },
            )
        self.stdout.write(f"  Tipos de observacion: {ObservationCategory.objects.count()}")

    def _school_year(self, institution, year):
        from core.academic.models import SchoolYear

        school_year, _ = SchoolYear.objects.get_or_create(
            institution=institution,
            year=year,
            defaults={
                "name": f"Ano lectivo {year}",
                "start_date": dt.date(year, 1, 20),
                "end_date": dt.date(year, 11, 30),
                "status": "ACTIVO",
                "is_current": True,
                "weeks": 40,
            },
        )
        if not school_year.is_current:
            school_year.is_current = True
            school_year.save(update_fields=["is_current"])
        self.stdout.write(f"  Ano lectivo: {school_year.name}")
        return school_year

    def _periods(self, year):
        from core.academic.models import AcademicPeriod

        blocks = [
            (1, dt.date(year.year, 1, 20), dt.date(year.year, 3, 28)),
            (2, dt.date(year.year, 3, 29), dt.date(year.year, 6, 14)),
            (3, dt.date(year.year, 7, 8), dt.date(year.year, 9, 20)),
            (4, dt.date(year.year, 9, 21), dt.date(year.year, 11, 30)),
        ]
        for number, start, end in blocks:
            AcademicPeriod.objects.get_or_create(
                school_year=year,
                number=number,
                defaults={
                    "name": f"Periodo {number}",
                    "short_name": f"P{number}",
                    "start_date": start,
                    "end_date": end,
                    "weight": Decimal("25.00"),
                    "is_current": number == 1,
                    "grades_open": True,
                },
            )
        self.stdout.write(f"  Periodos academicos: {year.periods.count()}")

    def _scale(self, year):
        from core.academic.models import GradingScale, GradingScaleLevel

        scale, _ = GradingScale.objects.get_or_create(
            school_year=year,
            name="Escala institucional 1.0 - 5.0",
            defaults={
                "scale_type": "NUMERICA",
                "minimum": Decimal("1.00"),
                "maximum": Decimal("5.00"),
                "passing": Decimal("3.00"),
                "decimals": 1,
                "is_default": True,
            },
        )
        for code, name, national, minimum, maximum, color, passing, order in PERFORMANCE_LEVELS:
            GradingScaleLevel.objects.get_or_create(
                scale=scale,
                code=code,
                defaults={
                    "name": name,
                    "national_equivalent": national,
                    "minimum": minimum,
                    "maximum": maximum,
                    "color": color,
                    "is_passing": passing,
                    "order": order,
                },
            )
        return scale

    def _dimensions(self, year):
        from core.academic.models import ValuationDimension

        for code, name, weight, order in DIMENSIONS:
            ValuationDimension.objects.get_or_create(
                school_year=year, code=code, defaults={"name": name, "weight": weight, "order": order}
            )
        self.stdout.write(f"  Dimensiones valorativas: {year.dimensions.count()}")

    def _coexistence(self, year):
        from core.academic.models import CoexistenceItem

        for order, (code, name, kind) in enumerate(COEXISTENCE, start=1):
            CoexistenceItem.objects.get_or_create(
                school_year=year, code=code, defaults={"name": name, "item_type": kind, "order": order}
            )

    def _report_header(self, institution):
        from core.configuration.models import ReportHeader

        ReportHeader.objects.get_or_create(
            institution=institution,
            name="Encabezado principal",
            defaults={
                "line_1": institution.name.upper(),
                "line_2": institution.resolution,
                "line_3": f"DANE {institution.code} - NIT {institution.nit}",
                "line_4": f"{institution.address} - {institution.city} - Tel. {institution.phone}",
                "footer_text": f"Documento generado por {settings.PLSGE['NAME']}",
                "is_default": True,
            },
        )

    def _grade_config(self, year):
        from core.configuration.models import GradeDecimalConfig

        GradeDecimalConfig.objects.get_or_create(
            school_year=year,
            name="Configuracion de decimas",
            defaults={
                "decimals": 1,
                "rounding_mode": "HALF_UP",
                "round_from": Decimal("0.50"),
                "minimum_grade": Decimal("1.00"),
                "maximum_grade": Decimal("5.00"),
                "passing_grade": Decimal("3.00"),
                "is_default": True,
            },
        )

    def _levels(self, institution):
        from core.academic.models import EducationLevel

        levels = {}
        for code, name, is_preschool, evaluation, order in LEVELS:
            level, _ = EducationLevel.objects.get_or_create(
                institution=institution,
                code=code,
                defaults={
                    "name": name,
                    "is_preschool": is_preschool,
                    "evaluation_type": evaluation,
                    "order": order,
                },
            )
            levels[code] = level
        self.stdout.write(f"  Niveles educativos: {len(levels)}")
        return levels

    def _grades(self, levels):
        from core.academic.models import Grade

        grades = {}
        for order, (level_code, code, name, value, min_age, max_age, graduation) in enumerate(GRADES, start=1):
            grade, _ = Grade.objects.get_or_create(
                level=levels[level_code],
                code=code,
                defaults={
                    "name": name,
                    "numeric_value": value,
                    "minimum_age": min_age,
                    "maximum_age": max_age,
                    "is_graduation": graduation,
                    "order": order,
                },
            )
            grades[code] = grade

        ordered = [grades[code] for _, code, *_ in GRADES]
        for index, grade in enumerate(ordered[:-1]):
            if grade.next_grade_id is None:
                grade.next_grade = ordered[index + 1]
                grade.save(update_fields=["next_grade"])
        self.stdout.write(f"  Grados: {len(grades)}")
        return grades

    def _groups(self, year, grades, per_grade):
        from core.academic.models import Group
        from core.institutions.models import Campus, Shift

        campus = Campus.objects.filter(institution=year.institution, is_main=True).first()
        shift = Shift.objects.filter(institution=year.institution).order_by("order").first()

        created = 0
        for grade in grades.values():
            for index in range(1, per_grade + 1):
                code = f"{grade.code}{index:02d}"
                _, was_created = Group.objects.get_or_create(
                    school_year=year,
                    grade=grade,
                    code=code,
                    defaults={
                        "name": f"{grade.name} {index:02d}",
                        "campus": campus,
                        "shift": shift,
                        "capacity": 35,
                        "classroom": f"Aula {code}",
                        "order": index,
                    },
                )
                created += int(was_created)
        self.stdout.write(f"  Grupos creados: {created}")

    def _areas(self, year):
        from core.academic.models import Area

        areas = {}
        for order, (code, name, color) in enumerate(AREAS, start=1):
            area, _ = Area.objects.get_or_create(
                school_year=year,
                code=code,
                defaults={"name": name, "color": color, "order": order},
            )
            areas[code] = area
        self.stdout.write(f"  Areas: {len(areas)}")
        return areas

    def _subjects(self, areas, grades):
        from core.academic.models import Subject

        created = 0
        for order, (area_code, code, name, hours, bilingual) in enumerate(SUBJECTS, start=1):
            subject, was_created = Subject.objects.get_or_create(
                area=areas[area_code],
                code=code,
                defaults={
                    "name": name,
                    "weekly_hours": hours,
                    "is_bilingual": bilingual,
                    "order": order,
                },
            )
            if was_created:
                subject.grades.set(grades.values())
                created += 1
        self.stdout.write(f"  Asignaturas: {created} nuevas de {Subject.objects.count()}")
