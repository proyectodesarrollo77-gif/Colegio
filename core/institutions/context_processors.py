"""Inyecta los datos institucionales en todas las plantillas."""
from django.conf import settings


def institution(request):
    data = {
        "APP": settings.PLSGE,
        "institution": None,
        "active_school_year": None,
        "active_period": None,
        # Instituciones a las que el Super Administrador puede cambiarse desde
        # la barra superior. Para los demas perfiles queda vacia.
        "available_institutions": [],
    }
    try:
        from core.academic.models import AcademicPeriod, SchoolYear

        from .models import Institution

        data["institution"] = Institution.current()
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_super_admin:
            data["available_institutions"] = list(
                Institution.objects.filter(is_active=True, deleted_at__isnull=True)
                .order_by("-is_default", "name")
            )
        # Debe salir de la institucion activa: sin filtrar, el menu mostraba el
        # ano lectivo de otra institucion en una que aun no tiene ninguno.
        year = SchoolYear.current()
        data["active_school_year"] = year
        if year:
            data["active_period"] = AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
    except Exception:
        # Durante migraciones iniciales las tablas aun no existen.
        pass
    return data
