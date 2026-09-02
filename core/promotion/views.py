"""Vistas HTML de promocion y boletines."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from config.permissions import require_permission
from config.resource import ModulePageView, ResourceView, column, field, remote
from core.academic.models import AcademicPeriod, Group, SchoolYear

from .models import FinalReportCard

RESULT_MAP = {
    "PROMOVIDO": {"label": "Promovido", "tone": "success"},
    "PROMOVIDO_COMPROMISO": {"label": "Promovido con compromiso", "tone": "warning"},
    "NO_PROMOVIDO": {"label": "No promovido", "tone": "danger"},
    "PENDIENTE_RECUPERACION": {"label": "Pendiente recuperacion", "tone": "warning"},
    "GRADUADO": {"label": "Graduado", "tone": "brand"},
    "RETIRADO": {"label": "Retirado", "tone": "neutral"},
}


class ClosingView(ModulePageView):
    template_name = "promotion/closing.html"
    module_code = "promotion.closing"
    title = "Cierre Academico"
    subtitle = "Consolide notas, calcule promedios y ejecute el cierre del periodo o del ano."
    icon = "lock"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = SchoolYear.current()
        context.update(
            {
                "school_year": year,
                "years": SchoolYear.objects.order_by("-year")[:10],
                "periods": AcademicPeriod.objects.filter(school_year=year).order_by("number") if year else [],
                "groups": Group.objects.filter(school_year=year).select_related("grade").order_by(
                    "grade__order", "code"
                ) if year else [],
            }
        )
        return context


class PromotionResultView(ResourceView):
    module_code = "promotion.results"
    title = "Promocion Estudiantil"
    subtitle = "Resultados de promocion aprobados por la comision de evaluacion."
    icon = "award"
    endpoint = "/api/promotion-results/"
    allow_create = False
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("group_name", "Grupo", type="badge", tone="brand", width=130),
        column("average", "Promedio", type="grade", width=110, align="center"),
        column("failed_subjects", "Asig. perdidas", type="number", width=130, align="center"),
        column("failed_areas", "Areas perdidas", type="number", width=130, align="center"),
        column("rank", "Puesto", type="number", width=90, align="center"),
        column("result", "Resultado", type="badge", width=200, map=RESULT_MAP),
        column("approved", "Aprobado", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        field("result", "Resultado", type="select", options=[
            {"value": key, "label": value["label"]} for key, value in RESULT_MAP.items()
        ]),
        remote("next_grade", "Grado siguiente", "/api/grades/options/", col="half"),
        field("honor_roll", "Cuadro de honor", type="boolean", col="half"),
        field("observations", "Observaciones de la comision", type="textarea"),
    ]
    filters = [
        {"name": "group", "label": "Grupo", "type": "remote", "endpoint": "/api/groups/options/"},
        {"name": "result", "label": "Resultado", "type": "select", "options": [
            {"value": key, "label": value["label"]} for key, value in RESULT_MAP.items()
        ]},
    ]


class FinalReportView(ResourceView):
    module_code = "promotion.final_reports"
    title = "Boletines Finales"
    subtitle = "Generacion, publicacion e impresion de boletines por grupo."
    icon = "file-text"
    endpoint = "/api/report-cards/"
    template_name = "promotion/report_cards.html"
    allow_create = False
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("group_name", "Grupo", type="badge", tone="brand", width=130),
        column("period_name", "Periodo", width=140),
        column("average", "Promedio", type="grade", width=110, align="center"),
        column("rank", "Puesto", type="number", width=90, align="center"),
        column("total_absences", "Fallas", type="number", width=100, align="center"),
        column("is_final", "Final", type="boolean", width=90, align="center"),
        column("published", "Publicado", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        field("tutor_observation", "Observacion del tutor", type="textarea"),
        field("published", "Publicado", type="boolean", col="half"),
    ]
    row_actions = [
        {"name": "print", "label": "Imprimir boletin", "icon": "printer", "url": "/promocion/boletin/{id}/"},
    ]


def _report_cards(request):
    """
    Boletines visibles para quien consulta.

    Se acotan a la institucion activa: un boletin es un documento de la
    institucion, y sin este filtro bastaba con adivinar el id para imprimir el
    de un estudiante de otra.
    """
    from core.institutions.context import get_active_institution
    from core.institutions.scoping import scope_queryset

    queryset = FinalReportCard.objects.filter(deleted_at__isnull=True)
    return scope_queryset(queryset, get_active_institution(), request.user)


def _print_context(request, card=None):
    from core.configuration.models import ReportHeader
    from core.institutions.models import Institution

    institution = Institution.current()
    return {"institution": institution, "header": ReportHeader.active(institution)}


def report_card_print(request, pk):
    """Boletin de un estudiante, listo para imprimir."""
    require_permission(request.user, "promotion.final_reports", "view")
    card = get_object_or_404(_report_cards(request), pk=pk)

    context = _print_context(request)
    context.update({"card": card, "areas": (card.snapshot or {}).get("areas", [])})
    return render(request, "promotion/report_card_print.html", context)


def report_cards_print(request):
    """
    Boletines de todo un grupo en un solo documento.

    Imprimir uno por uno no es viable con un grupo completo: aqui salen todos
    en el mismo documento, cada boletin en su propia hoja. El filtro es el
    mismo que se usa para generarlos (grupo, periodo y tipo), para que se
    imprima exactamente lo que se genero.
    """
    require_permission(request.user, "promotion.final_reports", "view")

    group = Group.objects.filter(pk=request.GET.get("group") or 0).first()
    if group is None:
        messages.warning(request, "Seleccione un grupo para imprimir sus boletines.")
        return redirect("promotion:final_reports")

    period = AcademicPeriod.objects.filter(pk=request.GET.get("period")).first()
    is_final = request.GET.get("final") in ("1", "true", "True")

    cards = (
        _report_cards(request)
        .filter(group=group, period=period, is_final=is_final)
        .select_related("student", "group", "group__grade", "group__director", "period", "school_year")
        .order_by("student__last_name", "student__first_name")
    )

    context = _print_context(request)
    context.update({
        "group": group,
        "period": period,
        "is_final": is_final,
        "cards": [
            {"card": card, "areas": (card.snapshot or {}).get("areas", [])} for card in cards
        ],
    })
    return render(request, "promotion/report_cards_print.html", context)
