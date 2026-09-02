"""
Datos minimos compartidos por las pruebas del modulo PAE.

Construye una institucion, un ano lectivo, una sede, un estudiante matriculado
y la configuracion basica del programa, sin depender de los comandos de
sembrado ni de la base de datos de desarrollo.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.utils import timezone


def build_platform():
    """Institucion + ano lectivo + sede + grado + grupo."""
    from core.academic.models import EducationLevel, Grade, Group, SchoolYear
    from core.institutions.models import Campus, Institution, Shift

    institution = Institution.objects.create(
        name="Institucion de Pruebas", short_name="IEP", nit="900000000-0",
        code="000000000000", is_default=True,
    )
    campus = Campus.objects.create(
        institution=institution, code="PRINCIPAL", name="Sede Principal", is_main=True
    )
    other_campus = Campus.objects.create(
        institution=institution, code="SEDE-B", name="Sede B"
    )
    shift = Shift.objects.create(institution=institution, code="MANANA", name="Manana", order=1)

    today = timezone.localdate()
    year = SchoolYear.objects.create(
        institution=institution,
        year=today.year,
        name=f"Ano lectivo {today.year}",
        start_date=today - dt.timedelta(days=60),
        end_date=today + dt.timedelta(days=120),
        is_current=True,
    )
    level = EducationLevel.objects.create(institution=institution, code="PRI", name="Primaria", order=1)
    grade = Grade.objects.create(level=level, code="G01", name="Primero", order=1, numeric_value=1)
    group = Group.objects.create(
        school_year=year, grade=grade, code="G01-A", name="A", shift=shift, campus=campus
    )
    return {
        "institution": institution,
        "campus": campus,
        "other_campus": other_campus,
        "shift": shift,
        "year": year,
        "grade": grade,
        "group": group,
    }


def build_student(platform, document="1000000001", status="ACTIVO"):
    from core.students.models import Enrollment, Student

    student = Student.objects.create(
        institution=platform["institution"],
        document_number=document,
        first_name="Estudiante",
        last_name="De Prueba",
        gender="N",
        status=status,
    )
    enrollment = Enrollment.objects.create(
        school_year=platform["year"],
        student=student,
        group=platform["group"],
        enrollment_date=platform["year"].start_date,
        status="ACTIVA",
    )
    return student, enrollment


def build_pae(platform):
    """Normativa, modalidad, complemento y vigencia del programa."""
    from ...pae.models import PaeComplementType, PaeModality, PaeNormative, PaeVigencia

    normative = PaeNormative.objects.create(
        code="RES-TEST-001", name="Norma de pruebas", status="POR_VALIDAR"
    )
    modality = PaeModality.objects.create(
        institution=platform["institution"], code="PREPARADA", name="Preparada en sitio"
    )
    complement = PaeComplementType.objects.create(
        institution=platform["institution"], code="AM", name="Jornada manana", modality=modality
    )
    vigencia = PaeVigencia.objects.create(
        institution=platform["institution"],
        school_year=platform["year"],
        normative=normative,
        name=f"PAE {platform['year'].year}",
        start_date=platform["year"].start_date,
        end_date=platform["year"].end_date,
        service_days=100,
        status="ACTIVA",
        is_current=True,
    )
    return {
        "normative": normative,
        "modality": modality,
        "complement": complement,
        "vigencia": vigencia,
    }


def build_plan(platform, pae, status="APROBADO", campus=None):
    from ...pae.models import PaePlan

    return PaePlan.objects.create(
        vigencia=pae["vigencia"],
        institution=platform["institution"],
        campus=campus or platform["campus"],
        name=f"Plan {(campus or platform['campus']).code}",
        start_date=pae["vigencia"].start_date,
        end_date=pae["vigencia"].end_date,
        modality=pae["modality"],
        complement_type=pae["complement"],
        beneficiaries_count=10,
        service_days=100,
        status=status,
    )


def build_menu_cycle(pae, days=3):
    from ...pae.models import PaeMenuCycle, PaeMenuDay, PaeMenuIngredient, PaeMenuPreparation

    cycle = PaeMenuCycle.objects.create(
        vigencia=pae["vigencia"],
        modality=pae["modality"],
        complement_type=pae["complement"],
        code="CM-TEST",
        name="Ciclo de pruebas",
        days_count=days,
        status="VIGENTE",
    )
    for number in range(1, days + 1):
        day = PaeMenuDay.objects.create(cycle=cycle, day_number=number, name=f"Dia {number}")
        preparation = PaeMenuPreparation.objects.create(
            day=day, name=f"Preparacion {number}", component="BEBIDA",
            calories=Decimal("100.00"), protein=Decimal("5.00"), order=1,
        )
        PaeMenuIngredient.objects.create(
            preparation=preparation, name="Ingrediente", quantity=Decimal("100.000"), unit="g"
        )
    return cycle


def build_checklist(pae, threshold_full="90.00", threshold_partial="70.00"):
    from ...pae.models import PaeCatalog, PaeChecklist, PaeChecklistItem

    category = PaeCatalog.objects.create(
        catalog_type=PaeCatalog.TYPE_CHECK_CATEGORY, code="GEN", name="General", order=1
    )
    checklist = PaeChecklist.objects.create(
        code="LV-TEST",
        name="Lista de pruebas",
        scope="CALIDAD",
        threshold_full=Decimal(threshold_full),
        threshold_partial=Decimal(threshold_partial),
    )
    items = [
        PaeChecklistItem.objects.create(
            checklist=checklist, category=category, criterion="Criterio normal 1",
            weight=Decimal("1.00"), order=1,
        ),
        PaeChecklistItem.objects.create(
            checklist=checklist, category=category, criterion="Criterio normal 2",
            weight=Decimal("1.00"), order=2,
        ),
        PaeChecklistItem.objects.create(
            checklist=checklist, category=category, criterion="Criterio critico",
            weight=Decimal("2.00"), is_critical=True, order=3,
        ),
    ]
    return checklist, items


def build_user(email, role_code, institution, password="Prueba123*"):
    """Usuario con un perfil y su matriz de permisos por defecto aplicada."""
    from config.permissions import invalidate_permission_cache
    from core.configuration.modules import DEFAULT_ROLE_MATRIX
    from core.users.models import Module, Role, RolePermission

    role, _ = Role.objects.get_or_create(
        code=role_code, defaults={"name": role_code.title(), "is_system": True}
    )
    matrix = DEFAULT_ROLE_MATRIX.get(role_code, {})

    for module in Module.objects.all():
        actions = _resolve_actions(matrix, module.code)
        if actions is None:
            continue
        RolePermission.objects.update_or_create(
            role=role,
            module=module,
            defaults={
                "can_view": "view" in actions,
                "can_create": "create" in actions,
                "can_edit": "edit" in actions,
                "can_delete": "delete" in actions,
                "can_export": "export" in actions,
                "can_approve": "approve" in actions,
            },
        )

    from core.users.models import User

    user = User.objects.create_user(
        email=email, password=password, first_name=role_code, last_name="Prueba",
        role=role, institution=institution,
    )
    invalidate_permission_cache()
    return user


def _resolve_actions(matrix, module_code):
    if module_code in matrix:
        return matrix[module_code]
    parent = module_code.split(".")[0]
    if parent in matrix:
        return matrix[parent]
    if "*" in matrix:
        return matrix["*"]
    return None


def seed_modules():
    """Crea la tabla de modulos a partir del registro central."""
    from core.configuration.modules import iter_modules
    from core.users.models import Module

    created = {}
    for entry in iter_modules():
        parent = created.get(entry["parent"]) if entry["parent"] else None
        module, _ = Module.objects.update_or_create(
            code=entry["code"],
            defaults={
                "name": entry["name"],
                "parent": parent,
                "icon": entry["icon"],
                "url_name": entry["url_name"] or "",
                "group": entry["group"],
                "order": entry["order"],
                "is_active": True,
            },
        )
        created[entry["code"]] = module
    return created
