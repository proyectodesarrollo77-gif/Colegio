"""API REST de enfasis y disciplinas."""
from __future__ import annotations

from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import Emphasis, EmphasisEnrollment, EmphasisGroup
from .serializers import EmphasisEnrollmentSerializer, EmphasisGroupSerializer, EmphasisSerializer


class EmphasisViewSet(BaseModelViewSet):
    module_code = "emphases.catalog"
    queryset = Emphasis.objects.select_related("institution").all()
    serializer_class = EmphasisSerializer
    search_fields = ["code", "name", "description"]
    filterset_fields = ["institution", "kind", "is_active"]
    export_filename = "enfasis"


class EmphasisGroupViewSet(BaseModelViewSet):
    module_code = "emphases.groups"
    queryset = EmphasisGroup.objects.select_related("emphasis", "teacher", "school_year").prefetch_related("grades").all()
    serializer_class = EmphasisGroupSerializer
    search_fields = ["code", "name", "place"]
    filterset_fields = ["emphasis", "school_year", "teacher", "status", "is_active"]
    export_filename = "grupos_enfasis"

    @action(detail=True, methods=["post"], url_path="open")
    def open_group(self, request, pk=None):
        group = self.get_object()
        group.status = "ABIERTO"
        group.save(update_fields=["status"])
        return Response({"success": True, "detail": "Grupo abierto para inscripciones."})

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        groups = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "results": [
                    {
                        "id": group.id,
                        "emphasis": group.emphasis.name,
                        "group": group.name,
                        "capacity": group.capacity,
                        "enrolled": group.enrolled_count,
                        "available": group.available_seats,
                    }
                    for group in groups
                ]
            }
        )


class EmphasisEnrollmentViewSet(BaseModelViewSet):
    module_code = "emphases.enrollment"
    queryset = EmphasisEnrollment.objects.select_related("group", "group__emphasis", "student").all()
    serializer_class = EmphasisEnrollmentSerializer
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    filterset_fields = ["group", "student", "status"]
    export_filename = "matriculas_enfasis"
    export_fields = (
        "group__emphasis__name", "group__name", "student__document_number",
        "student__last_name", "student__first_name", "enrolled_at", "status",
    )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        data = (
            EmphasisEnrollment.objects.filter(status="ACTIVA", deleted_at__isnull=True)
            .values("group__emphasis__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        return Response({"results": list(data)})


ROUTES = [
    ("emphases", EmphasisViewSet, "emphasis"),
    ("emphasis-groups", EmphasisGroupViewSet, "emphasisgroup"),
    ("emphasis-enrollments", EmphasisEnrollmentViewSet, "emphasisenrollment"),
]
