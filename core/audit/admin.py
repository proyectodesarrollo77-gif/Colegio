from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user_label", "action", "module", "object_label", "ip_address")
    list_filter = ("action", "module")
    search_fields = ("user_label", "object_label", "description", "ip_address")
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
