"""
Construccion de los indicadores, alertas y accesos rapidos del dashboard.
El contenido se adapta al perfil del usuario autenticado.
"""
from __future__ import annotations

import datetime as dt

from django.db.models import Avg, Count, Q
from django.utils import timezone


def _safe(callable_, default=0):
    try:
        return callable_()
    except Exception:
        return default


def institutional_metrics(user):
    from core.academic.models import AcademicPeriod, Group, SchoolYear
    from core.evaluations.models import SubjectGrade
    from core.students.models import Enrollment, Student
    from core.teachers.models import Teacher
    from core.users.models import User

    year = SchoolYear.current()
    period = AcademicPeriod.objects.filter(school_year=year, is_current=True).first() if year else None

    students = Student.objects.filter(status="ACTIVO", deleted_at__isnull=True).count()
    teachers = Teacher.objects.filter(status="ACTIVO", deleted_at__isnull=True).count()
    groups = Group.objects.filter(school_year=year, deleted_at__isnull=True).count() if year else 0
    users = User.objects.filter(is_active=True, deleted_at__isnull=True).count()

    grades = SubjectGrade.objects.filter(school_year=year, deleted_at__isnull=True) if year else SubjectGrade.objects.none()
    total_grades = grades.count()
    passing = grades.filter(is_passing=True).count()
    average = grades.aggregate(value=Avg("final_score"))["value"] or 0

    previous_year = SchoolYear.objects.filter(year=(year.year - 1)).first() if year else None
    previous_students = (
        Enrollment.objects.filter(school_year=previous_year, status="ACTIVA", deleted_at__isnull=True).count()
        if previous_year
        else 0
    )

    return {
        "school_year": {"id": year.id, "name": year.name, "progress": year.progress} if year else None,
        "period": {"id": period.id, "name": period.name} if period else None,
        "cards": [
            {
                "code": "students",
                "label": "Estudiantes activos",
                "value": students,
                "previous": previous_students,
                "icon": "graduation-cap",
                "color": "#4F46E5",
                "url": "/estudiantes/",
            },
            {
                "code": "teachers",
                "label": "Docentes activos",
                "value": teachers,
                "previous": teachers,
                "icon": "presentation",
                "color": "#0EA5E9",
                "url": "/docentes/",
            },
            {
                "code": "groups",
                "label": "Grupos abiertos",
                "value": groups,
                "previous": groups,
                "icon": "users",
                "color": "#10B981",
                "url": "/directiva/grupos/",
            },
            {
                "code": "average",
                "label": "Promedio institucional",
                "value": round(float(average), 2),
                "previous": round(float(average), 2),
                "icon": "trending-up",
                "color": "#F59E0B",
                "suffix": "",
                "url": "/reportes/estadisticos/",
            },
            {
                "code": "pass_rate",
                "label": "Tasa de aprobacion",
                "value": round(passing / total_grades * 100, 1) if total_grades else 0,
                "previous": 0,
                "icon": "award",
                "color": "#A855F7",
                "suffix": "%",
                "url": "/reportes/estadisticos/",
            },
            {
                "code": "users",
                "label": "Usuarios de la plataforma",
                "value": users,
                "previous": users,
                "icon": "user",
                "color": "#EC4899",
                "url": "/usuarios/",
            },
        ],
    }


def enrollment_by_grade(year):
    from core.students.models import Enrollment

    if year is None:
        return {"labels": [], "data": []}
    rows = (
        Enrollment.objects.filter(school_year=year, status="ACTIVA", deleted_at__isnull=True)
        .values("group__grade__name")
        .annotate(total=Count("id"))
        .order_by("group__grade__order")
    )
    return {
        "labels": [row["group__grade__name"] or "-" for row in rows],
        "data": [row["total"] for row in rows],
    }


def average_by_period(year):
    from core.evaluations.models import SubjectGrade

    if year is None:
        return {"labels": [], "data": []}
    rows = (
        SubjectGrade.objects.filter(school_year=year, deleted_at__isnull=True)
        .values("period__short_name", "period__number")
        .annotate(average=Avg("final_score"))
        .order_by("period__number")
    )
    return {
        "labels": [row["period__short_name"] or "-" for row in rows],
        "data": [round(float(row["average"] or 0), 2) for row in rows],
    }


