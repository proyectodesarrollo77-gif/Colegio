"""Inyecta las notificaciones no leidas del usuario autenticado."""


def notifications(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"unread_notifications": 0, "recent_notifications": []}
    try:
        from .models import Notification

        queryset = Notification.objects.filter(recipient=user, read_at__isnull=True).order_by("-created_at")
        return {
            "unread_notifications": queryset.count(),
            "recent_notifications": list(queryset[:6]),
        }
    except Exception:
        return {"unread_notifications": 0, "recent_notifications": []}
