"""
Pruebas de las reglas de negocio del PAE (casos positivos y negativos).

Cubre las 12 reglas declaradas en `core.pae.services`.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .. import services
from .factories import (
    build_menu_cycle,
    build_pae,
    build_plan,
    build_platform,
    build_student,
    build_user,
    seed_modules,
)


class DeliveryRuleTests(TestCase):
    """Reglas 1, 2 y 3: sede del plan, raciones y justificacion."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.plan = build_plan(cls.platform, cls.pae)

    def _delivery(self, **kwargs):
        from ..models import PaeDelivery

        data = {
            "plan": self.plan,
            "campus": self.platform["campus"],
            "service_date": timezone.localdate(),
            "scheduled_rations": 100,
            "received_rations": 100,
            "delivered_rations": 100,
        }
        data.update(kwargs)
        delivery = PaeDelivery(**data)
        delivery.compute_totals()
        return delivery

    # --- positivos ----------------------------------------------------
    def test_entrega_completa_es_valida(self):
        self.assertEqual(services.validate_delivery(self._delivery(), raise_error=False), {})

    def test_incumplimiento_con_justificacion_es_valido(self):
        delivery = self._delivery(received_rations=90, delivered_rations=90,
                                  justification="Retraso del proveedor")
        self.assertEqual(services.validate_delivery(delivery, raise_error=False), {})

    # --- negativos ----------------------------------------------------
    def test_regla_1_sede_ajena_al_plan(self):
        delivery = self._delivery(campus=self.platform["other_campus"])
        errors = services.validate_delivery(delivery, raise_error=False)
        self.assertIn("campus", errors)

    def test_regla_2_no_se_entrega_mas_de_lo_recibido(self):
        delivery = self._delivery(received_rations=80, delivered_rations=95)
        errors = services.validate_delivery(delivery, raise_error=False)
        self.assertIn("delivered_rations", errors)

    def test_regla_3_exceso_sobre_lo_programado_exige_justificacion(self):
        delivery = self._delivery(scheduled_rations=80, received_rations=100, delivered_rations=100)
        errors = services.validate_delivery(delivery, raise_error=False)
        self.assertIn("justification", errors)

    def test_regla_3_faltantes_exigen_justificacion(self):
        delivery = self._delivery(received_rations=90, delivered_rations=90)
        errors = services.validate_delivery(delivery, raise_error=False)
        self.assertIn("justification", errors)

    def test_hora_de_entrega_anterior_a_la_llegada(self):
        delivery = self._delivery(arrival_time=dt.time(8, 0), delivery_time=dt.time(7, 0))
        errors = services.validate_delivery(delivery, raise_error=False)
        self.assertIn("delivery_time", errors)

    def test_eleva_validation_error_cuando_se_solicita(self):
        with self.assertRaises(ValidationError):
            services.validate_delivery(self._delivery(received_rations=80, delivered_rations=95))