def performance_distribution(year):
    from core.evaluations.models import SubjectGrade

    if year is None:
        return []
    rows = (
        SubjectGrade.objects.filter(school_year=year, deleted_at__isnull=True, performance__isnull=False)
        .values("performance__name", "performance__color")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    return [
        {"label": row["performance__name"], "value": row["total"], "color": row["performance__color"]}
        for row in rows
    ]


def access_trend(days=14):
    from core.authentication.models import AccessLog

    since = timezone.now() - dt.timedelta(days=days)
    rows = (
        AccessLog.objects.filter(event="LOGIN", created_at__gte=since)
        .values("created_at__date")
        .annotate(total=Count("id"))
        .order_by("created_at__date")
    )
    return {
        "labels": [row["created_at__date"].strftime("%d/%m") for row in rows],
        "data": [row["total"] for row in rows],
    }


def institutional_alerts(user):
    from core.academic.models import AcademicPeriod, SchoolYear
    from core.students.models import Student
    from core.tutoring.models import ReportCardBlock
    from core.users.models import User

    alerts = []
    year = SchoolYear.current()

    if year is None:
        alerts.append(
            {
                "level": "danger",
                "title": "No hay ano lectivo configurado",
                "message": "Cree un ano lectivo para habilitar matriculas, notas y boletines.",
                "url": "/directiva/anos-lectivos/",
                "icon": "alert-triangle",
            }
        )
    else:
        if not AcademicPeriod.objects.filter(school_year=year).exists():
            alerts.append(
                {
                    "level": "warning",
                    "title": "El ano lectivo no tiene periodos",
                    "message": "Genere los periodos academicos para iniciar la digitacion de notas.",
                    "url": "/directiva/periodos/",
                    "icon": "calendar",
                }
            )
        period = AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
        if period and period.grades_open_to and period.grades_open_to < timezone.now():
            alerts.append(
                {
                    "level": "warning",
                    "title": f"Digitacion vencida en {period.name}",
                    "message": "La ventana de digitacion de notas ya finalizo.",
                    "url": "/evaluaciones/notas/",
                    "icon": "clock",
                }
            )

    blocked = ReportCardBlock.objects.filter(blocked=True, deleted_at__isnull=True).count()
    if blocked:
        alerts.append(
            {
                "level": "info",
                "title": f"{blocked} boletines bloqueados",
                "message": "Existen estudiantes con restriccion para la entrega del boletin.",
                "url": "/tutoria/bloqueo-boletin/",
                "icon": "lock",
            }
        )

    without_user = Student.objects.filter(user__isnull=True, status="ACTIVO", deleted_at__isnull=True).count()
    if without_user:
        alerts.append(
            {
                "level": "info",
                "title": f"{without_user} estudiantes sin usuario",
                "message": "Genere las credenciales de acceso para estos estudiantes.",
                "url": "/usuarios/estudiantes/",
                "icon": "key",
            }
        )

    locked = User.objects.filter(locked_until__gt=timezone.now()).count()
    if locked:
        alerts.append(
            {
                "level": "danger",
                "title": f"{locked} cuentas bloqueadas",
                "message": "Cuentas bloqueadas por intentos fallidos de acceso.",
                "url": "/usuarios/",
                "icon": "shield-check",
            }
        )

    return alerts


def quick_actions(user):
    from config.permissions import user_has_permission

    candidates = [
        ("students.registry", "create", "Registrar estudiante", "graduation-cap", "/estudiantes/"),
        ("students.enrollment", "create", "Nueva matricula", "clipboard-check", "/estudiantes/matricula/"),
        ("evaluations.grades", "edit", "Digitar notas", "pencil", "/evaluaciones/notas/"),
        ("attendance.register", "create", "Tomar asistencia", "calendar-check", "/asistencia/"),
        ("observer.records", "create", "Nueva observacion", "eye", "/observador/"),
        ("agenda.calendar", "create", "Crear evento", "calendar", "/agenda/eventos/"),
        ("promotion.final_reports", "view", "Generar boletines", "file-text", "/promocion/boletines/"),
        ("users.management", "create", "Crear usuario", "user", "/usuarios/"),
        ("documents.printing", "create", "Emitir documento", "printer", "/documentos/impresion/"),
        ("reports.academic", "view", "Ver reportes", "bar-chart", "/reportes/academicos/"),
    ]
    return [
        {"label": label, "icon": icon, "url": url}
        for code, action, label, icon, url in candidates
        if user_has_permission(user, code, action)
    ][:8]


def teacher_dashboard(user):
    from core.academic.models import AcademicPeriod, SchoolYear
    from core.evaluations.models import SubjectGrade
    from core.teachers.models import TeachingAssignment

    teacher = getattr(user, "teacher_profile", None)
    if teacher is None:
        return None
    year = SchoolYear.current()
    period = AcademicPeriod.objects.filter(school_year=year, is_current=True).first() if year else None
    assignments = TeachingAssignment.objects.filter(
        teacher=teacher, school_year=year, deleted_at__isnull=True
    ).select_related("subject", "group", "group__grade")

    pending = []
    for assignment in assignments:
        expected = assignment.group.enrolled_count
        recorded = SubjectGrade.objects.filter(
            subject=assignment.subject, group=assignment.group, period=period, deleted_at__isnull=True
        ).count() if period else 0
        pending.append(
            {
                "assignment": assignment.id,
                "subject": assignment.subject.name,
                "group": assignment.group.name,
                "expected": expected,
                "recorded": recorded,
                "progress": round(recorded / expected * 100) if expected else 0,
            }
        )

    return {
        "teacher": teacher.full_name,
        "assignments": len(pending),
        "students": sum(item["expected"] for item in pending),
        "hours": teacher.assigned_hours,
        "grade_progress": pending,
    }


def student_dashboard(user):
    from core.academic.models import AcademicPeriod, SchoolYear
    from core.attendance.models import AttendanceSummary
    from core.evaluations.models import SubjectGrade

    student = getattr(user, "student_profile", None)
    if student is None:
        return None
    year = SchoolYear.current()
    period = AcademicPeriod.objects.filter(school_year=year, is_current=True).first() if year else None
    grades = SubjectGrade.objects.filter(
        student=student, school_year=year, deleted_at__isnull=True
    ).select_related("subject", "period", "performance")

    return {
        "student": student.display_name,
        "group": student.current_group.name if student.current_group else "",
        "average": round(float(grades.aggregate(v=Avg("final_score"))["v"] or 0), 2),
        "failing": grades.filter(is_passing=False).count(),
        "absences": AttendanceSummary.objects.filter(student=student, period=period).aggregate(
            total=Count("absences")
        )["total"]
        or 0,
        "subjects": [
            {
                "subject": grade.subject.name,
                "score": float(grade.final_score or 0),
                "performance": grade.performance.name if grade.performance else "",
                "period": grade.period.short_name,
            }
            for grade in grades.order_by("subject__area__order")[:20]
        ],
    }


def platform_dashboard():
    """
    Panorama de toda la plataforma, para el Super Administrador.

    Las graficas academicas del dashboard normal pertenecen a una institucion
    concreta y no significan nada sumadas entre instituciones distintas. Lo que
    si necesita quien administra la plataforma es saber cuantas instituciones
    hay, como esta funcionando cada una y cual necesita atencion.
    """
    import datetime as dt

    from django.utils import timezone

    from core.institutions.models import Institution
    from core.institutions.services import institution_summary
    from core.users.models import User

    instituciones = list(
        Institution.objects.filter(deleted_at__isnull=True).order_by("-is_default", "name")
    )

    filas, totales = [], {"students": 0, "teachers": 0, "groups": 0, "campuses": 0}
    estados = {"En operacion": 0, "Lista, sin actividad": 0, "Incompleta": 0, "Inactiva": 0}
    alertas = []

    for institution in instituciones:
        resumen = institution_summary(institution)
        if institution.is_active:
            for clave in totales:
                totales[clave] += resumen[clave]
            estados[resumen["status"]] += 1
        else:
            estados["Inactiva"] += 1

        filas.append({"entity": institution, "summary": resumen})

        if not institution.is_active:
            continue
        if not resumen["users"]:
            alertas.append({
                "tone": "danger",
                "institution": institution,
                "text": "No tiene ningun usuario: nadie puede entrar a ella.",
            })
        elif resumen["missing"]:
            alertas.append({
                "tone": "warning",
                "institution": institution,
                "text": "Le falta " + ", ".join(resumen["missing"]) + " para poder operar.",
            })
        elif resumen["last_login"] is None:
            alertas.append({
                "tone": "info",
                "institution": institution,
                "text": "Esta lista, pero nadie ha ingresado todavia.",
            })

    activas = [i for i in instituciones if i.is_active]
    hace_30 = timezone.now() - dt.timedelta(days=30)
    usuarios = User.objects.filter(is_active=True, deleted_at__isnull=True)

    return {
        "institutions": filas,
        "alerts": alertas,
        "states": estados,
        "cards": {
            "institutions": len(activas),
            "inactive": len(instituciones) - len(activas),
            "students": totales["students"],
            "teachers": totales["teachers"],
            "groups": totales["groups"],
            "campuses": totales["campuses"],
            "users": usuarios.count(),
            "active_users": usuarios.filter(last_login__gte=hace_30).count(),
        },
    }


def build_dashboard(user):
    from core.academic.models import SchoolYear

    year = SchoolYear.current()
    payload = institutional_metrics(user)
    payload.update(
        {
            "charts": {
                "enrollment_by_grade": enrollment_by_grade(year),
                "average_by_period": average_by_period(year),
                "performance": performance_distribution(year),
                "access_trend": access_trend(),
            },
            "alerts": institutional_alerts(user),
            "quick_actions": quick_actions(user),
            "role": user.role_code,
        }
    )
    if user.role_code in ("DOCENTE", "TUTOR"):
        payload["teacher"] = teacher_dashboard(user)
    if user.role_code == "ESTUDIANTE":
        payload["student"] = student_dashboard(user)
    return payload
