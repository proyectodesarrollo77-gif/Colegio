from django.contrib import admin

from .models import Campus, Institution, InstitutionalCalendar, Shift


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "nature", "calendar", "is_default", "is_active")
    search_fields = ("name", "code", "nit")


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "code", "is_main", "is_active")
    list_filter = ("institution", "is_main")


admin.site.register(Shift)
admin.site.register(InstitutionalCalendar)
