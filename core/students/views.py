"""Vistas HTML del modulo de estudiantes."""
from __future__ import annotations

from django.shortcuts import get_object_or_404, render

from config.permissions import require_permission
from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote
from core.users.models import DOCUMENT_TYPES, GENDER_CHOICES

from .models import BLOOD_TYPES, STRATUM_CHOICES, Student, StudentCertificate
from .services import student_academic_summary

STUDENT_OPTIONS = "/api/students/options/"
GROUP_OPTIONS = "/api/groups/options/"
GRADE_OPTIONS = "/api/grades/options/"
YEAR_OPTIONS = "/api/school-years/options/"

STUDENT_COLUMNS = [
    column("full_name", "Estudiante", type="avatar", subfield="document_number"),
    column("student_code", "Codigo", type="mono", width=120),
    column("grade_name", "Grado", type="badge", tone="brand", width=140),
    column("group_name", "Grupo", width=120),
    column("age", "Edad", type="number", width=80, align="center"),
    column("guardian_name", "Acudiente", width=200),
    column("status", "Estado", type="badge", width=120, map={
        "ACTIVO": {"label": "Activo", "tone": "success"},
        "RETIRADO": {"label": "Retirado", "tone": "danger"},
        "EGRESADO": {"label": "Egresado", "tone": "info"},
        "TRASLADADO": {"label": "Trasladado", "tone": "warning"},
        "SUSPENDIDO": {"label": "Suspendido", "tone": "warning"},
        "INACTIVO": {"label": "Inactivo", "tone": "neutral"},
    }),
]

STUDENT_FORM = [
    field("section_basic", "Informacion basica", type="section"),
    remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
    field("document_type", "Tipo de documento", type="select", col="half",
          options=choices_to_options(DOCUMENT_TYPES), default="TI"),
    field("document_number", "Numero de documento", required=True, col="half"),
    field("document_city", "Lugar de expedicion", col="half"),
    field("first_name", "Nombres", required=True, col="half"),
    field("last_name", "Apellidos", required=True, col="half"),
    field("birth_date", "Fecha de nacimiento", type="date", col="half"),
    field("birth_place", "Lugar de nacimiento", col="half"),
    field("gender", "Genero", type="select", col="half", options=choices_to_options(GENDER_CHOICES)),
    field("photo", "Fotografia", type="image", col="half"),
    field("section_contact", "Contacto y residencia", type="section"),
    field("email", "Correo electronico", type="email", col="half"),
    field("mobile", "Celular", col="half"),
    field("phone", "Telefono fijo", col="half"),
    field("address", "Direccion de residencia", col="half"),
    field("neighborhood", "Barrio", col="third"),
    field("city", "Ciudad", col="third"),
    field("department", "Departamento", col="third"),
    field("stratum", "Estrato", type="select", col="half", options=choices_to_options(
        [(str(v), label) for v, label in STRATUM_CHOICES]
    )),
    field("section_health", "Informacion de salud", type="section"),
    field("blood_type", "Grupo sanguineo", type="select", col="third", options=choices_to_options(BLOOD_TYPES)),
    field("eps", "EPS", col="third"),
    field("disability", "Condicion de discapacidad", col="third"),
    field("allergies", "Alergias", type="textarea", col="half", rows=2),
    field("medical_notes", "Observaciones medicas", type="textarea", col="half", rows=2),
    field("emergency_contact", "Contacto de emergencia", col="half"),
    field("emergency_phone", "Telefono de emergencia", col="half"),
    field("section_extra", "Informacion complementaria", type="section"),
    field("ethnicity", "Etnia", col="third"),
    field("sisben", "SISBEN", col="third"),
    field("religion", "Religion", col="third"),
    field("previous_school", "Institucion anterior", col="half"),
    field("entry_date", "Fecha de ingreso", type="date", col="half"),
    field("status", "Estado", type="select", col="half", options=choices_to_options(Student.STATUS_CHOICES)),
    field("displaced", "Poblacion desplazada", type="boolean", col="half"),
    field("observations", "Observaciones", type="textarea"),
]


class StudentRegistryView(ResourceView):
    module_code = "students.registry"
    title = "Registro de Estudiantes"
    subtitle = "Base de datos completa de la poblacion estudiantil."
    icon = "graduation-cap"
    endpoint = "/api/students/"
    columns = STUDENT_COLUMNS
    form_fields = STUDENT_FORM
    search_placeholder = "Buscar por nombre, documento o codigo..."
    row_actions = [
        {"name": "resume", "label": "Hoja de vida", "icon": "file-text", "url": "/estudiantes/{id}/hoja-de-vida/"},
    ]
    filters = [
        {"name": "status", "label": "Todos los estados", "type": "select",
         "options": choices_to_options([(v, l) for v, l in Student.STATUS_CHOICES])},
        {"name": "grade", "label": "Grado", "type": "remote", "endpoint": GRADE_OPTIONS},
        {"name": "group", "label": "Grupo", "type": "remote", "endpoint": GROUP_OPTIONS},
    ]
    empty_title = "Sin estudiantes registrados"
    empty_message = "Registre el primer estudiante o importe la informacion desde admisiones."


