"""Vistas HTML del modulo de elecciones."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote
from core.academic.models import SchoolYear

from .models import Election

ELECTION_OPTIONS = "/api/elections/options/"
CANDIDACY_OPTIONS = "/api/candidacies/options/"
STUDENT_OPTIONS = "/api/students/options/"
YEAR_OPTIONS = "/api/school-years/options/"
GROUP_OPTIONS = "/api/groups/options/"

STATUS_MAP = {
    "CONFIGURACION": {"label": "En configuracion", "tone": "neutral"},
    "INSCRIPCIONES": {"label": "Inscripciones", "tone": "info"},
    "CAMPANA": {"label": "En campana", "tone": "warning"},
    "ABIERTA": {"label": "Votacion abierta", "tone": "success"},
    "CERRADA": {"label": "Votacion cerrada", "tone": "danger"},
    "PUBLICADA": {"label": "Resultados publicados", "tone": "brand"},
}


class ElectionSetupView(ResourceView):
    module_code = "elections.setup"
    title = "Configuracion Electoral"
    subtitle = "Procesos, cargos y candidatos del gobierno escolar."
    icon = "vote"
    endpoint = "/api/elections/"
    columns = [
        column("name", "Proceso electoral", width=260),
        column("school_year_name", "Ano lectivo", width=150),
        column("start_at", "Apertura", type="datetime", width=170),
        column("end_at", "Cierre", type="datetime", width=170),
        column("candidacies_count", "Cargos", type="number", width=100, align="center"),
        column("votes_count", "Votos", type="number", width=100, align="center"),
        column("status", "Estado", type="badge", width=190, map=STATUS_MAP),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        field("status", "Estado", type="select", col="half",
              options=choices_to_options(Election.STATUS_CHOICES)),
        field("name", "Nombre del proceso", required=True),
        field("description", "Descripcion", type="textarea"),
        field("start_at", "Apertura de votacion", type="datetime-local", required=True, col="half"),
        field("end_at", "Cierre de votacion", type="datetime-local", required=True, col="half"),
        field("allow_blank_vote", "Permite voto en blanco", type="boolean", col="half", default=True),
        field("show_live_results", "Mostrar resultados en vivo", type="boolean", col="half"),
        field("require_2fa", "Exigir doble factor", type="boolean", col="half"),
        field("banner", "Imagen del proceso", type="image", col="half"),
    ]
    empty_title = "Sin procesos electorales"
    empty_message = "Configure el proceso de eleccion del gobierno escolar."


class CandidacyView(ResourceView):
    module_code = "elections.setup"
    title = "Cargos Electorales"
    subtitle = "Dignidades a elegir y electores habilitados."
    icon = "list"
    endpoint = "/api/candidacies/"
    columns = [
        column("name", "Cargo", width=240),
        column("election_name", "Proceso", type="badge", tone="brand", width=220),
        column("voter_scope", "Electores", type="badge", tone="info", width=190),
        column("candidates_count", "Candidatos", type="number", width=130, align="center"),
        column("max_selections", "Selecciones", type="number", width=120, align="center"),
    ]
    form_fields = [
        remote("election", "Proceso electoral", ELECTION_OPTIONS, required=True, col="half"),
        field("name", "Nombre del cargo", required=True, col="half"),
        field("voter_scope", "Electores habilitados", type="select", col="half", options=choices_to_options([
            ("TODOS", "Todos los estudiantes"), ("GRADO", "Estudiantes de grados especificos"),
            ("GRUPO", "Estudiantes del grupo"), ("DOCENTES", "Docentes"), ("COMUNIDAD", "Toda la comunidad"),
        ])),
        remote("group", "Grupo", GROUP_OPTIONS, col="half"),
        field("max_selections", "Selecciones permitidas", type="number", col="half", default=1),
        field("order", "Orden", type="number", col="half", default=0),
        field("description", "Descripcion", type="textarea"),
    ]


class CandidateView(ResourceView):
    module_code = "elections.setup"
    title = "Candidatos"
    subtitle = "Inscripcion y aprobacion de candidaturas."
    icon = "user"
    endpoint = "/api/candidates/"
    columns = [
        column("student_name", "Candidato", type="avatar", subfield="slogan"),
        column("number", "N. tarjeton", type="number", width=120, align="center"),
        column("candidacy_name", "Cargo", type="badge", tone="brand", width=200),
        column("group_name", "Grupo", width=120),
        column("votes_count", "Votos", type="number", width=100, align="center"),
        column("is_approved", "Aprobado", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("candidacy", "Cargo", CANDIDACY_OPTIONS, required=True, col="half"),
        remote("student", "Estudiante candidato", STUDENT_OPTIONS, col="half"),
        field("number", "Numero del tarjeton", type="number", required=True, col="half"),
        field("photo", "Fotografia", type="image", col="half"),
        field("slogan", "Lema de campana"),
        field("proposals", "Propuestas", type="textarea", rows=5),
        field("is_approved", "Candidatura aprobada", type="boolean", col="half"),
        field("is_blank_vote", "Opcion de voto en blanco", type="boolean", col="half"),
    ]
    filters = [{"name": "candidacy", "label": "Cargo", "type": "remote", "endpoint": CANDIDACY_OPTIONS}]


class VotingView(ModulePageView):
    template_name = "elections/voting.html"
    module_code = "elections.voting"
    title = "Votacion Digital"
    subtitle = "Ejerza su voto de manera secreta y segura."
    icon = "vote"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = SchoolYear.current()
        context["elections"] = Election.objects.filter(
            school_year=year, deleted_at__isnull=True, status__in=["ABIERTA", "CAMPANA", "PUBLICADA"]
        ).order_by("-start_at")
        return context


class ElectionResultsView(ModulePageView):
    template_name = "elections/results.html"
    module_code = "elections.results"
    title = "Resultados Electorales"
    subtitle = "Escrutinio, porcentajes y dignidades electas."
    icon = "bar-chart"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["elections"] = Election.objects.filter(deleted_at__isnull=True).order_by("-start_at")[:20]
        return context
