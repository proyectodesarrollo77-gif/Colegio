"""Serializers del modulo de elecciones."""
from rest_framework import serializers

from .models import Candidacy, Candidate, Election, ElectionResult, Vote, VoterRegistry


class CandidateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    group_name = serializers.SerializerMethodField()
    candidacy_name = serializers.CharField(source="candidacy.name", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "candidacy", "candidacy_name", "student", "student_name", "group_name",
            "number", "slogan", "proposals", "photo", "is_approved", "is_blank_vote",
            "votes_count", "is_active",
        ]
        read_only_fields = ["votes_count"]

    def get_group_name(self, obj):
        group = obj.student.current_group if obj.student_id else None
        return group.name if group else None


class CandidacySerializer(serializers.ModelSerializer):
    election_name = serializers.CharField(source="election.name", read_only=True)
    candidates = CandidateSerializer(many=True, read_only=True)
    candidates_count = serializers.IntegerField(source="candidates.count", read_only=True)

    class Meta:
        model = Candidacy
        fields = [
            "id", "election", "election_name", "name", "description", "voter_scope",
            "grades", "group", "max_selections", "order", "is_active",
            "candidates", "candidates_count",
        ]


class ElectionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    candidacies_count = serializers.IntegerField(source="candidacies.count", read_only=True)
    votes_count = serializers.IntegerField(source="votes.count", read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Election
        fields = [
            "id", "school_year", "school_year_name", "name", "description", "start_at", "end_at",
            "status", "status_display", "allow_blank_vote", "show_live_results", "require_2fa",
            "banner", "is_open", "candidacies_count", "votes_count", "is_active",
        ]


class ElectionResultSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidacy_name = serializers.CharField(source="candidacy.name", read_only=True)
    election_name = serializers.CharField(source="election.name", read_only=True)

    class Meta:
        model = ElectionResult
        fields = [
            "id", "election", "election_name", "candidacy", "candidacy_name",
            "candidate", "candidate_name", "votes", "percentage", "position",
            "is_winner", "published_at",
        ]
        read_only_fields = fields

    def get_candidate_name(self, obj):
        return str(obj.candidate)


class VoterRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = VoterRegistry
        fields = ["id", "election", "voter_hash", "candidacies_voted", "completed", "voted_at"]
        read_only_fields = fields


class VoteCastSerializer(serializers.Serializer):
    election = serializers.IntegerField()
    selections = serializers.DictField(child=serializers.IntegerField())
