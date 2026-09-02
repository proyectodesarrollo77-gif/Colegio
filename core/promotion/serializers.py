"""Serializers de promocion y boletines."""
from rest_framework import serializers

from .models import ClosingProcess, EvaluationCommission, FinalReportCard, PromotionResult


class ClosingProcessSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    executed_by_name = serializers.CharField(source="executed_by.get_full_name", read_only=True)

    class Meta:
        model = ClosingProcess
        fields = [
            "id", "school_year", "school_year_name", "period", "period_name", "scope", "scope_display",
            "status", "status_display", "started_at", "finished_at", "processed_students",
            "processed_grades", "log", "executed_by", "executed_by_name", "created_at",
        ]
        read_only_fields = ["started_at", "finished_at", "processed_students", "processed_grades", "log", "executed_by"]


class PromotionResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    grade_name = serializers.CharField(source="group.grade.name", read_only=True)
    next_grade_name = serializers.CharField(source="next_grade.name", read_only=True)
    result_display = serializers.CharField(source="get_result_display", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)

    class Meta:
        model = PromotionResult
        fields = [
            "id", "student", "student_name", "student_document", "school_year", "school_year_name",
            "group", "group_name", "grade_name", "next_grade", "next_grade_name",
            "average", "failed_subjects", "failed_areas", "absences", "result", "result_display",
            "rank", "honor_roll", "observations", "approved", "approved_by", "approved_at",
        ]
        read_only_fields = ["approved_by", "approved_at"]


class FinalReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)

    class Meta:
        model = FinalReportCard
        fields = [
            "id", "student", "student_name", "student_document", "school_year", "school_year_name",
            "period", "period_name", "group", "group_name", "is_final", "average", "rank",
            "total_absences", "tutor_observation", "generated_at", "generated_by",
            "published", "file", "snapshot",
        ]
        read_only_fields = ["generated_at", "generated_by", "snapshot"]


class EvaluationCommissionSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = EvaluationCommission
        fields = [
            "id", "school_year", "school_year_name", "period", "period_name", "group", "group_name",
            "act_number", "date", "place", "attendees", "agenda", "decisions", "commitments", "closed",
        ]
