from django.contrib import admin

from .models import (
    AcademicPeriod, AcademicProcess, Area, CoexistenceItem, EducationLevel, Grade,
    GradingScale, GradingScaleLevel, Group, Purpose, SchoolYear, Subject,
    ValuationDimension, ValueJudgment,
)


class GradingScaleLevelInline(admin.TabularInline):
    model = GradingScaleLevel
    extra = 0


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "start_date", "end_date", "status", "is_current")
    list_filter = ("status", "is_current")


@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year", "number", "start_date", "end_date", "is_current", "grades_open")
    list_filter = ("school_year", "is_current")


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year", "scale_type", "minimum", "passing", "maximum", "is_default")
    inlines = [GradingScaleLevelInline]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "school_year", "director", "capacity")
    list_filter = ("school_year", "grade")
    search_fields = ("name", "code")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "area", "weekly_hours", "is_bilingual")
    list_filter = ("area", "is_bilingual")
    search_fields = ("name", "code")
    filter_horizontal = ("grades",)


for model in (ValuationDimension, EducationLevel, Grade, Area, AcademicProcess,
              ValueJudgment, CoexistenceItem, Purpose, GradingScaleLevel):
    admin.site.register(model)
