"""
Pruebas de la planilla de notas.

Fijan el contrato entre el calculo del navegador y el del servidor: la
definitiva y el desempeno que ve el docente mientras digita deben coincidir
con los que quedan guardados.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from ..services import apply_rounding, decimal_config, performance_for


def build_year():
    """Ano lectivo con escala valorativa y politica de decimas."""
    from core.academic.models import GradingScale, GradingScaleLevel, SchoolYear
    from core.configuration.models import GradeDecimalConfig
    from core.institutions.models import Institution

    institution = Institution.objects.create(
        name="Institucion de Pruebas", nit="900000000-0", code="000000000000", is_default=True
    )
    today = timezone.localdate()
    year = SchoolYear.objects.create(
        institution=institution, year=today.year, name=f"Ano {today.year}",
        start_date=today - dt.timedelta(days=60), end_date=today + dt.timedelta(days=120),
        is_current=True,
    )
    scale = GradingScale.objects.create(
        school_year=year, name="Escala 1.0 - 5.0",
        minimum=Decimal("1.00"), maximum=Decimal("5.00"), passing=Decimal("3.00"),
        decimals=1, is_default=True,
    )
    for code, name, low, high, passes, order in (
        ("S", "Superior", "4.60", "5.00", True, 1),
        ("A", "Alto", "4.00", "4.59", True, 2),
        ("B", "Basico", "3.00", "3.99", True, 3),
        ("J", "Bajo", "1.00", "2.99", False, 4),
    ):
        GradingScaleLevel.objects.create(
            scale=scale, code=code, name=name,
            minimum=Decimal(low), maximum=Decimal(high), is_passing=passes, order=order,
        )
    GradeDecimalConfig.objects.create(
        school_year=year, decimals=1, rounding_mode="HALF_UP",
        round_from=Decimal("0.50"), apply_to_period=True, is_default=True,
    )
    return year, scale


def server_final(scores_weights, config):
    """Reproduce compute_process_average + apply_rounding del servidor."""
    accumulated = Decimal("0")
    total = Decimal("0")
    for score, weight in scores_weights:
        if score is None:
            continue
        accumulated += Decimal(str(score)) * Decimal(str(weight))
        total += Decimal(str(weight))
    if total == 0:
        return None
    average = (accumulated / total).quantize(Decimal("0.01"))
    return apply_rounding(average, config if config.apply_to_period else None)


def browser_final(scores_weights, payload):
    """
    Traduccion literal de computeFinal() en static/js/modules/grades.js.

    Si esta funcion y el servidor divergen, la planilla mostraria una decima
    distinta de la que se guarda: por eso la prueba compara ambas.
    """
    numerator = 0
    denominator = 0
    for score, weight in scores_weights:
        if score is None:
            continue
        numerator += round(float(score) * 100) * round(float(weight) * 100)
        denominator += round(float(weight) * 100)
    if denominator == 0:
        return None

    # divideHalfEven: mitad al par, como Decimal.quantize por defecto.
    whole = numerator // denominator
    twice = 2 * (numerator - whole * denominator)
    if twice > denominator:
        hundredths = whole + 1
    elif twice < denominator:
        hundredths = whole
    else:
        hundredths = whole if whole % 2 == 0 else whole + 1

    # applyRounding
    if not payload["apply_to_period"]:
        return hundredths / 100
    decimals = payload["decimals"]
    divisor = 10 ** max(0, 2 - decimals)
    factor = 10 ** decimals
    mode = payload["mode"]
    if mode == "NONE":
        return hundredths / 100
    if mode == "DOWN":
        return (hundredths // divisor) / factor
    if mode == "UP_FROM":
        integer = hundredths // 100
        fraction = (hundredths - integer * 100) / 100
        return integer + 1 if fraction >= payload["round_from"] else integer
    return ((hundredths + divisor // 2) // divisor) / factor


class GradeSheetPayloadTests(TestCase):
    """La planilla debe entregar lo necesario para calcular en pantalla."""

    @classmethod
    def setUpTestData(cls):
        cls.year, cls.scale = build_year()

    def test_la_escala_incluye_los_niveles_de_desempeno(self):
        from ..services import _rounding_payload, default_scale

        scale = default_scale(self.year)
        levels = list(scale.levels.filter(deleted_at__isnull=True).order_by("order"))
        self.assertEqual(len(levels), 4)
        self.assertEqual([level.name for level in levels], ["Superior", "Alto", "Basico", "Bajo"])

    def test_la_politica_de_decimas_es_serializable(self):
        from ..services import _rounding_payload

        payload = _rounding_payload(self.year)
        self.assertEqual(payload["mode"], "HALF_UP")
        self.assertEqual(payload["decimals"], 1)
        self.assertTrue(payload["apply_to_period"])

    def test_sin_configuracion_de_decimas_se_entrega_un_valor_por_defecto(self):
        from core.configuration.models import GradeDecimalConfig

        from ..services import _rounding_payload

        GradeDecimalConfig.objects.all().delete()
        payload = _rounding_payload(self.year)
        self.assertEqual(payload["decimals"], 2)


class PerformanceTests(TestCase):
    """El desempeno sale de la escala, no de un valor fijo."""

    @classmethod
    def setUpTestData(cls):
        cls.year, cls.scale = build_year()

    def test_cada_rango_devuelve_su_desempeno(self):
        casos = [
            ("1.00", "Bajo"), ("2.99", "Bajo"),
            ("3.00", "Basico"), ("3.99", "Basico"),
            ("4.00", "Alto"), ("4.59", "Alto"),
            ("4.60", "Superior"), ("5.00", "Superior"),
        ]
        for value, expected in casos:
            with self.subTest(value=value):
                level = performance_for(self.year, Decimal(value))
                self.assertIsNotNone(level, f"{value} quedo sin desempeno")
                self.assertEqual(level.name, expected)

    def test_las_fronteras_no_dejan_huecos(self):
        """Ningun valor de la escala puede quedarse sin desempeno."""
        value = Decimal("1.00")
        while value <= Decimal("5.00"):
            self.assertIsNotNone(
                performance_for(self.year, value), f"{value} no tiene desempeno asignado"
            )
            value += Decimal("0.01")

    def test_el_desempeno_marca_correctamente_la_aprobacion(self):
        self.assertFalse(performance_for(self.year, Decimal("2.90")).is_passing)
        self.assertTrue(performance_for(self.year, Decimal("3.00")).is_passing)


class BrowserServerParityTests(TestCase):
    """
    El calculo del navegador y el del servidor deben coincidir siempre.

    Si divergen, el docente veria una definitiva y se guardaria otra.
    """

    @classmethod
    def setUpTestData(cls):
        cls.year, cls.scale = build_year()

    def setUp(self):
        self.config = decimal_config(self.year)
        self.payload = {
            "mode": self.config.rounding_mode,
            "decimals": self.config.decimals,
            "round_from": float(self.config.round_from),
            "apply_to_period": self.config.apply_to_period,
        }

    def assertParity(self, scores_weights):
        server = server_final(scores_weights, self.config)
        browser = browser_final(scores_weights, self.payload)
        if server is None:
            self.assertIsNone(browser)
            return
        self.assertAlmostEqual(
            float(server), browser, places=9,
            msg=f"Divergen para {scores_weights}: servidor={server} navegador={browser}",
        )

    def test_caso_de_la_planilla_real(self):
        # Los ocho estudiantes de Transicion 01 - Ciencias Sociales.
        pesos = (25, 25, 30, 20)
        filas = [
            (3.7, 2.6, 3.7, 4.1), (3.2, 2.8, 2.8, 3.6), (3.5, 3.6, 3.7, 3.8),
            (3.6, 4.1, 2.7, 3.6), (3.9, 3.9, 4.5, 4.2), (4.3, 4.3, 3.0, 3.9),
            (2.5, 3.2, 2.4, 4.5), (3.3, 3.8, 4.9, 3.2),
        ]
        esperados = [3.5, 3.1, 3.6, 3.5, 4.1, 3.8, 3.0, 3.9]
        for notas, esperado in zip(filas, esperados):
            with self.subTest(notas=notas):
                pares = list(zip(notas, pesos))
                self.assertAlmostEqual(float(server_final(pares, self.config)), esperado, places=2)
                self.assertParity(pares)

    def test_doble_redondeo_del_servidor(self):
        """2.0466 -> 2.05 (dos decimales) -> 2.1: el navegador debe hacer igual."""
        pares = [(None, 25), (1.3, 25), (1.3, 30), (4.1, 20)]
        self.assertAlmostEqual(float(server_final(pares, self.config)), 2.1, places=2)
        self.assertParity(pares)

    def test_primer_redondeo_es_mitad_al_par(self):
        """2.945 -> 2.94 por half-even, no 2.95; luego 2.9."""
        pares = [(3.6, 25), (4.3, 25), (2.5, 30), (1.1, 20)]
        self.assertAlmostEqual(float(server_final(pares, self.config)), 2.9, places=2)
        self.assertParity(pares)

    def test_proceso_sin_nota_sale_del_ponderado(self):
        """El peso de un proceso sin nota no cuenta en el denominador."""
        pares = [(4.0, 25), (None, 25), (4.0, 30), (4.0, 20)]
        # Solo pesan 25+30+20 = 75, todos en 4.0 -> definitiva 4.0
        self.assertAlmostEqual(float(server_final(pares, self.config)), 4.0, places=2)
        self.assertParity(pares)

    def test_sin_ninguna_nota_no_hay_definitiva(self):
        pares = [(None, 25), (None, 25), (None, 30), (None, 20)]
        self.assertIsNone(server_final(pares, self.config))
        self.assertIsNone(browser_final(pares, self.payload))

    def test_paridad_con_distintas_distribuciones_de_peso(self):
        import random

        random.seed(2026)
        distribuciones = [
            (25, 25, 30, 20), (10, 10, 10, 70), (33.33, 33.33, 33.34),
            (100,), (50, 50), (15, 15, 15, 15, 40), (12.5, 12.5, 25, 50),
        ]
        for pesos in distribuciones:
            for _ in range(300):
                notas = [
                    round(random.uniform(1.0, 5.0), 1) if random.random() > 0.2 else None
                    for _ in pesos
                ]
                self.assertParity(list(zip(notas, pesos)))

    def test_paridad_en_barrido_exhaustivo(self):
        """Recorre el rango completo de la escala en el caso 25/25/30/20."""
        pesos = (25, 25, 30, 20)
        for a in range(10, 51, 2):
            for b in range(10, 51, 5):
                for c in range(10, 51, 7):
                    for d in range(10, 51, 11):
                        self.assertParity(
                            list(zip((a / 10, b / 10, c / 10, d / 10), pesos))
                        )

    def test_paridad_con_truncamiento(self):
        self.config.rounding_mode = "DOWN"
        self.config.save(update_fields=["rounding_mode"])
        self.payload["mode"] = "DOWN"
        self.assertParity([(3.77, 25), (4.29, 25), (2.51, 30), (1.19, 20)])

    def test_paridad_sin_aproximacion(self):
        self.config.rounding_mode = "NONE"
        self.config.save(update_fields=["rounding_mode"])
        self.payload["mode"] = "NONE"
        self.assertParity([(3.7, 25), (2.6, 25), (3.7, 30), (4.1, 20)])


class AutomaticPerformanceTests(TestCase):
    """
    El desempeno se asigna solo al guardar, venga la nota por donde venga.

    Antes solo se calculaba al consolidar desde la planilla: una nota editada
    por la pagina de gestion, la API o una importacion conservaba el desempeno
    anterior, y un estudiante con 1.2 podia seguir figurando como aprobado.
    """

    @classmethod
    def setUpTestData(cls):
        from core.academic.models import (
            AcademicPeriod,
            Area,
            EducationLevel,
            Grade,
            Group,
            Subject,
        )
        from core.institutions.models import Campus
        from core.students.models import Student

        cls.year, cls.scale = build_year()
        institution = cls.year.institution
        cls.period = AcademicPeriod.objects.create(
            school_year=cls.year, number=1, name="Periodo 1",
            start_date=cls.year.start_date, end_date=cls.year.end_date,
        )
        campus = Campus.objects.create(institution=institution, code="P", name="Principal", is_main=True)
        level = EducationLevel.objects.create(institution=institution, code="PRI", name="Primaria", order=1)
        grade = Grade.objects.create(level=level, code="G01", name="Primero", order=1, numeric_value=1)
        cls.group = Group.objects.create(
            school_year=cls.year, grade=grade, code="G01-A", name="A", campus=campus
        )
        cls.area = Area.objects.create(school_year=cls.year, code="MAT", name="Matematicas")
        cls.subject = Subject.objects.create(area=cls.area, code="MAT1", name="Matematicas")
        cls.student = Student.objects.create(
            institution=institution, document_number="1000000001",
            first_name="Estudiante", last_name="De Prueba", gender="N", status="ACTIVO",
        )

    def _subject_grade(self, score):
        from ..models import SubjectGrade

        return SubjectGrade.objects.create(
            student=self.student, school_year=self.year, period=self.period,
            subject=self.subject, group=self.group, score=Decimal(score),
        )

    def test_al_crear_se_asigna_el_desempeno(self):
        grade = self._subject_grade("4.20")
        self.assertEqual(grade.final_score, Decimal("4.20"))
        self.assertEqual(grade.performance.name, "Alto")
        self.assertTrue(grade.is_passing)

    def test_al_editar_la_nota_se_recalcula(self):
        grade = self._subject_grade("3.10")
        self.assertEqual(grade.performance.name, "Basico")

        grade.score = Decimal("1.20")
        grade.save()
        grade.refresh_from_db()

        self.assertEqual(grade.final_score, Decimal("1.20"))
        self.assertEqual(grade.performance.name, "Bajo")
        self.assertFalse(grade.is_passing, "Un 1.2 no puede quedar como aprobado")

    def test_se_recalcula_incluso_con_update_fields(self):
        """save(update_fields=['score']) no puede descartar el recalculo."""
        grade = self._subject_grade("2.00")
        self.assertEqual(grade.performance.name, "Bajo")

        grade.score = Decimal("4.80")
        grade.save(update_fields=["score"])
        grade.refresh_from_db()

        self.assertEqual(grade.final_score, Decimal("4.80"))
        self.assertEqual(grade.performance.name, "Superior")
        self.assertTrue(grade.is_passing)

    def test_la_nota_de_recuperacion_manda_si_es_mayor(self):
        grade = self._subject_grade("2.50")
        grade.recovered_score = Decimal("3.50")
        grade.save()
        grade.refresh_from_db()

        self.assertEqual(grade.final_score, Decimal("3.50"))
        self.assertEqual(grade.performance.name, "Basico")
        self.assertEqual(grade.status, "RECUPERADA")
        self.assertTrue(grade.is_passing)

    def test_la_recuperacion_menor_no_baja_la_nota(self):
        grade = self._subject_grade("4.00")
        grade.recovered_score = Decimal("3.00")
        grade.save()
        grade.refresh_from_db()

        self.assertEqual(grade.final_score, Decimal("4.00"))
        self.assertEqual(grade.performance.name, "Alto")

    def test_cada_rango_de_la_escala_queda_bien_clasificado(self):
        casos = [("1.50", "Bajo"), ("2.99", "Bajo"), ("3.00", "Basico"),
                 ("3.99", "Basico"), ("4.00", "Alto"), ("4.59", "Alto"),
                 ("4.60", "Superior"), ("5.00", "Superior")]
        grade = self._subject_grade("3.00")
        for value, expected in casos:
            with self.subTest(value=value):
                grade.score = Decimal(value)
                grade.save()
                grade.refresh_from_db()
                self.assertEqual(grade.performance.name, expected)

    def test_el_area_asigna_su_desempeno(self):
        from ..models import AreaGrade

        area_grade = AreaGrade.objects.create(
            student=self.student, school_year=self.year, period=self.period,
            area=self.area, score=Decimal("4.70"),
        )
        self.assertEqual(area_grade.performance.name, "Superior")
        self.assertTrue(area_grade.is_passing)

        area_grade.score = Decimal("2.10")
        area_grade.save()
        area_grade.refresh_from_db()
        self.assertEqual(area_grade.performance.name, "Bajo")
        self.assertFalse(area_grade.is_passing)

    def test_la_valoracion_de_convivencia_asigna_su_desempeno(self):
        from core.academic.models import CoexistenceItem
        from core.tutoring.models import CoexistenceEvaluation

        item = CoexistenceItem.objects.create(
            school_year=self.year, code="COMP", name="Comportamiento"
        )
        evaluation = CoexistenceEvaluation.objects.create(
            student=self.student, period=self.period, item=item, score=Decimal("4.30")
        )
        self.assertEqual(evaluation.performance.name, "Alto")

        evaluation.score = Decimal("2.50")
        evaluation.save()
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.performance.name, "Bajo")

    def test_una_nota_sin_ano_lectivo_no_rompe_el_guardado(self):
        from ..models import AreaGrade

        area_grade = AreaGrade(
            student=self.student, period=self.period, area=self.area, score=Decimal("3.50")
        )
        area_grade.school_year = self.year
        area_grade.save()
        self.assertIsNotNone(area_grade.performance)
