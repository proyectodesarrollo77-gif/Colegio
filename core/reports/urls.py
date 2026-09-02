"""Rutas HTML del modulo de reportes."""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("academicos/", views.AcademicReportsView.as_view(), name="academic"),
    path("estadisticos/", views.StatisticalReportsView.as_view(), name="statistics"),
    path("administrativos/", views.AdministrativeReportsView.as_view(), name="administrative"),
]
