from django.contrib import admin

from .models import DocumentIssue, DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "requires_consecutive", "next_consecutive", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name")


@admin.register(DocumentIssue)
class DocumentIssueAdmin(admin.ModelAdmin):
    list_display = ("consecutive", "title", "template", "student", "status", "issued_at")
    list_filter = ("status", "template")
    search_fields = ("consecutive", "title", "verification_code")
