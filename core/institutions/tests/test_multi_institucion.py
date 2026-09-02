"""
Pruebas del ingreso y el aislamiento multi-institucion.

Lo que se protege aqui: que la institucion elegida al ingresar sea la unica
cuyos datos se ven, y que el selector no pueda usarse para entrar a una
institucion ajena.
"""
from __future__ import annotations

import datetime as dt

from django.test import Client, TestCase
from django.utils import timezone

from ..context import SESSION_KEY, get_active_institution, use_institution
from ..scoping import institution_path, scope_queryset


def build_institution(code, name, *, default=False):
    """Institucion con ano lectivo, sede, grado y grupo propios."""
    from core.academic.models import EducationLevel, Grade, Group, SchoolYear

    from ..models import Campus, Institution

    institution = Institution.objects.create(
        code=code, name=name, short_name=name[:20], nit=f"900{code[:6]}-1", is_default=default
    )
    Campus.objects.create(institution=institution, code="SEDE-A", name="Principal", is_main=True)
    today = timezone.localdate()
    year = SchoolYear.objects.create(
        institution=institution, year=today.year, name=f"Ano {today.year}",
        start_date=today - dt.timedelta(days=60), end_date=today + dt.timedelta(days=120),
        is_current=True,
    )
    level = EducationLevel.objects.create(institution=institution, code="PRI", name="Primaria", order=1)
    grade = Grade.objects.create(level=level, code="1", name="Primero", order=1, numeric_value=1)
    group = Group.objects.create(school_year=year, grade=grade, code="1-01", name="Primero 01")
    return institution, year, group


def build_student(institution, document):
    from core.students.models import Student

    return Student.objects.create(
        institution=institution, document_number=document,
        first_name="Estudiante", last_name="De Prueba", gender="N", status="ACTIVO",
    )


def build_user(email, institution, role_code, password="Prueba123*"):
    from config.permissions import invalidate_permission_cache
    from core.users.models import Module, Role, RolePermission, User

    role, _ = Role.objects.get_or_create(code=role_code, defaults={"name": role_code.title()})
    # Acceso total para no mezclar el aislamiento con la matriz de permisos.
    for module in Module.objects.all():
        RolePermission.objects.update_or_create(
            role=role, module=module,
            defaults={"can_view": True, "can_create": True, "can_edit": True,
                      "can_delete": True, "can_export": True, "can_approve": True},
        )
    user = User.objects.create_user(
        email=email, password=password, first_name="Usuario", last_name="Prueba",
        role=role, institution=institution,
    )
    invalidate_permission_cache()
    return user


def seed_modules():
    from core.configuration.modules import iter_modules
    from core.users.models import Module

    creados = {}
    for entry in iter_modules():
        parent = creados.get(entry["parent"]) if entry["parent"] else None
        module, _ = Module.objects.update_or_create(
            code=entry["code"],
            defaults={"name": entry["name"], "parent": parent, "icon": entry["icon"],
                      "url_name": entry["url_name"] or "", "group": entry["group"],
                      "order": entry["order"], "is_active": True},
        )
        creados[entry["code"]] = module


class ScopingPathTests(TestCase):
    """La ruta hacia la institucion debe ser la correcta, no cualquiera."""

    def test_ruta_directa(self):
        from core.students.models import Student

        self.assertEqual(institution_path(Student), "institution")

    def test_ruta_por_ano_lectivo(self):
        from core.academic.models import Group

        self.assertEqual(institution_path(Group), "school_year__institution")

    def test_ruta_de_dos_saltos(self):
        from core.academic.models import Subject

        self.assertEqual(institution_path(Subject), "area__school_year__institution")

    def test_no_se_usa_el_campo_de_auditoria(self):
        """
        created_by apunta a quien creo el registro, no a su institucion dueña.

        Seguir esa ruta acotaria los datos por el usuario que los cargo, que
        es un resultado incorrecto.
        """
        from core.academic.models import Grade

        path = institution_path(Grade)
        self.assertNotIn("created_by", path)
        self.assertEqual(path, "level__institution")

    def test_los_modelos_transversales_no_se_acotan(self):
        from core.users.models import Role

        self.assertIsNone(institution_path(Role))


