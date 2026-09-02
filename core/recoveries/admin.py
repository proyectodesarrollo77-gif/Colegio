from django.contrib import admin

from .models import RecoveryActivity, RecoveryActivitySubmission, RecoveryEnrollment, RecoveryPlan


class ActivityInline(admin.TabularInline):
    model = RecoveryActivity
    extra = 0


@admin.register(RecoveryPlan)
class RecoveryPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "group", "plan_type", "status", "evaluation_date")
    list_filter = ("plan_type", "status", "school_year")
    inlines = [ActivityInline]


@admin.register(RecoveryEnrollment)
class RecoveryEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "plan", "previous_score", "score", "final_score", "status")
    list_filter = ("status", "plan")


admin.site.register(RecoveryActivitySubmission)
