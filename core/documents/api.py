"""API REST de documentos institucionales."""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from config.viewsets import BaseModelViewSet

from .models import DocumentIssue, DocumentTemplate
from .serializers import DocumentIssueSerializer, DocumentTemplateSerializer


class DocumentTemplateViewSet(BaseModelViewSet):
    module_code = "documents.configuration"
    queryset = DocumentTemplate.objects.select_related("institution", "header").all()
    serializer_class = DocumentTemplateSerializer
    search_fields = ["code", "name", "body"]
    filterset_fields = ["institution", "kind", "is_active"]
    export_filename = "plantillas_documentos"

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        template = self.get_object()
        context = request.data.get("context") or {
            "estudiante": "NOMBRE DEL ESTUDIANTE",
            "documento": "TI 1234567890",
            "grado": "Sexto",
            "grupo": "601",
            "ano": str(timezone.localdate().year),
            "institucion": template.institution.name,
            "rector": template.institution.rector_name,
            "ciudad": template.institution.city,
            "fecha": timezone.localdate().strftime("%d/%m/%Y"),
            "consecutivo": f"{template.consecutive_prefix or template.code}-00001",
        }
        return Response({"content": template.render(context)})


class DocumentIssueViewSet(BaseModelViewSet):
    module_code = "documents.printing"
    queryset = DocumentIssue.objects.select_related("template", "student", "teacher", "issued_by").all()
    serializer_class = DocumentIssueSerializer
    search_fields = ["title", "consecutive", "verification_code", "student__first_name", "student__last_name"]
    filterset_fields = ["template", "student", "status"]
    approve_field = "status"
    approve_value = "APROBADO"
    export_filename = "documentos_emitidos"

    def perform_create(self, serializer):
        from core.students.services import certificate_context

        template = serializer.validated_data["template"]
        instance = serializer.save(
            issued_by=self.request.user,
            created_by=self.request.user,
            consecutive=template.build_consecutive(),
        )
        context = dict(instance.context_data or {})
        if instance.student_id:
            fake = type("Stub", (), {"student": instance.student, "consecutive": instance.consecutive, "purpose": ""})()
            context.update(certificate_context(fake))
        instance.content = template.render(context)
        instance.context_data = context
        instance.save(update_fields=["content", "context_data"])
        self.log_action("CREATE", instance)
        return instance

    @action(detail=True, methods=["post"], url_path="register-print")
    def register_print(self, request, pk=None):
        issue = self.get_object()
        issue.print_count += 1
        issue.save(update_fields=["print_count"])
        return Response({"success": True, "print_count": issue.print_count})


ROUTES = [
    ("document-templates", DocumentTemplateViewSet, "documenttemplate"),
    ("document-issues", DocumentIssueViewSet, "documentissue"),
]
