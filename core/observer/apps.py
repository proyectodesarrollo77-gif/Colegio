from django.apps import AppConfig


class ObserverConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.observer"
    label = "observer"
    verbose_name = "Observador"
