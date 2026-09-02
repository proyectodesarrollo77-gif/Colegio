"""Rutas HTML del modulo de usuarios y Mi Perfil."""
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.UserManagementView.as_view(), name="management"),
    path("estudiantes/", views.StudentUsersView.as_view(), name="students"),
    path("coordinadores/", views.CoordinatorUsersView.as_view(), name="coordinators"),
    path("credenciales/", views.CredentialsView.as_view(), name="credentials"),
    path("credenciales/<int:pk>/print/", views.credentials_print, name="credentials_print"),
    path("accesos/", views.AccessReportView.as_view(), name="access_report"),
    path("authenticator/", views.AuthenticatorView.as_view(), name="authenticator"),
    path("mi-perfil/", views.ProfileView.as_view(), name="profile"),
    path("mi-perfil/seguridad/", views.ProfileSecurityView.as_view(), name="profile_security"),
    path("mi-perfil/actualizar/", views.profile_update, name="profile_update"),
    path("mi-perfil/password/", views.profile_password, name="profile_password"),
]
