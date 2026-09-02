from django.contrib import admin

from .models import DashboardIndicator, ReportDefinition, ReportExecution


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "default_output", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name")


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ("definition", "executed_by", "output_format", "status", "rows", "executed_at")
    list_filter = ("status", "output_format")


admin.site.register(DashboardIndicator)
