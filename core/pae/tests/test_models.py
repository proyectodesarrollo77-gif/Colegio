"""Pruebas unitarias de los modelos del PAE: calculos automaticos y versionado."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .factories import build_checklist, build_menu_cycle, build_pae, build_plan, build_platform


class DeliveryCalculationTests(TestCase):
    """Formulas de la entrega diaria."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.plan = build_plan(cls.platform, cls.pae)

    def _delivery(self, scheduled, received, delivered, **extra):
        from ..models import PaeDelivery

        return PaeDelivery(
            plan=self.plan,
            campus=self.platform["campus"],
            service_date=timezone.localdate(),
            scheduled_rations=scheduled,
            received_rations=received,
            delivered_rations=delivered,
            **extra,
        )

    def test_totales_sin_incumplimiento(self):
        delivery = self._delivery(100, 100, 100)
        delivery.compute_totals()
        self.assertEqual(delivery.missing_rations, 0)
        self.assertEqual(delivery.undelivered_rations, 0)
        self.assertEqual(delivery.compliance, Decimal("100.00"))
        self.assertFalse(delivery.has_noncompliance)

    def test_faltantes_y_no_entregadas(self):
        delivery = self._delivery(100, 90, 85)
        delivery.compute_totals()
        self.assertEqual(delivery.missing_rations, 10)
        self.assertEqual(delivery.undelivered_rations, 5)
        self.assertEqual(delivery.compliance, Decimal("85.00"))
        self.assertTrue(delivery.has_noncompliance)

    def test_cumplimiento_con_programadas_en_cero(self):
        delivery = self._delivery(0, 0, 0)
        delivery.compute_totals()
        self.assertEqual(delivery.compliance, Decimal("0.00"))

    def test_menu_diferente_marca_incumplimiento(self):
        delivery = self._delivery(100, 100, 100, menu_matches=False)
        delivery.compute_totals()
        self.assertTrue(delivery.has_noncompliance)

    def test_save_recalcula_totales(self):
        delivery = self._delivery(50, 48, 45, justification="Novedad de prueba")
        delivery.save()
        delivery.refresh_from_db()
        self.assertEqual(delivery.missing_rations, 2)
        self.assertEqual(delivery.undelivered_rations, 3)
        self.assertEqual(delivery.compliance, Decimal("90.00"))


class VerificationScoreTests(TestCase):
    """Puntaje ponderado y efecto de los criterios criticos."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.checklist, cls.items = build_checklist(cls.pae)

    def _verification(self, answers):
        from ..models import PaeVerification, PaeVerificationResult

        verification = PaeVerification.objects.create(
            checklist=self.checklist,
            vigencia=self.pae["vigencia"],
            campus=self.platform["campus"],
            verification_date=timezone.localdate(),
        )
        for item, answer in zip(self.items, answers):
            PaeVerificationResult.objects.create(
                verification=verification, item=item, answer=answer
            )
        verification.recalculate()
        return verification

    def test_cumple_totalmente(self):
        verification = self._verification(["CUMPLE", "CUMPLE", "CUMPLE"])
        self.assertEqual(verification.score, Decimal("100.00"))
        self.assertEqual(verification.result, "CUMPLE")
        self.assertEqual(verification.critical_failures, 0)

    def test_criterio_critico_fuerza_no_cumple(self):
        # 2 de 4 puntos de peso, pero ademas falla el criterio critico.
        verification = self._verification(["CUMPLE", "CUMPLE", "NO_CUMPLE"])
        self.assertEqual(verification.score, Decimal("50.00"))
        self.assertEqual(verification.result, "NO_CUMPLE")
        self.assertEqual(verification.critical_failures, 1)

    def test_no_aplica_se_excluye_del_denominador(self):
        verification = self._verification(["CUMPLE", "NO_APLICA", "CUMPLE"])
        self.assertEqual(verification.score, Decimal("100.00"))
        self.assertEqual(verification.result, "CUMPLE")
        self.assertEqual(verification.not_applicable_items, 1)

    def test_cumplimiento_parcial_por_umbral(self):
        # Peso obtenido 2 de 4 sin criticos: por debajo del umbral pleno.
        verification = self._verification(["NO_CUMPLE", "CUMPLE", "CUMPLE"])
        self.assertEqual(verification.score, Decimal("75.00"))
        self.assertEqual(verification.result, "CUMPLE_PARCIAL")

    def test_umbrales_parametrizables(self):
        self.checklist.threshold_full = Decimal("70.00")
        self.checklist.threshold_partial = Decimal("40.00")
        self.checklist.save(update_fields=["threshold_full", "threshold_partial"])
        verification = self._verification(["NO_CUMPLE", "CUMPLE", "CUMPLE"])
        self.assertEqual(verification.result, "CUMPLE")

    def test_sin_respuestas_queda_sin_evaluar(self):
        from ..models import PaeVerification

        verification = PaeVerification.objects.create(
            checklist=self.checklist,
            vigencia=self.pae["vigencia"],
            campus=self.platform["campus"],
            verification_date=timezone.localdate(),
        )
        verification.recalculate()
        self.assertEqual(verification.result, "SIN_EVALUAR")


class MenuVersionTests(TestCase):
    """Versionado del ciclo de menu."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def test_nueva_version_clona_la_estructura_y_archiva_el_original(self):
        from ..models import PaeMenuIngredient, PaeMenuPreparation

        cycle = build_menu_cycle(self.pae, days=3)
        clone = cycle.create_new_version(user=None)
        cycle.refresh_from_db()

        self.assertEqual(clone.version, cycle.version + 1)
        self.assertEqual(clone.parent_version_id, cycle.pk)
        self.assertEqual(cycle.status, "ARCHIVADO")
        self.assertEqual(clone.days.count(), 3)
        self.assertEqual(
            PaeMenuPreparation.objects.filter(day__cycle=clone).count(),
            PaeMenuPreparation.objects.filter(day__cycle=cycle).count(),
        )
        self.assertEqual(
            PaeMenuIngredient.objects.filter(preparation__day__cycle=clone).count(),
            PaeMenuIngredient.objects.filter(preparation__day__cycle=cycle).count(),
        )

    def test_calorias_del_dia_suman_las_preparaciones(self):
        cycle = build_menu_cycle(self.pae, days=1)
        day = cycle.days.first()
        self.assertEqual(day.total_calories, Decimal("100.00"))


