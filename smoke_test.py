"""
Prueba de humo de PL_SGE: recorre todas las paginas y endpoints principales
con el usuario Super Administrador y reporta el estado de cada uno.

    python smoke_test.py
"""
from __future__ import annotations

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402

# El cliente de pruebas de Django usa el host "testserver": se habilita sin
# alterar la configuracion de ALLOWED_HOSTS del archivo .env.
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

from django.test import Client  # noqa: E402
from django.urls import get_resolver  # noqa: E402

from core.users.models import User  # noqa: E402

SKIP_PREFIXES = ("/admin/", "/api/", "/static/", "/media/")
SKIP_NAMES = {"authentication:logout"}


def collect_urls():
    """Rutas HTML estaticas (sin parametros dinamicos) declaradas en config.urls."""
    from django.urls.resolvers import URLPattern, URLResolver

    urls = []

    def walk(patterns, prefix="", namespace=""):
        for entry in patterns:
            route = str(getattr(entry.pattern, "_route", entry.pattern))
            if isinstance(entry, URLResolver):
                child_namespace = entry.namespace or namespace
                walk(entry.url_patterns, prefix + route, child_namespace)
                continue
            if isinstance(entry, URLPattern):
                full = "/" + (prefix + route).lstrip("/")
                if "<" in full or full.startswith(SKIP_PREFIXES):
                    continue
                name = f"{namespace}:{entry.name}" if namespace else (entry.name or "")
                if name in SKIP_NAMES:
                    continue
                urls.append((name, full))

    walk(get_resolver().url_patterns)
    return sorted(set(urls), key=lambda item: item[1])


