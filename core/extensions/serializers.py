"""Serializers del modulo de extensiones."""
from rest_framework import serializers

from .models import FormDefinition, FormField, FormSubmission, VirtualSpace


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            "id", "form", "key", "label", "field_type", "placeholder", "help_text",
            "options", "required", "order", "width",
        ]


class FormDefinitionSerializer(serializers.ModelSerializer):
    fields_list = FormFieldSerializer(source="fields", many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = FormDefinition
        fields = [
            "id", "institution", "slug", "title", "description", "audience", "audience_display",
            "status", "status_display", "opens_at", "closes_at", "allow_multiple",
            "notify_email", "success_message", "submissions_count", "is_open",
            "fields_list", "is_active",
        ]
        read_only_fields = ["submissions_count"]


class FormSubmissionSerializer(serializers.ModelSerializer):
    form_title = serializers.CharField(source="form.title", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = FormSubmission
        fields = [
            "id", "form", "form_title", "user", "user_name", "data", "submitted_at",
            "ip_address", "reviewed", "reviewed_by", "notes",
        ]
        read_only_fields = ["submitted_at", "ip_address", "user"]


class VirtualSpaceSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    audience_display = serializers.CharField(source="get_audience_display", read_only=True)

    class Meta:
        model = VirtualSpace
        fields = [
            "id", "institution", "name", "description", "kind", "kind_display", "url",
            "icon", "color", "audience", "audience_display", "open_in_new_tab",
            "order", "clicks", "is_active",
        ]
        read_only_fields = ["clicks"]