class StudentQueryView(StudentRegistryView):
    module_code = "students.query"
    title = "Consulta de Estudiantes"
    subtitle = "Consulta rapida de la informacion academica y de contacto."
    icon = "search"
    allow_create = False
    allow_edit = False
    allow_delete = False


class StudentListsView(StudentRegistryView):
    module_code = "students.lists"
    title = "Listados"
    subtitle = "Genere listados por grupo, grado o estado para impresion y exportacion."
    icon = "list"
    allow_create = False
    allow_edit = False
    allow_delete = False
    page_size = 100


class EnrollmentView(ResourceView):
    module_code = "students.enrollment"
    title = "Matricula"
    subtitle = "Matricule estudiantes en los grupos del ano lectivo vigente."
    icon = "clipboard-check"
    endpoint = "/api/enrollments/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("enrollment_number", "N. Matricula", type="mono", width=150),
        column("grade_name", "Grado", type="badge", tone="brand", width=130),
        column("group_name", "Grupo", width=120),
        column("enrollment_date", "Fecha", type="date", width=120),
        column("type_display", "Tipo", type="badge", tone="info", width=140),
        column("status", "Estado", type="badge", width=120, map={
            "ACTIVA": {"label": "Activa", "tone": "success"},
            "RETIRADA": {"label": "Retirada", "tone": "danger"},
            "TRASLADADA": {"label": "Trasladada", "tone": "warning"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
            "FINALIZADA": {"label": "Finalizada", "tone": "info"},
        }),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, required=True, col="half"),
        field("enrollment_date", "Fecha de matricula", type="date", col="half"),
        field("enrollment_type", "Tipo de matricula", type="select", col="half", options=choices_to_options([
            ("NUEVO", "Estudiante nuevo"), ("ANTIGUO", "Estudiante antiguo"),
            ("REINTEGRO", "Reintegro"), ("TRASLADO", "Traslado"),
        ])),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ACTIVA", "Activa"), ("RETIRADA", "Retirada"), ("TRASLADADA", "Trasladada"),
            ("CANCELADA", "Cancelada"), ("FINALIZADA", "Finalizada"),
        ])),
        field("folio", "Folio", col="third"),
        field("book", "Libro", col="third"),
        field("is_repeating", "Repitente", type="boolean", col="third"),
        field("scholarship", "Becado", type="boolean", col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "school_year", "label": "Ano lectivo", "type": "remote", "endpoint": YEAR_OPTIONS},
        {"name": "group", "label": "Grupo", "type": "remote", "endpoint": GROUP_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "ACTIVA", "label": "Activas"}, {"value": "RETIRADA", "label": "Retiradas"},
        ]},
    ]
    empty_title = "Sin matriculas registradas"
    empty_message = "Matricule estudiantes para habilitar la carga academica y las notas."


class GuardianView(ResourceView):
    module_code = "students.guardians"
    title = "Acudientes"
    subtitle = "Padres de familia y acudientes vinculados a los estudiantes."
    icon = "users"
    endpoint = "/api/guardians/"
    columns = [
        column("full_name", "Acudiente", type="avatar", subfield="email"),
        column("document_number", "Documento", type="mono", width=140),
        column("relation_display", "Parentesco", type="badge", tone="info", width=140),
        column("mobile", "Celular", width=140),
        column("occupation", "Ocupacion", width=180),
        column("students_count", "Estudiantes", type="number", width=120, align="center"),
    ]
    form_fields = [
        field("document_type", "Tipo de documento", type="select", col="half",
              options=choices_to_options(DOCUMENT_TYPES)),
        field("document_number", "Numero de documento", required=True, col="half"),
        field("first_name", "Nombres", required=True, col="half"),
        field("last_name", "Apellidos", required=True, col="half"),
        field("relation", "Parentesco", type="select", col="half", options=choices_to_options([
            ("PADRE", "Padre"), ("MADRE", "Madre"), ("ABUELO", "Abuelo(a)"),
            ("TIO", "Tio(a)"), ("HERMANO", "Hermano(a)"), ("TUTOR", "Tutor legal"), ("OTRO", "Otro"),
        ])),
        field("email", "Correo electronico", type="email", col="half"),
        field("mobile", "Celular", col="half"),
        field("phone", "Telefono", col="half"),
        field("address", "Direccion", col="half"),
        field("occupation", "Ocupacion", col="half"),
        field("workplace", "Lugar de trabajo", col="half"),
        field("education_level", "Nivel educativo", col="half"),
        field("lives_with_student", "Convive con el estudiante", type="boolean", col="half", default=True),
    ]


