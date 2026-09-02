"""API REST del observador del estudiante."""
from __future__ import annotations

from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import ObservationCategory, ObserverEntry, ObserverFollowUp
from .serializers import ObservationCategorySerializer, ObserverEntrySerializer, ObserverFollowUpSerializer


class ObservationCategoryViewSet(BaseModelViewSet):
    module_code = "observer.categories"
    queryset = ObservationCategory.objects.all()
    serializer_class = ObservationCategorySerializer
    search_fields = ["code", "name", "manual_article"]
    filterset_fields = ["severity", "requires_guardian", "is_active"]
    export_filename = "tipos_observacion"


class ObserverEntryViewSet(BaseModelViewSet):
    module_code = "observer.records"
    queryset = ObserverEntry.objects.select_related(
        "student", "category", "period", "reported_by"
    ).prefetch_related("follow_ups").all()
    serializer_class = ObserverEntrySerializer
    search_fields = ["student__first_name", "student__last_name", "description", "place"]
    filterset_fields = ["student", "category", "school_year", "period", "status", "guardian_notified"]
    ordering = ["-date"]
    export_filename = "observador"
    export_fields = (
        "date", "student__document_number", "student__last_name", "student__first_name",
        "category__name", "place", "description", "status",
    )

    def perform_create(self, serializer):
        instance = serializer.save(reported_by=self.request.user, created_by=self.request.user)
        self.log_action("CREATE", instance)
        self._notify(instance)
        return instance

    def _notify(self, entry):
        from core.notifications.models import Notification

        guardian_user = getattr(entry.student.main_guardian, "user", None)
        if guardian_user:
            Notification.push(
                recipient=guardian_user,
                title="Nueva anotacion en el observador",
                message=f"Se registro una anotacion de tipo {entry.category.name} el {entry.date}.",
                level="warning" if entry.category.severity != "POSITIVA" else "success",
                module="observer.records",
                icon="eye",
            )

    @action(detail=True, methods=["post"], url_path="notify-guardian")
    def notify_guardian(self, request, pk=None):
        entry = self.get_object()
        entry.notify_guardian()
        self._notify(entry)
        return Response({"success": True, "detail": "Acudiente notificado."})

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "total": queryset.count(),
                "by_severity": list(
                    queryset.values("category__severity").annotate(total=Count("id")).order_by("-total")
                ),
                "by_category": list(
                    queryset.values("category__name").annotate(total=Count("id")).order_by("-total")[:10]
                ),
                "by_status": list(queryset.values("status").annotate(total=Count("id"))),
            }
        )


class ObserverFollowUpViewSet(BaseModelViewSet):
    module_code = "observer.records"
    queryset = ObserverFollowUp.objects.select_related("entry", "responsible").all()
    serializer_class = ObserverFollowUpSerializer
    filterset_fields = ["entry", "result"]
    export_filename = "seguimientos_observador"

    def perform_create(self, serializer):
        return serializer.save(responsible=self.request.user, created_by=self.request.user)


ROUTES = [
    ("observation-categories", ObservationCategoryViewSet, "observationcategory"),
    ("observer-entries", ObserverEntryViewSet, "observerentry"),
    ("observer-followups", ObserverFollowUpViewSet, "observerfollowup"),
]
