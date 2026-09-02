from django.contrib import admin

from .models import (
    Admission, Enrollment, Guardian, Inscription, Student,
    StudentCertificate, StudentDocument, StudentGuardian,
)


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 0
    autocomplete_fields = ("guardian",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_code", "last_name", "first_name", "document_number", "status")
    list_filter = ("status", "gender", "institution")
    search_fields = ("first_name", "last_name", "document_number", "student_code")
    inlines = [StudentGuardianInline]
    readonly_fields = ("student_code", "uuid")


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "document_number", "relation", "mobile")
    search_fields = ("first_name", "last_name", "document_number")
    list_filter = ("relation",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_number", "student", "group", "school_year", "status")
    list_filter = ("school_year", "status", "group")
    search_fields = ("student__first_name", "student__last_name", "enrollment_number")


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ("applicant_first_name", "applicant_last_name", "grade", "status", "application_date")
    list_filter = ("status", "school_year", "grade")


admin.site.register(Inscription)
admin.site.register(StudentDocument)
admin.site.register(StudentCertificate)