API_ENDPOINTS = [
    "/api/auth/me/",
    "/api/auth/permissions/",
    "/api/dashboard/",
    "/api/statistics/academic/",
    "/api/statistics/administrative/",
    "/api/users/",
    "/api/roles/",
    "/api/modules/",
    "/api/institutions/",
    "/api/campuses/",
    "/api/shifts/",
    "/api/report-headers/",
    "/api/grade-decimals/",
    "/api/system-parameters/",
    "/api/school-years/",
    "/api/periods/",
    "/api/grading-scales/",
    "/api/grading-levels/",
    "/api/dimensions/",
    "/api/education-levels/",
    "/api/grades/",
    "/api/groups/",
    "/api/areas/",
    "/api/subjects/",
    "/api/academic-processes/",
    "/api/value-judgments/",
    "/api/coexistence-items/",
    "/api/purposes/",
    "/api/students/",
    "/api/guardians/",
    "/api/enrollments/",
    "/api/admissions/",
    "/api/inscriptions/",
    "/api/student-documents/",
    "/api/student-certificates/",
    "/api/teachers/",
    "/api/teaching-assignments/",
    "/api/schedule-slots/",
    "/api/teacher-processes/",
    "/api/teacher-absences/",
    "/api/process-grades/",
    "/api/subject-grades/",
    "/api/area-grades/",
    "/api/student-judgments/",
    "/api/qualitative-evaluations/",
    "/api/purpose-evaluations/",
    "/api/bilingual-evaluations/",
    "/api/grade-locks/",
    "/api/attendance-sessions/",
    "/api/attendance-records/",
    "/api/attendance-summaries/",
    "/api/tutors/",
    "/api/tutoring-judgments/",
    "/api/coexistence-evaluations/",
    "/api/report-blocks/",
    "/api/tutoring-meetings/",
    "/api/observation-categories/",
    "/api/observer-entries/",
    "/api/observer-followups/",
    "/api/closing-processes/",
    "/api/promotion-results/",
    "/api/report-cards/",
    "/api/evaluation-commissions/",
    "/api/recovery-plans/",
    "/api/recovery-activities/",
    "/api/recovery-enrollments/",
    "/api/recovery-submissions/",
    "/api/emphases/",
    "/api/emphasis-groups/",
    "/api/emphasis-enrollments/",
    "/api/document-templates/",
    "/api/document-issues/",
    "/api/report-definitions/",
    "/api/report-executions/",
    "/api/dashboard-indicators/",
    "/api/agenda-events/",
    "/api/agenda-activities/",
    "/api/circulars/",
    "/api/courses/",
    "/api/course-units/",
    "/api/course-materials/",
    "/api/course-activities/",
    "/api/activity-submissions/",
    "/api/course-progress/",
    "/api/elections/",
    "/api/candidacies/",
    "/api/candidates/",
    "/api/election-results/",
    "/api/voter-registry/",
    "/api/forms/",
    "/api/form-fields/",
    "/api/form-submissions/",
    "/api/virtual-spaces/",
    "/api/notifications/",
    "/api/audit-logs/",
    "/api/access-logs/",
    "/api/login-attempts/",
    "/api/user-sessions/",
    "/api/two-factor-devices/",
    "/api/credential-certificates/",
    "/api/user-permissions/",
    "/api/role-permissions/",
    "/api/institutional-calendar/",
    # ---- PAE ----
    "/api/pae/dashboard/",
    "/api/pae/alertas/",
    "/api/pae/planilla-entregas/",
    "/api/pae/importar/",
    "/api/pae/importar/?kind=beneficiarios",
    "/api/pae/importar/?kind=programacion&download=1",
    "/api/pae/normativa/",
    "/api/pae/catalogos/",
    "/api/pae/catalogos/types/",
    "/api/pae/modalidades/",
    "/api/pae/tipos-complemento/",
    "/api/pae/vigencias/",
    "/api/pae/diagnosticos/",
    "/api/pae/priorizaciones/",
    "/api/pae/beneficiarios/",
    "/api/pae/beneficiarios/coverage/",
    "/api/pae/beneficiarios-historial/",
    "/api/pae/operadores/",
    "/api/pae/contratos/",
    "/api/pae/contratos/expiring/",
    "/api/pae/planes/",
    "/api/pae/planes-historial/",
    "/api/pae/menus/",
    "/api/pae/menu-dias/",
    "/api/pae/menu-preparaciones/",
    "/api/pae/menu-ingredientes/",
    "/api/pae/programacion/",
    "/api/pae/entregas/",
    "/api/pae/entregas/summary/",
    "/api/pae/listas-verificacion/",
    "/api/pae/criterios-verificacion/",
    "/api/pae/verificaciones/",
    "/api/pae/verificacion-resultados/",
    "/api/pae/visitas/",
    "/api/pae/hallazgos/",
    "/api/pae/novedades/",
    "/api/pae/novedades-historial/",
    "/api/pae/mejoramiento/",
    "/api/pae/mejoramiento/overdue/",
    "/api/pae/pqrs/",
    "/api/pae/participacion/",
    "/api/pae/participantes/",
    "/api/pae/compromisos/",
    "/api/pae/documentos/",
    "/api/pae/evidencias/",
    "/api/pae/indicadores/",
    "/api/pae/informes/",
    "/api/audit-logs/?module_prefix=pae",
    # ---- Exportaciones ----
    "/api/students/export/?format=csv",
    "/api/audit-logs/export/?format=csv",
    "/api/audit-logs/export/?module_prefix=pae&format=xlsx",
    "/api/pae/beneficiarios/export/?format=csv",
    "/api/pae/entregas/export/?format=xlsx",
    "/api/pae/indicadores/export/?format=csv",
]


def main():
    user = User.objects.filter(email="admin@datly.local").first()
    if user is None:
        print("No existe el usuario admin@datly.local. Ejecute initialize_platform.")
        return 1

    client = Client()
    client.force_login(user)
    session = client.session
    session["plsge_2fa_verified"] = True
    session.save()

    failures = []

    print("=" * 78)
    print("PAGINAS HTML")
    print("=" * 78)
    for name, url in collect_urls():
        try:
            response = client.get(url, follow=False)
            status = response.status_code
        except Exception as exc:  # pragma: no cover
            status = f"EXC {type(exc).__name__}: {exc}"
        ok = status in (200, 302)
        flag = "OK " if ok else "FAIL"
        if not ok:
            failures.append((url, status))
        print(f"  [{flag}] {str(status):>4}  {url:<44} {name}")

    print()
    print("=" * 78)
    print("ENDPOINTS API")
    print("=" * 78)
    for url in API_ENDPOINTS:
        try:
            response = client.get(url, HTTP_ACCEPT="application/json")
            status = response.status_code
        except Exception as exc:  # pragma: no cover
            status = f"EXC {type(exc).__name__}: {exc}"
        ok = status == 200
        flag = "OK " if ok else "FAIL"
        if not ok:
            failures.append((url, status))
        print(f"  [{flag}] {str(status):>4}  {url}")

    print()
    print("=" * 78)
    if failures:
        print(f"RESULTADO: {len(failures)} rutas con error")
        for url, status in failures:
            print(f"   - {url} -> {status}")
        return 1
    print("RESULTADO: todas las rutas respondieron correctamente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
