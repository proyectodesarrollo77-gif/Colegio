"""API REST del modulo de elecciones (gobierno escolar)."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.viewsets import BaseModelViewSet
from core.authentication.utils import get_client_ip

from .models import Candidacy, Candidate, Election, ElectionResult, Vote, VoterRegistry
from .serializers import (
    CandidacySerializer,
    CandidateSerializer,
    ElectionResultSerializer,
    ElectionSerializer,
    VoteCastSerializer,
    VoterRegistrySerializer,
)


class ElectionViewSet(BaseModelViewSet):
    module_code = "elections.setup"
    queryset = Election.objects.select_related("school_year").all()
    serializer_class = ElectionSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["school_year", "status"]
    export_filename = "procesos_electorales"

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        election = self.get_object()
        new_status = request.data.get("status")
        valid = dict(Election.STATUS_CHOICES)
        if new_status not in valid:
            return Response({"detail": "Estado invalido."}, status=status.HTTP_400_BAD_REQUEST)
        election.status = new_status
        election.save(update_fields=["status"])
        if new_status == "PUBLICADA":
            consolidate_results(election)
        self.log_action("UPDATE", election)
        return Response({"success": True, "status": election.status})

    @action(detail=True, methods=["get"], url_path="ballot")
    def ballot(self, request, pk=None):
        """Tarjeton electoral del usuario autenticado."""
        election = self.get_object()
        voter_hash = Vote.build_hash(election.id, request.user.id)
        voted = set(
            Vote.objects.filter(election=election, voter_hash=voter_hash).values_list("candidacy_id", flat=True)
        )
        candidacies = election.candidacies.filter(deleted_at__isnull=True).prefetch_related("candidates")
        return Response(
            {
                "election": ElectionSerializer(election).data,
                "already_voted": list(voted),
                "candidacies": [
                    {
                        **CandidacySerializer(candidacy).data,
                        "voted": candidacy.id in voted,
                    }
                    for candidacy in candidacies
                ],
            }
        )


class CandidacyViewSet(BaseModelViewSet):
    module_code = "elections.setup"
    queryset = Candidacy.objects.select_related("election", "group").prefetch_related("candidates", "grades").all()
    serializer_class = CandidacySerializer
    search_fields = ["name", "description"]
    filterset_fields = ["election", "voter_scope"]
    export_filename = "cargos_electorales"


class CandidateViewSet(BaseModelViewSet):
    module_code = "elections.setup"
    queryset = Candidate.objects.select_related("candidacy", "student").all()
    serializer_class = CandidateSerializer
    search_fields = ["student__first_name", "student__last_name", "slogan"]
    filterset_fields = ["candidacy", "is_approved", "is_blank_vote"]
    approve_field = "is_approved"
    export_filename = "candidatos"


class ElectionResultViewSet(BaseModelViewSet):
    module_code = "elections.results"
    queryset = ElectionResult.objects.select_related("election", "candidacy", "candidate", "candidate__student").all()
    serializer_class = ElectionResultSerializer
    filterset_fields = ["election", "candidacy", "is_winner"]
    export_filename = "resultados_electorales"

    @action(detail=False, methods=["post"], url_path="consolidate")
    def consolidate(self, request):
        election = get_object_or_404(Election, pk=request.data.get("election"))
        results = consolidate_results(election)
        self.log_action("PROCESS", election)
        return Response({"success": True, "results": len(results)})


class VoterRegistryViewSet(BaseModelViewSet):
    module_code = "elections.results"
    queryset = VoterRegistry.objects.select_related("election").all()
    serializer_class = VoterRegistrySerializer
    filterset_fields = ["election", "completed"]
    export_filename = "censo_electoral"


@transaction.atomic
def consolidate_results(election):
    """Cuenta los votos y publica los resultados por cargo."""
    results = []
    for candidacy in election.candidacies.filter(deleted_at__isnull=True):
        counts = (
            Vote.objects.filter(candidacy=candidacy)
            .values("candidate_id")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        total_votes = sum(row["total"] for row in counts) or 1
        for position, row in enumerate(counts, start=1):
            candidate = Candidate.objects.get(pk=row["candidate_id"])
            candidate.votes_count = row["total"]
            candidate.save(update_fields=["votes_count"])
            result, _ = ElectionResult.objects.update_or_create(
                election=election,
                candidacy=candidacy,
                candidate=candidate,
                defaults={
                    "votes": row["total"],
                    "percentage": round(row["total"] / total_votes * 100, 2),
                    "position": position,
                    "is_winner": position == 1 and not candidate.is_blank_vote,
                    "published_at": timezone.now(),
                },
            )
            results.append(result)
    return results


class CastVoteAPIView(APIView):
    """Registro del voto digital del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = VoteCastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        election = get_object_or_404(Election, pk=serializer.validated_data["election"])

        if not election.is_open:
            return Response(
                {"success": False, "detail": "La votacion no se encuentra abierta."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if election.require_2fa and not request.user.two_factor_enabled:
            return Response(
                {"success": False, "detail": "Este proceso exige tener activo el doble factor."},
                status=status.HTTP_403_FORBIDDEN,
            )

        voter_hash = Vote.build_hash(election.id, request.user.id)
        registered = 0
        for candidacy_id, candidate_id in serializer.validated_data["selections"].items():
            candidacy = Candidacy.objects.filter(pk=candidacy_id, election=election).first()
            candidate = Candidate.objects.filter(pk=candidate_id, candidacy=candidacy).first()
            if candidacy is None or candidate is None:
                continue
            if Vote.objects.filter(candidacy=candidacy, voter_hash=voter_hash).exists():
                continue
            Vote.objects.create(
                election=election,
                candidacy=candidacy,
                candidate=candidate,
                voter_hash=voter_hash,
                ip_address=get_client_ip(request),
            )
            registered += 1

        total_candidacies = election.candidacies.filter(deleted_at__isnull=True).count()
        voted = Vote.objects.filter(election=election, voter_hash=voter_hash).count()
        VoterRegistry.objects.update_or_create(
            election=election,
            voter_hash=voter_hash,
            defaults={
                "candidacies_voted": voted,
                "completed": voted >= total_candidacies,
                "voted_at": timezone.now(),
            },
        )

        from core.audit.services import register_audit

        register_audit(
            user=request.user,
            action="CREATE",
            module="elections.voting",
            instance=election,
            request=request,
            description=f"Voto registrado en {registered} cargos",
        )
        return Response({"success": True, "registered": registered, "completed": voted >= total_candidacies})


ROUTES = [
    ("elections", ElectionViewSet, "election"),
    ("candidacies", CandidacyViewSet, "candidacy"),
    ("candidates", CandidateViewSet, "candidate"),
    ("election-results", ElectionResultViewSet, "electionresult"),
    ("voter-registry", VoterRegistryViewSet, "voterregistry"),
]
