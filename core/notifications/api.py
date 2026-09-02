"""API REST del centro de notificaciones."""
from __future__ import annotations

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """Cada usuario administra unicamente sus propias notificaciones."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["level", "module"]
    search_fields = ["title", "message"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, recipient=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({"success": True})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"success": True, "updated": updated})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(read_at__isnull=True).count()})


ROUTES = [("notifications", NotificationViewSet, "notification")]
