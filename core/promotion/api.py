"""API REST de promocion y boletines."""
from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet
from core.academic.models import AcademicPeriod, Group, SchoolYear

from .models import ClosingProcess, EvaluationCommission, FinalReportCard, PromotionResult
from .serializers import (
    ClosingProcessSerializer,
    EvaluationCommissionSerializer,
    FinalReportCardSerializer,
    PromotionResultSerializer,
)
from .services import apply_rankings, generate_group_report_cards, run_closing


class ClosingProcessViewSet(BaseModelViewSet):
    module_code = "promotion.closing"
    queryset = ClosingProcess.objects.select_related("school_year", "period", "executed_by").all()
    serializer_class = ClosingProcessSerializer
    filterset_fields = ["school_year", "period", "scope", "status"]
    export_filename = "cierres_academicos"

    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        year = get_object_or_404(SchoolYear, pk=request.data.get("school_year"))
        period = AcademicPeriod.objects.filter(pk=request.data.get("period")).first()
        scope = request.data.get("scope", "PERIODO")
        process = run_closing(year, period, scope, user=request.user)
        self.log_action("PROCESS", process)
        return Response({"success": True, "process": ClosingProcessSerializer(process).data})


class PromotionResultViewSet(BaseModelViewSet):
    module_code = "promotion.results"
    queryset = PromotionResult.objects.select_related(
        "student", "group", "group__grade", "school_year", "next_grade"
    ).all()
    serializer_class = PromotionResultSerializer
    filterset_fields = ["school_year", "group", "result", "approved", "honor_roll"]
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    approve_field = "approved"
    export_filename = "promocion"
    export_fields = (
        "student__document_number", "student__last_name", "student__first_name",
        "group__name", "average", "failed_subjects", "failed_areas", "result", "rank",
    )

    @action(detail=False, methods=["post"], url_path="rebuild-rankings")
    def rebuild_rankings(self, request):
        year = get_object_or_404(SchoolYear, pk=request.data.get("school_year"))
        apply_rankings(year)
        return Response({"success": True, "detail": "Puestos recalculados."})

    @action(detail=False, methods=["post"], url_path="approve-group")
    def approve_group(self, request):
        group = get_object_or_404(Group, pk=request.data.get("group"))
        updated = PromotionResult.objects.filter(group=group, deleted_at__isnull=True).update(
            approved=True, approved_by=request.user, approved_at=timezone.now()
        )
        return Response({"success": True, "approved": updated})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "total": queryset.count(),
                "by_result": list(queryset.values("result").annotate(total=Count("id")).order_by("-total")),
                "honor_roll": queryset.filter(honor_roll=True).count(),
            }
        )


class FinalReportCardViewSet(BaseModelViewSet):
    module_code = "promotion.final_reports"
    queryset = FinalReportCard.objects.select_related(
        "student", "group", "period", "school_year"
    ).all()
    serializer_class = FinalReportCardSerializer
    filterset_fields = ["school_year", "period", "group", "is_final", "published"]
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    export_filename = "boletines"

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        group = get_object_or_404(Group, pk=request.data.get("group"))
        period = AcademicPeriod.objects.filter(pk=request.data.get("period")).first()
        is_final = bool(request.data.get("is_final"))
        cards = generate_group_report_cards(group, period, is_final, user=request.user)
        self.log_action("PROCESS", group)
        return Response({"success": True, "generated": len(cards)})

    @action(detail=False, methods=["post"], url_path="publish")
    def publish(self, request):
        ids = request.data.get("ids") or []
        group = request.data.get("group")
        queryset = FinalReportCard.objects.filter(deleted_at__isnull=True)
        queryset = queryset.filter(pk__in=ids) if ids else queryset.filter(group_id=group)
        updated = queryset.update(published=True)
        return Response({"success": True, "published": updated})


class EvaluationCommissionViewSet(BaseModelViewSet):
    module_code = "promotion.results"
    queryset = EvaluationCommission.objects.select_related("school_year", "period", "group").all()
    serializer_class = EvaluationCommissionSerializer
    filterset_fields = ["school_year", "period", "group", "closed"]
    search_fields = ["act_number", "decisions", "agenda"]
    export_filename = "comisiones_evaluacion"


ROUTES = [
    ("closing-processes", ClosingProcessViewSet, "closingprocess"),
    ("promotion-results", PromotionResultViewSet, "promotionresult"),
    ("report-cards", FinalReportCardViewSet, "finalreportcard"),
    ("evaluation-commissions", EvaluationCommissionViewSet, "evaluationcommission"),
]
