"""Rutas HTML del modulo de asistencia."""
from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.AttendanceRegisterView.as_view(), name="register"),
    path("reporte/", views.AttendanceReportView.as_view(), name="report"),
]
