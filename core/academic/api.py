"""API REST de la Directiva Academica."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import (
    AcademicPeriod,
    AcademicProcess,
    Area,
    CoexistenceItem,
    EducationLevel,
    Grade,
    GradingScale,
    GradingScaleLevel,
    Group,
    Purpose,
    SchoolYear,
    Subject,
    ValuationDimension,
    ValueJudgment,
)
from .serializers import (
    AcademicPeriodSerializer,
    AcademicProcessSerializer,
    AreaSerializer,
    CoexistenceItemSerializer,
    EducationLevelSerializer,
    GradeSerializer,
    GradingScaleLevelSerializer,
    GradingScaleSerializer,
    GroupSerializer,
    PurposeSerializer,
    SchoolYearSerializer,
    SubjectSerializer,
    ValuationDimensionSerializer,
    ValueJudgmentSerializer,
)


class SchoolYearViewSet(BaseModelViewSet):
    module_code = "academic.years"
    queryset = SchoolYear.objects.select_related("institution").all()
    serializer_class = SchoolYearSerializer
    search_fields = ["name", "year"]
    filterset_fields = ["status", "is_current", "is_active", "institution"]
    ordering = ["-year"]
    export_filename = "anos_lectivos"

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        year = self.get_object()
        SchoolYear.objects.update(is_current=False)
        year.is_current = True
        year.status = "ACTIVO"
        year.save()
        self.log_action("UPDATE", year)
        return Response({"success": True, "detail": f"{year} definido como ano lectivo en curso."})

    @action(detail=True, methods=["post"], url_path="generate-periods")
    def generate_periods(self, request, pk=None):
        """Crea automaticamente los periodos academicos del ano lectivo."""
        year = self.get_object()
        quantity = int(request.data.get("quantity", 4))
        if quantity < 1 or quantity > 6:
            return Response({"detail": "La cantidad de periodos debe estar entre 1 y 6."}, status=400)

        total_days = (year.end_date - year.start_date).days
        block = max(total_days // quantity, 1)
        weight = round(100 / quantity, 2)
        created = []
        with transaction.atomic():
            for number in range(1, quantity + 1):
                start = year.start_date + timedelta(days=block * (number - 1))
                end = (
                    year.end_date
                    if number == quantity
                    else year.start_date + timedelta(days=block * number - 1)
                )
                period, was_created = AcademicPeriod.objects.get_or_create(
                    school_year=year,
                    number=number,
                    defaults={
                        "name": f"Periodo {number}",
                        "short_name": f"P{number}",
                        "start_date": start,
                        "end_date": end,
                        "weight": weight,
                        "is_current": number == 1,
                    },
                )
                if was_created:
                    created.append(period.name)
        return Response({"success": True, "created": created})


class AcademicPeriodViewSet(BaseModelViewSet):
    module_code = "academic.periods"
    queryset = AcademicPeriod.objects.select_related("school_year").all()
    serializer_class = AcademicPeriodSerializer
    search_fields = ["name", "short_name"]
    filterset_fields = ["school_year", "is_current", "is_recovery", "grades_open", "report_published"]
    ordering = ["school_year__year", "number"]
    export_filename = "periodos"

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        period = self.get_object()
        AcademicPeriod.objects.filter(school_year=period.school_year).update(is_current=False)
        period.is_current = True
        period.save()
        return Response({"success": True})

    @action(detail=True, methods=["post"], url_path="toggle-grades")
    def toggle_grades(self, request, pk=None):
        period = self.get_object()
        period.grades_open = not period.grades_open
        period.save(update_fields=["grades_open"])
        self.log_action("UPDATE", period)
        return Response({"success": True, "grades_open": period.grades_open})


class GradingScaleViewSet(BaseModelViewSet):
    module_code = "academic.scales"
    queryset = GradingScale.objects.select_related("school_year").prefetch_related("levels").all()
    serializer_class = GradingScaleSerializer
    search_fields = ["name"]
    filterset_fields = ["school_year", "scale_type", "is_default", "is_active"]
    export_filename = "escalas_valorativas"

    @action(detail=True, methods=["post"], url_path="apply-default-levels")
    def apply_default_levels(self, request, pk=None):
        scale = self.get_object()
        defaults = [
            ("SUP", "Superior", "Desempeno Superior", 4.60, 5.00, "#059669", True, 1),
            ("ALT", "Alto", "Desempeno Alto", 4.00, 4.59, "#0EA5E9", True, 2),
            ("BAS", "Basico", "Desempeno Basico", 3.00, 3.99, "#F59E0B", True, 3),
            ("BAJ", "Bajo", "Desempeno Bajo", 1.00, 2.99, "#EF4444", False, 4),
        ]
        created = 0
        for code, name, national, minimum, maximum, color, passing, order in defaults:
            _, was_created = GradingScaleLevel.objects.get_or_create(
                scale=scale,
                code=code,
                defaults={
                    "name": name,
                    "national_equivalent": national,
                    "minimum": minimum,
                    "maximum": maximum,
                    "color": color,
                    "is_passing": passing,
                    "order": order,
                },
            )
            created += int(was_created)
        return Response({"success": True, "created": created})


class GradingScaleLevelViewSet(BaseModelViewSet):
    module_code = "academic.scales"
    queryset = GradingScaleLevel.objects.select_related("scale").all()
    serializer_class = GradingScaleLevelSerializer
    filterset_fields = ["scale", "is_passing"]
    search_fields = ["name", "code"]
    export_filename = "niveles_desempeno"


class ValuationDimensionViewSet(BaseModelViewSet):
    module_code = "academic.dimensions"
    queryset = ValuationDimension.objects.select_related("school_year").all()
    serializer_class = ValuationDimensionSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["school_year", "is_active"]
    export_filename = "dimensiones"


class EducationLevelViewSet(BaseModelViewSet):
    module_code = "academic.levels"
    queryset = EducationLevel.objects.select_related("institution").all()
    serializer_class = EducationLevelSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["institution", "is_preschool", "is_active"]
    export_filename = "niveles_educativos"


class GradeViewSet(BaseModelViewSet):
    module_code = "academic.grades"
    queryset = Grade.objects.select_related("level").all()
    serializer_class = GradeSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["level", "is_graduation", "is_active"]
    ordering = ["order", "numeric_value"]
    export_filename = "grados"


class GroupViewSet(BaseModelViewSet):
    module_code = "academic.groups"
    queryset = Group.objects.select_related("grade", "grade__level", "campus", "shift", "director").all()
    serializer_class = GroupSerializer
    search_fields = ["code", "name", "classroom"]
    filterset_fields = ["school_year", "grade", "campus", "shift", "is_active"]
    export_filename = "grupos"

    @action(detail=True, methods=["get"], url_path="students")
    def students(self, request, pk=None):
        from core.students.serializers import StudentListSerializer

        group = self.get_object()
        enrollments = group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True).select_related("student")
        students = [enrollment.student for enrollment in enrollments]
        return Response({"count": len(students), "results": StudentListSerializer(students, many=True).data})


class AreaViewSet(BaseModelViewSet):
    module_code = "academic.areas"
    queryset = Area.objects.select_related("school_year").all()
    serializer_class = AreaSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["school_year", "is_mandatory", "is_active"]
    export_filename = "areas"


class SubjectViewSet(BaseModelViewSet):
    module_code = "academic.subjects"
    queryset = Subject.objects.select_related("area", "area__school_year").prefetch_related("grades").all()
    serializer_class = SubjectSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["area", "is_bilingual", "affects_promotion", "is_active"]
    export_filename = "asignaturas"


class AcademicProcessViewSet(BaseModelViewSet):
    module_code = "academic.processes"
    queryset = AcademicProcess.objects.select_related("period", "subject", "dimension").all()
    serializer_class = AcademicProcessSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["school_year", "period", "subject", "dimension"]
    export_filename = "procesos_academicos"


class ValueJudgmentViewSet(BaseModelViewSet):
    module_code = "academic.judgments"
    queryset = ValueJudgment.objects.select_related("subject", "grade", "period", "performance_level").all()
    serializer_class = ValueJudgmentSerializer
    search_fields = ["text", "code"]
    filterset_fields = ["school_year", "subject", "grade", "period", "judgment_type"]
    export_filename = "juicios_valorativos"


class CoexistenceItemViewSet(BaseModelViewSet):
    module_code = "academic.coexistence"
    queryset = CoexistenceItem.objects.select_related("school_year").all()
    serializer_class = CoexistenceItemSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["school_year", "item_type", "affects_report"]
    export_filename = "convivencia"


class PurposeViewSet(BaseModelViewSet):
    module_code = "academic.purposes"
    queryset = Purpose.objects.select_related("grade", "dimension", "period").all()
    serializer_class = PurposeSerializer
    search_fields = ["text", "code"]
    filterset_fields = ["school_year", "grade", "dimension", "period"]
    export_filename = "propositos"


ROUTES = [
    ("school-years", SchoolYearViewSet, "schoolyear"),
    ("periods", AcademicPeriodViewSet, "academicperiod"),
    ("grading-scales", GradingScaleViewSet, "gradingscale"),
    ("grading-levels", GradingScaleLevelViewSet, "gradingscalelevel"),
    ("dimensions", ValuationDimensionViewSet, "valuationdimension"),
    ("education-levels", EducationLevelViewSet, "educationlevel"),
    ("grades", GradeViewSet, "grade"),
    ("groups", GroupViewSet, "group"),
    ("areas", AreaViewSet, "area"),
    ("subjects", SubjectViewSet, "subject"),
    ("academic-processes", AcademicProcessViewSet, "academicprocess"),
    ("value-judgments", ValueJudgmentViewSet, "valuejudgment"),
    ("coexistence-items", CoexistenceItemViewSet, "coexistenceitem"),
    ("purposes", PurposeViewSet, "purpose"),
]
