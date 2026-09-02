"""API REST del modulo de tutoria."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import CoexistenceEvaluation, ReportCardBlock, Tutor, TutoringJudgment, TutoringMeeting
from .serializers import (
    CoexistenceEvaluationSerializer,
    ReportCardBlockSerializer,
    TutoringJudgmentSerializer,
    TutoringMeetingSerializer,
    TutorSerializer,
)


class TutorViewSet(BaseModelViewSet):
    module_code = "tutoring.tutors"
    queryset = Tutor.objects.select_related("teacher", "group", "group__grade", "school_year").all()
    serializer_class = TutorSerializer
    filterset_fields = ["school_year", "group", "teacher", "is_main", "is_active"]
    search_fields = ["teacher__first_name", "teacher__last_name", "group__name"]
    export_filename = "tutores"


class TutoringJudgmentViewSet(BaseModelViewSet):
    module_code = "tutoring.judgments"
    queryset = TutoringJudgment.objects.select_related("student", "period", "tutor", "performance").all()
    serializer_class = TutoringJudgmentSerializer
    filterset_fields = ["student", "period", "tutor", "published"]
    search_fields = ["student__first_name", "student__last_name", "strengths", "recommendations"]
    export_filename = "juicios_tutoria"

    @action(detail=False, methods=["post"], url_path="publish")
    def publish(self, request):
        ids = request.data.get("ids") or []
        updated = TutoringJudgment.objects.filter(pk__in=ids).update(published=True)
        return Response({"success": True, "updated": updated})


class CoexistenceEvaluationViewSet(BaseModelViewSet):
    module_code = "tutoring.coexistence"
    queryset = CoexistenceEvaluation.objects.select_related("student", "period", "item", "performance").all()
    serializer_class = CoexistenceEvaluationSerializer
    filterset_fields = ["student", "period", "item"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "convivencia_valoraciones"

    def perform_create(self, serializer):
        return serializer.save(evaluated_by=self.request.user, created_by=self.request.user)


class ReportCardBlockViewSet(BaseModelViewSet):
    module_code = "tutoring.block"
    queryset = ReportCardBlock.objects.select_related("student", "period", "released_by").all()
    serializer_class = ReportCardBlockSerializer
    filterset_fields = ["student", "school_year", "period", "reason", "blocked"]
    search_fields = ["student__first_name", "student__last_name", "detail"]
    export_filename = "bloqueos_boletin"

    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, pk=None):
        block = self.get_object()
        block.release(user=request.user)
        self.log_action("APPROVE", block)
        return Response({"success": True, "detail": "Bloqueo liberado."})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        data = (
            ReportCardBlock.objects.filter(blocked=True, deleted_at__isnull=True)
            .values("reason")
            .annotate(total=Count("id"))
        )
        return Response({"results": list(data)})


class TutoringMeetingViewSet(BaseModelViewSet):
    module_code = "tutoring.reports"
    queryset = TutoringMeeting.objects.select_related("student", "tutor", "tutor__teacher").all()
    serializer_class = TutoringMeetingSerializer
    filterset_fields = ["student", "tutor", "status"]
    search_fields = ["student__first_name", "student__last_name", "subject"]
    export_filename = "citaciones_tutoria"


ROUTES = [
    ("tutors", TutorViewSet, "tutor"),
    ("tutoring-judgments", TutoringJudgmentViewSet, "tutoringjudgment"),
    ("coexistence-evaluations", CoexistenceEvaluationViewSet, "coexistenceevaluation"),
    ("report-blocks", ReportCardBlockViewSet, "reportcardblock"),
    ("tutoring-meetings", TutoringMeetingViewSet, "tutoringmeeting"),
]
