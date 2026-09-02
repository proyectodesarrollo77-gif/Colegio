from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Module, Role, RolePermission, User, UserCredentialCertificate, UserModulePermission, UserPreference


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system", "is_active", "order")
    list_filter = ("is_system", "is_active")
    search_fields = ("code", "name")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "group", "order", "is_active")
    list_filter = ("group", "is_active")
    search_fields = ("code", "name")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "module", "can_view", "can_create", "can_edit", "can_delete", "can_export", "can_approve")
    list_filter = ("role", "can_view")
    search_fields = ("role__code", "module__code")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("first_name", "last_name")
    list_display = ("email", "username", "get_full_name", "role", "is_active", "two_factor_enabled", "last_login")
    list_filter = ("role", "is_active", "is_staff", "two_factor_enabled")
    search_fields = ("email", "username", "first_name", "last_name", "document_number")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "document_type", "document_number",
                                         "gender", "birth_date", "phone", "mobile", "address", "city", "photo")}),
        ("Perfil y acceso", {"fields": ("role", "institution", "is_active", "is_staff", "is_superuser",
                                        "email_verified", "must_change_password", "two_factor_enabled",
                                        "two_factor_enforced", "theme")}),
        ("Permisos Django", {"classes": ("collapse",), "fields": ("groups", "user_permissions")}),
        ("Auditoria", {"classes": ("collapse",), "fields": ("last_login", "last_login_ip", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_login", "last_login_ip", "created_at", "updated_at")
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email", "username", "first_name", "last_name", "role", "password1", "password2")}),
    )


admin.site.register(UserModulePermission)
admin.site.register(UserPreference)
admin.site.register(UserCredentialCertificate)

admin.site.site_header = "PL_SGE - Administracion"
admin.site.site_title = "PL_SGE"
admin.site.index_title = "Panel de administracion tecnica"
