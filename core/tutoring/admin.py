from django.contrib import admin

from .models import CoexistenceEvaluation, ReportCardBlock, Tutor, TutoringJudgment, TutoringMeeting


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ("teacher", "group", "school_year", "is_main")
    list_filter = ("school_year", "is_main")


@admin.register(ReportCardBlock)
class ReportCardBlockAdmin(admin.ModelAdmin):
    list_display = ("student", "reason", "amount", "blocked", "released_at")
    list_filter = ("reason", "blocked")
    search_fields = ("student__first_name", "student__last_name")


admin.site.register(TutoringJudgment)
admin.site.register(CoexistenceEvaluation)
admin.site.register(TutoringMeeting)
