"""
Pruebas de control de acceso del PAE.

La validacion no puede depender de ocultar botones: se comprueba que el backend
rechace la operacion tanto en las paginas HTML como en la API, para cada perfil.
"""
from __future__ import annotations

from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .factories import build_pae, build_plan, build_platform, build_student, build_user, seed_modules

PASSWORD = "Prueba123*"


class PermissionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        institution = cls.platform["institution"]
        cls.responsable = build_user("responsable@perm.local", "RESPONSABLE_PAE", institution)
        cls.coordinador = build_user("coordinador@perm.local", "COORDINADOR_SEDE", institution)
        cls.operador = build_user("operador@perm.local", "OPERADOR_PAE", institution)
        cls.supervisor = build_user("supervisor@perm.local", "SUPERVISOR_PAE", institution)
        cls.auditor = build_user("auditor@perm.local", "AUDITOR_PAE", institution)
        cls.consulta = build_user("consulta@perm.local", "CONSULTA_PAE", institution)
        cls.docente = build_user("docente@perm.local", "DOCENTE", institution)

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def html(self, user):
        if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]
        client = Client()
        client.force_login(user)
        session = client.session
        session["plsge_2fa_verified"] = True
        session.save()
        return client


class ApiPermissionTests(PermissionTestCase):
    """Lectura, escritura y aprobacion en la API por perfil."""

    def test_el_responsable_consulta_beneficiarios(self):
        self.assertEqual(self.api(self.responsable).get("/api/pae/beneficiarios/").status_code, 200)

    def test_el_docente_no_accede_al_pae(self):
        self.assertEqual(self.api(self.docente).get("/api/pae/beneficiarios/").status_code, 403)

    def test_el_operador_no_consulta_contratos(self):
        self.assertEqual(self.api(self.operador).get("/api/pae/contratos/").status_code, 403)

    def test_el_operador_si_registra_entregas(self):
        self.assertEqual(self.api(self.operador).get("/api/pae/entregas/").status_code, 200)

    def test_el_perfil_de_consulta_no_puede_crear(self):
        student, enrollment = build_student(self.platform, document="4000000001")
        response = self.api(self.consulta).post(
            "/api/pae/beneficiarios/",
            {
                "vigencia": self.pae["vigencia"].pk,
                "student": student.pk,
                "enrollment": enrollment.pk,
                "start_date": self.pae["vigencia"].start_date.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_el_perfil_de_consulta_no_puede_exportar(self):
        response = self.api(self.consulta).get("/api/pae/beneficiarios/export/", {"format": "csv"})
        self.assertEqual(response.status_code, 403)

    def test_el_auditor_consulta_y_exporta_pero_no_escribe(self):
        client = self.api(self.auditor)
        self.assertEqual(client.get("/api/pae/entregas/").status_code, 200)
        self.assertEqual(client.get("/api/pae/entregas/export/", {"format": "csv"}).status_code, 200)
        response = client.post("/api/pae/operadores/", {"code": "X", "business_name": "X"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_el_anonimo_no_accede(self):
        self.assertIn(APIClient().get("/api/pae/beneficiarios/").status_code, (401, 403))

    def test_el_coordinador_no_aprueba_planes(self):
        plan = build_plan(self.platform, self.pae, status="EN_REVISION")
        response = self.api(self.coordinador).post(
            f"/api/pae/planes/{plan.pk}/transition/", {"status": "APROBADO"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        plan.refresh_from_db()
        self.assertEqual(plan.status, "EN_REVISION")

    def test_el_responsable_si_aprueba_planes(self):
        plan = build_plan(self.platform, self.pae, status="EN_REVISION")
        response = self.api(self.responsable).post(
            f"/api/pae/planes/{plan.pk}/transition/", {"status": "APROBADO"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_el_supervisor_aprueba_visitas_pero_no_edita_beneficiarios(self):
        client = self.api(self.supervisor)
        self.assertEqual(client.get("/api/pae/visitas/").status_code, 200)
        student, enrollment = build_student(self.platform, document="4000000002")
        response = client.post(
            "/api/pae/beneficiarios/",
            {
                "vigencia": self.pae["vigencia"].pk,
                "student": student.pk,
                "enrollment": enrollment.pk,
                "start_date": self.pae["vigencia"].start_date.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_el_borrado_exige_permiso_de_eliminacion(self):
        from ..models import PaeCatalog

        catalog = PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="TMP", name="Temporal"
        )
        response = self.api(self.coordinador).delete(f"/api/pae/catalogos/{catalog.pk}/")
        self.assertEqual(response.status_code, 403)
        catalog.refresh_from_db()
        self.assertIsNone(catalog.deleted_at)


class HtmlPermissionTests(PermissionTestCase):
    """Las paginas tambien se protegen en el servidor."""

    def test_el_responsable_abre_el_tablero(self):
        self.assertEqual(self.html(self.responsable).get("/pae/").status_code, 200)

    def test_el_docente_recibe_403_en_las_paginas_del_pae(self):
        self.assertEqual(self.html(self.docente).get("/pae/beneficiarios/").status_code, 403)

    def test_el_operador_no_abre_contratos(self):
        self.assertEqual(self.html(self.operador).get("/pae/contratos/").status_code, 403)

    def test_el_operador_si_abre_la_planilla_de_entregas(self):
        self.assertEqual(self.html(self.operador).get("/pae/entregas/planilla/").status_code, 200)

    def test_el_anonimo_es_redirigido_al_login(self):
        response = Client().get("/pae/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response["Location"])

    def test_la_configuracion_de_la_pagina_refleja_los_permisos(self):
        response = self.html(self.consulta).get("/pae/beneficiarios/")
        self.assertEqual(response.status_code, 200)
        config = response.context["resource_config"]
        self.assertTrue(config["permissions"].get("view"))
        self.assertFalse(config["allow"]["create"])
        self.assertFalse(config["allow"]["delete"])

    def test_el_responsable_ve_habilitadas_las_acciones(self):
        response = self.html(self.responsable).get("/pae/beneficiarios/")
        config = response.context["resource_config"]
        self.assertTrue(config["allow"]["create"])
        self.assertTrue(config["allow"]["export"])


class CampusScopeTests(PermissionTestCase):
    """Control por sede: el coordinador solo ve su sede."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # El alcance por sede se toma de las sedes que el usuario coordina.
        cls.platform["campus"].coordinator = cls.coordinador
        cls.platform["campus"].save(update_fields=["coordinator"])

        from ..models import PaeDelivery

        cls.plan_principal = build_plan(cls.platform, cls.pae, status="EN_EJECUCION")
        cls.plan_otra = build_plan(
            cls.platform, cls.pae, status="EN_EJECUCION", campus=cls.platform["other_campus"]
        )
        for plan in (cls.plan_principal, cls.plan_otra):
            PaeDelivery.objects.create(
                plan=plan, campus=plan.campus, service_date=timezone.localdate(),
                scheduled_rations=10, received_rations=10, delivered_rations=10,
            )

    def test_el_coordinador_solo_ve_las_entregas_de_su_sede(self):
        response = self.api(self.coordinador).get("/api/pae/entregas/")
        self.assertEqual(response.status_code, 200)
        campuses = {row["campus"] for row in response.json()["results"]}
        self.assertEqual(campuses, {self.platform["campus"].pk})

    def test_el_responsable_ve_todas_las_sedes(self):
        response = self.api(self.responsable).get("/api/pae/entregas/")
        self.assertEqual(response.json()["count"], 2)

    def test_el_coordinador_no_accede_al_detalle_de_otra_sede(self):
        from ..models import PaeDelivery

        ajena = PaeDelivery.objects.get(campus=self.platform["other_campus"])
        response = self.api(self.coordinador).get(f"/api/pae/entregas/{ajena.pk}/")
        self.assertEqual(response.status_code, 404)
