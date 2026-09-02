from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.students"
    label = "students"
    verbose_name = "Estudiantes"

    def ready(self):
        from . import signals  # noqa: F401
