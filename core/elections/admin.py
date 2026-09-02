from django.contrib import admin

from .models import Candidacy, Candidate, Election, ElectionResult, Vote, VoterRegistry


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 0


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year", "start_at", "end_at", "status")
    list_filter = ("status", "school_year")


@admin.register(Candidacy)
class CandidacyAdmin(admin.ModelAdmin):
    list_display = ("name", "election", "voter_scope", "max_selections")
    list_filter = ("election",)
    inlines = [CandidateInline]
    filter_horizontal = ("grades",)


@admin.register(ElectionResult)
class ElectionResultAdmin(admin.ModelAdmin):
    list_display = ("election", "candidacy", "candidate", "votes", "percentage", "is_winner")
    list_filter = ("election", "is_winner")


admin.site.register(Vote)
admin.site.register(VoterRegistry)