class AdmissionView(ResourceView):
    module_code = "students.admissions"
    title = "Admisiones"
    subtitle = "Proceso de admision de aspirantes: entrevista, evaluacion y aprobacion."
    icon = "user"
    endpoint = "/api/admissions/"
    columns = [
        column("applicant_name", "Aspirante", type="avatar", subfield="applicant_document"),
        column("grade_name", "Grado solicitado", type="badge", tone="brand", width=160),
        column("guardian_name", "Acudiente", width=190),
        column("guardian_phone", "Telefono", width=130),
        column("application_date", "Solicitud", type="date", width=120),
        column("score", "Puntaje", type="number", decimals=2, width=100, align="right"),
        column("status", "Estado", type="badge", width=150, map={
            "RECIBIDA": {"label": "Recibida", "tone": "neutral"},
            "EN_ESTUDIO": {"label": "En estudio", "tone": "info"},
            "ENTREVISTA": {"label": "Entrevista", "tone": "warning"},
            "APROBADA": {"label": "Aprobada", "tone": "success"},
            "RECHAZADA": {"label": "Rechazada", "tone": "danger"},
            "MATRICULADA": {"label": "Matriculada", "tone": "brand"},
        }),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("grade", "Grado solicitado", GRADE_OPTIONS, required=True, col="half"),
        field("applicant_document_type", "Tipo de documento", type="select", col="half",
              options=choices_to_options(DOCUMENT_TYPES)),
        field("applicant_document", "Documento del aspirante", required=True, col="half"),
        field("applicant_first_name", "Nombres", required=True, col="half"),
        field("applicant_last_name", "Apellidos", required=True, col="half"),
        field("birth_date", "Fecha de nacimiento", type="date", col="half"),
        field("gender", "Genero", type="select", col="half", options=choices_to_options(GENDER_CHOICES)),
        field("guardian_name", "Nombre del acudiente", required=True, col="half"),
        field("guardian_document", "Documento del acudiente", col="half"),
        field("guardian_email", "Correo del acudiente", type="email", required=True, col="half"),
        field("guardian_phone", "Telefono del acudiente", required=True, col="half"),
        field("previous_school", "Institucion anterior", col="half"),
        field("interview_date", "Fecha de entrevista", type="datetime-local", col="half"),
        field("score", "Puntaje", type="number", step="0.01", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("RECIBIDA", "Solicitud recibida"), ("EN_ESTUDIO", "En estudio"),
            ("ENTREVISTA", "Entrevista programada"), ("APROBADA", "Aprobada"),
            ("RECHAZADA", "Rechazada"), ("MATRICULADA", "Matriculada"),
        ])),
        field("observations", "Observaciones", type="textarea"),
    ]
    row_actions = [{"name": "convert", "label": "Convertir en estudiante", "icon": "arrow-right"}]


class InscriptionView(ResourceView):
    module_code = "students.inscriptions"
    title = "Inscripciones"
    subtitle = "Preinscripciones recibidas desde el formulario publico."
    icon = "mail"
    endpoint = "/api/inscriptions/"
    columns = [
        column("full_name", "Aspirante", type="avatar", subfield="email"),
        column("grade_name", "Grado de interes", type="badge", tone="brand", width=160),
        column("guardian_name", "Acudiente", width=190),
        column("phone", "Telefono", width=130),
        column("source", "Origen", type="badge", tone="neutral", width=110),
        column("created_at", "Recibida", type="datetime", width=160),
        column("status", "Estado", type="badge", width=150, map={
            "PENDIENTE": {"label": "Pendiente", "tone": "warning"},
            "CONTACTADO": {"label": "Contactado", "tone": "info"},
            "CONVERTIDA": {"label": "Convertida", "tone": "success"},
            "DESCARTADA": {"label": "Descartada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("grade", "Grado de interes", GRADE_OPTIONS, required=True, col="half"),
        field("full_name", "Nombre del aspirante", required=True, col="half"),
        field("document", "Documento", col="half"),
        field("birth_date", "Fecha de nacimiento", type="date", col="half"),
        field("guardian_name", "Nombre del acudiente", required=True, col="half"),
        field("email", "Correo electronico", type="email", required=True, col="half"),
        field("phone", "Telefono", required=True, col="half"),
        field("source", "Origen", col="half", default="WEB"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PENDIENTE", "Pendiente"), ("CONTACTADO", "Contactado"),
            ("CONVERTIDA", "Convertida"), ("DESCARTADA", "Descartada"),
        ])),
        field("message", "Mensaje", type="textarea"),
    ]
    row_actions = [{"name": "to-admission", "label": "Pasar a admision", "icon": "arrow-right"}]


class CertificateView(ResourceView):
    module_code = "students.certificates"
    title = "Certificados"
    subtitle = "Emision y consulta de certificados y constancias estudiantiles."
    icon = "file-text"
    endpoint = "/api/student-certificates/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("kind_display", "Tipo", type="badge", tone="brand", width=190),
        column("consecutive", "Consecutivo", type="mono", width=150),
        column("issued_at", "Emision", type="datetime", width=160),
        column("issued_by_name", "Emitido por", width=180),
        column("verification_code", "Codigo", type="mono", width=140),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, col="half"),
        field("kind", "Tipo de certificado", type="select", required=True, col="half",
              options=choices_to_options(StudentCertificate.KIND_CHOICES)),
        field("purpose", "Dirigido a", col="half", placeholder="quien interese"),
    ]
    row_actions = [
        {"name": "print", "label": "Imprimir", "icon": "printer", "url": "/estudiantes/certificados/{id}/imprimir/"},
    ]
    empty_title = "Sin certificados emitidos"
    empty_message = "Genere certificados de estudio, notas, conducta o paz y salvo."


