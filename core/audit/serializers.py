"""Serializers de la bitacora de auditoria."""
from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    module_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "created_at", "user", "user_label", "role_label", "action", "action_display",
            "module", "module_name", "model_name", "object_id", "object_label", "description",
            "changes", "ip_address", "path", "method", "status_code", "duration_ms",
        ]
        read_only_fields = fields

    def get_module_name(self, obj):
        from core.configuration.modules import module_name

        return module_name(obj.module)
