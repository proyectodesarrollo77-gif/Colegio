"""
Enrutamiento principal de PL_SGE.

  /                     -> redireccion al dashboard o al login
  /auth/                -> autenticacion, 2FA y recuperacion de clave
  /api/                 -> API REST completa
  /admin/               -> administracion tecnica de Django
  /<modulo>/            -> paginas de cada modulo funcional
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView

from core.authentication.views import health


def root(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")
    return redirect("authentication:login")


urlpatterns = [
    path("", root, name="root"),
    path("healthz", health, name="health"),
    path("admin/", admin.site.urls),
    # ---- Autenticacion ----
    path("auth/", include("core.authentication.urls")),
    # ---- API REST ----
    path("api/", include("config.api")),
    # ---- Modulos funcionales ----
    path("dashboard/", include("core.dashboard.urls")),
    path("institucion/", include("core.institutions.urls")),
    path("configuracion/", include("core.configuration.urls")),
    path("usuarios/", include("core.users.urls")),
    path("directiva/", include("core.academic.urls")),
    path("estudiantes/", include("core.students.urls")),
    path("docentes/", include("core.teachers.urls")),
    path("evaluaciones/", include("core.evaluations.urls")),
    path("asistencia/", include("core.attendance.urls")),
    path("recuperaciones/", include("core.recoveries.urls")),
    path("promocion/", include("core.promotion.urls")),
    path("enfasis/", include("core.emphases.urls")),
    path("tutoria/", include("core.tutoring.urls")),
    path("observador/", include("core.observer.urls")),
    path("agenda/", include("core.agenda.urls")),
    path("aula-virtual/", include("core.classroom.urls")),
    path("elecciones/", include("core.elections.urls")),
    path("documentos/", include("core.documents.urls")),
    path("reportes/", include("core.reports.urls")),
    path("extensiones/", include("core.extensions.urls")),
    path("pae/", include("core.pae.urls")),
    path("auditoria/", include("core.audit.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")

handler400 = "config.errors.bad_request"
handler403 = "config.errors.permission_denied"
handler404 = "config.errors.page_not_found"
handler500 = "config.errors.server_error"
