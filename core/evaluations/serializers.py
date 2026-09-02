"""Serializers del modulo de evaluaciones."""
from rest_framework import serializers

from .models import (
    AreaGrade,
    BilingualEvaluation,
    GradeSheetLock,
    ProcessGrade,
    PurposeEvaluation,
    QualitativeEvaluation,
    StudentJudgment,
    SubjectGrade,
)


class ProcessGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)
    subject_name = serializers.CharField(source="assignment.subject.name", read_only=True)
    group_name = serializers.CharField(source="assignment.group.name", read_only=True)

    class Meta:
        model = ProcessGrade
        fields = [
            "id", "student", "student_name", "assignment", "subject_name", "group_name",
            "process", "process_name", "period", "dimension", "score", "observation",
            "recorded_at", "recorded_by",
        ]
        read_only_fields = ["recorded_at", "recorded_by"]


class SubjectGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    area_name = serializers.CharField(source="subject.area.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    performance_name = serializers.CharField(source="performance.name", read_only=True)
    performance_color = serializers.CharField(source="performance.color", read_only=True)

    class Meta:
        model = SubjectGrade
        fields = [
            "id", "student", "student_name", "student_document", "enrollment", "school_year",
            "period", "period_name", "subject", "subject_name", "area_name", "group", "group_name",
            "teacher", "teacher_name", "score", "recovered_score", "final_score",
            "performance", "performance_name", "performance_color", "absences",
            "status", "is_passing", "observation", "published_at",
        ]
        read_only_fields = ["final_score", "performance", "is_passing"]


class AreaGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    performance_name = serializers.CharField(source="performance.name", read_only=True)

    class Meta:
        model = AreaGrade
        fields = [
            "id", "student", "student_name", "school_year", "period", "period_name",
            "area", "area_name", "score", "performance", "performance_name", "is_passing",
        ]
        read_only_fields = fields


class StudentJudgmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    text = serializers.CharField(read_only=True)

    class Meta:
        model = StudentJudgment
        fields = [
            "id", "student", "student_name", "period", "period_name", "subject", "subject_name",
            "judgment", "custom_text", "text", "judgment_type", "teacher",
        ]


class QualitativeEvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    dimension_name = serializers.CharField(source="dimension.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    performance_name = serializers.CharField(source="performance.name", read_only=True)

    class Meta:
        model = QualitativeEvaluation
        fields = [
            "id", "student", "student_name", "period", "period_name", "subject", "subject_name",
            "dimension", "dimension_name", "performance", "performance_name", "description",
            "strengths", "difficulties", "recommendations", "teacher",
        ]


class PurposeEvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    purpose_text = serializers.CharField(source="purpose.text", read_only=True)
    dimension_name = serializers.CharField(source="purpose.dimension.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    achievement_display = serializers.CharField(source="get_achievement_display", read_only=True)

    class Meta:
        model = PurposeEvaluation
        fields = [
            "id", "student", "student_name", "purpose", "purpose_text", "dimension_name",
            "period", "period_name", "achievement", "achievement_display", "observation", "teacher",
        ]


class BilingualEvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    level_display = serializers.CharField(source="get_cefr_level_display", read_only=True)

    class Meta:
        model = BilingualEvaluation
        fields = [
            "id", "student", "student_name", "period", "period_name", "subject", "subject_name",
            "listening", "speaking", "reading", "writing", "grammar", "average",
            "cefr_level", "level_display", "comments", "teacher",
        ]
        read_only_fields = ["average"]


class GradeSheetLockSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    locked_by_name = serializers.CharField(source="locked_by.get_full_name", read_only=True)

    class Meta:
        model = GradeSheetLock
        fields = [
            "id", "period", "period_name", "group", "group_name", "subject", "subject_name",
            "locked", "reason", "locked_by", "locked_by_name", "created_at",
        ]
        read_only_fields = ["locked_by"]


class GradeSheetEntrySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    process_id = serializers.IntegerField()
    score = serializers.CharField(allow_blank=True, allow_null=True)


class GradeSheetSaveSerializer(serializers.Serializer):
    assignment = serializers.IntegerField()
    period = serializers.IntegerField()
    entries = GradeSheetEntrySerializer(many=True)
