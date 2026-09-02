"""
Creacion y puesta en marcha de instituciones educativas.

Crear la fila de la institucion no basta: sin ano lectivo, escala valorativa
ni estructura academica la plataforma queda inservible para esa institucion.
Aqui vive el arranque completo, que usan por igual el panel del super
administrador y el comando de instituciones de prueba.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import transaction

# --- Estructura academica de arranque ---------------------------------------
JORNADAS = [
    ("MAN", "Manana", dt.time(6, 30), dt.time(12, 30), 1),
    ("TAR", "Tarde", dt.time(12, 30), dt.time(18, 0), 2),
    ("UNI", "Unica", dt.time(7, 0), dt.time(15, 0), 3),
]

NIVELES = [
    ("PRE", "Preescolar", 1, True),
    ("PRI", "Basica Primaria", 2, False),
    ("SEC", "Basica Secundaria", 3, False),
    ("MED", "Media", 4, False),
]

GRADOS = [
    ("PRE", "T", "Transicion", 0, 1),
    ("PRI", "1", "Primero", 1, 2),
    ("PRI", "2", "Segundo", 2, 3),
    ("PRI", "3", "Tercero", 3, 4),
    ("PRI", "4", "Cuarto", 4, 5),
    ("PRI", "5", "Quinto", 5, 6),
    ("SEC", "6", "Sexto", 6, 7),
    ("SEC", "7", "Septimo", 7, 8),
    ("SEC", "8", "Octavo", 8, 9),
    ("SEC", "9", "Noveno", 9, 10),
    ("MED", "10", "Decimo", 10, 11),
    ("MED", "11", "Once", 11, 12),
]

AREAS = [
    ("MAT", "Matematicas", 1, [("MAT", "Matematicas", 5)]),
    ("LEN", "Humanidades y Lengua Castellana", 2, [("LEN", "Lengua Castellana", 5), ("ING", "Ingles", 3)]),
    ("CNA", "Ciencias Naturales", 3, [("CNA", "Ciencias Naturales", 4)]),
    ("CSO", "Ciencias Sociales", 4, [("CSO", "Ciencias Sociales", 3)]),
    ("EFI", "Educacion Fisica", 5, [("EFI", "Educacion Fisica", 2)]),
    ("ART", "Educacion Artistica", 6, [("ART", "Educacion Artistica", 2)]),
]

NIVELES_ESCALA = [
    ("S", "Superior", "4.60", "5.00", True, 1),
    ("A", "Alto", "4.00", "4.59", True, 2),
    ("B", "Basico", "3.00", "3.99", True, 3),
    ("J", "Bajo", "1.00", "2.99", False, 4),
]


#: Campos que se capturan al crear y al editar una institucion.
EDITABLE_FIELDS = (
    "name", "short_name", "nit", "resolution", "nature", "calendar",
    "country", "department", "city", "address", "phone", "email", "website",
    "rector_name", "rector_document", "secretary_name", "motto",
    "mission", "vision", "primary_color", "accent_color",
)


def _clean_fields(datos):
    """Normaliza el diccionario del formulario a los campos del modelo."""
    campos = {}
    for nombre in EDITABLE_FIELDS:
        if nombre in datos:
            campos[nombre] = (datos.get(nombre) or "").strip()
    if not campos.get("nature"):
        campos.pop("nature", None)
    if not campos.get("calendar"):
        campos.pop("calendar", None)
    if not campos.get("country"):
        campos.pop("country", None)
    return campos


def header_lines(institution):
    """Lineas del encabezado de reportes derivadas de los datos institucionales."""
    return {
        "line_1": (institution.name or "").upper(),
        "line_2": institution.resolution or "",
        "line_3": f"DANE {institution.code} - NIT {institution.nit}",
        "line_4": f"{institution.address} - {institution.city} - Tel. {institution.phone}",
    }


def sync_report_headers(institution, anteriores):
    """
    Pone al dia el encabezado impreso cuando cambian los datos institucionales.

    Solo toca las lineas que seguian siendo las derivadas de los datos
    anteriores: si alguien las redacto a mano, se respetan. Sin esto, renombrar
    la institucion dejaba los boletines saliendo con el nombre viejo.

    Devuelve cuantos encabezados se actualizaron.
    """
    from core.configuration.models import ReportHeader

    nuevas = header_lines(institution)
    if nuevas == anteriores:
        return 0

    actualizados = 0
    for header in ReportHeader.objects.filter(institution=institution):
        cambios = [
            campo for campo, valor in anteriores.items()
            if getattr(header, campo, "") == valor and getattr(header, campo, "") != nuevas[campo]
        ]
        if not cambios:
            continue
        for campo in cambios:
            setattr(header, campo, nuevas[campo])
        header.save(update_fields=cambios)
        actualizados += 1
    return actualizados


@transaction.atomic
def update_institution(institution, datos, *, user=None):
    """
    Actualiza los datos de una institucion existente.

    No toca `is_default` ni `is_active`: esas condiciones se cambian con sus
    propias acciones del panel, para no alterarlas sin querer al editar.
    """
    from .models import Institution

    # Se toman antes de modificar nada, para saber que lineas del encabezado
    # impreso seguian derivadas de los datos institucionales.
    anteriores = header_lines(institution)

    codigo = (datos.get("code") or "").strip()
    if codigo and codigo != institution.code:
        if Institution.objects.filter(code=codigo).exclude(pk=institution.pk).exists():
            raise ValueError(f"Ya existe otra institucion con el codigo {codigo}.")
        institution.code = codigo

    for nombre, valor in _clean_fields(datos).items():
        setattr(institution, nombre, valor)

    if user is not None and getattr(user, "pk", None):
        institution.updated_by = user
    institution.save()
    sync_report_headers(institution, anteriores)
    return institution


@transaction.atomic
def create_institution(datos, *, user=None, bootstrap=False, year=None, groups_per_grade=1):
    """
    Crea una institucion.

    Por defecto nace **limpia**: solo el registro institucional, sin ninguna
    estructura academica. Asi la institucion parte en blanco y quien la
    administra carga sus propios datos, sin arrastrar una plantilla copiada
    de otra institucion.

    Con `bootstrap=True` se agrega una estructura academica de ejemplo (sede,
    jornadas, ano lectivo, grados, grupos, areas y asignaturas), util solo
    cuando se quiere una institucion de prueba lista para explorar.

    `datos` es un diccionario con los campos de la institucion. El codigo DANE
    es obligatorio y unico en la plataforma.

    Devuelve (institucion, creada).
    """
    from django.utils import timezone

    from .models import Institution

    code = (datos.get("code") or "").strip()
    if not code:
        raise ValueError("El codigo DANE es obligatorio.")

    existente = Institution.objects.filter(code=code).first()
    if existente is not None:
        return existente, False

    campos = _clean_fields(datos)
    campos.setdefault("nature", "OFICIAL")
    campos.setdefault("calendar", "A")
    campos.setdefault("country", "Colombia")
    # Nunca se marca por defecto al crearla: esa condicion se cambia de forma
    # explicita desde el panel, para no desplazar sin querer a la institucion
    # que ya esta operando.
    campos["is_default"] = False
    campos["is_active"] = True
    if user is not None and getattr(user, "pk", None):
        campos["created_by"] = user

    institution = Institution.objects.create(code=code, **campos)

    if bootstrap:
        bootstrap_institution(
            institution,
            year=year or timezone.localdate().year,
            groups_per_grade=groups_per_grade,
            user=user,
        )
    return institution, True


# Perfiles que se pueden asignar al crear el acceso de una institucion nueva.
# El Super Administrador queda deliberadamente fuera: es un perfil de toda la
# plataforma, no de una institucion, y darlo aqui violaria el minimo privilegio.
ADMIN_ROLES = ("RECTOR", "COORDINADOR", "SECRETARIA")


@transaction.atomic
def create_institution_admin(institution, datos, *, user=None):
    """
    Crea el usuario con el que se ingresa a una institucion recien creada.

    Sin esto la institucion nace sin ninguna forma de entrar: habria que ir
    aparte a Gestion de Usuarios. Devuelve (usuario, clave_en_claro); la clave
    se devuelve para mostrarla una sola vez y dejar el certificado.

    La contrasena se valida con la politica de la plataforma. Si viene vacia,
    se genera una.
    """
    from django.contrib.auth.password_validation import ValidationError, validate_password

    from core.users.models import Role, User, UserCredentialCertificate

    correo = (datos.get("admin_email") or "").strip().lower()
    if not correo:
        raise ValueError("El correo del usuario de ingreso es obligatorio.")
    if User.objects.filter(email__iexact=correo).exists():
        raise ValueError(f"Ya existe un usuario con el correo {correo}.")

    codigo_rol = (datos.get("admin_role") or "RECTOR").strip().upper()
    if codigo_rol not in ADMIN_ROLES:
        raise ValueError("El perfil del usuario de ingreso no es valido.")
    rol = Role.objects.filter(code=codigo_rol).first()
    if rol is None:
        raise ValueError(f"No existe el perfil {codigo_rol} en la plataforma.")

    nombres = (datos.get("admin_first_name") or "").strip() or "Rector"
    apellidos = (datos.get("admin_last_name") or "").strip() or institution.short_name or "Institucion"

    clave = (datos.get("admin_password") or "").strip()
    generada = not clave
    if generada:
        clave = User.generate_password()

    nuevo = User(
        email=correo,
        username=User.build_username(nombres, apellidos),
        first_name=nombres,
        last_name=apellidos,
        role=rol,
        institution=institution,
        is_active=True,
        email_verified=True,
        must_change_password=bool(datos.get("admin_must_change")),
    )
    try:
        validate_password(clave, nuevo)
    except ValidationError as error:
        raise ValueError(" ".join(error.messages)) from error

    nuevo.set_password(clave)
    if user is not None and getattr(user, "pk", None):
        nuevo.created_by = user
    nuevo.save()

    UserCredentialCertificate.objects.create(
        user=nuevo, plain_password=clave, issued_by=user,
        notes=f"Acceso creado junto con la institucion {institution.name}",
    )
    return nuevo, clave


@transaction.atomic
def bootstrap_institution(institution, *, year, groups_per_grade=1, user=None):
    """
    Deja la institucion en condiciones de operar.

    Crea sede principal, jornadas, ano lectivo con periodos, escala valorativa,
    niveles, grados, grupos, areas y asignaturas. Es idempotente: volver a
    ejecutarlo sobre la misma institucion no duplica nada.
    """
    campus = _sede_principal(institution)
    _jornadas(institution)
    school_year = _ano_lectivo(institution, year)
    _periodos(school_year)
    _escala(school_year)
    niveles = _niveles(institution)
    grados = _grados(niveles)
    _grupos(school_year, grados, campus, groups_per_grade)
    areas = _areas(school_year)
    _asignaturas(areas, grados)
    return school_year


# ---------------------------------------------------------------------------
def _sede_principal(institution):
    from .models import Campus

    campus, _ = Campus.objects.get_or_create(
        institution=institution, code="SEDE-A",
        defaults={"name": "Sede Principal", "address": institution.address, "is_main": True},
    )
    return campus


def _jornadas(institution):
    from .models import Shift

    for code, name, inicio, fin, orden in JORNADAS:
        Shift.objects.get_or_create(
            institution=institution, code=code,
            defaults={"name": name, "start_time": inicio, "end_time": fin, "order": orden},
        )


def _ano_lectivo(institution, year):
    from core.academic.models import SchoolYear

    school_year, _ = SchoolYear.objects.get_or_create(
        institution=institution, year=year,
        defaults={
            "name": f"Ano lectivo {year}",
            "start_date": dt.date(year, 1, 20),
            "end_date": dt.date(year, 11, 30),
            "is_current": True,
        },
    )
    return school_year


def _periodos(school_year):
    from core.academic.models import AcademicPeriod

    year = school_year.year
    rangos = [
        (1, "Periodo 1", dt.date(year, 1, 20), dt.date(year, 3, 28)),
        (2, "Periodo 2", dt.date(year, 3, 29), dt.date(year, 6, 10)),
        (3, "Periodo 3", dt.date(year, 7, 5), dt.date(year, 9, 15)),
        (4, "Periodo 4", dt.date(year, 9, 16), dt.date(year, 11, 30)),
    ]
    for numero, nombre, inicio, fin in rangos:
        AcademicPeriod.objects.get_or_create(
            school_year=school_year, number=numero,
            defaults={"name": nombre, "start_date": inicio, "end_date": fin,
                      "weight": Decimal("25.00"), "is_current": numero == 1},
        )


def _escala(school_year):
    from core.academic.models import GradingScale, GradingScaleLevel

    escala, creada = GradingScale.objects.get_or_create(
        school_year=school_year, name="Escala institucional 1.0 - 5.0",
        defaults={"minimum": Decimal("1.00"), "maximum": Decimal("5.00"),
                  "passing": Decimal("3.00"), "decimals": 1, "is_default": True},
    )
    if creada:
        for code, name, minimo, maximo, aprueba, orden in NIVELES_ESCALA:
            GradingScaleLevel.objects.create(
                scale=escala, code=code, name=name, minimum=Decimal(minimo),
                maximum=Decimal(maximo), is_passing=aprueba, order=orden,
            )
    return escala


def _niveles(institution):
    from core.academic.models import EducationLevel

    niveles = {}
    for code, name, orden, preescolar in NIVELES:
        nivel, _ = EducationLevel.objects.get_or_create(
            institution=institution, code=code,
            defaults={"name": name, "order": orden, "is_preschool": preescolar,
                      "evaluation_type": "CUALITATIVA" if preescolar else "CUANTITATIVA"},
        )
        niveles[code] = nivel
    return niveles


def _grados(niveles):
    from core.academic.models import Grade

    grados = []
    for nivel_code, code, name, valor, orden in GRADOS:
        grado, _ = Grade.objects.get_or_create(
            level=niveles[nivel_code], code=code,
            defaults={"name": name, "numeric_value": valor, "order": orden,
                      "is_graduation": code == "11"},
        )
        grados.append(grado)
    return grados


def _grupos(school_year, grados, campus, por_grado):
    from core.academic.models import Group

    jornada = school_year.institution.shifts.filter(code="MAN").first()
    for grado in grados:
        for indice in range(1, por_grado + 1):
            Group.objects.get_or_create(
                school_year=school_year, grade=grado, code=f"{grado.code}-{indice:02d}",
                defaults={"name": f"{grado.name} {indice:02d}", "campus": campus,
                          "shift": jornada, "capacity": 35, "order": indice},
            )


def _areas(school_year):
    from core.academic.models import Area

    areas = {}
    for code, name, orden, _ in AREAS:
        area, _ = Area.objects.get_or_create(
            school_year=school_year, code=code, defaults={"name": name, "order": orden}
        )
        areas[code] = area
    return areas


def _asignaturas(areas, grados):
    from core.academic.models import Subject

    for area_code, _, _, asignaturas in AREAS:
        area = areas[area_code]
        for code, name, horas in asignaturas:
            asignatura, _ = Subject.objects.get_or_create(
                area=area, code=code,
                defaults={"name": name, "weekly_hours": horas, "order": 1},
            )
            asignatura.grades.set(grados)


# ---------------------------------------------------------------------------
def institution_summary(institution):
    """
    Estado de funcionamiento de una institucion, para el panel del Super
    Administrador.

    No son solo conteos: incluye si esta operando de verdad (si hay notas
    digitadas, asistencia registrada y accesos recientes) y que le falta para
    quedar lista.
    """
    import datetime as dt

    from django.utils import timezone

    from core.academic.models import Group, SchoolYear
    from core.attendance.models import AttendanceRecord
    from core.evaluations.models import SubjectGrade
    from core.students.models import Student
    from core.teachers.models import Teacher
    from core.users.models import User

    year = SchoolYear.objects.filter(
        institution=institution, deleted_at__isnull=True
    ).order_by("-is_current", "-year").first()

    estudiantes = Student.objects.filter(institution=institution, deleted_at__isnull=True).count()
    docentes = Teacher.objects.filter(institution=institution, deleted_at__isnull=True).count()
    usuarios = User.objects.filter(institution=institution)
    grupos = Group.objects.filter(school_year=year, deleted_at__isnull=True).count() if year else 0

    notas = SubjectGrade.objects.filter(
        school_year=year, deleted_at__isnull=True, final_score__isnull=False
    ).count() if year else 0
    asistencia = AttendanceRecord.objects.filter(
        student__institution=institution, deleted_at__isnull=True
    ).count()

    hace_30 = timezone.now() - dt.timedelta(days=30)
    ultimo_acceso = usuarios.exclude(last_login=None).order_by("-last_login").values_list(
        "last_login", flat=True
    ).first()

    # Que le falta para poder operar, en orden de dependencia.
    faltantes = []
    if year is None:
        faltantes.append("ano lectivo")
    else:
        if not year.periods.filter(deleted_at__isnull=True).exists():
            faltantes.append("periodos")
        if not year.grading_scales.filter(deleted_at__isnull=True).exists():
            faltantes.append("escala valorativa")
    if not grupos:
        faltantes.append("grupos")
    if not estudiantes:
        faltantes.append("estudiantes")
    if not docentes:
        faltantes.append("docentes")

    if faltantes:
        estado, tono = "Incompleta", "warning"
    elif notas or asistencia:
        estado, tono = "En operacion", "success"
    else:
        estado, tono = "Lista, sin actividad", "info"

    return {
        "school_year": year,
        "students": estudiantes,
        "teachers": docentes,
        "users": usuarios.count(),
        "active_users": usuarios.filter(last_login__gte=hace_30).count(),
        "campuses": institution.campuses.filter(deleted_at__isnull=True).count(),
        "groups": grupos,
        "grades_recorded": notas,
        "attendance_recorded": asistencia,
        "last_login": ultimo_acceso,
        "missing": faltantes,
        "status": estado,
        "tone": tono,
        "ready": not faltantes,
    }
