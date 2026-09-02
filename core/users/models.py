"""
Modelo de usuarios, roles, modulos y matriz de permisos de PL_SGE.
"""
from __future__ import annotations

import secrets
import string

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from config.models_base import BaseModel, TimeStampedModel

DOCUMENT_TYPES = [
    ("TI", "Tarjeta de Identidad"),
    ("CC", "Cedula de Ciudadania"),
    ("CE", "Cedula de Extranjeria"),
    ("RC", "Registro Civil"),
    ("PA", "Pasaporte"),
    ("NUIP", "NUIP"),
    ("PEP", "Permiso Especial de Permanencia"),
    ("NES", "Numero Establecido por la Secretaria"),
]

GENDER_CHOICES = [("M", "Masculino"), ("F", "Femenino"), ("O", "Otro"), ("N", "No informa")]


# ---------------------------------------------------------------------------
# Roles y modulos
# ---------------------------------------------------------------------------
class Role(TimeStampedModel):
    SUPER_ADMIN = "SUPER_ADMIN"
    RECTOR = "RECTOR"
    COORDINADOR = "COORDINADOR"
    SECRETARIA = "SECRETARIA"
    DOCENTE = "DOCENTE"
    TUTOR = "TUTOR"
    ESTUDIANTE = "ESTUDIANTE"
    ACUDIENTE = "ACUDIENTE"

    code = models.CharField("Codigo", max_length=40, unique=True)
    name = models.CharField("Nombre", max_length=80)
    description = models.TextField("Descripcion", blank=True)
    color = models.CharField("Color", max_length=20, default="#4F46E5")
    is_system = models.BooleanField("Rol del sistema", default=False)
    is_active = models.BooleanField("Activo", default=True)
    landing_url = models.CharField("Ruta de inicio", max_length=120, default="dashboard:index")
    order = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        db_table = "users_role"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def is_super(self):
        return self.code == self.SUPER_ADMIN


