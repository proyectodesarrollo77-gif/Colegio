"""Rutas HTML del modulo de recuperaciones."""
from django.urls import path

from . import views

app_name = "recoveries"

urlpatterns = [
    path("", views.RecoveryPlanView.as_view(), name="plans"),
    path("actividades/", views.RecoveryActivityView.as_view(), name="activities"),
    path("bilingue/", views.BilingualRecoveryView.as_view(), name="bilingual"),
    path("resultados/", views.RecoveryResultView.as_view(), name="results"),
]
