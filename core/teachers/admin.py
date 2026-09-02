from django.contrib import admin

from .models import ScheduleSlot, Teacher, TeacherAbsence, TeacherAcademicProcess, TeachingAssignment


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("teacher_code", "last_name", "first_name", "document_number", "contract_type", "status")
    list_filter = ("status", "contract_type", "is_tutor", "is_coordinator")
    search_fields = ("first_name", "last_name", "document_number", "teacher_code")
    readonly_fields = ("teacher_code", "uuid")


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "subject", "group", "school_year", "weekly_hours", "is_main")
    list_filter = ("school_year", "group", "subject")
    search_fields = ("teacher__first_name", "teacher__last_name", "subject__name")


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ("assignment", "weekday", "block", "start_time", "end_time", "classroom")
    list_filter = ("weekday",)


admin.site.register(TeacherAcademicProcess)
admin.site.register(TeacherAbsence)
