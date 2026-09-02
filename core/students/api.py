"""API REST del modulo de estudiantes."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import (
    Admission,
    Enrollment,
    Guardian,
    Inscription,
    Student,
    StudentCertificate,
    StudentDocument,
    StudentGuardian,
)
from .serializers import (
    AdmissionSerializer,
    EnrollmentSerializer,
    GuardianSerializer,
    InscriptionSerializer,
    StudentCertificateSerializer,
    StudentDocumentSerializer,
    StudentGuardianSerializer,
    StudentListSerializer,
    StudentSerializer,
)
from .services import build_certificate_content


class GuardianViewSet(BaseModelViewSet):
    module_code = "students.guardians"
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer
    search_fields = ["first_name", "last_name", "document_number", "email", "mobile"]
    filterset_fields = ["relation", "is_active"]
    export_filename = "acudientes"


class StudentViewSet(BaseModelViewSet):
    module_code = "students.registry"
    queryset = Student.objects.select_related("institution", "user").all()
    serializer_class = StudentSerializer
    search_fields = ["first_name", "last_name", "document_number", "student_code", "email"]
    filterset_fields = ["status", "gender", "institution", "is_active"]
    ordering = ["last_name", "first_name"]
    export_filename = "estudiantes"
    export_fields = (
        "student_code", "document_type", "document_number", "last_name", "first_name",
        "gender", "birth_date", "email", "mobile", "address", "status",
    )

    def get_serializer_class(self):
        return StudentListSerializer if self.action == "list" else StudentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        group = self.request.query_params.get("group")
        grade = self.request.query_params.get("grade")
        school_year = self.request.query_params.get("school_year")
        if group:
            queryset = queryset.filter(enrollments__group_id=group, enrollments__status="ACTIVA")
        if grade:
            queryset = queryset.filter(enrollments__group__grade_id=grade, enrollments__status="ACTIVA")
        if school_year:
            queryset = queryset.filter(enrollments__school_year_id=school_year)
        return queryset.distinct()

    @action(detail=True, methods=["get"], url_path="resume")
    def resume(self, request, pk=None):
        """Hoja de vida consolidada del estudiante."""
        from core.evaluations.serializers import SubjectGradeSerializer
        from core.observer.serializers import ObserverEntrySerializer

        student = self.get_object()
        enrollments = student.enrollments.select_related("group", "group__grade", "school_year").order_by(
            "-school_year__year"
        )
        return Response(
            {
                "student": StudentSerializer(student, context={"request": request}).data,
                "enrollments": EnrollmentSerializer(enrollments, many=True).data,
                "guardians": StudentGuardianSerializer(student.guardian_links.all(), many=True).data,
                "documents": StudentDocumentSerializer(student.documents.all(), many=True).data,
                "certificates": StudentCertificateSerializer(student.certificates.all()[:20], many=True).data,
                "observer": ObserverEntrySerializer(student.observer_entries.all()[:20], many=True).data,
                "grades": SubjectGradeSerializer(
                    student.subject_grades.select_related("subject", "period")[:60], many=True
                ).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="create-user")
    def create_user(self, request, pk=None):
        from core.users.models import Role, User, UserCredentialCertificate

        student = self.get_object()
        if student.user_id:
            return Response({"detail": "El estudiante ya cuenta con usuario."}, status=status.HTTP_400_BAD_REQUEST)
        role, _ = Role.objects.get_or_create(
            code=Role.ESTUDIANTE, defaults={"name": "Estudiante", "is_system": True, "order": 70}
        )
        password = User.generate_password()
        user = User(
            username=User.build_username(student.first_name, student.last_name, student.document_number),
            email=student.email or f"{student.document_number}@estudiante.local",
            first_name=student.first_name,
            last_name=student.last_name,
            document_type=student.document_type,
            document_number=student.document_number,
            role=role,
            institution=student.institution,
            must_change_password=True,
        )
        user.set_password(password)
        user.save()
        student.user = user
        student.save(update_fields=["user"])
        UserCredentialCertificate.objects.create(user=user, plain_password=password, issued_by=request.user)
        return Response({"success": True, "username": user.username, "password": password})

    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        queryset = self.get_queryset()
        by_status = queryset.values("status").annotate(total=Count("id"))
        by_gender = queryset.values("gender").annotate(total=Count("id"))
        by_grade = (
            Enrollment.objects.filter(status="ACTIVA", deleted_at__isnull=True)
            .values("group__grade__name")
            .annotate(total=Count("id"))
            .order_by("group__grade__order")
        )
        return Response(
            {
                "total": queryset.count(),
                "active": queryset.filter(status="ACTIVO").count(),
                "by_status": list(by_status),
                "by_gender": list(by_gender),
                "by_grade": list(by_grade),
            }
        )


class StudentGuardianViewSet(BaseModelViewSet):
    module_code = "students.registry"
    queryset = StudentGuardian.objects.select_related("student", "guardian").all()
    serializer_class = StudentGuardianSerializer
    filterset_fields = ["student", "guardian", "is_primary"]
    export_filename = "acudientes_estudiantes"


class EnrollmentViewSet(BaseModelViewSet):
    module_code = "students.enrollment"
    queryset = Enrollment.objects.select_related(
        "student", "group", "group__grade", "school_year"
    ).all()
    serializer_class = EnrollmentSerializer
    search_fields = [
        "student__first_name", "student__last_name", "student__document_number", "enrollment_number",
    ]
    filterset_fields = ["school_year", "group", "status", "enrollment_type", "is_repeating"]
    export_filename = "matriculas"
    export_fields = (
        "enrollment_number", "student__document_number", "student__last_name", "student__first_name",
        "group__grade__name", "group__name", "enrollment_date", "enrollment_type", "status",
    )

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.withdraw(reason=request.data.get("reason", ""))
        self.log_action("UPDATE", enrollment)
        return Response({"success": True, "detail": "Matricula retirada."})

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        from core.academic.models import Group

        enrollment = self.get_object()
        group = Group.objects.filter(pk=request.data.get("group")).first()
        if group is None:
            return Response({"detail": "Grupo destino invalido."}, status=status.HTTP_400_BAD_REQUEST)
        if group.available_seats <= 0:
            return Response({"detail": "El grupo destino no tiene cupos."}, status=status.HTTP_400_BAD_REQUEST)
        enrollment.group = group
        enrollment.save(update_fields=["group"])
        self.log_action("UPDATE", enrollment)
        return Response({"success": True, "detail": f"Estudiante trasladado a {group.name}."})

    @action(detail=False, methods=["post"], url_path="bulk-enroll")
    def bulk_enroll(self, request):
        """Matricula masiva de estudiantes en un grupo."""
        from core.academic.models import Group, SchoolYear

        group = Group.objects.filter(pk=request.data.get("group")).first()
        year = SchoolYear.objects.filter(pk=request.data.get("school_year")).first() or SchoolYear.current()
        ids = request.data.get("students") or []
        if group is None or year is None:
            return Response({"detail": "Debe indicar grupo y ano lectivo."}, status=status.HTTP_400_BAD_REQUEST)

        created, skipped = 0, []
        with transaction.atomic():
            for student in Student.objects.filter(pk__in=ids):
                if Enrollment.objects.filter(student=student, school_year=year, deleted_at__isnull=True).exists():
                    skipped.append(student.full_name)
                    continue
                if group.available_seats <= 0:
                    skipped.append(f"{student.full_name} (sin cupo)")
                    continue
                Enrollment.objects.create(
                    student=student, school_year=year, group=group,
                    enrollment_type="ANTIGUO", created_by=request.user,
                )
                created += 1
        return Response({"success": True, "created": created, "skipped": skipped})


class AdmissionViewSet(BaseModelViewSet):
    module_code = "students.admissions"
    queryset = Admission.objects.select_related("grade", "school_year", "student").all()
    serializer_class = AdmissionSerializer
    search_fields = ["applicant_first_name", "applicant_last_name", "applicant_document", "guardian_name"]
    filterset_fields = ["school_year", "grade", "status"]
    approve_field = "status"
    approve_value = "APROBADA"
    export_filename = "admisiones"

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        """Convierte una admision aprobada en estudiante matriculable."""
        from core.institutions.models import Institution

        admission = self.get_object()
        if admission.student_id:
            return Response({"detail": "La admision ya fue convertida."}, status=status.HTTP_400_BAD_REQUEST)
        if admission.status not in ("APROBADA", "MATRICULADA"):
            return Response({"detail": "Solo se convierten admisiones aprobadas."}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.create(
            institution=Institution.current(),
            document_type=admission.applicant_document_type,
            document_number=admission.applicant_document,
            first_name=admission.applicant_first_name,
            last_name=admission.applicant_last_name,
            birth_date=admission.birth_date,
            gender=admission.gender,
            email=admission.guardian_email,
            mobile=admission.guardian_phone,
            previous_school=admission.previous_school,
            entry_date=timezone.localdate(),
            created_by=request.user,
        )
        guardian, _ = Guardian.objects.get_or_create(
            document_number=admission.guardian_document or f"AC{admission.pk}",
            defaults={
                "first_name": admission.guardian_name.split(" ")[0],
                "last_name": " ".join(admission.guardian_name.split(" ")[1:]),
                "email": admission.guardian_email,
                "mobile": admission.guardian_phone,
            },
        )
        StudentGuardian.objects.get_or_create(student=student, guardian=guardian, defaults={"is_primary": True})
        admission.student = student
        admission.status = "MATRICULADA"
        admission.save(update_fields=["student", "status"])
        self.log_action("PROCESS", admission)
        return Response({"success": True, "student": StudentListSerializer(student).data})


class InscriptionViewSet(BaseModelViewSet):
    module_code = "students.inscriptions"
    queryset = Inscription.objects.select_related("grade", "school_year", "admission").all()
    serializer_class = InscriptionSerializer
    search_fields = ["full_name", "document", "guardian_name", "email", "phone"]
    filterset_fields = ["school_year", "grade", "status", "source"]
    export_filename = "inscripciones"

    @action(detail=True, methods=["post"], url_path="to-admission")
    def to_admission(self, request, pk=None):
        inscription = self.get_object()
        if inscription.admission_id:
            return Response({"detail": "Ya existe una admision asociada."}, status=status.HTTP_400_BAD_REQUEST)
        names = inscription.full_name.split(" ")
        admission = Admission.objects.create(
            school_year=inscription.school_year,
            grade=inscription.grade,
            applicant_document=inscription.document or f"PRE{inscription.pk}",
            applicant_first_name=names[0],
            applicant_last_name=" ".join(names[1:]) or names[0],
            birth_date=inscription.birth_date,
            guardian_name=inscription.guardian_name,
            guardian_email=inscription.email,
            guardian_phone=inscription.phone,
            created_by=request.user,
        )
        inscription.admission = admission
        inscription.status = "CONVERTIDA"
        inscription.save(update_fields=["admission", "status"])
        return Response({"success": True, "admission": AdmissionSerializer(admission).data})


class StudentDocumentViewSet(BaseModelViewSet):
    module_code = "students.resume"
    queryset = StudentDocument.objects.select_related("student", "verified_by").all()
    serializer_class = StudentDocumentSerializer
    search_fields = ["name", "student__first_name", "student__last_name"]
    filterset_fields = ["student", "kind", "is_verified"]
    export_filename = "documentos_estudiantes"


class StudentCertificateViewSet(BaseModelViewSet):
    module_code = "students.certificates"
    queryset = StudentCertificate.objects.select_related("student", "school_year", "issued_by").all()
    serializer_class = StudentCertificateSerializer
    search_fields = ["student__first_name", "student__last_name", "consecutive", "verification_code"]
    filterset_fields = ["student", "kind", "school_year"]
    export_filename = "certificados"

    def perform_create(self, serializer):
        instance = serializer.save(
            issued_by=self.request.user,
            created_by=self.request.user,
        )
        instance.content = build_certificate_content(instance)
        instance.save(update_fields=["content"])
        self.log_action("CREATE", instance)
        return instance


ROUTES = [
    ("guardians", GuardianViewSet, "guardian"),
    ("students", StudentViewSet, "student"),
    ("student-guardians", StudentGuardianViewSet, "studentguardian"),
    ("enrollments", EnrollmentViewSet, "enrollment"),
    ("admissions", AdmissionViewSet, "admission"),
    ("inscriptions", InscriptionViewSet, "inscription"),
    ("student-documents", StudentDocumentViewSet, "studentdocument"),
    ("student-certificates", StudentCertificateViewSet, "studentcertificate"),
]
