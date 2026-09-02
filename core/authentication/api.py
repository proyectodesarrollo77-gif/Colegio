"""API REST de autenticacion, 2FA y trazabilidad de accesos."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.permissions import build_permission_map
from config.viewsets import BaseModelViewSet, ReadOnlyBaseViewSet

from .middleware import TWO_FACTOR_SESSION_KEY
from .models import AccessLog, LoginAttempt, TwoFactorDevice, UserSession
from .serializers import (
    AccessLogSerializer,
    LoginAttemptSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TwoFactorDeviceSerializer,
    TwoFactorVerifySerializer,
    UserSessionSerializer,
)
from .services import (
    close_other_sessions,
    disable_two_factor,
    get_or_create_device,
    qr_svg,
    record_access,
    record_login_attempt,
    send_password_reset,
)
from .utils import get_client_ip


class LoginAPIView(APIView):
    """Autenticacion por sesion + emision de tokens JWT."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            record_login_attempt(
                request.data.get("identifier"), request, success=False, reason="Credenciales invalidas"
            )
            return Response(
                {"success": False, "detail": serializer.errors.get("detail", ["Credenciales invalidas."])[0]},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data["user"]
        django_login(request, user, backend="core.authentication.backends.EmailOrUsernameBackend")
        request.session[TWO_FACTOR_SESSION_KEY] = not user.two_factor_enabled
        user.register_successful_login(ip=get_client_ip(request))
        record_login_attempt(user.email, request, success=True, reason="OK", user=user)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.get_full_name(),
                    "role": user.role_code,
                    "role_name": user.role_name,
                    "must_change_password": user.must_change_password,
                    "requires_2fa": user.two_factor_enabled or user.two_factor_enforced,
                },
                "permissions": build_permission_map(user),
            }
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        record_access(request.user, request, event="LOGOUT")
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass
        django_logout(request)
        return Response({"success": True, "detail": "Sesion finalizada."})


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "uuid": str(user.uuid),
                "email": user.email,
                "username": user.username,
                "full_name": user.get_full_name(),
                "initials": user.initials,
                "role": user.role_code,
                "role_name": user.role_name,
                "photo": user.photo.url if user.photo else None,
                "two_factor_enabled": user.two_factor_enabled,
                "email_verified": user.email_verified,
                "must_change_password": user.must_change_password,
                "theme": user.theme,
                "permissions": build_permission_map(user),
            }
        )


class PasswordResetRequestAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()
        if user:
            send_password_reset(user, request)
        return Response(
            {"success": True, "detail": "Si el correo esta registrado recibira las instrucciones de recuperacion."}
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_access(user, request, event="PASSWORD_CHANGE", detail="Recuperacion via API")
        return Response({"success": True, "detail": "Contrasena actualizada correctamente."})


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from core.users.serializers import ChangePasswordSerializer

        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_access(request.user, request, event="PASSWORD_CHANGE")
        return Response({"success": True, "detail": "Contrasena actualizada."})


class TwoFactorAPIView(APIView):
    """Alta, confirmacion y baja del segundo factor."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        device = get_or_create_device(request.user)
        return Response(
            {
                "issuer": settings.PLSGE["OTP_ISSUER"],
                "secret": device.secret,
                "provisioning_uri": device.provisioning_uri(),
                "qr_svg": qr_svg(device.provisioning_uri()),
                "confirmed": device.confirmed,
                "recovery_codes": [item["code"] for item in device.recovery_codes if not item.get("used")],
            }
        )

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = get_or_create_device(request.user)
        if not device.verify(serializer.validated_data["token"]):
            record_access(request.user, request, event="2FA_FAIL", success=False)
            return Response(
                {"success": False, "detail": "Codigo invalido."}, status=status.HTTP_400_BAD_REQUEST
            )
        device.confirm()
        request.user.two_factor_enabled = True
        request.user.save(update_fields=["two_factor_enabled"])
        request.session[TWO_FACTOR_SESSION_KEY] = True
        record_access(request.user, request, event="2FA_OK")
        return Response({"success": True, "detail": "Doble factor activado."})

    def delete(self, request):
        disable_two_factor(request.user)
        return Response({"success": True, "detail": "Doble factor desactivado."})


class TwoFactorRegenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device = get_or_create_device(request.user)
        codes = device.build_recovery_codes()
        return Response({"success": True, "recovery_codes": codes})


class AccessLogViewSet(ReadOnlyBaseViewSet):
    module_code = "users.access_report"
    queryset = AccessLog.objects.select_related("user", "user__role").all()
    serializer_class = AccessLogSerializer
    filterset_fields = ["user", "event", "success"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "ip_address", "detail"]
    ordering = ["-created_at"]


class LoginAttemptViewSet(ReadOnlyBaseViewSet):
    module_code = "users.access_report"
    queryset = LoginAttempt.objects.select_related("user").all()
    serializer_class = LoginAttemptSerializer
    filterset_fields = ["success", "user"]
    search_fields = ["identifier", "ip_address", "reason"]


class UserSessionViewSet(BaseModelViewSet):
    module_code = "audit.sessions"
    queryset = UserSession.objects.select_related("user", "user__role").all()
    serializer_class = UserSessionSerializer
    filterset_fields = ["is_active", "user"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "ip_address"]
    export_filename = "sesiones"

    @action(detail=True, methods=["post"], url_path="close")
    def close_session(self, request, pk=None):
        from django.contrib.sessions.models import Session

        user_session = self.get_object()
        Session.objects.filter(session_key=user_session.session_key).delete()
        user_session.close()
        return Response({"success": True, "detail": "Sesion cerrada."})

    @action(detail=False, methods=["post"], url_path="close-mine")
    def close_mine(self, request):
        count = close_other_sessions(request.user, keep_session_key=request.session.session_key)
        return Response({"success": True, "closed": count})


class TwoFactorDeviceViewSet(ReadOnlyBaseViewSet):
    module_code = "users.authenticator"
    queryset = TwoFactorDevice.objects.select_related("user", "user__role").all()
    serializer_class = TwoFactorDeviceSerializer
    filterset_fields = ["confirmed", "user"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]

    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        device = self.get_object()
        device.rotate_secret()
        device.user.two_factor_enabled = False
        device.user.save(update_fields=["two_factor_enabled"])
        return Response({"success": True, "detail": "Dispositivo reiniciado."})


ROUTES = [
    ("access-logs", AccessLogViewSet, "accesslog"),
    ("login-attempts", LoginAttemptViewSet, "loginattempt"),
    ("user-sessions", UserSessionViewSet, "usersession"),
    ("two-factor-devices", TwoFactorDeviceViewSet, "twofactordevice"),
]
