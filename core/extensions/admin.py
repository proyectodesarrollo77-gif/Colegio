from django.contrib import admin

from .models import FormDefinition, FormField, FormSubmission, VirtualSpace


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "audience", "status", "submissions_count")
    list_filter = ("status", "audience")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [FormFieldInline]


@admin.register(VirtualSpace)
class VirtualSpaceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "audience", "clicks", "is_active")
    list_filter = ("kind", "audience", "is_active")


admin.site.register(FormSubmission)
