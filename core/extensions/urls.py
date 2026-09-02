"""Rutas HTML del modulo de extensiones."""
from django.urls import path

from . import views

app_name = "extensions"

urlpatterns = [
    path("", views.FormBuilderView.as_view(), name="forms"),
    path("campos/", views.FormFieldView.as_view(), name="form_fields"),
    path("espacios/", views.VirtualSpaceView.as_view(), name="spaces"),
    path("f/<slug:slug>/", views.public_form, name="public_form"),
]
