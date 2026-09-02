"""
Carga datos de demostracion sobre una plataforma ya inicializada:

    python manage.py seed_demo

Genera docentes, estudiantes, acudientes, matriculas, asignaciones academicas,
procesos evaluables, notas, asistencia, agenda y observaciones para poder
recorrer todos los modulos con informacion realista.
"""
from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

FIRST_NAMES_M = ["Juan", "Carlos", "Andres", "Santiago", "Mateo", "Sebastian", "Nicolas", "Daniel",
                 "Samuel", "Emiliano", "Tomas", "Martin", "Felipe", "Diego", "Alejandro"]
FIRST_NAMES_F = ["Maria", "Sofia", "Valentina", "Isabella", "Camila", "Luciana", "Mariana", "Salome",
                 "Antonia", "Emilia", "Gabriela", "Daniela", "Paulina", "Juliana", "Laura"]
LAST_NAMES = ["Gomez", "Rodriguez", "Martinez", "Lopez", "Garcia", "Perez", "Sanchez", "Ramirez",
              "Torres", "Diaz", "Vargas", "Castro", "Rojas", "Moreno", "Jimenez", "Herrera",
              "Munoz", "Alvarez", "Romero", "Suarez"]
CITIES = ["Bogota D.C.", "Medellin", "Cali", "Barranquilla", "Bucaramanga", "Pereira", "Manizales"]
NEIGHBORHOODS = ["El Prado", "La Castellana", "Villa Alsacia", "Los Alcazares", "Santa Barbara", "Modelia"]

PROCESSES = [
    ("Trabajo en clase", Decimal("25.00")),
    ("Taller evaluativo", Decimal("25.00")),
    ("Evaluacion de periodo", Decimal("30.00")),
    ("Actitudinal", Decimal("20.00")),
]

EVENTS = [
    ("Induccion de estudiantes", "INSTITUCIONAL", 5),
    ("Entrega de boletines - Periodo 1", "ENTREGA_BOLETINES", 62),
    ("Semana cultural", "CULTURAL", 90),
    ("Juegos interclases", "DEPORTIVO", 120),
    ("Reunion general de padres", "REUNION", 45),
    ("Simulacro de pruebas Saber", "EVALUACION", 150),
    ("Izada de bandera", "INSTITUCIONAL", 30),
    ("Consejo academico", "REUNION", 75),
]


