"""Rutas HTML del modulo de evaluaciones."""
from django.urls import path

from . import views

app_name = "evaluations"

urlpatterns = [
    path("notas/", views.GradeEntryView.as_view(), name="grades"),
    path("juicios/", views.JudgmentAssignmentView.as_view(), name="judgments"),
    path("cualitativa/", views.QualitativeView.as_view(), name="qualitative"),
    path("preescolar/", views.PreschoolPurposeView.as_view(), name="preschool"),
    path("bilingue/", views.BilingualView.as_view(), name="bilingual"),
]
