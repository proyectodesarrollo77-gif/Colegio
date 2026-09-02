"""Manejo homogeneo de errores para la API REST."""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("pl_sge")


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or list(exc.messages)
        return Response(
            {"success": False, "error": "validation_error", "detail": detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError en %s: %s", context.get("view"), exc)
        return Response(
            {
                "success": False,
                "error": "integrity_error",
                "detail": "El registro entra en conflicto con informacion existente.",
            },
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(
            {
                "success": False,
                "error": "server_error",
                "detail": "Se presento un error inesperado. El incidente fue registrado.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, (Http404, DjangoPermissionDenied)):
        payload = {"success": False, "error": "not_found" if isinstance(exc, Http404) else "forbidden"}
        payload["detail"] = response.data.get("detail") if isinstance(response.data, dict) else str(exc)
        response.data = payload
        return response

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        response.data = {"success": False, "error": "error", "detail": detail["detail"]}
    else:
        response.data = {"success": False, "error": "validation_error", "detail": detail}
    return response
