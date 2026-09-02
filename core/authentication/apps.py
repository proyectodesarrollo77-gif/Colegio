from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.authentication"
    label = "authentication"
    verbose_name = "Autenticacion y Seguridad"

    def ready(self):
        from . import signals  # noqa: F401
