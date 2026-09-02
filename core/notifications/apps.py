from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.notifications"
    label = "notifications"
    verbose_name = "Notificaciones"

    def ready(self):
        from . import signals  # noqa: F401
