"""
Importacion masiva del modulo PAE.

Cada importador declara sus columnas y como validar y guardar una fila; el
motor comun (`config.imports`) se encarga de leer CSV o XLSX y de reportar los
errores localizados por fila y columna.

El importador de estudiantes NO crea estudiantes: los resuelve por documento
contra el modulo de Estudiantes y los vincula al programa. Un documento que no
exista se reporta como error de la fila, para que el registro se haga en el
modulo que corresponde.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from config.imports import ImportResult, read_table, require_columns

from . import services

# ---------------------------------------------------------------------------
# Plantillas: columna -> descripcion (tambien alimentan el archivo de ejemplo)
# ---------------------------------------------------------------------------
TEMPLATES = {
    "beneficiarios": {
        "label": "Beneficiarios",
        "required": ["documento"],
        "columns": [
            ("documento", "Numero de documento del estudiante (debe existir en Estudiantes)"),
            ("modalidad", "Codigo de la modalidad de atencion"),
            ("complemento", "Codigo del tipo de complemento"),
            ("fecha_inicio", "Fecha de inicio AAAA-MM-DD"),
            ("estado", "ACTIVO / SUSPENDIDO / RETIRADO / TRASLADADO"),
            ("dieta_especial", "SI / NO"),
            ("detalle_dieta", "Detalle de la dieta especial"),
            ("observaciones", "Observaciones"),
        ],
        "example": ["1000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO", "NO", "", ""],
    },
    "programacion": {
        "label": "Programacion de entregas",
        "required": ["plan", "fecha"],
        "columns": [
            ("plan", "Codigo del plan operativo"),
            ("fecha", "Fecha de servicio AAAA-MM-DD"),
            ("sede", "Codigo de la sede (si se omite, la del plan)"),
            ("jornada", "Codigo de la jornada"),
            ("complemento", "Codigo del tipo de complemento"),
            ("dia_menu", "Numero del dia del ciclo de menu"),
            ("beneficiarios", "Beneficiarios programados"),
            ("raciones", "Raciones programadas"),
            ("observaciones", "Observaciones"),
        ],
        "example": ["PAE-2026-001", "2026-02-02", "PRINCIPAL", "", "AM", "1", "120", "120", ""],
    },
    "menus": {
        "label": "Ciclos de menu",
        "required": ["ciclo", "dia", "preparacion"],
        "columns": [
            ("ciclo", "Codigo del ciclo de menu"),
            ("dia", "Numero del dia dentro del ciclo"),
            ("nombre_dia", "Nombre del menu del dia"),
            ("preparacion", "Nombre de la preparacion"),
            ("componente", "BEBIDA / CEREAL / PROTEICO / FRUTA / VERDURA / LACTEO / ACOMPANAMIENTO / POSTRE / OTRO"),
            ("porcion", "Porcion servida"),
            ("calorias", "Calorias de la preparacion"),
            ("proteina", "Proteina en gramos"),
            ("ingrediente", "Nombre del ingrediente"),
            ("cantidad", "Cantidad del ingrediente"),
            ("unidad", "Unidad de medida"),
        ],
        "example": ["CM-2026-01", "1", "Menu dia 1", "Bebida lactea", "BEBIDA", "200 ml",
                    "180", "7.5", "Leche entera", "200", "ml"],
    },
}

# `estudiantes` es la vinculacion masiva de estudiantes ya matriculados: la
# misma operacion que `beneficiarios`, expuesta con el nombre que usa el area.
TEMPLATES["estudiantes"] = dict(TEMPLATES["beneficiarios"], label="Estudiantes a vincular")

KINDS = tuple(TEMPLATES)


# ---------------------------------------------------------------------------
# Conversores
# ---------------------------------------------------------------------------
def _date(value, row, column, result):
    text = (value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    result.add_error(row, column, f"Fecha no valida: '{text}'. Use AAAA-MM-DD.")
    return None


def _int(value, row, column, result, default=0):
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(float(text.replace(",", ".")))
    except (TypeError, ValueError):
        result.add_error(row, column, f"Se esperaba un numero entero: '{text}'.")
        return default


def _decimal(value, row, column, result, default="0.00"):
    text = (value or "").strip()
    if not text:
        return Decimal(default)
    try:
        return Decimal(text.replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        result.add_error(row, column, f"Se esperaba un numero: '{text}'.")
        return Decimal(default)


def _boolean(value):
    return (value or "").strip().upper() in ("SI", "S", "TRUE", "1", "X", "YES")


# ---------------------------------------------------------------------------
# Importadores
# ---------------------------------------------------------------------------
def import_beneficiaries(rows, result, vigencia, user):
    from core.students.models import Enrollment, Student

    from .models import PaeBeneficiary, PaeComplementType, PaeModality

    modalities = {row.code.upper(): row for row in PaeModality.objects.filter(deleted_at__isnull=True)}
    complements = {row.code.upper(): row for row in PaeComplementType.objects.filter(deleted_at__isnull=True)}
    seen = set()

    for row in rows:
        line = row["_row"]
        document = (row.get("documento") or "").strip()
        if not document:
            result.add_error(line, "documento", "El documento es obligatorio.")
            continue
        if document in seen:
            result.add_error(line, "documento", "El documento se repite dentro del archivo.")
            continue
        seen.add(document)

        student = Student.objects.filter(document_number=document, deleted_at__isnull=True).first()
        if student is None:
            result.add_error(
                line, "documento",
                f"El estudiante {document} no existe en el modulo de Estudiantes: registrelo alli primero.",
            )
            continue

        enrollment = Enrollment.objects.filter(
            student=student, school_year=vigencia.school_year, status="ACTIVA", deleted_at__isnull=True
        ).select_related("group").first()
        if enrollment is None:
            result.add_error(line, "documento", f"El estudiante {document} no tiene matricula activa en la vigencia.")
            continue

        modality_code = (row.get("modalidad") or "").strip().upper()
        if modality_code and modality_code not in modalities:
            result.add_error(line, "modalidad", f"Modalidad desconocida: '{modality_code}'.")
            continue

        complement_code = (row.get("complemento") or "").strip().upper()
        if complement_code and complement_code not in complements:
            result.add_error(line, "complemento", f"Tipo de complemento desconocido: '{complement_code}'.")
            continue

        status = (row.get("estado") or "ACTIVO").strip().upper()
        if status not in dict(PaeBeneficiary.STATUS_CHOICES):
            result.add_error(line, "estado", f"Estado no valido: '{status}'.")
            continue

        start_date = _date(row.get("fecha_inicio"), line, "fecha_inicio", result) or vigencia.start_date

        existing = PaeBeneficiary.objects.filter(
            vigencia=vigencia, student=student, deleted_at__isnull=True
        ).first()
        beneficiary = existing or PaeBeneficiary(vigencia=vigencia, student=student, created_by=user)
        beneficiary.enrollment = enrollment
        beneficiary.group = enrollment.group
        beneficiary.modality = modalities.get(modality_code)
        beneficiary.complement_type = complements.get(complement_code)
        beneficiary.start_date = start_date
        beneficiary.status = status
        beneficiary.has_special_diet = _boolean(row.get("dieta_especial"))
        beneficiary.special_diet_detail = (row.get("detalle_dieta") or "")[:240]
        beneficiary.observations = row.get("observaciones") or ""
        beneficiary.updated_by = user

        errors = services.validate_beneficiary(beneficiary, raise_error=False)
        if errors:
            for column, message in errors.items():
                result.add_error(line, column, message)
            continue

        beneficiary.save()
        if existing:
            result.updated += 1
        else:
            result.created += 1


def import_schedules(rows, result, vigencia, user):
    from core.institutions.models import Campus, Shift

    from .models import PaeComplementType, PaePlan, PaeSchedule

    plans = {row.code.upper(): row for row in PaePlan.objects.filter(vigencia=vigencia, deleted_at__isnull=True)}
    campuses = {row.code.upper(): row for row in Campus.objects.filter(deleted_at__isnull=True)}
    shifts = {row.code.upper(): row for row in Shift.objects.filter(deleted_at__isnull=True)}
    complements = {row.code.upper(): row for row in PaeComplementType.objects.filter(deleted_at__isnull=True)}
    seen = set()

    for row in rows:
        line = row["_row"]
        plan_code = (row.get("plan") or "").strip().upper()
        plan = plans.get(plan_code)
        if plan is None:
            result.add_error(line, "plan", f"El plan '{plan_code}' no existe en la vigencia actual.")
            continue
        if plan.status not in ("APROBADO", "EN_EJECUCION"):
            result.add_error(line, "plan", f"El plan '{plan_code}' no esta aprobado ni en ejecucion.")
            continue

        service_date = _date(row.get("fecha"), line, "fecha", result)
        if service_date is None:
            continue
        if not (plan.start_date <= service_date <= plan.end_date):
            result.add_error(line, "fecha", "La fecha esta fuera del periodo del plan.")
            continue

        campus_code = (row.get("sede") or "").strip().upper()
        campus = campuses.get(campus_code) if campus_code else plan.campus
        if campus is None:
            result.add_error(line, "sede", f"Sede desconocida: '{campus_code}'.")
            continue

        shift_code = (row.get("jornada") or "").strip().upper()
        if shift_code and shift_code not in shifts:
            result.add_error(line, "jornada", f"Jornada desconocida: '{shift_code}'.")
            continue
        shift = shifts.get(shift_code)

        complement_code = (row.get("complemento") or "").strip().upper()
        if complement_code and complement_code not in complements:
            result.add_error(line, "complemento", f"Tipo de complemento desconocido: '{complement_code}'.")
            continue
        complement = complements.get(complement_code) or plan.complement_type

        key = (plan.pk, service_date, campus.pk, shift.pk if shift else None,
               complement.pk if complement else None)
        if key in seen:
            result.add_error(line, "fecha", "La programacion se repite dentro del archivo.")
            continue
        seen.add(key)

        menu_day = None
        day_number = (row.get("dia_menu") or "").strip()
        if day_number and plan.menu_cycle_id:
            menu_day = plan.menu_cycle.days.filter(
                day_number=_int(day_number, line, "dia_menu", result), deleted_at__isnull=True
            ).first()
            if menu_day is None:
                result.add_error(line, "dia_menu", f"El ciclo de menu del plan no tiene el dia {day_number}.")
                continue

        beneficiaries = _int(row.get("beneficiarios"), line, "beneficiarios", result, plan.beneficiaries_count)
        rations = _int(row.get("raciones"), line, "raciones", result, beneficiaries)
        if rations < 0:
            result.add_error(line, "raciones", "Las raciones no pueden ser negativas.")
            continue

        existing = PaeSchedule.objects.filter(
            plan=plan, service_date=service_date, campus=campus, shift=shift,
            complement_type=complement, deleted_at__isnull=True,
        ).first()
        if existing:
            existing.menu_day = menu_day or existing.menu_day
            existing.beneficiaries_count = beneficiaries
            existing.scheduled_rations = rations
            existing.observations = (row.get("observaciones") or "")[:240]
            existing.updated_by = user
            existing.save()
            result.updated += 1
            continue

        PaeSchedule.objects.create(
            plan=plan,
            service_date=service_date,
            campus=campus,
            shift=shift,
            operator=plan.operator,
            complement_type=complement,
            menu_day=menu_day,
            beneficiaries_count=beneficiaries,
            scheduled_rations=rations,
            observations=(row.get("observaciones") or "")[:240],
            created_by=user,
        )
        result.created += 1


def import_menus(rows, result, vigencia, user):
    from .models import (
        PaeCatalog,
        PaeMenuCycle,
        PaeMenuDay,
        PaeMenuIngredient,
        PaeMenuPreparation,
    )

    components = dict(PaeMenuPreparation.COMPONENT_CHOICES)
    food_groups = {
        row.code.upper(): row
        for row in PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_FOOD_GROUP, deleted_at__isnull=True)
    }
    cycles = {}
    days = {}
    preparations = {}

    for row in rows:
        line = row["_row"]
        cycle_code = (row.get("ciclo") or "").strip().upper()
        if not cycle_code:
            result.add_error(line, "ciclo", "El codigo del ciclo es obligatorio.")
            continue

        cycle = cycles.get(cycle_code)
        if cycle is None:
            cycle = PaeMenuCycle.objects.filter(
                vigencia=vigencia, code=cycle_code, deleted_at__isnull=True
            ).order_by("-version").first()
            if cycle is None:
                result.add_error(
                    line, "ciclo",
                    f"El ciclo '{cycle_code}' no existe en la vigencia: creelo antes de importar sus dias.",
                )
                continue
            if cycle.status == "ARCHIVADO":
                result.add_error(line, "ciclo", f"El ciclo '{cycle_code}' esta archivado.")
                continue
            cycles[cycle_code] = cycle

        day_number = _int(row.get("dia"), line, "dia", result)
        if day_number <= 0:
            result.add_error(line, "dia", "El dia del ciclo debe ser un numero mayor que cero.")
            continue

        day_key = (cycle.pk, day_number)
        day = days.get(day_key)
        if day is None:
            day, day_created = PaeMenuDay.objects.get_or_create(
                cycle=cycle, day_number=day_number,
                defaults={"name": (row.get("nombre_dia") or f"Dia {day_number}")[:180], "created_by": user},
            )
            if not day_created and row.get("nombre_dia"):
                day.name = row["nombre_dia"][:180]
                day.updated_by = user
                day.save(update_fields=["name", "updated_by", "updated_at"])
            days[day_key] = day

        preparation_name = (row.get("preparacion") or "").strip()
        if not preparation_name:
            result.add_error(line, "preparacion", "El nombre de la preparacion es obligatorio.")
            continue

        component = (row.get("componente") or "OTRO").strip().upper()
        if component not in components:
            result.add_error(line, "componente", f"Componente no valido: '{component}'.")
            continue

        preparation_key = (day.pk, preparation_name.lower())
        preparation = preparations.get(preparation_key)
        if preparation is None:
            preparation, prep_created = PaeMenuPreparation.objects.get_or_create(
                day=day, name=preparation_name,
                defaults={
                    "component": component,
                    "portion": (row.get("porcion") or "")[:80],
                    "calories": _decimal(row.get("calorias"), line, "calorias", result),
                    "protein": _decimal(row.get("proteina"), line, "proteina", result),
                    "created_by": user,
                },
            )
            preparations[preparation_key] = preparation
            if prep_created:
                result.created += 1
            else:
                result.updated += 1

        ingredient_name = (row.get("ingrediente") or "").strip()
        if not ingredient_name:
            continue

        quantity = _decimal(row.get("cantidad"), line, "cantidad", result, "0.000")
        unit_code = (row.get("unidad") or "g").strip()
        _, ingredient_created = PaeMenuIngredient.objects.get_or_create(
            preparation=preparation, name=ingredient_name,
            defaults={
                "quantity": quantity,
                "unit": unit_code[:20],
                "food_group": food_groups.get(unit_code.upper()),
                "created_by": user,
            },
        )
        if not ingredient_created:
            result.skipped += 1


IMPORTERS = {
    "beneficiarios": import_beneficiaries,
    "estudiantes": import_beneficiaries,
    "programacion": import_schedules,
    "menus": import_menus,
}


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
@transaction.atomic
def run_import(kind, uploaded, vigencia, user=None, dry_run=False):
    """
    Ejecuta la importacion completa.

    Si alguna fila falla, no se guarda nada: la transaccion se revierte y se
    devuelve el detalle de los errores por fila y columna. `dry_run` valida el
    archivo sin conservar los cambios.
    """
    if kind not in IMPORTERS:
        raise ValidationError({"kind": f"Tipo de importacion no reconocido: '{kind}'."})
    if vigencia is None:
        raise ValidationError({"vigencia": "No hay vigencia del PAE configurada."})

    headers, rows = read_table(uploaded)
    result = ImportResult(headers=headers, total_rows=len(rows), dry_run=dry_run)

    template = TEMPLATES[kind]
    if not require_columns(headers, template["required"], result):
        transaction.set_rollback(True)
        return result

    if not rows:
        result.add_error(1, "archivo", "El archivo no tiene filas de datos.")
        transaction.set_rollback(True)
        return result

    IMPORTERS[kind](rows, result, vigencia, user)

    if result.has_errors or dry_run:
        transaction.set_rollback(True)
        if result.has_errors:
            result.created = result.updated = result.skipped = 0
    return result


def template_rows(kind):
    """Encabezado, descripciones y fila de ejemplo de una plantilla."""
    template = TEMPLATES[kind]
    return {
        "label": template["label"],
        "headers": [column for column, _ in template["columns"]],
        "descriptions": [description for _, description in template["columns"]],
        "example": template["example"],
        "required": template["required"],
    }
