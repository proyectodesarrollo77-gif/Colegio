"""
Datos de demostracion del modulo PAE:

    python manage.py seed_pae_demo

Requiere `initialize_platform`, `seed_demo` y `seed_pae`. Los beneficiarios se
toman de los estudiantes ya matriculados (modulo de Estudiantes): el PAE no
crea ni duplica informacion de estudiantes.

Toda la informacion es ficticia: operadores, contratos, personas y radicados
son inventados y no corresponden a organizaciones ni a personas reales.
"""
from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# --- Sedes de demostracion (ficticias) --------------------------------------
DEMO_CAMPUSES = [
    ("SEDE-B", "Sede B - Demostracion", "Calle 45 No. 12 - 30", "URBANA"),
    ("SEDE-C", "Sede C - Demostracion Rural", "Vereda La Esperanza km 4", "RURAL"),
]

# --- Ciclo de menu de demostracion ------------------------------------------
MENU_DAYS = [
    (1, "Menu dia 1", [
        ("Bebida lactea con avena", "BEBIDA", "200 ml", "180.00", "7.50",
         [("Leche entera", "LECHE", "200.000", "ml"), ("Avena en hojuelas", "CEREALES", "20.000", "g"),
          ("Azucar", "AZUCARES", "10.000", "g")]),
        ("Pan integral con queso", "CEREAL", "1 unidad", "230.00", "9.00",
         [("Pan integral", "CEREALES", "60.000", "g"), ("Queso campesino", "LECHE", "30.000", "g")]),
        ("Banano", "FRUTA", "1 unidad", "90.00", "1.20",
         [("Banano", "FRUTAS", "120.000", "g")]),
    ]),
    (2, "Menu dia 2", [
        ("Chocolate en leche", "BEBIDA", "200 ml", "190.00", "7.00",
         [("Leche entera", "LECHE", "200.000", "ml"), ("Chocolate", "AZUCARES", "15.000", "g")]),
        ("Arepa con huevo", "PROTEICO", "1 unidad", "260.00", "12.00",
         [("Arepa de maiz", "CEREALES", "70.000", "g"), ("Huevo", "CARNES", "50.000", "g")]),
        ("Mandarina", "FRUTA", "1 unidad", "70.00", "0.90",
         [("Mandarina", "FRUTAS", "110.000", "g")]),
    ]),
    (3, "Menu dia 3", [
        ("Jugo de guayaba en agua", "BEBIDA", "200 ml", "110.00", "1.00",
         [("Pulpa de guayaba", "FRUTAS", "80.000", "g"), ("Azucar", "AZUCARES", "12.000", "g")]),
        ("Sandwich de pollo", "PROTEICO", "1 unidad", "290.00", "16.00",
         [("Pan tajado", "CEREALES", "60.000", "g"), ("Pollo desmechado", "CARNES", "45.000", "g"),
          ("Lechuga", "FRUTAS", "15.000", "g")]),
        ("Manzana", "FRUTA", "1 unidad", "80.00", "0.50",
         [("Manzana", "FRUTAS", "130.000", "g")]),
    ]),
    (4, "Menu dia 4", [
        ("Bebida de kumis", "LACTEO", "200 ml", "170.00", "8.00",
         [("Kumis", "LECHE", "200.000", "ml")]),
        ("Galleta integral con bocadillo", "CEREAL", "2 unidades", "220.00", "4.00",
         [("Galleta integral", "CEREALES", "50.000", "g"), ("Bocadillo", "AZUCARES", "20.000", "g")]),
        ("Papaya en trozos", "FRUTA", "1 porcion", "60.00", "0.80",
         [("Papaya", "FRUTAS", "120.000", "g")]),
    ]),
    (5, "Menu dia 5", [
        ("Avena en leche", "BEBIDA", "200 ml", "185.00", "7.20",
         [("Leche entera", "LECHE", "200.000", "ml"), ("Avena molida", "CEREALES", "22.000", "g")]),
        ("Envuelto de maiz con queso", "CEREAL", "1 unidad", "250.00", "8.50",
         [("Masa de maiz", "CEREALES", "80.000", "g"), ("Queso campesino", "LECHE", "25.000", "g")]),
        ("Pera", "FRUTA", "1 unidad", "85.00", "0.60",
         [("Pera", "FRUTAS", "130.000", "g")]),
    ]),
]

