"""Serializers de la agenda virtual."""
from rest_framework import serializers

from .models import AgendaActivity, AgendaEvent, Circular


class AgendaEventSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)
    groups_display = serializers.SerializerMethodField()

    class Meta:
        model = AgendaEvent
        fields = [
            "id", "school_year", "title", "description", "event_type", "type_display",
            "audience", "audience_display", "groups", "groups_display", "start_at", "end_at",
            "all_day", "place", "color", "is_published", "send_notification", "attachment",
        ]

    def get_groups_display(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True)[:5])

    def validate(self, attrs):
        start = attrs.get("start_at") or getattr(self.instance, "start_at", None)
        end = attrs.get("end_at") or getattr(self.instance, "end_at", None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_at": "La fecha final debe ser posterior a la inicial."})
        return attrs


class AgendaActivitySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    teacher_name = serializers.CharField(source="assignment.teacher.full_name", read_only=True)

    class Meta:
        model = AgendaActivity
        fields = [
            "id", "assignment", "teacher_name", "group", "group_name", "subject", "subject_name",
            "period", "period_name", "title", "description", "assigned_date", "due_date",
            "status", "status_display", "attachment", "notify_guardians",
        ]


class CircularSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)

    class Meta:
        model = Circular
        fields = [
            "id", "school_year", "number", "subject", "body", "audience", "audience_display",
            "groups", "attachment", "scheduled_at", "sent_at", "recipients_count",
            "opened_count", "status", "status_display", "send_email", "created_at",
        ]
        read_only_fields = ["sent_at", "recipients_count", "opened_count"]
