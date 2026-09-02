"""
Enrutador maestro de la API REST de PL_SGE.

Cada aplicacion declara en su modulo `api.py` una lista `ROUTES` con tuplas
(prefijo, ViewSet, basename); este modulo las registra en un unico router.
"""
from __future__ import annotations

from importlib import import_module

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from core.attendance.api import AttendanceSheetAPIView
from core.authentication.api import (
    ChangePasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
    TwoFactorAPIView,
    TwoFactorRegenerateAPIView,
)
from core.dashboard.api import DashboardAPIView
from core.elections.api import CastVoteAPIView
from core.evaluations.api import GradeSheetAPIView
from core.pae.api import (
    PaeAlertsAPIView,
    PaeDashboardAPIView,
    PaeDeliverySheetAPIView,
    PaeImportAPIView,
    PaeVerificationSheetAPIView,
)
from core.reports.api import AcademicStatisticsAPIView, AdministrativeStatisticsAPIView
from core.users.api import MyPermissionsView

API_MODULES = [
    "core.users.api",
    "core.authentication.api",
    "core.audit.api",
    "core.institutions.api",
    "core.configuration.api",
    "core.academic.api",
    "core.students.api",
    "core.teachers.api",
    "core.evaluations.api",
    "core.attendance.api",
    "core.tutoring.api",
    "core.observer.api",
    "core.promotion.api",
    "core.recoveries.api",
    "core.emphases.api",
    "core.documents.api",
    "core.reports.api",
    "core.agenda.api",
    "core.classroom.api",
    "core.elections.api",
    "core.extensions.api",
    "core.notifications.api",
    "core.pae.api",
]

router = DefaultRouter()
router.trailing_slash = "/"

for module_path in API_MODULES:
    module = import_module(module_path)
    for prefix, viewset, basename in getattr(module, "ROUTES", []):
        router.register(prefix, viewset, basename=basename)


urlpatterns = [
    # ---- Autenticacion y tokens ----
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/login/", LoginAPIView.as_view(), name="api_login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="api_logout"),
    path("auth/me/", MeAPIView.as_view(), name="api_me"),
    path("auth/password-reset/", PasswordResetRequestAPIView.as_view(), name="api_password_reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmAPIView.as_view(), name="api_password_reset_confirm"),
    path("auth/password-change/", ChangePasswordAPIView.as_view(), name="api_password_change"),
    path("auth/2fa/", TwoFactorAPIView.as_view(), name="api_two_factor"),
    path("auth/2fa/recovery-codes/", TwoFactorRegenerateAPIView.as_view(), name="api_two_factor_codes"),
    path("auth/permissions/", MyPermissionsView.as_view(), name="api_permissions"),
    # ---- Procesos especializados ----
    path("dashboard/", DashboardAPIView.as_view(), name="api_dashboard"),
    path("grade-sheet/", GradeSheetAPIView.as_view(), name="api_grade_sheet"),
    path("attendance-sheet/", AttendanceSheetAPIView.as_view(), name="api_attendance_sheet"),
    path("elections/cast-vote/", CastVoteAPIView.as_view(), name="api_cast_vote"),
    path("statistics/academic/", AcademicStatisticsAPIView.as_view(), name="api_statistics_academic"),
    path("statistics/administrative/", AdministrativeStatisticsAPIView.as_view(), name="api_statistics_admin"),
    # ---- PAE ----
    path("pae/dashboard/", PaeDashboardAPIView.as_view(), name="api_pae_dashboard"),
    path("pae/alertas/", PaeAlertsAPIView.as_view(), name="api_pae_alerts"),
    path("pae/planilla-entregas/", PaeDeliverySheetAPIView.as_view(), name="api_pae_delivery_sheet"),
    path("pae/hoja-verificacion/", PaeVerificationSheetAPIView.as_view(), name="api_pae_verification_sheet"),
    path("pae/importar/", PaeImportAPIView.as_view(), name="api_pae_import"),
    # ---- Recursos CRUD ----
    path("", include(router.urls)),
]
