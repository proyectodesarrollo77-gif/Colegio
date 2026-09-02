from django.contrib import admin

from .models import Emphasis, EmphasisEnrollment, EmphasisGroup


@admin.register(Emphasis)
class EmphasisAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "is_active")
    list_filter = ("kind", "is_active")


@admin.register(EmphasisGroup)
class EmphasisGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "emphasis", "school_year", "teacher", "capacity", "status")
    list_filter = ("school_year", "status", "emphasis")
    filter_horizontal = ("grades",)


admin.site.register(EmphasisEnrollment)
