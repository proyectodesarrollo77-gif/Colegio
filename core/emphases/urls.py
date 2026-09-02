"""Rutas HTML de enfasis y disciplinas."""
from django.urls import path

from . import views

app_name = "emphases"

urlpatterns = [
    path("", views.EmphasisCatalogView.as_view(), name="catalog"),
    path("grupos/", views.EmphasisGroupView.as_view(), name="groups"),
    path("matriculas/", views.EmphasisEnrollmentView.as_view(), name="enrollment"),
]
