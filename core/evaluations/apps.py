from django.apps import AppConfig


class EvaluationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.evaluations"
    label = "evaluations"
    verbose_name = "Evaluaciones"

    def ready(self):
        from . import signals  # noqa: F401
