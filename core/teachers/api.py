"""API REST del modulo docente."""
from __future__ import annotations

from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import ScheduleSlot, Teacher, TeacherAbsence, TeacherAcademicProcess, TeachingAssignment
from .serializers import (
    ScheduleSlotSerializer,
    TeacherAbsenceSerializer,
    TeacherAcademicProcessSerializer,
    TeacherSerializer,
    TeachingAssignmentSerializer,
)


class TeacherViewSet(BaseModelViewSet):
    module_code = "teachers.registry"
    queryset = Teacher.objects.select_related("institution", "campus", "user").all()
    serializer_class = TeacherSerializer
    search_fields = ["first_name", "last_name", "document_number", "teacher_code", "email"]
    filterset_fields = ["status", "contract_type", "is_tutor", "is_coordinator", "campus", "is_active"]
    ordering = ["last_name", "first_name"]
    export_filename = "docentes"
    export_fields = (
        "teacher_code", "document_number", "last_name", "first_name", "email",
        "mobile", "profession", "contract_type", "weekly_hours", "status",
    )

    @action(detail=True, methods=["post"], url_path="create-user")
    def create_user(self, request, pk=None):
        from core.users.models import Role, User, UserCredentialCertificate

        teacher = self.get_object()
        if teacher.user_id:
            return Response({"detail": "El docente ya cuenta con usuario."}, status=status.HTTP_400_BAD_REQUEST)
        role, _ = Role.objects.get_or_create(
            code=Role.DOCENTE, defaults={"name": "Docente", "is_system": True, "order": 50}
        )
        password = User.generate_password()
        user = User(
            username=User.build_username(teacher.first_name, teacher.last_name, teacher.document_number),
            email=teacher.email or teacher.personal_email or f"{teacher.document_number}@docente.local",
            first_name=teacher.first_name,
            last_name=teacher.last_name,
            document_type=teacher.document_type,
            document_number=teacher.document_number,
            role=role,
            institution=teacher.institution,
            must_change_password=True,
        )
        user.set_password(password)
        user.save()
        teacher.user = user
        teacher.save(update_fields=["user"])
        UserCredentialCertificate.objects.create(user=user, plain_password=password, issued_by=request.user)
        return Response({"success": True, "username": user.username, "password": password})

    @action(detail=True, methods=["get"], url_path="workload")
    def workload(self, request, pk=None):
        teacher = self.get_object()
        assignments = teacher.assignments.select_related("subject", "group", "group__grade").filter(
            deleted_at__isnull=True
        )
        return Response(
            {
                "teacher": TeacherSerializer(teacher).data,
                "assigned_hours": teacher.assigned_hours,
                "contracted_hours": teacher.weekly_hours,
                "load_percentage": teacher.load_percentage,
                "assignments": TeachingAssignmentSerializer(assignments, many=True).data,
                "schedule": ScheduleSlotSerializer(
                    ScheduleSlot.objects.filter(assignment__teacher=teacher, deleted_at__isnull=True)
                    .select_related("assignment", "assignment__subject", "assignment__group"),
                    many=True,
                ).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="load-summary")
    def load_summary(self, request):
        data = (
            Teacher.objects.filter(status="ACTIVO", deleted_at__isnull=True)
            .annotate(
                assigned=Sum("assignments__weekly_hours", filter=None),
                groups=Count("assignments__group", distinct=True),
            )
            .values("id", "first_name", "last_name", "weekly_hours", "assigned", "groups")
            .order_by("last_name")
        )
        return Response({"results": list(data)})


class TeachingAssignmentViewSet(BaseModelViewSet):
    module_code = "teachers.subjects"
    queryset = TeachingAssignment.objects.select_related(
        "teacher", "subject", "subject__area", "group", "group__grade", "school_year"
    ).all()
    serializer_class = TeachingAssignmentSerializer
    search_fields = ["teacher__first_name", "teacher__last_name", "subject__name", "group__name"]
    filterset_fields = ["school_year", "teacher", "subject", "group", "is_main", "is_active"]
    export_filename = "asignaciones_academicas"
    export_fields = (
        "school_year__name", "teacher__last_name", "teacher__first_name",
        "subject__name", "group__name", "weekly_hours",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("mine") == "1":
            teacher = getattr(self.request.user, "teacher_profile", None)
            queryset = queryset.filter(teacher=teacher) if teacher else queryset.none()
        return queryset


class ScheduleSlotViewSet(BaseModelViewSet):
    module_code = "teachers.schedules"
    queryset = ScheduleSlot.objects.select_related(
        "assignment", "assignment__teacher", "assignment__subject", "assignment__group"
    ).all()
    serializer_class = ScheduleSlotSerializer
    filterset_fields = ["weekday", "assignment", "assignment__teacher", "assignment__group"]
    search_fields = ["classroom", "assignment__subject__name"]
    export_filename = "horarios"

    @action(detail=False, methods=["get"], url_path="matrix")
    def matrix(self, request):
        """Horario en formato matriz para un docente o grupo."""
        queryset = self.filter_queryset(self.get_queryset())
        teacher = request.query_params.get("teacher")
        group = request.query_params.get("group")
        if teacher:
            queryset = queryset.filter(assignment__teacher_id=teacher)
        if group:
            queryset = queryset.filter(assignment__group_id=group)

        blocks = {}
        for slot in queryset:
            key = slot.block
            blocks.setdefault(key, {"block": key, "start": str(slot.start_time), "end": str(slot.end_time), "days": {}})
            blocks[key]["days"][slot.weekday] = {
                "subject": slot.assignment.subject.name,
                "group": slot.assignment.group.name,
                "teacher": slot.assignment.teacher.full_name,
                "classroom": slot.classroom,
            }
        return Response({"results": sorted(blocks.values(), key=lambda item: item["block"])})


class TeacherAcademicProcessViewSet(BaseModelViewSet):
    module_code = "teachers.processes"
    queryset = TeacherAcademicProcess.objects.select_related(
        "assignment", "assignment__teacher", "assignment__subject", "assignment__group", "period"
    ).all()
    serializer_class = TeacherAcademicProcessSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["assignment", "period", "is_closed"]
    export_filename = "procesos_docente"

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("mine") == "1":
            teacher = getattr(self.request.user, "teacher_profile", None)
            queryset = queryset.filter(assignment__teacher=teacher) if teacher else queryset.none()
        return queryset


class TeacherAbsenceViewSet(BaseModelViewSet):
    module_code = "teachers.registry"
    queryset = TeacherAbsence.objects.select_related("teacher", "substitute").all()
    serializer_class = TeacherAbsenceSerializer
    filterset_fields = ["teacher", "kind", "approved"]
    search_fields = ["teacher__first_name", "teacher__last_name", "reason"]
    approve_field = "approved"
    export_filename = "novedades_docentes"


ROUTES = [
    ("teachers", TeacherViewSet, "teacher"),
    ("teaching-assignments", TeachingAssignmentViewSet, "teachingassignment"),
    ("schedule-slots", ScheduleSlotViewSet, "scheduleslot"),
    ("teacher-processes", TeacherAcademicProcessViewSet, "teacheracademicprocess"),
    ("teacher-absences", TeacherAbsenceViewSet, "teacherabsence"),
]
