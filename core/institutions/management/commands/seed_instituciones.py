"""
Crea instituciones educativas de prueba para el ingreso multi-institucion:

    python manage.py seed_instituciones

Cada institucion queda con su propia estructura completa e independiente:
sedes, jornadas, ano lectivo con periodos, escala valorativa, niveles, grados,
grupos, areas, asignaturas y un usuario administrador propio.

NO toca la institucion existente: se conserva tal como esta, con su marca de
institucion por defecto y todos sus datos.

La informacion es ficticia y no corresponde a instituciones reales.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.academic.models import SchoolYear

from ...services import create_institution

# Instituciones ficticias de demostracion.
INSTITUCIONES = [
    {
        "code": "111111111111",
        "name": "Institucion Educativa Ficticia San Rafael",
        "short_name": "IE San Rafael",
        "nit": "900111111-1",
        "nature": "OFICIAL",
        "department": "Antioquia",
        "city": "Medellin",
        "address": "Carrera 45 No. 30 - 12",
        "phone": "(604) 111 1111",
        "rector_name": "Rector Ficticio San Rafael",
        "motto": "Formar para la vida",
        "primary_color": "#4F46E5",
        "campuses": [("SEDE-A", "Sede Principal", True), ("SEDE-B", "Sede Norte", False)],
        "alias": "sanrafael",
    },
    {
        "code": "222222222222",
        "name": "Institucion Educativa Ficticia La Esperanza",
        "short_name": "IE La Esperanza",
        "nit": "900222222-2",
        "nature": "OFICIAL",
        "department": "Valle del Cauca",
        "city": "Cali",
        "address": "Calle 15 No. 22 - 40",
        "phone": "(602) 222 2222",
        "rector_name": "Rectora Ficticia La Esperanza",
        "motto": "Educacion con equidad",
        "primary_color": "#0EA5E9",
        "campuses": [("SEDE-A", "Sede Central", True), ("SEDE-R", "Sede Rural El Progreso", False)],
        "alias": "laesperanza",
    },
    {
        "code": "333333333333",
        "name": "Colegio Ficticio Santa Teresa",
        "short_name": "Col. Santa Teresa",
        "nit": "900333333-3",
        "nature": "PRIVADA",
        "department": "Atlantico",
        "city": "Barranquilla",
        "address": "Via 40 No. 70 - 05",
        "phone": "(605) 333 3333",
        "rector_name": "Rectora Ficticia Santa Teresa",
        "motto": "Excelencia y servicio",
        "primary_color": "#10B981",
        "campuses": [("SEDE-A", "Sede Unica", True)],
        "alias": "santateresa",
    },
]

# Un usuario por perfil en cada institucion, para poder recorrer cada entorno
# con distintos niveles de acceso.
PERFILES = [
    ("RECTOR", "rector", "Rector", "Institucional"),
    ("COORDINADOR", "coordinador", "Coordinador", "Academico"),
    ("SECRETARIA", "secretaria", "Secretaria", "Academica"),
    ("DOCENTE", "docente", "Docente", "De Prueba"),
]

PASSWORD = "Demo123*"

NOMBRES_M = ["Juan Carlos", "Andres Felipe", "Santiago", "Mateo", "Sebastian", "Nicolas",
             "Daniel", "Samuel", "Emiliano", "Tomas", "Martin", "Diego Alejandro"]
NOMBRES_F = ["Maria Jose", "Sofia", "Valentina", "Isabella", "Camila", "Luciana",
             "Mariana", "Salome", "Antonia", "Emilia", "Gabriela", "Daniela"]
APELLIDOS = ["Gomez", "Rodriguez", "Martinez", "Lopez", "Garcia", "Perez", "Sanchez",
             "Ramirez", "Torres", "Diaz", "Vargas", "Castro", "Rojas", "Moreno"]


class Command(BaseCommand):
    help = "Crea instituciones educativas de prueba con su estructura academica propia"

    def add_arguments(self, parser):
        parser.add_argument("--ano", type=int, default=None, help="Ano lectivo a crear.")
        parser.add_argument("--grupos-por-grado", type=int, default=1)
        parser.add_argument(
            "--solo", type=str, default=None,
            help="Codigo DANE de una sola institucion a crear.",
        )
        parser.add_argument(
            "--estudiantes-por-grupo", type=int, default=6,
            help="Estudiantes ficticios por grupo. Use 0 para no crear ninguno.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.utils import timezone

        from ...models import Institution

        year = options["ano"] or timezone.localdate().year
        objetivo = [i for i in INSTITUCIONES if not options["solo"] or i["code"] == options["solo"]]
        if not objetivo:
            self.stdout.write(self.style.ERROR(f"No hay institucion con codigo {options['solo']}."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("PL_SGE - Instituciones de prueba"))
        existente = Institution.objects.filter(is_default=True).first()
        if existente:
            self.stdout.write(f"  Se conserva la institucion actual: {existente.name}")

        creadas = []
        for datos in objetivo:
            institution, creada = create_institution(
                datos, bootstrap=True, year=year,
                groups_per_grade=options["grupos_por_grado"],
            )
            self._sedes(institution, datos["campuses"])
            school_year = SchoolYear.objects.get(institution=institution, year=year)
            self.stdout.write(f"  {institution.short_name:<22} {'creada' if creada else 'ya existia'}")
            usuarios = self._usuarios(institution, datos["alias"])
            if options["estudiantes_por_grupo"]:
                docentes = self._docentes(institution, datos["code"])
                total = self._estudiantes(
                    school_year, datos["code"], options["estudiantes_por_grupo"]
                )
                self.stdout.write(f"    docentes: {docentes} | estudiantes: {total}")
            creadas.append((institution, usuarios))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Instituciones de prueba disponibles: {len(creadas)}"))
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(
            f"  CREDENCIALES POR INSTITUCION   (contrasena comun: {PASSWORD})"
        ))
        for institution, usuarios in creadas:
            self.stdout.write("")
            self.stdout.write(f"  {institution.name}")
            self.stdout.write(f"    {institution.city} | codigo DANE {institution.code}")
            for role_code, usuario in usuarios:
                self.stdout.write(f"      {role_code:<14} {usuario.email}")

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  ACCESO A TODAS LAS INSTITUCIONES"))
        self.stdout.write("      SUPER_ADMIN    admin@datly.local / Admin123*")
        self.stdout.write("")
        self.stdout.write(
            "  En el ingreso aparece el selector de institucion. El Super Administrador\n"
            "  puede entrar a cualquiera; los demas usuarios solo a la suya."
        )
        self.stdout.write(self.style.WARNING(
            "  Informacion ficticia: no corresponde a instituciones reales."
        ))

    # ------------------------------------------------------------------

    def _sedes(self, institution, campuses):
        from ...models import Campus

        for code, name, principal in campuses:
            Campus.objects.get_or_create(
                institution=institution, code=code,
                defaults={"name": name, "address": institution.address, "is_main": principal},
            )










    def _docentes(self, institution, dane, cantidad=8):
        """
        Planta docente ficticia, con asignacion a los grupos.

        Sin docentes la institucion queda incompleta: no se puede digitar
        notas ni asistencia, que es lo que el panel reporta.
        """
        import random

        from core.teachers.models import Teacher

        random.seed(int(dane[:3]) + 7)
        titulos = ["Licenciado en Matematicas", "Licenciada en Espanol", "Licenciado en Biologia",
                   "Licenciada en Ingles", "Licenciado en Ciencias Sociales", "Licenciada en Artes",
                   "Licenciado en Educacion Fisica", "Ingeniera de Sistemas"]
        creados = 0
        for indice in range(1, cantidad + 1):
            documento = f"{dane[:3]}9{indice:05d}"
            if Teacher.objects.filter(document_number=documento).exists():
                continue
            genero = random.choice(["M", "F"])
            Teacher.objects.create(
                institution=institution,
                document_number=documento,
                first_name=random.choice(NOMBRES_M if genero == "M" else NOMBRES_F),
                last_name=f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}",
                gender=genero,
                email=f"docente{indice}.{institution.code[:3]}@datly.local",
                profession=random.choice(titulos),
                academic_title=random.choice(titulos),
                contract_type=random.choice(["PLANTA", "CONTRATO", "PROVISIONAL"]),
                weekly_hours=random.choice([20, 22, 24]),
                is_tutor=indice % 2 == 0,
                status="ACTIVO",
            )
            creados += 1
        return creados

    def _estudiantes(self, school_year, dane, por_grupo):
        """
        Estudiantes ficticios matriculados en la institucion.

        El documento lleva el prefijo del codigo DANE, de modo que dos
        instituciones nunca comparten un estudiante ni chocan por el numero,
        que es unico en toda la plataforma.
        """
        import random

        from core.students.models import Enrollment, Student

        random.seed(int(dane[:3]))
        prefijo = dane[:3]
        institution = school_year.institution
        grupos = list(school_year.groups.filter(deleted_at__isnull=True).select_related("grade"))

        creados = 0
        consecutivo = 0
        for grupo in grupos:
            for _ in range(por_grupo):
                consecutivo += 1
                documento = f"{prefijo}{consecutivo:07d}"
                if Student.objects.filter(document_number=documento).exists():
                    continue
                genero = random.choice(["M", "F"])
                nombre = random.choice(NOMBRES_M if genero == "M" else NOMBRES_F)
                estudiante = Student.objects.create(
                    institution=institution,
                    document_number=documento,
                    first_name=nombre,
                    last_name=f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}",
                    gender=genero,
                    birth_date=dt.date(
                        school_year.year - 6 - grupo.grade.numeric_value,
                        random.randint(1, 12), random.randint(1, 28),
                    ),
                    status="ACTIVO",
                )
                Enrollment.objects.create(
                    student=estudiante, school_year=school_year, group=grupo,
                    enrollment_date=school_year.start_date, status="ACTIVA",
                )
                creados += 1
        return creados

    def _usuarios(self, institution, alias):
        """
        Un usuario por perfil, propio de la institucion.

        Cada uno queda atado a su institucion: si intenta ingresar a otra, el
        sistema lo rechaza. Asi cada institucion es un entorno independiente.
        """
        from core.users.models import Role, User

        creados = []
        for role_code, prefijo, nombre, apellido in PERFILES:
            rol = Role.objects.filter(code=role_code).first()
            if rol is None:
                continue
            email = f"{prefijo}.{alias}@datly.local"
            usuario = User.objects.filter(email=email).first()
            if usuario is None:
                usuario = User.objects.create_user(
                    email=email,
                    password=PASSWORD,
                    username=email.split("@")[0],
                    first_name=nombre,
                    last_name=f"{apellido} {institution.short_name}",
                    role=rol,
                    institution=institution,
                    email_verified=True,
                )
            else:
                usuario.institution = institution
                usuario.role = rol
                usuario.set_password(PASSWORD)
                usuario.save(update_fields=["institution", "role", "password"])
            creados.append((role_code, usuario))
        return creados
