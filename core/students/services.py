"""Servicios del modulo de estudiantes: certificados y consolidados."""
from __future__ import annotations

from django.utils import timezone

MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def spanish_date(value=None):
    value = value or timezone.localdate()
    return f"{value.day} de {MONTHS[value.month - 1]} de {value.year}"


def certificate_context(certificate):
    from core.institutions.models import Institution

    student = certificate.student
    institution = student.institution or Institution.current()
    enrollment = student.current_enrollment
    return {
        "estudiante": student.display_name.upper(),
        "documento": f"{student.get_document_type_display()} {student.document_number}",
        "tipo_documento": student.get_document_type_display(),
        "numero_documento": student.document_number,
        "codigo": student.student_code,
        "grado": enrollment.group.grade.name if enrollment else "",
        "grupo": enrollment.group.name if enrollment else "",
        "ano": str(enrollment.school_year.year) if enrollment else str(timezone.localdate().year),
        "institucion": institution.name if institution else "",
        "rector": institution.rector_name if institution else "",
        "ciudad": institution.city if institution else "",
        "fecha": spanish_date(),
        "consecutivo": certificate.consecutive,
        "acudiente": student.main_guardian.full_name if student.main_guardian else "",
        "estado": student.get_status_display(),
        "dirigido_a": certificate.purpose or "quien interese",
    }


CERTIFICATE_TEMPLATES = {
    "ESTUDIO": (
        "El suscrito Rector de la institucion {institucion} hace constar que el(la) estudiante "
        "{estudiante}, identificado(a) con {documento}, se encuentra matriculado(a) en el grado "
        "{grado} - grupo {grupo} durante el ano lectivo {ano}, y su estado academico actual es "
        "{estado}.\n\nLa presente constancia se expide en {ciudad}, a los {fecha}, a solicitud del "
        "interesado y para los fines que estime conveniente ante {dirigido_a}."
    ),
    "NOTAS": (
        "El suscrito Rector de la institucion {institucion} certifica que el(la) estudiante "
        "{estudiante}, identificado(a) con {documento}, curso el grado {grado} durante el ano "
        "lectivo {ano}, obteniendo las valoraciones registradas en el anexo de este documento "
        "conforme al sistema institucional de evaluacion.\n\nSe expide en {ciudad}, a los {fecha}."
    ),
    "CONDUCTA": (
        "El suscrito Rector de la institucion {institucion} hace constar que el(la) estudiante "
        "{estudiante}, identificado(a) con {documento}, observo excelente comportamiento y "
        "cumplimiento del manual de convivencia durante el ano lectivo {ano}.\n\n"
        "Se expide en {ciudad}, a los {fecha}."
    ),
    "PAZ_Y_SALVO": (
        "La institucion {institucion} hace constar que el(la) estudiante {estudiante}, identificado(a) "
        "con {documento}, se encuentra a PAZ Y SALVO por todo concepto academico y administrativo "
        "a la fecha de expedicion del presente documento.\n\nSe expide en {ciudad}, a los {fecha}."
    ),
    "RETIRO": (
        "La institucion {institucion} hace constar que el(la) estudiante {estudiante}, identificado(a) "
        "con {documento}, curso el grado {grado} y presento retiro formal del establecimiento "
        "educativo durante el ano lectivo {ano}.\n\nSe expide en {ciudad}, a los {fecha}."
    ),
    "GRADO": (
        "ACTA DE GRADO\n\nEn {ciudad}, a los {fecha}, la institucion {institucion} deja constancia de "
        "que el(la) estudiante {estudiante}, identificado(a) con {documento}, curso y aprobo "
        "satisfactoriamente el grado {grado} correspondiente al ano lectivo {ano}, cumpliendo con "
        "todos los requisitos academicos exigidos."
    ),
    "DIPLOMA": (
        "La institucion {institucion} confiere a {estudiante}, identificado(a) con {documento}, el "
        "titulo correspondiente por haber culminado satisfactoriamente sus estudios en el ano "
        "lectivo {ano}.\n\nEn constancia se firma en {ciudad}, a los {fecha}."
    ),
}


def build_certificate_content(certificate) -> str:
    context = certificate_context(certificate)
    template = CERTIFICATE_TEMPLATES.get(certificate.kind, CERTIFICATE_TEMPLATES["ESTUDIO"])
    try:
        return template.format(**context)
    except KeyError:
        return template


def student_academic_summary(student, school_year=None):
    """Resumen academico por area para la hoja de vida."""
    from django.db.models import Avg

    grades = student.subject_grades.select_related("subject", "subject__area", "period")
    if school_year:
        grades = grades.filter(school_year=school_year)

    summary = (
        grades.values("subject__area__name")
        .annotate(average=Avg("final_score"))
        .order_by("subject__area__order")
    )
    overall = grades.aggregate(average=Avg("final_score"))["average"]
    failed = grades.filter(is_passing=False).count()
    return {
        "areas": [
            {"area": row["subject__area__name"], "average": round(float(row["average"] or 0), 2)}
            for row in summary
        ],
        "average": round(float(overall or 0), 2),
        "failed_subjects": failed,
    }