class StudentResumeView(ModulePageView):
    template_name = "students/resume.html"
    module_code = "students.resume"
    title = "Hoja de Vida"
    subtitle = "Historial academico, disciplinario y documental del estudiante."
    icon = "file-text"


class StudentResumeDetailView(ModulePageView):
    template_name = "students/resume_detail.html"
    module_code = "students.resume"
    title = "Hoja de Vida del Estudiante"
    icon = "file-text"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, pk=self.kwargs["pk"], deleted_at__isnull=True)
        context.update(
            {
                "student": student,
                "page_subtitle": f"{student.display_name} - {student.document_number}",
                "enrollments": student.enrollments.select_related("group", "group__grade", "school_year")
                .order_by("-school_year__year"),
                "guardians": student.guardian_links.select_related("guardian"),
                "documents": student.documents.all(),
                "certificates": student.certificates.all()[:15],
                "observer_entries": student.observer_entries.select_related("category")[:15],
                "summary": student_academic_summary(student),
            }
        )
        return context


class PromotionQueryView(ResourceView):
    module_code = "students.promotion"
    title = "Promocion de Estudiantes"
    subtitle = "Resultado de promocion por estudiante y ano lectivo."
    icon = "award"
    endpoint = "/api/promotion-results/"
    allow_create = False
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("group_name", "Grupo", type="badge", tone="brand", width=130),
        column("average", "Promedio", type="grade", width=110, align="center"),
        column("failed_subjects", "Perdidas", type="number", width=100, align="center"),
        column("rank", "Puesto", type="number", width=90, align="center"),
        column("result", "Resultado", type="badge", width=200, map={
            "PROMOVIDO": {"label": "Promovido", "tone": "success"},
            "PROMOVIDO_COMPROMISO": {"label": "Promovido con compromiso", "tone": "warning"},
            "NO_PROMOVIDO": {"label": "No promovido", "tone": "danger"},
            "PENDIENTE_RECUPERACION": {"label": "Pendiente recuperacion", "tone": "warning"},
            "GRADUADO": {"label": "Graduado", "tone": "brand"},
            "RETIRADO": {"label": "Retirado", "tone": "neutral"},
        }),
        column("approved", "Aprobado", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        field("result", "Resultado", type="select", options=choices_to_options([
            ("PROMOVIDO", "Promovido"), ("PROMOVIDO_COMPROMISO", "Promovido con compromiso"),
            ("NO_PROMOVIDO", "No promovido"), ("PENDIENTE_RECUPERACION", "Pendiente de recuperacion"),
            ("GRADUADO", "Graduado"), ("RETIRADO", "Retirado"),
        ])),
        field("honor_roll", "Cuadro de honor", type="boolean", col="half"),
        field("observations", "Observaciones de la comision", type="textarea"),
    ]


def certificate_print(request, pk):
    require_permission(request.user, "students.certificates", "view")
    certificate = get_object_or_404(StudentCertificate, pk=pk)
    from core.configuration.models import ReportHeader
    from core.institutions.models import Institution

    institution = Institution.current()
    return render(
        request,
        "students/certificate_print.html",
        {
            "certificate": certificate,
            "institution": institution,
            "header": ReportHeader.active(institution),
        },
    )
