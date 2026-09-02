"""
Registro de modulos: es la unica fuente de la navegacion y de la matriz de
permisos.

Dos claves gobiernan lo que ve el Super Administrador:

  ``platform``              la pantalla administra la plataforma entera, no una
                            institucion. Son las unicas que ve mientras no haya
                            entrado a ninguna.
  ``hide_for_super_admin``  la pantalla no le corresponde nunca, porque tiene
                            otra equivalente que si distingue de que institucion
                            se trata.

No se pueden expresar con permisos: el Super Administrador los recibe todos.
"""
from __future__ import annotations

# group: agrupador visual del sidebar
# code : identificador unico usado por config.permissions
# url  : nombre de ruta Django (namespace:name) o None si es solo agrupador
MODULE_REGISTRY = [
    {
        "code": "dashboard", "platform": True,
        "name": "Dashboard",
        "icon": "layout-dashboard",
        "url": "dashboard:index",
        "group": "Principal",
        "order": 10,
        "children": [],
    },
    {
        "code": "institutions", "platform": True,
        "name": "Institucion",
        "icon": "building",
        "url": None,
        "group": "Principal",
        "order": 20,
        "children": [
            # El Super Administrador no la ve: administra los datos de cualquier
            # institucion desde el Panel de Instituciones, que si distingue de cual
            # se trata. Esta pantalla edita la institucion activa y para el resulta
            # ambigua.
            {"code": "institutions.profile", "name": "Datos Institucionales",
             "url": "institutions:profile", "hide_for_super_admin": True},
            {"code": "institutions.campuses", "name": "Sedes y Jornadas", "url": "institutions:campuses"},
            {"code": "institutions.panel", "platform": True, "name": "Panel de Instituciones", "url": "institutions:panel", "icon": "grid"},
        ],
    },
    {
        "code": "configuration", "platform": True,
        "name": "Configuracion",
        "icon": "settings",
        "url": None,
        "group": "Administracion",
        "order": 30,
        "children": [
            {"code": "configuration.profiles", "platform": True, "name": "Acceso de Perfiles", "url": "configuration:profiles"},
            {"code": "configuration.report_header", "name": "Encabezado de Reportes", "url": "configuration:report_header"},
            {"code": "configuration.grade_decimals", "name": "Decimas de Notas", "url": "configuration:grade_decimals"},
            {"code": "configuration.parameters", "platform": True, "name": "Parametros del Sistema", "url": "configuration:parameters"},
        ],
    },
    {
        "code": "users", "platform": True,
        "name": "Usuarios",
        "icon": "users",
        "url": None,
        "group": "Administracion",
        "order": 40,
        "children": [
            {"code": "users.management", "platform": True, "name": "Gestion de Usuarios", "url": "users:management"},
            {"code": "users.students", "name": "Usuarios de Estudiantes", "url": "users:students"},
            {"code": "users.coordinators", "name": "Usuarios Coordinadores", "url": "users:coordinators"},
            {"code": "users.credentials", "platform": True, "name": "Certificados Usuario y Contrasena", "url": "users:credentials"},
            {"code": "users.access_report", "platform": True, "name": "Reporte de Accesos", "url": "users:access_report"},
            {"code": "users.authenticator", "platform": True, "name": "Google Authenticator", "url": "users:authenticator"},
        ],
    },
    {
        "code": "academic",
        "name": "Directiva",
        "icon": "compass",
        "url": None,
        "group": "Gestion Academica",
        "order": 50,
        "children": [
            {"code": "academic.years", "name": "Ano Lectivo", "url": "academic:years"},
            {"code": "academic.periods", "name": "Periodo Academico", "url": "academic:periods"},
            {"code": "academic.scales", "name": "Escala Valorativa", "url": "academic:scales"},
            {"code": "academic.dimensions", "name": "Dimensiones Valorativas", "url": "academic:dimensions"},
            {"code": "academic.areas", "name": "Areas", "url": "academic:areas"},
            {"code": "academic.subjects", "name": "Asignaturas", "url": "academic:subjects"},
            {"code": "academic.levels", "name": "Niveles Educativos", "url": "academic:levels"},
            {"code": "academic.grades", "name": "Grados", "url": "academic:grades"},
            {"code": "academic.groups", "name": "Grupos", "url": "academic:groups"},
            {"code": "academic.processes", "name": "Procesos Academicos", "url": "academic:processes"},
            {"code": "academic.judgments", "name": "Juicios Valorativos", "url": "academic:judgments"},
            {"code": "academic.coexistence", "name": "Convivencia", "url": "academic:coexistence"},
            {"code": "academic.purposes", "name": "Propositos", "url": "academic:purposes"},
        ],
    },
    {
        "code": "students",
        "name": "Estudiantes",
        "icon": "graduation-cap",
        "url": None,
        "group": "Gestion Academica",
        "order": 60,
        "children": [
            {"code": "students.registry", "name": "Registro de Estudiantes", "url": "students:registry"},
            {"code": "students.enrollment", "name": "Matricula", "url": "students:enrollment"},
            {"code": "students.query", "name": "Consulta", "url": "students:query"},
            {"code": "students.promotion", "name": "Promocion", "url": "students:promotion"},
            {"code": "students.certificates", "name": "Certificados", "url": "students:certificates"},
            {"code": "students.resume", "name": "Hoja de Vida", "url": "students:resume"},
            {"code": "students.lists", "name": "Listados", "url": "students:lists"},
            {"code": "students.admissions", "name": "Admisiones", "url": "students:admissions"},
            {"code": "students.inscriptions", "name": "Inscripciones", "url": "students:inscriptions"},
            {"code": "students.guardians", "name": "Acudientes", "url": "students:guardians"},
        ],
    },
    {
        "code": "teachers",
        "name": "Docentes",
        "icon": "presentation",
        "url": None,
        "group": "Gestion Academica",
        "order": 70,
        "children": [
            {"code": "teachers.registry", "name": "Registro Docente", "url": "teachers:registry"},
            {"code": "teachers.subjects", "name": "Asignaturas", "url": "teachers:subjects"},
            {"code": "teachers.schedules", "name": "Horarios", "url": "teachers:schedules"},
            {"code": "teachers.load", "name": "Carga Academica", "url": "teachers:load"},
            {"code": "teachers.processes", "name": "Procesos Academicos", "url": "teachers:processes"},
        ],
    },
    {
        "code": "evaluations",
        "name": "Evaluaciones",
        "icon": "clipboard-check",
        "url": None,
        "group": "Gestion Academica",
        "order": 80,
        "children": [
            {"code": "evaluations.grades", "name": "Asignacion de Notas", "url": "evaluations:grades"},
            {"code": "evaluations.judgments", "name": "Juicios Valorativos", "url": "evaluations:judgments"},
            {"code": "evaluations.qualitative", "name": "Evaluacion Cualitativa", "url": "evaluations:qualitative"},
            {"code": "evaluations.preschool", "name": "Propositos Preescolar", "url": "evaluations:preschool"},
            {"code": "evaluations.bilingual", "name": "Modulo Bilingue", "url": "evaluations:bilingual"},
        ],
    },
    {
        "code": "attendance",
        "name": "Asistencia",
        "icon": "calendar-check",
        "url": None,
        "group": "Gestion Academica",
        "order": 85,
        "children": [
            {"code": "attendance.register", "name": "Registro de Asistencia", "url": "attendance:register"},
            {"code": "attendance.report", "name": "Reporte de Inasistencias", "url": "attendance:report"},
        ],
    },
    {
        "code": "recoveries",
        "name": "Recuperaciones",
        "icon": "refresh",
        "url": None,
        "group": "Gestion Academica",
        "order": 90,
        "children": [
            {"code": "recoveries.plans", "name": "Planes de Recuperacion", "url": "recoveries:plans"},
            {"code": "recoveries.activities", "name": "Actividades Complementarias", "url": "recoveries:activities"},
            {"code": "recoveries.bilingual", "name": "Recuperacion Bilingue", "url": "recoveries:bilingual"},
            {"code": "recoveries.results", "name": "Resultados", "url": "recoveries:results"},
        ],
    },
    {
        "code": "promotion",
        "name": "Promocion y Boletin Final",
        "icon": "award",
        "url": None,
        "group": "Gestion Academica",
        "order": 100,
        "children": [
            {"code": "promotion.closing", "name": "Cierre Academico", "url": "promotion:closing"},
            {"code": "promotion.results", "name": "Promocion Estudiantil", "url": "promotion:results"},
            {"code": "promotion.final_reports", "name": "Boletines Finales", "url": "promotion:final_reports"},
        ],
    },
    {
        "code": "emphases",
        "name": "Enfasis y Disciplinas",
        "icon": "target",
        "url": None,
        "group": "Gestion Academica",
        "order": 110,
        "children": [
            {"code": "emphases.catalog", "name": "Enfasis", "url": "emphases:catalog"},
            {"code": "emphases.groups", "name": "Apertura de Grupos", "url": "emphases:groups"},
            {"code": "emphases.enrollment", "name": "Matriculas de Enfasis", "url": "emphases:enrollment"},
        ],
    },
    {
        "code": "tutoring",
        "name": "Tutoria",
        "icon": "heart-handshake",
        "url": None,
        "group": "Convivencia",
        "order": 120,
        "children": [
            {"code": "tutoring.tutors", "name": "Tutores", "url": "tutoring:tutors"},
            {"code": "tutoring.judgments", "name": "Juicios de Tutoria", "url": "tutoring:judgments"},
            {"code": "tutoring.coexistence", "name": "Convivencia", "url": "tutoring:coexistence"},
            {"code": "tutoring.reports", "name": "Reportes de Tutoria", "url": "tutoring:reports"},
            {"code": "tutoring.block", "name": "Bloqueo de Boletin", "url": "tutoring:block"},
        ],
    },
    {
        "code": "observer",
        "name": "Observador",
        "icon": "eye",
        "url": None,
        "group": "Convivencia",
        "order": 130,
        "children": [
            {"code": "observer.categories", "name": "Tipos de Observacion", "url": "observer:categories"},
            {"code": "observer.records", "name": "Registro de Observaciones", "url": "observer:records"},
            {"code": "observer.history", "name": "Historial Estudiantil", "url": "observer:history"},
        ],
    },
    {
        "code": "agenda",
        "name": "Agenda Virtual",
        "icon": "calendar",
        "url": None,
        "group": "Comunicacion",
        "order": 140,
        "children": [
            {"code": "agenda.calendar", "name": "Calendario Institucional", "url": "agenda:calendar"},
            {"code": "agenda.activities", "name": "Actividades", "url": "agenda:activities"},
            {"code": "agenda.mail", "name": "Correos y Circulares", "url": "agenda:mail"},
        ],
    },
    {
        "code": "classroom",
        "name": "Aula Virtual",
        "icon": "monitor-play",
        "url": None,
        "group": "Comunicacion",
        "order": 150,
        "children": [
            {"code": "classroom.courses", "name": "Cursos", "url": "classroom:courses"},
            {"code": "classroom.materials", "name": "Material Academico", "url": "classroom:materials"},
            {"code": "classroom.activities", "name": "Actividades", "url": "classroom:activities"},
            {"code": "classroom.tracking", "name": "Seguimiento", "url": "classroom:tracking"},
        ],
    },
    {
        "code": "elections",
        "name": "Elecciones",
        "icon": "vote",
        "url": None,
        "group": "Comunicacion",
        "order": 160,
        "children": [
            {"code": "elections.setup", "name": "Configuracion Electoral", "url": "elections:setup"},
            {"code": "elections.voting", "name": "Votacion Digital", "url": "elections:voting"},
            {"code": "elections.results", "name": "Resultados", "url": "elections:results"},
        ],
    },
    {
        "code": "documents",
        "name": "Documentos Institucionales",
        "icon": "file-text",
        "url": None,
        "group": "Documentacion",
        "order": 170,
        "children": [
            {"code": "documents.configuration", "name": "Configuracion Documental", "url": "documents:configuration"},
            {"code": "documents.printing", "name": "Impresion de Documentos", "url": "documents:printing"},
        ],
    },
    {
        "code": "reports",
        "name": "Reportes",
        "icon": "bar-chart",
        "url": None,
        "group": "Documentacion",
        "order": 180,
        "children": [
            {"code": "reports.academic", "name": "Reportes Academicos", "url": "reports:academic"},
            {"code": "reports.statistics", "name": "Reportes Estadisticos", "url": "reports:statistics"},
            {"code": "reports.administrative", "name": "Reportes Administrativos", "url": "reports:administrative"},
        ],
    },
    {
        "code": "extensions",
        "name": "Extensiones",
        "icon": "puzzle",
        "url": None,
        "group": "Documentacion",
        "order": 190,
        "children": [
            {"code": "extensions.forms", "name": "Formularios", "url": "extensions:forms"},
            {"code": "extensions.spaces", "name": "Espacios Virtuales", "url": "extensions:spaces"},
        ],
    },
    {
        "code": "audit", "platform": True,
        "name": "Auditoria",
        "icon": "shield-check",
        "url": None,
        "group": "Seguridad",
        "order": 200,
        "children": [
            {"code": "audit.log", "platform": True, "name": "Bitacora de Acciones", "url": "audit:log"},
            {"code": "audit.sessions", "platform": True, "name": "Sesiones Activas", "url": "audit:sessions"},
        ],
    },
    {
        "code": "pae",
        "name": "PAE",
        "icon": "utensils",
        "url": None,
        "group": "Alimentacion Escolar",
        "order": 300,
        "children": [
            {"code": "pae.dashboard", "name": "Dashboard PAE", "url": "pae:dashboard", "icon": "layout-dashboard"},
            {"code": "pae.configuracion", "name": "Configuracion del Programa", "url": "pae:configuration", "icon": "settings"},
            {"code": "pae.diagnostico", "name": "Diagnostico de Sedes", "url": "pae:diagnosis", "icon": "compass"},
            {"code": "pae.priorizacion", "name": "Priorizacion de Poblacion", "url": "pae:prioritization", "icon": "target"},
            {"code": "pae.beneficiarios", "name": "Beneficiarios", "url": "pae:beneficiaries", "icon": "users"},
            {"code": "pae.planeacion", "name": "Planeacion Operativa", "url": "pae:plans", "icon": "calendar-check"},
            {"code": "pae.menus", "name": "Ciclos de Menu", "url": "pae:menus", "icon": "layers"},
            {"code": "pae.operadores", "name": "Operadores", "url": "pae:operators", "icon": "building"},
            {"code": "pae.contratos", "name": "Contratos y Convenios", "url": "pae:contracts", "icon": "file-text"},
            {"code": "pae.programacion", "name": "Programacion de Entregas", "url": "pae:schedules", "icon": "calendar"},
            {"code": "pae.entregas", "name": "Entregas Diarias", "url": "pae:deliveries", "icon": "truck"},
            {"code": "pae.control", "name": "Control de Calidad", "url": "pae:quality", "icon": "clipboard-check"},
            {"code": "pae.visitas", "name": "Visitas de Supervision", "url": "pae:visits", "icon": "eye"},
            {"code": "pae.novedades", "name": "Novedades e Incidencias", "url": "pae:incidents", "icon": "alert-triangle"},
            {"code": "pae.mejoramiento", "name": "Planes de Mejoramiento", "url": "pae:improvement", "icon": "refresh"},
            {"code": "pae.pqrs", "name": "PQRS", "url": "pae:pqrs", "icon": "message"},
            {"code": "pae.participacion", "name": "Participacion Ciudadana", "url": "pae:participation", "icon": "heart-handshake"},
            {"code": "pae.documentos", "name": "Documentos del Programa", "url": "pae:documents", "icon": "folder"},
            {"code": "pae.evidencias", "name": "Evidencias", "url": "pae:evidence", "icon": "paperclip"},
            {"code": "pae.indicadores", "name": "Indicadores", "url": "pae:indicators", "icon": "bar-chart"},
            {"code": "pae.informes", "name": "Informes PAE", "url": "pae:reports", "icon": "list"},
            {"code": "pae.auditoria", "name": "Auditoria del PAE", "url": "pae:audit", "icon": "shield-check"},
        ],
    },
]

