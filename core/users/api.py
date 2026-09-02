"""API REST del modulo de usuarios, roles y permisos."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import ACTION_LABELS, ACTIONS, build_permission_map, invalidate_permission_cache
from config.viewsets import BaseModelViewSet

from .models import Module, Role, RolePermission, User, UserCredentialCertificate, UserModulePermission
from .serializers import (
    CredentialCertificateSerializer,
    ModuleSerializer,
    PermissionMatrixSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    UserListSerializer,
    UserModulePermissionSerializer,
    UserSerializer,
    registry_tree,
)


class RoleViewSet(BaseModelViewSet):
    module_code = "configuration.profiles"
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active", "is_system"]
    ordering = ["order", "name"]
    export_filename = "perfiles"

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "Los perfiles del sistema no pueden eliminarse."})
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="matrix")
    def matrix(self, request, pk=None):
        role = self.get_object()
        stored = {
            permission.module.code: permission.as_dict()
            for permission in RolePermission.objects.filter(role=role).select_related("module")
        }
        return Response(
            {
                "role": RoleSerializer(role).data,
                "actions": [{"key": key, "label": label} for key, label in ACTION_LABELS.items()],
                "modules": registry_tree(),
                "permissions": stored,
            }
        )

    @action(detail=False, methods=["post"], url_path="matrix")
    def save_matrix(self, request):
        serializer = PermissionMatrixSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        invalidate_permission_cache()
        self.log_action("UPDATE", Role.objects.get(code=result["role"]))
        return Response({"success": True, **result})

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, pk=None):
        source = self.get_object()
        code = (request.data.get("code") or f"{source.code}_COPIA").upper()
        if Role.objects.filter(code=code).exists():
            return Response({"detail": "Ya existe un perfil con ese codigo."}, status=status.HTTP_400_BAD_REQUEST)
        clone = Role.objects.create(
            code=code,
            name=request.data.get("name") or f"{source.name} (copia)",
            description=source.description,
            color=source.color,
            order=source.order + 1,
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(
                    role=clone,
                    module=permission.module,
                    can_view=permission.can_view,
                    can_create=permission.can_create,
                    can_edit=permission.can_edit,
                    can_delete=permission.can_delete,
                    can_export=permission.can_export,
                    can_approve=permission.can_approve,
                )
                for permission in RolePermission.objects.filter(role=source)
            ]
        )
        invalidate_permission_cache()
        return Response(RoleSerializer(clone).data, status=status.HTTP_201_CREATED)


class ModuleViewSet(BaseModelViewSet):
    module_code = "configuration.profiles"
    queryset = Module.objects.select_related("parent").all()
    serializer_class = ModuleSerializer
    search_fields = ["code", "name", "group"]
    filterset_fields = ["is_active", "group", "parent"]
    export_filename = "modulos"


class RolePermissionViewSet(BaseModelViewSet):
    module_code = "configuration.profiles"
    queryset = RolePermission.objects.select_related("role", "module").all()
    serializer_class = RolePermissionSerializer
    filterset_fields = ["role", "module"]
    export_filename = "permisos"


class UserViewSet(BaseModelViewSet):
    module_code = "users.management"
    queryset = User.objects.select_related("role", "institution").all()
    serializer_class = UserSerializer
    search_fields = ["first_name", "last_name", "email", "username", "document_number"]
    filterset_fields = ["role", "is_active", "two_factor_enabled", "email_verified", "institution"]
    ordering = ["first_name", "last_name"]
    export_filename = "usuarios"
    export_fields = (
        "username", "email", "first_name", "last_name", "document_type",
        "document_number", "role__name", "is_active", "last_login",
    )

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        role_code = self.request.query_params.get("role_code")
        if role_code:
            queryset = queryset.filter(role__code=role_code)
        return queryset

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        password = User.generate_password()
        user.set_password(password)
        user.must_change_password = True
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save()
        UserCredentialCertificate.objects.create(user=user, plain_password=password, issued_by=request.user)
        self.log_action("UPDATE", user)
        if request.data.get("send_email"):
            from core.authentication.services import send_credentials

            send_credentials(user, password, request)
        return Response({"success": True, "password": password})

    @action(detail=True, methods=["post"], url_path="unlock")
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        self.log_action("UPDATE", user)
        return Response({"success": True, "detail": "Cuenta desbloqueada."})

    @action(detail=True, methods=["post"], url_path="disable-2fa")
    def disable_2fa(self, request, pk=None):
        from core.authentication.services import disable_two_factor

        user = self.get_object()
        disable_two_factor(user)
        self.log_action("UPDATE", user)
        return Response({"success": True, "detail": "Doble factor desactivado."})

    @action(detail=False, methods=["post"], url_path="bulk-create-students")
    def bulk_create_students(self, request):
        """Genera usuarios de acceso para estudiantes matriculados sin usuario."""
        from core.students.models import Student

        role, _ = Role.objects.get_or_create(
            code=Role.ESTUDIANTE, defaults={"name": "Estudiante", "is_system": True, "order": 70}
        )
        group_id = request.data.get("group")
        students = Student.objects.filter(user__isnull=True, deleted_at__isnull=True, status="ACTIVO")
        if group_id:
            students = students.filter(enrollments__group_id=group_id, enrollments__status="ACTIVA")
        created = []
        for student in students.distinct()[:500]:
            email = student.email or f"{student.document_number}@estudiante.local"
            if User.objects.filter(email__iexact=email).exists():
                continue
            password = User.generate_password()
            user = User(
                username=User.build_username(student.first_name, student.last_name, student.document_number),
                email=email,
                first_name=student.first_name,
                last_name=student.last_name,
                document_type=student.document_type,
                document_number=student.document_number,
                role=role,
                institution=student.institution,
                must_change_password=True,
            )
            user.set_password(password)
            user.save()
            student.user = user
            student.save(update_fields=["user"])
            UserCredentialCertificate.objects.create(user=user, plain_password=password, issued_by=request.user)
            created.append({"student": student.full_name, "username": user.username, "password": password})
        return Response({"success": True, "created": len(created), "users": created})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        data = (
            User.objects.filter(deleted_at__isnull=True)
            .values("role__code", "role__name")
            .annotate(total=Count("id"), active=Count("id", filter=Q(is_active=True)))
            .order_by("-total")
        )
        return Response({"results": list(data)})


class UserModulePermissionViewSet(BaseModelViewSet):
    module_code = "configuration.profiles"
    queryset = UserModulePermission.objects.select_related("user", "module").all()
    serializer_class = UserModulePermissionSerializer
    filterset_fields = ["user", "module", "action", "granted"]
    export_filename = "permisos_individuales"


class CredentialCertificateViewSet(BaseModelViewSet):
    module_code = "users.credentials"
    queryset = UserCredentialCertificate.objects.select_related("user", "user__role").all()
    serializer_class = CredentialCertificateSerializer
    search_fields = ["user__first_name", "user__last_name", "user__email", "user__username"]
    filterset_fields = ["delivered", "user"]
    export_filename = "certificados_credenciales"

    @action(detail=True, methods=["post"], url_path="mark-delivered")
    def mark_delivered(self, request, pk=None):
        from django.utils import timezone

        certificate = self.get_object()
        certificate.delivered = True
        certificate.delivered_at = timezone.now()
        certificate.save(update_fields=["delivered", "delivered_at"])
        return Response({"success": True})


class MyPermissionsView(APIView):
    """Devuelve el mapa completo de permisos del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "user": UserListSerializer(request.user).data,
                "role": request.user.role_code,
                "is_super_admin": request.user.is_super_admin,
                "actions": ACTIONS,
                "permissions": build_permission_map(request.user),
            }
        )


ROUTES = [
    ("roles", RoleViewSet, "role"),
    ("modules", ModuleViewSet, "module"),
    ("role-permissions", RolePermissionViewSet, "rolepermission"),
    ("users", UserViewSet, "user"),
    ("user-permissions", UserModulePermissionViewSet, "usermodulepermission"),
    ("credential-certificates", CredentialCertificateViewSet, "credentialcertificate"),
]
