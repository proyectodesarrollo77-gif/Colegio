"""Manejadores de error personalizados de PL_SGE."""
from django.shortcuts import render


def _render(request, template, status, title, message):
    context = {"status": status, "title": title, "message": message}
    return render(request, template, context, status=status)


def bad_request(request, exception=None):
    return _render(
        request, "errors/error.html", 400,
        "Solicitud incorrecta",
        "La informacion enviada no pudo ser procesada. Verifique los datos e intente nuevamente.",
    )


def permission_denied(request, exception=None):
    return _render(
        request, "errors/error.html", 403,
        "Acceso restringido",
        "No cuenta con los permisos necesarios para acceder a este modulo. Contacte al administrador.",
    )


def page_not_found(request, exception=None):
    return _render(
        request, "errors/error.html", 404,
        "Pagina no encontrada",
        "La direccion solicitada no existe o fue movida dentro de la plataforma.",
    )


def server_error(request):
    return _render(
        request, "errors/error.html", 500,
        "Error interno del servidor",
        "Se presento un error inesperado. El incidente quedo registrado en la bitacora.",
    )
