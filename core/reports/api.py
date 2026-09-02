"""API REST del modulo de reportes y estadisticas institucionales."""
from __future__ import annotations

import datetime as dt
import time

from django.db.models import Avg, Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import HasModulePermission
from config.viewsets import BaseModelViewSet

from .models import DashboardIndicator, ReportDefinition, ReportExecution
from .serializers import DashboardIndicatorSerializer, ReportDefinitionSerializer, ReportExecutionSerializer


class ReportDefinitionViewSet(BaseModelViewSet):
    module_code = "reports.academic"
    queryset = ReportDefinition.objects.all()
    serializer_class = ReportDefinitionSerializer
    search_fields = ["code", "name", "description"]
    filterset_fields = ["category", "is_active"]
    export_filename = "catalogo_reportes"


class ReportExecutionViewSet(BaseModelViewSet):
    module_code = "reports.academic"
    queryset = ReportExecution.objects.select_related("definition", "executed_by").all()
    serializer_class = ReportExecutionSerializer
    filterset_fields = ["definition", "status", "output_format"]
    export_filename = "historial_reportes"

    def perform_create(self, serializer):
        started = time.monotonic()
        instance = serializer.save(executed_by=self.request.user, created_by=self.request.user)
        instance.status = "COMPLETADO"
        instance.duration_ms = int((time.monotonic() - started) * 1000)
        instance.save(update_fields=["status", "duration_ms"])
        self.log_action("EXPORT", instance)
        return instance


class DashboardIndicatorViewSet(BaseModelViewSet):
    module_code = "dashboard"
    queryset = DashboardIndicator.objects.all()
    serializer_class = DashboardIndicatorSerializer
    filterset_fields = ["category", "is_active"]
    export_filename = "indicadores"


class AcademicStatisticsAPIView(APIView):
    """Estadisticas academicas consolidadas para reportes y tableros."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "reports.statistics"

    def get(self, request):
        from core.academic.models import Group, SchoolYear
        from core.evaluations.models import SubjectGrade
        from core.students.models import Enrollment, Student

        year_id = request.query_params.get("school_year")
        year = SchoolYear.objects.filter(pk=year_id).first() or SchoolYear.current()
        if year is None:
            return Response({"detail": "No hay ano lectivo configurado."}, status=404)

        enrollments = Enrollment.objects.filter(school_year=year, deleted_at__isnull=True)
        grades = SubjectGrade.objects.filter(school_year=year, deleted_at__isnull=True)

        by_grade = list(
            enrollments.filter(status="ACTIVA")
            .values("group__grade__name")
            .annotate(total=Count("id"))
            .order_by("group__grade__order")
        )
        by_group = list(
            enrollments.filter(status="ACTIVA")
            .values("group__name")
            .annotate(total=Count("id"))
            .order_by("group__grade__order", "group__code")
        )
        by_area = list(
            grades.values("subject__area__name")
            .annotate(average=Avg("final_score"), total=Count("id"))
            .order_by("subject__area__order")
        )
        by_period = list(
            grades.values("period__name", "period__number")
            .annotate(average=Avg("final_score"))
            .order_by("period__number")
        )
        performance = list(
            grades.values("performance__name", "performance__color")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        gender = list(
            Student.objects.filter(status="ACTIVO", deleted_at__isnull=True)
            .values("gender")
            .annotate(total=Count("id"))
        )

        total_grades = grades.count()
        passing = grades.filter(is_passing=True).count()

        return Response(
            {
                "school_year": {"id": year.id, "name": year.name, "progress": year.progress},
                "totals": {
                    "students": enrollments.filter(status="ACTIVA").count(),
                    "groups": Group.objects.filter(school_year=year, deleted_at__isnull=True).count(),
                    "grades_recorded": total_grades,
                    "pass_rate": round(passing / total_grades * 100, 1) if total_grades else 0,
                    "average": round(float(grades.aggregate(v=Avg("final_score"))["v"] or 0), 2),
                },
                "by_grade": by_grade,
                "by_group": by_group,
                "by_area": by_area,
                "by_period": by_period,
                "performance": performance,
                "gender": gender,
            }
        )


class AdministrativeStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "reports.administrative"

    def get(self, request):
        from core.authentication.models import AccessLog
        from core.students.models import Enrollment
        from core.teachers.models import Teacher, TeachingAssignment
        from core.users.models import User

        return Response(
            {
                "users": {
                    "total": User.objects.filter(deleted_at__isnull=True).count(),
                    "active": User.objects.filter(is_active=True, deleted_at__isnull=True).count(),
                    "with_2fa": User.objects.filter(two_factor_enabled=True, deleted_at__isnull=True).count(),
                    "by_role": list(
                        User.objects.filter(deleted_at__isnull=True)
                        .values("role__name")
                        .annotate(total=Count("id"))
                        .order_by("-total")
                    ),
                },
                "teachers": {
                    "total": Teacher.objects.filter(deleted_at__isnull=True).count(),
                    "active": Teacher.objects.filter(status="ACTIVO", deleted_at__isnull=True).count(),
                    "assignments": TeachingAssignment.objects.filter(deleted_at__isnull=True).count(),
                },
                "enrollment": {
                    "active": Enrollment.objects.filter(status="ACTIVA", deleted_at__isnull=True).count(),
                    "withdrawn": Enrollment.objects.filter(status="RETIRADA", deleted_at__isnull=True).count(),
                    "by_type": list(
                        Enrollment.objects.filter(deleted_at__isnull=True)
                        .values("enrollment_type")
                        .annotate(total=Count("id"))
                    ),
                },
                "access": {
                    "logins_today": AccessLog.objects.filter(
                        event="LOGIN", created_at__date=dt.date.today()
                    ).count(),
                    "failed": AccessLog.objects.filter(success=False).count(),
                },
            }
        )


ROUTES = [
    ("report-definitions", ReportDefinitionViewSet, "reportdefinition"),
    ("report-executions", ReportExecutionViewSet, "reportexecution"),
    ("dashboard-indicators", DashboardIndicatorViewSet, "dashboardindicator"),
]
