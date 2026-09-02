"""Serializers del modulo de recuperaciones."""
from rest_framework import serializers

from .models import RecoveryActivity, RecoveryActivitySubmission, RecoveryEnrollment, RecoveryPlan


class RecoveryPlanSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    type_display = serializers.CharField(source="get_plan_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    enrolled_count = serializers.IntegerField(source="enrollments.count", read_only=True)
    activities_count = serializers.IntegerField(source="activities.count", read_only=True)

    class Meta:
        model = RecoveryPlan
        fields = [
            "id", "school_year", "period", "period_name", "subject", "subject_name",
            "group", "group_name", "teacher", "teacher_name", "plan_type", "type_display",
            "name", "description", "objectives", "start_date", "end_date", "evaluation_date",
            "maximum_score", "status", "status_display", "is_bilingual",
            "enrolled_count", "activities_count", "is_active",
        ]


class RecoveryActivitySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = RecoveryActivity
        fields = ["id", "plan", "plan_name", "name", "description", "weight", "due_date", "resource", "order"]


class RecoveryEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    subject_name = serializers.CharField(source="plan.subject.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RecoveryEnrollment
        fields = [
            "id", "plan", "plan_name", "subject_name", "student", "student_name", "student_document",
            "previous_score", "score", "final_score", "status", "status_display",
            "observation", "evaluated_at", "evaluated_by", "applied_to_grade",
        ]
        read_only_fields = ["final_score", "evaluated_at", "evaluated_by", "applied_to_grade"]


class RecoverySubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrollment.student.full_name", read_only=True)
    activity_name = serializers.CharField(source="activity.name", read_only=True)

    class Meta:
        model = RecoveryActivitySubmission
        fields = [
            "id", "activity", "activity_name", "enrollment", "student_name",
            "submitted_at", "file", "comments", "score", "feedback",
        ]