# --- Textos ficticios --------------------------------------------------------
INCIDENT_TEXTS = [
    "Se recibieron menos raciones de las programadas para la jornada.",
    "El complemento llego 40 minutos despues del horario acordado.",
    "El menu entregado no correspondio al menu programado del ciclo.",
    "Se detecto temperatura de refrigeracion por encima del rango establecido.",
    "El gramaje de la porcion proteica resulto inferior al establecido.",
    "Una manipuladora no contaba con la dotacion completa durante el servicio.",
]

FINDING_TEXTS = [
    "La bodega de almacenamiento no tiene estibas suficientes.",
    "El registro de temperaturas presenta dias sin diligenciar.",
    "El listado de beneficiarios de la sede no esta actualizado.",
    "Falta senalizacion de las areas de preparacion.",
]

PQRS_TEXTS = [
    ("QUEJA", "El complemento del dia llego incompleto para el grupo de la manana."),
    ("PETICION", "Se solicita ampliar la cobertura del programa al grado once."),
    ("SUGERENCIA", "Se sugiere incluir mas fruta fresca en el ciclo de menu."),
    ("RECLAMO", "El estudiante con dieta especial no recibio su racion adaptada."),
    ("FELICITACION", "Se reconoce la puntualidad del servicio durante el mes."),
]

DOCUMENTS = [
    ("CONTRATO", "CONTRATOS", "Contrato de operacion PAE (demostracion)", 300),
    ("MINUTA", "MENUS", "Minuta patron del ciclo de menu (demostracion)", 200),
    ("CERTIFICADO", "OPERADORES", "Concepto sanitario del operador (demostracion)", 20),
    ("MANIPULADOR", "OPERADORES", "Certificados de manipulacion de alimentos (demostracion)", 45),
    ("ACTA", "PARTICIPACION", "Acta de comite de alimentacion escolar (demostracion)", None),
    ("INFORME", "VISITAS", "Informe de supervision del periodo (demostracion)", None),
]