class PlanAndVigenciaTests(TestCase):
    """Codigo automatico, transiciones declaradas y avance de la vigencia."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def test_el_plan_genera_codigo_automatico(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        self.assertTrue(plan.code.startswith("PAE-"))

    def test_raciones_proyectadas_se_calculan(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        self.assertEqual(plan.projected_rations, plan.beneficiaries_count * plan.service_days)

    def test_plan_editable_solo_en_borrador_y_revision(self):
        borrador = build_plan(self.platform, self.pae, status="BORRADOR")
        aprobado = build_plan(
            self.platform, self.pae, status="APROBADO", campus=self.platform["other_campus"]
        )
        self.assertTrue(borrador.is_editable)
        self.assertFalse(aprobado.is_editable)

    def test_transiciones_declaradas_del_plan(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        self.assertEqual([t for t, _ in plan.allowed_transitions()], ["EN_REVISION"])
        plan.status = "CERRADO"
        self.assertEqual(plan.allowed_transitions(), [])

    def test_una_sola_vigencia_en_curso(self):
        from core.academic.models import SchoolYear

        from ..models import PaeVigencia

        other_year = SchoolYear.objects.create(
            institution=self.platform["institution"],
            year=self.platform["year"].year + 1,
            name="Siguiente",
            start_date=self.platform["year"].end_date + dt.timedelta(days=1),
            end_date=self.platform["year"].end_date + dt.timedelta(days=200),
        )
        nueva = PaeVigencia.objects.create(
            institution=self.platform["institution"],
            school_year=other_year,
            name="PAE siguiente",
            start_date=other_year.start_date,
            end_date=other_year.end_date,
            is_current=True,
        )
        self.pae["vigencia"].refresh_from_db()
        self.assertFalse(self.pae["vigencia"].is_current)
        self.assertEqual(PaeVigencia.current().pk, nueva.pk)

    def test_avance_de_la_vigencia_entre_0_y_100(self):
        self.assertGreaterEqual(self.pae["vigencia"].progress, 0)
        self.assertLessEqual(self.pae["vigencia"].progress, 100)


class SiteDiagnosisTests(TestCase):
    """Puntaje ponderado del diagnostico de sede."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def _diagnosis(self, condition):
        from ..models import PaeSiteDiagnosis

        fields = {
            name: condition
            for name in (
                "infrastructure", "kitchen", "dining_room", "storage", "refrigeration",
                "water", "energy", "gas", "equipment", "sanitary", "accessibility",
            )
        }
        return PaeSiteDiagnosis.objects.create(
            vigencia=self.pae["vigencia"], campus=self.platform["campus"], **fields
        )

    def test_condiciones_optimas_dan_puntaje_maximo(self):
        diagnosis = self._diagnosis("OPTIMA")
        self.assertEqual(diagnosis.compute_score(), Decimal("100.00"))

    def test_condiciones_inexistentes_dan_puntaje_minimo(self):
        diagnosis = self._diagnosis("NO_EXISTE")
        self.assertEqual(diagnosis.compute_score(), Decimal("0.00"))

    def test_no_aplica_no_penaliza(self):
        diagnosis = self._diagnosis("NO_APLICA")
        self.assertEqual(diagnosis.compute_score(), Decimal("0.00"))
