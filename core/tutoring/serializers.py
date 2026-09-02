"""Serializers del modulo de tutoria."""
from rest_framework import serializers

from .models import CoexistenceEvaluation, ReportCardBlock, Tutor, TutoringJudgment, TutoringMeeting


class TutorSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    grade_name = serializers.CharField(source="group.grade.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Tutor
        fields = [
            "id", "school_year", "school_year_name", "teacher", "teacher_name",
            "group", "group_name", "grade_name", "start_date", "end_date",
            "is_main", "notes", "is_active", "students_count",
        ]

    def get_students_count(self, obj):
        return obj.group.enrolled_count


class TutoringJudgmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    tutor_name = serializers.CharField(source="tutor.teacher.full_name", read_only=True)
    performance_name = serializers.CharField(source="performance.name", read_only=True)

    class Meta:
        model = TutoringJudgment
        fields = [
            "id", "student", "student_name", "student_document", "period", "period_name",
            "tutor", "tutor_name", "performance", "performance_name", "strengths",
            "difficulties", "recommendations", "commitment", "published",
        ]


class CoexistenceEvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_type = serializers.CharField(source="item.get_item_type_display", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    performance_name = serializers.CharField(source="performance.name", read_only=True)

    class Meta:
        model = CoexistenceEvaluation
        fields = [
            "id", "student", "student_name", "period", "period_name", "item", "item_name",
            "item_type", "score", "performance", "performance_name", "observation", "evaluated_by",
        ]
        # El desempeno lo deriva el modelo a partir de la valoracion.
        read_only_fields = ["evaluated_by", "performance"]


class ReportCardBlockSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    released_by_name = serializers.CharField(source="released_by.get_full_name", read_only=True)

    class Meta:
        model = ReportCardBlock
        fields = [
            "id", "student", "student_name", "student_document", "school_year",
            "period", "period_name", "reason", "reason_display", "detail", "amount",
            "blocked", "released_at", "released_by", "released_by_name", "created_at",
        ]
        read_only_fields = ["released_at", "released_by"]


class TutoringMeetingSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    tutor_name = serializers.CharField(source="tutor.teacher.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TutoringMeeting
        fields = [
            "id", "student", "student_name", "tutor", "tutor_name", "scheduled_at",
            "place", "subject", "agreements", "status", "status_display", "guardian_attended",
        ]
