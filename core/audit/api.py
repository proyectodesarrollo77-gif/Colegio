"""API REST de la bitacora de auditoria."""
from __future__ import annotations

import datetime as dt

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import ReadOnlyBaseViewSet

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyBaseViewSet):
    module_code = "audit.log"
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "module", "user", "method", "status_code"]
    search_fields = ["user_label", "object_label", "description", "path", "ip_address"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Permite acotar la bitacora a un dominio: ?module_prefix=pae."""
        queryset = super().get_queryset()
        prefix = (self.request.query_params.get("module_prefix") or "").strip()
        if prefix:
            queryset = queryset.filter(module__startswith=prefix)
        return queryset

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - dt.timedelta(days=days)
        queryset = AuditLog.objects.filter(created_at__gte=since)
        by_day = (
            queryset.values("created_at__date")
            .annotate(total=Count("id"))
            .order_by("created_at__date")
        )
        return Response(
            {
                "total": queryset.count(),
                "by_action": list(queryset.values("action").annotate(total=Count("id")).order_by("-total")),
                "by_module": list(queryset.values("module").annotate(total=Count("id")).order_by("-total")[:12]),
                "by_user": list(queryset.values("user_label").annotate(total=Count("id")).order_by("-total")[:12]),
                "by_day": [
                    {"date": row["created_at__date"].isoformat(), "total": row["total"]} for row in by_day
                ],
            }
        )

    export_fields = (
        "created_at", "user_label", "role_label", "action", "module",
        "model_name", "object_label", "ip_address", "path", "status_code",
    )
    export_filename = "bitacora_auditoria"


ROUTES = [("audit-logs", AuditLogViewSet, "auditlog")]
