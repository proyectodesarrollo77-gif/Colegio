"""API REST de configuracion transversal."""
from __future__ import annotations

from decimal import Decimal

from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import GradeDecimalConfig, ReportHeader, SystemParameter
from .serializers import GradeDecimalConfigSerializer, ReportHeaderSerializer, SystemParameterSerializer


class ReportHeaderViewSet(BaseModelViewSet):
    module_code = "configuration.report_header"
    queryset = ReportHeader.objects.select_related("institution").all()
    serializer_class = ReportHeaderSerializer
    search_fields = ["name", "line_1", "line_2"]
    filterset_fields = ["institution", "is_default", "is_active"]
    export_filename = "encabezados_reportes"

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        header = self.get_object()
        header.is_default = True
        header.save()
        return Response({"success": True})


class GradeDecimalConfigViewSet(BaseModelViewSet):
    module_code = "configuration.grade_decimals"
    queryset = GradeDecimalConfig.objects.select_related("school_year").all()
    serializer_class = GradeDecimalConfigSerializer
    search_fields = ["name"]
    filterset_fields = ["school_year", "is_default", "rounding_mode"]
    export_filename = "decimas_notas"

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        """Simula la aproximacion configurada sobre una lista de valores."""
        config = self.get_object()
        values = request.data.get("values") or [2.94, 2.95, 3.44, 3.46, 4.55, 4.94]
        results = []
        for raw in values:
            try:
                results.append({"input": str(raw), "output": str(config.apply(Decimal(str(raw))))})
            except (TypeError, ValueError):
                continue
        return Response({"results": results})


class SystemParameterViewSet(BaseModelViewSet):
    module_code = "configuration.parameters"
    queryset = SystemParameter.objects.all()
    serializer_class = SystemParameterSerializer
    search_fields = ["key", "label", "group"]
    filterset_fields = ["group", "value_type", "is_active"]
    export_filename = "parametros"

    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request):
        updated = 0
        for key, value in (request.data.get("values") or {}).items():
            parameter = SystemParameter.objects.filter(key=key, is_editable=True).first()
            if parameter:
                parameter.value = str(value)
                parameter.save(update_fields=["value"])
                updated += 1
        return Response({"success": True, "updated": updated})


ROUTES = [
    ("report-headers", ReportHeaderViewSet, "reportheader"),
    ("grade-decimals", GradeDecimalConfigViewSet, "gradedecimalconfig"),
    ("system-parameters", SystemParameterViewSet, "systemparameter"),
]
