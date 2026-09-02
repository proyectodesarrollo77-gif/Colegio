"""Serializers del modulo de estudiantes."""
from __future__ import annotations

from rest_framework import serializers

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


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    relation_display = serializers.CharField(source="get_relation_display", read_only=True)
    students_count = serializers.IntegerField(source="students.count", read_only=True)

    class Meta:
        model = Guardian
        fields = [
            "id", "user", "document_type", "document_number", "first_name", "last_name",
            "full_name", "relation", "relation_display", "email", "phone", "mobile",
            "address", "occupation", "workplace", "education_level",
            "lives_with_student", "is_active", "students_count",
        ]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True)
    guardian_phone = serializers.CharField(source="guardian.mobile", read_only=True)
    guardian_email = serializers.CharField(source="guardian.email", read_only=True)
    relation_display = serializers.CharField(source="guardian.get_relation_display", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            "id", "student", "student_name", "guardian", "guardian_name", "guardian_phone",
            "guardian_email", "relation_display", "is_primary", "is_financial",
            "can_pickup", "notes",
        ]


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    group_name = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "student_code", "document_type", "document_number", "first_name", "last_name",
            "full_name", "display_name", "gender", "age", "birth_date", "email", "mobile",
            "status", "group_name", "grade_name", "guardian_name", "photo",
        ]

    def get_group_name(self, obj):
        group = obj.current_group
        return group.name if group else None

    def get_grade_name(self, obj):
        group = obj.current_group
        return group.grade.name if group else None

    def get_guardian_name(self, obj):
        guardian = obj.main_guardian
        return guardian.full_name if guardian else None


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    guardian_links = StudentGuardianSerializer(many=True, read_only=True)
    current_group_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "uuid", "user", "user_email", "institution", "institution_name", "student_code",
            "document_type", "document_number", "document_city", "first_name", "last_name", "full_name",
            "birth_date", "birth_place", "gender", "age", "photo", "email", "phone", "mobile",
            "address", "neighborhood", "city", "department", "stratum",
            "blood_type", "eps", "disability", "allergies", "medical_notes",
            "emergency_contact", "emergency_phone", "ethnicity", "displaced", "sisben", "religion",
            "previous_school", "entry_date", "exit_date", "exit_reason", "status",
            "observations", "is_active", "guardian_links", "current_group_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "student_code", "created_at", "updated_at"]

    def get_current_group_name(self, obj):
        group = obj.current_group
        return group.name if group else None


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    grade_name = serializers.CharField(source="group.grade.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    type_display = serializers.CharField(source="get_enrollment_type_display", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "student", "student_name", "student_document", "school_year", "school_year_name",
            "group", "group_name", "grade_name", "enrollment_number", "enrollment_date",
            "enrollment_type", "type_display", "status", "status_display", "folio", "book",
            "withdrawal_date", "withdrawal_reason", "is_repeating", "scholarship",
            "observations", "is_active",
        ]
        read_only_fields = ["enrollment_number"]

    def validate(self, attrs):
        group = attrs.get("group") or getattr(self.instance, "group", None)
        student = attrs.get("student") or getattr(self.instance, "student", None)
        year = attrs.get("school_year") or getattr(self.instance, "school_year", None)
        if group and self.instance is None and group.available_seats <= 0:
            raise serializers.ValidationError({"group": "El grupo no tiene cupos disponibles."})
        if student and year:
            queryset = Enrollment.objects.filter(student=student, school_year=year, deleted_at__isnull=True)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"student": "El estudiante ya tiene una matricula registrada para este ano lectivo."}
                )
        return attrs


class AdmissionSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Admission
        fields = [
            "id", "school_year", "school_year_name", "grade", "grade_name",
            "applicant_document_type", "applicant_document", "applicant_first_name",
            "applicant_last_name", "applicant_name", "birth_date", "gender",
            "guardian_name", "guardian_document", "guardian_email", "guardian_phone",
            "previous_school", "application_date", "interview_date", "score",
            "status", "status_display", "approved_by", "approved_at", "student",
            "observations", "is_active",
        ]
        read_only_fields = ["approved_by", "approved_at", "student"]


class InscriptionSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Inscription
        fields = [
            "id", "school_year", "grade", "grade_name", "full_name", "document", "birth_date",
            "guardian_name", "email", "phone", "message", "source", "status", "status_display",
            "admission", "created_at",
        ]


class StudentDocumentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)

    class Meta:
        model = StudentDocument
        fields = [
            "id", "student", "student_name", "kind", "kind_display", "name", "file",
            "is_verified", "verified_by", "verified_by_name", "notes", "created_at",
        ]


class StudentCertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.get_full_name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)

    class Meta:
        model = StudentCertificate
        fields = [
            "id", "student", "student_name", "student_document", "school_year", "school_year_name",
            "kind", "kind_display", "consecutive", "issued_at", "issued_by", "issued_by_name",
            "purpose", "content", "file", "verification_code",
        ]
        read_only_fields = ["consecutive", "verification_code", "issued_by", "content"]
