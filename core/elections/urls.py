"""Rutas HTML del modulo de elecciones."""
from django.urls import path

from . import views

app_name = "elections"

urlpatterns = [
    path("", views.ElectionSetupView.as_view(), name="setup"),
    path("cargos/", views.CandidacyView.as_view(), name="candidacies"),
    path("candidatos/", views.CandidateView.as_view(), name="candidates"),
    path("votacion/", views.VotingView.as_view(), name="voting"),
    path("resultados/", views.ElectionResultsView.as_view(), name="results"),
]
