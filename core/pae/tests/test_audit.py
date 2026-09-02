"""
Pruebas de auditoria y seguridad del modulo PAE.

Comprueba que las operaciones queden registradas, que la bitacora se pueda
acotar al dominio del PAE y que un usuario normal no pueda alterarla.
"""
from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .factories import build_pae, build_plan, build_platform, build_student, build_user, seed_modules


class AuditTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        institution = cls.platform["institution"]
        cls.responsable = build_user("responsable@audit.local", "RESPONSABLE_PAE", institution)
        cls.auditor = build_user("auditor@audit.local", "AUDITOR_PAE", institution)
        cls.coordinador = build_user("coordinador@audit.local", "COORDINADOR_SEDE", institution)

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client


class AuditTrailTests(AuditTestCase):
    def test_la_creacion_queda_registrada(self):
        from core.audit.models import AuditLog

        student, enrollment = build_student(self.platform, document="5000000001")
        self.api(self.responsable).post(
            "/api/pae/beneficiarios/",
            {
                "vigencia": self.pae["vigencia"].pk,
                "student": student.pk,
                "enrollment": enrollment.pk,
                "start_date": self.pae["vigencia"].start_date.isoformat(),
            },
            format="json",
        )
        entries = AuditLog.objects.filter(module="pae.beneficiarios", action="CREATE")
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().user_id, self.responsable.pk)

    def test_la_exportacion_queda_registrada(self):
        from core.audit.models import AuditLog

        self.api(self.responsable).get("/api/pae/beneficiarios/export/", {"format": "csv"})
        self.assertTrue(
            AuditLog.objects.filter(module="pae.beneficiarios", action="EXPORT").exists()
        )

    def test_la_aprobacion_de_un_plan_queda_registrada(self):
        from core.audit.models import AuditLog

        plan = build_plan(self.platform, self.pae, status="EN_REVISION")
        self.api(self.responsable).post(
            f"/api/pae/planes/{plan.pk}/transition/", {"status": "APROBADO"}, format="json"
        )
        self.assertTrue(AuditLog.objects.filter(module="pae.planeacion", action="APPROVE").exists())

    def test_el_borrado_logico_queda_registrado(self):
        from core.audit.models import AuditLog

        from ..models import PaeCatalog

        catalog = PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="TMP", name="Temporal"
        )
        self.api(self.responsable).delete(f"/api/pae/catalogos/{catalog.pk}/")
        self.assertTrue(
            AuditLog.objects.filter(module="pae.configuracion", action="DELETE").exists()
        )


class AuditFilterTests(AuditTestCase):
    def test_module_prefix_acota_la_bitacora_al_pae(self):
        from core.audit.models import AuditLog

        AuditLog.objects.create(module="pae.entregas", action="CREATE", user_label="x")
        AuditLog.objects.create(module="students.registry", action="CREATE", user_label="x")

        response = self.api(self.auditor).get("/api/audit-logs/", {"module_prefix": "pae"})
        self.assertEqual(response.status_code, 200)
        modules = {row["module"] for row in response.json()["results"]}
        self.assertTrue(all(module.startswith("pae") for module in modules))
        self.assertNotIn("students.registry", modules)

    def test_sin_prefijo_se_devuelve_toda_la_bitacora(self):
        from core.audit.models import AuditLog

        AuditLog.objects.create(module="pae.entregas", action="CREATE", user_label="x")
        AuditLog.objects.create(module="students.registry", action="CREATE", user_label="x")

        response = self.api(self.auditor).get("/api/audit-logs/")
        modules = {row["module"] for row in response.json()["results"]}
        self.assertIn("students.registry", modules)

    def test_la_exportacion_respeta_el_prefijo(self):
        from core.audit.models import AuditLog

        AuditLog.objects.create(module="pae.entregas", action="CREATE", user_label="x")
        response = self.api(self.auditor).get(
            "/api/audit-logs/export/", {"module_prefix": "pae", "format": "csv"}
        )
        self.assertEqual(response.status_code, 200)


