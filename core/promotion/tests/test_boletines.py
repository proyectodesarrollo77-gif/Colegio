"""
Pruebas de la entrega de boletines: por estudiante y por grupo.

Lo que se protege aqui: que imprimir un grupo entero produzca una hoja por
estudiante, que el documento en lote sea el mismo que el individual, y que un
boletin no se pueda imprimir desde otra institucion.
"""
from __future__ import annotations

from django.test import Client, TestCase

from core.institutions.tests.test_multi_institucion import (
    build_institution,
    build_user,
    seed_modules,
)

from ..models import FinalReportCard


def build_card(institution, school_year, group, *, nombre, apellido, period=None):
    """Boletin de un estudiante nuevo del grupo indicado."""
    from core.students.models import Enrollment, Student

    student = Student.objects.create(
        institution=institution,
        document_number=f"{abs(hash(nombre + apellido)) % 10**8:08d}",
        first_name=nombre,
        last_name=apellido,
    )
    Enrollment.objects.create(
        student=student, school_year=school_year, group=group, status="ACTIVA"
    )
    return FinalReportCard.objects.create(
        student=student,
        school_year=school_year,
        group=group,
        period=period,
        average=4,
        snapshot={"areas": [{"area": "Matematicas", "subjects": [], "average": 4}]},
    )


class ImpresionDeBoletinesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.propia, cls.year, cls.group = build_institution("810000000001", "Propia", default=True)
        cls.ajena, cls.year_ajena, cls.group_ajena = build_institution("810000000002", "Ajena")

        cls.usuario = build_user("rector.propia@test.local", cls.propia, "RECTOR")
        cls.usuario_ajeno = build_user("rector.ajena@test.local", cls.ajena, "RECTOR")

        cls.cards = [
            build_card(cls.propia, cls.year, cls.group, nombre="Ana", apellido="Alvarez"),
            build_card(cls.propia, cls.year, cls.group, nombre="Bruno", apellido="Bermudez"),
            build_card(cls.propia, cls.year, cls.group, nombre="Carla", apellido="Cardona"),
        ]
        cls.card_ajena = build_card(
            cls.ajena, cls.year_ajena, cls.group_ajena, nombre="Diana", apellido="Duarte"
        )

    def _cliente(self, usuario):
        client = Client()
        client.force_login(usuario)
        return client

    def test_imprime_el_boletin_de_un_estudiante(self):
        respuesta = self._cliente(self.usuario).get(f"/promocion/boletin/{self.cards[0].pk}/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ALVAREZ")

    def test_imprime_el_grupo_completo_con_una_hoja_por_estudiante(self):
        respuesta = self._cliente(self.usuario).get(
            f"/promocion/boletines/imprimir/?group={self.group.pk}"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.content.decode().count('class="print-sheet"'), 3)

    def test_el_lote_sale_ordenado_por_apellido(self):
        contenido = self._cliente(self.usuario).get(
            f"/promocion/boletines/imprimir/?group={self.group.pk}"
        ).content.decode()

        self.assertLess(contenido.index("ALVAREZ"), contenido.index("BERMUDEZ"))
        self.assertLess(contenido.index("BERMUDEZ"), contenido.index("CARDONA"))

    def test_el_lote_avisa_cuando_no_hay_boletines_generados(self):
        FinalReportCard.objects.all().delete()

        respuesta = self._cliente(self.usuario).get(
            f"/promocion/boletines/imprimir/?group={self.group.pk}"
        )

        self.assertContains(respuesta, "No hay boletines generados")

    def test_no_se_imprime_el_boletin_de_otra_institucion(self):
        respuesta = self._cliente(self.usuario).get(f"/promocion/boletin/{self.card_ajena.pk}/")

        self.assertEqual(respuesta.status_code, 404)

    def test_el_lote_no_trae_boletines_de_otra_institucion(self):
        respuesta = self._cliente(self.usuario).get(
            f"/promocion/boletines/imprimir/?group={self.group_ajena.pk}"
        )

        self.assertNotContains(respuesta, "DUARTE")

    def test_sin_grupo_devuelve_al_listado_con_un_aviso(self):
        respuesta = self._cliente(self.usuario).get("/promocion/boletines/imprimir/")

        self.assertRedirects(respuesta, "/promocion/boletines/")
