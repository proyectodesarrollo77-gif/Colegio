"""Aplica la matriz de permisos por defecto a cada perfil institucional."""
from django.core.management.base import BaseCommand
from django.db import transaction

from config.permissions import invalidate_permission_cache
from core.configuration.modules import DEFAULT_ROLE_MATRIX
from core.users.models import Module, Role, RolePermission


class Command(BaseCommand):
    help = "Asigna los permisos por defecto de cada perfil segun DEFAULT_ROLE_MATRIX"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los permisos existentes antes de aplicar la matriz por defecto.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        modules = list(Module.objects.all())
        if not modules:
            self.stdout.write(self.style.ERROR("No hay modulos registrados. Ejecute primero seed_modules."))
            return

        if options["reset"]:
            deleted, _ = RolePermission.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Permisos eliminados: {deleted}"))

        total = 0
        for role_code, matrix in DEFAULT_ROLE_MATRIX.items():
            role = Role.objects.filter(code=role_code).first()
            if role is None:
                self.stdout.write(self.style.WARNING(f"Perfil {role_code} no existe, se omite."))
                continue

            for module in modules:
                actions = self._resolve_actions(matrix, module.code)
                if actions is None:
                    continue
                RolePermission.objects.update_or_create(
                    role=role,
                    module=module,
                    defaults={
                        "can_view": "view" in actions,
                        "can_create": "create" in actions,
                        "can_edit": "edit" in actions,
                        "can_delete": "delete" in actions,
                        "can_export": "export" in actions,
                        "can_approve": "approve" in actions,
                    },
                )
                total += 1

            self.stdout.write(f"  {role_code}: permisos aplicados")

        invalidate_permission_cache()
        self.stdout.write(self.style.SUCCESS(f"Registros de permisos procesados: {total}"))

    @staticmethod
    def _resolve_actions(matrix, module_code):
        """Resuelve las acciones aplicables a un modulo: exacto > padre > comodin."""
        if module_code in matrix:
            return matrix[module_code]

        parent_code = module_code.split(".")[0]
        if parent_code in matrix:
            return matrix[parent_code]

        if "*" in matrix:
            return matrix["*"]

        return None