class ActiveInstitutionTests(TestCase):
    """La institucion activa manda sobre `current()`."""

    @classmethod
    def setUpTestData(cls):
        cls.uno, cls.year_uno, _ = build_institution("100000000001", "Institucion Uno", default=True)
        cls.dos, cls.year_dos, _ = build_institution("100000000002", "Institucion Dos")

    def test_sin_institucion_activa_se_usa_la_predeterminada(self):
        from ..models import Institution

        self.assertEqual(Institution.current().pk, self.uno.pk)

    def test_el_contexto_cambia_la_institucion_actual(self):
        from ..models import Institution

        with use_institution(self.dos):
            self.assertEqual(Institution.current().pk, self.dos.pk)
        self.assertEqual(Institution.current().pk, self.uno.pk)

    def test_el_ano_lectivo_sigue_a_la_institucion(self):
        from core.academic.models import SchoolYear

        with use_institution(self.dos):
            self.assertEqual(SchoolYear.current().pk, self.year_dos.pk)
        with use_institution(self.uno):
            self.assertEqual(SchoolYear.current().pk, self.year_uno.pk)

    def test_el_contexto_se_restaura_al_salir(self):
        with use_institution(self.dos):
            with use_institution(self.uno):
                self.assertEqual(get_active_institution().pk, self.uno.pk)
            self.assertEqual(get_active_institution().pk, self.dos.pk)
        self.assertIsNone(get_active_institution())

    def test_la_consulta_se_acota(self):
        from core.students.models import Student

        build_student(self.uno, "900000001")
        build_student(self.uno, "900000002")
        build_student(self.dos, "900000003")

        self.assertEqual(scope_queryset(Student.objects.all(), self.uno).count(), 2)
        self.assertEqual(scope_queryset(Student.objects.all(), self.dos).count(), 1)
        self.assertEqual(Student.objects.count(), 3)

    def test_sin_institucion_no_se_filtra(self):
        from core.students.models import Student

        build_student(self.uno, "900000004")
        self.assertEqual(scope_queryset(Student.objects.all(), None).count(), 1)


