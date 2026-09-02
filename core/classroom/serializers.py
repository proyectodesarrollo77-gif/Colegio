"""Serializers del aula virtual."""
from rest_framework import serializers

from .models import ActivitySubmission, Course, CourseActivity, CourseMaterial, CourseProgress, CourseUnit


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    materials_count = serializers.IntegerField(source="materials.count", read_only=True)
    activities_count = serializers.IntegerField(source="activities.count", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "school_year", "assignment", "subject", "subject_name", "group", "group_name",
            "teacher", "teacher_name", "title", "summary", "cover", "color",
            "status", "status_display", "allow_submissions",
            "materials_count", "activities_count", "is_active",
        ]


class CourseUnitSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseUnit
        fields = ["id", "course", "course_title", "period", "title", "description", "order", "is_published"]


class CourseMaterialSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    unit_title = serializers.CharField(source="unit.title", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = CourseMaterial
        fields = [
            "id", "course", "course_title", "unit", "unit_title", "title", "description",
            "kind", "kind_display", "file", "url", "published_at", "downloads", "order",
        ]
        read_only_fields = ["downloads"]


class CourseActivitySerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    group_name = serializers.CharField(source="course.group.name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    submissions_count = serializers.IntegerField(source="submissions.count", read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseActivity
        fields = [
            "id", "course", "course_title", "group_name", "unit", "period", "process",
            "title", "instructions", "kind", "kind_display", "attachment", "max_score",
            "weight", "opens_at", "due_at", "allow_late", "status", "status_display",
            "submissions_count", "is_open",
        ]


class ActivitySubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    activity_title = serializers.CharField(source="activity.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    max_score = serializers.DecimalField(source="activity.max_score", max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = ActivitySubmission
        fields = [
            "id", "activity", "activity_title", "student", "student_name", "content", "file",
            "submitted_at", "status", "status_display", "score", "max_score",
            "feedback", "graded_at", "graded_by",
        ]
        read_only_fields = ["graded_at", "graded_by"]


class CourseProgressSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    completion = serializers.IntegerField(read_only=True)

    class Meta:
        model = CourseProgress
        fields = [
            "id", "course", "course_title", "student", "student_name",
            "activities_total", "activities_done", "average_score", "completion", "last_access",
        ]
        read_only_fields = fields
