"""
Pruebas de `initialize_platform` frente a una instalacion ya en uso.

Lo que se protege aqui: que reejecutar el comando de inicializacion en una
plataforma que ya tiene instituciones no cree una duplicada, no le quite la
marca de predeterminada a la que esta operando, y no mueva al Super
Administrador a otra institucion. Cuando eso pasaba, el administrador entraba
a una institucion vacia y la plataforma parecia no tener datos.
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.users.models import Role, User

from ..models import Institution


def inicializar():
    """Corre el comando sin la estructura academica ni el PAE (mas rapido)."""
    call_command(
        "initialize_platform",
        skip_academic=True,
        skip_pae=True,
        stdout=StringIO(),
        stderr=StringIO(),
    )


class InicializacionSobreInstalacionEnUsoTests(TestCase):
    def setUp(self):
        # Institucion ya en produccion, con su propio codigo DANE.
        self.propia = Institution.objects.create(
            code="108001002606",
            name="Institucion Educativa Distrital",
            short_name="IED",
            is_default=True,
        )

    def test_no_crea_una_institucion_duplicada(self):
        inicializar()

        self.assertEqual(Institution.objects.count(), 1)
        self.assertEqual(Institution.objects.get().pk, self.propia.pk)

    def test_conserva_la_institucion_predeterminada(self):
        inicializar()

        self.propia.refresh_from_db()
        self.assertTrue(self.propia.is_default)
        self.assertTrue(self.propia.is_active)

    def test_no_mueve_al_super_admin_de_institucion(self):
        otra = Institution.objects.create(code="222222222222", name="Otra")
        admin = User.objects.create_user(
            email="admin@datly.local",
            username="admin",
            password="Admin123*",
            role=Role.objects.create(code=Role.SUPER_ADMIN, name="Super Admin"),
            institution=otra,
        )

        inicializar()

        admin.refresh_from_db()
        self.assertEqual(admin.institution_id, otra.pk)

    def test_reejecutarlo_no_cambia_nada(self):
        inicializar()
        antes = list(Institution.objects.values_list("pk", "code", "is_default", "is_active"))

        inicializar()

        self.assertEqual(
            antes, list(Institution.objects.values_list("pk", "code", "is_default", "is_active"))
        )


class InicializacionEnInstalacionNuevaTests(TestCase):
    def test_crea_la_institucion_de_arranque_cuando_no_hay_ninguna(self):
        self.assertEqual(Institution.objects.count(), 0)

        inicializar()

        institution = Institution.objects.get()
        self.assertEqual(institution.code, "000000000000")
        self.assertTrue(institution.is_default)

    def test_le_asigna_institucion_al_super_admin_recien_creado(self):
        inicializar()

        admin = User.objects.get(email="admin@datly.local")
        self.assertEqual(admin.institution, Institution.objects.get())
