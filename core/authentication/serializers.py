"""Serializers de autenticacion, 2FA y trazabilidad."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from config.permissions import build_permission_map

from .models import AccessLog, LoginAttempt, SecurityToken, TwoFactorDevice, UserSession

User = get_user_model()


class PLSGETokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT enriquecido con perfil, permisos y estado de 2FA."""

    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["username"] = user.username
        token["name"] = user.get_full_name()
        token["role"] = user.role_code
        token["is_super_admin"] = user.is_super_admin
        token["two_factor"] = user.two_factor_enabled
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if user.is_locked:
            raise serializers.ValidationError(
                {"detail": "La cuenta se encuentra bloqueada temporalmente. Intente mas tarde."}
            )
        data["user"] = {
            "id": user.id,
            "uuid": str(user.uuid),
            "email": user.email,
            "username": user.username,
            "full_name": user.get_full_name(),
            "role": user.role_code,
            "role_name": user.role_name,
            "must_change_password": user.must_change_password,
            "two_factor_enabled": user.two_factor_enabled,
            "requires_2fa": user.two_factor_enabled or user.two_factor_enforced,
        }
        data["permissions"] = build_permission_map(user)
        return data


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Correo electronico o nombre de usuario")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    remember_me = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request, username=attrs["identifier"], password=attrs["password"])
        if user is None:
            candidate = User.objects.filter(email__iexact=attrs["identifier"]).first()
            if candidate and candidate.is_locked:
                raise serializers.ValidationError(
                    {"detail": f"Cuenta bloqueada por seguridad hasta {candidate.locked_until:%H:%M}."}
                )
            raise serializers.ValidationError({"detail": "Credenciales invalidas. Verifique e intente nuevamente."})
        if not user.is_active:
            raise serializers.ValidationError({"detail": "El usuario se encuentra inactivo."})
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def get_user(self):
        return User.objects.filter(email__iexact=self.validated_data["email"], is_active=True).first()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        record = SecurityToken.objects.filter(
            token=attrs["token"], purpose=SecurityToken.PURPOSE_RESET
        ).select_related("user").first()
        if record is None or not record.is_valid:
            raise serializers.ValidationError({"token": "El enlace es invalido o ya expiro."})
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Las contrasenas no coinciden."})
        validate_password(attrs["new_password"], record.user)
        attrs["record"] = record
        return attrs

    def save(self, **kwargs):
        record = self.validated_data["record"]
        user = record.user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save()
        record.consume()
        return user


class TwoFactorSetupSerializer(serializers.Serializer):
    secret = serializers.CharField(read_only=True)
    provisioning_uri = serializers.CharField(read_only=True)
    qr_svg = serializers.CharField(read_only=True)
    recovery_codes = serializers.ListField(read_only=True)
    issuer = serializers.CharField(read_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=16)

    def validate_token(self, value):
        return value.strip().replace(" ", "")


class TwoFactorDeviceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = TwoFactorDevice
        fields = ["id", "user", "user_name", "user_email", "name", "confirmed", "confirmed_at", "last_used_at", "created_at"]
        read_only_fields = fields


class AccessLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="user.role.name", read_only=True)
    event_display = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = AccessLog
        fields = [
            "id", "user", "user_name", "user_email", "role_name", "event", "event_display",
            "success", "ip_address", "device", "location", "detail", "created_at",
        ]
        read_only_fields = fields


class LoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginAttempt
        fields = ["id", "identifier", "user", "success", "reason", "ip_address", "user_agent", "created_at"]
        read_only_fields = fields


class UserSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    role_name = serializers.CharField(source="user.role.name", read_only=True)

    class Meta:
        model = UserSession
        fields = [
            "id", "user", "user_name", "role_name", "session_key", "ip_address",
            "user_agent", "last_activity", "is_active", "closed_at", "created_at",
        ]
        read_only_fields = fields
