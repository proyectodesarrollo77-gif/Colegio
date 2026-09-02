"""Serializers del modulo de asistencia."""
from rest_framework import serializers

from .models import AttendanceRecord, AttendanceSession, AttendanceSummary


class AttendanceSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="assignment.teacher.full_name", read_only=True)
    subject_name = serializers.CharField(source="assignment.subject.name", read_only=True)
    group_name = serializers.CharField(source="assignment.group.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    summary = serializers.DictField(read_only=True)
    records_count = serializers.IntegerField(source="records.count", read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id", "assignment", "teacher_name", "subject_name", "group_name",
            "period", "period_name", "date", "block", "topic", "is_closed",
            "taken_by", "summary", "records_count", "created_at",
        ]
        read_only_fields = ["taken_by"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    date = serializers.DateField(source="session.date", read_only=True)
    subject_name = serializers.CharField(source="session.assignment.subject.name", read_only=True)
    group_name = serializers.CharField(source="session.assignment.group.name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "session", "date", "subject_name", "group_name", "student", "student_name",
            "student_document", "status", "status_display", "minutes_late",
            "excuse_document", "observation",
        ]


class AttendanceSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = AttendanceSummary
        fields = [
            "id", "student", "student_name", "period", "period_name", "subject", "subject_name",
            "total_sessions", "absences", "justified", "late_arrivals", "attendance_rate",
        ]
        read_only_fields = fields


class AttendanceSheetEntrySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[c[0] for c in AttendanceRecord.STATUS_CHOICES])
    minutes_late = serializers.IntegerField(required=False, default=0)
    observation = serializers.CharField(required=False, allow_blank=True, default="")


class AttendanceSheetSaveSerializer(serializers.Serializer):
    assignment = serializers.IntegerField()
    period = serializers.IntegerField()
    date = serializers.DateField()
    block = serializers.IntegerField(required=False, default=1)
    topic = serializers.CharField(required=False, allow_blank=True, default="")
    entries = AttendanceSheetEntrySerializer(many=True)
