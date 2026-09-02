"""
Pruebas del usuario de ingreso que se crea junto con la institucion.

Lo que se protege aqui: que una institucion nueva nunca quede sin forma de
entrar, que la contrasena pase la politica de seguridad antes de crear nada, y
que ese usuario solo alcance su propia institucion.
"""
from __future__ import annotations

from django.test import Client, TestCase

from .test_multi_institucion import build_institution, build_user, seed_modules

from ..models import Institution
from ..services import create_institution, create_institution_admin


class CreateInstitutionAdminTests(TestCase):
    def setUp(self):
        self.institution, _ = create_institution(
            {"code": "700000000001", "name": "Colegio Nuevo"}
        )

    def test_crea_el_usuario_con_la_institucion_y_el_perfil_pedidos(self):
        from core.users.models import Role

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})

        usuario, clave = create_institution_admin(
            self.institution,
            {
                "admin_email": "rector@colegionuevo.edu.co",
                "admin_first_name": "Ana",
                "admin_last_name": "Restrepo",
                "admin_password": "Vh4$tRq8Wm",
                "admin_role": "RECTOR",
            },
        )

        self.assertEqual(usuario.institution, self.institution)
        self.assertEqual(usuario.role.code, "RECTOR")
        self.assertEqual(clave, "Vh4$tRq8Wm")
        self.assertTrue(usuario.check_password("Vh4$tRq8Wm"))

    def test_genera_la_contrasena_cuando_se_deja_vacia(self):
        from core.users.models import Role

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})

        usuario, clave = create_institution_admin(
            self.institution, {"admin_email": "rector2@colegionuevo.edu.co"}
        )

        self.assertTrue(clave)
        self.assertTrue(usuario.check_password(clave))

    def test_deja_certificado_de_credenciales(self):
        from core.users.models import Role, UserCredentialCertificate

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})

        usuario, clave = create_institution_admin(
            self.institution, {"admin_email": "rector3@colegionuevo.edu.co"}
        )

        certificado = UserCredentialCertificate.objects.get(user=usuario)
        self.assertEqual(certificado.plain_password, clave)

    def test_rechaza_una_contrasena_que_no_cumple_la_politica(self):
        from core.users.models import Role, User

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})

        with self.assertRaises(ValueError):
            create_institution_admin(
                self.institution,
                {"admin_email": "rector4@colegionuevo.edu.co", "admin_password": "12345"},
            )
        self.assertFalse(User.objects.filter(email="rector4@colegionuevo.edu.co").exists())

    def test_rechaza_el_correo_repetido(self):
        from core.users.models import Role

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})
        create_institution_admin(
            self.institution, {"admin_email": "repetido@colegionuevo.edu.co"}
        )

        with self.assertRaises(ValueError):
            create_institution_admin(
                self.institution, {"admin_email": "REPETIDO@colegionuevo.edu.co"}
            )

    def test_no_permite_crear_un_super_administrador(self):
        from core.users.models import Role

        Role.objects.get_or_create(code="SUPER_ADMIN", defaults={"name": "Super Admin"})

        with self.assertRaises(ValueError):
            create_institution_admin(
                self.institution,
                {"admin_email": "colado@colegionuevo.edu.co", "admin_role": "SUPER_ADMIN"},
            )

    def test_exige_el_correo(self):
        with self.assertRaises(ValueError):
            create_institution_admin(self.institution, {"admin_email": "  "})


