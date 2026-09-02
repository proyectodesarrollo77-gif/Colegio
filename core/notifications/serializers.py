"""Serializers de notificaciones."""
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "recipient", "sender", "sender_name", "title", "message", "level",
            "icon", "module", "url", "read_at", "is_read", "emailed", "created_at",
        ]
        read_only_fields = ["recipient", "sender", "read_at", "emailed", "created_at"]
