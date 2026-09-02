"""Serializers del modulo de usuarios, roles y permisos."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from config.permissions import ACTIONS
from core.configuration.modules import MODULE_REGISTRY

from .models import (
    Module,
    Role,
    RolePermission,
    User,
    UserCredentialCertificate,
    UserModulePermission,
    UserPreference,
)


class RoleSerializer(serializers.ModelSerializer):
    users_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id", "code", "name", "description", "color", "is_system",
            "is_active", "landing_url", "order", "users_count", "created_at",
        ]
        read_only_fields = ["is_system", "created_at"]

    def get_users_count(self, obj):
        return obj.users.filter(is_active=True, deleted_at__isnull=True).count()

    def validate_code(self, value):
        return value.strip().upper().replace(" ", "_")


class ModuleSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True)

    class Meta:
        model = Module
        fields = ["id", "code", "name", "parent", "parent_code", "icon", "url_name", "group", "order", "is_active", "show_in_menu"]


class RolePermissionSerializer(serializers.ModelSerializer):
    module_code = serializers.CharField(source="module.code", read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)

    class Meta:
        model = RolePermission
        fields = [
            "id", "role", "role_code", "module", "module_code", "module_name",
            "can_view", "can_create", "can_edit", "can_delete", "can_export", "can_approve",
        ]


class PermissionMatrixSerializer(serializers.Serializer):
    """Carga y guarda la matriz completa de permisos de un rol."""

    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    permissions = serializers.DictField(child=serializers.DictField(child=serializers.BooleanField()))

    @transaction.atomic
    def save(self, **kwargs):
        role = self.validated_data["role"]
        matrix = self.validated_data["permissions"]
        modules = {module.code: module for module in Module.objects.all()}
        updated = 0
        for code, actions in matrix.items():
            module = modules.get(code)
            if not module:
                continue
            RolePermission.objects.update_or_create(
                role=role,
                module=module,
                defaults={
                    "can_view": bool(actions.get("view")),
                    "can_create": bool(actions.get("create")),
                    "can_edit": bool(actions.get("edit")),
                    "can_delete": bool(actions.get("delete")),
                    "can_export": bool(actions.get("export")),
                    "can_approve": bool(actions.get("approve")),
                },
            )
            updated += 1
        return {"role": role.code, "modules": updated}


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            "sidebar_collapsed", "density", "default_module",
            "email_notifications", "push_notifications", "items_per_page",
        ]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    initials = serializers.CharField(read_only=True)
    is_locked = serializers.BooleanField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    generated_password = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "uuid", "username", "email", "first_name", "last_name", "full_name", "initials",
            "document_type", "document_number", "gender", "birth_date", "phone", "mobile",
            "address", "city", "photo", "role", "role_name", "role_code",
            "institution", "institution_name", "is_active", "is_staff", "email_verified",
            "must_change_password", "two_factor_enabled", "two_factor_enforced", "is_locked",
            "last_login", "last_login_ip", "theme", "notes", "password", "generated_password",
            "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "last_login", "last_login_ip", "created_at", "updated_at"]
        extra_kwargs = {"username": {"required": False}}

    def validate_email(self, value):
        value = value.strip().lower()
        queryset = User.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario registrado con este correo.")
        return value

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        raw_password = validated_data.pop("password", "") or User.generate_password()
        if not validated_data.get("username"):
            validated_data["username"] = User.build_username(
                validated_data.get("first_name", ""),
                validated_data.get("last_name", ""),
                validated_data.get("document_number", ""),
            )
        user = User(**validated_data)
        user.set_password(raw_password)
        user.must_change_password = True
        user.save()
        user.generated_password = raw_password
        UserCredentialCertificate.objects.create(
            user=user,
            plain_password=raw_password,
            issued_by=self.context["request"].user if self.context.get("request") else None,
        )
        return user

    def update(self, instance, validated_data):
        raw_password = validated_data.pop("password", "")
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        if raw_password:
            instance.set_password(raw_password)
            instance.must_change_password = True
        instance.save()
        return instance


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "document_number",
            "role", "role_name", "is_active", "two_factor_enabled",
            "email_verified", "last_login", "status_display",
        ]

    def get_status_display(self, obj):
        if obj.is_locked:
            return "BLOQUEADO"
        return "ACTIVO" if obj.is_active else "INACTIVO"


class UserModulePermissionSerializer(serializers.ModelSerializer):
    module_code = serializers.CharField(source="module.code", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = UserModulePermission
        fields = ["id", "user", "user_name", "module", "module_code", "action", "granted", "reason"]

    def validate_action(self, value):
        if value not in ACTIONS:
            raise serializers.ValidationError(f"Accion invalida. Permitidas: {', '.join(ACTIONS)}")
        return value


class CredentialCertificateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    role_name = serializers.CharField(source="user.role.name", read_only=True)

    class Meta:
        model = UserCredentialCertificate
        fields = [
            "id", "user", "user_name", "user_email", "username", "role_name",
            "plain_password", "delivered", "delivered_at", "notes", "created_at",
        ]
        read_only_fields = ["plain_password", "created_at"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "La contrasena actual no es correcta."})
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Las contrasenas no coinciden."})
        validate_password(attrs["new_password"], user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save()
        return user


def registry_tree():
    """Estructura del registro de modulos para la matriz de permisos."""
    tree = []
    for module in MODULE_REGISTRY:
        tree.append(
            {
                "code": module["code"],
                "name": module["name"],
                "icon": module.get("icon", "circle"),
                "group": module.get("group", "Principal"),
                "children": [{"code": child["code"], "name": child["name"]} for child in module.get("children", [])],
            }
        )
    return tree