class AltaDesdeElPanelTests(TestCase):
    """El alta desde el panel crea institucion y acceso en una sola operacion."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.propia, _, _ = build_institution("710000000001", "Institucion Base", default=True)
        cls.super_admin = build_user("super@test.local", cls.propia, "SUPER_ADMIN")

        from core.users.models import Role

        Role.objects.get_or_create(code="RECTOR", defaults={"name": "Rector"})

    def _cliente(self):
        client = Client()
        client.force_login(self.super_admin)
        return client

    def _datos(self, **extra):
        datos = {
            "code": "710000000002",
            "name": "Colegio Creado Desde El Panel",
            "admin_email": "rector.panel@test.local",
            "admin_password": "Vh4$tRq8Wm",
            "admin_role": "RECTOR",
        }
        datos.update(extra)
        return datos

    def test_crea_la_institucion_con_su_usuario_de_ingreso(self):
        from core.users.models import User

        respuesta = self._cliente().post("/institucion/panel/nueva/", self._datos())

        self.assertEqual(respuesta.status_code, 302)
        institucion = Institution.objects.get(code="710000000002")
        usuario = User.objects.get(email="rector.panel@test.local")
        self.assertEqual(usuario.institution, institucion)

    def test_una_contrasena_invalida_no_deja_institucion_a_medias(self):
        from core.users.models import User

        self._cliente().post("/institucion/panel/nueva/", self._datos(admin_password="12345"))

        self.assertFalse(Institution.objects.filter(code="710000000002").exists())
        self.assertFalse(User.objects.filter(email="rector.panel@test.local").exists())

    def test_un_correo_repetido_no_deja_institucion_a_medias(self):
        self._cliente().post("/institucion/panel/nueva/", self._datos())
        self._cliente().post(
            "/institucion/panel/nueva/", self._datos(code="710000000003")
        )

        self.assertFalse(Institution.objects.filter(code="710000000003").exists())

    def test_la_institucion_nueva_no_desplaza_a_la_predeterminada(self):
        self._cliente().post("/institucion/panel/nueva/", self._datos())

        self.propia.refresh_from_db()
        self.assertTrue(self.propia.is_default)
        self.assertFalse(Institution.objects.get(code="710000000002").is_default)


class MenuSinFugaEntreInstitucionesTests(TestCase):
    """El encabezado del menu no puede mostrar el ano lectivo de otra."""

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.con_datos, cls.year, _ = build_institution("720000000001", "Con Datos", default=True)
        cls.limpia, _ = create_institution({"code": "720000000002", "name": "Limpia"})
        cls.usuario = build_user("rector.limpia@test.local", cls.limpia, "RECTOR")

    def test_una_institucion_sin_ano_lectivo_no_muestra_el_de_otra(self):
        client = Client()
        client.force_login(self.usuario)

        respuesta = client.get("/dashboard/")

        self.assertIsNone(respuesta.context["active_school_year"])


class EncabezadoDeReportesTests(TestCase):
    """Renombrar la institucion no puede dejar los boletines con el nombre viejo."""

    def setUp(self):
        from core.configuration.models import ReportHeader

        from ..services import header_lines

        self.institution, _ = create_institution(
            {"code": "730000000001", "name": "Colegio Antiguo", "nit": "900111-1",
             "address": "Calle 1", "city": "Cali", "phone": "111"}
        )
        self.header = ReportHeader.objects.create(
            institution=self.institution, name="Encabezado principal",
            is_default=True, **header_lines(self.institution)
        )

    def test_al_renombrar_la_institucion_se_actualiza_el_encabezado(self):
        from ..services import update_institution

        update_institution(self.institution, {"name": "Colegio Nuevo Nombre"})

        self.header.refresh_from_db()
        self.assertEqual(self.header.line_1, "COLEGIO NUEVO NOMBRE")

    def test_al_cambiar_el_codigo_se_actualiza_la_linea_del_dane(self):
        from ..services import update_institution

        update_institution(self.institution, {"name": "Colegio Antiguo", "code": "730000000009"})

        self.header.refresh_from_db()
        self.assertIn("730000000009", self.header.line_3)

    def test_respeta_las_lineas_escritas_a_mano(self):
        from ..services import update_institution

        self.header.line_1 = "TEXTO REDACTADO POR LA SECRETARIA"
        self.header.save(update_fields=["line_1"])

        update_institution(self.institution, {"name": "Colegio Nuevo Nombre"})

        self.header.refresh_from_db()
        self.assertEqual(self.header.line_1, "TEXTO REDACTADO POR LA SECRETARIA")


class MenuDelSuperAdministradorTests(TestCase):
    """
    El Super Administrador administra los datos de cualquier institucion desde
    el Panel de Instituciones, no desde Datos Institucionales.
    """

    @classmethod
    def setUpTestData(cls):
        seed_modules()
        cls.institution, _, _ = build_institution("740000000001", "Institucion", default=True)
        cls.super_admin = build_user("super.menu@test.local", cls.institution, "SUPER_ADMIN")
        cls.rector = build_user("rector.menu@test.local", cls.institution, "RECTOR")

    def _modulos(self, usuario):
        client = Client()
        client.force_login(usuario)
        respuesta = client.get("/dashboard/")
        return {
            hijo["code"]
            for grupo in respuesta.context["nav_groups"]
            for item in grupo["items"]
            for hijo in item["children"]
        }

    def test_el_super_administrador_no_ve_datos_institucionales(self):
        self.assertNotIn("institutions.profile", self._modulos(self.super_admin))

    def test_el_super_administrador_si_ve_el_panel_de_instituciones(self):
        self.assertIn("institutions.panel", self._modulos(self.super_admin))

    def test_los_demas_perfiles_siguen_viendo_datos_institucionales(self):
        self.assertIn("institutions.profile", self._modulos(self.rector))
