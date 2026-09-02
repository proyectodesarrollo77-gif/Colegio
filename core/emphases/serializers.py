"""Serializers de enfasis y disciplinas."""
from rest_framework import serializers

from .models import Emphasis, EmphasisEnrollment, EmphasisGroup


class EmphasisSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    groups_count = serializers.IntegerField(source="groups.count", read_only=True)

    class Meta:
        model = Emphasis
        fields = [
            "id", "institution", "code", "name", "description", "kind", "kind_display",
            "image", "color", "requirements", "order", "is_active", "groups_count",
        ]


class EmphasisGroupSerializer(serializers.ModelSerializer):
    emphasis_name = serializers.CharField(source="emphasis.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    grades_display = serializers.SerializerMethodField()

    class Meta:
        model = EmphasisGroup
        fields = [
            "id", "emphasis", "emphasis_name", "school_year", "school_year_name", "code", "name",
            "teacher", "teacher_name", "grades", "grades_display", "capacity", "weekday",
            "start_time", "end_time", "place", "status", "status_display",
            "enrolled_count", "available_seats", "is_active",
        ]

    def get_grades_display(self, obj):
        return ", ".join(obj.grades.values_list("name", flat=True)[:6])


class EmphasisEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    emphasis_name = serializers.CharField(source="group.emphasis.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EmphasisEnrollment
        fields = [
            "id", "group", "group_name", "emphasis_name", "student", "student_name",
            "student_document", "enrolled_at", "status", "status_display",
            "priority", "score", "observation",
        ]

    def validate(self, attrs):
        group = attrs.get("group") or getattr(self.instance, "group", None)
        if group and self.instance is None and group.available_seats <= 0:
            raise serializers.ValidationError({"group": "El grupo de enfasis no tiene cupos disponibles."})
        return attrs