class AuditImmutabilityTests(AuditTestCase):
    """La bitacora no se modifica ni se elimina desde la aplicacion."""

    def _entry(self):
        from core.audit.models import AuditLog

        return AuditLog.objects.create(
            module="pae.entregas", action="CREATE", user_label="Usuario", description="Original"
        )

    def test_no_se_puede_crear_una_entrada_por_la_api(self):
        response = self.api(self.responsable).post(
            "/api/audit-logs/", {"module": "pae.entregas", "action": "CREATE"}, format="json"
        )
        self.assertIn(response.status_code, (403, 405))

    def test_no_se_puede_editar_una_entrada(self):
        entry = self._entry()
        response = self.api(self.responsable).patch(
            f"/api/audit-logs/{entry.pk}/", {"description": "Alterado"}, format="json"
        )
        self.assertIn(response.status_code, (403, 405))
        entry.refresh_from_db()
        self.assertEqual(entry.description, "Original")

    def test_no_se_puede_eliminar_una_entrada(self):
        from core.audit.models import AuditLog

        entry = self._entry()
        response = self.api(self.responsable).delete(f"/api/audit-logs/{entry.pk}/")
        self.assertIn(response.status_code, (403, 405))
        self.assertTrue(AuditLog.objects.filter(pk=entry.pk).exists())

    def test_el_auditor_tampoco_puede_eliminar(self):
        from core.audit.models import AuditLog

        entry = self._entry()
        response = self.api(self.auditor).delete(f"/api/audit-logs/{entry.pk}/")
        self.assertIn(response.status_code, (403, 405))
        self.assertTrue(AuditLog.objects.filter(pk=entry.pk).exists())

    def test_el_coordinador_no_consulta_la_bitacora_general(self):
        response = self.api(self.coordinador).get("/api/audit-logs/")
        self.assertEqual(response.status_code, 403)


class InputSecurityTests(AuditTestCase):
    """Entradas hostiles: el ORM y los serializers deben neutralizarlas."""

    def test_el_texto_con_sql_se_almacena_literal(self):
        from ..models import PaeIncident

        payload = "'; DROP TABLE pae_novedad; --"
        response = self.api(self.responsable).post(
            "/api/pae/novedades/",
            {
                "vigencia": self.pae["vigencia"].pk,
                "campus": self.platform["campus"].pk,
                "description": payload,
                "reported_on": timezone.localdate().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        incident = PaeIncident.objects.get(pk=response.json()["id"])
        self.assertEqual(incident.description, payload)
        self.assertTrue(PaeIncident.objects.exists())

    def test_la_busqueda_con_comillas_no_rompe_la_consulta(self):
        response = self.api(self.responsable).get(
            "/api/pae/novedades/", {"search": "' OR 1=1 --"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_el_script_se_devuelve_escapado_en_la_pagina(self):
        from django.conf import settings
        from django.test import Client

        from ..models import PaeIncident

        if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

        PaeIncident.objects.create(
            vigencia=self.pae["vigencia"], campus=self.platform["campus"],
            description="<script>alert(1)</script>",
        )
        client = Client()
        client.force_login(self.responsable)
        session = client.session
        session["plsge_2fa_verified"] = True
        session.save()

        response = client.get("/pae/novedades/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<script>alert(1)</script>", response.content)

    def test_las_peticiones_sin_csrf_se_rechazan(self):
        from django.conf import settings
        from django.test import Client

        if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.responsable)
        session = client.session
        session["plsge_2fa_verified"] = True
        session.save()

        response = client.post(
            "/api/pae/operadores/",
            data={"code": "X", "business_name": "X", "nit": "1"},
        )
        self.assertEqual(response.status_code, 403)

    def test_los_campos_calculados_no_se_aceptan_desde_el_cliente(self):
        from ..models import PaeDelivery

        plan = build_plan(self.platform, self.pae, status="EN_EJECUCION")
        response = self.api(self.responsable).post(
            "/api/pae/entregas/",
            {
                "plan": plan.pk,
                "campus": self.platform["campus"].pk,
                "service_date": timezone.localdate().isoformat(),
                "scheduled_rations": 100,
                "received_rations": 100,
                "delivered_rations": 100,
                "compliance": "10.00",
                "missing_rations": 999,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        delivery = PaeDelivery.objects.get(pk=response.json()["id"])
        self.assertEqual(float(delivery.compliance), 100.0)
        self.assertEqual(delivery.missing_rations, 0)
