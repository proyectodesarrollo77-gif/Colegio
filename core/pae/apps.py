from django.apps import AppConfig


class PaeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.pae"
    label = "pae"
    verbose_name = "Programa de Alimentacion Escolar"

    def ready(self):
        from . import signals  # noqa: F401
