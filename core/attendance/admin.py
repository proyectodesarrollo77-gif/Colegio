from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession, AttendanceSummary


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "date", "block", "period", "is_closed")
    list_filter = ("period", "is_closed", "date")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "status", "minutes_late")
    list_filter = ("status",)
    search_fields = ("student__first_name", "student__last_name")


admin.site.register(AttendanceSummary)