class Command(BaseCommand):
    help = "Carga datos de demostracion para recorrer todos los modulos de PL_SGE"

    def add_arguments(self, parser):
        parser.add_argument("--students-per-group", type=int, default=12)
        parser.add_argument("--teachers", type=int, default=14)
        parser.add_argument("--seed", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, **options):
        from core.academic.models import AcademicPeriod, Group, SchoolYear

        random.seed(options["seed"])

        year = SchoolYear.current()
        if year is None:
            self.stdout.write(self.style.ERROR("No hay ano lectivo. Ejecute primero initialize_platform."))
            return
        period = AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
        groups = list(Group.objects.filter(school_year=year, deleted_at__isnull=True).select_related("grade"))
        if not groups:
            self.stdout.write(self.style.ERROR("No hay grupos creados. Ejecute initialize_platform."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("PL_SGE - Carga de datos de demostracion"))

        teachers = self._teachers(year, options["teachers"])
        self._tutors(year, groups, teachers)
        students = self._students(year, groups, options["students_per_group"])
        assignments = self._assignments(year, groups, teachers)
        self._schedules(assignments)
        processes = self._processes(assignments, period)
        self._grades(assignments, processes, period)
        self._attendance(assignments, period)
        self._agenda(year, groups)
        self._observer(year, period, students)
        self._emphases(year, students)
        self._election(year, students)
        self._demo_users(year, teachers, students)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de demostracion cargados correctamente."))

    # ------------------------------------------------------------------
    def _person(self, gender=None):
        gender = gender or random.choice(["M", "F"])
        first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        second = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        last = f"{random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"
        return f"{first} {second}", last, gender

    def _teachers(self, year, quantity):
        from core.teachers.models import Teacher

        institution = year.institution
        created = []
        titles = ["Licenciado en Matematicas", "Licenciada en Espanol", "Licenciado en Biologia",
                  "Licenciada en Ingles", "Licenciado en Ciencias Sociales", "Licenciada en Artes",
                  "Licenciado en Educacion Fisica", "Ingeniero de Sistemas"]

        for index in range(1, quantity + 1):
            document = f"10{index:06d}"
            if Teacher.objects.filter(document_number=document).exists():
                continue
            first, last, gender = self._person()
            teacher = Teacher.objects.create(
                institution=institution,
                document_number=document,
                first_name=first,
                last_name=last,
                gender=gender,
                birth_date=dt.date(random.randint(1975, 1995), random.randint(1, 12), random.randint(1, 28)),
                email=f"docente{index}@datly.local",
                mobile=f"3{random.randint(100000000, 199999999)}",
                address=f"Calle {random.randint(1, 180)} No. {random.randint(1, 90)} - {random.randint(1, 99)}",
                profession=random.choice(titles),
                academic_title=random.choice(titles),
                contract_type=random.choice(["PLANTA", "CONTRATO", "PROVISIONAL"]),
                hire_date=dt.date(random.randint(2015, 2024), random.randint(1, 12), random.randint(1, 28)),
                weekly_hours=random.choice([20, 22, 24]),
                is_tutor=index % 2 == 0,
                status="ACTIVO",
            )
            created.append(teacher)

        teachers = list(Teacher.objects.filter(institution=institution, status="ACTIVO"))
        self.stdout.write(f"  Docentes: {len(created)} nuevos ({len(teachers)} totales)")
        return teachers

    def _tutors(self, year, groups, teachers):
        from core.tutoring.models import Tutor

        candidates = [teacher for teacher in teachers if teacher.is_tutor] or teachers
        created = 0
        for index, group in enumerate(groups):
            teacher = candidates[index % len(candidates)]
            _, was_created = Tutor.objects.get_or_create(
                school_year=year, group=group, teacher=teacher, defaults={"is_main": True}
            )
            if group.director_id is None:
                group.director = teacher
                group.save(update_fields=["director"])
            created += int(was_created)
        self.stdout.write(f"  Tutores asignados: {created}")

    def _students(self, year, groups, per_group):
        from core.students.models import Enrollment, Guardian, Student, StudentGuardian

        institution = year.institution
        created_students = 0
        counter = 0

        for group in groups:
            for _ in range(per_group):
                counter += 1
                document = f"11{counter:07d}"
                if Student.objects.filter(document_number=document).exists():
                    continue
                first, last, gender = self._person()
                age = max(group.minimum_age if hasattr(group, "minimum_age") else 0, group.grade.minimum_age or 6)
                birth_year = year.year - (age or 10)
                student = Student.objects.create(
                    institution=institution,
                    document_type="TI",
                    document_number=document,
                    first_name=first,
                    last_name=last,
                    gender=gender,
                    birth_date=dt.date(birth_year, random.randint(1, 12), random.randint(1, 28)),
                    birth_place=random.choice(CITIES),
                    email=f"estudiante{counter}@datly.local",
                    mobile=f"3{random.randint(100000000, 199999999)}",
                    address=f"Carrera {random.randint(1, 120)} No. {random.randint(1, 90)} - {random.randint(1, 99)}",
                    neighborhood=random.choice(NEIGHBORHOODS),
                    city=institution.city,
                    department=institution.department,
                    stratum=random.randint(1, 5),
                    blood_type=random.choice(["O+", "A+", "B+", "AB+", "O-"]),
                    eps=random.choice(["Sura", "Sanitas", "Compensar", "Nueva EPS", "Famisanar"]),
                    emergency_contact=f"{random.choice(FIRST_NAMES_F)} {random.choice(LAST_NAMES)}",
                    emergency_phone=f"3{random.randint(100000000, 199999999)}",
                    entry_date=year.start_date,
                    status="ACTIVO",
                )

                guardian_first, guardian_last, guardian_gender = self._person()
                guardian, _ = Guardian.objects.get_or_create(
                    document_number=f"12{counter:07d}",
                    defaults={
                        "first_name": guardian_first,
                        "last_name": guardian_last,
                        "relation": "MADRE" if guardian_gender == "F" else "PADRE",
                        "email": f"acudiente{counter}@datly.local",
                        "mobile": f"3{random.randint(100000000, 199999999)}",
                        "address": student.address,
                        "occupation": random.choice(["Independiente", "Empleado", "Docente", "Comerciante", "Ingeniero"]),
                    },
                )
                StudentGuardian.objects.get_or_create(
                    student=student, guardian=guardian, defaults={"is_primary": True, "is_financial": True}
                )
                Enrollment.objects.get_or_create(
                    student=student,
                    school_year=year,
                    defaults={
                        "group": group,
                        "enrollment_date": year.start_date,
                        "enrollment_type": random.choice(["NUEVO", "ANTIGUO"]),
                        "status": "ACTIVA",
                    },
                )
                created_students += 1

        total = Student.objects.filter(institution=institution, deleted_at__isnull=True).count()
        self.stdout.write(f"  Estudiantes: {created_students} nuevos ({total} totales)")
        return list(Student.objects.filter(institution=institution, status="ACTIVO")[:400])

    def _assignments(self, year, groups, teachers):
        from core.academic.models import Subject
        from core.teachers.models import TeachingAssignment

        subjects = list(Subject.objects.filter(area__school_year=year, deleted_at__isnull=True))
        created = 0
        for group in groups:
            for index, subject in enumerate(subjects):
                teacher = teachers[(index + group.id) % len(teachers)]
                _, was_created = TeachingAssignment.objects.get_or_create(
                    school_year=year,
                    teacher=teacher,
                    subject=subject,
                    group=group,
                    defaults={"weekly_hours": subject.weekly_hours, "is_main": True},
                )
                created += int(was_created)

        assignments = list(
            TeachingAssignment.objects.filter(school_year=year, deleted_at__isnull=True)
            .select_related("subject", "group", "teacher")
        )
        self.stdout.write(f"  Asignaciones academicas: {created} nuevas ({len(assignments)} totales)")
        return assignments

    def _schedules(self, assignments):
        from core.teachers.models import ScheduleSlot

        blocks = [
            (1, dt.time(6, 30), dt.time(7, 25)),
            (2, dt.time(7, 25), dt.time(8, 20)),
            (3, dt.time(8, 40), dt.time(9, 35)),
            (4, dt.time(9, 35), dt.time(10, 30)),
            (5, dt.time(10, 50), dt.time(11, 45)),
            (6, dt.time(11, 45), dt.time(12, 40)),
        ]
        taken = set()
        created = 0
        for assignment in assignments:
            for _ in range(min(assignment.weekly_hours, 3)):
                for weekday in range(1, 6):
                    for block, start, end in blocks:
                        key = (assignment.teacher_id, weekday, block)
                        group_key = (assignment.group_id, weekday, block)
                        if key in taken or group_key in taken:
                            continue
                        ScheduleSlot.objects.get_or_create(
                            assignment=assignment,
                            weekday=weekday,
                            block=block,
                            defaults={
                                "start_time": start,
                                "end_time": end,
                                "classroom": assignment.group.classroom,
                            },
                        )
                        taken.add(key)
                        taken.add(group_key)
                        created += 1
                        break
                    else:
                        continue
                    break
                else:
                    continue
        self.stdout.write(f"  Franjas de horario: {created}")

    def _processes(self, assignments, period):
        from core.teachers.models import TeacherAcademicProcess

        if period is None:
            return []
        created = 0
        for assignment in assignments:
            for order, (name, weight) in enumerate(PROCESSES, start=1):
                _, was_created = TeacherAcademicProcess.objects.get_or_create(
                    assignment=assignment,
                    period=period,
                    name=name,
                    defaults={"weight": weight, "order": order},
                )
                created += int(was_created)
        processes = list(TeacherAcademicProcess.objects.filter(period=period, deleted_at__isnull=True))
        self.stdout.write(f"  Procesos evaluables: {created} nuevos ({len(processes)} totales)")
        return processes

    def _grades(self, assignments, processes, period):
        from core.evaluations.services import compute_area_grades, consolidate_subject_grade
        from core.evaluations.models import ProcessGrade

        if period is None:
            return
        by_assignment = {}
        for process in processes:
            by_assignment.setdefault(process.assignment_id, []).append(process)

        recorded = 0
        consolidated = 0
        touched_students = set()

        for assignment in assignments:
            items = by_assignment.get(assignment.id, [])
            if not items:
                continue
            enrollments = assignment.group.enrollments.filter(
                status="ACTIVA", deleted_at__isnull=True
            ).select_related("student")
            for enrollment in enrollments:
                for process in items:
                    score = Decimal(str(round(random.triangular(2.2, 5.0, 4.0), 1)))
                    _, was_created = ProcessGrade.objects.get_or_create(
                        student=enrollment.student,
                        process=process,
                        defaults={
                            "assignment": assignment,
                            "period": period,
                            "score": score,
                        },
                    )
                    recorded += int(was_created)
                if consolidate_subject_grade(enrollment.student, assignment, period):
                    consolidated += 1
                touched_students.add(enrollment.student)

        for student in touched_students:
            compute_area_grades(student, period)

        self.stdout.write(f"  Notas registradas: {recorded} | definitivas consolidadas: {consolidated}")

    def _attendance(self, assignments, period):
        from core.attendance.models import AttendanceRecord, AttendanceSession

        if period is None:
            return
        today = timezone.localdate()
        sessions = 0
        records = 0
        for assignment in assignments[:60]:
            for delta in range(1, 6):
                date = today - dt.timedelta(days=delta * 3)
                if date < period.start_date:
                    continue
                session, was_created = AttendanceSession.objects.get_or_create(
                    assignment=assignment,
                    date=date,
                    block=1,
                    defaults={"period": period, "topic": f"Sesion de {assignment.subject.name}"},
                )
                sessions += int(was_created)
                if not was_created:
                    continue
                for enrollment in assignment.group.enrollments.filter(status="ACTIVA", deleted_at__isnull=True):
                    status = random.choices(
                        ["PRESENTE", "AUSENTE", "TARDE", "EXCUSA"], weights=[88, 6, 4, 2]
                    )[0]
                    AttendanceRecord.objects.get_or_create(
                        session=session,
                        student=enrollment.student,
                        defaults={
                            "status": status,
                            "minutes_late": random.randint(5, 20) if status == "TARDE" else 0,
                        },
                    )
                    records += 1
        self.stdout.write(f"  Sesiones de asistencia: {sessions} | registros: {records}")

    def _agenda(self, year, groups):
        from core.agenda.models import AgendaEvent

        created = 0
        colors = {"INSTITUCIONAL": "#0EA5E9", "ENTREGA_BOLETINES": "#4F46E5", "CULTURAL": "#10B981",
                  "DEPORTIVO": "#10B981", "REUNION": "#A855F7", "EVALUACION": "#F59E0B"}
        for title, kind, offset in EVENTS:
            start = timezone.make_aware(
                dt.datetime.combine(year.start_date + dt.timedelta(days=offset), dt.time(8, 0))
            )
            _, was_created = AgendaEvent.objects.get_or_create(
                school_year=year,
                title=title,
                defaults={
                    "event_type": kind,
                    "audience": "TODOS",
                    "start_at": start,
                    "end_at": start + dt.timedelta(hours=3),
                    "place": "Sede Principal",
                    "color": colors.get(kind, "#4F46E5"),
                    "is_published": True,
                    "description": f"{title} programada dentro del calendario institucional.",
                },
            )
            created += int(was_created)
        self.stdout.write(f"  Eventos de agenda: {created}")

    def _observer(self, year, period, students):
        from core.observer.models import ObservationCategory, ObserverEntry

        categories = list(ObservationCategory.objects.all())
        if not categories or not students:
            return
        descriptions = [
            "El estudiante presenta dificultades para entregar los trabajos en las fechas establecidas.",
            "Se destaca por su participacion activa y liderazgo positivo en el aula.",
            "Llega tarde de manera reiterada al primer bloque de clase.",
            "Se presenta una situacion de convivencia con un companero durante el descanso.",
            "Se compromete a mejorar su desempeno academico en el area de matematicas.",
            "Representa a la institucion en el torneo interinstitucional de matematicas.",
        ]
        created = 0
        for student in random.sample(students, min(40, len(students))):
            category = random.choice(categories)
            ObserverEntry.objects.get_or_create(
                student=student,
                school_year=year,
                date=timezone.localdate() - dt.timedelta(days=random.randint(1, 60)),
                category=category,
                defaults={
                    "period": period,
                    "place": random.choice(["Aula de clase", "Patio", "Biblioteca", "Coordinacion"]),
                    "description": random.choice(descriptions),
                    "status": random.choice(["ABIERTA", "EN_SEGUIMIENTO", "CERRADA"]),
                },
            )
            created += 1
        self.stdout.write(f"  Anotaciones del observador: {created}")

    def _emphases(self, year, students):
        from core.emphases.models import Emphasis, EmphasisEnrollment, EmphasisGroup

        catalog = [
            ("DEP01", "Futbol", "DEPORTIVO", "#10B981"),
            ("DEP02", "Baloncesto", "DEPORTIVO", "#0EA5E9"),
            ("ART01", "Musica", "ARTISTICO", "#A855F7"),
            ("ART02", "Danzas", "ARTISTICO", "#EC4899"),
            ("TEC01", "Robotica", "TECNOLOGICO", "#4F46E5"),
            ("ACA01", "Semillero de Investigacion", "ACADEMICO", "#F59E0B"),
        ]
        created_groups = 0
        for order, (code, name, kind, color) in enumerate(catalog, start=1):
            emphasis, _ = Emphasis.objects.get_or_create(
                institution=year.institution,
                code=code,
                defaults={"name": name, "kind": kind, "color": color, "order": order},
            )
            group, was_created = EmphasisGroup.objects.get_or_create(
                emphasis=emphasis,
                school_year=year,
                code=f"{code}-01",
                defaults={
                    "name": f"{name} - Grupo 01",
                    "capacity": 25,
                    "weekday": (order % 5) + 1,
                    "start_time": dt.time(14, 0),
                    "end_time": dt.time(16, 0),
                    "place": "Sede Principal",
                    "status": "ABIERTO",
                },
            )
            created_groups += int(was_created)
            if was_created and students:
                for student in random.sample(students, min(15, len(students))):
                    EmphasisEnrollment.objects.get_or_create(group=group, student=student)
        self.stdout.write(f"  Grupos de enfasis: {created_groups}")

    def _election(self, year, students):
        from core.elections.models import Candidacy, Candidate, Election

        if not students:
            return
        election, created = Election.objects.get_or_create(
            school_year=year,
            name=f"Gobierno Escolar {year.year}",
            defaults={
                "description": "Eleccion de personero, contralor y representante estudiantil.",
                "start_at": timezone.now() - dt.timedelta(days=1),
                "end_at": timezone.now() + dt.timedelta(days=15),
                "status": "ABIERTA",
                "allow_blank_vote": True,
            },
        )
        if not created:
            return

        for order, (name, description) in enumerate(
            [
                ("Personero Estudiantil", "Representa a los estudiantes ante las directivas."),
                ("Contralor Estudiantil", "Vigila el uso de los recursos institucionales."),
                ("Representante de los Estudiantes", "Integra el consejo directivo."),
            ],
            start=1,
        ):
            candidacy = Candidacy.objects.create(
                election=election, name=name, description=description, voter_scope="TODOS", order=order
            )
            for number, student in enumerate(random.sample(students, min(3, len(students))), start=1):
                Candidate.objects.create(
                    candidacy=candidacy,
                    student=student,
                    number=number,
                    slogan=random.choice([
                        "Union y compromiso", "Tu voz, mi propuesta", "Por un colegio mejor",
                        "Liderazgo con proposito", "Juntos construimos",
                    ]),
                    proposals="Mejorar los espacios de descanso, fortalecer los proyectos culturales "
                              "y ampliar los canales de comunicacion con las directivas.",
                    is_approved=True,
                )
            Candidate.objects.create(
                candidacy=candidacy,
                number=99,
                slogan="Voto en blanco",
                is_blank_vote=True,
                is_approved=True,
            )
        self.stdout.write("  Proceso electoral de demostracion creado")

    def _demo_users(self, year, teachers, students):
        """Crea una cuenta de acceso por cada perfil para recorrer la plataforma."""
        from core.students.models import Student
        from core.users.models import Role, User

        password = "Demo123*"
        created = []

        # Docente vinculado a un docente real. Si el comando se ejecuta de
        # nuevo, se conserva el vinculo existente en vez de crear uno duplicado
        # (la relacion usuario-docente es uno a uno).
        teacher = next((t for t in teachers if t.user and t.user.email == "docente@datly.local"), None)
        teacher = teacher or next((t for t in teachers if t.user_id is None), None)
        if teacher:
            user = self._demo_user(
                "docente@datly.local", "docente", teacher.first_name, teacher.last_name,
                Role.DOCENTE, year.institution, password,
            )
            if teacher.user_id != user.pk:
                teacher.user = user
                teacher.save(update_fields=["user"])
            created.append(("DOCENTE", user.email))

        # Tutor vinculado a otro docente
        tutor_teacher = next((t for t in teachers if t.user and t.user.email == "tutor@datly.local"), None)
        tutor_teacher = tutor_teacher or next(
            (t for t in teachers if t.user_id is None and t.is_tutor), None
        )
        if tutor_teacher:
            user = self._demo_user(
                "tutor@datly.local", "tutor", tutor_teacher.first_name, tutor_teacher.last_name,
                Role.TUTOR, year.institution, password,
            )
            if tutor_teacher.user_id != user.pk:
                tutor_teacher.user = user
                tutor_teacher.save(update_fields=["user"])
            created.append(("TUTOR", user.email))

        # Estudiante vinculado a un estudiante matriculado
        student = Student.objects.filter(user__email="estudiante@datly.local").first()
        student = student or Student.objects.filter(user__isnull=True, status="ACTIVO").first()
        if student:
            user = self._demo_user(
                "estudiante@datly.local", "estudiante", student.first_name, student.last_name,
                Role.ESTUDIANTE, year.institution, password,
            )
            if student.user_id != user.pk:
                student.user = user
                student.save(update_fields=["user"])
            created.append(("ESTUDIANTE", user.email))

            guardian = student.main_guardian
            if guardian and (guardian.user_id is None or guardian.user.email == "acudiente@datly.local"):
                guardian_user = self._demo_user(
                    "acudiente@datly.local", "acudiente", guardian.first_name, guardian.last_name,
                    Role.ACUDIENTE, year.institution, password,
                )
                if guardian.user_id != guardian_user.pk:
                    guardian.user = guardian_user
                    guardian.save(update_fields=["user"])
                created.append(("ACUDIENTE", guardian_user.email))

        for code, email, first, last in [
            (Role.RECTOR, "rector@datly.local", "Rector", "Institucional"),
            (Role.COORDINADOR, "coordinador@datly.local", "Coordinador", "Academico"),
            (Role.SECRETARIA, "secretaria@datly.local", "Secretaria", "Academica"),
        ]:
            user = self._demo_user(email, email.split("@")[0], first, last, code, year.institution, password)
            created.append((code, user.email))

        self.stdout.write(f"  Usuarios de demostracion: {len(created)} (contrasena {password})")
        for code, email in created:
            self.stdout.write(f"    {code:<12} {email}")

    @staticmethod
    def _demo_user(email, username, first_name, last_name, role_code, institution, password):
        from core.users.models import Role, User

        role = Role.objects.get(code=role_code)
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "institution": institution,
                "is_active": True,
                "email_verified": True,
            },
        )
        user.role = role
        user.institution = institution
        user.is_active = True
        user.email_verified = True
        user.must_change_password = False
        user.set_password(password)
        user.save()
        return user
