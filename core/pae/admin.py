"""Administracion tecnica del modulo PAE."""
from django.contrib import admin

from .models import (
    PaeBeneficiary, PaeBeneficiaryHistory, PaeCatalog, PaeChecklist, PaeChecklistItem,
    PaeCommitment, PaeComplementType, PaeContract, PaeDelivery, PaeDocument, PaeEvidence,
    PaeFinding, PaeImprovementAction, PaeIncident, PaeIncidentHistory, PaeIndicator,
    PaeMenuCycle, PaeMenuDay, PaeMenuIngredient, PaeMenuPreparation, PaeModality,
    PaeNormative, PaeOperator, PaeParticipant, PaeParticipationMeeting, PaePlan,
    PaePlanStateHistory, PaePqrs, PaePrioritization, PaeReport, PaeSchedule,
    PaeSiteDiagnosis, PaeVerification, PaeVerificationResult, PaeVigencia, PaeVisit,
)


class ChecklistItemInline(admin.TabularInline):
    model = PaeChecklistItem
    extra = 0


class MenuDayInline(admin.TabularInline):
    model = PaeMenuDay
    extra = 0


class MenuIngredientInline(admin.TabularInline):
    model = PaeMenuIngredient
    extra = 0


class ParticipantInline(admin.TabularInline):
    model = PaeParticipant
    extra = 0


@admin.register(PaeNormative)
class PaeNormativeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "issuer", "issued_on", "status")
    list_filter = ("status", "issuer")
    search_fields = ("code", "name", "number")


@admin.register(PaeCatalog)
class PaeCatalogAdmin(admin.ModelAdmin):
    list_display = ("catalog_type", "code", "name", "weight", "validation_status", "is_active")
    list_filter = ("catalog_type", "validation_status", "is_active")
    search_fields = ("code", "name")


@admin.register(PaeVigencia)
class PaeVigenciaAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year", "start_date", "end_date", "status", "is_current")
    list_filter = ("status", "is_current")


@admin.register(PaeBeneficiary)
class PaeBeneficiaryAdmin(admin.ModelAdmin):
    list_display = ("student", "vigencia", "campus", "grade", "group", "status")
    list_filter = ("vigencia", "status", "campus", "modality")
    search_fields = ("student__first_name", "student__last_name", "student__document_number")
    raw_id_fields = ("student", "enrollment")


@admin.register(PaePlan)
class PaePlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "campus", "vigencia", "beneficiaries_count", "status")
    list_filter = ("vigencia", "status", "campus")
    search_fields = ("code", "name")


@admin.register(PaeDelivery)
class PaeDeliveryAdmin(admin.ModelAdmin):
    list_display = ("service_date", "campus", "scheduled_rations", "received_rations",
                    "delivered_rations", "compliance", "status")
    list_filter = ("status", "campus", "service_date")
    date_hierarchy = "service_date"


@admin.register(PaeIncident)
class PaeIncidentAdmin(admin.ModelAdmin):
    list_display = ("number", "reported_on", "campus", "incident_type", "priority", "status")
    list_filter = ("status", "priority", "campus")
    search_fields = ("number", "description")


@admin.register(PaeChecklist)
class PaeChecklistAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scope", "version", "is_active")
    list_filter = ("scope", "is_active")
    inlines = [ChecklistItemInline]


@admin.register(PaeMenuCycle)
class PaeMenuCycleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "version", "vigencia", "status")
    list_filter = ("vigencia", "status")
    inlines = [MenuDayInline]


@admin.register(PaeMenuPreparation)
class PaeMenuPreparationAdmin(admin.ModelAdmin):
    list_display = ("name", "day", "component", "calories")
    list_filter = ("component",)
    inlines = [MenuIngredientInline]


@admin.register(PaeParticipationMeeting)
class PaeParticipationMeetingAdmin(admin.ModelAdmin):
    list_display = ("act_number", "subject", "meeting_date", "campus", "status")
    list_filter = ("status", "campus")
    inlines = [ParticipantInline]


@admin.register(PaeDocument)
class PaeDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "version", "document_date", "expires_on", "status")
    list_filter = ("module", "status")
    search_fields = ("name",)


for model in (
    PaeModality, PaeComplementType, PaeSiteDiagnosis, PaePrioritization,
    PaeBeneficiaryHistory, PaeOperator, PaeContract, PaePlanStateHistory,
    PaeMenuDay, PaeMenuIngredient, PaeSchedule, PaeChecklistItem, PaeVerification,
    PaeVerificationResult, PaeVisit, PaeFinding, PaeIncidentHistory,
    PaeImprovementAction, PaePqrs, PaeParticipant, PaeCommitment, PaeEvidence,
    PaeIndicator, PaeReport,
):
    admin.site.register(model)
