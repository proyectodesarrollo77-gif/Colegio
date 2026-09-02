"""
Motor de calificaciones de PL_SGE.

Responsable de:
  * Consolidar notas de procesos -> nota de asignatura del periodo
  * Aplicar la politica de decimas configurada
  * Calcular promedios de area y desempenos
  * Construir la planilla de notas del docente
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Utilidades de redondeo
# ---------------------------------------------------------------------------
def decimal_config(school_year):
    from core.configuration.models import GradeDecimalConfig

    return GradeDecimalConfig.for_year(school_year)


def apply_rounding(value, config=None):
    if value is None:
        return None
    value = Decimal(str(value))
    if config is None:
        return value.quantize(Decimal("0.01"))
    return config.apply(value)


def default_scale(school_year):
    from core.academic.models import GradingScale

    return GradingScale.default_for(school_year)


def performance_for(school_year, value):
    """Desempeno de una nota. Delega en el unico resolvedor de la plataforma."""
    from core.academic.models import resolve_performance

    return resolve_performance(school_year, value)


def _rounding_payload(school_year):
    """
    Politica de aproximacion en forma serializable.

    Permite que la planilla replique en el navegador exactamente el mismo
    redondeo que aplica `apply_rounding` en el servidor.
    """
    config = decimal_config(school_year)
    if config is None:
        # Sin configuracion, `apply_rounding` cuantiza a dos decimales.
        return {"mode": "HALF_UP", "decimals": 2, "round_from": 0.5, "apply_to_period": True}
    return {
        "mode": config.rounding_mode,
        "decimals": config.decimals,
        "round_from": float(config.round_from),
        "apply_to_period": config.apply_to_period,
    }


# ---------------------------------------------------------------------------
# Consolidacion
# ---------------------------------------------------------------------------
def compute_process_average(student, assignment, period):
    """Promedio ponderado de los procesos del docente para una asignacion."""
    from .models import ProcessGrade

    rows = (
        ProcessGrade.objects.filter(
            student=student, assignment=assignment, period=period, deleted_at__isnull=True, score__isnull=False
        )
        .select_related("process")
    )
    total_weight = ZERO
    accumulated = ZERO
    for row in rows:
        weight = Decimal(str(row.process.weight or 100))
        accumulated += Decimal(str(row.score)) * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return (accumulated / total_weight).quantize(Decimal("0.01"))


@transaction.atomic
def consolidate_subject_grade(student, assignment, period, save=True):
    """Calcula y guarda la nota de asignatura del periodo para un estudiante."""
    from .models import SubjectGrade

    average = compute_process_average(student, assignment, period)
    if average is None:
        return None

    school_year = period.school_year
    config = decimal_config(school_year)
    rounded = apply_rounding(average, config if (config and config.apply_to_period) else None)

    grade, _ = SubjectGrade.objects.get_or_create(
        student=student,
        period=period,
        subject=assignment.subject,
        defaults={
            "school_year": school_year,
            "group": assignment.group,
            "teacher": assignment.teacher,
            "enrollment": student.current_enrollment,
        },
    )
    grade.score = rounded
    grade.group = assignment.group
    grade.teacher = assignment.teacher
    grade.school_year = school_year
    grade.resolve_final()
    if save:
        grade.save()
    return grade


@transaction.atomic
def consolidate_group_period(group, period, subject=None):
    """Consolida todas las notas de un grupo en un periodo."""
    from core.teachers.models import TeachingAssignment

    assignments = TeachingAssignment.objects.filter(
        group=group, school_year=period.school_year, deleted_at__isnull=True
    ).select_related("subject", "teacher")
    if subject:
        assignments = assignments.filter(subject=subject)

    enrollments = group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True).select_related("student")
    processed = 0
    for enrollment in enrollments:
        for assignment in assignments:
            if consolidate_subject_grade(enrollment.student, assignment, period):
                processed += 1
        compute_area_grades(enrollment.student, period)
    return processed


@transaction.atomic
def compute_area_grades(student, period):
    """Calcula el promedio de cada area a partir de las notas de asignatura."""
    from core.academic.models import Area

    from .models import AreaGrade, SubjectGrade

    school_year = period.school_year
    config = decimal_config(school_year)
    grades = SubjectGrade.objects.filter(
        student=student, period=period, deleted_at__isnull=True
    ).select_related("subject", "subject__area")

    by_area = {}
    for grade in grades:
        area = grade.subject.area
        by_area.setdefault(area, []).append(grade)

    results = []
    for area, items in by_area.items():
        if area.average_by_intensity:
            total_hours = sum(Decimal(str(item.subject.weekly_hours or 1)) for item in items)
            accumulated = sum(
                Decimal(str(item.final_score or 0)) * Decimal(str(item.subject.weekly_hours or 1)) for item in items
            )
            average = (accumulated / total_hours) if total_hours else ZERO
        else:
            total_weight = sum(Decimal(str(item.subject.weight or 100)) for item in items)
            accumulated = sum(
                Decimal(str(item.final_score or 0)) * Decimal(str(item.subject.weight or 100)) for item in items
            )
            average = (accumulated / total_weight) if total_weight else ZERO

        rounded = apply_rounding(average, config if (config and config.apply_to_area) else None)
        level = performance_for(school_year, rounded)
        area_grade, _ = AreaGrade.objects.update_or_create(
            student=student,
            period=period,
            area=area,
            defaults={
                "school_year": school_year,
                "score": rounded,
                "performance": level,
                "is_passing": level.is_passing if level else True,
            },
        )
        results.append(area_grade)
    return results


def student_period_average(student, period):
    from .models import AreaGrade

    value = AreaGrade.objects.filter(student=student, period=period, deleted_at__isnull=True).aggregate(
        average=Avg("score")
    )["average"]
    return round(float(value or 0), 2)


def student_year_average(student, school_year):
    from .models import SubjectGrade

    value = SubjectGrade.objects.filter(
        student=student, school_year=school_year, deleted_at__isnull=True
    ).aggregate(average=Avg("final_score"))["average"]
    return round(float(value or 0), 2)


def group_ranking(group, period=None):
    """Devuelve el escalafon del grupo por promedio."""
    from .models import SubjectGrade

    queryset = SubjectGrade.objects.filter(group=group, deleted_at__isnull=True)
    if period:
        queryset = queryset.filter(period=period)
    rows = (
        queryset.values("student_id", "student__first_name", "student__last_name")
        .annotate(average=Avg("final_score"))
        .order_by("-average")
    )
    ranking = []
    for position, row in enumerate(rows, start=1):
        ranking.append(
            {
                "position": position,
                "student_id": row["student_id"],
                "student": f"{row['student__last_name']} {row['student__first_name']}".strip(),
                "average": round(float(row["average"] or 0), 2),
            }
        )
    return ranking


# ---------------------------------------------------------------------------
# Planilla de notas
# ---------------------------------------------------------------------------
def build_grade_sheet(assignment, period):
    """Estructura completa de la planilla de digitacion de notas."""
    from core.teachers.models import TeacherAcademicProcess

    from .models import GradeSheetLock, ProcessGrade, SubjectGrade

    processes = list(
        TeacherAcademicProcess.objects.filter(
            assignment=assignment, period=period, deleted_at__isnull=True
        ).order_by("order", "id")
    )
    enrollments = (
        assignment.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True)
        .select_related("student")
        .order_by("student__last_name", "student__first_name")
    )

    process_grades = {
        (row.student_id, row.process_id): row
        for row in ProcessGrade.objects.filter(
            assignment=assignment, period=period, deleted_at__isnull=True
        )
    }
    subject_grades = {
        row.student_id: row
        for row in SubjectGrade.objects.filter(
            subject=assignment.subject, period=period, group=assignment.group, deleted_at__isnull=True
        )
    }

    lock = GradeSheetLock.objects.filter(
        period=period, group=assignment.group, deleted_at__isnull=True
    ).filter(subject__in=[assignment.subject, None]).first()

    scale = default_scale(period.school_year)
    rows = []
    for enrollment in enrollments:
        student = enrollment.student
        consolidated = subject_grades.get(student.id)
        rows.append(
            {
                "student_id": student.id,
                "student": student.full_name,
                "document": student.document_number,
                "photo": student.photo.url if student.photo else None,
                "grades": {
                    str(process.id): (
                        float(process_grades[(student.id, process.id)].score)
                        if (student.id, process.id) in process_grades
                        and process_grades[(student.id, process.id)].score is not None
                        else None
                    )
                    for process in processes
                },
                "final": float(consolidated.final_score) if consolidated and consolidated.final_score else None,
                "performance": consolidated.performance.name if consolidated and consolidated.performance else None,
                "absences": consolidated.absences if consolidated else 0,
            }
        )

    return {
        "assignment": {
            "id": assignment.id,
            "teacher": assignment.teacher.full_name,
            "subject": assignment.subject.name,
            "group": assignment.group.name,
            "grade": assignment.group.grade.name,
        },
        "period": {"id": period.id, "name": period.name, "open": period.is_open_now},
        "locked": bool(lock and lock.locked),
        # Se envian los niveles de desempeno y la politica de decimas para que
        # la planilla calcule la definitiva en pantalla con la misma formula
        # del servidor. El calculo definitivo lo sigue haciendo el backend al
        # guardar: lo del navegador es una previsualizacion.
        "scale": {
            "minimum": float(scale.minimum) if scale else 1.0,
            "maximum": float(scale.maximum) if scale else 5.0,
            "passing": float(scale.passing) if scale else 3.0,
            "decimals": scale.decimals if scale else 1,
            "levels": [
                {
                    "name": level.name,
                    "minimum": float(level.minimum),
                    "maximum": float(level.maximum),
                    "is_passing": level.is_passing,
                    "order": level.order,
                }
                for level in (
                    scale.levels.filter(deleted_at__isnull=True).order_by("order") if scale else []
                )
            ],
        },
        "rounding": _rounding_payload(period.school_year),
        "processes": [
            {"id": process.id, "name": process.name, "weight": float(process.weight), "closed": process.is_closed}
            for process in processes
        ],
        "students": rows,
    }


@transaction.atomic
def save_grade_sheet(assignment, period, payload, user=None):
    """Guarda las notas digitadas y reconsolida las definitivas."""
    from core.teachers.models import TeacherAcademicProcess

    from .models import ProcessGrade

    processes = {
        process.id: process
        for process in TeacherAcademicProcess.objects.filter(assignment=assignment, period=period)
    }
    students = {
        enrollment.student_id: enrollment.student
        for enrollment in assignment.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True)
        .select_related("student")
    }

    saved = 0
    for entry in payload:
        student = students.get(int(entry.get("student_id", 0)))
        process = processes.get(int(entry.get("process_id", 0)))
        if student is None or process is None:
            continue
        raw = entry.get("score")
        score = None if raw in ("", None) else Decimal(str(raw))
        ProcessGrade.objects.update_or_create(
            student=student,
            process=process,
            defaults={
                "assignment": assignment,
                "period": period,
                "score": score,
                "recorded_at": timezone.now(),
                "recorded_by": user,
                "updated_by": user,
            },
        )
        saved += 1

    for student in students.values():
        consolidate_subject_grade(student, assignment, period)
        compute_area_grades(student, period)

    return saved


def subject_statistics(assignment, period):
    """Estadisticas de desempeno de la asignatura en el periodo."""
    from .models import SubjectGrade

    grades = SubjectGrade.objects.filter(
        subject=assignment.subject, group=assignment.group, period=period, deleted_at__isnull=True
    )
    total = grades.count()
    passing = grades.filter(is_passing=True).count()
    return {
        "total": total,
        "passing": passing,
        "failing": total - passing,
        "average": round(float(grades.aggregate(value=Avg("final_score"))["value"] or 0), 2),
        "pass_rate": round(passing / total * 100, 1) if total else 0.0,
        "highest": float(grades.order_by("-final_score").values_list("final_score", flat=True).first() or 0),
        "lowest": float(grades.exclude(final_score=None).order_by("final_score").values_list("final_score", flat=True).first() or 0),
    }
