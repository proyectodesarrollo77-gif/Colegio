"""Rutas HTML del aula virtual."""
from django.urls import path

from . import views

app_name = "classroom"

urlpatterns = [
    path("", views.CourseView.as_view(), name="courses"),
    path("material/", views.CourseMaterialView.as_view(), name="materials"),
    path("actividades/", views.CourseActivityView.as_view(), name="activities"),
    path("seguimiento/", views.CourseTrackingView.as_view(), name="tracking"),
]
