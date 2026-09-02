"""API REST de datos institucionales."""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import Campus, Institution, InstitutionalCalendar, Shift
from .serializers import (
    CampusSerializer,
    InstitutionalCalendarSerializer,
    InstitutionSerializer,
    ShiftSerializer,
)


class InstitutionViewSet(BaseModelViewSet):
    module_code = "institutions.profile"
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    search_fields = ["name", "short_name", "code", "nit", "city"]
    filterset_fields = ["nature", "calendar", "is_active"]
    export_filename = "instituciones"

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        institution = Institution.current()
        if institution is None:
            return Response({"detail": "No hay institucion configurada."}, status=404)
        return Response(InstitutionSerializer(institution, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        institution = self.get_object()
        institution.is_default = True
        institution.save()
        return Response({"success": True})


class CampusViewSet(BaseModelViewSet):
    module_code = "institutions.campuses"
    queryset = Campus.objects.select_related("institution", "coordinator").all()
    serializer_class = CampusSerializer
    search_fields = ["code", "name", "address"]
    filterset_fields = ["institution", "is_main", "is_active"]
    export_filename = "sedes"


class ShiftViewSet(BaseModelViewSet):
    module_code = "institutions.campuses"
    queryset = Shift.objects.select_related("institution").all()
    serializer_class = ShiftSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["institution", "is_active"]
    export_filename = "jornadas"


class InstitutionalCalendarViewSet(BaseModelViewSet):
    module_code = "institutions.profile"
    queryset = InstitutionalCalendar.objects.select_related("institution").all()
    serializer_class = InstitutionalCalendarSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["institution", "event_type"]
    export_filename = "calendario_institucional"


ROUTES = [
    ("institutions", InstitutionViewSet, "institution"),
    ("campuses", CampusViewSet, "campus"),
    ("shifts", ShiftViewSet, "shift"),
    ("institutional-calendar", InstitutionalCalendarViewSet, "institutionalcalendar"),
]
