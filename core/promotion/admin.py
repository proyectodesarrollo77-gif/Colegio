from django.contrib import admin

from .models import ClosingProcess, EvaluationCommission, FinalReportCard, PromotionResult


@admin.register(PromotionResult)
class PromotionResultAdmin(admin.ModelAdmin):
    list_display = ("student", "group", "average", "failed_subjects", "result", "rank", "approved")
    list_filter = ("school_year", "result", "approved")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(FinalReportCard)
class FinalReportCardAdmin(admin.ModelAdmin):
    list_display = ("student", "group", "period", "average", "is_final", "published")
    list_filter = ("school_year", "is_final", "published")


admin.site.register(ClosingProcess)
admin.site.register(EvaluationCommission)
