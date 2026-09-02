"""
Pruebas de los dos modos del Super Administrador.

Mientras no ha entrado a ninguna institucion administra la **plataforma**: ve
las instituciones y las cuentas, no la operacion academica, que pertenece a una
institucion concreta. Al entrar a una con `Ingresar` trabaja dentro de ella,
con el menu y el dashboard completos.
"""
from __future__ import annotations

from django.test import Client, TestCase

from .test_multi_institucion import build_institution, build_user, seed_modules

from ..context import SESSION_KEY


class ModoPlataformaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.una, _, _ = build_institution("750000000001", "Institucion Una", default=True)
        cls.otra, _, _ = build_institution("750000000002", "Institucion Dos")
        cls.super_admin = build_user("super.modo@test.local", cls.una, "SUPER_ADMIN")
        cls.rector = build_user("rector.modo@test.local", cls.una, "RECTOR")

    def _entrar(self, email, institution=None, password="Prueba123*"):
        client = Client()
        datos = {"identifier": email, "password": password}
        if institution is not None:
            datos["institution"] = institution.pk
        client.post("/auth/login/", datos)
        return client

    def _modulos(self, client):
        respuesta = client.get("/dashboard/")
        return {
            item["code"]
            for grupo in respuesta.context["nav_groups"]
            for item in grupo["items"]
        }

    # --- Modo plataforma -------------------------------------------------
    def test_el_super_admin_que_no_elige_institucion_administra_la_plataforma(self):
        client = self._entrar("super.modo@test.local")

        self.assertNotIn(SESSION_KEY, client.session)
        self.assertTrue(client.get("/dashboard/").context["solo_plataforma"])

    def test_en_modo_plataforma_ve_el_panorama_y_no_el_dashboard_academico(self):
        client = self._entrar("super.modo@test.local")

        respuesta = client.get("/dashboard/")

        self.assertTemplateUsed(respuesta, "dashboard/platform.html")
        self.assertEqual(len(respuesta.context["institutions"]), 2)

    def test_en_modo_plataforma_el_menu_no_trae_modulos_academicos(self):
        modulos = self._modulos(self._entrar("super.modo@test.local"))

        self.assertIn("institutions", modulos)
        self.assertIn("users", modulos)
        self.assertIn("audit", modulos)
        for academico in ("students", "evaluations", "attendance", "promotion", "pae"):
            self.assertNotIn(academico, modulos)

    # --- Dentro de una institucion ---------------------------------------
    def test_al_ingresar_a_una_institucion_recupera_el_menu_completo(self):
        client = self._entrar("super.modo@test.local")

        client.get(f"/institucion/panel/{self.otra.pk}/ingresar/")

        modulos = self._modulos(client)
        self.assertIn("students", modulos)
        self.assertIn("evaluations", modulos)
        self.assertEqual(client.session[SESSION_KEY], self.otra.pk)

    def test_dentro_de_una_institucion_ve_el_dashboard_academico(self):
        client = self._entrar("super.modo@test.local")
        client.get(f"/institucion/panel/{self.otra.pk}/ingresar/")

        respuesta = client.get("/dashboard/")

        self.assertTemplateUsed(respuesta, "dashboard/index.html")
        self.assertFalse(respuesta.context["solo_plataforma"])

    def test_elegir_institucion_al_ingresar_entra_directo_a_ella(self):
        client = self._entrar("super.modo@test.local", institution=self.otra)

        self.assertEqual(client.session[SESSION_KEY], self.otra.pk)
        self.assertFalse(client.get("/dashboard/").context["solo_plataforma"])

    # --- Volver a la plataforma ------------------------------------------
    def test_salir_devuelve_a_la_administracion_de_la_plataforma(self):
        client = self._entrar("super.modo@test.local")
        client.get(f"/institucion/panel/{self.otra.pk}/ingresar/")

        client.get("/institucion/panel/salir/")

        self.assertNotIn(SESSION_KEY, client.session)
        self.assertTrue(client.get("/dashboard/").context["solo_plataforma"])

    # --- Los demas perfiles no cambian ------------------------------------
    def test_los_demas_perfiles_nunca_entran_en_modo_plataforma(self):
        client = self._entrar("rector.modo@test.local")

        respuesta = client.get("/dashboard/")

        self.assertFalse(respuesta.context["solo_plataforma"])
        self.assertTemplateUsed(respuesta, "dashboard/index.html")
        self.assertIn("students", self._modulos(client))

    def test_solo_el_super_administrador_puede_salir_a_la_plataforma(self):
        client = self._entrar("rector.modo@test.local")

        self.assertEqual(client.get("/institucion/panel/salir/").status_code, 403)
