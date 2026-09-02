"""Vistas HTML del modulo PAE (reutilizan ResourceView y ModulePageView)."""
from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from config.permissions import require_permission
from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote

from .models import (
    PaeCatalog,
    PaeChecklist,
    PaeContract,
    PaeDelivery,
    PaeDocument,
    PaeMenuCycle,
    PaeVigencia,
)

# --- Endpoints de opciones reutilizados -------------------------------------
VIGENCIA_OPTIONS = "/api/pae/vigencias/options/"
CAMPUS_OPTIONS = "/api/campuses/options/"
SHIFT_OPTIONS = "/api/shifts/options/"
GRADE_OPTIONS = "/api/grades/options/"
GROUP_OPTIONS = "/api/groups/options/"
STUDENT_OPTIONS = "/api/students/options/"
ENROLLMENT_OPTIONS = "/api/enrollments/options/"
USER_OPTIONS = "/api/users/options/"
INSTITUTION_OPTIONS = "/api/institutions/options/"
SCHOOL_YEAR_OPTIONS = "/api/school-years/options/"

MODALITY_OPTIONS = "/api/pae/modalidades/options/"
COMPLEMENT_OPTIONS = "/api/pae/tipos-complemento/options/"
OPERATOR_OPTIONS = "/api/pae/operadores/options/"
CONTRACT_OPTIONS = "/api/pae/contratos/options/"
PLAN_OPTIONS = "/api/pae/planes/options/"
MENU_CYCLE_OPTIONS = "/api/pae/menus/options/"
MENU_DAY_OPTIONS = "/api/pae/menu-dias/options/"
PREPARATION_OPTIONS = "/api/pae/menu-preparaciones/options/"
CHECKLIST_OPTIONS = "/api/pae/listas-verificacion/options/"
VISIT_OPTIONS = "/api/pae/visitas/options/"
FINDING_OPTIONS = "/api/pae/hallazgos/options/"
INCIDENT_OPTIONS = "/api/pae/novedades/options/"
MEETING_OPTIONS = "/api/pae/participacion/options/"
NORMATIVE_OPTIONS = "/api/pae/normativa/options/"


def catalog_options(catalog_type):
    return f"/api/pae/catalogos/options/?catalog_type={catalog_type}"


CONDITION_MAP = {
    "OPTIMA": {"label": "Optima", "tone": "success"},
    "ACEPTABLE": {"label": "Aceptable", "tone": "info"},
    "DEFICIENTE": {"label": "Deficiente", "tone": "danger"},
    "NO_EXISTE": {"label": "No existe", "tone": "danger"},
    "NO_APLICA": {"label": "No aplica", "tone": "neutral"},
}
RESULT_MAP = {
    "CUMPLE": {"label": "Cumple", "tone": "success"},
    "CUMPLE_PARCIAL": {"label": "Cumple parcialmente", "tone": "warning"},
    "NO_CUMPLE": {"label": "No cumple", "tone": "danger"},
    "SIN_EVALUAR": {"label": "Sin evaluar", "tone": "neutral"},
}
PRIORITY_MAP = {
    "BAJA": {"label": "Baja", "tone": "neutral"},
    "MEDIA": {"label": "Media", "tone": "info"},
    "ALTA": {"label": "Alta", "tone": "warning"},
    "CRITICA": {"label": "Critica", "tone": "danger"},
}


