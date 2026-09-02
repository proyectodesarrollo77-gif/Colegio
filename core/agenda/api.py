"""API REST de la agenda virtual."""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import AgendaActivity, AgendaEvent, Circular
from .serializers import AgendaActivitySerializer, AgendaEventSerializer, CircularSerializer


class AgendaEventViewSet(BaseModelViewSet):
    module_code = "agenda.calendar"
    queryset = AgendaEvent.objects.select_related("school_year").prefetch_related("groups").all()
    serializer_class = AgendaEventSerializer
    search_fields = ["title", "description", "place"]
    filterset_fields = ["school_year", "event_type", "audience", "is_published"]
    ordering = ["start_at"]
    export_filename = "agenda_eventos"

    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        """Eventos del mes solicitado, listos para el calendario del frontend."""
        month = int(request.query_params.get("month", timezone.localdate().month))
        year = int(request.query_params.get("year", timezone.localdate().year))
        events = self.filter_queryset(self.get_queryset()).filter(
            start_at__year=year, start_at__month=month, is_published=True
        )
        return Response(
            {
                "year": year,
                "month": month,
                "events": [
                    {
                        "id": event.id,
                        "title": event.title,
                        "day": timezone.localtime(event.start_at).day,
                        "date": timezone.localtime(event.start_at).date().isoformat(),
                        "time": timezone.localtime(event.start_at).strftime("%H:%M"),
                        "type": event.get_event_type_display(),
                        "color": event.color,
                        "place": event.place,
                        "description": event.description,
                        "all_day": event.all_day,
                    }
                    for event in events
                ],
            }
        )

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        if instance.send_notification:
            self._notify(instance)
        return instance

    def _notify(self, event):
        from core.notifications.models import Notification
        from core.users.models import User

        recipients = User.objects.filter(is_active=True, deleted_at__isnull=True)
        role_map = {
            "ESTUDIANTES": "ESTUDIANTE",
            "DOCENTES": "DOCENTE",
            "ACUDIENTES": "ACUDIENTE",
            "DIRECTIVOS": "RECTOR",
        }
        if event.audience in role_map:
            recipients = recipients.filter(role__code=role_map[event.audience])
        Notification.broadcast(
            recipients[:2000],
            title=event.title,
            message=f"{event.get_event_type_display()} - {timezone.localtime(event.start_at):%d/%m/%Y %H:%M}",
            level="info",
            module="agenda.calendar",
            icon="calendar",
        )


class AgendaActivityViewSet(BaseModelViewSet):
    module_code = "agenda.activities"
    queryset = AgendaActivity.objects.select_related(
        "assignment", "assignment__teacher", "group", "subject", "period"
    ).all()
    serializer_class = AgendaActivitySerializer
    search_fields = ["title", "description"]
    filterset_fields = ["group", "subject", "period", "status"]
    ordering = ["-assigned_date"]
    export_filename = "agenda_actividades"


class CircularViewSet(BaseModelViewSet):
    module_code = "agenda.mail"
    queryset = Circular.objects.select_related("school_year").prefetch_related("groups").all()
    serializer_class = CircularSerializer
    search_fields = ["subject", "body", "number"]
    filterset_fields = ["school_year", "audience", "status"]
    export_filename = "circulares"

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        from django.conf import settings
        from django.core.mail import send_mass_mail

        from core.notifications.models import Notification
        from core.users.models import User

        circular = self.get_object()
        recipients = User.objects.filter(is_active=True, deleted_at__isnull=True).exclude(email="")
        role_map = {"ESTUDIANTES": "ESTUDIANTE", "DOCENTES": "DOCENTE", "ACUDIENTES": "ACUDIENTE"}
        if circular.audience in role_map:
            recipients = recipients.filter(role__code=role_map[circular.audience])

        recipients = list(recipients[:3000])
        Notification.broadcast(
            recipients,
            title=circular.subject,
            message=circular.body[:280],
            level="info",
            module="agenda.mail",
            icon="mail",
        )

        if circular.send_email:
            messages = [
                (f"[{settings.PLSGE['NAME']}] {circular.subject}", circular.body,
                 settings.DEFAULT_FROM_EMAIL, [user.email])
                for user in recipients
            ]
            try:
                send_mass_mail(tuple(messages), fail_silently=True)
            except Exception:
                pass

        circular.status = "ENVIADA"
        circular.sent_at = timezone.now()
        circular.recipients_count = len(recipients)
        circular.save(update_fields=["status", "sent_at", "recipients_count"])
        self.log_action("PROCESS", circular)
        return Response({"success": True, "recipients": len(recipients)})


ROUTES = [
    ("agenda-events", AgendaEventViewSet, "agendaevent"),
    ("agenda-activities", AgendaActivityViewSet, "agendaactivity"),
    ("circulars", CircularViewSet, "circular"),
]
