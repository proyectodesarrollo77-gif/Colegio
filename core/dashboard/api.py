"""API REST del dashboard institucional."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_dashboard


class DashboardAPIView(APIView):
    """Indicadores, graficas, alertas y accesos rapidos del usuario."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_dashboard(request.user))


ROUTES = []
