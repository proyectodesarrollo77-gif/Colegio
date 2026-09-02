"""Sincroniza el registro de modulos de PL_SGE con la base de datos."""
from django.core.management.base import BaseCommand
from django.db import transaction

from config.permissions import invalidate_permission_cache
from core.configuration.modules import iter_modules
from core.users.models import Module


class Command(BaseCommand):
    help = "Crea o actualiza los modulos de la plataforma a partir de core.configuration.modules"

    @transaction.atomic
    def handle(self, *args, **options):
        created, updated = 0, 0
        parents = {}

        for entry in iter_modules():
            parent = parents.get(entry["parent"]) if entry["parent"] else None
            module, was_created = Module.objects.update_or_create(
                code=entry["code"],
                defaults={
                    "name": entry["name"],
                    "parent": parent,
                    "icon": entry["icon"],
                    "url_name": entry["url_name"],
                    "group": entry["group"],
                    "order": entry["order"],
                    "is_active": True,
                },
            )
            parents[entry["code"]] = module
            created += int(was_created)
            updated += int(not was_created)

        invalidate_permission_cache()
        self.stdout.write(self.style.SUCCESS(f"Modulos creados: {created} | actualizados: {updated}"))