class Module(TimeStampedModel):
    code = models.CharField("Codigo", max_length=80, unique=True)
    name = models.CharField("Nombre", max_length=120)
    parent = models.ForeignKey(
        "self",
        verbose_name="Modulo padre",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    icon = models.CharField("Icono", max_length=48, default="circle")
    url_name = models.CharField("Ruta", max_length=120, blank=True, null=True)
    group = models.CharField("Grupo", max_length=60, default="Principal")
    order = models.PositiveIntegerField("Orden", default=0)
    is_active = models.BooleanField("Activo", default=True)
    show_in_menu = models.BooleanField("Visible en el menu", default=True)

    class Meta:
        db_table = "users_module"
        verbose_name = "Modulo"
        verbose_name_plural = "Modulos"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def resolved_url(self):
        from django.urls import NoReverseMatch, reverse

        if not self.url_name:
            return None
        try:
            return reverse(self.url_name)
        except NoReverseMatch:
            return None


class RolePermission(TimeStampedModel):
    role = models.ForeignKey(Role, verbose_name="Rol", on_delete=models.CASCADE, related_name="permissions")
    module = models.ForeignKey(
        Module, verbose_name="Modulo", on_delete=models.CASCADE, related_name="role_permissions"
    )
    can_view = models.BooleanField("Consultar", default=False)
    can_create = models.BooleanField("Crear", default=False)
    can_edit = models.BooleanField("Editar", default=False)
    can_delete = models.BooleanField("Eliminar", default=False)
    can_export = models.BooleanField("Exportar", default=False)
    can_approve = models.BooleanField("Aprobar", default=False)

    class Meta:
        db_table = "users_role_permission"
        verbose_name = "Permiso de rol"
        verbose_name_plural = "Permisos por rol"
        unique_together = ("role", "module")
        ordering = ["role__order", "module__order"]

    def __str__(self):
        return f"{self.role.code} / {self.module.code}"

    def as_dict(self):
        return {
            "view": self.can_view,
            "create": self.can_create,
            "edit": self.can_edit,
            "delete": self.can_delete,
            "export": self.can_export,
            "approve": self.can_approve,
        }


class UserModulePermission(TimeStampedModel):
    """Excepcion individual: concede o revoca una accion puntual a un usuario."""

    user = models.ForeignKey(
        "users.User", verbose_name="Usuario", on_delete=models.CASCADE, related_name="module_permissions"
    )
    module = models.ForeignKey(Module, verbose_name="Modulo", on_delete=models.CASCADE)
    action = models.CharField("Accion", max_length=20)
    granted = models.BooleanField("Concedido", default=True)
    reason = models.CharField("Motivo", max_length=240, blank=True)

    class Meta:
        db_table = "users_user_module_permission"
        verbose_name = "Permiso individual"
        verbose_name_plural = "Permisos individuales"
        unique_together = ("user", "module", "action")

    def __str__(self):
        return f"{self.user} / {self.module.code} / {self.action}"


# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El correo electronico es obligatorio.")
        email = self.normalize_email(email).lower()
        username = extra_fields.pop("username", None) or email.split("@")[0]
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.last_password_change = timezone.now()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        role, _ = Role.objects.get_or_create(
            code=Role.SUPER_ADMIN,
            defaults={"name": "Super Administrador", "is_system": True, "order": 1},
        )
        extra_fields.setdefault("role", role)
        return self._create_user(email, password, **extra_fields)

    def active(self):
        return self.filter(is_active=True, deleted_at__isnull=True)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = models.CharField("Usuario", max_length=150, unique=True)
    email = models.EmailField("Correo electronico", unique=True)
    first_name = models.CharField("Nombres", max_length=120)
    last_name = models.CharField("Apellidos", max_length=120, blank=True)

    document_type = models.CharField("Tipo de documento", max_length=8, choices=DOCUMENT_TYPES, default="CC")
    document_number = models.CharField("Numero de documento", max_length=32, blank=True, db_index=True)
    gender = models.CharField("Genero", max_length=1, choices=GENDER_CHOICES, default="N")
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    mobile = models.CharField("Celular", max_length=32, blank=True)
    address = models.CharField("Direccion", max_length=240, blank=True)
    city = models.CharField("Ciudad", max_length=120, blank=True)
    photo = models.ImageField("Fotografia", upload_to="users/photos/", null=True, blank=True)

    role = models.ForeignKey(
        Role, verbose_name="Perfil", null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        verbose_name="Institucion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    is_staff = models.BooleanField("Acceso al admin", default=False)
    email_verified = models.BooleanField("Correo verificado", default=False)
    must_change_password = models.BooleanField("Debe cambiar la contrasena", default=False)
    two_factor_enabled = models.BooleanField("2FA activo", default=False)
    two_factor_enforced = models.BooleanField("2FA obligatorio", default=False)

    last_password_change = models.DateTimeField("Ultimo cambio de contrasena", null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField("Intentos fallidos", default=0)
    locked_until = models.DateTimeField("Bloqueado hasta", null=True, blank=True)
    last_login_ip = models.GenericIPAddressField("Ultima IP", null=True, blank=True)
    theme = models.CharField(
        "Tema", max_length=10, choices=[("light", "Claro"), ("dark", "Oscuro"), ("auto", "Sistema")], default="light"
    )
    notes = models.TextField("Observaciones", blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name"]

    class Meta:
        db_table = "users_user"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["first_name", "last_name"]
        default_manager_name = "objects"
        base_manager_name = "objects"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["document_number"]),
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self):
        return self.get_full_name() or self.email

    # -- Datos de presentacion -------------------------------------------
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name.split(" ")[0] if self.first_name else self.username

    @property
    def initials(self):
        parts = [p for p in [self.first_name, self.last_name] if p]
        if not parts:
            return self.email[:2].upper()
        return "".join(p[0] for p in parts)[:2].upper()

    @property
    def role_code(self):
        return self.role.code if self.role_id else ""

    @property
    def role_name(self):
        return self.role.name if self.role_id else "Sin perfil"

    @property
    def is_super_admin(self):
        return self.is_superuser or self.role_code == Role.SUPER_ADMIN

    @property
    def avatar_url(self):
        if self.photo:
            return self.photo.url
        return None

    # -- Seguridad -------------------------------------------------------
    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self, max_attempts=5, lock_minutes=15):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=lock_minutes)
            self.failed_login_attempts = 0
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def register_successful_login(self, ip=None):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = timezone.now()
        self.last_login_ip = ip
        self.save(update_fields=["failed_login_attempts", "locked_until", "last_login", "last_login_ip"])

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.last_password_change = timezone.now()

    def has_module_perm_code(self, module_code, action="view"):
        from config.permissions import user_has_permission

        return user_has_permission(self, module_code, action)

    @staticmethod
    def generate_password(length=10):
        alphabet = string.ascii_letters + string.digits + "*.-#$"
        while True:
            candidate = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(c.islower() for c in candidate)
                and any(c.isupper() for c in candidate)
                and any(c.isdigit() for c in candidate)
            ):
                return candidate

    @staticmethod
    def build_username(first_name, last_name, document=""):
        base = f"{(first_name or '').strip().split(' ')[0]}.{(last_name or '').strip().split(' ')[0]}".lower()
        base = "".join(ch for ch in base if ch.isalnum() or ch == ".")
        base = base or (document or "usuario")
        candidate = base
        index = 1
        while User.objects.filter(username=candidate).exists():
            index += 1
            candidate = f"{base}{index}"
        return candidate


class UserPreference(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    sidebar_collapsed = models.BooleanField("Menu contraido", default=False)
    density = models.CharField(
        "Densidad", max_length=12, choices=[("comfortable", "Comoda"), ("compact", "Compacta")], default="comfortable"
    )
    default_module = models.CharField("Modulo inicial", max_length=80, blank=True)
    email_notifications = models.BooleanField("Notificaciones por correo", default=True)
    push_notifications = models.BooleanField("Notificaciones en plataforma", default=True)
    items_per_page = models.PositiveSmallIntegerField("Registros por pagina", default=25)

    class Meta:
        db_table = "users_preference"
        verbose_name = "Preferencia de usuario"
        verbose_name_plural = "Preferencias de usuario"

    def __str__(self):
        return f"Preferencias de {self.user}"


class UserCredentialCertificate(TimeStampedModel):
    """Certificado imprimible de usuario y contrasena entregado al acudiente."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credential_certificates")
    plain_password = models.CharField("Contrasena entregada", max_length=64)
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_credentials"
    )
    delivered = models.BooleanField("Entregado", default=False)
    delivered_at = models.DateTimeField("Fecha de entrega", null=True, blank=True)
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "users_credential_certificate"
        verbose_name = "Certificado de credenciales"
        verbose_name_plural = "Certificados de credenciales"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Credenciales de {self.user}"
