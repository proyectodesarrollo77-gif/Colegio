from django.contrib import admin

from .models import GradeDecimalConfig, ReportHeader, SystemParameter


@admin.register(ReportHeader)
class ReportHeaderAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "paper_size", "orientation", "is_default", "is_active")
    list_filter = ("institution", "is_default")


@admin.register(GradeDecimalConfig)
class GradeDecimalConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year", "decimals", "rounding_mode", "passing_grade", "is_default")
    list_filter = ("school_year", "rounding_mode")


@admin.register(SystemParameter)
class SystemParameterAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "value", "value_type", "group", "is_editable")
    list_filter = ("group", "value_type")
    search_fields = ("key", "label")
