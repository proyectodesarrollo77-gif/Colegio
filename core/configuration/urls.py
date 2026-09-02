"""Rutas HTML del modulo de configuracion."""
from django.urls import path

from core.users.views import PermissionMatrixView

from . import views

app_name = "configuration"

urlpatterns = [
    path("perfiles/", PermissionMatrixView.as_view(), name="profiles"),
    path("encabezado-reportes/", views.ReportHeaderView.as_view(), name="report_header"),
    path("decimas-notas/", views.GradeDecimalView.as_view(), name="grade_decimals"),
    path("parametros/", views.SystemParameterView.as_view(), name="parameters"),
]
