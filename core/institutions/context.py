"""
Institucion activa de la peticion en curso.

La plataforma resuelve la institucion en `Institution.current()`, que se invoca
desde vistas, servicios, plantillas y comandos sin recibir el request. Para
soportar varias instituciones sin reescribir esas llamadas, la institucion
elegida en el ingreso se guarda aqui durante la peticion y `current()` la
consulta.

Se usa `asgiref.local.Local`, que aisla el valor por hilo y por tarea async,
de modo que dos peticiones concurrentes de instituciones distintas nunca se
mezclan.
"""
from __future__ import annotations

from asgiref.local import Local

SESSION_KEY = "plsge_institution_id"

_state = Local()


def set_active_institution(institution):
    """Fija la institucion de la peticion en curso."""
    _state.institution = institution
    return institution


def in_institution_mode(request):
    """
    Indica si se esta trabajando *dentro* de una institucion concreta.

    El Super Administrador tiene dos modos: administra la plataforma (ve las
    instituciones y las cuentas, no la operacion academica) o entra a una
    institucion con `Ingresar` y desde ese momento trabaja como si fuera de
    ella. Lo que los distingue es haberla elegido de forma explicita, que es
    justo lo que guarda la sesion.

    Para los demas perfiles siempre es cierto: solo tienen su institucion.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    if not user.is_super_admin:
        return True
    try:
        return bool(request.session.get(SESSION_KEY))
    except AttributeError:
        return False


def get_active_institution():
    """Institucion de la peticion en curso, o None fuera de una peticion."""
    return getattr(_state, "institution", None)


def clear_active_institution():
    """Libera la institucion al terminar la peticion."""
    try:
        del _state.institution
    except AttributeError:
        pass


class use_institution:
    """
    Contexto para ejecutar codigo bajo una institucion concreta.

        with use_institution(otra):
            ...

    Util en comandos, tareas y pruebas, donde no hay peticion HTTP.
    """

    def __init__(self, institution):
        self.institution = institution
        self._previous = None

    def __enter__(self):
        self._previous = get_active_institution()
        set_active_institution(self.institution)
        return self.institution

    def __exit__(self, *exc_info):
        if self._previous is None:
            clear_active_institution()
        else:
            set_active_institution(self._previous)
        return False
