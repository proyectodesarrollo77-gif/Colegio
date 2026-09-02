"""Rutas HTML del modulo institucional."""
from django.urls import path

from . import views

app_name = "institutions"

urlpatterns = [
    path("", views.InstitutionProfileView.as_view(), name="profile"),
    path("sedes/", views.CampusView.as_view(), name="campuses"),
    # Panel del Super Administrador: administra todas las instituciones.
    path("panel/", views.InstitutionPanelView.as_view(), name="panel"),
    path("panel/nueva/", views.InstitutionFormView.as_view(), name="create"),
    path("panel/<int:pk>/editar/", views.InstitutionFormView.as_view(), name="edit"),
    path("panel/<int:pk>/ingresar/", views.switch_institution, name="switch"),
    path("panel/salir/", views.exit_institution, name="exit"),
    path("panel/<int:pk>/estado/", views.toggle_institution, name="toggle"),
    path("panel/<int:pk>/usuarios/", views.InstitutionUsersView.as_view(), name="users"),
    path("panel/usuarios/<int:pk>/clave/", views.change_user_password, name="change_password"),
]
