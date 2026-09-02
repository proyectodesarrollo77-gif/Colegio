"""
Motor de cierre academico, promocion y generacion de boletines.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone


def evaluate_promotion(student, school_year):
    """Determina el resultado de promocion de un estudiante."""
    from core.evaluations.models import AreaGrade, SubjectGrade

    subject_grades = SubjectGrade.objects.filter(
        student=student, school_year=school_year, deleted_at__isnull=True
    ).select_related("subject")

    by_subject = {}
    for grade in subject_grades:
        by_subject.setdefault(grade.subject_id, []).append(grade)

    failed_subjects = 0
    for subject_id, grades in by_subject.items():
        values = [Decimal(str(item.final_score or 0)) for item in grades if item.final_score is not None]
        if not values:
            continue
        average = sum(values) / len(values)
        scale = school_year.grading_scales.filter(is_default=True).first()
        passing = Decimal(str(scale.passing)) if scale else Decimal("3.00")
        subject = grades[0].subject
        if average < passing and subject.affects_promotion:
            failed_subjects += 1

    failed_areas = (
        AreaGrade.objects.filter(student=student, school_year=school_year, is_passing=False, deleted_at__isnull=True)
        .values("area_id")
        .distinct()
        .count()
    )

    average = subject_grades.aggregate(value=Avg("final_score"))["value"] or Decimal("0.00")

    max_failed = 2
    if failed_areas == 0 and failed_subjects == 0:
        result = "PROMOVIDO"
    elif failed_areas <= 1 and failed_subjects <= max_failed:
        result = "PROMOVIDO_COMPROMISO"
    elif failed_subjects > max_failed or failed_areas > 2:
        result = "NO_PROMOVIDO"
    else:
        result = "PENDIENTE_RECUPERACION"

    return {
        "average": round(Decimal(str(average)), 2),
        "failed_subjects": failed_subjects,
        "failed_areas": failed_areas,
        "result": result,
    }


@transaction.atomic
def run_closing(school_year, period=None, scope="PERIODO", user=None):
    """Ejecuta el cierre academico consolidando notas y promocion."""
    from core.academic.models import Group
    from core.evaluations.services import consolidate_group_period
    from core.students.models import Enrollment

    from .models import ClosingProcess, PromotionResult

    process = ClosingProcess.objects.create(
        school_year=school_year,
        period=period,
        scope=scope,
        status="EN_PROCESO",
        started_at=timezone.now(),
        executed_by=user,
        created_by=user,
    )

    log_lines = []
    total_grades = 0
    groups = Group.objects.filter(school_year=school_year, deleted_at__isnull=True)

    if period:
        for group in groups:
            count = consolidate_group_period(group, period)
            total_grades += count
            log_lines.append(f"Grupo {group.name}: {count} notas consolidadas.")

    students_processed = 0
    if scope == "ANUAL":
        enrollments = Enrollment.objects.filter(
            school_year=school_year, status="ACTIVA", deleted_at__isnull=True
        ).select_related("student", "group", "group__grade")
        for enrollment in enrollments:
            outcome = evaluate_promotion(enrollment.student, school_year)
            PromotionResult.objects.update_or_create(
                student=enrollment.student,
                school_year=school_year,
                defaults={
                    "group": enrollment.group,
                    "next_grade": enrollment.group.grade.next_grade,
                    "average": outcome["average"],
                    "failed_subjects": outcome["failed_subjects"],
                    "failed_areas": outcome["failed_areas"],
                    "result": "GRADUADO" if enrollment.group.grade.is_graduation and outcome["result"].startswith("PROMOVIDO") else outcome["result"],
                    "created_by": user,
                    "updated_by": user,
                },
            )
            students_processed += 1
        log_lines.append(f"Promocion evaluada para {students_processed} estudiantes.")
        apply_rankings(school_year)

    process.status = "CONSOLIDADO"
    process.finished_at = timezone.now()
    process.processed_grades = total_grades
    process.processed_students = students_processed
    process.log = "\n".join(log_lines)
    process.save()
    return process


def apply_rankings(school_year):
    """Asigna el puesto de cada estudiante dentro de su grupo."""
    from .models import PromotionResult

    groups = (
        PromotionResult.objects.filter(school_year=school_year, deleted_at__isnull=True)
        .values_list("group_id", flat=True)
        .distinct()
    )
    for group_id in groups:
        rows = PromotionResult.objects.filter(
            school_year=school_year, group_id=group_id, deleted_at__isnull=True
        ).order_by("-average")
        for position, row in enumerate(rows, start=1):
            row.rank = position
            row.honor_roll = position <= 3
            row.save(update_fields=["rank", "honor_roll"])


@transaction.atomic
def build_report_card(student, school_year, period=None, is_final=False, user=None):
    """Genera el boletin del estudiante con el detalle completo de notas."""
    from core.evaluations.models import AreaGrade, SubjectGrade
    from core.tutoring.models import TutoringJudgment
    from core.students.models import Enrollment

    from .models import FinalReportCard

    enrollment = Enrollment.objects.filter(
        student=student, school_year=school_year, deleted_at__isnull=True
    ).select_related("group", "group__grade").first()
    if enrollment is None:
        return None

    grades = SubjectGrade.objects.filter(
        student=student, school_year=school_year, deleted_at__isnull=True
    ).select_related("subject", "subject__area", "period", "performance", "teacher")
    if period:
        grades = grades.filter(period=period)

    areas = AreaGrade.objects.filter(
        student=student, school_year=school_year, deleted_at__isnull=True
    ).select_related("area", "performance")
    if period:
        areas = areas.filter(period=period)

    detail = {}
    for grade in grades.order_by("subject__area__order", "subject__order"):
        area = grade.subject.area
        block = detail.setdefault(
            area.name, {"area": area.name, "color": area.color, "subjects": [], "average": 0}
        )
        block["subjects"].append(
            {
                "subject": grade.subject.name,
                "hours": grade.subject.weekly_hours,
                "score": float(grade.final_score or 0),
                "performance": grade.performance.name if grade.performance else "",
                "absences": grade.absences,
                "teacher": grade.teacher.full_name if grade.teacher else "",
                "observation": grade.observation,
            }
        )

    for area_grade in areas:
        if area_grade.area.name in detail:
            detail[area_grade.area.name]["average"] = float(area_grade.score or 0)
            detail[area_grade.area.name]["performance"] = (
                area_grade.performance.name if area_grade.performance else ""
            )

    average = grades.aggregate(value=Avg("final_score"))["value"] or 0
    absences = sum(grade.absences for grade in grades)
    judgment = TutoringJudgment.objects.filter(student=student, period=period).first() if period else None

    card, _ = FinalReportCard.objects.update_or_create(
        student=student,
        school_year=school_year,
        period=period,
        is_final=is_final,
        defaults={
            "group": enrollment.group,
            "average": round(float(average), 2),
            "total_absences": absences,
            "tutor_observation": judgment.recommendations if judgment else "",
            "generated_at": timezone.now(),
            "generated_by": user,
            "snapshot": {"areas": list(detail.values())},
            "updated_by": user,
        },
    )
    return card


def generate_group_report_cards(group, period=None, is_final=False, user=None):
    cards = []
    enrollments = group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True).select_related("student")
    for enrollment in enrollments:
        card = build_report_card(enrollment.student, group.school_year, period, is_final, user)
        if card:
            cards.append(card)
    return cards
