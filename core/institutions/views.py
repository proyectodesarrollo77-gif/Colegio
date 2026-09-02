"""Vistas HTML del modulo institucional."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote
from core.audit.services import register_audit

from .context import SESSION_KEY as INSTITUTION_SESSION_KEY
from .models import Campus, Institution, InstitutionalCalendar, Shift


class InstitutionProfileView(ModulePageView):
    template_name = "institutions/profile.html"
    module_code = "institutions.profile"
    title = "Datos Institucionales"
    subtitle = "Informacion oficial de la institucion usada en reportes y certificados."
    icon = "building"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = Institution.current()
        context.update(
            {
                "entity": institution,
                "campuses": Campus.objects.filter(institution=institution) if institution else [],
                "shifts": Shift.objects.filter(institution=institution) if institution else [],
                "calendar_dates": (
                    InstitutionalCalendar.objects.filter(institution=institution).order_by("start_date")[:20]
                    if institution
                    else []
                ),
                "nature_choices": Institution.NATURE_CHOICES,
                "calendar_choices": Institution.CALENDAR_CHOICES,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        institution = Institution.current()
        creando = institution is None
        if creando:
            institution = Institution(code=request.POST.get("code") or "000000000000", is_default=True)

        text_fields = [
            "code", "name", "short_name", "nit", "resolution", "nature", "calendar",
            "country", "department", "city", "address", "phone", "email", "website",
            "rector_name", "rector_document", "secretary_name", "motto", "mission",
            "vision", "primary_color", "accent_color",
        ]
        for name in text_fields:
            if name in request.POST:
                setattr(institution, name, request.POST.get(name, "").strip())

        for file_field in ["logo", "seal", "rector_signature", "secretary_signature"]:
            if request.FILES.get(file_field):
                setattr(institution, file_field, request.FILES[file_field])

        # Solo la primera institucion nace como predeterminada. Editar los
        # datos de una institucion no puede arrebatarle esa condicion a otra:
        # se cambia de forma explicita desde el Panel de Instituciones.
        if creando:
            institution.is_default = True
        institution.updated_by = request.user
        institution.save()
        messages.success(request, "Datos institucionales actualizados correctamente.")
        return redirect("institutions:profile")


class InstitutionPanelView(ModulePageView):
    """
    Panel del Super Administrador: administra la plataforma completa.

    Es la unica pantalla que ve todas las instituciones a la vez. Desde aqui
    se crean, se activan o desactivan, y se entra a cualquiera de ellas sin
    cerrar la sesion.
    """

    template_name = "institutions/panel.html"
    module_code = "institutions.panel"
    title = "Panel de Instituciones"
    subtitle = "Administre todas las instituciones educativas de la plataforma."
    icon = "building"

    def dispatch(self, request, *args, **kwargs):
        # Doble control: el permiso del modulo y, ademas, el perfil. Este panel
        # cruza la frontera entre instituciones, asi que no basta con el
        # permiso: se exige explicitamente ser Super Administrador.
        if request.user.is_authenticated and not request.user.is_super_admin:
            raise PermissionDenied("Solo el Super Administrador puede administrar las instituciones.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from .services import institution_summary

        context = super().get_context_data(**kwargs)
        activa = Institution.current()
        instituciones = []
        for institution in Institution.objects.filter(deleted_at__isnull=True).order_by(
            "-is_default", "-is_active", "name"
        ):
            instituciones.append({
                "entity": institution,
                "summary": institution_summary(institution),
                "is_active_session": activa is not None and institution.pk == activa.pk,
                # Datos para prellenar el formulario de edicion sin volver al
                # servidor: cada institucion se edita con los suyos.
                "form": {
                    "pk": institution.pk,
                    "code": institution.code,
                    "name": institution.name,
                    "short_name": institution.short_name,
                    "nit": institution.nit,
                    "resolution": institution.resolution,
                    "nature": institution.nature,
                    "calendar": institution.calendar,
                    "country": institution.country,
                    "department": institution.department,
                    "city": institution.city,
                    "address": institution.address,
                    "phone": institution.phone,
                    "email": institution.email,
                    "website": institution.website,
                    "rector_name": institution.rector_name,
                    "rector_document": institution.rector_document,
                    "secretary_name": institution.secretary_name,
                    "motto": institution.motto,
                },
            })
        context.update({
            "institutions": instituciones,
            "institutions_data": {str(i["form"]["pk"]): i["form"] for i in instituciones},
            "active_institution": activa,
            "nature_choices": Institution.NATURE_CHOICES,
            "calendar_choices": Institution.CALENDAR_CHOICES,
            "total_students": sum(i["summary"]["students"] for i in instituciones),
            "total_users": sum(i["summary"]["users"] for i in instituciones),
        })
        return context

    def post(self, request, *args, **kwargs):
        """Crea una institucion. Por defecto nace limpia, sin datos."""
        from .services import create_institution

        datos = _institution_form(request)
        if not datos["code"].strip() or not datos["name"].strip():
            messages.error(request, "El codigo DANE y el nombre son obligatorios.")
            return redirect("institutions:panel")

        con_ejemplo = request.POST.get("bootstrap") == "1"
        try:
            institution, creada = create_institution(
                datos,
                user=request.user,
                bootstrap=con_ejemplo,
                groups_per_grade=int(request.POST.get("groups_per_grade") or 1),
            )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("institutions:panel")

        if not creada:
            messages.warning(
                request, f"Ya existe una institucion con el codigo {institution.code}: {institution.name}."
            )
            return redirect("institutions:panel")

        register_audit(
            user=request.user, action="CREATE", module="institutions.panel",
            instance=institution, request=request,
            description=f"Institucion creada: {institution.name}",
        )
        if con_ejemplo:
            messages.success(
                request,
                f"Institucion '{institution.name}' creada con estructura academica de ejemplo.",
            )
        else:
            messages.success(
                request,
                f"Institucion '{institution.name}' creada limpia, sin datos. "
                "Entre a ella para cargar su ano lectivo, grados y estudiantes.",
            )
        return redirect("institutions:panel")


def _institution_form(request):
    """Campos de institucion recibidos del formulario del panel."""
    from .services import EDITABLE_FIELDS

    campos = ("code",) + EDITABLE_FIELDS + ("mission", "vision", "primary_color", "accent_color")
    return {nombre: request.POST.get(nombre, "") for nombre in campos}


def _admin_form(request):
    """Campos del usuario de ingreso que acompanan al alta de una institucion."""
    campos = (
        "admin_first_name", "admin_last_name", "admin_email",
        "admin_password", "admin_role",
    )
    datos = {nombre: request.POST.get(nombre, "") for nombre in campos}
    datos["admin_must_change"] = request.POST.get("admin_must_change") == "1"
    return datos


def _apply_files(institution, request):
    """Guarda los archivos institucionales que vengan en el formulario."""
    for campo in ("logo", "seal", "rector_signature", "secretary_signature"):
        if request.FILES.get(campo):
            setattr(institution, campo, request.FILES[campo])


class InstitutionFormView(ModulePageView):
    """
    Crear una institucion nueva o modificar una existente.

    Usa el mismo formulario de Datos Institucionales, para que administrar una
    institucion desde el panel se vea y funcione igual que administrar la
    propia. Al crear, los campos salen en blanco; al modificar, cargados con
    los datos de esa institucion y solo de esa.
    """

    template_name = "institutions/form.html"
    module_code = "institutions.panel"
    icon = "building"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_super_admin:
            raise PermissionDenied("Solo el Super Administrador puede administrar las instituciones.")
        return super().dispatch(request, *args, **kwargs)

    @property
    def instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(Institution, pk=pk, deleted_at__isnull=True)

    @property
    def title(self):
        entidad = self.instance
        return f"Modificar {entidad.short_name or entidad.name}" if entidad else "Nueva institucion educativa"

    @property
    def subtitle(self):
        if self.instance:
            return "Los datos que ve son unicamente de esta institucion."
        return "Los campos salen en blanco. La institucion nace limpia, sin datos de otras."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entidad = self.instance
        context.update({
            "entity": entidad,
            "is_new": entidad is None,
            "nature_choices": Institution.NATURE_CHOICES,
            "calendar_choices": Institution.CALENDAR_CHOICES,
            "admin_roles": self._admin_roles(),
            "breadcrumbs": [
                {"label": "Panel de Instituciones", "url": reverse("institutions:panel")},
                {"label": "Nueva" if entidad is None else entidad.name},
            ],
        })
        return context

    @staticmethod
    def _admin_roles():
        """Perfiles ofrecidos para el usuario de ingreso, con su nombre real."""
        from core.users.models import Role

        from .services import ADMIN_ROLES

        nombres = dict(Role.objects.filter(code__in=ADMIN_ROLES).values_list("code", "name"))
        return [(codigo, nombres.get(codigo, codigo.title())) for codigo in ADMIN_ROLES]

    def post(self, request, *args, **kwargs):
        from .services import (
            create_institution,
            create_institution_admin,
            update_institution,
        )

        entidad = self.instance
        datos = _institution_form(request)

        if not (datos.get("name") or "").strip():
            messages.error(request, "El nombre de la institucion es obligatorio.")
            return redirect(request.path)

        if entidad is None:
            codigo = (datos.get("code") or "").strip()
            if not codigo:
                messages.error(request, "El codigo DANE es obligatorio.")
                return redirect(request.path)

            repetida = Institution.objects.filter(code=codigo).first()
            if repetida is not None:
                messages.warning(
                    request,
                    f"Ya existe una institucion con el codigo {repetida.code}: {repetida.name}.",
                )
                return redirect("institutions:panel")

            # La institucion y su usuario de ingreso se crean juntos: si la
            # contrasena no pasa la politica, no debe quedar una institucion
            # a la que nadie puede entrar.
            try:
                with transaction.atomic():
                    entidad, _ = create_institution(datos, user=request.user, bootstrap=False)
                    _apply_files(entidad, request)
                    entidad.save()
                    acceso, clave = create_institution_admin(
                        entidad, _admin_form(request), user=request.user
                    )
            except ValueError as error:
                messages.error(request, str(error))
                return redirect(request.path)

            register_audit(
                user=request.user, action="CREATE", module="institutions.panel",
                instance=entidad, request=request,
                description=f"Institucion creada: {entidad.name} (acceso: {acceso.email})",
            )
            messages.success(
                request,
                f"Institucion '{entidad.name}' creada limpia. Entre a ella para cargar "
                "su ano lectivo, grados y estudiantes.",
            )
            messages.success(
                request,
                f"Acceso de {entidad.name} - usuario: {acceso.email} - contrasena: {clave} "
                "(queda en Usuarios > Certificados de Usuario y Contrasena).",
            )
        else:
            try:
                update_institution(entidad, datos, user=request.user)
            except ValueError as error:
                messages.error(request, str(error))
                return redirect(request.path)
            _apply_files(entidad, request)
            entidad.save()
            register_audit(
                user=request.user, action="UPDATE", module="institutions.panel",
                instance=entidad, request=request,
                description=f"Datos actualizados de la institucion {entidad.name}",
            )
            messages.success(request, f"Datos de '{entidad.name}' actualizados.")

        return redirect("institutions:panel")



@login_required
def switch_institution(request, pk):
    """
    Cambia la institucion en la que trabaja el Super Administrador.

    Evita tener que cerrar la sesion para pasar de una institucion a otra.
    """
    if not request.user.is_super_admin:
        raise PermissionDenied("Solo el Super Administrador puede cambiar de institucion.")

    institution = get_object_or_404(Institution, pk=pk, is_active=True, deleted_at__isnull=True)
    request.session[INSTITUTION_SESSION_KEY] = institution.pk

    register_audit(
        user=request.user, action="PROCESS", module="institutions.panel",
        instance=institution, request=request,
        description=f"Cambio de institucion activa a {institution.name}",
    )
    messages.success(request, f"Esta trabajando en {institution.name}.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:index")


@login_required
def exit_institution(request):
    """
    Devuelve al Super Administrador a la administracion de la plataforma.

    Es la contraparte de `switch_institution`: al soltar la institucion de la
    sesion, el menu vuelve a mostrar solo lo que administra de la plataforma y
    el dashboard vuelve al panorama de todas las instituciones.
    """
    if not request.user.is_super_admin:
        raise PermissionDenied("Solo el Super Administrador administra la plataforma.")

    anterior = request.session.pop(INSTITUTION_SESSION_KEY, None)
    if anterior is not None:
        institution = Institution.objects.filter(pk=anterior).first()
        register_audit(
            user=request.user, action="PROCESS", module="institutions.panel",
            instance=institution, request=request,
            description=f"Salida de la institucion {institution.name if institution else anterior}",
        )
    messages.success(request, "Esta administrando la plataforma.")
    return redirect("dashboard:index")


class InstitutionUsersView(ModulePageView):
    """
    Usuarios de una institucion, con cambio de contrasena.

    Permite al Super Administrador administrar el acceso de cada plantel sin
    salir del panel: ver quien puede entrar y restablecer su contrasena.
    """

    template_name = "institutions/users.html"
    module_code = "institutions.panel"
    icon = "users"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_super_admin:
            raise PermissionDenied("Solo el Super Administrador puede administrar los accesos.")
        return super().dispatch(request, *args, **kwargs)

    @property
    def institution(self):
        return get_object_or_404(Institution, pk=self.kwargs["pk"], deleted_at__isnull=True)

    @property
    def title(self):
        return f"Accesos de {self.institution.short_name or self.institution.name}"

    subtitle = "Usuarios que pueden ingresar a esta institucion y su contrasena."

    def get_context_data(self, **kwargs):
        from core.users.models import User

        context = super().get_context_data(**kwargs)
        institution = self.institution
        context.update({
            "entity": institution,
            "users": (
                User.objects.filter(institution=institution)
                .select_related("role").order_by("role__order", "email")
            ),
            "breadcrumbs": [
                {"label": "Panel de Instituciones", "url": reverse("institutions:panel")},
                {"label": institution.name},
            ],
        })
        return context


@login_required
def change_user_password(request, pk):
    """
    Asigna una contrasena a un usuario, desde el panel del Super Administrador.

    Se puede escribir una concreta o dejar que el sistema genere una. En ambos
    casos queda un certificado de credenciales, que es el mecanismo que la
    plataforma ya usa para entregar accesos, y la operacion se audita.
    """
    from django.contrib.auth.password_validation import ValidationError, validate_password

    from core.users.models import User, UserCredentialCertificate

    if not request.user.is_super_admin:
        raise PermissionDenied("Solo el Super Administrador puede cambiar contrasenas.")
    if request.method != "POST":
        return redirect("institutions:panel")

    usuario = get_object_or_404(User, pk=pk)
    destino = redirect("institutions:users", pk=usuario.institution_id) if usuario.institution_id \
        else redirect("institutions:panel")

    clave = (request.POST.get("password") or "").strip()
    generada = False
    if not clave:
        clave = User.generate_password()
        generada = True
    else:
        try:
            validate_password(clave, usuario)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return destino

    usuario.set_password(clave)
    usuario.must_change_password = request.POST.get("must_change") == "1"
    usuario.failed_login_attempts = 0
    usuario.locked_until = None
    usuario.save(update_fields=[
        "password", "must_change_password", "failed_login_attempts", "locked_until",
    ])
    UserCredentialCertificate.objects.create(
        user=usuario, plain_password=clave, issued_by=request.user
    )
    register_audit(
        user=request.user, action="UPDATE", module="institutions.panel",
        instance=usuario, request=request,
        description=f"Contrasena restablecida para {usuario.email}",
    )
    if generada:
        messages.success(
            request,
            f"Contrasena generada para {usuario.email}: {clave} "
            "(queda en Usuarios > Certificados de Usuario y Contrasena).",
        )
    else:
        messages.success(request, f"Contrasena actualizada para {usuario.email}.")
    return destino


@login_required
def toggle_institution(request, pk):
    """Activa o desactiva una institucion sin borrarla."""
    if not request.user.is_super_admin:
        raise PermissionDenied("Solo el Super Administrador puede administrar las instituciones.")
    if request.method != "POST":
        return redirect("institutions:panel")

    institution = get_object_or_404(Institution, pk=pk, deleted_at__isnull=True)
    if institution.is_default and institution.is_active:
        messages.error(request, "No se puede desactivar la institucion predeterminada.")
        return redirect("institutions:panel")

    institution.is_active = not institution.is_active
    institution.updated_by = request.user
    institution.save(update_fields=["is_active", "updated_by", "updated_at"])

    estado = "activada" if institution.is_active else "desactivada"
    register_audit(
        user=request.user, action="UPDATE", module="institutions.panel",
        instance=institution, request=request,
        description=f"Institucion {estado}: {institution.name}",
    )
    messages.success(request, f"Institucion {estado}: {institution.name}.")
    return redirect("institutions:panel")


class CampusView(ResourceView):
    module_code = "institutions.campuses"
    title = "Sedes y Jornadas"
    subtitle = "Sedes fisicas de la institucion y sus responsables."
    icon = "building"
    endpoint = "/api/campuses/"
    template_name = "institutions/campuses.html"
    columns = [
        column("name", "Sede", width=240),
        column("code", "Codigo", type="mono", width=120),
        column("address", "Direccion", type="truncate", width=260),
        column("coordinator_name", "Coordinador", width=200),
        column("groups_count", "Grupos", type="number", width=100, align="center"),
        column("is_main", "Principal", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre de la sede", required=True),
        field("address", "Direccion", col="half"),
        field("phone", "Telefono", col="half"),
        remote("coordinator", "Coordinador de sede", "/api/users/options/", col="half"),
        field("is_main", "Sede principal", type="boolean", col="half"),
    ]
    empty_title = "Sin sedes registradas"
    empty_message = "Registre las sedes de la institucion para organizar grupos y jornadas."


class ShiftResourceView(ResourceView):
    module_code = "institutions.campuses"
    title = "Jornadas"
    subtitle = "Jornadas academicas de la institucion."
    icon = "clock"
    endpoint = "/api/shifts/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Jornada", width=220),
        column("start_time", "Inicio", width=110),
        column("end_time", "Fin", width=110),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre de la jornada", required=True, col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("start_time", "Hora de inicio", type="time", col="half"),
        field("end_time", "Hora de finalizacion", type="time", col="half"),
        field("description", "Descripcion", type="textarea"),
    ]


class CalendarResourceView(ResourceView):
    module_code = "institutions.profile"
    title = "Calendario Institucional"
    subtitle = "Fechas clave del ano escolar."
    icon = "calendar"
    endpoint = "/api/institutional-calendar/"
    columns = [
        column("name", "Evento", width=280),
        column("type_display", "Tipo", type="badge", tone="info", width=160),
        column("start_date", "Desde", type="date", width=130),
        column("end_date", "Hasta", type="date", width=130),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("event_type", "Tipo", type="select", col="half", options=choices_to_options(
            InstitutionalCalendar.TYPE_CHOICES
        )),
        field("name", "Nombre del evento", required=True),
        field("start_date", "Fecha inicial", type="date", required=True, col="half"),
        field("end_date", "Fecha final", type="date", col="half"),
        field("description", "Descripcion", type="textarea"),
    ]
