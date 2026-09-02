from django.contrib import admin

from .models import (
    AreaGrade, BilingualEvaluation, GradeSheetLock, ProcessGrade,
    PurposeEvaluation, QualitativeEvaluation, StudentJudgment, SubjectGrade,
)


@admin.register(SubjectGrade)
class SubjectGradeAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "period", "score", "final_score", "performance", "is_passing")
    list_filter = ("period", "subject", "is_passing", "status")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(ProcessGrade)
class ProcessGradeAdmin(admin.ModelAdmin):
    list_display = ("student", "process", "period", "score")
    list_filter = ("period",)
    search_fields = ("student__first_name", "student__last_name")


for model in (AreaGrade, StudentJudgment, QualitativeEvaluation,
              PurposeEvaluation, BilingualEvaluation, GradeSheetLock):
    admin.site.register(model)
