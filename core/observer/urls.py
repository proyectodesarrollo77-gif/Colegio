"""Rutas HTML del observador."""
from django.urls import path

from . import views

app_name = "observer"

urlpatterns = [
    path("", views.ObserverRecordView.as_view(), name="records"),
    path("tipos/", views.ObservationCategoryView.as_view(), name="categories"),
    path("historial/", views.ObserverHistoryView.as_view(), name="history"),
]
