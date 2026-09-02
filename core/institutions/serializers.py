"""Serializers de datos institucionales."""
from rest_framework import serializers

from .models import Campus, Institution, InstitutionalCalendar, Shift


class InstitutionSerializer(serializers.ModelSerializer):
    campuses_count = serializers.IntegerField(source="campuses.count", read_only=True)
    students_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id", "code", "name", "short_name", "nit", "resolution", "nature", "calendar",
            "country", "department", "city", "address", "phone", "email", "website",
            "logo", "logo_url", "seal", "rector_name", "rector_document", "rector_signature",
            "secretary_name", "secretary_signature", "motto", "mission", "vision",
            "primary_color", "accent_color", "is_default", "is_active",
            "campuses_count", "students_count",
        ]

    def get_students_count(self, obj):
        return obj.students.filter(status="ACTIVO", deleted_at__isnull=True).count()

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None


class CampusSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    coordinator_name = serializers.CharField(source="coordinator.get_full_name", read_only=True)
    groups_count = serializers.IntegerField(source="groups.count", read_only=True)

    class Meta:
        model = Campus
        fields = [
            "id", "institution", "institution_name", "code", "name", "address", "phone",
            "coordinator", "coordinator_name", "is_main", "is_active", "groups_count",
        ]


class ShiftSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "institution", "institution_name", "code", "name", "description",
            "start_time", "end_time", "order", "is_active",
        ]


class InstitutionalCalendarSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = InstitutionalCalendar
        fields = [
            "id", "institution", "name", "event_type", "type_display",
            "start_date", "end_date", "description", "is_active",
        ]
