"""Vistas HTML del modulo de extensiones."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.resource import ResourceView, choices_to_options, column, field, remote
from core.authentication.utils import get_client_ip

from .models import FormDefinition, FormSubmission


class FormBuilderView(ResourceView):
    module_code = "extensions.forms"
    title = "Formularios"
    subtitle = "Constructor de formularios dinamicos para la comunidad educativa."
    icon = "puzzle"
    endpoint = "/api/forms/"
    columns = [
        column("title", "Formulario", width=260),
        column("slug", "Identificador", type="mono", width=180),
        column("audience_display", "Dirigido a", type="badge", tone="brand", width=190),
        column("submissions_count", "Respuestas", type="number", width=130, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "PUBLICADO": {"label": "Publicado", "tone": "success"},
            "CERRADO": {"label": "Cerrado", "tone": "warning"},
        }),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("slug", "Identificador URL", required=True, col="half", placeholder="matricula-2026"),
        field("title", "Titulo del formulario", required=True),
        field("description", "Descripcion", type="textarea"),
        field("audience", "Dirigido a", type="select", col="half", options=choices_to_options([
            ("PUBLICO", "Publico (sin autenticacion)"), ("ESTUDIANTES", "Estudiantes"),
            ("DOCENTES", "Docentes"), ("ACUDIENTES", "Acudientes"), ("INTERNO", "Usuarios autenticados"),
        ])),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("PUBLICADO", "Publicado"), ("CERRADO", "Cerrado"),
        ])),
        field("opens_at", "Disponible desde", type="datetime-local", col="half"),
        field("closes_at", "Disponible hasta", type="datetime-local", col="half"),
        field("notify_email", "Notificar a", type="email", col="half"),
        field("allow_multiple", "Permite multiples respuestas", type="boolean", col="half"),
        field("success_message", "Mensaje de confirmacion"),
    ]
    row_actions = [{"name": "publish", "label": "Publicar formulario", "icon": "check"}]
    empty_title = "Sin formularios creados"
    empty_message = "Cree formularios de inscripcion, encuestas o solicitudes."


class FormFieldView(ResourceView):
    module_code = "extensions.forms"
    title = "Campos de Formularios"
    subtitle = "Defina los campos que componen cada formulario."
    icon = "list"
    endpoint = "/api/form-fields/"
    columns = [
        column("label", "Etiqueta", width=250),
        column("key", "Clave", type="mono", width=160),
        column("field_type", "Tipo", type="badge", tone="info", width=150),
        column("required", "Obligatorio", type="boolean", width=130, align="center"),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("form", "Formulario", "/api/forms/options/", required=True, col="half"),
        field("key", "Clave", required=True, col="half"),
        field("label", "Etiqueta", required=True),
        field("field_type", "Tipo de campo", type="select", col="half", options=choices_to_options([
            ("text", "Texto corto"), ("textarea", "Texto largo"), ("number", "Numero"),
            ("email", "Correo electronico"), ("date", "Fecha"), ("time", "Hora"),
            ("select", "Lista desplegable"), ("radio", "Opcion unica"), ("checkbox", "Casillas multiples"),
            ("file", "Archivo"), ("rating", "Valoracion 1-5"), ("section", "Titulo de seccion"),
        ])),
        field("width", "Ancho", type="select", col="half", options=choices_to_options([
            ("full", "Completo"), ("half", "Mitad"), ("third", "Un tercio"),
        ])),
        field("placeholder", "Texto de ayuda", col="half"),
        field("help_text", "Descripcion", col="half"),
        field("required", "Obligatorio", type="boolean", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
    ]
    filters = [{"name": "form", "label": "Formulario", "type": "remote", "endpoint": "/api/forms/options/"}]


class VirtualSpaceView(ResourceView):
    module_code = "extensions.spaces"
    title = "Espacios Virtuales"
    subtitle = "Accesos directos a plataformas y recursos institucionales."
    icon = "external"
    endpoint = "/api/virtual-spaces/"
    columns = [
        column("name", "Espacio", width=240),
        column("kind_display", "Tipo", type="badge", tone="brand", width=180),
        column("url", "Enlace", type="truncate", width=280),
        column("audience_display", "Dirigido a", type="badge", tone="info", width=170),
        column("clicks", "Accesos", type="number", width=110, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("kind", "Tipo", type="select", col="half", options=choices_to_options([
            ("VIDEOCONFERENCIA", "Videoconferencia"), ("BIBLIOTECA", "Biblioteca digital"),
            ("PLATAFORMA", "Plataforma externa"), ("REPOSITORIO", "Repositorio"),
            ("APLICACION", "Aplicacion institucional"),
        ])),
        field("name", "Nombre", required=True),
        field("url", "Enlace", required=True),
        field("description", "Descripcion", type="textarea"),
        field("icon", "Icono", col="third", default="external"),
        field("color", "Color", type="color", col="third", default="#0EA5E9"),
        field("order", "Orden", type="number", col="third", default=0),
        field("audience", "Dirigido a", type="select", col="half", options=choices_to_options([
            ("TODOS", "Toda la comunidad"), ("ESTUDIANTES", "Estudiantes"),
            ("DOCENTES", "Docentes"), ("ACUDIENTES", "Acudientes"),
        ])),
        field("open_in_new_tab", "Abrir en nueva pestana", type="boolean", col="half", default=True),
    ]
    empty_title = "Sin espacios virtuales"
    empty_message = "Publique accesos a plataformas externas y recursos institucionales."


def public_form(request, slug):
    """Formulario dinamico publico o interno."""
    form = get_object_or_404(FormDefinition, slug=slug, deleted_at__isnull=True)
    context = {
        "form": form,
        "fields": form.fields.filter(deleted_at__isnull=True).order_by("order"),
    }

    if not form.is_open:
        context["closed"] = True
        return render(request, "extensions/public_form.html", context)

    if form.audience != "PUBLICO" and not request.user.is_authenticated:
        return redirect(f"/auth/login/?next=/extensiones/f/{slug}/")

    if request.method == "POST":
        data = {}
        for field_definition in context["fields"]:
            if field_definition.field_type == "section":
                continue
            if field_definition.field_type == "checkbox":
                data[field_definition.key] = request.POST.getlist(field_definition.key)
            else:
                data[field_definition.key] = request.POST.get(field_definition.key, "")
        FormSubmission.objects.create(
            form=form,
            user=request.user if request.user.is_authenticated else None,
            data=data,
            ip_address=get_client_ip(request),
            submitted_at=timezone.now(),
        )
        FormDefinition.objects.filter(pk=form.pk).update(submissions_count=form.submissions.count())
        messages.success(request, form.success_message)
        context["submitted"] = True

    return render(request, "extensions/public_form.html", context)
