"""Rutas HTML de la agenda virtual."""
from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.AgendaCalendarView.as_view(), name="calendar"),
    path("eventos/", views.AgendaEventResourceView.as_view(), name="events"),
    path("actividades/", views.AgendaActivityView.as_view(), name="activities"),
    path("circulares/", views.CircularView.as_view(), name="mail"),
]
