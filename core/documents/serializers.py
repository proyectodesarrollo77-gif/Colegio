"""Serializers de documentos institucionales."""
from rest_framework import serializers

from .models import DocumentIssue, DocumentTemplate


class DocumentTemplateSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    issues_count = serializers.IntegerField(source="issues.count", read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = [
            "id", "institution", "institution_name", "code", "name", "kind", "kind_display",
            "header", "body", "footer", "signatures", "paper_size", "orientation",
            "requires_consecutive", "consecutive_prefix", "next_consecutive",
            "requires_approval", "show_qr", "is_active", "issues_count",
        ]


class DocumentIssueSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DocumentIssue
        fields = [
            "id", "template", "template_name", "student", "student_name", "teacher", "teacher_name",
            "consecutive", "title", "content", "context_data", "issued_at", "issued_by",
            "issued_by_name", "status", "status_display", "approved_by", "approved_at",
            "verification_code", "file", "print_count",
        ]
        read_only_fields = [
            "consecutive", "content", "issued_by", "approved_by", "approved_at",
            "verification_code", "print_count",
        ]
