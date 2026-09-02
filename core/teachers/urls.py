"""Rutas HTML del modulo docente."""
from django.urls import path

from . import views

app_name = "teachers"

urlpatterns = [
    path("", views.TeacherRegistryView.as_view(), name="registry"),
    path("asignaturas/", views.TeacherSubjectsView.as_view(), name="subjects"),
    path("horarios/", views.TeacherScheduleView.as_view(), name="schedules"),
    path("carga-academica/", views.TeacherLoadView.as_view(), name="load"),
    path("procesos/", views.TeacherProcessView.as_view(), name="processes"),
]
