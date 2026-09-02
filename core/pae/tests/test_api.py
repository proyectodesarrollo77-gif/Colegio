"""
Pruebas de integracion de la API del PAE.

Verifica que las reglas de negocio se apliquen tambien cuando la operacion
entra por la API, no solo al invocar los servicios directamente.
"""
from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .factories import (
    build_checklist,
    build_menu_cycle,
    build_pae,
    build_plan,
    build_platform,
    build_student,
    build_user,
    seed_modules,
)


class PaeApiTestCase(TestCase):
    """Base con un usuario responsable del programa autenticado."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.user = build_user("api@test.local", "RESPONSABLE_PAE", cls.platform["institution"])

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class DashboardApiTests(PaeApiTestCase):
    def test_el_tablero_responde_con_la_estructura_esperada(self):
        response = self.client.get("/api/pae/dashboard/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        for key in ("vigencia", "cards", "charts", "alerts", "totals"):
            self.assertIn(key, payload)

    def test_las_alertas_se_listan(self):
        response = self.client.get("/api/pae/alertas/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_el_tablero_acepta_filtro_por_sede(self):
        response = self.client.get("/api/pae/dashboard/", {"campus": self.platform["campus"].pk})
        self.assertEqual(response.status_code, 200)


class BeneficiaryApiTests(PaeApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.student, cls.enrollment = build_student(cls.platform)

    def _payload(self, **extra):
        data = {
            "vigencia": self.pae["vigencia"].pk,
            "student": self.student.pk,
            "enrollment": self.enrollment.pk,
            "start_date": self.pae["vigencia"].start_date.isoformat(),
            "status": "ACTIVO",
        }
        data.update(extra)
        return data

    def test_crear_beneficiario(self):
        response = self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        self.assertEqual(response.status_code, 201)

    def test_regla_8_el_duplicado_se_rechaza_en_la_api(self):
        self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        response = self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertIn("student", detail)
        self.assertIn("ya esta registrado", detail["student"][0])

    def test_cambio_de_estado_por_la_api(self):
        created = self.client.post("/api/pae/beneficiarios/", self._payload(), format="json").json()
        response = self.client.post(
            f"/api/pae/beneficiarios/{created['id']}/change-status/",
            {"status": "RETIRADO", "reason": "Traslado"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "RETIRADO")

    def test_historial_del_beneficiario(self):
        created = self.client.post("/api/pae/beneficiarios/", self._payload(), format="json").json()
        response = self.client.get(f"/api/pae/beneficiarios/{created['id']}/history/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["results"]), 1)

    def test_cobertura(self):
        self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        response = self.client.get("/api/pae/beneficiarios/coverage/")
        self.assertEqual(response.status_code, 200)

    def test_exportacion_xlsx(self):
        self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        response = self.client.get("/api/pae/beneficiarios/export/", {"format": "xlsx"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheet", response["Content-Type"])

    def test_exportacion_csv(self):
        self.client.post("/api/pae/beneficiarios/", self._payload(), format="json")
        response = self.client.get("/api/pae/beneficiarios/export/", {"format": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("csv", response["Content-Type"])


class PlanApiTests(PaeApiTestCase):
    def test_transicion_valida(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        response = self.client.post(
            f"/api/pae/planes/{plan.pk}/transition/",
            {"status": "EN_REVISION", "reason": "Listo para revision"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "EN_REVISION")

    def test_transicion_invalida_devuelve_400(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        response = self.client.post(
            f"/api/pae/planes/{plan.pk}/transition/", {"status": "CERRADO"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_sincronizacion_de_beneficiarios(self):
        student, enrollment = build_student(self.platform, document="3000000001")
        from ..models import PaeBeneficiary

        PaeBeneficiary.objects.create(
            vigencia=self.pae["vigencia"], student=student, enrollment=enrollment,
            campus=self.platform["campus"], start_date=self.pae["vigencia"].start_date,
        )
        plan = build_plan(self.platform, self.pae, status="APROBADO")
        response = self.client.post(f"/api/pae/planes/{plan.pk}/sync-beneficiaries/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["beneficiaries"], 1)

    def test_el_serializer_expone_las_transiciones_permitidas(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        response = self.client.get(f"/api/pae/planes/{plan.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["status"] for item in response.json()["allowed_transitions"]], ["EN_REVISION"]
        )


class ScheduleApiTests(PaeApiTestCase):
    def test_generacion_masiva(self):
        cycle = build_menu_cycle(self.pae, days=2)
        plan = build_plan(self.platform, self.pae, status="APROBADO")
        plan.menu_cycle = cycle
        plan.save(update_fields=["menu_cycle"])

        start = timezone.localdate()
        start += dt.timedelta(days=(1 - start.isoweekday()) % 7)
        response = self.client.post(
            "/api/pae/programacion/generate/",
            {
                "plan": plan.pk,
                "start_date": start.isoformat(),
                "end_date": (start + dt.timedelta(days=4)).isoformat(),
                "weekdays": [1, 2, 3, 4, 5],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 5)

    def test_no_se_programa_sobre_un_plan_en_borrador(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        start = timezone.localdate()
        response = self.client.post(
            "/api/pae/programacion/generate/",
            {"plan": plan.pk, "start_date": start.isoformat(),
             "end_date": (start + dt.timedelta(days=4)).isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rango_invertido_se_rechaza(self):
        plan = build_plan(self.platform, self.pae, status="APROBADO")
        start = timezone.localdate()
        response = self.client.post(
            "/api/pae/programacion/generate/",
            {"plan": plan.pk, "start_date": start.isoformat(),
             "end_date": (start - dt.timedelta(days=1)).isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class DeliverySheetApiTests(PaeApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cycle = build_menu_cycle(cls.pae, days=1)
        cls.plan = build_plan(cls.platform, cls.pae, status="EN_EJECUCION")
        cls.plan.menu_cycle = cls.cycle
        cls.plan.save(update_fields=["menu_cycle"])

    def _schedule(self, service_date=None, rations=100):
        from ..models import PaeSchedule

        return PaeSchedule.objects.create(
            plan=self.plan,
            service_date=service_date or timezone.localdate(),
            campus=self.platform["campus"],
            complement_type=self.pae["complement"],
            menu_day=self.cycle.days.first(),
            beneficiaries_count=rations,
            scheduled_rations=rations,
        )

    def test_la_planilla_carga_la_programacion_del_dia(self):
        schedule = self._schedule()
        response = self.client.get(
            "/api/pae/planilla-entregas/", {"date": schedule.service_date.isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["scheduled"], 100)
        self.assertEqual(rows[0]["status"], "PENDIENTE")

    def test_guardado_en_bloque_de_una_entrega_completa(self):
        schedule = self._schedule()
        response = self.client.post(
            "/api/pae/planilla-entregas/",
            {
                "service_date": schedule.service_date.isoformat(),
                "rows": [{"schedule": schedule.pk, "received_rations": 100, "delivered_rations": 100}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saved"], 1)

        from ..models import PaeDelivery

        delivery = PaeDelivery.objects.get(schedule=schedule)
        self.assertEqual(delivery.status, "REGISTRADA")
        self.assertEqual(float(delivery.compliance), 100.0)

    def test_regla_2_la_planilla_rechaza_entregar_mas_de_lo_recibido(self):
        schedule = self._schedule()
        response = self.client.post(
            "/api/pae/planilla-entregas/",
            {
                "service_date": schedule.service_date.isoformat(),
                "rows": [{"schedule": schedule.pk, "received_rations": 80, "delivered_rations": 100}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivered_rations", response.json()["errors"]["0"])

    def test_regla_3_la_planilla_exige_justificacion_ante_faltantes(self):
        schedule = self._schedule()
        response = self.client.post(
            "/api/pae/planilla-entregas/",
            {
                "service_date": schedule.service_date.isoformat(),
                "rows": [{"schedule": schedule.pk, "received_rations": 90, "delivered_rations": 90}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("justification", response.json()["errors"]["0"])

    def test_una_fila_invalida_revierte_toda_la_planilla(self):
        from ..models import PaeDelivery

        valid = self._schedule()
        invalid = self._schedule(service_date=valid.service_date, rations=50)
        invalid.complement_type = None
        invalid.save(update_fields=["complement_type"])

        response = self.client.post(
            "/api/pae/planilla-entregas/",
            {
                "service_date": valid.service_date.isoformat(),
                "rows": [
                    {"schedule": valid.pk, "received_rations": 100, "delivered_rations": 100},
                    {"schedule": invalid.pk, "received_rations": 40, "delivered_rations": 60},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaeDelivery.objects.count(), 0)

    def test_incumplimiento_justificado_queda_con_novedad(self):
        schedule = self._schedule()
        response = self.client.post(
            "/api/pae/planilla-entregas/",
            {
                "service_date": schedule.service_date.isoformat(),
                "rows": [{
                    "schedule": schedule.pk, "received_rations": 90, "delivered_rations": 90,
                    "justification": "El proveedor entrego menos raciones",
                }],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        from ..models import PaeDelivery

        delivery = PaeDelivery.objects.get(schedule=schedule)
        self.assertEqual(delivery.status, "CON_NOVEDAD")
        self.assertEqual(delivery.missing_rations, 10)


class VerificationSheetApiTests(PaeApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.checklist, cls.items = build_checklist(cls.pae)

    def _verification(self):
        from ..models import PaeVerification, PaeVerificationResult

        verification = PaeVerification.objects.create(
            checklist=self.checklist,
            vigencia=self.pae["vigencia"],
            campus=self.platform["campus"],
            verification_date=timezone.localdate(),
        )
        for item in self.items:
            PaeVerificationResult.objects.create(verification=verification, item=item)
        return verification

    def test_la_hoja_agrupa_los_criterios_y_expone_los_umbrales(self):
        verification = self._verification()
        response = self.client.get("/api/pae/hoja-verificacion/", {"verification": verification.pk})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["thresholds"], {"full": 90.0, "partial": 70.0})
        self.assertEqual(len(payload["categories"]), 1)
        self.assertEqual(len(payload["categories"][0]["items"]), 3)

    def test_guardar_respuestas_recalcula_el_resultado(self):
        verification = self._verification()
        response = self.client.post(
            "/api/pae/hoja-verificacion/",
            {
                "verification": verification.pk,
                "entries": [
                    {"item": self.items[0].pk, "answer": "CUMPLE"},
                    {"item": self.items[1].pk, "answer": "CUMPLE"},
                    {"item": self.items[2].pk, "answer": "CUMPLE"},
                ],
                "observations": "Todo conforme",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saved"], 3)
        self.assertEqual(response.json()["verification"]["result"], "CUMPLE")

    def test_un_criterio_critico_incumplido_fuerza_no_cumple(self):
        verification = self._verification()
        response = self.client.post(
            "/api/pae/hoja-verificacion/",
            {
                "verification": verification.pk,
                "entries": [
                    {"item": self.items[0].pk, "answer": "CUMPLE"},
                    {"item": self.items[1].pk, "answer": "CUMPLE"},
                    {"item": self.items[2].pk, "answer": "NO_CUMPLE"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verification"]["result"], "NO_CUMPLE")

    def test_respuesta_no_valida_se_rechaza(self):
        verification = self._verification()
        response = self.client.post(
            "/api/pae/hoja-verificacion/",
            {
                "verification": verification.pk,
                "entries": [{"item": self.items[0].pk, "answer": "TAL_VEZ"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class MenuApiTests(PaeApiTestCase):
    def test_detalle_del_ciclo(self):
        cycle = build_menu_cycle(self.pae, days=2)
        response = self.client.get(f"/api/pae/menus/{cycle.pk}/detail/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["days"]), 2)

    def test_nueva_version(self):
        cycle = build_menu_cycle(self.pae, days=2)
        response = self.client.post(f"/api/pae/menus/{cycle.pk}/new-version/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["cycle"]["version"], 2)

    def test_publicar_archiva_las_versiones_anteriores(self):
        from ..models import PaeMenuCycle

        cycle = build_menu_cycle(self.pae, days=1)
        clone = cycle.create_new_version(user=self.user)
        response = self.client.post(f"/api/pae/menus/{clone.pk}/publish/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        clone.refresh_from_db()
        self.assertEqual(clone.status, "VIGENTE")
        self.assertEqual(
            PaeMenuCycle.objects.filter(code=cycle.code, status="VIGENTE").count(), 1
        )


class CatalogApiTests(PaeApiTestCase):
    def test_los_tipos_de_catalogo_se_listan_con_su_conteo(self):
        from ..models import PaeCatalog

        PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="NO_ENTREGA", name="No entrega"
        )
        response = self.client.get("/api/pae/catalogos/types/")
        self.assertEqual(response.status_code, 200)
        rows = {row["value"]: row["count"] for row in response.json()["results"]}
        self.assertEqual(rows[PaeCatalog.TYPE_INCIDENT], 1)
        self.assertEqual(rows[PaeCatalog.TYPE_VISIT], 0)

    def test_filtrado_por_tipo_de_catalogo(self):
        from ..models import PaeCatalog

        PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="NO_ENTREGA", name="No entrega"
        )
        PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_VISIT, code="SEGUIMIENTO", name="Seguimiento"
        )
        response = self.client.get(
            "/api/pae/catalogos/", {"catalog_type": PaeCatalog.TYPE_INCIDENT}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)


class VigenciaApiTests(PaeApiTestCase):
    def test_definir_vigencia_actual(self):
        response = self.client.post(
            f"/api/pae/vigencias/{self.pae['vigencia'].pk}/set-current/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.pae["vigencia"].refresh_from_db()
        self.assertTrue(self.pae["vigencia"].is_current)

    def test_recalcular_indicadores(self):
        response = self.client.post(
            f"/api/pae/vigencias/{self.pae['vigencia'].pk}/refresh-indicators/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["indicators"], 0)


class SoftDeleteApiTests(PaeApiTestCase):
    def test_el_borrado_es_logico(self):
        from ..models import PaeCatalog

        catalog = PaeCatalog.objects.create(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="TMP", name="Temporal"
        )
        response = self.client.delete(f"/api/pae/catalogos/{catalog.pk}/")
        self.assertIn(response.status_code, (200, 204))

        catalog.refresh_from_db()
        self.assertIsNotNone(catalog.deleted_at)
        listing = self.client.get("/api/pae/catalogos/").json()
        self.assertEqual(listing["count"], 0)
