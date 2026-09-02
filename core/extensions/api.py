"""API REST del modulo de extensiones."""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet
from core.authentication.utils import get_client_ip

from .models import FormDefinition, FormField, FormSubmission, VirtualSpace
from .serializers import (
    FormDefinitionSerializer,
    FormFieldSerializer,
    FormSubmissionSerializer,
    VirtualSpaceSerializer,
)


class FormDefinitionViewSet(BaseModelViewSet):
    module_code = "extensions.forms"
    queryset = FormDefinition.objects.select_related("institution").prefetch_related("fields").all()
    serializer_class = FormDefinitionSerializer
    search_fields = ["title", "slug", "description"]
    filterset_fields = ["institution", "status", "audience"]
    export_filename = "formularios"

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        form = self.get_object()
        form.status = "PUBLICADO"
        form.save(update_fields=["status"])
        return Response({"success": True, "url": f"/extensiones/f/{form.slug}/"})

    @action(detail=True, methods=["get"], url_path="submissions")
    def submissions(self, request, pk=None):
        form = self.get_object()
        queryset = form.submissions.select_related("user").order_by("-submitted_at")
        return Response({"results": FormSubmissionSerializer(queryset, many=True).data})


class FormFieldViewSet(BaseModelViewSet):
    module_code = "extensions.forms"
    queryset = FormField.objects.select_related("form").all()
    serializer_class = FormFieldSerializer
    filterset_fields = ["form", "field_type", "required"]
    export_filename = "campos_formulario"


class FormSubmissionViewSet(BaseModelViewSet):
    module_code = "extensions.forms"
    queryset = FormSubmission.objects.select_related("form", "user", "reviewed_by").all()
    serializer_class = FormSubmissionSerializer
    filterset_fields = ["form", "reviewed"]
    export_filename = "respuestas_formularios"

    def perform_create(self, serializer):
        instance = serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            ip_address=get_client_ip(self.request),
            submitted_at=timezone.now(),
        )
        FormDefinition.objects.filter(pk=instance.form_id).update(
            submissions_count=instance.form.submissions.count()
        )
        return instance

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        submission = self.get_object()
        submission.reviewed = True
        submission.reviewed_by = request.user
        submission.notes = request.data.get("notes", submission.notes)
        submission.save(update_fields=["reviewed", "reviewed_by", "notes"])
        return Response({"success": True})


class VirtualSpaceViewSet(BaseModelViewSet):
    module_code = "extensions.spaces"
    queryset = VirtualSpace.objects.select_related("institution").all()
    serializer_class = VirtualSpaceSerializer
    search_fields = ["name", "description", "url"]
    filterset_fields = ["institution", "kind", "audience", "is_active"]
    export_filename = "espacios_virtuales"

    @action(detail=True, methods=["post"], url_path="register-click")
    def register_click(self, request, pk=None):
        space = self.get_object()
        space.clicks += 1
        space.save(update_fields=["clicks"])
        return Response({"success": True, "clicks": space.clicks})


ROUTES = [
    ("forms", FormDefinitionViewSet, "formdefinition"),
    ("form-fields", FormFieldViewSet, "formfield"),
    ("form-submissions", FormSubmissionViewSet, "formsubmission"),
    ("virtual-spaces", VirtualSpaceViewSet, "virtualspace"),
]
