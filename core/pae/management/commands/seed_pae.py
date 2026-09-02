"""
Configuracion base del modulo PAE:

    python manage.py seed_pae

Carga la normativa de referencia, los catalogos parametrizables, las
modalidades de atencion, los tipos de complemento, las listas de verificacion
y la vigencia del programa asociada al ano lectivo vigente.

Todo valor de origen normativo se registra con estado POR_VALIDAR cuando no
puede confirmarse contra el texto publicado: la operacion continua y el valor
se ajusta desde la interfaz, sin modificar el software.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

# ---------------------------------------------------------------------------
# Normativa de referencia
# ---------------------------------------------------------------------------
NORMATIVES = [
    {
        "code": "RES-0003-2026",
        "name": "Lineamientos tecnicos administrativos del Programa de Alimentacion Escolar",
        "issuer": "UApA - Alimentos para Aprender",
        "number": "0003",
        "issued_on": "2026-01-07",
        "effective_from": "2026-01-07",
        "status": "POR_VALIDAR",
        "summary": (
            "Resolucion de referencia para la operacion del PAE. Los valores numericos derivados "
            "de esta norma (aportes caloricos, umbrales y plazos) se administran como parametros."
        ),
        "notes": "Verificar el texto oficial publicado antes de dar por definitivos los parametros.",
    },
    {
        "code": "RES-0155-2026",
        "name": "Modificacion a los lineamientos tecnicos del Programa de Alimentacion Escolar",
        "issuer": "UApA - Alimentos para Aprender",
        "number": "0155",
        "issued_on": "2026-04-08",
        "effective_from": "2026-04-08",
        "status": "POR_VALIDAR",
        "summary": "Ajustes a los lineamientos vigentes del programa.",
        "notes": "Verificar el texto oficial publicado antes de dar por definitivos los parametros.",
    },
]

# ---------------------------------------------------------------------------
# Catalogos parametrizables (catalog_type, code, name, extras)
# ---------------------------------------------------------------------------
CATALOGS = {
    "CRITERIO_PRIORIZACION": [
        ("VICTIMA", "Poblacion victima del conflicto armado", {"weight": "30.00", "requires_evidence": True}),
        ("DISCAPACIDAD", "Estudiante con discapacidad", {"weight": "30.00", "requires_evidence": True}),
        ("ETNICO", "Poblacion indigena, ROM o afrodescendiente", {"weight": "25.00", "requires_evidence": True}),
        ("SISBEN", "Clasificacion Sisben de menor puntaje", {"weight": "25.00"}),
        ("RURAL", "Sede ubicada en zona rural", {"weight": "20.00"}),
        ("TRANSICION", "Estudiante de transicion y primaria", {"weight": "20.00"}),
        ("JORNADA_UNICA", "Sede con jornada unica", {"weight": "15.00"}),
        ("MIGRANTE", "Poblacion migrante", {"weight": "15.00", "requires_evidence": True}),
        ("DESPLAZADO", "Poblacion en situacion de desplazamiento", {"weight": "20.00", "requires_evidence": True}),
    ],
    "TIPO_POBLACION": [
        ("REGULAR", "Poblacion regular", {}),
        ("VICTIMA", "Victima del conflicto", {}),
        ("DISCAPACIDAD", "Con discapacidad", {}),
        ("INDIGENA", "Indigena", {}),
        ("AFRO", "Afrodescendiente", {}),
        ("ROM", "ROM / gitano", {}),
        ("MIGRANTE", "Migrante", {}),
        ("RURAL", "Rural disperso", {}),
    ],
    "TIPO_NOVEDAD": [
        ("NO_ENTREGA", "No entrega del complemento", {"requires_action": True, "requires_evidence": True}),
        ("ENTREGA_PARCIAL", "Entrega parcial de raciones", {"requires_action": True}),
        ("CALIDAD", "Calidad del alimento", {"requires_action": True, "requires_evidence": True}),
        ("INOCUIDAD", "Riesgo de inocuidad", {"requires_action": True, "requires_evidence": True}),
        ("GRAMAJE", "Gramaje inferior al establecido", {"requires_action": True}),
        ("TEMPERATURA", "Temperatura fuera de rango", {"requires_action": True}),
        ("MENU_DIFERENTE", "Menu diferente al programado", {"requires_action": True}),
        ("HORARIO", "Entrega fuera del horario", {}),
        ("INFRAESTRUCTURA", "Falla de infraestructura o dotacion", {"requires_action": True}),
        ("PERSONAL", "Novedad con el personal manipulador", {"requires_action": True}),
        ("TRANSPORTE", "Novedad en el transporte de alimentos", {}),
        ("OTRA", "Otra novedad", {}),
    ],
    "CAUSA_INCUMPLIMIENTO": [
        ("PROVEEDOR", "Incumplimiento del proveedor", {}),
        ("TRANSPORTE", "Retraso o falla del transporte", {}),
        ("INASISTENCIA", "Inasistencia de estudiantes", {}),
        ("CALAMIDAD", "Calamidad o fuerza mayor", {}),
        ("SUSPENSION", "Suspension de actividades academicas", {}),
        ("INFRAESTRUCTURA", "Falla de infraestructura", {}),
        ("OTRA", "Otra causa", {}),
    ],
    "TIPO_VISITA": [
        ("SEGUIMIENTO", "Visita de seguimiento", {}),
        ("SUPERVISION", "Visita de supervision", {}),
        ("CONTROL", "Visita de control social", {}),
        ("SORPRESA", "Visita sin previo aviso", {}),
        ("VERIFICACION", "Verificacion de plan de mejoramiento", {}),
    ],
    "TIPO_HALLAZGO": [
        ("CALIDAD", "Calidad e inocuidad", {"requires_action": True}),
        ("COBERTURA", "Cobertura y focalizacion", {"requires_action": True}),
        ("INFRAESTRUCTURA", "Infraestructura y dotacion", {"requires_action": True}),
        ("DOCUMENTAL", "Soporte documental", {}),
        ("CONTRACTUAL", "Cumplimiento contractual", {"requires_action": True}),
        ("PERSONAL", "Personal manipulador", {"requires_action": True}),
    ],
    "TIPO_PQRS": [
        ("PETICION", "Peticion", {"metadata": {"response_days": 15}}),
        ("QUEJA", "Queja", {"metadata": {"response_days": 15}}),
        ("RECLAMO", "Reclamo", {"metadata": {"response_days": 15}}),
        ("SUGERENCIA", "Sugerencia", {"metadata": {"response_days": 15}}),
        ("FELICITACION", "Felicitacion", {"metadata": {"response_days": 15}}),
        ("DENUNCIA", "Denuncia", {"metadata": {"response_days": 10}, "requires_evidence": True}),
    ],
    "TIPO_DOCUMENTO": [
        ("CONTRATO", "Contrato o convenio", {"requires_evidence": True}),
        ("ACTA", "Acta", {}),
        ("MINUTA", "Minuta patron y analisis de menu", {}),
        ("CERTIFICADO", "Certificado sanitario", {"requires_evidence": True}),
        ("MANIPULADOR", "Certificacion de manipulador de alimentos", {"requires_evidence": True}),
        ("INFORME", "Informe de supervision", {}),
        ("PLANILLA", "Planilla de entrega", {}),
        ("POLIZA", "Poliza", {"requires_evidence": True}),
        ("OTRO", "Otro documento", {}),
    ],
    "CATEGORIA_VERIFICACION": [
        ("INFRAESTRUCTURA", "Infraestructura y dotacion", {"order": 1}),
        ("MANIPULACION", "Manipulacion de alimentos", {"order": 2}),
        ("ALMACENAMIENTO", "Almacenamiento y conservacion", {"order": 3}),
        ("PREPARACION", "Preparacion y servido", {"order": 4}),
        ("DOCUMENTAL", "Soporte documental", {"order": 5}),
        ("PERSONAL", "Personal manipulador", {"order": 6}),
    ],
    "UNIDAD_MEDIDA": [
        ("G", "Gramo", {}),
        ("KG", "Kilogramo", {}),
        ("ML", "Mililitro", {}),
        ("L", "Litro", {}),
        ("UND", "Unidad", {}),
        ("PORCION", "Porcion", {}),
    ],
    "GRUPO_ALIMENTO": [
        ("CEREALES", "Cereales, raices, tuberculos y platanos", {"order": 1}),
        ("FRUTAS", "Frutas y verduras", {"order": 2}),
        ("LECHE", "Leche y productos lacteos", {"order": 3}),
        ("CARNES", "Carnes, huevos, leguminosas y frutos secos", {"order": 4}),
        ("GRASAS", "Grasas", {"order": 5}),
        ("AZUCARES", "Azucares", {"order": 6}),
    ],
    "TIPO_REUNION": [
        ("COMITE", "Comite de alimentacion escolar", {}),
        ("VEEDURIA", "Veeduria ciudadana", {}),
        ("PADRES", "Reunion con padres de familia", {}),
        ("MESA_PUBLICA", "Mesa publica", {}),
        ("SOCIALIZACION", "Socializacion del programa", {}),
    ],
}

# ---------------------------------------------------------------------------
# Modalidades y complementos
# ---------------------------------------------------------------------------
MODALITIES = [
    ("PREPARADA", "Comida preparada en sitio", True, True, False, 1),
    ("INDUSTRIALIZADA", "Racion industrializada", False, True, True, 2),
    ("RPC", "Racion para preparar en casa", False, False, False, 3),
]

# code, nombre, modalidad, kcal (POR VALIDAR), % requerimiento (POR VALIDAR), orden
COMPLEMENT_TYPES = [
    ("AM", "Complemento alimentario jornada manana", "PREPARADA", "0.00", "0.00", 1),
    ("PM", "Complemento alimentario jornada tarde", "PREPARADA", "0.00", "0.00", 2),
    ("ALMUERZO", "Almuerzo", "PREPARADA", "0.00", "0.00", 3),
    ("JU", "Complemento jornada unica", "PREPARADA", "0.00", "0.00", 4),
    ("RPC", "Racion para preparar en casa", "RPC", "0.00", "0.00", 5),
    ("RI", "Racion industrializada", "INDUSTRIALIZADA", "0.00", "0.00", 6),
]

# ---------------------------------------------------------------------------
# Listas de verificacion
# ---------------------------------------------------------------------------
CHECKLISTS = [
    {
        "code": "LV-CALIDAD",
        "name": "Lista de verificacion de calidad e inocuidad",
        "scope": "CALIDAD",
        "description": "Verificacion en sitio de las condiciones de calidad e inocuidad del servicio.",
        "items": [
            ("INFRAESTRUCTURA", "La zona de preparacion se encuentra limpia y ordenada", "3.00", False, False),
            ("INFRAESTRUCTURA", "El comedor cuenta con mobiliario suficiente y en buen estado", "2.00", False, False),
            ("INFRAESTRUCTURA", "Existe suministro de agua potable", "4.00", True, True),
            ("MANIPULACION", "El personal usa dotacion completa (gorro, tapabocas, delantal)", "3.00", True, True),
            ("MANIPULACION", "Se realiza lavado de manos con la tecnica establecida", "3.00", True, False),
            ("MANIPULACION", "No se manipulan alimentos con joyas o esmalte", "2.00", False, False),
            ("ALMACENAMIENTO", "Los alimentos se almacenan separados del piso y la pared", "3.00", False, False),
            ("ALMACENAMIENTO", "Se controla y registra la temperatura de refrigeracion", "4.00", True, True),
            ("ALMACENAMIENTO", "Ningun alimento presenta fecha de vencimiento superada", "4.00", True, True),
            ("PREPARACION", "El menu servido corresponde al menu programado", "3.00", False, True),
            ("PREPARACION", "El gramaje servido corresponde al establecido", "3.00", True, True),
            ("PREPARACION", "Se conserva contramuestra del servicio del dia", "2.00", False, True),
            ("DOCUMENTAL", "La planilla de entrega esta diligenciada y firmada", "2.00", False, True),
            ("DOCUMENTAL", "Se exhibe la minuta patron vigente", "1.00", False, False),
            ("PERSONAL", "El personal cuenta con certificado de manipulacion vigente", "4.00", True, True),
            ("PERSONAL", "Se cuenta con los examenes medicos ocupacionales al dia", "3.00", True, True),
        ],
    },
    {
        "code": "LV-VISITA",
        "name": "Lista de verificacion de visita de seguimiento",
        "scope": "VISITA",
        "description": "Verificacion aplicada durante las visitas de seguimiento y supervision.",
        "items": [
            ("DOCUMENTAL", "Los soportes contractuales estan disponibles en la sede", "2.00", False, False),
            ("DOCUMENTAL", "El listado de beneficiarios coincide con el reportado", "3.00", True, True),
            ("PREPARACION", "El servicio se presta en el horario establecido", "2.00", False, False),
            ("INFRAESTRUCTURA", "Las condiciones locativas permiten la prestacion del servicio", "3.00", False, False),
            ("PERSONAL", "El numero de manipuladoras corresponde al contratado", "2.00", False, False),
        ],
    },
    {
        "code": "LV-DIAGNOSTICO",
        "name": "Lista de diagnostico de sede",
        "scope": "DIAGNOSTICO",
        "description": "Diagnostico inicial de las condiciones de la sede para operar el programa.",
        "items": [
            ("INFRAESTRUCTURA", "La sede cuenta con cocina en condiciones de uso", "3.00", False, False),
            ("INFRAESTRUCTURA", "La sede cuenta con comedor o espacio de consumo", "3.00", False, False),
            ("INFRAESTRUCTURA", "La sede cuenta con bodega de almacenamiento", "2.00", False, False),
            ("INFRAESTRUCTURA", "La sede cuenta con servicio de energia electrica", "3.00", True, False),
            ("INFRAESTRUCTURA", "La sede cuenta con unidades sanitarias en funcionamiento", "3.00", True, False),
        ],
    },
]


class Command(BaseCommand):
    help = "Carga la configuracion base del modulo PAE (normativa, catalogos, modalidades y listas)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-vigencia",
            action="store_true",
            help="No crea la vigencia PAE asociada al ano lectivo vigente.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from core.institutions.models import Institution

        institution = Institution.current()
        if institution is None:
            self.stdout.write(self.style.ERROR(
                "No hay institucion configurada. Ejecute primero initialize_platform."
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("PL_SGE - Configuracion base del PAE"))

        normatives = self._normatives()
        current_normative = normatives.get("RES-0155-2026") or normatives.get("RES-0003-2026")
        self._catalogs(current_normative)
        modalities = self._modalities(institution, current_normative)
        self._complement_types(institution, modalities, current_normative)
        self._checklists(current_normative)
        if not options["sin_vigencia"]:
            self._vigencia(institution, current_normative)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Configuracion base del PAE cargada correctamente."))
        self.stdout.write(self.style.WARNING(
            "Los parametros de origen normativo quedan en estado POR_VALIDAR: "
            "ajustelos desde Configuracion del PAE cuando confirme el texto oficial."
        ))

    # ------------------------------------------------------------------
    def _normatives(self):
        from ...models import PaeNormative

        created = {}
        for entry in NORMATIVES:
            data = dict(entry)
            code = data.pop("code")
            normative, _ = PaeNormative.objects.update_or_create(code=code, defaults=data)
            created[code] = normative
        self.stdout.write(f"  Normativa registrada: {len(created)}")
        return created

    def _catalogs(self, normative):
        from ...models import PaeCatalog

        total = 0
        for catalog_type, entries in CATALOGS.items():
            for index, (code, name, extras) in enumerate(entries, start=1):
                defaults = {
                    "name": name,
                    "order": extras.get("order", index),
                    "weight": Decimal(extras.get("weight", "0.00")),
                    "requires_evidence": extras.get("requires_evidence", False),
                    "requires_action": extras.get("requires_action", False),
                    "metadata": extras.get("metadata", {}),
                    "validation_status": "POR_VALIDAR",
                    "normative": normative,
                    "is_active": True,
                }
                PaeCatalog.objects.update_or_create(
                    catalog_type=catalog_type, code=code, defaults=defaults
                )
                total += 1
        self.stdout.write(f"  Elementos de catalogo: {total} en {len(CATALOGS)} catalogos")

    def _modalities(self, institution, normative):
        from ...models import PaeModality

        result = {}
        for code, name, kitchen, dining, cold, order in MODALITIES:
            modality, _ = PaeModality.objects.update_or_create(
                institution=institution,
                code=code,
                defaults={
                    "name": name,
                    "requires_kitchen": kitchen,
                    "requires_dining_room": dining,
                    "requires_cold_chain": cold,
                    "order": order,
                    "normative": normative,
                    "is_active": True,
                },
            )
            result[code] = modality
        self.stdout.write(f"  Modalidades de atencion: {len(result)}")
        return result

    def _complement_types(self, institution, modalities, normative):
        from ...models import PaeComplementType

        total = 0
        for code, name, modality_code, calories, percentage, order in COMPLEMENT_TYPES:
            PaeComplementType.objects.update_or_create(
                institution=institution,
                code=code,
                defaults={
                    "name": name,
                    "modality": modalities.get(modality_code),
                    "calorie_contribution": Decimal(calories),
                    "energy_percentage": Decimal(percentage),
                    "order": order,
                    "normative": normative,
                    "description": "Aporte nutricional parametrizable. POR VALIDAR contra la norma vigente.",
                    "is_active": True,
                },
            )
            total += 1
        self.stdout.write(f"  Tipos de complemento: {total} (aportes en POR VALIDAR)")

    def _checklists(self, normative):
        from ...models import PaeCatalog, PaeChecklist, PaeChecklistItem

        categories = {
            row.code: row
            for row in PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_CHECK_CATEGORY)
        }

        total_items = 0
        for entry in CHECKLISTS:
            checklist, _ = PaeChecklist.objects.update_or_create(
                code=entry["code"],
                defaults={
                    "name": entry["name"],
                    "scope": entry["scope"],
                    "description": entry["description"],
                    "normative": normative,
                    "is_active": True,
                },
            )
            for order, (category_code, criterion, weight, critical, evidence) in enumerate(entry["items"], start=1):
                PaeChecklistItem.objects.update_or_create(
                    checklist=checklist,
                    criterion=criterion,
                    defaults={
                        "category": categories.get(category_code),
                        "code": f"{entry['code']}-{order:02d}",
                        "weight": Decimal(weight),
                        "is_critical": critical,
                        "requires_evidence": evidence,
                        "order": order,
                        "is_active": True,
                    },
                )
                total_items += 1
        self.stdout.write(f"  Listas de verificacion: {len(CHECKLISTS)} con {total_items} criterios")

    def _vigencia(self, institution, normative):
        from core.academic.models import SchoolYear

        from ...models import PaeVigencia

        year = SchoolYear.current()
        if year is None:
            self.stdout.write(self.style.WARNING(
                "  No hay ano lectivo vigente: la vigencia PAE no se creo."
            ))
            return

        vigencia, created = PaeVigencia.objects.update_or_create(
            institution=institution,
            school_year=year,
            defaults={
                "name": f"PAE {year.year}",
                "normative": normative,
                "start_date": year.start_date,
                "end_date": year.end_date,
                "status": "ACTIVA",
                "is_current": True,
            },
        )
        estado = "creada" if created else "actualizada"
        self.stdout.write(f"  Vigencia PAE {estado}: {vigencia.name}")
