from django.contrib import admin

from .models import ActivitySubmission, Course, CourseActivity, CourseMaterial, CourseProgress, CourseUnit


class UnitInline(admin.TabularInline):
    model = CourseUnit
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "group", "teacher", "status")
    list_filter = ("school_year", "status", "group")
    search_fields = ("title", "subject__name")
    inlines = [UnitInline]


@admin.register(CourseActivity)
class CourseActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "kind", "due_at", "status")
    list_filter = ("kind", "status")


admin.site.register(CourseMaterial)
admin.site.register(ActivitySubmission)
admin.site.register(CourseProgress)
