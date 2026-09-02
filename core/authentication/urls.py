"""Rutas HTML del modulo de autenticacion."""
from django.urls import path

from . import views

app_name = "authentication"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-change/", views.force_password_change, name="force_password_change"),
    path("2fa/setup/", views.two_factor_setup, name="two_factor_setup"),
    path("2fa/verify/", views.two_factor_verify, name="two_factor_verify"),
    path("2fa/disable/", views.two_factor_disable, name="two_factor_disable"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("verify-email/resend/", views.resend_verification, name="resend_verification"),
]