class PaeContextMixin:
    """Inyecta la vigencia vigente y el aviso normativo en todas las paginas PAE."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vigencia = PaeVigencia.current()
        context["pae_vigencia"] = vigencia
        context["pae_vigencias"] = PaeVigencia.objects.filter(deleted_at__isnull=True).order_by("-start_date")[:10]
        context["pae_normative"] = vigencia.normative if vigencia and vigencia.normative_id else None
        return context


class PaeResourceView(PaeContextMixin, ResourceView):
    """Pagina CRUD del modulo PAE."""

    template_name = "pae/resource.html"


class PaePageView(PaeContextMixin, ModulePageView):
    """Pagina especializada del modulo PAE."""


# ===========================================================================
# 1. DASHBOARD
# ===========================================================================
class PaeDashboardView(PaePageView):
    template_name = "pae/dashboard.html"
    module_code = "pae.dashboard"
    title = "Dashboard PAE"
    subtitle = "Cobertura, cumplimiento, novedades y alertas del Programa de Alimentacion Escolar."
    icon = "utensils"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.institutions.models import Campus, Shift

        from .models import PaeOperator

        context.update({
            "campuses": Campus.objects.filter(deleted_at__isnull=True).order_by("name"),
            "shifts": Shift.objects.filter(deleted_at__isnull=True).order_by("order"),
            "operators": PaeOperator.objects.filter(deleted_at__isnull=True, status="ACTIVO").order_by("business_name"),
        })
        return context


# ===========================================================================
# 2. CONFIGURACION
# ===========================================================================
class PaeConfigurationView(PaePageView):
    template_name = "pae/configuration.html"
    module_code = "pae.configuracion"
    title = "Configuracion del PAE"
    subtitle = "Vigencias, normativa aplicable, modalidades, complementos y catalogos parametrizables."
    icon = "settings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PaeComplementType, PaeModality, PaeNormative

        context.update({
            "catalog_types": PaeCatalog.TYPE_CHOICES,
            "catalog_counts": {
                row["catalog_type"]: row["total"]
                for row in PaeCatalog.objects.filter(deleted_at__isnull=True)
                .values("catalog_type").annotate(total=Count("id"))
            },
            "normatives": PaeNormative.objects.filter(deleted_at__isnull=True).order_by("-effective_from")[:6],
            "modalities_count": PaeModality.objects.filter(deleted_at__isnull=True).count(),
            "complements_count": PaeComplementType.objects.filter(deleted_at__isnull=True).count(),
        })
        return context


class PaeVigenciaView(PaeResourceView):
    module_code = "pae.configuracion"
    title = "Vigencias del PAE"
    subtitle = "Cada vigencia registra la norma aplicable, el calendario y las metas del programa."
    icon = "calendar"
    endpoint = "/api/pae/vigencias/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Configuracion", "url": "/pae/configuracion/"},
                   {"label": "Vigencias"}]
    columns = [
        column("name", "Vigencia", width=200),
        column("school_year_name", "Ano lectivo", width=160),
        column("normative_code", "Norma aplicable", type="badge", tone="brand", width=170),
        column("start_date", "Inicio", type="date", width=120),
        column("end_date", "Fin", type="date", width=120),
        column("beneficiaries_count", "Beneficiarios", type="number", width=130, align="center"),
        column("progress", "Avance", type="percent", width=140),
        column("status", "Estado", type="badge", width=140, map={
            "PLANEACION": {"label": "En planeacion", "tone": "neutral"},
            "ACTIVA": {"label": "Activa", "tone": "success"},
            "CIERRE": {"label": "En cierre", "tone": "warning"},
            "CERRADA": {"label": "Cerrada", "tone": "danger"},
        }),
        column("is_current", "En curso", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", INSTITUTION_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        remote("normative", "Norma aplicable", NORMATIVE_OPTIONS, col="half",
               hint="Resolucion vigente registrada en el modulo de normativa."),
        field("name", "Nombre de la vigencia", col="half", placeholder="PAE 2026"),
        field("start_date", "Fecha inicial", type="date", required=True, col="half"),
        field("end_date", "Fecha final", type="date", required=True, col="half"),
        field("service_days", "Dias de atencion proyectados", type="number", col="half", default=180),
        field("status", "Estado", type="select", col="half", options=choices_to_options(PaeVigencia.STATUS_CHOICES)),
        field("coverage_goal", "Meta de cobertura (%)", type="number", step="0.01", col="half", default=100),
        field("compliance_goal", "Meta de cumplimiento (%)", type="number", step="0.01", col="half", default=95),
        field("is_current", "Vigencia en curso", type="boolean", col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [{"name": "set-current", "label": "Definir como vigencia actual", "icon": "check"}]
    empty_title = "Sin vigencias del PAE"
    empty_message = "Cree la vigencia para habilitar diagnostico, beneficiarios y planeacion."


class PaeNormativeView(PaeResourceView):
    module_code = "pae.configuracion"
    title = "Normativa aplicable"
    subtitle = "Resoluciones y lineamientos que rigen el programa. Los requisitos se parametrizan, no se codifican."
    icon = "book"
    endpoint = "/api/pae/normativa/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Configuracion", "url": "/pae/configuracion/"},
                   {"label": "Normativa"}]
    help_text = ("Registre aqui la resolucion vigente. Los criterios que dependan de la norma se cargan como "
                 "datos en los catalogos y se marcan POR VALIDAR hasta que la institucion confirme el texto oficial.")
    columns = [
        column("code", "Codigo", type="mono", width=140),
        column("name", "Norma", width=280),
        column("issuer", "Entidad", width=200),
        column("issued_on", "Expedicion", type="date", width=130),
        column("effective_from", "Vigente desde", type="date", width=140),
        column("status", "Estado", type="badge", width=140, map={
            "VIGENTE": {"label": "Vigente", "tone": "success"},
            "POR_VALIDAR": {"label": "Por validar", "tone": "warning"},
            "DEROGADO": {"label": "Derogado", "tone": "neutral"},
        }),
    ]
    form_fields = [
        field("code", "Codigo", required=True, col="half", placeholder="RES-0003-2026"),
        field("number", "Numero", col="half"),
        field("name", "Nombre de la norma", required=True),
        field("issuer", "Entidad emisora", col="half", default="UApA - Alimentos para Aprender"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("VIGENTE", "Vigente"), ("POR_VALIDAR", "Por validar"), ("DEROGADO", "Derogado"),
        ])),
        field("issued_on", "Fecha de expedicion", type="date", col="third"),
        field("effective_from", "Vigente desde", type="date", col="third"),
        field("effective_to", "Vigente hasta", type="date", col="third"),
        field("summary", "Resumen", type="textarea", rows=4),
        field("url", "Enlace oficial", col="half"),
        field("file", "Documento", type="file", col="half"),
        field("notes", "Observaciones", type="textarea"),
    ]


class PaeCatalogView(PaeResourceView):
    module_code = "pae.configuracion"
    title = "Catalogos parametrizables"
    subtitle = "Criterios, tipos de novedad, visita, hallazgo, PQRS, documento y demas listas configurables."
    icon = "list"
    endpoint = "/api/pae/catalogos/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Configuracion", "url": "/pae/configuracion/"},
                   {"label": "Catalogos"}]
    help_text = ("Toda lista que la normativa pueda modificar se administra desde aqui. "
                 "Marque como POR VALIDAR los elementos cuyo texto oficial aun no este confirmado.")
    columns = [
        column("type_display", "Catalogo", type="badge", tone="brand", width=210),
        column("code", "Codigo", type="mono", width=170),
        column("name", "Nombre", width=260),
        column("weight", "Peso", type="number", decimals=2, width=100, align="right"),
        column("validation_status", "Estado normativo", type="badge", width=160, map={
            "VIGENTE": {"label": "Vigente", "tone": "success"},
            "POR_VALIDAR": {"label": "Por validar", "tone": "warning"},
            "DEROGADO": {"label": "Derogado", "tone": "neutral"},
        }),
        column("is_active", "Activo", type="boolean", width=90, align="center"),
    ]
    form_fields = [
        field("catalog_type", "Tipo de catalogo", type="select", required=True, col="half",
              options=choices_to_options(PaeCatalog.TYPE_CHOICES)),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre", required=True),
        field("description", "Descripcion", type="textarea"),
        field("weight", "Peso / puntaje", type="number", step="0.01", col="third", default=0),
        field("order", "Orden", type="number", col="third", default=0),
        field("color", "Color", type="color", col="third", default="#4F46E5"),
        remote("normative", "Norma de referencia", NORMATIVE_OPTIONS, col="half"),
        field("validation_status", "Estado normativo", type="select", col="half", options=choices_to_options([
            ("VIGENTE", "Vigente"), ("POR_VALIDAR", "Por validar"), ("DEROGADO", "Derogado"),
        ])),
        field("requires_evidence", "Exige evidencia", type="boolean", col="half"),
        field("requires_action", "Genera accion correctiva", type="boolean", col="half"),
    ]
    filters = [
        {"name": "catalog_type", "label": "Todos los catalogos", "type": "select",
         "options": choices_to_options(PaeCatalog.TYPE_CHOICES)},
        {"name": "validation_status", "label": "Estado normativo", "type": "select", "options": [
            {"value": "VIGENTE", "label": "Vigente"},
            {"value": "POR_VALIDAR", "label": "Por validar"},
            {"value": "DEROGADO", "label": "Derogado"},
        ]},
    ]


class PaeModalityView(PaeResourceView):
    module_code = "pae.configuracion"
    title = "Modalidades de atencion"
    subtitle = "Preparada en sitio, industrializada, racion para preparar en casa u otras definidas por la norma."
    icon = "layers"
    endpoint = "/api/pae/modalidades/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Configuracion", "url": "/pae/configuracion/"},
                   {"label": "Modalidades"}]
    columns = [
        column("code", "Codigo", type="mono", width=130),
        column("name", "Modalidad", width=260),
        column("requires_kitchen", "Cocina", type="boolean", width=100, align="center"),
        column("requires_dining_room", "Comedor", type="boolean", width=110, align="center"),
        column("requires_cold_chain", "Cadena de frio", type="boolean", width=140, align="center"),
        column("beneficiaries_count", "Beneficiarios", type="number", width=130, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", INSTITUTION_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre de la modalidad", required=True),
        field("description", "Descripcion", type="textarea"),
        remote("normative", "Norma", NORMATIVE_OPTIONS, col="half"),
        field("color", "Color", type="color", col="half", default="#0EA5E9"),
        field("requires_kitchen", "Requiere cocina en sitio", type="boolean", col="third", default=True),
        field("requires_dining_room", "Requiere comedor", type="boolean", col="third", default=True),
        field("requires_cold_chain", "Requiere cadena de frio", type="boolean", col="third"),
        field("order", "Orden", type="number", col="half", default=0),
    ]


class PaeComplementTypeView(PaeResourceView):
    module_code = "pae.configuracion"
    title = "Tipos de complemento"
    subtitle = "Complemento de jornada, almuerzo y jornada unica, con su aporte nutricional parametrizable."
    icon = "utensils"
    endpoint = "/api/pae/tipos-complemento/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Configuracion", "url": "/pae/configuracion/"},
                   {"label": "Tipos de complemento"}]
    help_text = "El aporte calorico depende de la norma vigente y del grupo etario: verifique el valor oficial."
    columns = [
        column("code", "Codigo", type="mono", width=130),
        column("name", "Tipo de complemento", width=250),
        column("modality_name", "Modalidad", type="badge", tone="info", width=190),
        column("shift_name", "Jornada", width=130),
        column("calorie_contribution", "Aporte (kcal)", type="number", decimals=2, width=140, align="right"),
        column("energy_percentage", "% requerimiento", type="number", decimals=2, width=150, align="right"),
    ]
    form_fields = [
        remote("institution", "Institucion", INSTITUTION_OPTIONS, required=True, col="half"),
        remote("modality", "Modalidad", MODALITY_OPTIONS, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre", required=True, col="half"),
        remote("shift", "Jornada", SHIFT_OPTIONS, col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("calorie_contribution", "Aporte calorico (kcal)", type="number", step="0.01", col="half",
              hint="Valor parametrizable segun la norma. POR VALIDAR."),
        field("energy_percentage", "Porcentaje del requerimiento diario", type="number", step="0.01", col="half"),
        field("service_start", "Hora de servicio (desde)", type="time", col="half"),
        field("service_end", "Hora de servicio (hasta)", type="time", col="half"),
        field("description", "Descripcion", type="textarea"),
    ]


# ===========================================================================
# 3. DIAGNOSTICO
# ===========================================================================
class PaeDiagnosisView(PaeResourceView):
    module_code = "pae.diagnostico"
    title = "Diagnostico de sedes"
    subtitle = "Infraestructura, cocina, comedor, servicios y capacidad de cada sede por vigencia."
    icon = "clipboard-check"
    endpoint = "/api/pae/diagnosticos/"
    columns = [
        column("campus_name", "Sede", width=220),
        column("vigencia_name", "Vigencia", type="badge", tone="brand", width=150),
        column("diagnosis_date", "Fecha", type="date", width=120),
        column("zone_display", "Zona", type="badge", tone="info", width=140),
        column("kitchen", "Cocina", type="badge", width=130, map=CONDITION_MAP),
        column("dining_room", "Comedor", type="badge", width=130, map=CONDITION_MAP),
        column("max_rations", "Cap. raciones", type="number", width=130, align="center"),
        column("score", "Puntaje", type="percent", width=140),
        column("result", "Resultado", type="badge", width=180, map=RESULT_MAP),
    ]
    form_fields = [
        field("s1", "Identificacion", type="section"),
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        field("diagnosis_date", "Fecha del diagnostico", type="date", col="half"),
        field("zone", "Zona", type="select", col="half", options=choices_to_options([
            ("URBANA", "Urbana"), ("RURAL", "Rural"), ("RURAL_DISPERSA", "Rural dispersa"),
        ])),
        field("s2", "Condiciones evaluadas", type="section",
              hint="Optima / Aceptable / Deficiente / No existe / No aplica"),
        field("infrastructure", "Infraestructura general", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("kitchen", "Cocina", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("dining_room", "Comedor", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("storage", "Bodega", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("refrigeration", "Refrigeracion", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("water", "Suministro de agua", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("energy", "Energia electrica", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("gas", "Gas / combustible", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("equipment", "Equipos y menaje", type="select", col="third",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("sanitary", "Condiciones sanitarias", type="select", col="half",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("accessibility", "Accesibilidad", type="select", col="half",
              options=choices_to_options([(k, v["label"]) for k, v in CONDITION_MAP.items()])),
        field("s3", "Servicios y saneamiento", type="section"),
        field("has_potable_water", "Agua potable disponible", type="boolean", col="third", default=True),
        field("has_handwashing", "Lavamanos disponible", type="boolean", col="third", default=True),
        field("has_waste_management", "Manejo de residuos", type="boolean", col="third", default=True),
        field("has_pest_control", "Control de plagas", type="boolean", col="third"),
        field("has_sanitary_concept", "Concepto sanitario favorable", type="boolean", col="third"),
        field("s4", "Capacidad", type="section"),
        field("dining_capacity", "Capacidad del comedor (puestos)", type="number", col="third", default=0),
        field("max_rations", "Capacidad maxima de raciones", type="number", col="third", default=0),
        field("food_handlers", "Manipuladores de alimentos", type="number", col="third", default=0),
        field("kitchen_area_m2", "Area de cocina (m2)", type="number", step="0.01", col="half", default=0),
        field("storage_area_m2", "Area de bodega (m2)", type="number", step="0.01", col="half", default=0),
        field("territorial_conditions", "Condiciones territoriales", type="textarea"),
        field("observations", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "vigencia", "label": "Vigencia", "type": "remote", "endpoint": VIGENCIA_OPTIONS},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "result", "label": "Resultado", "type": "select",
         "options": [{"value": k, "label": v["label"]} for k, v in RESULT_MAP.items()]},
    ]
    empty_title = "Sin diagnosticos registrados"
    empty_message = "Registre el diagnostico de cada sede para sustentar la priorizacion y la planeacion."


# ===========================================================================
# 4. PRIORIZACION
# ===========================================================================
class PaePrioritizationView(PaeResourceView):
    module_code = "pae.priorizacion"
    title = "Priorizacion"
    subtitle = "Focalizacion de la poblacion a atender por sede, grado y grupo, con criterios y justificacion."
    icon = "target"
    endpoint = "/api/pae/priorizaciones/"
    columns = [
        column("campus_name", "Sede", width=190),
        column("grade_name", "Grado", type="badge", tone="brand", width=140),
        column("group_name", "Grupo", width=120),
        column("population_name", "Poblacion", width=160),
        column("enrolled_students", "Matriculados", type="number", width=130, align="center"),
        column("prioritized_students", "Priorizados", type="number", width=130, align="center"),
        column("coverage", "Cobertura", type="percent", width=150),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "EN_REVISION": {"label": "En revision", "tone": "info"},
            "APROBADA": {"label": "Aprobada", "tone": "success"},
            "RECHAZADA": {"label": "Rechazada", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("grade", "Grado", GRADE_OPTIONS, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, col="half"),
        remote("shift", "Jornada", SHIFT_OPTIONS, col="half"),
        remote("population_type", "Tipo de poblacion", catalog_options(PaeCatalog.TYPE_POPULATION), col="half"),
        field("enrolled_students", "Estudiantes matriculados", type="number", col="third", default=0),
        field("prioritized_students", "Estudiantes priorizados", type="number", col="third", default=0),
        field("score", "Puntaje de priorizacion", type="number", step="0.01", col="third", default=0),
        field("registered_on", "Fecha de registro", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("EN_REVISION", "En revision"),
            ("APROBADA", "Aprobada"), ("RECHAZADA", "Rechazada"),
        ])),
        field("justification", "Justificacion", type="textarea", rows=4),
    ]
    row_actions = [{"name": "enroll-beneficiaries", "label": "Vincular beneficiarios", "icon": "users"}]
    filters = [
        {"name": "vigencia", "label": "Vigencia", "type": "remote", "endpoint": VIGENCIA_OPTIONS},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
    ]
    empty_title = "Sin priorizaciones registradas"
    empty_message = "Registre la focalizacion por sede y grado antes de vincular beneficiarios."


# ===========================================================================
# 5. BENEFICIARIOS
# ===========================================================================
class PaeBeneficiaryView(PaeResourceView):
    module_code = "pae.beneficiarios"
    title = "Beneficiarios del PAE"
    subtitle = "Estudiantes matriculados vinculados al programa. La informacion personal proviene del modulo de estudiantes."
    icon = "users"
    template_name = "pae/beneficiaries.html"
    endpoint = "/api/pae/beneficiarios/"
    help_text = ("Los beneficiarios no duplican al estudiante: se referencian desde el registro academico "
                 "junto con su matricula vigente.")
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("student_code", "Codigo", type="mono", width=120),
        column("campus_name", "Sede", width=170),
        column("grade_name", "Grado", type="badge", tone="brand", width=130),
        column("group_name", "Grupo", width=110),
        column("complement_name", "Complemento", type="badge", tone="info", width=170),
        column("has_special_diet", "Dieta especial", type="boolean", width=130, align="center"),
        column("status", "Estado", type="badge", width=130, map={
            "ACTIVO": {"label": "Activo", "tone": "success"},
            "SUSPENDIDO": {"label": "Suspendido", "tone": "warning"},
            "RETIRADO": {"label": "Retirado", "tone": "danger"},
            "TRASLADADO": {"label": "Trasladado", "tone": "info"},
            "FINALIZADO": {"label": "Finalizado", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half",
               hint="Solo estudiantes registrados en el modulo academico."),
        remote("enrollment", "Matricula", ENROLLMENT_OPTIONS, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        remote("grade", "Grado", GRADE_OPTIONS, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, col="half"),
        remote("shift", "Jornada", SHIFT_OPTIONS, col="half"),
        remote("modality", "Modalidad", MODALITY_OPTIONS, col="half"),
        remote("complement_type", "Tipo de complemento", COMPLEMENT_OPTIONS, col="half"),
        field("start_date", "Fecha de inicio", type="date", col="half"),
        field("end_date", "Fecha final", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ACTIVO", "Activo"), ("SUSPENDIDO", "Suspendido"), ("RETIRADO", "Retirado"),
            ("TRASLADADO", "Trasladado"), ("FINALIZADO", "Finalizado"),
        ])),
        field("has_special_diet", "Requiere dieta especial", type="boolean", col="half"),
        field("special_diet_detail", "Detalle de la dieta", col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "vigencia", "label": "Vigencia", "type": "remote", "endpoint": VIGENCIA_OPTIONS},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "grade", "label": "Grado", "type": "remote", "endpoint": GRADE_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "ACTIVO", "label": "Activos"}, {"value": "SUSPENDIDO", "label": "Suspendidos"},
            {"value": "RETIRADO", "label": "Retirados"},
        ]},
    ]
    row_actions = [
        {"name": "cambiar-estado", "label": "Cambiar estado", "icon": "arrow-right"},
        {"name": "history", "label": "Ver historial", "icon": "activity"},
    ]
    empty_title = "Sin beneficiarios registrados"
    empty_message = "Vincule beneficiarios desde una priorizacion aprobada o registrelos individualmente."


# ===========================================================================
# 6. PLANEACION
# ===========================================================================
class PaePlanView(PaeResourceView):
    module_code = "pae.planeacion"
    title = "Planeacion del PAE"
    subtitle = "Plan operativo por sede: beneficiarios, dias de atencion, raciones proyectadas y operador."
    icon = "compass"
    template_name = "pae/plans.html"
    endpoint = "/api/pae/planes/"
    columns = [
        column("code", "Codigo", type="mono", width=140),
        column("name", "Plan", width=220),
        column("campus_name", "Sede", width=170),
        column("operator_name", "Operador", width=180),
        column("beneficiaries_count", "Beneficiarios", type="number", width=130, align="center"),
        column("projected_rations", "Raciones", type="number", width=120, align="center"),
        column("status", "Estado", type="badge", width=150, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "EN_REVISION": {"label": "En revision", "tone": "info"},
            "APROBADO": {"label": "Aprobado", "tone": "success"},
            "EN_EJECUCION": {"label": "En ejecucion", "tone": "brand"},
            "CERRADO": {"label": "Cerrado", "tone": "warning"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("institution", "Institucion", INSTITUTION_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        field("name", "Nombre del plan", required=True, col="half"),
        field("start_date", "Fecha inicial", type="date", required=True, col="half"),
        field("end_date", "Fecha final", type="date", required=True, col="half"),
        remote("responsible", "Responsable", USER_OPTIONS, col="half"),
        remote("modality", "Modalidad", MODALITY_OPTIONS, col="half"),
        remote("complement_type", "Tipo de complemento", COMPLEMENT_OPTIONS, col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("contract", "Contrato", CONTRACT_OPTIONS, col="half"),
        remote("menu_cycle", "Ciclo de menu", MENU_CYCLE_OPTIONS, col="half"),
        field("beneficiaries_count", "Beneficiarios", type="number", col="third", default=0),
        field("service_days", "Dias de atencion", type="number", col="third", default=0),
        field("projected_rations", "Raciones proyectadas", type="number", col="third", default=0),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [
        {"name": "transition", "label": "Cambiar estado", "icon": "arrow-right"},
        {"name": "sync-beneficiaries", "label": "Sincronizar beneficiarios", "icon": "refresh"},
        {"name": "history", "label": "Historial de estados", "icon": "activity"},
    ]
    filters = [
        {"name": "vigencia", "label": "Vigencia", "type": "remote", "endpoint": VIGENCIA_OPTIONS},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "BORRADOR", "label": "Borrador"}, {"value": "EN_REVISION", "label": "En revision"},
            {"value": "APROBADO", "label": "Aprobado"}, {"value": "EN_EJECUCION", "label": "En ejecucion"},
            {"value": "CERRADO", "label": "Cerrado"},
        ]},
    ]
    empty_title = "Sin planes registrados"
    empty_message = "Cree el plan operativo de cada sede para habilitar la programacion de entregas."


# ===========================================================================
# 7. MENUS
# ===========================================================================
class PaeMenuCycleView(PaeResourceView):
    module_code = "pae.menus"
    title = "Ciclos de menu"
    subtitle = "Ciclos con versionamiento: dias, preparaciones, componentes e ingredientes."
    icon = "utensils"
    template_name = "pae/menus.html"
    endpoint = "/api/pae/menus/"
    columns = [
        column("code", "Codigo", type="mono", width=130),
        column("name", "Ciclo", width=240),
        column("version", "Version", type="number", width=100, align="center"),
        column("modality_name", "Modalidad", type="badge", tone="info", width=180),
        column("days_registered", "Dias", type="number", width=90, align="center"),
        column("nutritionist", "Nutricionista", width=180),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "EN_REVISION": {"label": "En revision", "tone": "info"},
            "APROBADO": {"label": "Aprobado", "tone": "success"},
            "VIGENTE": {"label": "Vigente", "tone": "brand"},
            "ARCHIVADO": {"label": "Archivado", "tone": "warning"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del ciclo", required=True),
        remote("modality", "Modalidad", MODALITY_OPTIONS, col="half"),
        remote("complement_type", "Tipo de complemento", COMPLEMENT_OPTIONS, col="half"),
        field("days_count", "Dias del ciclo", type="number", col="third", default=5),
        field("start_date", "Vigente desde", type="date", col="third"),
        field("end_date", "Vigente hasta", type="date", col="third"),
        field("nutritionist", "Nutricionista responsable", col="half"),
        field("professional_card", "Tarjeta profesional", col="half"),
        remote("normative", "Norma", NORMATIVE_OPTIONS, col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [
        {"name": "detail", "label": "Ver ciclo completo", "icon": "eye"},
        {"name": "new-version", "label": "Crear nueva version", "icon": "copy"},
        {"name": "publish", "label": "Publicar como vigente", "icon": "check"},
    ]
    empty_title = "Sin ciclos de menu"
    empty_message = "Cree el ciclo de menu con sus dias, preparaciones e ingredientes."


class PaeMenuDayView(PaeResourceView):
    module_code = "pae.menus"
    title = "Dias del ciclo de menu"
    subtitle = "Cada dia agrupa las preparaciones que componen el complemento."
    icon = "calendar"
    endpoint = "/api/pae/menu-dias/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Menus", "url": "/pae/menus/"}, {"label": "Dias"}]
    columns = [
        column("cycle_name", "Ciclo", type="badge", tone="brand", width=220),
        column("day_number", "Dia", type="number", width=80, align="center"),
        column("weekday_display", "Dia de la semana", width=160),
        column("name", "Menu", width=240),
        column("total_calories", "Calorias", type="number", decimals=2, width=130, align="right"),
    ]
    form_fields = [
        remote("cycle", "Ciclo de menu", MENU_CYCLE_OPTIONS, required=True, col="half"),
        field("day_number", "Dia del ciclo", type="number", required=True, col="half", default=1),
        field("weekday", "Dia de la semana", type="select", col="half", options=choices_to_options([
            ("1", "Lunes"), ("2", "Martes"), ("3", "Miercoles"),
            ("4", "Jueves"), ("5", "Viernes"), ("6", "Sabado"), ("7", "Domingo"),
        ])),
        field("name", "Nombre del menu", col="half"),
        field("notes", "Observaciones", type="textarea"),
    ]
    filters = [{"name": "cycle", "label": "Ciclo", "type": "remote", "endpoint": MENU_CYCLE_OPTIONS}]


class PaeMenuPreparationView(PaeResourceView):
    module_code = "pae.menus"
    title = "Preparaciones"
    subtitle = "Componentes servidos en cada dia del ciclo con su porcion y aporte nutricional."
    icon = "utensils"
    endpoint = "/api/pae/menu-preparaciones/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Menus", "url": "/pae/menus/"},
                   {"label": "Preparaciones"}]
    columns = [
        column("name", "Preparacion", width=230),
        column("day_label", "Dia", width=200),
        column("component_display", "Componente", type="badge", tone="brand", width=170),
        column("portion", "Porcion", width=130),
        column("calories", "Calorias", type="number", decimals=2, width=120, align="right"),
        column("protein", "Proteina (g)", type="number", decimals=2, width=130, align="right"),
    ]
    form_fields = [
        remote("day", "Dia del ciclo", MENU_DAY_OPTIONS, required=True, col="half"),
        field("name", "Nombre de la preparacion", required=True, col="half"),
        field("component", "Componente", type="select", col="half", options=choices_to_options([
            ("BEBIDA", "Bebida"), ("CEREAL", "Cereal / derivado"), ("PROTEICO", "Alimento proteico"),
            ("FRUTA", "Fruta"), ("VERDURA", "Verdura / hortaliza"), ("LACTEO", "Lacteo"),
            ("ACOMPANAMIENTO", "Acompanamiento"), ("POSTRE", "Postre"), ("OTRO", "Otro"),
        ])),
        field("portion", "Porcion servida", col="half"),
        field("calories", "Calorias (kcal)", type="number", step="0.01", col="third", default=0),
        field("protein", "Proteina (g)", type="number", step="0.01", col="third", default=0),
        field("order", "Orden", type="number", col="third", default=0),
        field("notes", "Observaciones"),
    ]
    filters = [{"name": "day", "label": "Dia", "type": "remote", "endpoint": MENU_DAY_OPTIONS}]


class PaeMenuIngredientView(PaeResourceView):
    module_code = "pae.menus"
    title = "Ingredientes"
    subtitle = "Cantidades por preparacion, base para el calculo de compras y la verificacion de gramajes."
    icon = "list"
    endpoint = "/api/pae/menu-ingredientes/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Menus", "url": "/pae/menus/"},
                   {"label": "Ingredientes"}]
    columns = [
        column("name", "Ingrediente", width=240),
        column("food_group_name", "Grupo de alimento", type="badge", tone="info", width=190),
        column("quantity", "Cantidad", type="number", decimals=3, width=130, align="right"),
        column("unit", "Unidad", width=100),
        column("notes", "Observaciones", type="truncate", width=220),
    ]
    form_fields = [
        remote("preparation", "Preparacion", PREPARATION_OPTIONS, required=True, col="half"),
        remote("food_group", "Grupo de alimento", catalog_options(PaeCatalog.TYPE_FOOD_GROUP), col="half"),
        field("name", "Ingrediente", required=True, col="half"),
        field("quantity", "Cantidad", type="number", step="0.001", col="third", default=0),
        field("unit", "Unidad", col="third", default="g"),
        field("notes", "Observaciones"),
    ]
    filters = [{"name": "preparation", "label": "Preparacion", "type": "remote", "endpoint": PREPARATION_OPTIONS}]


# ===========================================================================
# 8. OPERADORES
# ===========================================================================
class PaeOperatorView(PaeResourceView):
    module_code = "pae.operadores"
    title = "Operadores"
    subtitle = "Empresas responsables de la prestacion del servicio de alimentacion escolar."
    icon = "truck"
    endpoint = "/api/pae/operadores/"
    columns = [
        column("business_name", "Razon social", type="avatar", subfield="nit"),
        column("code", "Codigo", type="mono", width=120),
        column("legal_representative", "Representante legal", width=200),
        column("phone", "Telefono", width=130),
        column("email", "Correo", width=200),
        column("contracts_count", "Contratos", type="number", width=110, align="center"),
        column("status", "Estado", type="badge", width=130, map={
            "ACTIVO": {"label": "Activo", "tone": "success"},
            "SUSPENDIDO": {"label": "Suspendido", "tone": "warning"},
            "INACTIVO": {"label": "Inactivo", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("institution", "Institucion", INSTITUTION_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("business_name", "Razon social", required=True, col="half"),
        field("nit", "NIT", required=True, col="half"),
        field("legal_representative", "Representante legal", col="half"),
        field("contact_name", "Persona de contacto", col="half"),
        field("phone", "Telefono", col="third"),
        field("mobile", "Celular", col="third"),
        field("email", "Correo electronico", type="email", col="third"),
        field("address", "Direccion", col="half"),
        field("city", "Ciudad", col="half"),
        field("sanitary_registration", "Registro sanitario", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ACTIVO", "Activo"), ("SUSPENDIDO", "Suspendido"), ("INACTIVO", "Inactivo"),
        ])),
        remote("user", "Usuario de acceso", USER_OPTIONS, col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [{"name": "performance", "label": "Ver desempeno", "icon": "activity"}]
    empty_title = "Sin operadores registrados"
    empty_message = "Registre los operadores antes de suscribir contratos."


# ===========================================================================
# 9. CONTRATOS
# ===========================================================================
class PaeContractView(PaeResourceView):
    module_code = "pae.contratos"
    title = "Contratos"
    subtitle = "Contratos suscritos con los operadores, con alertas automaticas de vencimiento."
    icon = "file-text"
    template_name = "pae/contracts.html"
    endpoint = "/api/pae/contratos/"
    columns = [
        column("number", "Numero", type="mono", width=150),
        column("operator_name", "Operador", width=210),
        column("start_date", "Inicio", type="date", width=120),
        column("end_date", "Fin", type="date", width=120),
        column("days_to_expire", "Dias restantes", type="number", width=140, align="center"),
        column("total_rations", "Raciones", type="number", width=120, align="center"),
        column("execution_percentage", "Ejecucion", type="percent", width=150),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "VIGENTE": {"label": "Vigente", "tone": "success"},
            "SUSPENDIDO": {"label": "Suspendido", "tone": "warning"},
            "VENCIDO": {"label": "Vencido", "tone": "danger"},
            "LIQUIDADO": {"label": "Liquidado", "tone": "info"},
            "TERMINADO": {"label": "Terminado", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, required=True, col="half"),
        field("number", "Numero de contrato", required=True, col="half"),
        remote("supervisor", "Supervisor del contrato", USER_OPTIONS, col="half"),
        field("subject", "Objeto del contrato", type="textarea", required=True, rows=3),
        field("value", "Valor", type="number", step="0.01", col="third", default=0),
        field("ration_value", "Valor unitario de la racion", type="number", step="0.01", col="third", default=0),
        field("total_rations", "Raciones contratadas", type="number", col="third", default=0),
        field("start_date", "Fecha inicial", type="date", required=True, col="half"),
        field("end_date", "Fecha final", type="date", required=True, col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("VIGENTE", "Vigente"), ("SUSPENDIDO", "Suspendido"),
            ("VENCIDO", "Vencido"), ("LIQUIDADO", "Liquidado"), ("TERMINADO", "Terminado"),
        ])),
        field("alert_days", "Alertar dias antes del vencimiento", type="number", col="half", default=30),
        field("observations", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "vigencia", "label": "Vigencia", "type": "remote", "endpoint": VIGENCIA_OPTIONS},
        {"name": "operator", "label": "Operador", "type": "remote", "endpoint": OPERATOR_OPTIONS},
    ]
    empty_title = "Sin contratos registrados"
    empty_message = "Registre el contrato para habilitar la ejecucion y el seguimiento de raciones."


# ===========================================================================
# 10. PROGRAMACION
# ===========================================================================
class PaeScheduleView(PaeResourceView):
    module_code = "pae.programacion"
    title = "Programacion de entregas"
    subtitle = "Programacion diaria por sede, jornada y tipo de complemento. Permite generacion masiva por periodo."
    icon = "calendar-check"
    template_name = "pae/schedules.html"
    endpoint = "/api/pae/programacion/"
    columns = [
        column("service_date", "Fecha", type="date", width=120),
        column("campus_name", "Sede", width=180),
        column("plan_name", "Plan", width=180),
        column("shift_name", "Jornada", width=120),
        column("operator_name", "Operador", width=180),
        column("complement_name", "Complemento", type="badge", tone="info", width=160),
        column("scheduled_rations", "Raciones", type="number", width=110, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "CONFIRMADA": {"label": "Confirmada", "tone": "brand"},
            "EJECUTADA": {"label": "Ejecutada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("plan", "Plan", PLAN_OPTIONS, required=True, col="half"),
        field("service_date", "Fecha de servicio", type="date", required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("shift", "Jornada", SHIFT_OPTIONS, col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("complement_type", "Tipo de complemento", COMPLEMENT_OPTIONS, col="half"),
        remote("menu_day", "Menu programado", MENU_DAY_OPTIONS, col="half"),
        field("service_time", "Horario de servicio", type="time", col="half"),
        field("beneficiaries_count", "Beneficiarios programados", type="number", col="half", default=0),
        field("scheduled_rations", "Raciones programadas", type="number", col="half", default=0),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PROGRAMADA", "Programada"), ("CONFIRMADA", "Confirmada"),
            ("EJECUTADA", "Ejecutada"), ("CANCELADA", "Cancelada"),
        ])),
        field("observations", "Observaciones"),
    ]
    filters = [
        {"name": "plan", "label": "Plan", "type": "remote", "endpoint": PLAN_OPTIONS},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "PROGRAMADA", "label": "Programadas"}, {"value": "EJECUTADA", "label": "Ejecutadas"},
        ]},
    ]
    empty_title = "Sin programacion registrada"
    empty_message = "Genere la programacion masiva desde un plan aprobado."


# ===========================================================================
# 11. ENTREGAS
# ===========================================================================
class PaeDeliveryView(PaeResourceView):
    module_code = "pae.entregas"
    title = "Entregas diarias"
    subtitle = "Registro de la entrega efectiva. Faltantes, no entregadas y cumplimiento se calculan automaticamente."
    icon = "truck"
    template_name = "pae/deliveries.html"
    endpoint = "/api/pae/entregas/"
    help_text = ("faltantes = programadas - recibidas · no entregadas = recibidas - entregadas · "
                 "cumplimiento = entregadas / programadas x 100")
    columns = [
        column("service_date", "Fecha", type="date", width=115),
        column("campus_name", "Sede", width=170),
        column("operator_name", "Operador", width=170),
        column("scheduled_rations", "Programadas", type="number", width=125, align="center"),
        column("received_rations", "Recibidas", type="number", width=110, align="center"),
        column("delivered_rations", "Entregadas", type="number", width=115, align="center"),
        column("missing_rations", "Faltantes", type="number", width=105, align="center"),
        column("compliance", "Cumplimiento", type="percent", width=155),
        column("status", "Estado", type="badge", width=140, map={
            "REGISTRADA": {"label": "Registrada", "tone": "info"},
            "VERIFICADA": {"label": "Verificada", "tone": "success"},
            "CON_NOVEDAD": {"label": "Con novedad", "tone": "danger"},
            "ANULADA": {"label": "Anulada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        field("s1", "Identificacion de la entrega", type="section"),
        remote("plan", "Plan", PLAN_OPTIONS, required=True, col="half"),
        field("service_date", "Fecha", type="date", required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("shift", "Jornada", SHIFT_OPTIONS, col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("complement_type", "Tipo de complemento", COMPLEMENT_OPTIONS, col="half"),
        remote("contract", "Contrato", CONTRACT_OPTIONS, col="half"),
        remote("schedule", "Programacion asociada", "/api/pae/programacion/options/", col="half"),
        field("s2", "Raciones", type="section"),
        field("scheduled_beneficiaries", "Beneficiarios programados", type="number", col="third", default=0),
        field("scheduled_rations", "Raciones programadas", type="number", col="third", default=0),
        field("received_rations", "Raciones recibidas", type="number", col="third", default=0),
        field("delivered_rations", "Raciones entregadas", type="number", col="third", default=0),
        field("s3", "Horarios y menu", type="section"),
        field("arrival_time", "Hora de llegada", type="time", col="third"),
        field("delivery_time", "Hora de entrega", type="time", col="third"),
        remote("scheduled_menu", "Menu programado", MENU_DAY_OPTIONS, col="third"),
        field("menu_matches", "El menu recibido corresponde al programado", type="boolean",
              col="half", default=True),
        field("received_menu_detail", "Menu recibido", col="half"),
        field("s4", "Novedades", type="section"),
        remote("noncompliance_cause", "Causa del incumplimiento", catalog_options(PaeCatalog.TYPE_CAUSE), col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("REGISTRADA", "Registrada"), ("VERIFICADA", "Verificada"),
            ("CON_NOVEDAD", "Con novedad"), ("ANULADA", "Anulada"),
        ])),
        field("justification", "Justificacion del incumplimiento", type="textarea", rows=3,
              hint="Obligatoria cuando hay faltantes, no entregadas o el menu difiere del programado."),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [{"name": "create-incident", "label": "Generar novedad", "icon": "alert-triangle"}]
    filters = [
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "operator", "label": "Operador", "type": "remote", "endpoint": OPERATOR_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "REGISTRADA", "label": "Registradas"},
            {"value": "CON_NOVEDAD", "label": "Con novedad"},
            {"value": "VERIFICADA", "label": "Verificadas"},
        ]},
    ]
    empty_title = "Sin entregas registradas"
    empty_message = "Registre la entrega diaria a partir de la programacion."


# ===========================================================================
# 12. CONTROL DE CALIDAD
# ===========================================================================
class PaeQualityControlView(PaeResourceView):
    module_code = "pae.control"
    title = "Control de calidad e inocuidad"
    subtitle = "Aplicacion de listas de verificacion con resultado automatico y trazabilidad de criterios criticos."
    icon = "shield-check"
    template_name = "pae/quality.html"
    endpoint = "/api/pae/verificaciones/"
    columns = [
        column("verification_date", "Fecha", type="date", width=120),
        column("campus_name", "Sede", width=180),
        column("checklist_name", "Lista aplicada", width=220),
        column("operator_name", "Operador", width=170),
        column("compliant_items", "Cumple", type="number", width=100, align="center"),
        column("noncompliant_items", "No cumple", type="number", width=110, align="center"),
        column("critical_failures", "Criticos", type="number", width=100, align="center"),
        column("score", "Puntaje", type="percent", width=140),
        column("result", "Resultado", type="badge", width=180, map=RESULT_MAP),
    ]
    form_fields = [
        remote("checklist", "Lista de verificacion", CHECKLIST_OPTIONS, required=True, col="half"),
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("delivery", "Entrega asociada", "/api/pae/entregas/options/", col="half"),
        field("verification_date", "Fecha", type="date", col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [{"name": "apply", "label": "Aplicar lista", "icon": "clipboard-check"}]
    filters = [
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "result", "label": "Resultado", "type": "select",
         "options": [{"value": k, "label": v["label"]} for k, v in RESULT_MAP.items()]},
    ]
    empty_title = "Sin verificaciones aplicadas"
    empty_message = "Cree la verificacion y aplique la lista de criterios en la sede."


class PaeChecklistView(PaeResourceView):
    module_code = "pae.control"
    title = "Listas de verificacion"
    subtitle = "Listas configurables por ambito: recepcion, almacenamiento, manipulacion, preparacion y servicio."
    icon = "list"
    endpoint = "/api/pae/listas-verificacion/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Control de calidad", "url": "/pae/control/"},
                   {"label": "Listas"}]
    columns = [
        column("code", "Codigo", type="mono", width=140),
        column("name", "Lista", width=280),
        column("scope_display", "Ambito", type="badge", tone="brand", width=200),
        column("version", "Version", type="number", width=100, align="center"),
        column("items_count", "Criterios", type="number", width=110, align="center"),
        column("threshold_full", "Umbral cumple", type="number", decimals=2, width=140, align="right"),
    ]
    form_fields = [
        field("code", "Codigo", required=True, col="half"),
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, col="half"),
        field("name", "Nombre de la lista", required=True),
        field("scope", "Ambito", type="select", col="half", options=choices_to_options(PaeChecklist.SCOPE_CHOICES)),
        remote("normative", "Norma", NORMATIVE_OPTIONS, col="half"),
        field("threshold_full", "Umbral de cumplimiento (%)", type="number", step="0.01", col="half", default=90),
        field("threshold_partial", "Umbral parcial (%)", type="number", step="0.01", col="half", default=70),
        field("description", "Descripcion", type="textarea"),
    ]


class PaeChecklistItemView(PaeResourceView):
    module_code = "pae.control"
    title = "Criterios de verificacion"
    subtitle = "Cada criterio pertenece a una categoria, tiene peso y puede marcarse como critico."
    icon = "check"
    endpoint = "/api/pae/criterios-verificacion/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Control de calidad", "url": "/pae/control/"},
                   {"label": "Criterios"}]
    columns = [
        column("criterion", "Criterio", type="truncate", width=380),
        column("checklist_name", "Lista", type="badge", tone="brand", width=200),
        column("category_name", "Categoria", width=180),
        column("weight", "Peso", type="number", decimals=2, width=90, align="right"),
        column("is_critical", "Critico", type="boolean", width=95, align="center"),
        column("requires_evidence", "Evidencia", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("checklist", "Lista de verificacion", CHECKLIST_OPTIONS, required=True, col="half"),
        remote("category", "Categoria", catalog_options(PaeCatalog.TYPE_CHECK_CATEGORY), col="half"),
        field("code", "Codigo", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("criterion", "Criterio", type="textarea", required=True, rows=3),
        field("weight", "Peso", type="number", step="0.01", col="third", default=1),
        field("is_critical", "Criterio critico", type="boolean", col="third"),
        field("requires_evidence", "Exige evidencia", type="boolean", col="third"),
        field("normative_reference", "Referencia normativa"),
    ]
    filters = [{"name": "checklist", "label": "Lista", "type": "remote", "endpoint": CHECKLIST_OPTIONS}]


# ===========================================================================
# 13. VISITAS
# ===========================================================================
class PaeVisitView(PaeResourceView):
    module_code = "pae.visitas"
    title = "Visitas y seguimiento"
    subtitle = "Visitas de supervision con lista de verificacion, hallazgos y compromisos."
    icon = "eye"
    endpoint = "/api/pae/visitas/"
    columns = [
        column("number", "Numero", type="mono", width=140),
        column("visit_date", "Fecha", type="date", width=120),
        column("campus_name", "Sede", width=190),
        column("visit_type_name", "Tipo", type="badge", tone="brand", width=170),
        column("responsible_name", "Responsable", width=180),
        column("findings_count", "Hallazgos", type="number", width=110, align="center"),
        column("commitments_count", "Compromisos", type="number", width=130, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "REALIZADA": {"label": "Realizada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
            "CERRADA": {"label": "Cerrada", "tone": "brand"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("visit_type", "Tipo de visita", catalog_options(PaeCatalog.TYPE_VISIT), col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        field("visit_date", "Fecha", type="date", required=True, col="third"),
        field("start_time", "Hora de inicio", type="time", col="third"),
        field("end_time", "Hora de finalizacion", type="time", col="third"),
        remote("verification", "Lista aplicada", "/api/pae/verificaciones/options/", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PROGRAMADA", "Programada"), ("REALIZADA", "Realizada"),
            ("CANCELADA", "Cancelada"), ("CERRADA", "Cerrada"),
        ])),
        field("objective", "Objetivo", type="textarea", rows=3),
        field("attendees", "Asistentes", type="textarea", rows=2),
        field("development", "Desarrollo de la visita", type="textarea", rows=4),
        field("conclusions", "Conclusiones", type="textarea", rows=3),
    ]
    filters = [
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "visit_type", "label": "Tipo", "type": "remote",
         "endpoint": catalog_options(PaeCatalog.TYPE_VISIT)},
    ]
    empty_title = "Sin visitas registradas"
    empty_message = "Programe la visita de seguimiento a las sedes atendidas."


class PaeFindingView(PaeResourceView):
    module_code = "pae.visitas"
    title = "Hallazgos"
    subtitle = "Situaciones detectadas en visitas y verificaciones, con severidad y estado de tratamiento."
    icon = "alert-triangle"
    endpoint = "/api/pae/hallazgos/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"}, {"label": "Visitas", "url": "/pae/visitas/"},
                   {"label": "Hallazgos"}]
    columns = [
        column("detected_on", "Fecha", type="date", width=120),
        column("campus_name", "Sede", width=180),
        column("finding_type_name", "Tipo", type="badge", tone="brand", width=170),
        column("description", "Hallazgo", type="truncate", width=300),
        column("severity", "Severidad", type="badge", width=140, map={
            "LEVE": {"label": "Leve", "tone": "info"},
            "MODERADO": {"label": "Moderado", "tone": "warning"},
            "GRAVE": {"label": "Grave", "tone": "danger"},
            "CRITICO": {"label": "Critico", "tone": "danger"},
        }),
        column("status", "Estado", type="badge", width=150, map={
            "ABIERTO": {"label": "Abierto", "tone": "warning"},
            "EN_TRATAMIENTO": {"label": "En tratamiento", "tone": "info"},
            "VERIFICADO": {"label": "Verificado", "tone": "success"},
            "CERRADO": {"label": "Cerrado", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("visit", "Visita", VISIT_OPTIONS, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("finding_type", "Tipo de hallazgo", catalog_options(PaeCatalog.TYPE_FINDING), col="half"),
        field("severity", "Severidad", type="select", col="half", options=choices_to_options([
            ("LEVE", "Leve"), ("MODERADO", "Moderado"), ("GRAVE", "Grave"), ("CRITICO", "Critico"),
        ])),
        field("code", "Codigo", col="half"),
        field("detected_on", "Fecha de deteccion", type="date", col="half"),
        field("description", "Descripcion del hallazgo", type="textarea", required=True, rows=4),
        field("normative_reference", "Referencia normativa", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ABIERTO", "Abierto"), ("EN_TRATAMIENTO", "En tratamiento"),
            ("VERIFICADO", "Verificado"), ("CERRADO", "Cerrado"),
        ])),
    ]
    row_actions = [{"name": "create-action", "label": "Generar plan de mejoramiento", "icon": "refresh"}]


# ===========================================================================
# 14. NOVEDADES
# ===========================================================================
class PaeIncidentView(PaeResourceView):
    module_code = "pae.novedades"
    title = "Novedades"
    subtitle = "Reporte, asignacion, investigacion, correccion y cierre con historial completo de estados."
    icon = "alert-triangle"
    template_name = "pae/incidents.html"
    endpoint = "/api/pae/novedades/"
    columns = [
        column("number", "Numero", type="mono", width=140),
        column("reported_on", "Fecha", type="date", width=115),
        column("campus_name", "Sede", width=170),
        column("incident_type_name", "Tipo", type="badge", tone="brand", width=170),
        column("description", "Descripcion", type="truncate", width=260),
        column("priority", "Prioridad", type="badge", width=125, map=PRIORITY_MAP),
        column("assigned_to_name", "Responsable", width=170),
        column("status", "Estado", type="badge", width=165, map={
            "REPORTADA": {"label": "Reportada", "tone": "info"},
            "ASIGNADA": {"label": "Asignada", "tone": "brand"},
            "EN_INVESTIGACION": {"label": "En investigacion", "tone": "warning"},
            "EN_CORRECCION": {"label": "En correccion", "tone": "warning"},
            "SOLUCIONADA": {"label": "Solucionada", "tone": "success"},
            "CERRADA": {"label": "Cerrada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, required=True, col="half"),
        remote("incident_type", "Tipo de novedad", catalog_options(PaeCatalog.TYPE_INCIDENT), col="half"),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("delivery", "Entrega relacionada", "/api/pae/entregas/options/", col="half"),
        field("reported_on", "Fecha del reporte", type="date", col="half"),
        field("priority", "Prioridad", type="select", col="half",
              options=[{"value": k, "label": v["label"]} for k, v in PRIORITY_MAP.items()]),
        remote("assigned_to", "Responsable asignado", USER_OPTIONS, col="half"),
        field("due_date", "Fecha limite", type="date", col="half"),
        field("description", "Descripcion", type="textarea", required=True, rows=4),
        field("solution", "Solucion aplicada", type="textarea", rows=3,
              hint="Obligatoria para cerrar la novedad."),
    ]
    row_actions = [
        {"name": "estado", "label": "Cambiar estado", "icon": "arrow-right"},
        {"name": "history", "label": "Ver historial", "icon": "activity"},
    ]
    filters = [
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "REPORTADA", "label": "Reportadas"}, {"value": "ASIGNADA", "label": "Asignadas"},
            {"value": "EN_INVESTIGACION", "label": "En investigacion"},
            {"value": "EN_CORRECCION", "label": "En correccion"},
            {"value": "SOLUCIONADA", "label": "Solucionadas"}, {"value": "CERRADA", "label": "Cerradas"},
        ]},
        {"name": "priority", "label": "Prioridad", "type": "select",
         "options": [{"value": k, "label": v["label"]} for k, v in PRIORITY_MAP.items()]},
    ]
    empty_title = "Sin novedades registradas"
    empty_message = "Las novedades pueden generarse automaticamente desde una entrega con incumplimiento."


# ===========================================================================
# 15. PLANES DE MEJORAMIENTO
# ===========================================================================
class PaeImprovementView(PaeResourceView):
    module_code = "pae.mejoramiento"
    title = "Planes de mejoramiento"
    subtitle = "Acciones correctivas con causa raiz, indicador, meta, evidencia y verificacion de eficacia."
    icon = "refresh"
    endpoint = "/api/pae/mejoramiento/"
    columns = [
        column("code", "Codigo", type="mono", width=140),
        column("campus_name", "Sede", width=170),
        column("action", "Accion", type="truncate", width=280),
        column("responsible_name", "Responsable", width=170),
        column("due_date", "Fecha limite", type="date", width=130),
        column("progress", "Avance", type="percent", width=140),
        column("status", "Estado", type="badge", width=145, map={
            "PENDIENTE": {"label": "Pendiente", "tone": "neutral"},
            "EN_EJECUCION": {"label": "En ejecucion", "tone": "info"},
            "VERIFICADA": {"label": "Verificada", "tone": "success"},
            "CERRADA": {"label": "Cerrada", "tone": "brand"},
            "VENCIDA": {"label": "Vencida", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        remote("finding", "Hallazgo asociado", FINDING_OPTIONS, col="half"),
        remote("incident", "Novedad asociada", INCIDENT_OPTIONS, col="half"),
        field("finding_description", "Hallazgo / situacion", type="textarea", required=True, rows=3),
        field("root_cause", "Causa raiz", type="textarea", rows=3),
        field("action", "Accion de mejora", type="textarea", required=True, rows=3),
        remote("responsible", "Responsable", USER_OPTIONS, col="half"),
        field("start_date", "Fecha inicial", type="date", col="half"),
        field("due_date", "Fecha limite", type="date", required=True, col="half"),
        field("progress", "Avance (%)", type="number", col="half", default=0, min=0, max=100),
        field("indicator", "Indicador de seguimiento", col="half"),
        field("goal", "Meta", col="half"),
        field("requires_evidence", "Exige evidencia para cerrar", type="boolean", col="half", default=True),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PENDIENTE", "Pendiente"), ("EN_EJECUCION", "En ejecucion"),
            ("VERIFICADA", "Verificada"), ("CERRADA", "Cerrada"), ("VENCIDA", "Vencida"),
        ])),
        field("verification_note", "Verificacion de eficacia", type="textarea", rows=3,
              hint="Obligatoria para cerrar la accion."),
    ]
    row_actions = [{"name": "close", "label": "Verificar y cerrar", "icon": "check"}]
    filters = [
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "PENDIENTE", "label": "Pendientes"}, {"value": "EN_EJECUCION", "label": "En ejecucion"},
            {"value": "VENCIDA", "label": "Vencidas"}, {"value": "CERRADA", "label": "Cerradas"},
        ]},
    ]
    empty_title = "Sin planes de mejoramiento"
    empty_message = "Genere acciones de mejora desde los hallazgos de las visitas."


# ===========================================================================
# 16. PQRS
# ===========================================================================
class PaePqrsView(PaeResourceView):
    module_code = "pae.pqrs"
    title = "PQRS"
    subtitle = "Peticiones, quejas, reclamos, sugerencias y felicitaciones sobre el programa."
    icon = "message"
    endpoint = "/api/pae/pqrs/"
    columns = [
        column("filing_number", "Radicado", type="mono", width=150),
        column("filed_on", "Fecha", type="date", width=115),
        column("kind", "Tipo", type="badge", width=140, map={
            "PETICION": {"label": "Peticion", "tone": "info"},
            "QUEJA": {"label": "Queja", "tone": "warning"},
            "RECLAMO": {"label": "Reclamo", "tone": "danger"},
            "SUGERENCIA": {"label": "Sugerencia", "tone": "brand"},
            "FELICITACION": {"label": "Felicitacion", "tone": "success"},
        }),
        column("campus_name", "Sede", width=170),
        column("description", "Descripcion", type="truncate", width=250),
        column("due_date", "Vence", type="date", width=115),
        column("status", "Estado", type="badge", width=140, map={
            "RADICADA": {"label": "Radicada", "tone": "info"},
            "EN_TRAMITE": {"label": "En tramite", "tone": "warning"},
            "RESPONDIDA": {"label": "Respondida", "tone": "success"},
            "CERRADA": {"label": "Cerrada", "tone": "neutral"},
            "VENCIDA": {"label": "Vencida", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        field("kind", "Tipo", type="select", required=True, col="half", options=choices_to_options([
            ("PETICION", "Peticion"), ("QUEJA", "Queja"), ("RECLAMO", "Reclamo"),
            ("SUGERENCIA", "Sugerencia"), ("FELICITACION", "Felicitacion"),
        ])),
        remote("pqrs_type", "Clasificacion", catalog_options(PaeCatalog.TYPE_PQRS), col="half"),
        field("channel", "Canal", type="select", col="half", options=choices_to_options([
            ("PRESENCIAL", "Presencial"), ("BUZON", "Buzon"), ("TELEFONO", "Telefono"),
            ("CORREO", "Correo electronico"), ("PLATAFORMA", "Plataforma"),
        ])),
        field("filed_on", "Fecha de radicacion", type="date", col="half"),
        field("is_anonymous", "Anonima", type="boolean", col="half"),
        field("applicant_name", "Nombre del solicitante", col="half"),
        field("applicant_document", "Documento", col="third"),
        field("applicant_email", "Correo", type="email", col="third"),
        field("applicant_phone", "Telefono", col="third"),
        field("description", "Descripcion", type="textarea", required=True, rows=4),
        remote("responsible", "Responsable", USER_OPTIONS, col="half"),
        field("due_date", "Fecha limite de respuesta", type="date", col="half"),
        field("answer", "Respuesta", type="textarea", rows=4),
        field("answered_on", "Fecha de respuesta", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("RADICADA", "Radicada"), ("EN_TRAMITE", "En tramite"), ("RESPONDIDA", "Respondida"),
            ("CERRADA", "Cerrada"), ("VENCIDA", "Vencida"),
        ])),
    ]
    filters = [
        {"name": "kind", "label": "Tipo", "type": "select", "options": choices_to_options([
            ("PETICION", "Peticion"), ("QUEJA", "Queja"), ("RECLAMO", "Reclamo"),
            ("SUGERENCIA", "Sugerencia"), ("FELICITACION", "Felicitacion"),
        ])},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "RADICADA", "label": "Radicadas"}, {"value": "EN_TRAMITE", "label": "En tramite"},
            {"value": "RESPONDIDA", "label": "Respondidas"},
        ]},
    ]
    empty_title = "Sin PQRS radicadas"
    empty_message = "Las PQRS del programa se radican y responden desde este modulo."


# ===========================================================================
# 17. PARTICIPACION CIUDADANA
# ===========================================================================
class PaeParticipationView(PaeResourceView):
    module_code = "pae.participacion"
    title = "Participacion ciudadana"
    subtitle = "Reuniones del comite de alimentacion escolar: actas, participantes y compromisos."
    icon = "heart-handshake"
    endpoint = "/api/pae/participacion/"
    columns = [
        column("act_number", "Acta", type="mono", width=130),
        column("meeting_date", "Fecha", type="datetime", width=165),
        column("subject", "Asunto", width=260),
        column("campus_name", "Sede", width=170),
        column("meeting_type_name", "Tipo", type="badge", tone="brand", width=170),
        column("participants_registered", "Asistentes", type="number", width=120, align="center"),
        column("commitments_count", "Compromisos", type="number", width=130, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "REALIZADA": {"label": "Realizada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, required=True, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        remote("meeting_type", "Tipo de reunion", catalog_options(PaeCatalog.TYPE_MEETING), col="half"),
        field("act_number", "Numero de acta", col="half"),
        field("meeting_date", "Fecha y hora", type="datetime-local", required=True, col="half"),
        field("place", "Lugar", col="half"),
        field("subject", "Asunto", required=True),
        field("agenda", "Orden del dia", type="textarea", rows=3),
        field("development", "Desarrollo", type="textarea", rows=4),
        field("agreements", "Compromisos y acuerdos", type="textarea", rows=3),
        field("attendees_count", "Numero de asistentes", type="number", col="half", default=0),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PROGRAMADA", "Programada"), ("REALIZADA", "Realizada"), ("CANCELADA", "Cancelada"),
        ])),
    ]
    empty_title = "Sin reuniones registradas"
    empty_message = "Registre las reuniones de participacion y sus compromisos."


class PaeParticipantView(PaeResourceView):
    module_code = "pae.participacion"
    title = "Participantes"
    subtitle = "Asistentes registrados en cada reunion de participacion ciudadana."
    icon = "users"
    endpoint = "/api/pae/participantes/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"},
                   {"label": "Participacion", "url": "/pae/participacion/"}, {"label": "Participantes"}]
    columns = [
        column("full_name", "Participante", type="avatar", subfield="document"),
        column("meeting_subject", "Reunion", type="truncate", width=240),
        column("role_display", "Calidad", type="badge", tone="brand", width=190),
        column("organization", "Organizacion", width=180),
        column("phone", "Telefono", width=130),
    ]
    form_fields = [
        remote("meeting", "Reunion", MEETING_OPTIONS, required=True, col="half"),
        field("full_name", "Nombre completo", required=True, col="half"),
        field("document", "Documento", col="half"),
        field("role", "Calidad en que asiste", type="select", col="half", options=choices_to_options([
            ("PADRE", "Padre de familia / acudiente"), ("ESTUDIANTE", "Estudiante"),
            ("DOCENTE", "Docente"), ("DIRECTIVO", "Directivo"), ("OPERADOR", "Operador"),
            ("ENTE_TERRITORIAL", "Ente territorial"), ("OTRO", "Otro"),
        ])),
        field("organization", "Organizacion", col="half"),
        field("email", "Correo", type="email", col="half"),
        field("phone", "Telefono", col="half"),
        remote("user", "Usuario", USER_OPTIONS, col="half"),
    ]
    filters = [{"name": "meeting", "label": "Reunion", "type": "remote", "endpoint": MEETING_OPTIONS}]


class PaeCommitmentView(PaeResourceView):
    module_code = "pae.participacion"
    title = "Compromisos"
    subtitle = "Compromisos adquiridos en visitas y reuniones, con responsable y seguimiento."
    icon = "check"
    endpoint = "/api/pae/compromisos/"
    breadcrumbs = [{"label": "PAE", "url": "/pae/"},
                   {"label": "Participacion", "url": "/pae/participacion/"}, {"label": "Compromisos"}]
    columns = [
        column("description", "Compromiso", type="truncate", width=340),
        column("responsible_name", "Responsable", width=190),
        column("due_date", "Fecha limite", type="date", width=130),
        column("status", "Estado", type="badge", width=140, map={
            "PENDIENTE": {"label": "Pendiente", "tone": "warning"},
            "EN_PROCESO": {"label": "En proceso", "tone": "info"},
            "CUMPLIDO": {"label": "Cumplido", "tone": "success"},
            "INCUMPLIDO": {"label": "Incumplido", "tone": "danger"},
        }),
        column("is_overdue", "Vencido", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("visit", "Visita", VISIT_OPTIONS, col="half"),
        remote("meeting", "Reunion", MEETING_OPTIONS, col="half"),
        field("description", "Compromiso", type="textarea", required=True, rows=3),
        field("responsible_name", "Responsable", col="half"),
        remote("responsible_user", "Usuario responsable", USER_OPTIONS, col="half"),
        field("due_date", "Fecha limite", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PENDIENTE", "Pendiente"), ("EN_PROCESO", "En proceso"),
            ("CUMPLIDO", "Cumplido"), ("INCUMPLIDO", "Incumplido"),
        ])),
        field("follow_up", "Seguimiento", type="textarea", rows=3),
    ]


# ===========================================================================
# 18-19. DOCUMENTOS Y EVIDENCIAS
# ===========================================================================
class PaeDocumentView(PaeResourceView):
    module_code = "pae.documentos"
    title = "Documentos del PAE"
    subtitle = "Repositorio documental con versionamiento, vigencia y alertas de vencimiento."
    icon = "folder"
    endpoint = "/api/pae/documentos/"
    columns = [
        column("name", "Documento", width=250),
        column("module_display", "Modulo", type="badge", tone="brand", width=180),
        column("document_type_name", "Tipo", width=170),
        column("version", "Version", type="number", width=95, align="center"),
        column("document_date", "Fecha", type="date", width=120),
        column("expires_on", "Vence", type="date", width=120),
        column("status", "Estado", type="badge", width=130, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "VIGENTE": {"label": "Vigente", "tone": "success"},
            "VENCIDO": {"label": "Vencido", "tone": "danger"},
            "ARCHIVADO": {"label": "Archivado", "tone": "warning"},
        }),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        remote("document_type", "Tipo de documento", catalog_options(PaeCatalog.TYPE_DOCUMENT), col="half"),
        field("module", "Modulo", type="select", col="half",
              options=choices_to_options(PaeDocument.MODULE_CHOICES)),
        field("name", "Nombre del documento", required=True),
        field("description", "Descripcion", type="textarea"),
        field("file", "Archivo", type="file", required=True, col="half"),
        field("document_date", "Fecha del documento", type="date", col="half"),
        field("expires_on", "Vence el", type="date", col="half"),
        field("alert_days", "Alertar dias antes", type="number", col="half", default=30),
        remote("operator", "Operador", OPERATOR_OPTIONS, col="half"),
        remote("contract", "Contrato", CONTRACT_OPTIONS, col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("VIGENTE", "Vigente"),
            ("VENCIDO", "Vencido"), ("ARCHIVADO", "Archivado"),
        ])),
    ]
    row_actions = [
        {"name": "versions", "label": "Ver versiones", "icon": "copy"},
        {"name": "new-version", "label": "Cargar nueva version", "icon": "upload"},
    ]
    filters = [
        {"name": "module", "label": "Modulo", "type": "select",
         "options": choices_to_options(PaeDocument.MODULE_CHOICES)},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "VIGENTE", "label": "Vigentes"}, {"value": "VENCIDO", "label": "Vencidos"},
        ]},
    ]
    empty_title = "Sin documentos cargados"
    empty_message = "Cargue los soportes documentales del programa (contratos, conceptos, actas)."


class PaeEvidenceView(PaeResourceView):
    module_code = "pae.evidencias"
    title = "Evidencias"
    subtitle = "Fotografias, actas y soportes asociados a entregas, visitas, novedades y acciones."
    icon = "paperclip"
    endpoint = "/api/pae/evidencias/"
    columns = [
        column("name", "Evidencia", width=250),
        column("module_display", "Modulo", type="badge", tone="brand", width=180),
        column("reference_label", "Registro", type="truncate", width=210),
        column("kind_display", "Tipo", type="badge", tone="info", width=150),
        column("campus_name", "Sede", width=160),
        column("captured_at", "Captura", type="datetime", width=160),
    ]
    form_fields = [
        remote("vigencia", "Vigencia", VIGENCIA_OPTIONS, col="half"),
        remote("campus", "Sede", CAMPUS_OPTIONS, col="half"),
        field("module", "Modulo", type="select", col="half",
              options=choices_to_options(PaeDocument.MODULE_CHOICES)),
        field("kind", "Tipo de evidencia", type="select", col="half", options=choices_to_options([
            ("FOTOGRAFIA", "Fotografia"), ("ACTA", "Acta"), ("PLANILLA", "Planilla"),
            ("REGISTRO", "Registro"), ("SOPORTE", "Soporte"), ("OTRO", "Otro"),
        ])),
        field("reference_id", "Identificador del registro", type="number", col="half"),
        field("reference_label", "Registro", col="half"),
        field("name", "Nombre", required=True),
        field("description", "Descripcion", type="textarea"),
        field("file", "Archivo", type="file", required=True),
    ]
    filters = [
        {"name": "module", "label": "Modulo", "type": "select",
         "options": choices_to_options(PaeDocument.MODULE_CHOICES)},
        {"name": "campus", "label": "Sede", "type": "remote", "endpoint": CAMPUS_OPTIONS},
    ]
    empty_title = "Sin evidencias cargadas"
    empty_message = "Adjunte fotografias y soportes de la operacion del programa."


# ===========================================================================
# 20-22. INDICADORES, INFORMES Y AUDITORIA
# ===========================================================================
class PaeIndicatorView(PaePageView):
    template_name = "pae/indicators.html"
    module_code = "pae.indicadores"
    title = "Indicadores del PAE"
    subtitle = "Cobertura, cumplimiento, novedades y acciones frente a las metas de la vigencia."
    icon = "bar-chart"


class PaeReportView(PaePageView):
    template_name = "pae/reports.html"
    module_code = "pae.informes"
    title = "Informes del PAE"
    subtitle = "Catorce informes con filtros por vigencia, institucion, sede y periodo."
    icon = "file-text"

    REPORTS = [
        ("beneficiarios", "Reporte de beneficiarios", "Beneficiarios activos con sede, grado, grupo y modalidad.",
         "users", "/api/pae/beneficiarios/export/"),
        ("cobertura", "Reporte de cobertura", "Cobertura del programa frente a la matricula por sede y grado.",
         "target", "/api/pae/beneficiarios/export/"),
        ("raciones", "Reporte de raciones", "Raciones programadas, recibidas y entregadas por periodo.",
         "utensils", "/api/pae/entregas/export/"),
        ("entregas", "Reporte de entregas", "Detalle de la entrega diaria con horarios y cumplimiento.",
         "truck", "/api/pae/entregas/export/"),
        ("faltantes", "Reporte de faltantes", "Entregas con raciones faltantes o no entregadas.",
         "alert-triangle", "/api/pae/entregas/export/"),
        ("novedades", "Reporte de novedades", "Novedades por tipo, prioridad, estado y sede.",
         "activity", "/api/pae/novedades/export/"),
        ("visitas", "Reporte de visitas", "Visitas de seguimiento realizadas y su resultado.",
         "eye", "/api/pae/visitas/export/"),
        ("hallazgos", "Reporte de hallazgos", "Hallazgos por severidad, tipo y estado de tratamiento.",
         "alert-triangle", "/api/pae/hallazgos/export/"),
        ("mejoramiento", "Reporte de planes de mejoramiento", "Acciones correctivas, avance y vencimientos.",
         "refresh", "/api/pae/mejoramiento/export/"),
        ("pqrs", "Reporte de PQRS", "Peticiones, quejas y reclamos con tiempos de respuesta.",
         "message", "/api/pae/pqrs/export/"),
        ("operadores", "Reporte de operadores", "Operadores, contratos y desempeno en la entrega.",
         "truck", "/api/pae/operadores/export/"),
        ("contratos", "Reporte de contratos", "Contratos, valores, raciones y estado de ejecucion.",
         "file-text", "/api/pae/contratos/export/"),
        ("documentos", "Reporte de documentos", "Inventario documental con versiones y vencimientos.",
         "folder", "/api/pae/documentos/export/"),
        ("consolidado", "Informe consolidado PAE", "Consolidado de indicadores de la vigencia.",
         "bar-chart", "/api/pae/indicadores/export/"),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.institutions.models import Campus

        context.update({
            "reports": [
                {"code": code, "name": name, "description": description, "icon": icon, "endpoint": endpoint}
                for code, name, description, icon, endpoint in self.REPORTS
            ],
            "campuses": Campus.objects.filter(deleted_at__isnull=True).order_by("name"),
        })
        return context


class PaeImportView(PaePageView):
    """Importacion masiva desde archivos CSV o XLSX."""

    template_name = "pae/import.html"
    module_code = "pae.beneficiarios"
    title = "Importar informacion"
    subtitle = "Cargue beneficiarios, programaciones y ciclos de menu desde un archivo CSV o XLSX."
    icon = "upload"
    help_text = (
        "El archivo se valida completo antes de guardar: si una fila falla, no se guarda ninguna. "
        "Los estudiantes deben existir en el modulo de Estudiantes; aqui solo se vinculan al programa."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .imports import TEMPLATES, template_rows

        context["import_kinds"] = [
            dict(template_rows(kind), kind=kind) for kind in TEMPLATES
        ]
        return context


class PaeAuditView(PaeResourceView):
    module_code = "pae.auditoria"
    title = "Auditoria del PAE"
    subtitle = "Bitacora de las operaciones realizadas sobre el modulo, con usuario, IP y detalle del cambio."
    icon = "shield-check"
    endpoint = "/api/audit-logs/"
    base_params = {"module_prefix": "pae"}
    allow_create = False
    allow_edit = False
    allow_delete = False
    page_size = 50
    ordering = "-created_at"
    columns = [
        column("created_at", "Fecha y hora", type="datetime", width=170),
        column("user_label", "Usuario", type="avatar", subfield="role_label"),
        column("action", "Accion", type="badge", width=150, map={
            "CREATE": {"label": "Creacion", "tone": "success"},
            "UPDATE": {"label": "Modificacion", "tone": "info"},
            "DELETE": {"label": "Eliminacion", "tone": "danger"},
            "EXPORT": {"label": "Exportacion", "tone": "brand"},
            "APPROVE": {"label": "Aprobacion", "tone": "success"},
            "PROCESS": {"label": "Proceso", "tone": "brand"},
            "ERROR": {"label": "Error", "tone": "danger"},
        }),
        column("module_name", "Modulo", width=200),
        column("object_label", "Registro", type="truncate", width=240),
        column("ip_address", "IP", type="mono", width=130),
    ]
    form_fields = []
    empty_title = "Sin registros de auditoria del PAE"
    empty_message = "Las operaciones sobre el modulo se registran automaticamente."


# ===========================================================================
# PAGINAS OPERATIVAS
# ===========================================================================
class PaeDeliverySheetView(PaePageView):
    template_name = "pae/delivery_sheet.html"
    module_code = "pae.entregas"
    title = "Planilla diaria de entregas"
    subtitle = "Registre en una sola pantalla las entregas programadas para la fecha seleccionada."
    icon = "clipboard-check"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PaePlan

        vigencia = context.get("pae_vigencia")
        context["plans"] = PaePlan.objects.filter(
            vigencia=vigencia, deleted_at__isnull=True, status__in=["APROBADO", "EN_EJECUCION"]
        ).select_related("campus") if vigencia else []
        return context


class PaeVerificationSheetView(PaePageView):
    template_name = "pae/verification_sheet.html"
    module_code = "pae.control"
    title = "Aplicacion de lista de verificacion"
    subtitle = "Marque cada criterio como cumple, no cumple o no aplica; el resultado se calcula automaticamente."
    icon = "clipboard-check"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PaeVerification

        vigencia = context.get("pae_vigencia")
        context["verifications"] = PaeVerification.objects.filter(
            vigencia=vigencia, deleted_at__isnull=True
        ).select_related("checklist", "campus").order_by("-verification_date")[:60] if vigencia else []
        return context


def menu_cycle_print(request, pk):
    """Ficha imprimible del ciclo de menu con dias, preparaciones e ingredientes."""
    require_permission(request.user, "pae.menus", "view")
    cycle = get_object_or_404(PaeMenuCycle, pk=pk, deleted_at__isnull=True)
    from core.configuration.models import ReportHeader
    from core.institutions.models import Institution

    institution = Institution.current()
    days = cycle.days.filter(deleted_at__isnull=True).prefetch_related(
        "preparations__ingredients"
    ).order_by("day_number")
    return render(request, "pae/menu_print.html", {
        "cycle": cycle,
        "days": days,
        "institution": institution,
        "header": ReportHeader.active(institution),
    })


def delivery_print(request, pk):
    """Acta imprimible de la entrega diaria."""
    require_permission(request.user, "pae.entregas", "view")
    delivery = get_object_or_404(PaeDelivery, pk=pk, deleted_at__isnull=True)
    from core.configuration.models import ReportHeader
    from core.institutions.models import Institution

    institution = Institution.current()
    return render(request, "pae/delivery_print.html", {
        "delivery": delivery,
        "institution": institution,
        "header": ReportHeader.active(institution),
    })
