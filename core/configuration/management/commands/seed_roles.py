"""Crea los perfiles institucionales base de PL_SGE."""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.users.models import Role

ROLES = [
    ("SUPER_ADMIN", "Super Administrador", "Control total de la plataforma", "#4F46E5", 1, "dashboard:index"),
    ("RECTOR", "Rector", "Direccion general de la institucion", "#0EA5E9", 2, "dashboard:index"),
    ("COORDINADOR", "Coordinador", "Coordinacion academica y de convivencia", "#10B981", 3, "dashboard:index"),
    ("SECRETARIA", "Secretaria", "Gestion administrativa y documental", "#F59E0B", 4, "dashboard:index"),
    ("DOCENTE", "Docente", "Digitacion de notas y seguimiento academico", "#A855F7", 5, "dashboard:index"),
    ("TUTOR", "Tutor", "Acompanamiento y convivencia del grupo", "#EC4899", 6, "dashboard:index"),
    ("ESTUDIANTE", "Estudiante", "Consulta de notas, agenda y aula virtual", "#14B8A6", 7, "dashboard:index"),
    ("ACUDIENTE", "Acudiente", "Seguimiento del proceso academico del estudiante", "#6366F1", 8, "dashboard:index"),
    # Perfiles del Programa de Alimentacion Escolar.
    ("RESPONSABLE_PAE", "Responsable PAE", "Gestion integral del Programa de Alimentacion Escolar", "#0EA5E9", 9, "pae:dashboard"),
    ("COORDINADOR_SEDE", "Coordinador de Sede PAE", "Operacion del PAE en la sede asignada", "#10B981", 10, "pae:dashboard"),
    ("OPERADOR_PAE", "Operador PAE", "Registro de entregas y evidencias del operador contratado", "#F59E0B", 11, "pae:deliveries"),
    ("SUPERVISOR_PAE", "Supervisor PAE", "Supervision, visitas y control de calidad del programa", "#A855F7", 12, "pae:visits"),
    ("AUDITOR_PAE", "Auditor PAE", "Consulta y exportacion con trazabilidad del programa", "#EC4899", 13, "pae:audit"),
    ("CONSULTA_PAE", "Consulta PAE", "Consulta de informacion publica del programa", "#14B8A6", 14, "pae:dashboard"),
]


class Command(BaseCommand):
    help = "Crea los perfiles (roles) iniciales de la plataforma"

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for code, name, description, color, order, landing in ROLES:
            _, was_created = Role.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "color": color,
                    "order": order,
                    "landing_url": landing,
                    "is_system": True,
                    "is_active": True,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Perfiles disponibles: {Role.objects.count()} (nuevos: {created})"))