GROUP_ORDER = [
    "Principal",
    "Administracion",
    "Gestion Academica",
    "Convivencia",
    "Comunicacion",
    "Documentacion",
    "Alimentacion Escolar",
    "Seguridad",
]


def iter_modules():
    """Genera tuplas planas (code, name, parent_code, icon, url, group, order)."""
    for order, module in enumerate(MODULE_REGISTRY):
        yield {
            "code": module["code"],
            "name": module["name"],
            "parent": None,
            "icon": module.get("icon", "circle"),
            "url_name": module.get("url"),
            "group": module.get("group", "Principal"),
            "order": module.get("order", order * 10),
        }
        for child_order, child in enumerate(module.get("children", [])):
            yield {
                "code": child["code"],
                "name": child["name"],
                "parent": module["code"],
                "icon": child.get("icon", "dot"),
                "url_name": child.get("url"),
                "group": module.get("group", "Principal"),
                "order": module.get("order", order * 10) + child_order + 1,
            }


MODULE_CODES = [item["code"] for item in iter_modules()]

MODULE_INDEX = {item["code"]: item for item in iter_modules()}


def module_name(code: str) -> str:
    entry = MODULE_INDEX.get(code)
    return entry["name"] if entry else code


# Permisos por defecto asignados a cada rol al ejecutar `seed_permissions`.
# "*" concede todas las acciones sobre todos los modulos.
DEFAULT_ROLE_MATRIX = {
    "SUPER_ADMIN": {"*": ["view", "create", "edit", "delete", "export", "approve"]},
    "RECTOR": {
        "*": ["view", "export", "approve"],
        # El panel cruza la frontera entre instituciones: es exclusivo del
        # Super Administrador, aunque el rector tenga el comodin.
        "institutions.panel": [],
        "students": ["view", "create", "edit", "export", "approve"],
        "academic": ["view", "create", "edit", "export", "approve"],
        "promotion": ["view", "create", "edit", "export", "approve"],
        "documents": ["view", "create", "edit", "export", "approve"],
        "reports": ["view", "export"],
        "audit": ["view", "export"],
    },
    "COORDINADOR": {
        "dashboard": ["view"],
        "academic": ["view", "create", "edit", "export"],
        "students": ["view", "create", "edit", "export"],
        "teachers": ["view", "create", "edit", "export"],
        "evaluations": ["view", "create", "edit", "export", "approve"],
        "attendance": ["view", "create", "edit", "export"],
        "recoveries": ["view", "create", "edit", "export", "approve"],
        "promotion": ["view", "create", "edit", "export"],
        "tutoring": ["view", "create", "edit", "export"],
        "observer": ["view", "create", "edit", "export"],
        "emphases": ["view", "create", "edit", "export"],
        "agenda": ["view", "create", "edit", "export"],
        "classroom": ["view", "create", "edit", "export"],
        "reports": ["view", "export"],
        "documents": ["view", "export"],
        "elections": ["view", "create", "edit", "export"],
        "pae": ["view", "export"],
    },
    "SECRETARIA": {
        "dashboard": ["view"],
        "students": ["view", "create", "edit", "export"],
        "users": ["view", "create", "edit", "export"],
        "documents": ["view", "create", "edit", "export"],
        "reports": ["view", "export"],
        "agenda": ["view", "create", "edit"],
        "attendance": ["view", "export"],
        "institutions": ["view"],
    },
    "DOCENTE": {
        "dashboard": ["view"],
        "evaluations": ["view", "create", "edit"],
        "attendance": ["view", "create", "edit"],
        "recoveries": ["view", "create", "edit"],
        "classroom": ["view", "create", "edit"],
        "agenda": ["view", "create"],
        "observer": ["view", "create"],
        "students": ["view"],
        "teachers": ["view"],
        "reports": ["view", "export"],
    },
    "TUTOR": {
        "dashboard": ["view"],
        "tutoring": ["view", "create", "edit", "export"],
        "observer": ["view", "create", "edit", "export"],
        "attendance": ["view", "export"],
        "students": ["view"],
        "agenda": ["view", "create"],
        "reports": ["view", "export"],
    },
    "ESTUDIANTE": {
        "dashboard": ["view"],
        "classroom": ["view"],
        "agenda": ["view"],
        "elections.voting": ["view", "create"],
        "extensions": ["view"],
    },
    "ACUDIENTE": {
        "dashboard": ["view"],
        "agenda": ["view"],
        "classroom": ["view"],
        "extensions": ["view"],
    },
    # -----------------------------------------------------------------
    # Perfiles del Programa de Alimentacion Escolar (PAE).
    # El perfil ADMINISTRADOR del PAE corresponde a SUPER_ADMIN y el perfil
    # DIRECTIVO a RECTOR, que ya cubren el modulo mediante el comodin "*".
    # -----------------------------------------------------------------
    "RESPONSABLE_PAE": {
        "dashboard": ["view"],
        "pae": ["view", "create", "edit", "delete", "export", "approve"],
        "pae.auditoria": ["view", "export"],
        "students": ["view", "export"],
        "academic": ["view"],
        "institutions": ["view"],
        "reports": ["view", "export"],
    },
    "COORDINADOR_SEDE": {
        "dashboard": ["view"],
        "pae.dashboard": ["view"],
        "pae.configuracion": ["view"],
        "pae.diagnostico": ["view", "create", "edit", "export"],
        "pae.priorizacion": ["view", "export"],
        "pae.beneficiarios": ["view", "create", "edit", "export"],
        "pae.planeacion": ["view", "export"],
        "pae.menus": ["view", "export"],
        "pae.operadores": ["view"],
        "pae.contratos": ["view"],
        "pae.programacion": ["view", "create", "edit", "export"],
        "pae.entregas": ["view", "create", "edit", "export"],
        "pae.control": ["view", "create", "edit", "export"],
        "pae.visitas": ["view", "export"],
        "pae.novedades": ["view", "create", "edit", "export"],
        "pae.mejoramiento": ["view", "create", "edit", "export"],
        "pae.pqrs": ["view", "create", "edit", "export"],
        "pae.participacion": ["view", "create", "edit", "export"],
        "pae.documentos": ["view", "create", "export"],
        "pae.evidencias": ["view", "create", "export"],
        "pae.indicadores": ["view", "export"],
        "pae.informes": ["view", "export"],
        "students": ["view"],
    },
    "OPERADOR_PAE": {
        "dashboard": ["view"],
        "pae.dashboard": ["view"],
        "pae.beneficiarios": ["view"],
        "pae.planeacion": ["view"],
        "pae.menus": ["view"],
        "pae.programacion": ["view"],
        "pae.entregas": ["view", "create", "edit"],
        "pae.novedades": ["view", "create"],
        "pae.documentos": ["view", "create"],
        "pae.evidencias": ["view", "create"],
        "pae.informes": ["view", "export"],
    },
    "SUPERVISOR_PAE": {
        "dashboard": ["view"],
        "pae": ["view", "export"],
        "pae.control": ["view", "create", "edit", "export", "approve"],
        "pae.visitas": ["view", "create", "edit", "export", "approve"],
        "pae.novedades": ["view", "create", "edit", "export"],
        "pae.mejoramiento": ["view", "create", "edit", "export", "approve"],
        "pae.pqrs": ["view", "create", "edit", "export"],
    },
    "AUDITOR_PAE": {
        "dashboard": ["view"],
        "pae": ["view", "export"],
        "pae.auditoria": ["view", "export"],
        "audit": ["view", "export"],
        "reports": ["view", "export"],
    },
    "CONSULTA_PAE": {
        "dashboard": ["view"],
        "pae.dashboard": ["view"],
        "pae.beneficiarios": ["view"],
        "pae.menus": ["view"],
        "pae.programacion": ["view"],
        "pae.entregas": ["view"],
        "pae.indicadores": ["view"],
        "pae.informes": ["view"],
    },
}
