"""API REST del modulo de recuperaciones."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import RecoveryActivity, RecoveryActivitySubmission, RecoveryEnrollment, RecoveryPlan
from .serializers import (
    RecoveryActivitySerializer,
    RecoveryEnrollmentSerializer,
    RecoveryPlanSerializer,
    RecoverySubmissionSerializer,
)


class RecoveryPlanViewSet(BaseModelViewSet):
    module_code = "recoveries.plans"
    queryset = RecoveryPlan.objects.select_related("subject", "group", "teacher", "period", "school_year").all()
    serializer_class = RecoveryPlanSerializer
    search_fields = ["name", "description", "subject__name"]
    filterset_fields = ["school_year", "period", "subject", "group", "plan_type", "status", "is_bilingual"]
    export_filename = "planes_recuperacion"

    @action(detail=True, methods=["post"], url_path="enroll-failing")
    def enroll_failing(self, request, pk=None):
        """Inscribe automaticamente a los estudiantes que reprobaron la asignatura."""
        from core.evaluations.models import SubjectGrade

        plan = self.get_object()
        grades = SubjectGrade.objects.filter(
            subject=plan.subject, is_passing=False, deleted_at__isnull=True
        ).select_related("student")
        if plan.period_id:
            grades = grades.filter(period=plan.period)
        if plan.group_id:
            grades = grades.filter(group=plan.group)

        created = 0
        with transaction.atomic():
            for grade in grades:
                _, was_created = RecoveryEnrollment.objects.get_or_create(
                    plan=plan,
                    student=grade.student,
                    defaults={"previous_score": grade.final_score, "created_by": request.user},
                )
                created += int(was_created)
        return Response({"success": True, "enrolled": created})


class RecoveryActivityViewSet(BaseModelViewSet):
    module_code = "recoveries.activities"
    queryset = RecoveryActivity.objects.select_related("plan").all()
    serializer_class = RecoveryActivitySerializer
    filterset_fields = ["plan"]
    search_fields = ["name", "description"]
    export_filename = "actividades_recuperacion"


class RecoveryEnrollmentViewSet(BaseModelViewSet):
    module_code = "recoveries.results"
    queryset = RecoveryEnrollment.objects.select_related(
        "plan", "plan__subject", "student", "evaluated_by"
    ).all()
    serializer_class = RecoveryEnrollmentSerializer
    filterset_fields = ["plan", "student", "status", "applied_to_grade"]
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    export_filename = "resultados_recuperacion"
    export_fields = (
        "plan__name", "student__document_number", "student__last_name", "student__first_name",
        "previous_score", "score", "final_score", "status",
    )

    @action(detail=True, methods=["post"], url_path="evaluate")
    def evaluate(self, request, pk=None):
        enrollment = self.get_object()
        raw = request.data.get("score")
        if raw in (None, ""):
            return Response({"detail": "Debe indicar la nota obtenida."}, status=400)
        enrollment.score = Decimal(str(raw))
        enrollment.resolve()
        enrollment.evaluated_by = request.user
        enrollment.save()
        self.log_action("UPDATE", enrollment)
        return Response({"success": True, "final_score": str(enrollment.final_score), "status": enrollment.status})

    @action(detail=False, methods=["post"], url_path="apply-to-grades")
    def apply_to_grades(self, request):
        """Traslada la nota de recuperacion al boletin."""
        from core.evaluations.models import SubjectGrade

        plan = get_object_or_404(RecoveryPlan, pk=request.data.get("plan"))
        applied = 0
        with transaction.atomic():
            for enrollment in plan.enrollments.filter(final_score__isnull=False, deleted_at__isnull=True):
                grades = SubjectGrade.objects.filter(
                    student=enrollment.student, subject=plan.subject, deleted_at__isnull=True
                )
                if plan.period_id:
                    grades = grades.filter(period=plan.period)
                for grade in grades:
                    grade.recovered_score = enrollment.final_score
                    grade.resolve_final()
                    grade.save()
                    applied += 1
                enrollment.applied_to_grade = True
                enrollment.save(update_fields=["applied_to_grade"])
        return Response({"success": True, "applied": applied})


class RecoverySubmissionViewSet(BaseModelViewSet):
    module_code = "recoveries.activities"
    queryset = RecoveryActivitySubmission.objects.select_related(
        "activity", "enrollment", "enrollment__student"
    ).all()
    serializer_class = RecoverySubmissionSerializer
    filterset_fields = ["activity", "enrollment"]
    export_filename = "entregas_recuperacion"


ROUTES = [
    ("recovery-plans", RecoveryPlanViewSet, "recoveryplan"),
    ("recovery-activities", RecoveryActivityViewSet, "recoveryactivity"),
    ("recovery-enrollments", RecoveryEnrollmentViewSet, "recoveryenrollment"),
    ("recovery-submissions", RecoverySubmissionViewSet, "recoverysubmission"),
]
