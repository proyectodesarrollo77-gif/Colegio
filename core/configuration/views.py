"""Vistas HTML del modulo de configuracion."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

from .models import GradeDecimalConfig, ReportHeader, SystemParameter


class ReportHeaderView(ResourceView):
    module_code = "configuration.report_header"
    title = "Encabezado de Reportes"
    subtitle = "Configure el encabezado, pie de pagina y formato de todos los documentos impresos."
    icon = "printer"
    endpoint = "/api/report-headers/"
    template_name = "configuration/report_header.html"
    columns = [
        column("name", "Configuracion", width=240),
        column("line_1", "Linea 1", type="truncate", width=260),
        column("paper_size", "Papel", type="badge", tone="neutral", width=110),
        column("orientation", "Orientacion", type="badge", tone="info", width=130, map={
            "P": {"label": "Vertical", "tone": "info"},
            "L": {"label": "Horizontal", "tone": "warning"},
        }),
        column("show_logo", "Logo", type="boolean", width=90, align="center"),
        column("is_default", "Por defecto", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("name", "Nombre de la configuracion", required=True, col="half"),
        field("line_1", "Linea 1", placeholder="INSTITUCION EDUCATIVA ..."),
        field("line_2", "Linea 2", placeholder="Resolucion de aprobacion ..."),
        field("line_3", "Linea 3", placeholder="DANE - NIT"),
        field("line_4", "Linea 4", placeholder="Direccion - Telefono - Ciudad"),
        field("logo_position", "Posicion del logo", type="select", col="third", options=choices_to_options([
            ("left", "Izquierda"), ("center", "Centro"), ("right", "Derecha"),
        ])),
        field("paper_size", "Tamano de papel", type="select", col="third", options=choices_to_options([
            ("LETTER", "Carta"), ("A4", "A4"), ("LEGAL", "Oficio"),
        ])),
        field("orientation", "Orientacion", type="select", col="third", options=choices_to_options([
            ("P", "Vertical"), ("L", "Horizontal"),
        ])),
        field("margin_top", "Margen superior (mm)", type="number", col="quarter", default=15),
        field("margin_bottom", "Margen inferior (mm)", type="number", col="quarter", default=15),
        field("margin_left", "Margen izquierdo (mm)", type="number", col="quarter", default=12),
        field("margin_right", "Margen derecho (mm)", type="number", col="quarter", default=12),
        field("footer_text", "Texto de pie de pagina"),
        field("watermark", "Marca de agua", col="half"),
        field("show_logo", "Mostrar logotipo", type="boolean", col="half", default=True),
        field("show_seal", "Mostrar sello", type="boolean", col="half"),
        field("show_page_numbers", "Numerar paginas", type="boolean", col="half", default=True),
        field("show_print_date", "Mostrar fecha de impresion", type="boolean", col="half", default=True),
        field("is_default", "Encabezado por defecto", type="boolean", col="half"),
    ]
    empty_title = "Sin encabezados configurados"
    empty_message = "Cree el encabezado institucional que se usara en boletines y certificados."


class GradeDecimalView(ResourceView):
    module_code = "configuration.grade_decimals"
    title = "Decimas de Notas"
    subtitle = "Reglas de aproximacion y redondeo aplicadas al consolidar calificaciones."
    icon = "sparkles"
    endpoint = "/api/grade-decimals/"
    template_name = "configuration/grade_decimals.html"
    columns = [
        column("name", "Configuracion", width=240),
        column("school_year_name", "Ano lectivo", width=160),
        column("decimals", "Decimales", type="number", width=110, align="center"),
        column("rounding_display", "Aproximacion", type="badge", tone="info", width=220),
        column("round_from", "Desde", type="number", decimals=2, width=100, align="right"),
        column("passing_grade", "Aprobatoria", type="number", decimals=2, width=120, align="right"),
        column("is_default", "Por defecto", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", "/api/school-years/options/", required=True, col="half"),
        field("name", "Nombre", required=True, col="half"),
        field("decimals", "Numero de decimales", type="number", col="half", default=1, min=0, max=3),
        field("rounding_mode", "Modo de aproximacion", type="select", col="half",
              options=choices_to_options(GradeDecimalConfig.ROUNDING_CHOICES)),
        field("round_from", "Aproximar a partir de", type="number", step="0.01", col="half", default=0.5,
              hint="Aplica solo con el modo 'Aproximar desde una decima especifica'."),
        field("minimum_grade", "Nota minima", type="number", step="0.01", col="third", default=1),
        field("passing_grade", "Nota aprobatoria", type="number", step="0.01", col="third", default=3),
        field("maximum_grade", "Nota maxima", type="number", step="0.01", col="third", default=5),
        field("apply_to_period", "Aplicar a notas de periodo", type="boolean", col="half", default=True),
        field("apply_to_area", "Aplicar a promedio de area", type="boolean", col="half", default=True),
        field("apply_to_final", "Aplicar a nota final", type="boolean", col="half", default=True),
        field("is_default", "Configuracion por defecto", type="boolean", col="half", default=True),
    ]
    empty_title = "Sin configuracion de decimas"
    empty_message = "Defina como se aproximan las notas al consolidar periodos y boletines."


class SystemParameterView(ResourceView):
    module_code = "configuration.parameters"
    title = "Parametros del Sistema"
    subtitle = "Valores globales que gobiernan el comportamiento de la plataforma."
    icon = "settings"
    endpoint = "/api/system-parameters/"
    columns = [
        column("label", "Parametro", width=280),
        column("key", "Clave", type="mono", width=200),
        column("value", "Valor", type="truncate", width=220),
        column("value_type", "Tipo", type="badge", tone="neutral", width=120),
        column("group", "Grupo", type="badge", tone="brand", width=150),
        column("is_editable", "Editable", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        field("key", "Clave", required=True, col="half", hint="Identificador unico en mayusculas."),
        field("label", "Etiqueta", required=True, col="half"),
        field("value", "Valor", type="textarea", rows=3),
        field("value_type", "Tipo de dato", type="select", col="half",
              options=choices_to_options(SystemParameter.TYPE_CHOICES)),
        field("group", "Grupo", col="half", default="General"),
        field("help_text", "Texto de ayuda"),
        field("is_editable", "Editable", type="boolean", col="half", default=True),
    ]
    filters = [
        {"name": "group", "label": "Todos los grupos", "type": "select", "options": [
            {"value": group, "label": group}
            for group in ["General", "Academico", "Seguridad", "Notificaciones", "Documentos"]
        ]},
    ]
    empty_title = "Sin parametros definidos"
    empty_message = "Ejecute el comando seed_configuration para cargar los parametros base."
