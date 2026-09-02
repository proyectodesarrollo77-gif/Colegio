"""Serializers de la Directiva Academica."""
from __future__ import annotations

from rest_framework import serializers

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


class SchoolYearSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    progress = serializers.IntegerField(read_only=True)
    periods_count = serializers.IntegerField(source="periods.count", read_only=True)

    class Meta:
        model = SchoolYear
        fields = [
            "id", "institution", "institution_name", "year", "name", "start_date", "end_date",
            "status", "status_display", "is_current", "weeks", "enrollment_open", "grades_locked",
            "is_active", "progress", "periods_count", "created_at",
        ]


class AcademicPeriodSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    is_open_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = AcademicPeriod
        fields = [
            "id", "school_year", "school_year_name", "number", "name", "short_name",
            "start_date", "end_date", "weight", "is_current", "is_recovery",
            "grades_open", "grades_open_from", "grades_open_to", "report_published",
            "is_open_now", "is_active",
        ]


class GradingScaleLevelSerializer(serializers.ModelSerializer):
    scale_name = serializers.CharField(source="scale.name", read_only=True)

    class Meta:
        model = GradingScaleLevel
        fields = [
            "id", "scale", "scale_name", "code", "name", "national_equivalent",
            "minimum", "maximum", "color", "is_passing", "order", "is_active",
        ]


class GradingScaleSerializer(serializers.ModelSerializer):
    levels = GradingScaleLevelSerializer(many=True, read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    scale_type_display = serializers.CharField(source="get_scale_type_display", read_only=True)

    class Meta:
        model = GradingScale
        fields = [
            "id", "school_year", "school_year_name", "name", "scale_type", "scale_type_display",
            "minimum", "maximum", "passing", "decimals", "is_default",
            "applies_to_preschool", "is_active", "levels",
        ]


class ValuationDimensionSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)

    class Meta:
        model = ValuationDimension
        fields = [
            "id", "school_year", "school_year_name", "code", "name", "description",
            "weight", "applies_to_all", "order", "is_active",
        ]


class EducationLevelSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    grades_count = serializers.IntegerField(source="grades.count", read_only=True)

    class Meta:
        model = EducationLevel
        fields = [
            "id", "institution", "institution_name", "code", "name", "description",
            "is_preschool", "evaluation_type", "order", "is_active", "grades_count",
        ]


class GradeSerializer(serializers.ModelSerializer):
    level_name = serializers.CharField(source="level.name", read_only=True)
    groups_count = serializers.IntegerField(source="groups.count", read_only=True)

    class Meta:
        model = Grade
        fields = [
            "id", "level", "level_name", "code", "name", "description", "numeric_value",
            "next_grade", "minimum_age", "maximum_age", "is_graduation", "order",
            "is_active", "groups_count",
        ]


class GroupSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    level_name = serializers.CharField(source="grade.level.name", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    director_name = serializers.CharField(source="director.full_name", read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    occupancy = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id", "school_year", "grade", "grade_name", "level_name", "campus", "campus_name",
            "shift", "shift_name", "code", "name", "capacity", "classroom", "director",
            "director_name", "order", "is_active", "enrolled_count", "available_seats", "occupancy",
        ]


class AreaSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    subjects_count = serializers.IntegerField(source="subjects.count", read_only=True)

    class Meta:
        model = Area
        fields = [
            "id", "school_year", "school_year_name", "code", "name", "description",
            "weight", "is_mandatory", "color", "average_by_intensity", "order",
            "is_active", "subjects_count",
        ]


class SubjectSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    grades_display = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id", "area", "area_name", "code", "name", "description", "grades", "grades_display",
            "weekly_hours", "weight", "is_bilingual", "affects_promotion", "allows_recovery",
            "evaluation_type", "order", "is_active",
        ]

    def get_grades_display(self, obj):
        return ", ".join(obj.grades.values_list("name", flat=True)[:6])


class AcademicProcessSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    dimension_name = serializers.CharField(source="dimension.name", read_only=True)

    class Meta:
        model = AcademicProcess
        fields = [
            "id", "school_year", "period", "period_name", "subject", "subject_name",
            "dimension", "dimension_name", "code", "name", "description", "weight",
            "order", "applies_to_all_subjects", "is_active",
        ]


class ValueJudgmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    type_display = serializers.CharField(source="get_judgment_type_display", read_only=True)
    performance_name = serializers.CharField(source="performance_level.name", read_only=True)

    class Meta:
        model = ValueJudgment
        fields = [
            "id", "school_year", "subject", "subject_name", "grade", "grade_name",
            "period", "period_name", "performance_level", "performance_name",
            "judgment_type", "type_display", "code", "text", "order", "is_active",
        ]


class CoexistenceItemSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_item_type_display", read_only=True)

    class Meta:
        model = CoexistenceItem
        fields = [
            "id", "school_year", "code", "name", "item_type", "type_display",
            "description", "weight", "affects_report", "order", "is_active",
        ]


class PurposeSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    dimension_name = serializers.CharField(source="dimension.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = Purpose
        fields = [
            "id", "school_year", "grade", "grade_name", "dimension", "dimension_name",
            "period", "period_name", "code", "text", "order", "is_active",
        ]