class Command(BaseCommand):
    help = "Carga datos de demostracion ficticios del modulo PAE"

    def add_arguments(self, parser):
        parser.add_argument("--beneficiarios", type=int, default=350)
        parser.add_argument("--dias", type=int, default=40, help="Dias habiles de operacion a simular")
        parser.add_argument("--seed", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **options):
        from core.institutions.models import Institution

        from ...models import PaeVigencia

        random.seed(options["seed"])

        institution = Institution.current()
        if institution is None:
            self.stdout.write(self.style.ERROR("No hay institucion. Ejecute initialize_platform."))
            return

        vigencia = PaeVigencia.current()
        if vigencia is None:
            self.stdout.write(self.style.ERROR("No hay vigencia PAE. Ejecute seed_pae."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("PL_SGE - Datos de demostracion del PAE"))
        self.stdout.write(self.style.WARNING(
            "  Informacion ficticia: operadores, contratos y personas son inventados."
        ))

        campuses = self._campuses(institution)
        self._diagnoses(vigencia, campuses)
        prioritizations = self._prioritizations(vigencia, campuses)
        beneficiaries = self._beneficiaries(vigencia, prioritizations, options["beneficiarios"])
        operator = self._operator(institution)
        contract = self._contract(vigencia, operator, campuses)
        cycle = self._menu_cycle(vigencia)
        plans = self._plans(vigencia, institution, campuses, operator, contract, cycle, beneficiaries)
        schedules = self._schedules(plans, cycle, options["dias"])
        deliveries = self._deliveries(schedules)
        incidents = self._incidents(vigencia, deliveries, operator)
        visits = self._visits(vigencia, campuses, operator)
        findings = self._findings(visits)
        self._improvement_actions(vigencia, findings, incidents)
        self._pqrs(vigencia, campuses)
        self._participation(vigencia, campuses)
        self._documents(vigencia, operator, contract)
        self._indicators(vigencia)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de demostracion del PAE cargados correctamente."))

    # ------------------------------------------------------------------
    def _campuses(self, institution):
        from core.institutions.models import Campus

        for code, name, address, _zone in DEMO_CAMPUSES:
            Campus.objects.get_or_create(
                institution=institution,
                code=code,
                defaults={"name": name, "address": address, "phone": "6015550000"},
            )
        campuses = list(Campus.objects.filter(institution=institution, deleted_at__isnull=True).order_by("-is_main", "code"))
        self.stdout.write(f"  Sedes disponibles: {len(campuses)}")
        return campuses

    def _diagnoses(self, vigencia, campuses):
        from ...models import PaeSiteDiagnosis

        conditions = ["OPTIMA", "ACEPTABLE", "DEFICIENTE"]
        created = 0
        for index, campus in enumerate(campuses):
            zone = "RURAL" if "RURAL" in campus.code.upper() or "Rural" in campus.name else "URBANA"
            diagnosis, was_created = PaeSiteDiagnosis.objects.get_or_create(
                vigencia=vigencia,
                campus=campus,
                defaults={
                    "zone": zone,
                    "infrastructure": conditions[index % len(conditions)],
                    "kitchen": conditions[(index + 1) % len(conditions)],
                    "dining_room": conditions[index % len(conditions)],
                    "storage": conditions[(index + 2) % len(conditions)],
                    "refrigeration": conditions[(index + 1) % len(conditions)],
                    "water": "OPTIMA",
                    "energy": "OPTIMA",
                    "gas": conditions[index % len(conditions)],
                    "equipment": conditions[(index + 1) % len(conditions)],
                    "sanitary": conditions[index % len(conditions)],
                    "accessibility": "ACEPTABLE",
                    "dining_capacity": random.randint(60, 220),
                    "kitchen_area_m2": Decimal(random.randint(18, 60)),
                    "storage_area_m2": Decimal(random.randint(8, 30)),
                    "max_rations": random.randint(150, 400),
                    "food_handlers": random.randint(2, 6),
                    "observations": "Diagnostico de demostracion.",
                },
            )
            if was_created:
                created += 1
            diagnosis.save()  # recalcula el puntaje
        self.stdout.write(f"  Diagnosticos de sede: {created} nuevos")

    def _prioritizations(self, vigencia, campuses):
        from core.students.models import Enrollment

        from ...models import PaeCatalog, PaePrioritization

        criteria = list(PaeCatalog.objects.filter(
            catalog_type=PaeCatalog.TYPE_CRITERION, code__in=["TRANSICION", "SISBEN", "RURAL"]
        ))
        population = PaeCatalog.objects.filter(
            catalog_type=PaeCatalog.TYPE_POPULATION, code="REGULAR"
        ).first()
        enrolled = Enrollment.objects.filter(
            school_year=vigencia.school_year, status="ACTIVA", deleted_at__isnull=True
        ).count()

        result = []
        for campus in campuses:
            prioritization, _ = PaePrioritization.objects.get_or_create(
                vigencia=vigencia,
                campus=campus,
                grade=None,
                group=None,
                defaults={
                    "population_type": population,
                    "enrolled_students": enrolled,
                    "prioritized_students": 0,
                    "score": Decimal("75.00"),
                    "justification": "Focalizacion de demostracion por sede.",
                    "status": "APROBADA",
                },
            )
            if criteria:
                prioritization.criteria.set(criteria)
            result.append(prioritization)
        self.stdout.write(f"  Priorizaciones: {len(result)}")
        return result

    def _beneficiaries(self, vigencia, prioritizations, target):
        from core.students.models import Enrollment

        from ...models import PaeBeneficiary, PaeComplementType, PaeModality

        # Orden estable para que ejecuciones sucesivas tomen el mismo conjunto
        # y el total no crezca por encima del objetivo.
        enrollments = list(
            Enrollment.objects.filter(
                school_year=vigencia.school_year, status="ACTIVA", deleted_at__isnull=True
            ).select_related("student", "group", "group__grade").order_by("student_id")[: target]
        )
        if not enrollments:
            self.stdout.write(self.style.WARNING(
                "  No hay matriculas activas: ejecute seed_demo antes de cargar beneficiarios."
            ))
            return []

        modality = PaeModality.objects.filter(code="PREPARADA").first()
        complements = list(PaeComplementType.objects.filter(code__in=["AM", "PM", "JU"]))
        prioritization = prioritizations[0] if prioritizations else None

        created = 0
        for index, enrollment in enumerate(enrollments):
            _, was_created = PaeBeneficiary.objects.get_or_create(
                vigencia=vigencia,
                student=enrollment.student,
                defaults={
                    "enrollment": enrollment,
                    "group": enrollment.group,
                    "grade": enrollment.group.grade if enrollment.group_id else None,
                    "modality": modality,
                    "complement_type": complements[index % len(complements)] if complements else None,
                    "prioritization": prioritization,
                    "start_date": vigencia.start_date,
                    "status": "ACTIVO",
                    "has_special_diet": index % 60 == 0,
                    "special_diet_detail": "Dieta sin lactosa (demostracion)." if index % 60 == 0 else "",
                },
            )
            created += int(was_created)

        total = PaeBeneficiary.objects.filter(vigencia=vigencia, deleted_at__isnull=True).count()
        for prioritization in prioritizations:
            prioritization.prioritized_students = prioritization.beneficiaries.count()
            prioritization.save(update_fields=["prioritized_students", "updated_at"])

        if len(enrollments) < target:
            self.stdout.write(self.style.WARNING(
                f"  Solo hay {len(enrollments)} matriculas activas de las {target} solicitadas. "
                "Ejecute seed_demo con mas estudiantes por grupo si desea la cifra completa."
            ))
        self.stdout.write(f"  Beneficiarios: {created} nuevos ({total} totales)")
        return list(PaeBeneficiary.objects.filter(vigencia=vigencia, status="ACTIVO", deleted_at__isnull=True))

    def _operator(self, institution):
        from ...models import PaeOperator

        operator, _ = PaeOperator.objects.get_or_create(
            institution=institution,
            code="OP-DEMO-01",
            defaults={
                "business_name": "Alimentos Escolares Demo S.A.S.",
                "nit": "900123456-7",
                "legal_representative": "Ana Maria Ficticia Gomez",
                "contact_name": "Carlos Demo Ramirez",
                "phone": "6015551234",
                "mobile": "3105550000",
                "email": "contacto@operador.demo.local",
                "address": "Carrera 10 No. 20 - 15",
                "city": "Bogota D.C.",
                "sanitary_registration": "CS-DEMO-2026",
                "status": "ACTIVO",
                "observations": "Operador ficticio para demostracion.",
            },
        )
        self.stdout.write(f"  Operador: {operator.business_name}")
        return operator

    def _contract(self, vigencia, operator, campuses):
        from ...models import PaeContract, PaeModality

        rations = 60000
        contract, _ = PaeContract.objects.get_or_create(
            vigencia=vigencia,
            number="CT-DEMO-2026-001",
            defaults={
                "operator": operator,
                "subject": "Prestacion del servicio de alimentacion escolar (contrato de demostracion).",
                "value": Decimal("180000000.00"),
                "ration_value": Decimal("3000.00"),
                "start_date": vigencia.start_date,
                "end_date": vigencia.end_date,
                "total_rations": rations,
                "status": "VIGENTE",
                "alert_days": 30,
                "observations": "Contrato ficticio para demostracion.",
            },
        )
        contract.campuses.set(campuses)
        modality = PaeModality.objects.filter(code="PREPARADA").first()
        if modality:
            contract.modalities.set([modality])
        self.stdout.write(f"  Contrato: {contract.number}")
        return contract

    def _menu_cycle(self, vigencia):
        from ...models import (
            PaeCatalog,
            PaeComplementType,
            PaeMenuCycle,
            PaeMenuDay,
            PaeMenuIngredient,
            PaeMenuPreparation,
            PaeModality,
        )

        cycle, created = PaeMenuCycle.objects.get_or_create(
            vigencia=vigencia,
            code="CM-DEMO-01",
            version=1,
            defaults={
                "name": "Ciclo de menu de demostracion",
                "modality": PaeModality.objects.filter(code="PREPARADA").first(),
                "complement_type": PaeComplementType.objects.filter(code="AM").first(),
                "days_count": len(MENU_DAYS),
                "start_date": vigencia.start_date,
                "end_date": vigencia.end_date,
                "nutritionist": "Laura Ficticia Perez",
                "professional_card": "TP-DEMO-0001",
                "status": "VIGENTE",
                "normative": vigencia.normative,
            },
        )

        if created:
            food_groups = {
                row.code: row
                for row in PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_FOOD_GROUP)
            }
            for day_number, day_name, preparations in MENU_DAYS:
                day = PaeMenuDay.objects.create(
                    cycle=cycle, day_number=day_number, weekday=day_number, name=day_name
                )
                for order, (name, component, portion, calories, protein, ingredients) in enumerate(preparations, start=1):
                    preparation = PaeMenuPreparation.objects.create(
                        day=day,
                        name=name,
                        component=component,
                        portion=portion,
                        calories=Decimal(calories),
                        protein=Decimal(protein),
                        order=order,
                    )
                    for ingredient_name, group_code, quantity, unit in ingredients:
                        PaeMenuIngredient.objects.create(
                            preparation=preparation,
                            name=ingredient_name,
                            food_group=food_groups.get(group_code),
                            quantity=Decimal(quantity),
                            unit=unit,
                        )

        days = cycle.days.count()
        self.stdout.write(f"  Ciclo de menu: {cycle.code} con {days} dias")
        return cycle

    def _plans(self, vigencia, institution, campuses, operator, contract, cycle, beneficiaries):
        from ...models import PaeComplementType, PaeModality, PaePlan

        modality = PaeModality.objects.filter(code="PREPARADA").first()
        complement = PaeComplementType.objects.filter(code="AM").first()
        per_campus = max(len(beneficiaries) // max(len(campuses), 1), 1)

        plans = []
        for campus in campuses:
            plan, _ = PaePlan.objects.get_or_create(
                vigencia=vigencia,
                campus=campus,
                name=f"Plan operativo {campus.name}",
                defaults={
                    "institution": institution,
                    "start_date": vigencia.start_date,
                    "end_date": vigencia.end_date,
                    "modality": modality,
                    "complement_type": complement,
                    "operator": operator,
                    "contract": contract,
                    "menu_cycle": cycle,
                    "beneficiaries_count": per_campus,
                    "service_days": vigencia.service_days,
                    "status": "EN_EJECUCION",
                    "approved_at": timezone.now(),
                    "observations": "Plan de demostracion.",
                },
            )
            plans.append(plan)
        self.stdout.write(f"  Planes operativos: {len(plans)}")
        return plans

    def _schedules(self, plans, cycle, working_days):
        from ...models import PaeSchedule

        days = list(cycle.days.order_by("day_number"))
        if not days:
            return []

        created = 0
        schedules = []
        for plan in plans:
            current = min(timezone.localdate(), plan.end_date) - dt.timedelta(days=working_days * 2)
            current = max(current, plan.start_date)
            index = 0
            produced = 0
            while produced < working_days and current <= plan.end_date:
                if current.isoweekday() <= 5:
                    schedule, was_created = PaeSchedule.objects.get_or_create(
                        plan=plan,
                        service_date=current,
                        campus=plan.campus,
                        shift=None,
                        complement_type=plan.complement_type,
                        defaults={
                            "operator": plan.operator,
                            "menu_day": days[index % len(days)],
                            "beneficiaries_count": plan.beneficiaries_count,
                            "scheduled_rations": plan.beneficiaries_count,
                            "status": "EJECUTADA",
                        },
                    )
                    schedules.append(schedule)
                    created += int(was_created)
                    index += 1
                    produced += 1
                current += dt.timedelta(days=1)
        self.stdout.write(f"  Programaciones: {created} nuevas ({len(schedules)} en el rango)")
        return schedules

    def _deliveries(self, schedules):
        from ...models import PaeCatalog, PaeDelivery

        causes = list(PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_CAUSE))
        created = 0
        deliveries = []
        today = timezone.localdate()

        for schedule in schedules:
            if schedule.service_date > today:
                continue
            scheduled = schedule.scheduled_rations
            # 1 de cada 8 entregas presenta faltantes; 1 de cada 12 queda incompleta.
            received = scheduled - (random.randint(2, 12) if random.random() < 0.125 else 0)
            delivered = received - (random.randint(1, 8) if random.random() < 0.083 else 0)
            received = max(received, 0)
            delivered = max(min(delivered, received), 0)
            incomplete = received < scheduled or delivered < received

            delivery, was_created = PaeDelivery.objects.get_or_create(
                schedule=schedule,
                defaults={
                    "plan": schedule.plan,
                    "contract": schedule.plan.contract,
                    "service_date": schedule.service_date,
                    "campus": schedule.campus,
                    "shift": schedule.shift,
                    "operator": schedule.operator,
                    "complement_type": schedule.complement_type,
                    "scheduled_menu": schedule.menu_day,
                    "scheduled_beneficiaries": schedule.beneficiaries_count,
                    "scheduled_rations": scheduled,
                    "received_rations": received,
                    "delivered_rations": delivered,
                    "arrival_time": dt.time(6, 40),
                    "delivery_time": dt.time(7, 10),
                    "menu_matches": True,
                    "status": "CON_NOVEDAD" if incomplete else "REGISTRADA",
                    "noncompliance_cause": random.choice(causes) if (incomplete and causes) else None,
                    "justification": (
                        "Novedad de demostracion registrada por diferencia entre lo programado y lo entregado."
                        if incomplete else ""
                    ),
                },
            )
            deliveries.append(delivery)
            created += int(was_created)

        self.stdout.write(f"  Entregas diarias: {created} nuevas ({len(deliveries)} en el rango)")
        return deliveries

    def _incidents(self, vigencia, deliveries, operator):
        from ...models import PaeCatalog, PaeIncident

        types = list(PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_INCIDENT))
        candidates = [row for row in deliveries if row.status == "CON_NOVEDAD"][:18]
        statuses = ["REPORTADA", "ASIGNADA", "EN_INVESTIGACION", "EN_CORRECCION", "SOLUCIONADA", "CERRADA"]

        created = []
        for index, delivery in enumerate(candidates):
            status = statuses[index % len(statuses)]
            incident, was_created = PaeIncident.objects.get_or_create(
                vigencia=vigencia,
                campus=delivery.campus,
                delivery=delivery,
                defaults={
                    "operator": operator,
                    "incident_type": types[index % len(types)] if types else None,
                    "reported_on": delivery.service_date,
                    "description": INCIDENT_TEXTS[index % len(INCIDENT_TEXTS)],
                    "priority": ["BAJA", "MEDIA", "ALTA", "CRITICA"][index % 4],
                    "due_date": delivery.service_date + dt.timedelta(days=8),
                    "status": status,
                    "solution": "Accion de demostracion aplicada." if status in ("SOLUCIONADA", "CERRADA") else "",
                    "solved_at": timezone.now() if status in ("SOLUCIONADA", "CERRADA") else None,
                    "closed_at": timezone.now() if status == "CERRADA" else None,
                },
            )
            if was_created:
                created.append(incident)
        self.stdout.write(f"  Novedades: {len(created)} nuevas")
        return created

    def _visits(self, vigencia, campuses, operator):
        from ...models import PaeCatalog, PaeVisit

        types = list(PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_VISIT))
        today = timezone.localdate()
        visits = []
        for index, campus in enumerate(campuses):
            for offset, status in ((45, "CERRADA"), (18, "REALIZADA"), (-12, "PROGRAMADA")):
                visit, _ = PaeVisit.objects.get_or_create(
                    vigencia=vigencia,
                    campus=campus,
                    visit_date=today - dt.timedelta(days=offset),
                    defaults={
                        "operator": operator,
                        "visit_type": types[index % len(types)] if types else None,
                        "number": f"VIS-{campus.code}-{abs(offset)}",
                        "start_time": dt.time(8, 0),
                        "end_time": dt.time(10, 30),
                        "objective": "Verificar las condiciones de prestacion del servicio (demostracion).",
                        "attendees": "Coordinador de sede, supervisor y representante del operador.",
                        "development": "Recorrido por las areas de preparacion, almacenamiento y servido.",
                        "conclusions": "Se dejan compromisos de mejora en acta.",
                        "status": status,
                    },
                )
                visits.append(visit)
        self.stdout.write(f"  Visitas: {len(visits)}")
        return visits

    def _findings(self, visits):
        from ...models import PaeCatalog, PaeFinding

        types = list(PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_FINDING))
        severities = ["LEVE", "MODERADO", "GRAVE", "CRITICO"]
        findings = []
        for index, visit in enumerate(v for v in visits if v.status in ("REALIZADA", "CERRADA")):
            finding, _ = PaeFinding.objects.get_or_create(
                visit=visit,
                campus=visit.campus,
                description=FINDING_TEXTS[index % len(FINDING_TEXTS)],
                defaults={
                    "finding_type": types[index % len(types)] if types else None,
                    "code": f"HAL-{visit.number}-{index + 1}",
                    "severity": severities[index % len(severities)],
                    "detected_on": visit.visit_date,
                    "normative_reference": "POR VALIDAR",
                    "status": "CERRADO" if visit.status == "CERRADA" else "ABIERTO",
                },
            )
            findings.append(finding)
        self.stdout.write(f"  Hallazgos: {len(findings)}")
        return findings

    def _improvement_actions(self, vigencia, findings, incidents):
        from ...models import PaeImprovementAction

        today = timezone.localdate()
        created = 0
        for index, finding in enumerate(findings):
            vencida = index % 4 == 0
            _, was_created = PaeImprovementAction.objects.get_or_create(
                vigencia=vigencia,
                finding=finding,
                defaults={
                    "campus": finding.campus,
                    "code": f"PM-{finding.code}",
                    "finding_description": finding.description,
                    "root_cause": "Causa raiz de demostracion.",
                    "action": "Implementar el control correspondiente y verificar su eficacia.",
                    "start_date": finding.detected_on,
                    "due_date": today - dt.timedelta(days=5) if vencida else today + dt.timedelta(days=20),
                    "indicator": "Porcentaje de cumplimiento del control",
                    "goal": "100%",
                    "progress": 100 if finding.status == "CERRADO" else random.randint(10, 80),
                    "status": "CERRADA" if finding.status == "CERRADO" else "EN_EJECUCION",
                },
            )
            created += int(was_created)

        for incident in incidents[:4]:
            _, was_created = PaeImprovementAction.objects.get_or_create(
                vigencia=vigencia,
                incident=incident,
                defaults={
                    "campus": incident.campus,
                    "code": f"PM-{incident.number}",
                    "finding_description": incident.description,
                    "root_cause": "Causa raiz de demostracion.",
                    "action": "Reforzar el control operativo en la sede.",
                    "start_date": incident.reported_on,
                    "due_date": incident.reported_on + dt.timedelta(days=25),
                    "progress": 40,
                    "status": "EN_EJECUCION",
                },
            )
            created += int(was_created)
        self.stdout.write(f"  Planes de mejoramiento: {created} nuevos")

    def _pqrs(self, vigencia, campuses):
        from ...models import PaeCatalog, PaePqrs

        types = {row.code: row for row in PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_PQRS)}
        today = timezone.localdate()
        statuses = ["RADICADA", "EN_TRAMITE", "RESPONDIDA", "CERRADA", "EN_TRAMITE"]

        created = 0
        for index, (kind, description) in enumerate(PQRS_TEXTS):
            filed = today - dt.timedelta(days=(index + 1) * 6)
            status = statuses[index % len(statuses)]
            _, was_created = PaePqrs.objects.get_or_create(
                vigencia=vigencia,
                filing_number=f"PQRS-DEMO-{index + 1:03d}",
                defaults={
                    "campus": campuses[index % len(campuses)],
                    "kind": kind,
                    "pqrs_type": types.get(kind),
                    "channel": ["PRESENCIAL", "BUZON", "PLATAFORMA", "CORREO", "TELEFONO"][index % 5],
                    "filed_on": filed,
                    "applicant_name": "" if index == 3 else f"Solicitante Ficticio {index + 1}",
                    "applicant_email": "" if index == 3 else f"solicitante{index + 1}@demo.local",
                    "is_anonymous": index == 3,
                    "description": description,
                    "due_date": filed + dt.timedelta(days=15),
                    "answer": "Respuesta de demostracion." if status in ("RESPONDIDA", "CERRADA") else "",
                    "answered_on": filed + dt.timedelta(days=9) if status in ("RESPONDIDA", "CERRADA") else None,
                    "status": status,
                },
            )
            created += int(was_created)
        self.stdout.write(f"  PQRS: {created} nuevas")

    def _participation(self, vigencia, campuses):
        from ...models import PaeCatalog, PaeCommitment, PaeParticipant, PaeParticipationMeeting

        meeting_type = PaeCatalog.objects.filter(
            catalog_type=PaeCatalog.TYPE_MEETING, code="COMITE"
        ).first()
        today = timezone.localdate()

        meeting, created = PaeParticipationMeeting.objects.get_or_create(
            vigencia=vigencia,
            act_number="ACTA-DEMO-001",
            defaults={
                "campus": campuses[0],
                "meeting_type": meeting_type,
                "meeting_date": timezone.now() - dt.timedelta(days=20),
                "place": "Sala de juntas de la sede principal",
                "subject": "Instalacion del comite de alimentacion escolar (demostracion)",
                "agenda": "1. Verificacion de quorum. 2. Presentacion del programa. 3. Compromisos.",
                "development": "Se presento la operacion del programa y se recogieron observaciones.",
                "agreements": "Se acuerda realizar seguimiento mensual a la entrega del complemento.",
                "attendees_count": 9,
                "status": "REALIZADA",
            },
        )

        if created:
            for index, (name, role, organization) in enumerate([
                ("Rector Ficticio Institucional", "DIRECTIVO", "Institucion educativa"),
                ("Coordinadora Ficticia de Sede", "DIRECTIVO", "Institucion educativa"),
                ("Representante Ficticio de Padres", "PADRE", "Consejo de padres"),
                ("Personero Ficticio Estudiantil", "ESTUDIANTE", "Gobierno escolar"),
                ("Supervisor Ficticio del Contrato", "ENTE_TERRITORIAL", "Ente territorial"),
            ], start=1):
                PaeParticipant.objects.create(
                    meeting=meeting, full_name=name, role=role, organization=organization,
                    document=f"DEMO{index:04d}",
                )
            PaeCommitment.objects.create(
                meeting=meeting,
                description="Publicar mensualmente el ciclo de menu en la cartelera de cada sede.",
                responsible_name="Coordinadora Ficticia de Sede",
                due_date=today + dt.timedelta(days=30),
                status="PENDIENTE",
            )
        self.stdout.write(f"  Participacion ciudadana: acta {meeting.act_number}")

    def _documents(self, vigencia, operator, contract):
        from ...models import PaeCatalog, PaeDocument

        types = {row.code: row for row in PaeCatalog.objects.filter(catalog_type=PaeCatalog.TYPE_DOCUMENT)}
        today = timezone.localdate()

        created = 0
        for type_code, module, name, expires_in in DOCUMENTS:
            if PaeDocument.objects.filter(vigencia=vigencia, name=name).exists():
                continue
            document = PaeDocument(
                vigencia=vigencia,
                document_type=types.get(type_code),
                module=module,
                name=name,
                description="Documento ficticio generado para la demostracion del modulo.",
                document_date=today - dt.timedelta(days=30),
                expires_on=today + dt.timedelta(days=expires_in) if expires_in is not None else None,
                operator=operator if module == "OPERADORES" else None,
                contract=contract if module == "CONTRATOS" else None,
                status="VIGENTE",
            )
            document.file.save(
                f"{type_code.lower()}_demo.txt",
                ContentFile(f"Documento de demostracion: {name}.\nNo corresponde a un soporte real.\n".encode("utf-8")),
                save=False,
            )
            document.save()
            created += 1
        self.stdout.write(f"  Documentos: {created} nuevos")

    def _indicators(self, vigencia):
        from ... import services

        saved = services.refresh_indicators(vigencia)
        self.stdout.write(f"  Indicadores calculados: {saved}")
