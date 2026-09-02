"""Senales de autenticacion: trazabilidad de accesos."""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    from .services import record_access

    record_access(user=user, request=request, event="LOGIN", success=True)


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    from .services import record_access

    if user is not None:
        record_access(user=user, request=request, event="LOGOUT", success=True)


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    from .services import record_failed_attempt

    record_failed_attempt(credentials.get("username") or credentials.get("email"), request)
