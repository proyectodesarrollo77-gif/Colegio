"""Vistas HTML de documentos institucionales."""
from __future__ import annotations

from django.shortcuts import get_object_or_404, render

from config.permissions import require_permission
from config.resource import ResourceView, choices_to_options, column, field, remote

from .models import DocumentIssue, DocumentTemplate

TEMPLATE_OPTIONS = "/api/document-templates/options/"
STUDENT_OPTIONS = "/api/students/options/"


class DocumentConfigurationView(ResourceView):
    module_code = "documents.configuration"
    title = "Configuracion Documental"
    subtitle = "Plantillas de certificados, actas y constancias con variables dinamicas."
    icon = "settings"
    endpoint = "/api/document-templates/"
    template_name = "documents/configuration.html"
    columns = [
        column("code", "Codigo", type="mono", width=120),
        column("name", "Documento", width=260),
        column("kind_display", "Tipo", type="badge", tone="brand", width=160),
        column("paper_size", "Papel", type="badge", tone="neutral", width=100),
        column("next_consecutive", "Consecutivo", type="number", width=130, align="center"),
        column("issues_count", "Emitidos", type="number", width=110, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        remote("header", "Encabezado de reportes", "/api/report-headers/options/", col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("kind", "Tipo de documento", type="select", col="half",
              options=choices_to_options(DocumentTemplate.KIND_CHOICES)),
        field("name", "Nombre del documento", required=True),
        field("body", "Cuerpo del documento", type="textarea", rows=10,
              hint="Variables: {{estudiante}} {{documento}} {{grado}} {{grupo}} {{ano}} {{fecha}} "
                   "{{institucion}} {{rector}} {{ciudad}} {{consecutivo}} {{acudiente}}"),
        field("footer", "Pie del documento", type="textarea", rows=3),
        field("paper_size", "Tamano", type="select", col="third", options=choices_to_options([
            ("LETTER", "Carta"), ("A4", "A4"), ("LEGAL", "Oficio"),
        ])),
        field("orientation", "Orientacion", type="select", col="third", options=choices_to_options([
            ("P", "Vertical"), ("L", "Horizontal"),
        ])),
        field("consecutive_prefix", "Prefijo del consecutivo", col="third"),
        field("requires_consecutive", "Usa consecutivo", type="boolean", col="third", default=True),
        field("requires_approval", "Requiere aprobacion", type="boolean", col="third"),
        field("show_qr", "Incluir codigo QR", type="boolean", col="third", default=True),
    ]
    empty_title = "Sin plantillas configuradas"
    empty_message = "Cree plantillas para emitir certificados, actas y constancias."


class DocumentPrintingView(ResourceView):
    module_code = "documents.printing"
    title = "Impresion de Documentos"
    subtitle = "Emision, consulta e impresion de documentos institucionales."
    icon = "printer"
    endpoint = "/api/document-issues/"
    columns = [
        column("consecutive", "Consecutivo", type="mono", width=150),
        column("title", "Documento", width=250),
        column("template_name", "Plantilla", type="badge", tone="brand", width=190),
        column("student_name", "Estudiante", width=190),
        column("issued_at", "Emision", type="datetime", width=160),
        column("status", "Estado", type="badge", width=130, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "EMITIDO": {"label": "Emitido", "tone": "info"},
            "APROBADO": {"label": "Aprobado", "tone": "success"},
            "ANULADO": {"label": "Anulado", "tone": "danger"},
        }),
        column("print_count", "Impresiones", type="number", width=120, align="center"),
    ]
    form_fields = [
        remote("template", "Plantilla", TEMPLATE_OPTIONS, required=True, col="half"),
        remote("student", "Estudiante", STUDENT_OPTIONS, col="half"),
        field("title", "Titulo del documento", required=True),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("EMITIDO", "Emitido"),
            ("APROBADO", "Aprobado"), ("ANULADO", "Anulado"),
        ])),
    ]
    row_actions = [
        {"name": "print", "label": "Imprimir", "icon": "printer", "url": "/documentos/{id}/imprimir/"},
    ]


def document_print(request, pk):
    require_permission(request.user, "documents.printing", "view")
    issue = get_object_or_404(DocumentIssue, pk=pk)
    issue.print_count += 1
    issue.save(update_fields=["print_count"])
    from core.institutions.models import Institution

    institution = Institution.current()
    return render(
        request,
        "documents/document_print.html",
        {
            "issue": issue,
            "institution": institution,
            "header": issue.template.header,
        },
    )
