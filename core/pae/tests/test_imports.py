"""
Pruebas de la importacion masiva del PAE.

Verifica el reporte de errores por fila y columna, la ausencia de duplicados,
la validacion del archivo cargado y que una fila invalida impida guardar todo.
"""
from __future__ import annotations

import datetime as dt
import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from ..imports import run_import
from .factories import (
    build_menu_cycle,
    build_pae,
    build_plan,
    build_platform,
    build_student,
    build_user,
    seed_modules,
)


def csv_file(rows, name="datos.csv"):
    content = "\n".join(";".join(str(cell) for cell in row) for row in rows)
    return SimpleUploadedFile(name, content.encode("utf-8-sig"), content_type="text/csv")


class BeneficiaryImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.student, cls.enrollment = build_student(cls.platform, document="7000000001")
        cls.otro, _ = build_student(cls.platform, document="7000000002")

    def _import(self, rows, dry_run=False):
        header = ["documento", "modalidad", "complemento", "fecha_inicio", "estado"]
        return run_import(
            "beneficiarios", csv_file([header] + rows), self.pae["vigencia"], dry_run=dry_run
        )

    def test_importa_los_beneficiarios(self):
        from ..models import PaeBeneficiary

        result = self._import([
            ["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
            ["7000000002", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
        ])
        self.assertFalse(result.has_errors)
        self.assertEqual(result.created, 2)
        self.assertEqual(PaeBeneficiary.objects.count(), 2)

    def test_la_segunda_importacion_actualiza_y_no_duplica(self):
        from ..models import PaeBeneficiary

        rows = [["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"]]
        self._import(rows)
        result = self._import(rows)
        self.assertEqual(result.created, 0)
        self.assertEqual(result.updated, 1)
        self.assertEqual(PaeBeneficiary.objects.count(), 1)

    def test_el_documento_repetido_en_el_archivo_se_reporta(self):
        result = self._import([
            ["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
            ["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
        ])
        self.assertTrue(result.has_errors)
        error = result.errors[0]
        self.assertEqual(error.row, 3)
        self.assertEqual(error.column, "documento")
        self.assertIn("se repite", error.message)

    def test_el_estudiante_inexistente_se_reporta_con_su_fila(self):
        result = self._import([["9999999999", "PREPARADA", "AM", "2026-02-01", "ACTIVO"]])
        self.assertTrue(result.has_errors)
        self.assertEqual(result.errors[0].row, 2)
        self.assertIn("no existe en el modulo de Estudiantes", result.errors[0].message)

    def test_una_fila_invalida_impide_guardar_todo_el_archivo(self):
        from ..models import PaeBeneficiary

        result = self._import([
            ["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
            ["9999999999", "PREPARADA", "AM", "2026-02-01", "ACTIVO"],
        ])
        self.assertTrue(result.has_errors)
        self.assertEqual(result.created, 0)
        self.assertEqual(PaeBeneficiary.objects.count(), 0)

    def test_modalidad_desconocida(self):
        result = self._import([["7000000001", "INVENTADA", "AM", "2026-02-01", "ACTIVO"]])
        self.assertEqual(result.errors[0].column, "modalidad")

    def test_estado_no_valido(self):
        result = self._import([["7000000001", "PREPARADA", "AM", "2026-02-01", "PENDIENTE"]])
        self.assertEqual(result.errors[0].column, "estado")

    def test_fecha_no_valida(self):
        result = self._import([["7000000001", "PREPARADA", "AM", "31/31/2026", "ACTIVO"]])
        self.assertEqual(result.errors[0].column, "fecha_inicio")

    def test_falta_una_columna_obligatoria(self):
        result = run_import(
            "beneficiarios",
            csv_file([["modalidad", "estado"], ["PREPARADA", "ACTIVO"]]),
            self.pae["vigencia"],
        )
        self.assertTrue(result.has_errors)
        self.assertEqual(result.errors[0].row, 1)
        self.assertEqual(result.errors[0].column, "documento")

    def test_solo_validar_no_guarda_nada(self):
        from ..models import PaeBeneficiary

        result = self._import([["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"]], dry_run=True)
        self.assertFalse(result.has_errors)
        self.assertTrue(result.dry_run)
        self.assertEqual(PaeBeneficiary.objects.count(), 0)

    def test_los_encabezados_se_normalizan(self):
        header = ["Documento", "Modalidad", "Complemento", "Fecha de Inicio", "Estado"]
        result = run_import(
            "beneficiarios",
            csv_file([header, ["7000000001", "PREPARADA", "AM", "2026-02-01", "ACTIVO"]]),
            self.pae["vigencia"],
        )
        # "Fecha de Inicio" -> fecha_de_inicio, que no es la columna esperada:
        # el documento si se reconoce y la importacion usa la fecha por defecto.
        self.assertFalse(result.has_errors)
        self.assertEqual(result.created, 1)

    def test_archivo_vacio(self):
        result = run_import("beneficiarios", csv_file([["documento"]]), self.pae["vigencia"])
        self.assertTrue(result.has_errors)
        self.assertEqual(result.errors[0].column, "archivo")


class ScheduleImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.cycle = build_menu_cycle(cls.pae, days=2)
        cls.plan = build_plan(cls.platform, cls.pae, status="APROBADO")
        cls.plan.menu_cycle = cls.cycle
        cls.plan.save(update_fields=["menu_cycle"])
        cls.fecha = (cls.pae["vigencia"].start_date + dt.timedelta(days=5)).isoformat()

    def _import(self, rows):
        header = ["plan", "fecha", "sede", "complemento", "dia_menu", "beneficiarios", "raciones"]
        return run_import("programacion", csv_file([header] + rows), self.pae["vigencia"])

    def test_importa_la_programacion(self):
        from ..models import PaeSchedule

        result = self._import([[self.plan.code, self.fecha, "PRINCIPAL", "AM", "1", "50", "50"]])
        self.assertFalse(result.has_errors)
        self.assertEqual(PaeSchedule.objects.count(), 1)

    def test_no_duplica_la_misma_fecha(self):
        from ..models import PaeSchedule

        rows = [[self.plan.code, self.fecha, "PRINCIPAL", "AM", "1", "50", "50"]]
        self._import(rows)
        result = self._import(rows)
        self.assertEqual(result.updated, 1)
        self.assertEqual(PaeSchedule.objects.count(), 1)

    def test_la_fecha_repetida_dentro_del_archivo_se_reporta(self):
        row = [self.plan.code, self.fecha, "PRINCIPAL", "AM", "1", "50", "50"]
        result = self._import([row, list(row)])
        self.assertTrue(result.has_errors)
        self.assertIn("se repite", result.errors[0].message)

    def test_plan_inexistente(self):
        result = self._import([["PAE-NO-EXISTE", self.fecha, "PRINCIPAL", "AM", "1", "50", "50"]])
        self.assertEqual(result.errors[0].column, "plan")

    def test_fecha_fuera_del_periodo_del_plan(self):
        fuera = (self.pae["vigencia"].end_date + dt.timedelta(days=30)).isoformat()
        result = self._import([[self.plan.code, fuera, "PRINCIPAL", "AM", "1", "50", "50"]])
        self.assertEqual(result.errors[0].column, "fecha")

    def test_dia_de_menu_inexistente(self):
        result = self._import([[self.plan.code, self.fecha, "PRINCIPAL", "AM", "9", "50", "50"]])
        self.assertEqual(result.errors[0].column, "dia_menu")

    def test_no_se_programa_sobre_un_plan_en_borrador(self):
        self.plan.status = "BORRADOR"
        self.plan.save(update_fields=["status"])
        result = self._import([[self.plan.code, self.fecha, "PRINCIPAL", "AM", "1", "50", "50"]])
        self.assertEqual(result.errors[0].column, "plan")
        self.plan.status = "APROBADO"
        self.plan.save(update_fields=["status"])


class MenuImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.cycle = build_menu_cycle(cls.pae, days=1)

    def _import(self, rows):
        header = ["ciclo", "dia", "nombre_dia", "preparacion", "componente",
                  "porcion", "calorias", "proteina", "ingrediente", "cantidad", "unidad"]
        return run_import("menus", csv_file([header] + rows), self.pae["vigencia"])

    def test_importa_dias_preparaciones_e_ingredientes(self):
        from ..models import PaeMenuDay, PaeMenuIngredient, PaeMenuPreparation

        result = self._import([
            ["CM-TEST", "2", "Menu dia 2", "Arepa con queso", "CEREAL", "1 und", "250", "9", "Arepa", "70", "g"],
            ["CM-TEST", "2", "Menu dia 2", "Arepa con queso", "CEREAL", "1 und", "250", "9", "Queso", "30", "g"],
        ])
        self.assertFalse(result.has_errors)
        self.assertEqual(PaeMenuDay.objects.filter(cycle=self.cycle, day_number=2).count(), 1)
        day = PaeMenuDay.objects.get(cycle=self.cycle, day_number=2)
        self.assertEqual(PaeMenuPreparation.objects.filter(day=day).count(), 1)
        self.assertEqual(
            PaeMenuIngredient.objects.filter(preparation__day=day).count(), 2
        )

    def test_ciclo_inexistente(self):
        result = self._import([["CM-NO", "1", "x", "y", "CEREAL", "", "", "", "", "", ""]])
        self.assertEqual(result.errors[0].column, "ciclo")

    def test_componente_no_valido(self):
        result = self._import([["CM-TEST", "2", "x", "y", "INVENTADO", "", "", "", "", "", ""]])
        self.assertEqual(result.errors[0].column, "componente")

    def test_ciclo_archivado_se_rechaza(self):
        self.cycle.status = "ARCHIVADO"
        self.cycle.save(update_fields=["status"])
        result = self._import([["CM-TEST", "2", "x", "y", "CEREAL", "", "", "", "", "", ""]])
        self.assertEqual(result.errors[0].column, "ciclo")
        self.cycle.status = "VIGENTE"
        self.cycle.save(update_fields=["status"])


class FileValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)

    def test_extension_no_permitida(self):
        archivo = SimpleUploadedFile("datos.exe", b"contenido", content_type="application/octet-stream")
        with self.assertRaises(ValidationError) as ctx:
            run_import("beneficiarios", archivo, self.pae["vigencia"])
        self.assertIn("Extension no permitida", str(ctx.exception))

    def test_archivo_vacio(self):
        archivo = SimpleUploadedFile("datos.csv", b"", content_type="text/csv")
        with self.assertRaises(ValidationError) as ctx:
            run_import("beneficiarios", archivo, self.pae["vigencia"])
        self.assertIn("vacio", str(ctx.exception))

    def test_archivo_demasiado_grande(self):
        from config.imports import MAX_IMPORT_BYTES

        contenido = b"a" * (MAX_IMPORT_BYTES + 1)
        archivo = SimpleUploadedFile("datos.csv", contenido, content_type="text/csv")
        with self.assertRaises(ValidationError) as ctx:
            run_import("beneficiarios", archivo, self.pae["vigencia"])
        self.assertIn("supera el limite", str(ctx.exception))

    def test_tipo_de_importacion_no_reconocido(self):
        with self.assertRaises(ValidationError):
            run_import("inventado", csv_file([["a"], ["b"]]), self.pae["vigencia"])

    def test_sin_vigencia_no_se_importa(self):
        with self.assertRaises(ValidationError):
            run_import("beneficiarios", csv_file([["documento"], ["1"]]), None)

    def test_el_documento_adjunto_valida_extension(self):
        from ..serializers import PaeEvidenceSerializer

        serializer = PaeEvidenceSerializer(data={
            "module": "ENTREGAS",
            "name": "Evidencia",
            "file": SimpleUploadedFile("virus.exe", b"x" * 10, content_type="application/octet-stream"),
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)


class ImportApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.platform = build_platform()
        cls.pae = build_pae(cls.platform)
        cls.student, cls.enrollment = build_student(cls.platform, document="8000000001")
        institution = cls.platform["institution"]
        cls.responsable = build_user("import@test.local", "RESPONSABLE_PAE", institution)
        cls.consulta = build_user("consulta.import@test.local", "CONSULTA_PAE", institution)

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_listado_de_plantillas(self):
        response = self.api(self.responsable).get("/api/pae/importar/")
        self.assertEqual(response.status_code, 200)
        kinds = {row["kind"] for row in response.json()["results"]}
        self.assertEqual(kinds, {"beneficiarios", "estudiantes", "programacion", "menus"})

    def test_descarga_de_la_plantilla(self):
        response = self.api(self.responsable).get(
            "/api/pae/importar/", {"kind": "beneficiarios", "download": "1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("csv", response["Content-Type"])
        self.assertIn(b"documento", response.content)

    def test_importacion_por_la_api(self):
        archivo = csv_file([
            ["documento", "estado"],
            ["8000000001", "ACTIVO"],
        ])
        response = self.api(self.responsable).post(
            "/api/pae/importar/", {"kind": "beneficiarios", "file": archivo}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 1)

    def test_los_errores_llegan_con_fila_y_columna(self):
        archivo = csv_file([["documento", "estado"], ["0000000000", "ACTIVO"]])
        response = self.api(self.responsable).post(
            "/api/pae/importar/", {"kind": "beneficiarios", "file": archivo}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        error = response.json()["errors"][0]
        self.assertEqual(error["fila"], 2)
        self.assertEqual(error["columna"], "documento")

    def test_el_perfil_de_consulta_no_puede_importar(self):
        archivo = csv_file([["documento", "estado"], ["8000000001", "ACTIVO"]])
        response = self.api(self.consulta).post(
            "/api/pae/importar/", {"kind": "beneficiarios", "file": archivo}, format="multipart"
        )
        self.assertEqual(response.status_code, 403)

    def test_la_importacion_queda_en_la_bitacora(self):
        from core.audit.models import AuditLog

        archivo = csv_file([["documento", "estado"], ["8000000001", "ACTIVO"]])
        self.api(self.responsable).post(
            "/api/pae/importar/", {"kind": "beneficiarios", "file": archivo}, format="multipart"
        )
        self.assertTrue(
            AuditLog.objects.filter(module="pae.beneficiarios", action="PROCESS").exists()
        )

    def test_importacion_de_menus_exige_permiso_del_modulo_de_menus(self):
        archivo = csv_file([["ciclo", "dia", "preparacion"], ["CM-X", "1", "P"]])
        response = self.api(self.consulta).post(
            "/api/pae/importar/", {"kind": "menus", "file": archivo}, format="multipart"
        )
        self.assertEqual(response.status_code, 403)
