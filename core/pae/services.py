"""
Reglas de negocio, calculo de indicadores y alertas del modulo PAE.

Toda validacion critica vive aqui y se invoca tanto desde los serializers de la
API como desde los formularios y comandos, de modo que la regla no depende de
la interfaz que la dispare.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

ZERO = Decimal("0.00")


# ===========================================================================
# REGLAS DE NEGOCIO
# ===========================================================================
def validate_delivery(delivery, raise_error=True):
    """
    Reglas 1, 2 y 3 del modulo.

      1. La sede debe pertenecer al plan (o al contrato asociado).
      2. No se pueden entregar mas raciones de las recibidas.
      3. No se pueden entregar mas raciones de las programadas sin justificacion.

    Devuelve la lista de errores; si raise_error, eleva ValidationError.
    """
    errors = {}

    if delivery.plan_id and delivery.campus_id and delivery.plan.campus_id != delivery.campus_id:
        contract = delivery.contract or delivery.plan.contract
        covered = (
            contract.campuses.filter(pk=delivery.campus_id).exists() if contract else False
        )
        if not covered:
            errors["campus"] = (
                "La sede no esta asociada al plan ni al contrato seleccionado."
            )

    if delivery.delivered_rations > delivery.received_rations:
        errors["delivered_rations"] = (
            "No es posible entregar mas raciones de las recibidas "
            f"({delivery.delivered_rations} entregadas vs {delivery.received_rations} recibidas)."
        )

    if delivery.delivered_rations > delivery.scheduled_rations and not (delivery.justification or "").strip():
        errors["justification"] = (
            "Se entregaron mas raciones de las programadas: registre la justificacion."
        )

    missing = int(delivery.scheduled_rations) - int(delivery.received_rations)
    undelivered = int(delivery.received_rations) - int(delivery.delivered_rations)
    if (missing > 0 or undelivered > 0 or not delivery.menu_matches) and not (delivery.justification or "").strip():
        errors["justification"] = (
            "Existe incumplimiento (faltantes, no entregadas o menu diferente): "
            "registre la justificacion."
        )

    if delivery.arrival_time and delivery.delivery_time and delivery.delivery_time < delivery.arrival_time:
        errors["delivery_time"] = "La hora de entrega no puede ser anterior a la hora de llegada."

    if errors and raise_error:
        raise ValidationError(errors)
    return errors


def validate_beneficiary(beneficiary, raise_error=True):
    """
    Reglas 7 y 8.

      7. El estudiante debe existir y estar activo.
      8. No se puede duplicar el beneficiario en la misma vigencia.
    """
    from .models import PaeBeneficiary

    errors = {}

    if beneficiary.student_id is None:
        errors["student"] = "Debe seleccionar un estudiante existente."
    else:
        student = beneficiary.student
        if student.deleted_at is not None:
            errors["student"] = "El estudiante seleccionado fue eliminado del sistema."
        elif student.status not in ("ACTIVO",) and beneficiary.status == "ACTIVO":
            errors["student"] = (
                f"El estudiante se encuentra en estado {student.get_status_display()}: "
                "no puede registrarse como beneficiario activo."
            )

    if beneficiary.student_id and beneficiary.vigencia_id:
        duplicated = PaeBeneficiary.objects.filter(
            vigencia_id=beneficiary.vigencia_id,
            student_id=beneficiary.student_id,
            deleted_at__isnull=True,
        ).exclude(pk=beneficiary.pk)
        if duplicated.exists():
            errors["student"] = "El estudiante ya esta registrado como beneficiario en esta vigencia."

    if beneficiary.end_date and beneficiary.start_date and beneficiary.end_date < beneficiary.start_date:
        errors["end_date"] = "La fecha final no puede ser anterior a la fecha de inicio."

    if errors and raise_error:
        raise ValidationError(errors)
    return errors


def validate_plan_edit(plan, user, raise_error=True):
    """
    Regla 6: un plan APROBADO, EN EJECUCION o CERRADO solo lo modifica quien
    tenga permiso de aprobacion sobre el modulo de planeacion.
    """
    from config.permissions import user_has_permission

    if plan.status in ("BORRADOR", "EN_REVISION"):
        return {}

    if user_has_permission(user, "pae.planeacion", "approve"):
        return {}

    error = {
        "status": (
            f"El plan se encuentra en estado {plan.get_status_display()}. "
            "Se requiere permiso de aprobacion para modificarlo."
        )
    }
    if raise_error:
        raise ValidationError(error)
    return error


def validate_incident_close(incident, raise_error=True):
    """Regla 4: no se cierra una novedad sin registrar la solucion aplicada."""
    errors = {}
    if not (incident.solution or "").strip():
        errors["solution"] = "Debe registrar la solucion aplicada antes de cerrar la novedad."
    if errors and raise_error:
        raise ValidationError(errors)
    return errors


def validate_action_close(action, raise_error=True):
    """
    Regla 5: no se cierra una accion de mejoramiento sin verificacion y,
    cuando la accion lo exige, sin evidencia cargada.
    """
    from .models import PaeEvidence

    errors = {}

    if not (action.verification_note or "").strip():
        errors["verification_note"] = (
            "Registre la verificacion de eficacia antes de cerrar la accion."
        )

    if action.requires_evidence:
        has_evidence = PaeEvidence.objects.filter(
            module="MEJORAMIENTO", reference_id=action.pk, deleted_at__isnull=True
        ).exists()
        if not has_evidence:
            errors["evidence"] = (
                "La accion exige evidencia: cargue al menos un soporte antes de cerrarla."
            )

    if errors and raise_error:
        raise ValidationError(errors)
    return errors


# ===========================================================================
# HISTORIAL DE ESTADOS (regla 11)
# ===========================================================================
@transaction.atomic
def change_plan_status(plan, new_status, user=None, reason=""):
    """Transiciona el estado del plan validando el flujo y dejando historial."""
    from .models import PaePlanStateHistory

    allowed = [target for target, _action in plan.allowed_transitions()]
    if new_status not in allowed:
        raise ValidationError(
            {"status": f"Transicion no permitida: {plan.status} -> {new_status}. "
                       f"Permitidas: {', '.join(allowed) or 'ninguna'}."}
        )

    previous = plan.status
    plan.status = new_status
    if new_status == "APROBADO":
        plan.approved_by = user
        plan.approved_at = timezone.now()
    if new_status == "CERRADO":
        plan.closed_at = timezone.now()
    plan.updated_by = user
    plan.save()

    PaePlanStateHistory.objects.create(
        plan=plan, previous_status=previous, new_status=new_status,
        reason=reason, changed_by=user, created_by=user,
    )
    return plan


@transaction.atomic
def change_incident_status(incident, new_status, user=None, comment=""):
    """Transiciona una novedad validando el flujo y dejando historial."""
    from .models import PaeIncidentHistory

    allowed = incident.allowed_transitions()
    if new_status not in allowed:
        raise ValidationError(
            {"status": f"Transicion no permitida: {incident.status} -> {new_status}. "
                       f"Permitidas: {', '.join(allowed) or 'ninguna'}."}
        )

    if new_status == "CERRADA":
        validate_incident_close(incident)

    previous = incident.status
    incident.status = new_status
    if new_status == "SOLUCIONADA":
        incident.solved_at = timezone.now()
    if new_status == "CERRADA":
        incident.closed_at = timezone.now()
    incident.updated_by = user
    incident.save()

    PaeIncidentHistory.objects.create(
        incident=incident, previous_status=previous, new_status=new_status,
        comment=comment, changed_by=user, created_by=user,
    )
    return incident


@transaction.atomic
def change_beneficiary_status(beneficiary, new_status, user=None, reason=""):
    """
    Cambia el estado del beneficiario conservando el historial.

    La fila del historial la escribe la senal `log_beneficiary_status`, que es
    el unico punto de registro: aqui solo se aporta el motivo, para que un
    cambio de estado no quede duplicado en la trazabilidad.
    """
    previous = beneficiary.status
    if previous == new_status:
        return beneficiary

    beneficiary.status = new_status
    if new_status in ("RETIRADO", "FINALIZADO", "TRASLADADO") and not beneficiary.end_date:
        beneficiary.end_date = timezone.localdate()
    beneficiary.updated_by = user
    beneficiary._history_reason = reason
    beneficiary.save()
    return beneficiary


# ===========================================================================
# GENERACION MASIVA
# ===========================================================================
@transaction.atomic
def generate_schedules(plan, start_date, end_date, weekdays=None, user=None):
    """
    Genera la programacion diaria de un plan entre dos fechas.

    weekdays: lista 1..5 (lunes a viernes por defecto).
    Rota automaticamente los dias del ciclo de menu asociado al plan.
    """
    from .models import PaeSchedule

    weekdays = weekdays or [1, 2, 3, 4, 5]
    menu_days = []
    if plan.menu_cycle_id:
        menu_days = list(plan.menu_cycle.days.filter(deleted_at__isnull=True).order_by("day_number"))

    beneficiaries = plan.vigencia.beneficiaries.filter(
        campus=plan.campus, status="ACTIVO", deleted_at__isnull=True
    ).count()

    created = 0
    skipped = 0
    index = 0
    current = start_date

    while current <= end_date:
        if current.isoweekday() in weekdays:
            menu_day = menu_days[index % len(menu_days)] if menu_days else None
            _, was_created = PaeSchedule.objects.get_or_create(
                plan=plan,
                service_date=current,
                campus=plan.campus,
                shift=None,
                complement_type=plan.complement_type,
                defaults={
                    "operator": plan.operator,
                    "menu_day": menu_day,
                    "beneficiaries_count": beneficiaries,
                    "scheduled_rations": beneficiaries,
                    "created_by": user,
                },
            )
            created += int(was_created)
            skipped += int(not was_created)
            index += 1
        current += dt.timedelta(days=1)

    return {"created": created, "skipped": skipped, "beneficiaries": beneficiaries}


@transaction.atomic
def enroll_prioritized_students(prioritization, user=None):
    """Convierte en beneficiarios a los estudiantes matriculados de una priorizacion aprobada."""
    from core.students.models import Enrollment

    from .models import PaeBeneficiary

    if prioritization.status != "APROBADA":
        raise ValidationError({"status": "Solo se pueden vincular beneficiarios de una priorizacion aprobada."})

    enrollments = Enrollment.objects.filter(
        school_year=prioritization.vigencia.school_year,
        status="ACTIVA",
        deleted_at__isnull=True,
    ).select_related("student", "group", "group__grade")

    if prioritization.group_id:
        enrollments = enrollments.filter(group_id=prioritization.group_id)
    elif prioritization.grade_id:
        enrollments = enrollments.filter(group__grade_id=prioritization.grade_id)
    if prioritization.campus_id:
        enrollments = enrollments.filter(group__campus_id=prioritization.campus_id)

    created, skipped = 0, 0
    for enrollment in enrollments:
        exists = PaeBeneficiary.objects.filter(
            vigencia=prioritization.vigencia, student=enrollment.student, deleted_at__isnull=True
        ).exists()
        if exists:
            skipped += 1
            continue
        PaeBeneficiary.objects.create(
            vigencia=prioritization.vigencia,
            student=enrollment.student,
            enrollment=enrollment,
            campus=enrollment.group.campus or prioritization.campus,
            grade=enrollment.group.grade,
            group=enrollment.group,
            shift=enrollment.group.shift,
            prioritization=prioritization,
            start_date=prioritization.vigencia.start_date,
            created_by=user,
        )
        created += 1

    return {"created": created, "skipped": skipped}


# ===========================================================================
# INDICADORES Y TABLERO
# ===========================================================================
def dashboard_filters(request):
    """Extrae y normaliza los filtros del tablero desde la peticion."""
    params = request.query_params if hasattr(request, "query_params") else request.GET
    return {
        "vigencia": params.get("vigencia") or None,
        "campus": params.get("campus") or None,
        "shift": params.get("shift") or None,
        "operator": params.get("operator") or None,
        "date_from": params.get("date_from") or None,
        "date_to": params.get("date_to") or None,
    }


def _delivery_queryset(vigencia, filters):
    from .models import PaeDelivery

    queryset = PaeDelivery.objects.filter(
        plan__vigencia=vigencia, deleted_at__isnull=True
    ).exclude(status="ANULADA")

    if filters.get("campus"):
        queryset = queryset.filter(campus_id=filters["campus"])
    if filters.get("shift"):
        queryset = queryset.filter(shift_id=filters["shift"])
    if filters.get("operator"):
        queryset = queryset.filter(operator_id=filters["operator"])
    if filters.get("date_from"):
        queryset = queryset.filter(service_date__gte=filters["date_from"])
    if filters.get("date_to"):
        queryset = queryset.filter(service_date__lte=filters["date_to"])
    return queryset


def build_dashboard(vigencia, filters=None):
    """Construye el tablero completo del PAE: tarjetas, graficas y alertas."""
    from core.students.models import Enrollment

    from .models import (
        PaeBeneficiary,
        PaeContract,
        PaeFinding,
        PaeImprovementAction,
        PaeIncident,
        PaePqrs,
        PaeVisit,
    )

    filters = filters or {}
    if vigencia is None:
        return {"vigencia": None, "cards": [], "charts": {}, "alerts": []}

    beneficiaries = PaeBeneficiary.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    if filters.get("campus"):
        beneficiaries = beneficiaries.filter(campus_id=filters["campus"])
    if filters.get("shift"):
        beneficiaries = beneficiaries.filter(shift_id=filters["shift"])

    active_beneficiaries = beneficiaries.filter(status="ACTIVO").count()
    enrolled = Enrollment.objects.filter(
        school_year=vigencia.school_year, status="ACTIVA", deleted_at__isnull=True
    ).count()
    coverage = round(active_beneficiaries / enrolled * 100, 2) if enrolled else 0

    deliveries = _delivery_queryset(vigencia, filters)
    totals = deliveries.aggregate(
        scheduled=Sum("scheduled_rations"),
        received=Sum("received_rations"),
        delivered=Sum("delivered_rations"),
    )
    scheduled = totals["scheduled"] or 0
    received = totals["received"] or 0
    delivered = totals["delivered"] or 0
    missing = scheduled - received
    compliance = round(delivered / scheduled * 100, 2) if scheduled else 0

    incidents = PaeIncident.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    if filters.get("campus"):
        incidents = incidents.filter(campus_id=filters["campus"])
    incidents_open = incidents.exclude(status="CERRADA").count()
    incidents_closed = incidents.filter(status="CERRADA").count()

    visits = PaeVisit.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    findings = PaeFinding.objects.filter(visit__vigencia=vigencia, deleted_at__isnull=True)
    actions = PaeImprovementAction.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    overdue_actions = actions.exclude(status__in=["CERRADA", "VERIFICADA"]).filter(
        due_date__lt=timezone.localdate()
    ).count()
    pqrs = PaePqrs.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    pqrs_open = pqrs.exclude(status__in=["RESPONDIDA", "CERRADA"]).count()

    cards = [
        {"code": "beneficiarios", "label": "Beneficiarios activos", "value": active_beneficiaries,
         "icon": "users", "color": "#4F46E5", "url": "/pae/beneficiarios/"},
        {"code": "cobertura", "label": "Cobertura", "value": coverage, "suffix": "%",
         "goal": float(vigencia.coverage_goal), "icon": "target", "color": "#0EA5E9",
         "url": "/pae/indicadores/"},
        {"code": "programadas", "label": "Raciones programadas", "value": scheduled,
         "icon": "calendar-check", "color": "#6366F1", "url": "/pae/programacion/"},
        {"code": "entregadas", "label": "Raciones entregadas", "value": delivered,
         "icon": "check", "color": "#10B981", "url": "/pae/entregas/"},
        {"code": "cumplimiento", "label": "Cumplimiento", "value": compliance, "suffix": "%",
         "goal": float(vigencia.compliance_goal), "icon": "trending-up", "color": "#F59E0B",
         "url": "/pae/indicadores/"},
        {"code": "faltantes", "label": "Raciones faltantes", "value": max(missing, 0),
         "icon": "alert-triangle", "color": "#EF4444", "url": "/pae/entregas/"},
        {"code": "novedades", "label": "Novedades abiertas", "value": incidents_open,
         "icon": "alert-triangle", "color": "#EC4899", "url": "/pae/novedades/"},
        {"code": "visitas", "label": "Visitas realizadas", "value": visits.filter(status="REALIZADA").count(),
         "icon": "eye", "color": "#A855F7", "url": "/pae/visitas/"},
        {"code": "acciones", "label": "Acciones vencidas", "value": overdue_actions,
         "icon": "clock", "color": "#DC2626", "url": "/pae/mejoramiento/"},
        {"code": "pqrs", "label": "PQRS pendientes", "value": pqrs_open,
         "icon": "message", "color": "#14B8A6", "url": "/pae/pqrs/"},
    ]

    charts = {
        "beneficiaries_by_campus": _chart_rows(
            beneficiaries.filter(status="ACTIVO").values("campus__name").annotate(total=Count("id")).order_by("-total"),
            "campus__name",
        ),
        "rations": _rations_series(deliveries),
        "monthly_compliance": _monthly_compliance(deliveries),
        "incidents_by_type": _chart_rows(
            incidents.values("incident_type__name").annotate(total=Count("id")).order_by("-total")[:10],
            "incident_type__name",
        ),
        "incidents_by_status": _chart_rows(
            incidents.values("status").annotate(total=Count("id")).order_by("-total"), "status"
        ),
        "compliance_by_operator": _compliance_by_operator(deliveries),
        "findings_by_severity": _chart_rows(
            findings.values("severity").annotate(total=Count("id")).order_by("-total"), "severity"
        ),
        "coverage_evolution": _coverage_evolution(vigencia, beneficiaries),
    }

    return {
        "vigencia": {
            "id": vigencia.id,
            "name": vigencia.name,
            "status": vigencia.get_status_display(),
            "progress": vigencia.progress,
            "coverage_goal": float(vigencia.coverage_goal),
            "compliance_goal": float(vigencia.compliance_goal),
            "normative": vigencia.normative.code if vigencia.normative_id else None,
        },
        "cards": cards,
        "charts": charts,
        "alerts": build_alerts(vigencia),
        "totals": {
            "enrolled": enrolled,
            "beneficiaries": active_beneficiaries,
            "coverage": coverage,
            "scheduled": scheduled,
            "received": received,
            "delivered": delivered,
            "missing": max(missing, 0),
            "compliance": compliance,
            "incidents_open": incidents_open,
            "incidents_closed": incidents_closed,
            "visits": visits.count(),
            "findings": findings.count(),
            "overdue_actions": overdue_actions,
            "pqrs_open": pqrs_open,
        },
    }


def _chart_rows(queryset, key):
    labels, data = [], []
    for row in queryset:
        labels.append(str(row.get(key) or "Sin clasificar").replace("_", " ").title())
        data.append(row["total"])
    return {"labels": labels, "data": data}


def _rations_series(deliveries):
    rows = (
        deliveries.values("campus__name")
        .annotate(scheduled=Sum("scheduled_rations"), delivered=Sum("delivered_rations"))
        .order_by("campus__name")
    )
    return {
        "labels": [row["campus__name"] or "-" for row in rows],
        "scheduled": [row["scheduled"] or 0 for row in rows],
        "delivered": [row["delivered"] or 0 for row in rows],
    }


def _monthly_compliance(deliveries):
    from django.db.models.functions import TruncMonth

    rows = (
        deliveries.annotate(month=TruncMonth("service_date"))
        .values("month")
        .annotate(scheduled=Sum("scheduled_rations"), delivered=Sum("delivered_rations"))
        .order_by("month")
    )
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    labels, data = [], []
    for row in rows:
        if not row["month"]:
            continue
        labels.append(months[row["month"].month - 1])
        scheduled = row["scheduled"] or 0
        delivered = row["delivered"] or 0
        data.append(round(delivered / scheduled * 100, 2) if scheduled else 0)
    return {"labels": labels, "data": data}


def _compliance_by_operator(deliveries):
    rows = (
        deliveries.values("operator__business_name")
        .annotate(scheduled=Sum("scheduled_rations"), delivered=Sum("delivered_rations"))
        .order_by("operator__business_name")
    )
    labels, data = [], []
    for row in rows:
        scheduled = row["scheduled"] or 0
        delivered = row["delivered"] or 0
        labels.append(row["operator__business_name"] or "Sin operador")
        data.append(round(delivered / scheduled * 100, 2) if scheduled else 0)
    return {"labels": labels, "data": data}


def _coverage_evolution(vigencia, beneficiaries):
    from django.db.models.functions import TruncMonth

    rows = (
        beneficiaries.annotate(month=TruncMonth("start_date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    labels, data = [], []
    accumulated = 0
    for row in rows:
        if not row["month"]:
            continue
        accumulated += row["total"]
        labels.append(months[row["month"].month - 1])
        data.append(accumulated)
    return {"labels": labels, "data": data}


# ===========================================================================
# ALERTAS (reglas 9 y 10)
# ===========================================================================
def build_alerts(vigencia):
    """Alertas operativas del programa, ordenadas por criticidad."""
    from .models import (
        PaeContract,
        PaeDelivery,
        PaeDocument,
        PaeImprovementAction,
        PaeIncident,
        PaePqrs,
        PaeVisit,
    )

    today = timezone.localdate()
    alerts = []

    if vigencia is None:
        return [{
            "level": "danger", "code": "sin_vigencia", "icon": "alert-triangle",
            "title": "No hay vigencia PAE configurada",
            "message": "Cree la vigencia del programa para habilitar la operacion.",
            "url": "/pae/configuracion/vigencias/", "count": 0,
        }]

    # --- Contratos ---------------------------------------------------------
    contracts = PaeContract.objects.filter(vigencia=vigencia, deleted_at__isnull=True, status="VIGENTE")
    expiring = [c for c in contracts if c.is_expiring]
    expired = [c for c in contracts if c.is_expired]
    if expired:
        alerts.append({
            "level": "danger", "code": "contratos_vencidos", "icon": "alert-triangle",
            "title": f"{len(expired)} contrato(s) vencido(s)",
            "message": "Existen contratos cuya fecha final ya paso y siguen marcados como vigentes.",
            "url": "/pae/contratos/", "count": len(expired),
        })
    if expiring:
        alerts.append({
            "level": "warning", "code": "contratos_por_vencer", "icon": "clock",
            "title": f"{len(expiring)} contrato(s) proximo(s) a vencer",
            "message": "Gestione la prorroga o el nuevo proceso contractual.",
            "url": "/pae/contratos/", "count": len(expiring),
        })

    # --- Documentos --------------------------------------------------------
    documents = PaeDocument.objects.filter(vigencia=vigencia, deleted_at__isnull=True)
    docs_expired = documents.filter(expires_on__lt=today).exclude(status="ARCHIVADO").count()
    docs_expiring = documents.filter(
        expires_on__gte=today, expires_on__lte=today + dt.timedelta(days=30)
    ).count()
    if docs_expired:
        alerts.append({
            "level": "danger", "code": "documentos_vencidos", "icon": "file-text",
            "title": f"{docs_expired} documento(s) vencido(s)",
            "message": "Actualice los soportes documentales del programa.",
            "url": "/pae/documentos/", "count": docs_expired,
        })
    if docs_expiring:
        alerts.append({
            "level": "warning", "code": "documentos_por_vencer", "icon": "file-text",
            "title": f"{docs_expiring} documento(s) por vencer",
            "message": "Documentos que vencen dentro de los proximos 30 dias.",
            "url": "/pae/documentos/", "count": docs_expiring,
        })

    # --- Novedades ---------------------------------------------------------
    overdue_incidents = PaeIncident.objects.filter(
        vigencia=vigencia, deleted_at__isnull=True, due_date__lt=today
    ).exclude(status="CERRADA").count()
    if overdue_incidents:
        alerts.append({
            "level": "danger", "code": "novedades_vencidas", "icon": "alert-triangle",
            "title": f"{overdue_incidents} novedad(es) vencida(s)",
            "message": "Novedades que superaron su fecha limite sin cierre.",
            "url": "/pae/novedades/", "count": overdue_incidents,
        })

    # --- Acciones correctivas ---------------------------------------------
    overdue_actions = PaeImprovementAction.objects.filter(
        vigencia=vigencia, deleted_at__isnull=True, due_date__lt=today
    ).exclude(status__in=["CERRADA", "VERIFICADA"]).count()
    if overdue_actions:
        alerts.append({
            "level": "danger", "code": "acciones_vencidas", "icon": "clock",
            "title": f"{overdue_actions} accion(es) correctiva(s) vencida(s)",
            "message": "Planes de mejoramiento que superaron su fecha limite.",
            "url": "/pae/mejoramiento/", "count": overdue_actions,
        })

    # --- Visitas pendientes -----------------------------------------------
    pending_visits = PaeVisit.objects.filter(
        vigencia=vigencia, deleted_at__isnull=True, status="PROGRAMADA", visit_date__lt=today
    ).count()
    if pending_visits:
        alerts.append({
            "level": "warning", "code": "visitas_pendientes", "icon": "eye",
            "title": f"{pending_visits} visita(s) programada(s) sin realizar",
            "message": "Registre el resultado de las visitas vencidas.",
            "url": "/pae/visitas/", "count": pending_visits,
        })

    # --- Incumplimientos de entrega ---------------------------------------
    noncompliant = PaeDelivery.objects.filter(
        plan__vigencia=vigencia, deleted_at__isnull=True
    ).filter(Q(missing_rations__gt=0) | Q(undelivered_rations__gt=0)).count()
    if noncompliant:
        alerts.append({
            "level": "warning", "code": "entregas_incumplidas", "icon": "activity",
            "title": f"{noncompliant} entrega(s) con incumplimiento",
            "message": "Entregas con raciones faltantes o no entregadas.",
            "url": "/pae/entregas/", "count": noncompliant,
        })

    # --- PQRS --------------------------------------------------------------
    overdue_pqrs = PaePqrs.objects.filter(
        vigencia=vigencia, deleted_at__isnull=True, due_date__lt=today
    ).exclude(status__in=["RESPONDIDA", "CERRADA"]).count()
    if overdue_pqrs:
        alerts.append({
            "level": "danger", "code": "pqrs_vencidas", "icon": "message",
            "title": f"{overdue_pqrs} PQRS fuera de termino",
            "message": "Peticiones sin respuesta dentro del plazo legal.",
            "url": "/pae/pqrs/", "count": overdue_pqrs,
        })

    priority = {"danger": 0, "warning": 1, "info": 2}
    return sorted(alerts, key=lambda item: priority.get(item["level"], 3))


@transaction.atomic
def refresh_indicators(vigencia, user=None):
    """Recalcula y persiste los indicadores del tablero para la vigencia."""
    from .models import PaeIndicator

    data = build_dashboard(vigencia)
    totals = data["totals"]
    period_label = f"VIG-{vigencia.school_year.year}"

    definitions = [
        ("COBERTURA", "Cobertura del programa", totals["coverage"], float(vigencia.coverage_goal), "%"),
        ("CUMPLIMIENTO", "Cumplimiento de entregas", totals["compliance"], float(vigencia.compliance_goal), "%"),
        ("BENEFICIARIOS", "Beneficiarios activos", totals["beneficiaries"], totals["enrolled"], ""),
        ("RACIONES_PROGRAMADAS", "Raciones programadas", totals["scheduled"], 0, ""),
        ("RACIONES_ENTREGADAS", "Raciones entregadas", totals["delivered"], totals["scheduled"], ""),
        ("RACIONES_FALTANTES", "Raciones faltantes", totals["missing"], 0, ""),
        ("NOVEDADES_ABIERTAS", "Novedades abiertas", totals["incidents_open"], 0, ""),
        ("NOVEDADES_CERRADAS", "Novedades cerradas", totals["incidents_closed"], 0, ""),
        ("VISITAS", "Visitas realizadas", totals["visits"], 0, ""),
        ("HALLAZGOS", "Hallazgos registrados", totals["findings"], 0, ""),
        ("ACCIONES_VENCIDAS", "Acciones correctivas vencidas", totals["overdue_actions"], 0, ""),
        ("PQRS_PENDIENTES", "PQRS pendientes", totals["pqrs_open"], 0, ""),
    ]

    saved = 0
    for code, name, value, goal, unit in definitions:
        PaeIndicator.objects.update_or_create(
            vigencia=vigencia,
            campus=None,
            code=code,
            period_label=period_label,
            defaults={
                "name": name,
                "period_type": "VIGENCIA",
                "period_start": vigencia.start_date,
                "period_end": vigencia.end_date,
                "value": Decimal(str(round(float(value or 0), 2))),
                "goal": Decimal(str(round(float(goal or 0), 2))),
                "unit": unit,
                "calculated_at": timezone.now(),
                "updated_by": user,
            },
        )
        saved += 1
    return saved


def notify_alerts(vigencia, user=None):
    """Envia al centro de notificaciones las alertas criticas del programa."""
    from core.notifications.models import Notification
    from core.users.models import User

    alerts = [alert for alert in build_alerts(vigencia) if alert["level"] == "danger"]
    if not alerts:
        return 0

    recipients = User.objects.filter(
        is_active=True, deleted_at__isnull=True,
        role__code__in=["SUPER_ADMIN", "RECTOR", "RESPONSABLE_PAE", "SUPERVISOR_PAE"],
    )
    sent = 0
    for alert in alerts:
        Notification.broadcast(
            list(recipients[:200]),
            title=alert["title"],
            message=alert["message"],
            level="danger",
            url=alert["url"],
            module="pae.dashboard",
            icon=alert.get("icon", "alert-triangle"),
            sender=user,
        )
        sent += 1
    return sent