class LoginInstitutionTests(TestCase):
    """El selector del ingreso y sus reglas de acceso."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.uno, _, _ = build_institution("200000000001", "Institucion Uno", default=True)
        cls.dos, _, _ = build_institution("200000000002", "Institucion Dos")
        cls.usuario_uno = build_user("usuario.uno@test.local", cls.uno, "RECTOR")
        cls.super_admin = build_user("super@test.local", cls.uno, "SUPER_ADMIN")

    def _login(self, email, institution=None, password="Prueba123*"):
        client = Client()
        datos = {"identifier": email, "password": password}
        if institution is not None:
            datos["institution"] = institution.pk
        response = client.post("/auth/login/", datos)
        return client, response

    def test_el_selector_aparece_con_varias_instituciones(self):
        response = Client().get("/auth/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_institution_selector"])
        self.assertEqual(len(response.context["institutions"]), 2)

    def test_el_selector_no_aparece_con_una_sola(self):
        from ..models import Institution

        Institution.objects.filter(pk=self.dos.pk).update(is_active=False)
        response = Client().get("/auth/login/")
        self.assertFalse(response.context["show_institution_selector"])
        Institution.objects.filter(pk=self.dos.pk).update(is_active=True)

    def test_ingreso_a_la_institucion_propia(self):
        client, response = self._login("usuario.uno@test.local", self.uno)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.session[SESSION_KEY], self.uno.pk)

    def test_el_selector_no_es_obligatorio(self):
        """
        Elegir institucion es opcional: sin elegir, cada usuario entra a la
        suya. Marcarlo obligatorio dejaba a la gente fuera del sistema.
        """
        client, response = self._login("usuario.uno@test.local", institution=None)
        self.assertEqual(response.status_code, 302, "Debe poder entrar sin elegir institucion")
        self.assertEqual(client.session[SESSION_KEY], self.uno.pk)

    def test_el_super_admin_sin_elegir_entra_a_administrar_la_plataforma(self):
        """
        No elegir institucion no es un error: el Super Administrador entra a
        administrar la plataforma. La sesion queda sin institucion, que es lo
        que distingue ese modo de haber entrado a una en concreto.
        """
        client, response = self._login("super@test.local", institution=None)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_el_super_admin_que_elige_institucion_entra_a_ella(self):
        client, response = self._login("super@test.local", self.dos)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.session[SESSION_KEY], self.dos.pk)

    def test_enviar_el_selector_vacio_equivale_a_no_elegir(self):
        """El navegador envia la cadena vacia cuando no se toca el desplegable."""
        client = Client()
        response = client.post(
            "/auth/login/",
            {"identifier": "usuario.uno@test.local", "password": "Prueba123*", "institution": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.session[SESSION_KEY], self.uno.pk)

    def test_no_se_puede_ingresar_a_una_institucion_ajena(self):
        client, response = self._login("usuario.uno@test.local", self.dos)
        self.assertEqual(response.status_code, 403)
        self.assertIn("no pertenece", response.context["error"])
        self.assertNotIn("_auth_user_id", client.session)

    def test_el_super_admin_entra_a_cualquiera(self):
        for institution in (self.uno, self.dos):
            with self.subTest(institution=institution.name):
                client, response = self._login("super@test.local", institution)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(client.session[SESSION_KEY], institution.pk)

    def test_una_institucion_inexistente_se_rechaza(self):
        client = Client()
        response = client.post(
            "/auth/login/",
            {"identifier": "usuario.uno@test.local", "password": "Prueba123*", "institution": 999999},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("no esta disponible", response.context["error"])

    def test_las_credenciales_invalidas_siguen_fallando(self):
        client, response = self._login("usuario.uno@test.local", self.uno, password="incorrecta")
        self.assertEqual(response.status_code, 401)


class ApiIsolationTests(TestCase):
    """La API solo devuelve datos de la institucion en la que se trabaja."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.uno, _, _ = build_institution("300000000001", "Institucion Uno", default=True)
        cls.dos, _, _ = build_institution("300000000002", "Institucion Dos")
        cls.usuario_uno = build_user("api.uno@test.local", cls.uno, "RECTOR")
        cls.super_admin = build_user("api.super@test.local", cls.uno, "SUPER_ADMIN")
        cls.est_uno = build_student(cls.uno, "800000001")
        build_student(cls.uno, "800000002")
        cls.est_dos = build_student(cls.dos, "800000003")

    def _client(self, email, institution):
        from core.users.models import User

        client = Client()
        client.force_login(User.objects.get(email=email))
        session = client.session
        session["plsge_2fa_verified"] = True
        session[SESSION_KEY] = institution.pk
        session.save()
        return client

    def test_cada_institucion_ve_solo_sus_estudiantes(self):
        client = self._client("api.uno@test.local", self.uno)
        self.assertEqual(client.get("/api/students/").json()["count"], 2)

    def test_el_super_admin_cambia_de_entorno(self):
        cliente_uno = self._client("api.super@test.local", self.uno)
        cliente_dos = self._client("api.super@test.local", self.dos)
        self.assertEqual(cliente_uno.get("/api/students/").json()["count"], 2)
        self.assertEqual(cliente_dos.get("/api/students/").json()["count"], 1)

    def test_no_se_accede_al_detalle_de_otra_institucion(self):
        client = self._client("api.uno@test.local", self.uno)
        response = client.get(f"/api/students/{self.est_dos.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_si_se_ve_el_detalle_propio(self):
        client = self._client("api.uno@test.local", self.uno)
        response = client.get(f"/api/students/{self.est_uno.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_solo_se_ve_la_institucion_en_la_que_se_trabaja(self):
        client = self._client("api.uno@test.local", self.uno)
        data = client.get("/api/institutions/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["code"], "300000000001")

    def test_la_exportacion_tambien_se_acota(self):
        client = self._client("api.uno@test.local", self.uno)
        response = client.get("/api/students/export/", {"format": "csv"})
        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode("utf-8-sig")
        self.assertIn("800000001", contenido)
        self.assertNotIn("800000003", contenido)

    def test_el_super_admin_ve_todas_las_instituciones(self):
        """
        Excepcion deliberada: es quien las administra y las crea.

        Sin esto no podria ni listarlas ni crear una nueva.
        """
        client = self._client("api.super@test.local", self.uno)
        data = client.get("/api/institutions/").json()
        self.assertEqual(data["count"], 2)

    def test_el_super_admin_si_queda_acotado_en_el_resto(self):
        """Ver todas las instituciones no implica ver todos los datos."""
        client = self._client("api.super@test.local", self.uno)
        self.assertEqual(client.get("/api/students/").json()["count"], 2)


class SuperAdminPanelTests(TestCase):
    """Panel del Super Administrador: crear instituciones y cambiar de entorno."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.uno, _, _ = build_institution("400000000001", "Institucion Uno", default=True)
        cls.dos, _, _ = build_institution("400000000002", "Institucion Dos")
        cls.super_admin = build_user("panel.super@test.local", cls.uno, "SUPER_ADMIN")
        cls.rector = build_user("panel.rector@test.local", cls.uno, "RECTOR")

    def _client(self, email, institution=None):
        from core.users.models import User

        client = Client()
        client.force_login(User.objects.get(email=email))
        session = client.session
        session["plsge_2fa_verified"] = True
        session[SESSION_KEY] = (institution or self.uno).pk
        session.save()
        return client

    def test_el_super_admin_abre_el_panel(self):
        response = self._client("panel.super@test.local").get("/institucion/panel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["institutions"]), 2)

    def test_el_panel_esta_cerrado_para_los_demas_perfiles(self):
        response = self._client("panel.rector@test.local").get("/institucion/panel/")
        self.assertEqual(response.status_code, 403)

    def test_crear_desde_la_interfaz_siempre_nace_limpia(self):
        """
        La pagina de creacion no ofrece estructura de ejemplo: la institucion
        se crea solo con los datos que se registran, para que quien la
        administra cargue los suyos.
        """
        from core.academic.models import Group, SchoolYear

        from ..models import Institution

        client = self._client("panel.super@test.local")
        response = client.post("/institucion/panel/nueva/", {
            "code": "400000000003", "name": "Institucion Tres", "short_name": "Tres",
            "city": "Bogota", "nature": "OFICIAL",
            # Aunque se envie, la pagina no arma estructura de ejemplo.
            "bootstrap": "1",
            "admin_email": "rector400000000003@test.local", "admin_password": "Vh4$tRq8Wm",
        })
        self.assertEqual(response.status_code, 302)

        nueva = Institution.objects.get(code="400000000003")
        self.assertFalse(nueva.is_default, "Crear no puede desplazar a la predeterminada")
        self.assertTrue(nueva.is_active)
        self.assertEqual(nueva.city, "Bogota")

        self.assertEqual(nueva.campuses.count(), 0)
        self.assertEqual(nueva.shifts.count(), 0)
        self.assertFalse(SchoolYear.objects.filter(institution=nueva).exists())
        self.assertFalse(Group.objects.filter(school_year__institution=nueva).exists())


    def test_la_institucion_nueva_nace_limpia(self):
        """
        Sin marcar la casilla de ejemplo, la institucion no arrastra ninguna
        estructura: quien la administra carga sus propios datos.
        """
        from core.academic.models import Area, Grade, Group, SchoolYear, Subject

        from ..models import Institution

        client = self._client("panel.super@test.local")
        client.post("/institucion/panel/nueva/", {
            "code": "400000000010", "name": "Institucion Limpia", "city": "Tunja",
            "nature": "OFICIAL", "groups_per_grade": "1",
            # El alta crea siempre el usuario con el que se entra a la institucion.
            "admin_email": "rector.limpia@test.local", "admin_password": "Vh4$tRq8Wm",
        })

        nueva = Institution.objects.get(code="400000000010")
        self.assertEqual(nueva.campuses.count(), 0)
        self.assertEqual(nueva.shifts.count(), 0)
        self.assertEqual(nueva.levels.count(), 0)
        self.assertFalse(SchoolYear.objects.filter(institution=nueva).exists())
        self.assertFalse(Grade.objects.filter(level__institution=nueva).exists())
        self.assertFalse(Group.objects.filter(school_year__institution=nueva).exists())
        self.assertFalse(Area.objects.filter(school_year__institution=nueva).exists())
        self.assertFalse(Subject.objects.filter(area__school_year__institution=nueva).exists())

    def test_la_estructura_de_ejemplo_vive_en_el_servicio(self):
        """
        Sigue disponible para las instituciones de prueba (seed_instituciones),
        pero ya no se ofrece al crear desde la interfaz.
        """
        from core.academic.models import Group, SchoolYear

        from ..services import create_institution

        con_ejemplo, _ = create_institution(
            {"code": "400000000011", "name": "Con ejemplo"}, bootstrap=True
        )
        year = SchoolYear.objects.get(institution=con_ejemplo)
        self.assertEqual(Group.objects.filter(school_year=year).count(), 12)


    def test_la_institucion_limpia_no_muestra_datos_de_otras(self):
        """El aislamiento tiene que sostenerse tambien en una institucion vacia."""
        from ..models import Institution

        build_student(self.uno, "820000001")
        build_student(self.dos, "820000002")

        client = self._client("panel.super@test.local")
        client.post("/institucion/panel/nueva/", {
            "code": "400000000012", "name": "Limpia aislada", "nature": "OFICIAL",
            "admin_email": "rector400000000012@test.local", "admin_password": "Vh4$tRq8Wm",
        })
        limpia = Institution.objects.get(code="400000000012")

        dentro = self._client("panel.super@test.local", institution=limpia)
        for ruta in ("/api/students/", "/api/teachers/", "/api/groups/", "/api/school-years/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(dentro.get(ruta).json()["count"], 0)

    def test_modificar_los_datos_de_una_institucion(self):
        client = self._client("panel.super@test.local")
        response = client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.dos.code, "name": "Institucion Dos Renombrada",
            "city": "Manizales", "rector_name": "Rector Nuevo", "nature": "PRIVADA",
        })
        self.assertEqual(response.status_code, 302)

        self.dos.refresh_from_db()
        self.assertEqual(self.dos.name, "Institucion Dos Renombrada")
        self.assertEqual(self.dos.city, "Manizales")
        self.assertEqual(self.dos.rector_name, "Rector Nuevo")

    def test_modificar_una_no_toca_a_las_demas(self):
        nombre_original = self.uno.name
        client = self._client("panel.super@test.local")
        client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.dos.code, "name": "Solo esta cambia", "city": "Pasto",
        })
        self.uno.refresh_from_db()
        self.assertEqual(self.uno.name, nombre_original)
        self.assertEqual(self.uno.city, "")

    def test_modificar_no_altera_predeterminada_ni_estado(self):
        client = self._client("panel.super@test.local")
        client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.dos.code, "name": "Otro nombre",
        })
        self.dos.refresh_from_db()
        self.uno.refresh_from_db()
        self.assertFalse(self.dos.is_default)
        self.assertTrue(self.dos.is_active)
        self.assertTrue(self.uno.is_default, "La predeterminada no cambia al editar otra")

    def test_no_se_puede_repetir_el_codigo_al_modificar(self):
        client = self._client("panel.super@test.local")
        client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.uno.code, "name": "Intento de choque",
        })
        self.dos.refresh_from_db()
        self.assertEqual(self.dos.code, "400000000002", "El codigo no debe cambiar al chocar")

    def test_los_demas_perfiles_no_modifican_instituciones(self):
        client = self._client("panel.rector@test.local")
        response = client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.dos.code, "name": "Cambio no autorizado",
        })
        self.assertEqual(response.status_code, 403)
        self.dos.refresh_from_db()
        self.assertNotEqual(self.dos.name, "Cambio no autorizado")

    def test_el_panel_entrega_los_datos_de_cada_institucion(self):
        """Cada fila se edita con sus propios datos, no con los de otra."""
        response = self._client("panel.super@test.local").get("/institucion/panel/")
        datos = response.context["institutions_data"]
        self.assertEqual(len(datos), 2)
        self.assertEqual(datos[str(self.uno.pk)]["code"], self.uno.code)
        self.assertEqual(datos[str(self.dos.pk)]["code"], self.dos.code)
        self.assertNotEqual(datos[str(self.uno.pk)]["name"], datos[str(self.dos.pk)]["name"])

    def test_no_se_duplica_una_institucion_existente(self):
        from ..models import Institution

        client = self._client("panel.super@test.local")
        client.post("/institucion/panel/nueva/", {
            "code": "400000000002", "name": "Intento duplicado", "groups_per_grade": "1",
            "admin_email": "rector400000000002@test.local", "admin_password": "Vh4$tRq8Wm",
        })
        self.assertEqual(Institution.objects.filter(code="400000000002").count(), 1)
        self.assertEqual(Institution.objects.get(code="400000000002").name, "Institucion Dos")

    def test_el_codigo_y_el_nombre_son_obligatorios(self):
        from ..models import Institution

        antes = Institution.objects.count()
        client = self._client("panel.super@test.local")
        client.post("/institucion/panel/nueva/", {"code": "", "name": "Sin codigo"})
        self.assertEqual(Institution.objects.count(), antes)

    def test_cambiar_de_institucion_sin_cerrar_sesion(self):
        client = self._client("panel.super@test.local")
        response = client.get(f"/institucion/panel/{self.dos.pk}/ingresar/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.session[SESSION_KEY], self.dos.pk)

    def test_los_demas_perfiles_no_cambian_de_institucion(self):
        client = self._client("panel.rector@test.local")
        response = client.get(f"/institucion/panel/{self.dos.pk}/ingresar/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(client.session[SESSION_KEY], self.uno.pk)

    def test_desactivar_una_institucion(self):
        from ..models import Institution

        client = self._client("panel.super@test.local")
        response = client.post(f"/institucion/panel/{self.dos.pk}/estado/")
        self.assertEqual(response.status_code, 302)
        self.dos.refresh_from_db()
        self.assertFalse(self.dos.is_active)

        # Y una institucion inactiva desaparece del selector de ingreso.
        login = Client().get("/auth/login/")
        codigos = [i.code for i in login.context["institutions"]]
        self.assertNotIn("400000000002", codigos)

        Institution.objects.filter(pk=self.dos.pk).update(is_active=True)

    def test_no_se_desactiva_la_institucion_predeterminada(self):
        client = self._client("panel.super@test.local")
        client.post(f"/institucion/panel/{self.uno.pk}/estado/")
        self.uno.refresh_from_db()
        self.assertTrue(self.uno.is_active, "La predeterminada no se puede desactivar")

    def test_editar_los_datos_no_roba_la_marca_de_predeterminada(self):
        """
        Antes, guardar los datos institucionales marcaba siempre is_default,
        con lo que la institucion en la que se estuviera trabajando le quitaba
        la condicion a la que ya la tenia.
        """
        from ..models import Institution

        client = self._client("panel.super@test.local", institution=self.dos)
        client.post("/institucion/", {
            "code": self.dos.code, "name": "Institucion Dos editada", "nature": "OFICIAL",
        })
        self.dos.refresh_from_db()
        self.uno.refresh_from_db()
        self.assertEqual(self.dos.name, "Institucion Dos editada")
        self.assertFalse(self.dos.is_default)
        self.assertTrue(self.uno.is_default, "La predeterminada no debe cambiar al editar otra")


class InstitutionFormPageTests(TestCase):
    """
    La pagina de crear y modificar usa el mismo formulario que Datos
    Institucionales, en blanco al crear y cargado al modificar.
    """

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.uno, _, _ = build_institution("600000000001", "Institucion Uno", default=True)
        cls.dos, _, _ = build_institution("600000000002", "Institucion Dos")
        cls.dos.city = "Cartagena"
        cls.dos.rector_name = "Rector Dos"
        cls.dos.mission = "Mision propia de la dos."
        cls.dos.save()
        cls.super_admin = build_user("form.super@test.local", cls.uno, "SUPER_ADMIN")
        cls.rector = build_user("form.rector@test.local", cls.uno, "RECTOR")

    def _client(self, email):
        from core.users.models import User

        client = Client()
        client.force_login(User.objects.get(email=email))
        session = client.session
        session["plsge_2fa_verified"] = True
        session[SESSION_KEY] = self.uno.pk
        session.save()
        return client

    def test_el_formulario_de_creacion_sale_en_blanco(self):
        response = self._client("form.super@test.local").get("/institucion/panel/nueva/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_new"])
        self.assertIsNone(response.context["entity"])

    def test_el_formulario_de_modificacion_carga_sus_datos(self):
        response = self._client("form.super@test.local").get(
            f"/institucion/panel/{self.dos.pk}/editar/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_new"])
        entidad = response.context["entity"]
        self.assertEqual(entidad.pk, self.dos.pk)
        self.assertEqual(entidad.city, "Cartagena")
        self.assertEqual(entidad.mission, "Mision propia de la dos.")

    def test_el_formulario_tiene_los_campos_de_datos_institucionales(self):
        """Ambas pantallas comparten la misma plantilla de campos."""
        import re

        client = self._client("form.super@test.local")
        panel = client.get("/institucion/panel/nueva/").content.decode("utf-8", "ignore")
        perfil = client.get("/institucion/").content.decode("utf-8", "ignore")

        def campos(html):
            omitir = {"csrfmiddlewaretoken", "viewport", "description", "robots"}
            return {n for n in re.findall(r'name="([a-z_]+)"', html)} - omitir

        # El alta tiene ademas el bloque del usuario de ingreso, que Datos
        # Institucionales no necesita: la institucion propia ya tiene usuarios.
        acceso = {n for n in campos(panel) if n.startswith("admin_")}
        self.assertEqual(campos(panel) - acceso, campos(perfil))
        self.assertTrue(acceso, "Falta el bloque del usuario de ingreso")
        # Y estan los que importan, incluidos archivos y textos largos.
        for campo in ("code", "name", "nit", "mission", "vision", "logo", "seal",
                      "rector_signature", "primary_color"):
            self.assertIn(campo, campos(panel), f"Falta el campo {campo}")

    def test_modificar_guarda_los_campos_largos(self):
        client = self._client("form.super@test.local")
        client.post(f"/institucion/panel/{self.dos.pk}/editar/", {
            "code": self.dos.code, "name": "Institucion Dos", "city": "Sincelejo",
            "mission": "Nueva mision", "vision": "Nueva vision", "motto": "Nuevo lema",
        })
        self.dos.refresh_from_db()
        self.assertEqual(self.dos.city, "Sincelejo")
        self.assertEqual(self.dos.mission, "Nueva mision")
        self.assertEqual(self.dos.vision, "Nueva vision")

    def test_los_demas_perfiles_no_abren_el_formulario(self):
        client = self._client("form.rector@test.local")
        self.assertEqual(client.get("/institucion/panel/nueva/").status_code, 403)
        self.assertEqual(
            client.get(f"/institucion/panel/{self.dos.pk}/editar/").status_code, 403
        )


class InstitutionPasswordTests(TestCase):
    """El Super Administrador administra los accesos de cada institucion."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.uno, _, _ = build_institution("700000000001", "Institucion Uno", default=True)
        cls.dos, _, _ = build_institution("700000000002", "Institucion Dos")
        cls.super_admin = build_user("clave.super@test.local", cls.uno, "SUPER_ADMIN")
        cls.rector_dos = build_user("clave.rector@test.local", cls.dos, "RECTOR")

    def _client(self, email):
        from core.users.models import User

        client = Client()
        client.force_login(User.objects.get(email=email))
        session = client.session
        session["plsge_2fa_verified"] = True
        session[SESSION_KEY] = self.uno.pk
        session.save()
        return client

    def test_los_accesos_se_listan_por_institucion(self):
        response = self._client("clave.super@test.local").get(
            f"/institucion/panel/{self.dos.pk}/usuarios/"
        )
        self.assertEqual(response.status_code, 200)
        correos = {u.email for u in response.context["users"]}
        self.assertIn("clave.rector@test.local", correos)
        self.assertNotIn("clave.super@test.local", correos, "Solo los de esa institucion")

    def test_asignar_una_contrasena_concreta(self):
        from core.users.models import User

        client = self._client("clave.super@test.local")
        response = client.post(
            f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/",
            {"password": "ClaveNueva2026*", "must_change": ""},
        )
        self.assertEqual(response.status_code, 302)

        usuario = User.objects.get(pk=self.rector_dos.pk)
        self.assertTrue(usuario.check_password("ClaveNueva2026*"))
        self.assertFalse(usuario.check_password("Prueba123*"), "La anterior deja de servir")

    def test_generar_la_contrasena_cuando_se_deja_vacia(self):
        from core.users.models import User, UserCredentialCertificate

        client = self._client("clave.super@test.local")
        client.post(f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/", {"password": ""})

        certificado = UserCredentialCertificate.objects.filter(
            user=self.rector_dos
        ).order_by("-created_at").first()
        self.assertIsNotNone(certificado, "Debe quedar constancia de la credencial")
        usuario = User.objects.get(pk=self.rector_dos.pk)
        self.assertTrue(usuario.check_password(certificado.plain_password))

    def test_la_contrasena_debil_se_rechaza(self):
        from core.users.models import User

        client = self._client("clave.super@test.local")
        client.post(
            f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/", {"password": "123"}
        )
        usuario = User.objects.get(pk=self.rector_dos.pk)
        self.assertFalse(usuario.check_password("123"))
        self.assertTrue(usuario.check_password("Prueba123*"), "La anterior se conserva")

    def test_el_cambio_desbloquea_la_cuenta(self):
        from django.utils import timezone

        from core.users.models import User

        self.rector_dos.failed_login_attempts = 5
        self.rector_dos.locked_until = timezone.now() + dt.timedelta(minutes=15)
        self.rector_dos.save(update_fields=["failed_login_attempts", "locked_until"])

        client = self._client("clave.super@test.local")
        client.post(
            f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/",
            {"password": "OtraClave2026*"},
        )
        usuario = User.objects.get(pk=self.rector_dos.pk)
        self.assertEqual(usuario.failed_login_attempts, 0)
        self.assertIsNone(usuario.locked_until)

    def test_el_cambio_queda_en_la_bitacora(self):
        from core.audit.models import AuditLog

        client = self._client("clave.super@test.local")
        client.post(
            f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/",
            {"password": "Auditada2026*"},
        )
        self.assertTrue(
            AuditLog.objects.filter(
                module="institutions.panel", description__icontains="Contrasena restablecida"
            ).exists()
        )

    def test_los_demas_perfiles_no_cambian_contrasenas(self):
        from core.users.models import User

        otro = build_user("clave.otro@test.local", self.uno, "COORDINADOR")
        client = Client()
        client.force_login(otro)
        session = client.session
        session["plsge_2fa_verified"] = True
        session.save()

        response = client.post(
            f"/institucion/panel/usuarios/{self.rector_dos.pk}/clave/",
            {"password": "Intruso2026*"},
        )
        self.assertEqual(response.status_code, 403)
        usuario = User.objects.get(pk=self.rector_dos.pk)
        self.assertFalse(usuario.check_password("Intruso2026*"))

    def test_los_demas_perfiles_no_ven_los_accesos(self):
        from core.users.models import User

        client = Client()
        client.force_login(User.objects.get(email="clave.rector@test.local"))
        session = client.session
        session["plsge_2fa_verified"] = True
        session.save()
        response = client.get(f"/institucion/panel/{self.dos.pk}/usuarios/")
        self.assertEqual(response.status_code, 403)


class BootstrapServiceTests(TestCase):
    """El arranque deja la institucion en condiciones de operar."""

    def test_una_institucion_sin_arranque_queda_vacia(self):
        from core.academic.models import SchoolYear

        from ..services import create_institution

        institution, creada = create_institution(
            {"code": "500000000001", "name": "Sin arranque"}, bootstrap=False
        )
        self.assertTrue(creada)
        self.assertFalse(SchoolYear.objects.filter(institution=institution).exists())

    def test_el_arranque_crea_la_estructura_completa(self):
        from core.academic.models import Area, Grade, Group, SchoolYear, Subject

        from ..services import create_institution

        institution, _ = create_institution(
            {"code": "500000000002", "name": "Con arranque", "city": "Cali"},
            bootstrap=True, groups_per_grade=2,
        )
        year = SchoolYear.objects.get(institution=institution)
        self.assertEqual(year.periods.count(), 4)
        self.assertEqual(year.grading_scales.count(), 1)
        self.assertEqual(year.grading_scales.first().levels.count(), 4)
        self.assertEqual(institution.levels.count(), 4)
        self.assertEqual(Grade.objects.filter(level__institution=institution).count(), 12)
        self.assertEqual(Group.objects.filter(school_year=year).count(), 24)
        self.assertEqual(Area.objects.filter(school_year=year).count(), 6)
        self.assertEqual(Subject.objects.filter(area__school_year=year).count(), 7)

    def test_el_arranque_es_idempotente(self):
        from core.academic.models import Group, SchoolYear

        from ..services import bootstrap_institution, create_institution

        institution, _ = create_institution(
            {"code": "500000000003", "name": "Idempotente"}, bootstrap=True
        )
        year = SchoolYear.objects.get(institution=institution)
        antes = Group.objects.filter(school_year=year).count()

        bootstrap_institution(institution, year=year.year)
        self.assertEqual(Group.objects.filter(school_year=year).count(), antes)
        self.assertEqual(SchoolYear.objects.filter(institution=institution).count(), 1)

    def test_el_codigo_es_obligatorio(self):
        from ..services import create_institution

        with self.assertRaises(ValueError):
            create_institution({"name": "Sin codigo"})