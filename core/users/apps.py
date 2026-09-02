from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.users"
    label = "users"
    verbose_name = "Usuarios y Permisos"

    def ready(self):
        from . import signals  # noqa: F401
