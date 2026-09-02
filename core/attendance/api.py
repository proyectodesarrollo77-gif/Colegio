"""API REST del modulo de asistencia."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import HasModulePermission
from config.viewsets import BaseModelViewSet
from core.academic.models import AcademicPeriod
from core.teachers.models import TeachingAssignment

from .models import AttendanceRecord, AttendanceSession, AttendanceSummary
from .serializers import (
    AttendanceRecordSerializer,
    AttendanceSessionSerializer,
    AttendanceSheetSaveSerializer,
    AttendanceSummarySerializer,
)


class AttendanceSessionViewSet(BaseModelViewSet):
    module_code = "attendance.register"
    queryset = AttendanceSession.objects.select_related(
        "assignment", "assignment__teacher", "assignment__subject", "assignment__group", "period"
    ).all()
    serializer_class = AttendanceSessionSerializer
    filterset_fields = ["assignment", "period", "date", "is_closed"]
    search_fields = ["topic", "assignment__subject__name"]
    ordering = ["-date"]
    export_filename = "sesiones_asistencia"

    def perform_create(self, serializer):
        return serializer.save(taken_by=self.request.user, created_by=self.request.user)


class AttendanceRecordViewSet(BaseModelViewSet):
    module_code = "attendance.register"
    queryset = AttendanceRecord.objects.select_related(
        "session", "session__assignment", "session__assignment__subject", "student"
    ).all()
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ["session", "student", "status"]
    search_fields = ["student__first_name", "student__last_name", "student__document_number"]
    export_filename = "registros_asistencia"
    export_fields = (
        "session__date", "session__assignment__subject__name", "session__assignment__group__name",
        "student__document_number", "student__last_name", "student__first_name", "status", "observation",
    )


class AttendanceSummaryViewSet(BaseModelViewSet):
    module_code = "attendance.report"
    queryset = AttendanceSummary.objects.select_related("student", "period", "subject").all()
    serializer_class = AttendanceSummarySerializer
    filterset_fields = ["student", "period", "subject"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "consolidado_asistencia"

    @action(detail=False, methods=["post"], url_path="recalculate")
    def recalculate(self, request):
        period = get_object_or_404(AcademicPeriod, pk=request.data.get("period"))
        created = rebuild_summaries(period)
        return Response({"success": True, "processed": created})


def rebuild_summaries(period):
    """Recalcula el consolidado de inasistencias del periodo."""
    from core.evaluations.models import SubjectGrade

    rows = (
        AttendanceRecord.objects.filter(session__period=period, deleted_at__isnull=True)
        .values("student_id", "session__assignment__subject_id")
        .annotate(
            total=Count("id"),
            absences=Count("id", filter=Q(status="AUSENTE")),
            justified=Count("id", filter=Q(status="EXCUSA")),
            late=Count("id", filter=Q(status="TARDE")),
        )
    )
    processed = 0
    with transaction.atomic():
        for row in rows:
            total = row["total"] or 1
            attended = total - row["absences"]
            AttendanceSummary.objects.update_or_create(
                student_id=row["student_id"],
                period=period,
                subject_id=row["session__assignment__subject_id"],
                defaults={
                    "total_sessions": row["total"],
                    "absences": row["absences"],
                    "justified": row["justified"],
                    "late_arrivals": row["late"],
                    "attendance_rate": round(attended / total * 100, 2),
                },
            )
            SubjectGrade.objects.filter(
                student_id=row["student_id"], period=period, subject_id=row["session__assignment__subject_id"]
            ).update(absences=row["absences"])
            processed += 1
    return processed


class AttendanceSheetAPIView(APIView):
    """Planilla diaria de asistencia."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "attendance.register"

    def get(self, request):
        assignment = get_object_or_404(TeachingAssignment, pk=request.query_params.get("assignment"))
        period = get_object_or_404(AcademicPeriod, pk=request.query_params.get("period"))
        date = request.query_params.get("date")
        block = int(request.query_params.get("block", 1))

        session = AttendanceSession.objects.filter(
            assignment=assignment, date=date, block=block, deleted_at__isnull=True
        ).first()
        existing = (
            {record.student_id: record for record in session.records.all()} if session else {}
        )
        enrollments = (
            assignment.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True)
            .select_related("student")
            .order_by("student__last_name", "student__first_name")
        )
        students = []
        for enrollment in enrollments:
            record = existing.get(enrollment.student_id)
            students.append(
                {
                    "student_id": enrollment.student_id,
                    "student": enrollment.student.full_name,
                    "document": enrollment.student.document_number,
                    "status": record.status if record else "PRESENTE",
                    "minutes_late": record.minutes_late if record else 0,
                    "observation": record.observation if record else "",
                }
            )
        return Response(
            {
                "assignment": {
                    "id": assignment.id,
                    "subject": assignment.subject.name,
                    "group": assignment.group.name,
                    "teacher": assignment.teacher.full_name,
                },
                "session": AttendanceSessionSerializer(session).data if session else None,
                "date": date,
                "block": block,
                "students": students,
                "statuses": [{"value": v, "label": label} for v, label in AttendanceRecord.STATUS_CHOICES],
            }
        )

    @transaction.atomic
    def post(self, request):
        self.required_action = "create"
        serializer = AttendanceSheetSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assignment = get_object_or_404(TeachingAssignment, pk=data["assignment"])
        period = get_object_or_404(AcademicPeriod, pk=data["period"])

        session, _ = AttendanceSession.objects.update_or_create(
            assignment=assignment,
            date=data["date"],
            block=data.get("block", 1),
            defaults={
                "period": period,
                "topic": data.get("topic", ""),
                "taken_by": request.user,
                "updated_by": request.user,
            },
        )

        saved = 0
        for entry in data["entries"]:
            AttendanceRecord.objects.update_or_create(
                session=session,
                student_id=entry["student_id"],
                defaults={
                    "status": entry["status"],
                    "minutes_late": entry.get("minutes_late", 0),
                    "observation": entry.get("observation", ""),
                    "updated_by": request.user,
                },
            )
            saved += 1

        rebuild_summaries(period)

        from core.audit.services import register_audit

        register_audit(
            user=request.user,
            action="CREATE",
            module=self.module_code,
            instance=session,
            request=request,
            description=f"Asistencia registrada: {saved} estudiantes",
        )
        return Response({"success": True, "saved": saved, "session": AttendanceSessionSerializer(session).data})


ROUTES = [
    ("attendance-sessions", AttendanceSessionViewSet, "attendancesession"),
    ("attendance-records", AttendanceRecordViewSet, "attendancerecord"),
    ("attendance-summaries", AttendanceSummaryViewSet, "attendancesummary"),
]
