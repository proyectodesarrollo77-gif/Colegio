"""Rutas HTML del modulo de tutoria."""
from django.urls import path

from . import views

app_name = "tutoring"

urlpatterns = [
    path("", views.TutorView.as_view(), name="tutors"),
    path("juicios/", views.TutoringJudgmentView.as_view(), name="judgments"),
    path("convivencia/", views.CoexistenceView.as_view(), name="coexistence"),
    path("reportes/", views.TutoringReportView.as_view(), name="reports"),
    path("bloqueo-boletin/", views.ReportBlockView.as_view(), name="block"),
]
