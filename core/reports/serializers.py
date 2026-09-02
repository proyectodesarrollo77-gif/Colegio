"""Serializers del modulo de reportes."""
from rest_framework import serializers

from .models import DashboardIndicator, ReportDefinition, ReportExecution


class ReportDefinitionSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    executions_count = serializers.IntegerField(source="executions.count", read_only=True)

    class Meta:
        model = ReportDefinition
        fields = [
            "id", "code", "name", "category", "category_display", "description", "icon",
            "parameters", "default_output", "allowed_outputs", "required_module",
            "order", "is_active", "executions_count",
        ]


class ReportExecutionSerializer(serializers.ModelSerializer):
    definition_name = serializers.CharField(source="definition.name", read_only=True)
    executed_by_name = serializers.CharField(source="executed_by.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ReportExecution
        fields = [
            "id", "definition", "definition_name", "executed_by", "executed_by_name",
            "parameters", "output_format", "status", "status_display", "rows",
            "duration_ms", "file", "error_message", "executed_at",
        ]
        read_only_fields = ["executed_by", "rows", "duration_ms", "status", "error_message"]


class DashboardIndicatorSerializer(serializers.ModelSerializer):
    variation = serializers.FloatField(read_only=True)

    class Meta:
        model = DashboardIndicator
        fields = [
            "id", "code", "name", "value", "previous_value", "variation", "unit",
            "icon", "color", "category", "calculated_at", "order", "is_active",
        ]
