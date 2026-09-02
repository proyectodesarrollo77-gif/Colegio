from django.contrib import admin

from .models import AccessLog, LoginAttempt, SecurityToken, TwoFactorDevice, UserSession


@admin.register(TwoFactorDevice)
class TwoFactorDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "confirmed", "confirmed_at", "last_used_at")
    list_filter = ("confirmed",)
    search_fields = ("user__email", "user__first_name", "user__last_name")


@admin.register(SecurityToken)
class SecurityTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "expires_at", "used_at", "created_at")
    list_filter = ("purpose",)
    search_fields = ("user__email",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identifier", "success", "reason", "ip_address", "created_at")
    list_filter = ("success",)
    search_fields = ("identifier", "ip_address")


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "success", "ip_address", "device", "created_at")
    list_filter = ("event", "success")
    search_fields = ("user__email", "ip_address")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "last_activity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__email", "ip_address")
