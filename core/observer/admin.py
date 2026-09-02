from django.contrib import admin

from .models import ObservationCategory, ObserverEntry, ObserverFollowUp


class FollowUpInline(admin.TabularInline):
    model = ObserverFollowUp
    extra = 0


@admin.register(ObserverEntry)
class ObserverEntryAdmin(admin.ModelAdmin):
    list_display = ("student", "category", "date", "status", "guardian_notified")
    list_filter = ("category", "status", "school_year")
    search_fields = ("student__first_name", "student__last_name", "description")
    inlines = [FollowUpInline]


admin.site.register(ObservationCategory)