class BeneficiaryRuleTests(TestCase):
    """Reglas 7 y 8: estudiante existente y sin duplicados."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.student, cls.enrollment = build_student(cls.platform)

    def _beneficiary(self, **kwargs):
        from ..models import PaeBeneficiary

        data = {
            "vigencia": self.pae["vigencia"],
            "student": self.student,
            "enrollment": self.enrollment,
            "start_date": self.pae["vigencia"].start_date,
        }
        data.update(kwargs)
        return PaeBeneficiary(**data)

    def test_beneficiario_valido(self):
        self.assertEqual(services.validate_beneficiary(self._beneficiary(), raise_error=False), {})

    def test_regla_7_estudiante_retirado_no_puede_estar_activo(self):
        self.student.status = "RETIRADO"
        self.student.save(update_fields=["status"])
        errors = services.validate_beneficiary(self._beneficiary(status="ACTIVO"), raise_error=False)
        self.assertIn("student", errors)

    def test_regla_8_no_se_duplica_en_la_misma_vigencia(self):
        self._beneficiary().save()
        errors = services.validate_beneficiary(self._beneficiary(), raise_error=False)
        self.assertIn("student", errors)
        self.assertIn("ya esta registrado", errors["student"])

    def test_fecha_final_anterior_al_inicio(self):
        beneficiary = self._beneficiary(
            start_date=timezone.localdate(), end_date=timezone.localdate() - dt.timedelta(days=1)
        )
        errors = services.validate_beneficiary(beneficiary, raise_error=False)
        self.assertIn("end_date", errors)

    def test_regla_11_el_cambio_de_estado_deja_historial(self):
        from ..models import PaeBeneficiaryHistory

        beneficiary = self._beneficiary()
        beneficiary.save()
        services.change_beneficiary_status(beneficiary, "RETIRADO", reason="Traslado de ciudad")
        beneficiary.refresh_from_db()
        self.assertEqual(beneficiary.status, "RETIRADO")
        self.assertIsNotNone(beneficiary.end_date)

        history = PaeBeneficiaryHistory.objects.filter(beneficiary=beneficiary).order_by("changed_at")
        # Una fila por el registro inicial y una sola por la transicion.
        self.assertEqual(history.count(), 2)
        transicion = history.last()
        self.assertEqual(transicion.previous_status, "ACTIVO")
        self.assertEqual(transicion.new_status, "RETIRADO")
        self.assertEqual(transicion.reason, "Traslado de ciudad")

    def test_un_cambio_de_estado_no_duplica_el_historial(self):
        from ..models import PaeBeneficiaryHistory

        beneficiary = self._beneficiary()
        beneficiary.save()
        services.change_beneficiary_status(beneficiary, "SUSPENDIDO", reason="Suspension temporal")
        services.change_beneficiary_status(beneficiary, "ACTIVO", reason="Reactivacion")
        rows = PaeBeneficiaryHistory.objects.filter(beneficiary=beneficiary)
        self.assertEqual(rows.count(), 3)
        self.assertEqual(rows.filter(new_status="SUSPENDIDO").count(), 1)

    def test_el_beneficiario_hereda_sede_y_grado_de_la_matricula(self):
        beneficiary = self._beneficiary()
        beneficiary.save()
        self.assertEqual(beneficiary.campus_id, self.platform["campus"].pk)
        self.assertEqual(beneficiary.grade_id, self.platform["grade"].pk)


class PlanRuleTests(TestCase):
    """Regla 6: edicion de planes aprobados y transiciones de estado."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.responsable = build_user("responsable@test.local", "RESPONSABLE_PAE", cls.platform["institution"])
        cls.operador = build_user("operador@test.local", "OPERADOR_PAE", cls.platform["institution"])

    def test_plan_en_borrador_lo_edita_cualquiera_con_acceso(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        self.assertEqual(services.validate_plan_edit(plan, self.operador, raise_error=False), {})

    def test_regla_6_plan_aprobado_requiere_permiso_de_aprobacion(self):
        plan = build_plan(self.platform, self.pae, status="APROBADO")
        errors = services.validate_plan_edit(plan, self.operador, raise_error=False)
        self.assertIn("status", errors)

    def test_regla_6_el_responsable_si_puede_editar_un_plan_aprobado(self):
        plan = build_plan(self.platform, self.pae, status="APROBADO")
        self.assertEqual(services.validate_plan_edit(plan, self.responsable, raise_error=False), {})

    def test_transicion_valida_registra_historial(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        services.change_plan_status(plan, "EN_REVISION", user=self.responsable, reason="Listo")
        plan.refresh_from_db()
        self.assertEqual(plan.status, "EN_REVISION")
        self.assertEqual(plan.state_history.count(), 1)

    def test_transicion_invalida_se_rechaza(self):
        plan = build_plan(self.platform, self.pae, status="BORRADOR")
        with self.assertRaises(ValidationError):
            services.change_plan_status(plan, "CERRADO", user=self.responsable)

    def test_aprobacion_registra_usuario_y_fecha(self):
        plan = build_plan(self.platform, self.pae, status="EN_REVISION")
        services.change_plan_status(plan, "APROBADO", user=self.responsable)
        plan.refresh_from_db()
        self.assertEqual(plan.approved_by_id, self.responsable.pk)
        self.assertIsNotNone(plan.approved_at)


class IncidentRuleTests(TestCase):
    """Regla 4: no se cierra una novedad sin solucion."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def _incident(self, status="SOLUCIONADA", solution=""):
        from ..models import PaeIncident

        return PaeIncident.objects.create(
            vigencia=self.pae["vigencia"],
            campus=self.platform["campus"],
            description="Novedad de prueba",
            status=status,
            solution=solution,
        )

    def test_regla_4_cerrar_sin_solucion_falla(self):
        incident = self._incident()
        with self.assertRaises(ValidationError):
            services.change_incident_status(incident, "CERRADA")

    def test_regla_4_cerrar_con_solucion_funciona(self):
        incident = self._incident(solution="Se reprogramo la entrega")
        services.change_incident_status(incident, "CERRADA", comment="Verificado")
        incident.refresh_from_db()
        self.assertEqual(incident.status, "CERRADA")
        self.assertIsNotNone(incident.closed_at)
        self.assertEqual(incident.history.count(), 1)

    def test_transicion_no_permitida(self):
        incident = self._incident(status="REPORTADA")
        with self.assertRaises(ValidationError):
            services.change_incident_status(incident, "CERRADA")

    def test_flujo_completo_de_estados(self):
        incident = self._incident(status="REPORTADA")
        for target in ("ASIGNADA", "EN_CORRECCION", "SOLUCIONADA"):
            services.change_incident_status(incident, target)
        incident.solution = "Accion correctiva aplicada"
        incident.save(update_fields=["solution"])
        services.change_incident_status(incident, "CERRADA")
        incident.refresh_from_db()
        self.assertEqual(incident.status, "CERRADA")
        self.assertEqual(incident.history.count(), 4)


class ImprovementActionRuleTests(TestCase):
    """Regla 5: cierre de acciones con verificacion y evidencia."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def _action(self, **kwargs):
        from ..models import PaeImprovementAction

        data = {
            "vigencia": self.pae["vigencia"],
            "campus": self.platform["campus"],
            "finding_description": "Hallazgo de prueba",
            "action": "Accion de prueba",
            "due_date": timezone.localdate() + dt.timedelta(days=10),
        }
        data.update(kwargs)
        return PaeImprovementAction.objects.create(**data)

    def test_regla_5_sin_verificacion_no_cierra(self):
        errors = services.validate_action_close(self._action(), raise_error=False)
        self.assertIn("verification_note", errors)

    def test_regla_5_exige_evidencia_cuando_corresponde(self):
        action = self._action(verification_note="Verificado en sitio", requires_evidence=True)
        errors = services.validate_action_close(action, raise_error=False)
        self.assertIn("evidence", errors)

    def test_regla_5_sin_exigencia_de_evidencia_cierra(self):
        action = self._action(verification_note="Verificado en sitio", requires_evidence=False)
        self.assertEqual(services.validate_action_close(action, raise_error=False), {})

    def test_regla_5_con_evidencia_cargada_cierra(self):
        from ..models import PaeEvidence

        action = self._action(verification_note="Verificado en sitio", requires_evidence=True)
        PaeEvidence.objects.create(
            module="MEJORAMIENTO", reference_id=action.pk, name="Soporte", description="Evidencia"
        )
        self.assertEqual(services.validate_action_close(action, raise_error=False), {})


class ScheduleGenerationTests(TestCase):
    """Generacion masiva de programaciones con rotacion del ciclo de menu."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.cycle = build_menu_cycle(cls.pae, days=3)
        cls.plan = build_plan(cls.platform, cls.pae, status="APROBADO")
        cls.plan.menu_cycle = cls.cycle
        cls.plan.save(update_fields=["menu_cycle"])

    def test_genera_solo_dias_habiles(self):
        start = timezone.localdate()
        start += dt.timedelta(days=(1 - start.isoweekday()) % 7)  # proximo lunes
        result = services.generate_schedules(self.plan, start, start + dt.timedelta(days=6))
        self.assertEqual(result["created"], 5)

    def test_no_duplica_fechas_ya_programadas(self):
        start = timezone.localdate()
        start += dt.timedelta(days=(1 - start.isoweekday()) % 7)
        services.generate_schedules(self.plan, start, start + dt.timedelta(days=6))
        result = services.generate_schedules(self.plan, start, start + dt.timedelta(days=6))
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"], 5)

    def test_rota_los_dias_del_ciclo_de_menu(self):
        from ..models import PaeSchedule

        start = timezone.localdate()
        start += dt.timedelta(days=(1 - start.isoweekday()) % 7)
        services.generate_schedules(self.plan, start, start + dt.timedelta(days=6))
        menus = list(
            PaeSchedule.objects.filter(plan=self.plan).order_by("service_date")
            .values_list("menu_day__day_number", flat=True)
        )
        self.assertEqual(menus, [1, 2, 3, 1, 2])

    def test_respeta_los_dias_seleccionados(self):
        start = timezone.localdate()
        start += dt.timedelta(days=(1 - start.isoweekday()) % 7)
        result = services.generate_schedules(
            self.plan, start, start + dt.timedelta(days=6), weekdays=[1, 3]
        )
        self.assertEqual(result["created"], 2)


class PrioritizationEnrollmentTests(TestCase):
    """Vinculacion masiva de beneficiarios desde una priorizacion."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        for index in range(5):
            build_student(cls.platform, document=f"200000000{index}")

    def _prioritization(self, status="APROBADA"):
        from ..models import PaePrioritization

        return PaePrioritization.objects.create(
            vigencia=self.pae["vigencia"], campus=self.platform["campus"], status=status
        )

    def test_solo_se_vinculan_priorizaciones_aprobadas(self):
        with self.assertRaises(ValidationError):
            services.enroll_prioritized_students(self._prioritization(status="BORRADOR"))

    def test_vincula_los_estudiantes_matriculados(self):
        result = services.enroll_prioritized_students(self._prioritization())
        self.assertEqual(result["created"], 5)

    def test_segunda_ejecucion_no_duplica(self):
        prioritization = self._prioritization()
        services.enroll_prioritized_students(prioritization)
        result = services.enroll_prioritized_students(prioritization)
        self.assertEqual(result["created"], 0)


class DashboardAndAlertTests(TestCase):
    """Reglas 9 y 10: tablero e alertas operativas."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.student, cls.enrollment = build_student(cls.platform)

    def test_sin_vigencia_el_tablero_responde_vacio(self):
        data = services.build_dashboard(None)
        self.assertEqual(data["cards"], [])
        self.assertIsNone(data["vigencia"])

    def test_sin_vigencia_se_alerta_la_falta_de_configuracion(self):
        alerts = services.build_alerts(None)
        self.assertEqual(alerts[0]["code"], "sin_vigencia")

    def test_cobertura_se_calcula_sobre_la_matricula_activa(self):
        from ..models import PaeBeneficiary

        PaeBeneficiary.objects.create(
            vigencia=self.pae["vigencia"], student=self.student, enrollment=self.enrollment,
            start_date=self.pae["vigencia"].start_date,
        )
        data = services.build_dashboard(self.pae["vigencia"])
        self.assertEqual(data["totals"]["enrolled"], 1)
        self.assertEqual(data["totals"]["beneficiaries"], 1)
        self.assertEqual(data["totals"]["coverage"], 100)

    def test_regla_9_contrato_vencido_genera_alerta(self):
        from ..models import PaeContract, PaeOperator

        operator = PaeOperator.objects.create(
            institution=self.platform["institution"], code="OP1",
            business_name="Operador de prueba", nit="900111111-1",
        )
        contract = PaeContract.objects.create(
            vigencia=self.pae["vigencia"], operator=operator, number="CT-1",
            subject="Objeto", start_date=timezone.localdate() - dt.timedelta(days=120),
            end_date=timezone.localdate() - dt.timedelta(days=1), status="VIGENTE",
        )
        # La senal marca como VENCIDO todo contrato que ya vencio al guardarlo.
        # El caso real es el contrato que vence sin que nadie lo vuelva a
        # guardar: se reproduce escribiendo el estado sin pasar por save().
        PaeContract.objects.filter(pk=contract.pk).update(status="VIGENTE")
        codes = [alert["code"] for alert in services.build_alerts(self.pae["vigencia"])]
        self.assertIn("contratos_vencidos", codes)

    def test_la_senal_marca_como_vencido_el_contrato_al_guardarlo(self):
        from ..models import PaeContract, PaeOperator

        operator = PaeOperator.objects.create(
            institution=self.platform["institution"], code="OP2",
            business_name="Operador vencido", nit="900222222-2",
        )
        contract = PaeContract.objects.create(
            vigencia=self.pae["vigencia"], operator=operator, number="CT-2",
            subject="Objeto", start_date=timezone.localdate() - dt.timedelta(days=120),
            end_date=timezone.localdate() - dt.timedelta(days=1), status="VIGENTE",
        )
        contract.refresh_from_db()
        self.assertEqual(contract.status, "VENCIDO")

    def test_regla_10_accion_vencida_genera_alerta(self):
        from ..models import PaeImprovementAction

        PaeImprovementAction.objects.create(
            vigencia=self.pae["vigencia"], campus=self.platform["campus"],
            finding_description="Hallazgo", action="Accion",
            due_date=timezone.localdate() - dt.timedelta(days=3), status="EN_EJECUCION",
        )
        codes = [alert["code"] for alert in services.build_alerts(self.pae["vigencia"])]
        self.assertIn("acciones_vencidas", codes)

    def test_los_indicadores_se_persisten(self):
        from ..models import PaeIndicator

        saved = services.refresh_indicators(self.pae["vigencia"])
        self.assertGreater(saved, 0)
        self.assertEqual(PaeIndicator.objects.filter(vigencia=self.pae["vigencia"]).count(), saved)

    def test_recalcular_indicadores_no_los_duplica(self):
        from ..models import PaeIndicator

        services.refresh_indicators(self.pae["vigencia"])
        first = PaeIndicator.objects.filter(vigencia=self.pae["vigencia"]).count()
        services.refresh_indicators(self.pae["vigencia"])
        self.assertEqual(PaeIndicator.objects.filter(vigencia=self.pae["vigencia"]).count(), first)

    def test_las_metas_de_la_vigencia_llegan_a_las_tarjetas(self):
        data = services.build_dashboard(self.pae["vigencia"])
        cobertura = next(card for card in data["cards"] if card["code"] == "cobertura")
        self.assertEqual(Decimal(str(cobertura["goal"])), self.pae["vigencia"].coverage_goal)
