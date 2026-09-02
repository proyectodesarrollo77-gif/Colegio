"""Serializers del modulo docente."""
from rest_framework import serializers

from .models import ScheduleSlot, Teacher, TeacherAbsence, TeacherAcademicProcess, TeachingAssignment


class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    assigned_hours = serializers.IntegerField(read_only=True)
    load_percentage = serializers.IntegerField(read_only=True)
    contract_display = serializers.CharField(source="get_contract_type_display", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = [
            "id", "uuid", "user", "user_email", "institution", "campus", "campus_name",
            "teacher_code", "document_type", "document_number", "first_name", "last_name",
            "full_name", "gender", "birth_date", "photo", "email", "personal_email",
            "phone", "mobile", "address", "profession", "academic_title", "specialization",
            "escalafon", "contract_type", "contract_display", "hire_date", "end_date",
            "weekly_hours", "assigned_hours", "load_percentage", "status",
            "is_tutor", "is_coordinator", "signature", "observations", "is_active",
        ]
        read_only_fields = ["uuid", "teacher_code"]


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    area_name = serializers.CharField(source="subject.area.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    grade_name = serializers.CharField(source="group.grade.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = [
            "id", "school_year", "school_year_name", "teacher", "teacher_name",
            "subject", "subject_name", "area_name", "group", "group_name", "grade_name",
            "weekly_hours", "is_main", "notes", "is_active",
        ]

    def validate(self, attrs):
        teacher = attrs.get("teacher") or getattr(self.instance, "teacher", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        group = attrs.get("group") or getattr(self.instance, "group", None)
        year = attrs.get("school_year") or getattr(self.instance, "school_year", None)
        if teacher and subject and group and year:
            queryset = TeachingAssignment.objects.filter(
                teacher=teacher, subject=subject, group=group, school_year=year, deleted_at__isnull=True
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"subject": "Esta asignacion ya existe para el docente."})
        return attrs


class ScheduleSlotSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="assignment.teacher.full_name", read_only=True)
    subject_name = serializers.CharField(source="assignment.subject.name", read_only=True)
    group_name = serializers.CharField(source="assignment.group.name", read_only=True)
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = ScheduleSlot
        fields = [
            "id", "assignment", "teacher_name", "subject_name", "group_name",
            "weekday", "weekday_display", "block", "start_time", "end_time", "classroom", "is_active",
        ]

    def validate(self, attrs):
        assignment = attrs.get("assignment") or getattr(self.instance, "assignment", None)
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "La hora final debe ser posterior a la inicial."})
        if assignment and weekday and start and end:
            conflicts = ScheduleSlot.objects.filter(
                assignment__teacher=assignment.teacher,
                weekday=weekday,
                deleted_at__isnull=True,
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise serializers.ValidationError(
                    {"start_time": "El docente ya tiene una clase asignada en ese horario."}
                )
        return attrs


class TeacherAcademicProcessSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="assignment.teacher.full_name", read_only=True)
    subject_name = serializers.CharField(source="assignment.subject.name", read_only=True)
    group_name = serializers.CharField(source="assignment.group.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = TeacherAcademicProcess
        fields = [
            "id", "assignment", "teacher_name", "subject_name", "group_name",
            "period", "period_name", "process", "name", "description",
            "weight", "due_date", "is_closed", "order", "is_active",
        ]


class TeacherAbsenceSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    substitute_name = serializers.CharField(source="substitute.full_name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = TeacherAbsence
        fields = [
            "id", "teacher", "teacher_name", "kind", "kind_display", "start_date", "end_date",
            "reason", "substitute", "substitute_name", "approved", "approved_by", "approved_at",
        ]
        read_only_fields = ["approved_by", "approved_at"]
