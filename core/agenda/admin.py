from django.contrib import admin

from .models import AgendaActivity, AgendaEvent, Circular


@admin.register(AgendaEvent)
class AgendaEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "start_at", "audience", "is_published")
    list_filter = ("event_type", "audience", "is_published")
    search_fields = ("title", "description")
    filter_horizontal = ("groups",)


@admin.register(Circular)
class CircularAdmin(admin.ModelAdmin):
    list_display = ("number", "subject", "audience", "status", "sent_at", "recipients_count")
    list_filter = ("status", "audience")
    filter_horizontal = ("groups",)


admin.site.register(AgendaActivity)
