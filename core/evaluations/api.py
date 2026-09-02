"""API REST del modulo de evaluaciones."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import HasModulePermission, user_has_permission
from config.viewsets import BaseModelViewSet
from core.academic.models import AcademicPeriod, Group
from core.teachers.models import TeachingAssignment

from .models import (
    AreaGrade,
    BilingualEvaluation,
    GradeSheetLock,
    ProcessGrade,
    PurposeEvaluation,
    QualitativeEvaluation,
    StudentJudgment,
    SubjectGrade,
)
from .serializers import (
    AreaGradeSerializer,
    BilingualEvaluationSerializer,
    GradeSheetLockSerializer,
    GradeSheetSaveSerializer,
    ProcessGradeSerializer,
    PurposeEvaluationSerializer,
    QualitativeEvaluationSerializer,
    StudentJudgmentSerializer,
    SubjectGradeSerializer,
)
from .services import (
    build_grade_sheet,
    consolidate_group_period,
    group_ranking,
    save_grade_sheet,
    subject_statistics,
)


class ProcessGradeViewSet(BaseModelViewSet):
    module_code = "evaluations.grades"
    queryset = ProcessGrade.objects.select_related(
        "student", "assignment", "assignment__subject", "process", "period"
    ).all()
    serializer_class = ProcessGradeSerializer
    filterset_fields = ["student", "assignment", "process", "period"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "notas_procesos"


class SubjectGradeViewSet(BaseModelViewSet):
    module_code = "evaluations.grades"
    queryset = SubjectGrade.objects.select_related(
        "student", "subject", "subject__area", "group", "period", "teacher", "performance"
    ).all()
    serializer_class = SubjectGradeSerializer
    filterset_fields = ["student", "subject", "group", "period", "school_year", "status", "is_passing"]
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    export_filename = "notas_asignaturas"
    export_fields = (
        "student__document_number", "student__last_name", "student__first_name",
        "group__name", "subject__name", "period__name", "score", "recovered_score",
        "final_score", "performance__name", "absences",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("mine") == "1":
            teacher = getattr(self.request.user, "teacher_profile", None)
            queryset = queryset.filter(teacher=teacher) if teacher else queryset.none()
        student_profile = getattr(self.request.user, "student_profile", None)
        if student_profile and not user_has_permission(self.request.user, self.module_code, "edit"):
            queryset = queryset.filter(student=student_profile)
        return queryset

    @action(detail=False, methods=["post"], url_path="consolidate")
    def consolidate(self, request):
        group = get_object_or_404(Group, pk=request.data.get("group"))
        period = get_object_or_404(AcademicPeriod, pk=request.data.get("period"))
        processed = consolidate_group_period(group, period)
        self.log_action("PROCESS", group)
        return Response({"success": True, "processed": processed})

    @action(detail=False, methods=["get"], url_path="ranking")
    def ranking(self, request):
        group = get_object_or_404(Group, pk=request.query_params.get("group"))
        period = AcademicPeriod.objects.filter(pk=request.query_params.get("period")).first()
        return Response({"results": group_ranking(group, period)})


class AreaGradeViewSet(BaseModelViewSet):
    module_code = "evaluations.grades"
    queryset = AreaGrade.objects.select_related("student", "area", "period", "performance").all()
    serializer_class = AreaGradeSerializer
    filterset_fields = ["student", "area", "period", "school_year", "is_passing"]
    export_filename = "notas_areas"


class StudentJudgmentViewSet(BaseModelViewSet):
    module_code = "evaluations.judgments"
    queryset = StudentJudgment.objects.select_related("student", "subject", "period", "judgment").all()
    serializer_class = StudentJudgmentSerializer
    filterset_fields = ["student", "subject", "period", "judgment_type"]
    search_fields = ["custom_text", "student__first_name", "student__last_name"]
    export_filename = "juicios_estudiantes"


class QualitativeEvaluationViewSet(BaseModelViewSet):
    module_code = "evaluations.qualitative"
    queryset = QualitativeEvaluation.objects.select_related(
        "student", "subject", "dimension", "period", "performance"
    ).all()
    serializer_class = QualitativeEvaluationSerializer
    filterset_fields = ["student", "subject", "dimension", "period"]
    search_fields = ["student__first_name", "student__last_name", "description"]
    export_filename = "evaluacion_cualitativa"


class PurposeEvaluationViewSet(BaseModelViewSet):
    module_code = "evaluations.preschool"
    queryset = PurposeEvaluation.objects.select_related("student", "purpose", "period").all()
    serializer_class = PurposeEvaluationSerializer
    filterset_fields = ["student", "purpose", "period", "achievement"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "propositos_preescolar"


class BilingualEvaluationViewSet(BaseModelViewSet):
    module_code = "evaluations.bilingual"
    queryset = BilingualEvaluation.objects.select_related("student", "subject", "period").all()
    serializer_class = BilingualEvaluationSerializer
    filterset_fields = ["student", "subject", "period", "cefr_level"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "modulo_bilingue"


class GradeSheetLockViewSet(BaseModelViewSet):
    module_code = "evaluations.grades"
    queryset = GradeSheetLock.objects.select_related("period", "group", "subject", "locked_by").all()
    serializer_class = GradeSheetLockSerializer
    filterset_fields = ["period", "group", "subject", "locked"]
    export_filename = "bloqueos_digitacion"

    def perform_create(self, serializer):
        return serializer.save(locked_by=self.request.user, created_by=self.request.user)


class GradeSheetAPIView(APIView):
    """Planilla de digitacion de notas: lectura y guardado masivo."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "evaluations.grades"

    def get(self, request):
        assignment = get_object_or_404(TeachingAssignment, pk=request.query_params.get("assignment"))
        period = get_object_or_404(AcademicPeriod, pk=request.query_params.get("period"))
        data = build_grade_sheet(assignment, period)
        data["statistics"] = subject_statistics(assignment, period)
        return Response(data)

    def post(self, request):
        self.required_action = "edit"
        serializer = GradeSheetSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = get_object_or_404(TeachingAssignment, pk=serializer.validated_data["assignment"])
        period = get_object_or_404(AcademicPeriod, pk=serializer.validated_data["period"])

        if not period.is_open_now and not request.user.is_super_admin:
            return Response(
                {"success": False, "detail": "La digitacion de notas esta cerrada para este periodo."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lock = (
            GradeSheetLock.objects.filter(period=period, group=assignment.group, locked=True, deleted_at__isnull=True)
            .filter(subject__in=[assignment.subject, None])
            .first()
        )
        if lock and not request.user.is_super_admin:
            return Response(
                {"success": False, "detail": f"Planilla bloqueada: {lock.reason or 'sin motivo registrado'}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        saved = save_grade_sheet(assignment, period, serializer.validated_data["entries"], user=request.user)

        from core.audit.services import register_audit

        register_audit(
            user=request.user,
            action="UPDATE",
            module=self.module_code,
            instance=assignment,
            request=request,
            description=f"Digitacion de {saved} notas en {assignment.subject} - {assignment.group}",
        )
        data = build_grade_sheet(assignment, period)
        data["statistics"] = subject_statistics(assignment, period)
        data["saved"] = saved
        return Response(data)


ROUTES = [
    ("process-grades", ProcessGradeViewSet, "processgrade"),
    ("subject-grades", SubjectGradeViewSet, "subjectgrade"),
    ("area-grades", AreaGradeViewSet, "areagrade"),
    ("student-judgments", StudentJudgmentViewSet, "studentjudgment"),
    ("qualitative-evaluations", QualitativeEvaluationViewSet, "qualitativeevaluation"),
    ("purpose-evaluations", PurposeEvaluationViewSet, "purposeevaluation"),
    ("bilingual-evaluations", BilingualEvaluationViewSet, "bilingualevaluation"),
    ("grade-locks", GradeSheetLockViewSet, "gradesheetlock"),
]
