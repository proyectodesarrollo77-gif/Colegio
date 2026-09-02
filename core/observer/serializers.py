"""Serializers del observador del estudiante."""
from rest_framework import serializers

from .models import ObservationCategory, ObserverEntry, ObserverFollowUp


class ObservationCategorySerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    entries_count = serializers.IntegerField(source="entries.count", read_only=True)

    class Meta:
        model = ObservationCategory
        fields = [
            "id", "code", "name", "description", "severity", "severity_display", "color",
            "requires_guardian", "requires_commitment", "manual_article", "order",
            "is_active", "entries_count",
        ]


class ObserverFollowUpSerializer(serializers.ModelSerializer):
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)

    class Meta:
        model = ObserverFollowUp
        fields = ["id", "entry", "date", "description", "result", "responsible", "responsible_name"]


class ObserverEntrySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    group_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    severity = serializers.CharField(source="category.severity", read_only=True)
    severity_display = serializers.CharField(source="category.get_severity_display", read_only=True)
    reported_by_name = serializers.CharField(source="reported_by.get_full_name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    follow_ups = ObserverFollowUpSerializer(many=True, read_only=True)

    class Meta:
        model = ObserverEntry
        fields = [
            "id", "student", "student_name", "student_document", "group_name", "school_year",
            "period", "period_name", "category", "category_name", "severity", "severity_display",
            "date", "place", "description", "student_version", "actions_taken", "commitments",
            "reported_by", "reported_by_name", "guardian_notified", "guardian_notified_at",
            "student_signed", "guardian_signed", "status", "attachment", "follow_ups", "created_at",
        ]
        read_only_fields = ["guardian_notified_at", "reported_by"]

    def get_group_name(self, obj):
        group = obj.student.current_group
        return group.name if group else None
