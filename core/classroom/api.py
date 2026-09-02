"""API REST del aula virtual."""
from __future__ import annotations

from django.db.models import Avg
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import ActivitySubmission, Course, CourseActivity, CourseMaterial, CourseProgress, CourseUnit
from .serializers import (
    ActivitySubmissionSerializer,
    CourseActivitySerializer,
    CourseMaterialSerializer,
    CourseProgressSerializer,
    CourseSerializer,
    CourseUnitSerializer,
)


class CourseViewSet(BaseModelViewSet):
    module_code = "classroom.courses"
    queryset = Course.objects.select_related("subject", "group", "teacher", "school_year").all()
    serializer_class = CourseSerializer
    search_fields = ["title", "summary", "subject__name"]
    filterset_fields = ["school_year", "subject", "group", "teacher", "status"]
    export_filename = "cursos"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role_code == "DOCENTE":
            teacher = getattr(user, "teacher_profile", None)
            if teacher:
                queryset = queryset.filter(teacher=teacher)
        elif user.role_code == "ESTUDIANTE":
            student = getattr(user, "student_profile", None)
            group = student.current_group if student else None
            queryset = queryset.filter(group=group, status="PUBLICADO") if group else queryset.none()
        return queryset

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        course = self.get_object()
        course.status = "PUBLICADO"
        course.save(update_fields=["status"])
        return Response({"success": True})

    @action(detail=True, methods=["get"], url_path="detail")
    def course_detail(self, request, pk=None):
        course = self.get_object()
        return Response(
            {
                "course": CourseSerializer(course).data,
                "units": CourseUnitSerializer(course.units.all(), many=True).data,
                "materials": CourseMaterialSerializer(course.materials.all(), many=True).data,
                "activities": CourseActivitySerializer(course.activities.all(), many=True).data,
            }
        )


class CourseUnitViewSet(BaseModelViewSet):
    module_code = "classroom.courses"
    queryset = CourseUnit.objects.select_related("course", "period").all()
    serializer_class = CourseUnitSerializer
    filterset_fields = ["course", "period", "is_published"]
    search_fields = ["title", "description"]
    export_filename = "unidades_curso"


class CourseMaterialViewSet(BaseModelViewSet):
    module_code = "classroom.materials"
    queryset = CourseMaterial.objects.select_related("course", "unit").all()
    serializer_class = CourseMaterialSerializer
    filterset_fields = ["course", "unit", "kind"]
    search_fields = ["title", "description"]
    export_filename = "material_academico"

    @action(detail=True, methods=["post"], url_path="register-download")
    def register_download(self, request, pk=None):
        material = self.get_object()
        material.downloads += 1
        material.save(update_fields=["downloads"])
        return Response({"success": True, "downloads": material.downloads})


class CourseActivityViewSet(BaseModelViewSet):
    module_code = "classroom.activities"
    queryset = CourseActivity.objects.select_related("course", "course__group", "unit", "period").all()
    serializer_class = CourseActivitySerializer
    filterset_fields = ["course", "unit", "period", "kind", "status"]
    search_fields = ["title", "instructions"]
    export_filename = "actividades_aula"

    @action(detail=True, methods=["post"], url_path="open-submissions")
    def open_submissions(self, request, pk=None):
        """Publica la actividad y crea las entregas pendientes de cada estudiante."""
        activity = self.get_object()
        activity.status = "PUBLICADA"
        activity.save(update_fields=["status"])
        created = 0
        for enrollment in activity.course.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True):
            _, was_created = ActivitySubmission.objects.get_or_create(
                activity=activity, student=enrollment.student, defaults={"created_by": request.user}
            )
            created += int(was_created)
        return Response({"success": True, "submissions": created})

    @action(detail=True, methods=["get"], url_path="submissions")
    def submissions(self, request, pk=None):
        activity = self.get_object()
        queryset = activity.submissions.select_related("student").order_by("student__last_name")
        return Response({"results": ActivitySubmissionSerializer(queryset, many=True).data})


class ActivitySubmissionViewSet(BaseModelViewSet):
    module_code = "classroom.activities"
    queryset = ActivitySubmission.objects.select_related("activity", "student", "graded_by").all()
    serializer_class = ActivitySubmissionSerializer
    filterset_fields = ["activity", "student", "status"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "entregas_aula"

    def get_queryset(self):
        queryset = super().get_queryset()
        student = getattr(self.request.user, "student_profile", None)
        if student and self.request.user.role_code == "ESTUDIANTE":
            queryset = queryset.filter(student=student)
        return queryset

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        submission = self.get_object()
        submission.content = request.data.get("content", submission.content)
        submission.submit()
        return Response({"success": True, "status": submission.status})

    @action(detail=True, methods=["post"], url_path="grade")
    def grade(self, request, pk=None):
        submission = self.get_object()
        submission.score = request.data.get("score")
        submission.feedback = request.data.get("feedback", "")
        submission.status = "CALIFICADA"
        submission.graded_at = timezone.now()
        submission.graded_by = request.user
        submission.save()
        update_progress(submission.activity.course, submission.student)
        self.log_action("UPDATE", submission)
        return Response({"success": True})


def update_progress(course, student):
    """Recalcula el avance del estudiante dentro del curso."""
    total = course.activities.filter(status__in=["PUBLICADA", "CERRADA", "CALIFICADA"]).count()
    submissions = ActivitySubmission.objects.filter(activity__course=course, student=student)
    done = submissions.exclude(status__in=["PENDIENTE", "NO_ENTREGADA"]).count()
    average = submissions.aggregate(value=Avg("score"))["value"] or 0
    CourseProgress.objects.update_or_create(
        course=course,
        student=student,
        defaults={
            "activities_total": total,
            "activities_done": done,
            "average_score": round(float(average), 2),
            "last_access": timezone.now(),
        },
    )


class CourseProgressViewSet(BaseModelViewSet):
    module_code = "classroom.tracking"
    queryset = CourseProgress.objects.select_related("course", "student").all()
    serializer_class = CourseProgressSerializer
    filterset_fields = ["course", "student"]
    search_fields = ["student__first_name", "student__last_name"]
    export_filename = "seguimiento_aula"

    @action(detail=False, methods=["post"], url_path="rebuild")
    def rebuild(self, request):
        course = Course.objects.filter(pk=request.data.get("course")).first()
        if course is None:
            return Response({"detail": "Curso invalido."}, status=400)
        processed = 0
        for enrollment in course.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True):
            update_progress(course, enrollment.student)
            processed += 1
        return Response({"success": True, "processed": processed})


ROUTES = [
    ("courses", CourseViewSet, "course"),
    ("course-units", CourseUnitViewSet, "courseunit"),
    ("course-materials", CourseMaterialViewSet, "coursematerial"),
    ("course-activities", CourseActivityViewSet, "courseactivity"),
    ("activity-submissions", ActivitySubmissionViewSet, "activitysubmission"),
    ("course-progress", CourseProgressViewSet, "courseprogress"),
]
