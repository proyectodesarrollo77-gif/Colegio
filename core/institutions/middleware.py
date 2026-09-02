"""Middleware que resuelve la institucion activa de cada peticion."""
from __future__ import annotations

from .context import (
    SESSION_KEY,
    clear_active_institution,
    set_active_institution,
)


class ActiveInstitutionMiddleware:
    """
    Deja disponible la institucion elegida en el ingreso durante toda la
    peticion, tanto en `request.institution` como en `Institution.current()`.

    Orden de resolucion:
      1. La institucion guardada en la sesion al iniciar sesion.
      2. La institucion asignada al usuario.
      3. La institucion por defecto (comportamiento de instalacion unica).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        institution = self._resolve(request)
        set_active_institution(institution)
        request.institution = institution
        try:
            return self.get_response(request)
        finally:
            # Se libera siempre: el hilo se reutiliza entre peticiones.
            clear_active_institution()

    def _resolve(self, request):
        from .models import Institution

        session_id = None
        try:
            session_id = request.session.get(SESSION_KEY)
        except AttributeError:
            # Peticiones sin sesion (healthz, estaticos).
            pass

        if session_id:
            institution = Institution.objects.filter(pk=session_id, is_active=True).first()
            if institution is not None:
                return institution

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.institution_id:
            institution = Institution.objects.filter(pk=user.institution_id, is_active=True).first()
            if institution is not None:
                return institution

        return Institution.objects.filter(is_active=True).order_by("-is_default", "id").first()
