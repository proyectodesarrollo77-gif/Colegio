"""Serializers del modulo PAE. Toda regla de negocio se delega en services."""
from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import services
from .models import (
    PaeBeneficiary,
    PaeBeneficiaryHistory,
    PaeCatalog,
    PaeChecklist,
    PaeChecklistItem,
    PaeCommitment,
    PaeComplementType,
    PaeContract,
    PaeDelivery,
    PaeDocument,
    PaeEvidence,
    PaeFinding,
    PaeImprovementAction,
    PaeIncident,
    PaeIncidentHistory,
    PaeIndicator,
    PaeMenuCycle,
    PaeMenuDay,
    PaeMenuIngredient,
    PaeMenuPreparation,
    PaeModality,
    PaeNormative,
    PaeOperator,
    PaeParticipant,
    PaeParticipationMeeting,
    PaePlan,
    PaePlanStateHistory,
    PaePqrs,
    PaePrioritization,
    PaeReport,
    PaeSchedule,
    PaeSiteDiagnosis,
    PaeVerification,
    PaeVerificationResult,
    PaeVigencia,
    PaeVisit,
)


def _raise(errors):
    """Traduce ValidationError de Django a la forma esperada por DRF."""
    raise serializers.ValidationError(errors.message_dict if hasattr(errors, "message_dict") else errors.messages)


def _validate_upload(value):
    """Extension, tipo y tamano de los archivos que se adjuntan al modulo."""
    from config.imports import validate_document_upload

    if value in (None, ""):
        return value
    try:
        validate_document_upload(value)
    except DjangoValidationError as error:
        messages = error.message_dict.get("file") if hasattr(error, "message_dict") else error.messages
        raise serializers.ValidationError(messages)
    return value


# ===========================================================================
# CONFIGURACION
# ===========================================================================
class PaeNormativeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    vigencias_count = serializers.IntegerField(source="vigencias.count", read_only=True)

    class Meta:
        model = PaeNormative
        fields = [
            "id", "code", "name", "issuer", "number", "issued_on", "effective_from", "effective_to",
            "status", "status_display", "summary", "url", "file", "notes", "is_active", "vigencias_count",
        ]


class PaeCatalogSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_catalog_type_display", read_only=True)
    normative_code = serializers.CharField(source="normative.code", read_only=True)

    class Meta:
        model = PaeCatalog
        fields = [
            "id", "catalog_type", "type_display", "code", "name", "description", "order",
            "weight", "color", "icon", "requires_evidence", "requires_action",
            "validation_status", "normative", "normative_code", "metadata", "is_active",
        ]

    def validate_code(self, value):
        return value.strip().upper().replace(" ", "_")


class PaeModalitySerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    beneficiaries_count = serializers.IntegerField(source="beneficiaries.count", read_only=True)

    class Meta:
        model = PaeModality
        fields = [
            "id", "institution", "institution_name", "code", "name", "description",
            "requires_kitchen", "requires_dining_room", "requires_cold_chain",
            "normative", "color", "order", "is_active", "beneficiaries_count",
        ]


class PaeComplementTypeSerializer(serializers.ModelSerializer):
    modality_name = serializers.CharField(source="modality.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)

    class Meta:
        model = PaeComplementType
        fields = [
            "id", "institution", "modality", "modality_name", "shift", "shift_name",
            "code", "name", "description", "calorie_contribution", "energy_percentage",
            "service_start", "service_end", "normative", "color", "order", "is_active",
        ]


class PaeVigenciaSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    normative_code = serializers.CharField(source="normative.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    progress = serializers.IntegerField(read_only=True)
    beneficiaries_count = serializers.SerializerMethodField()
    plans_count = serializers.IntegerField(source="plans.count", read_only=True)

    class Meta:
        model = PaeVigencia
        fields = [
            "id", "institution", "institution_name", "school_year", "school_year_name",
            "normative", "normative_code", "name", "start_date", "end_date", "service_days",
            "status", "status_display", "is_current", "coverage_goal", "compliance_goal",
            "observations", "progress", "beneficiaries_count", "plans_count", "is_active",
        ]

    def get_beneficiaries_count(self, obj):
        return obj.beneficiaries.filter(status="ACTIVO", deleted_at__isnull=True).count()

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
        return attrs


# ===========================================================================
# DIAGNOSTICO Y PRIORIZACION
# ===========================================================================
class PaeSiteDiagnosisSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    vigencia_name = serializers.CharField(source="vigencia.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    result_display = serializers.CharField(source="get_result_display", read_only=True)
    zone_display = serializers.CharField(source="get_zone_display", read_only=True)

    class Meta:
        model = PaeSiteDiagnosis
        fields = [
            "id", "vigencia", "vigencia_name", "campus", "campus_name", "diagnosis_date",
            "responsible", "responsible_name", "zone", "zone_display",
            "infrastructure", "kitchen", "dining_room", "storage", "refrigeration",
            "water", "energy", "gas", "equipment", "sanitary", "accessibility",
            "has_potable_water", "has_handwashing", "has_waste_management",
            "has_pest_control", "has_sanitary_concept",
            "dining_capacity", "kitchen_area_m2", "storage_area_m2", "max_rations", "food_handlers",
            "territorial_conditions", "observations", "result", "result_display", "score", "is_active",
        ]
        read_only_fields = ["result", "score"]


class PaePrioritizationSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    population_name = serializers.CharField(source="population_type.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    coverage = serializers.FloatField(read_only=True)
    criteria_display = serializers.SerializerMethodField()

    class Meta:
        model = PaePrioritization
        fields = [
            "id", "vigencia", "campus", "campus_name", "grade", "grade_name", "group", "group_name",
            "shift", "shift_name", "population_type", "population_name", "criteria", "criteria_display",
            "enrolled_students", "prioritized_students", "coverage", "score", "justification",
            "responsible", "responsible_name", "registered_on", "status", "status_display",
            "approved_by", "approved_at", "is_active",
        ]
        read_only_fields = ["approved_by", "approved_at"]

    def get_criteria_display(self, obj):
        return ", ".join(obj.criteria.values_list("name", flat=True)[:6])

    def validate(self, attrs):
        enrolled = attrs.get("enrolled_students", getattr(self.instance, "enrolled_students", 0))
        prioritized = attrs.get("prioritized_students", getattr(self.instance, "prioritized_students", 0))
        if prioritized > enrolled:
            raise serializers.ValidationError(
                {"prioritized_students": "Los priorizados no pueden superar a los matriculados."}
            )
        return attrs


# ===========================================================================
# BENEFICIARIOS
# ===========================================================================
class PaeBeneficiarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_document = serializers.CharField(source="student.document_number", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    modality_name = serializers.CharField(source="modality.name", read_only=True)
    complement_name = serializers.CharField(source="complement_type.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    vigencia_name = serializers.CharField(source="vigencia.name", read_only=True)

    class Meta:
        model = PaeBeneficiary
        fields = [
            "id", "vigencia", "vigencia_name", "student", "student_name", "student_document",
            "student_code", "enrollment", "campus", "campus_name", "grade", "grade_name",
            "group", "group_name", "shift", "shift_name", "modality", "modality_name",
            "complement_type", "complement_name", "prioritization", "start_date", "end_date",
            "status", "status_display", "has_special_diet", "special_diet_detail",
            "observations", "is_active",
        ]
        # El duplicado lo reporta `services.validate_beneficiary` sobre el campo
        # `student` y con el mensaje de la regla 8. Sin esto, el validador
        # automatico de unicidad se adelanta con un error generico y, ademas,
        # ignora el borrado logico. La restriccion en la base sigue vigente.
        validators = []

    def validate(self, attrs):
        instance = self.instance or PaeBeneficiary()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        try:
            services.validate_beneficiary(instance)
        except DjangoValidationError as error:
            _raise(error)
        return attrs


class PaeBeneficiaryHistorySerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source="beneficiary.student.full_name", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = PaeBeneficiaryHistory
        fields = [
            "id", "beneficiary", "beneficiary_name", "previous_status", "new_status",
            "previous_group", "new_group", "reason", "changed_at", "changed_by", "changed_by_name",
        ]
        read_only_fields = fields


# ===========================================================================
# OPERADORES Y CONTRATOS
# ===========================================================================
class PaeOperatorSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contracts_count = serializers.IntegerField(source="contracts.count", read_only=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True)

    class Meta:
        model = PaeOperator
        fields = [
            "id", "institution", "institution_name", "code", "business_name", "nit",
            "legal_representative", "contact_name", "phone", "mobile", "email", "address",
            "city", "sanitary_registration", "status", "status_display", "user",
            "observations", "is_active", "contracts_count",
        ]


class PaeContractSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    vigencia_name = serializers.CharField(source="vigencia.name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_to_expire = serializers.IntegerField(read_only=True)
    is_expiring = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    execution_percentage = serializers.FloatField(read_only=True)
    campuses_display = serializers.SerializerMethodField()

    class Meta:
        model = PaeContract
        fields = [
            "id", "vigencia", "vigencia_name", "operator", "operator_name", "number", "subject",
            "value", "ration_value", "start_date", "end_date", "total_rations", "campuses",
            "campuses_display", "modalities", "supervisor", "supervisor_name", "status",
            "status_display", "alert_days", "observations", "days_to_expire", "is_expiring",
            "is_expired", "execution_percentage", "is_active",
        ]

    def get_campuses_display(self, obj):
        return ", ".join(obj.campuses.values_list("name", flat=True)[:5])

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
        return attrs


# ===========================================================================
# PLANEACION
# ===========================================================================
class PaePlanSerializer(serializers.ModelSerializer):
    vigencia_name = serializers.CharField(source="vigencia.name", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    contract_number = serializers.CharField(source="contract.number", read_only=True)
    modality_name = serializers.CharField(source="modality.name", read_only=True)
    menu_cycle_name = serializers.CharField(source="menu_cycle.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_editable = serializers.BooleanField(read_only=True)
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = PaePlan
        fields = [
            "id", "vigencia", "vigencia_name", "institution", "campus", "campus_name", "code",
            "name", "start_date", "end_date", "responsible", "responsible_name", "modality",
            "modality_name", "complement_type", "operator", "operator_name", "contract",
            "contract_number", "menu_cycle", "menu_cycle_name", "beneficiaries_count",
            "service_days", "projected_rations", "status", "status_display", "approved_by",
            "approved_at", "closed_at", "observations", "is_editable", "allowed_transitions",
            "is_active",
        ]
        read_only_fields = ["code", "status", "approved_by", "approved_at", "closed_at"]

    def get_allowed_transitions(self, obj):
        return [{"status": status, "action": action} for status, action in obj.allowed_transitions()]

    def validate(self, attrs):
        if self.instance:
            request = self.context.get("request")
            try:
                services.validate_plan_edit(self.instance, getattr(request, "user", None))
            except DjangoValidationError as error:
                _raise(error)
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
        return attrs


class PaePlanStateHistorySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = PaePlanStateHistory
        fields = ["id", "plan", "plan_name", "previous_status", "new_status", "reason",
                  "changed_at", "changed_by", "changed_by_name"]
        read_only_fields = fields


# ===========================================================================
# MENUS
# ===========================================================================
class PaeMenuIngredientSerializer(serializers.ModelSerializer):
    food_group_name = serializers.CharField(source="food_group.name", read_only=True)

    class Meta:
        model = PaeMenuIngredient
        fields = ["id", "preparation", "name", "food_group", "food_group_name", "quantity", "unit", "notes"]


class PaeMenuPreparationSerializer(serializers.ModelSerializer):
    ingredients = PaeMenuIngredientSerializer(many=True, read_only=True)
    component_display = serializers.CharField(source="get_component_display", read_only=True)
    day_label = serializers.CharField(source="day.__str__", read_only=True)

    class Meta:
        model = PaeMenuPreparation
        fields = ["id", "day", "day_label", "name", "component", "component_display", "portion",
                  "calories", "protein", "notes", "order", "ingredients"]


class PaeMenuDaySerializer(serializers.ModelSerializer):
    preparations = PaeMenuPreparationSerializer(many=True, read_only=True)
    cycle_name = serializers.CharField(source="cycle.name", read_only=True)
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)
    total_calories = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PaeMenuDay
        fields = ["id", "cycle", "cycle_name", "day_number", "weekday", "weekday_display",
                  "name", "notes", "total_calories", "preparations"]


class PaeMenuCycleSerializer(serializers.ModelSerializer):
    modality_name = serializers.CharField(source="modality.name", read_only=True)
    complement_name = serializers.CharField(source="complement_type.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_registered = serializers.IntegerField(source="days.count", read_only=True)

    class Meta:
        model = PaeMenuCycle
        fields = [
            "id", "vigencia", "modality", "modality_name", "complement_type", "complement_name",
            "code", "name", "version", "days_count", "days_registered", "start_date", "end_date",
            "nutritionist", "professional_card", "status", "status_display", "parent_version",
            "normative", "observations", "is_active",
        ]
        read_only_fields = ["version", "parent_version"]


# ===========================================================================
# PROGRAMACION Y ENTREGAS
# ===========================================================================
class PaeScheduleSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    complement_name = serializers.CharField(source="complement_type.name", read_only=True)
    menu_label = serializers.CharField(source="menu_day.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PaeSchedule
        fields = [
            "id", "plan", "plan_name", "service_date", "campus", "campus_name", "shift", "shift_name",
            "operator", "operator_name", "complement_type", "complement_name", "menu_day", "menu_label",
            "beneficiaries_count", "scheduled_rations", "service_time", "status", "status_display",
            "observations", "is_active",
        ]


class PaeDeliverySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    complement_name = serializers.CharField(source="complement_type.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    cause_name = serializers.CharField(source="noncompliance_cause.name", read_only=True)
    has_noncompliance = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaeDelivery
        fields = [
            "id", "schedule", "plan", "plan_name", "contract", "service_date", "campus", "campus_name",
            "shift", "shift_name", "operator", "operator_name", "complement_type", "complement_name",
            "scheduled_beneficiaries", "scheduled_rations", "received_rations", "delivered_rations",
            "missing_rations", "undelivered_rations", "compliance", "arrival_time", "delivery_time",
            "scheduled_menu", "menu_matches", "received_menu_detail", "responsible", "responsible_name",
            "noncompliance_cause", "cause_name", "justification", "status", "status_display",
            "observations", "has_noncompliance", "is_active",
        ]
        read_only_fields = ["missing_rations", "undelivered_rations", "compliance"]

    def validate(self, attrs):
        instance = self.instance or PaeDelivery()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        instance.compute_totals()
        try:
            services.validate_delivery(instance)
        except DjangoValidationError as error:
            _raise(error)
        return attrs


# ===========================================================================
# CONTROL DE CALIDAD
# ===========================================================================
class PaeChecklistItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    checklist_name = serializers.CharField(source="checklist.name", read_only=True)

    class Meta:
        model = PaeChecklistItem
        fields = ["id", "checklist", "checklist_name", "category", "category_name", "code",
                  "criterion", "weight", "is_critical", "requires_evidence",
                  "normative_reference", "order", "is_active"]


class PaeChecklistSerializer(serializers.ModelSerializer):
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)
    items = PaeChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = PaeChecklist
        fields = ["id", "vigencia", "code", "name", "scope", "scope_display", "description",
                  "version", "normative", "threshold_full", "threshold_partial",
                  "items_count", "items", "is_active"]


class PaeVerificationResultSerializer(serializers.ModelSerializer):
    criterion = serializers.CharField(source="item.criterion", read_only=True)
    category_name = serializers.CharField(source="item.category.name", read_only=True)
    is_critical = serializers.BooleanField(source="item.is_critical", read_only=True)

    class Meta:
        model = PaeVerificationResult
        fields = ["id", "verification", "item", "criterion", "category_name",
                  "is_critical", "answer", "observation"]


class PaeVerificationSerializer(serializers.ModelSerializer):
    checklist_name = serializers.CharField(source="checklist.name", read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    result_display = serializers.CharField(source="get_result_display", read_only=True)
    results = PaeVerificationResultSerializer(many=True, read_only=True)

    class Meta:
        model = PaeVerification
        fields = [
            "id", "checklist", "checklist_name", "vigencia", "campus", "campus_name", "delivery",
            "operator", "operator_name", "verification_date", "responsible", "responsible_name",
            "total_items", "compliant_items", "noncompliant_items", "not_applicable_items",
            "critical_failures", "score", "result", "result_display", "observations",
            "results", "is_active",
        ]
        read_only_fields = ["total_items", "compliant_items", "noncompliant_items",
                            "not_applicable_items", "critical_failures", "score", "result"]


# ===========================================================================
# VISITAS, HALLAZGOS Y NOVEDADES
# ===========================================================================
class PaeFindingSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    finding_type_name = serializers.CharField(source="finding_type.name", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    visit_number = serializers.CharField(source="visit.number", read_only=True)

    class Meta:
        model = PaeFinding
        fields = ["id", "visit", "visit_number", "verification", "campus", "campus_name",
                  "finding_type", "finding_type_name", "code", "description", "severity",
                  "severity_display", "detected_on", "normative_reference", "status",
                  "status_display", "closed_at", "is_active"]


class PaeCommitmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaeCommitment
        fields = ["id", "visit", "meeting", "description", "responsible_name", "responsible_user",
                  "due_date", "status", "status_display", "follow_up", "completed_at",
                  "is_overdue", "is_active"]


class PaeVisitSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    visit_type_name = serializers.CharField(source="visit_type.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    findings_count = serializers.IntegerField(source="findings.count", read_only=True)
    commitments_count = serializers.IntegerField(source="commitments.count", read_only=True)
    verification_result = serializers.CharField(source="verification.result", read_only=True)

    class Meta:
        model = PaeVisit
        fields = [
            "id", "vigencia", "campus", "campus_name", "operator", "operator_name", "visit_type",
            "visit_type_name", "verification", "verification_result", "number", "visit_date",
            "start_time", "end_time", "responsible", "responsible_name", "objective", "attendees",
            "development", "conclusions", "status", "status_display", "findings_count",
            "commitments_count", "is_active",
        ]
        read_only_fields = ["number"]


class PaeIncidentSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    operator_name = serializers.CharField(source="operator.business_name", read_only=True)
    incident_type_name = serializers.CharField(source="incident_type.name", read_only=True)
    reported_by_name = serializers.CharField(source="reported_by.get_full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = PaeIncident
        fields = [
            "id", "vigencia", "campus", "campus_name", "delivery", "operator", "operator_name",
            "incident_type", "incident_type_name", "number", "reported_on", "description",
            "priority", "priority_display", "reported_by", "reported_by_name", "assigned_to",
            "assigned_to_name", "due_date", "solution", "solved_at", "closed_at", "status",
            "status_display", "is_overdue", "allowed_transitions", "is_active",
        ]
        read_only_fields = ["number", "status", "solved_at", "closed_at"]

    def get_allowed_transitions(self, obj):
        return obj.allowed_transitions()


class PaeIncidentHistorySerializer(serializers.ModelSerializer):
    incident_number = serializers.CharField(source="incident.number", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = PaeIncidentHistory
        fields = ["id", "incident", "incident_number", "previous_status", "new_status",
                  "comment", "changed_at", "changed_by", "changed_by_name"]
        read_only_fields = fields


class PaeImprovementActionSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    incident_number = serializers.CharField(source="incident.number", read_only=True)

    class Meta:
        model = PaeImprovementAction
        fields = [
            "id", "vigencia", "campus", "campus_name", "finding", "incident", "incident_number",
            "code", "finding_description", "root_cause", "action", "responsible", "responsible_name",
            "start_date", "due_date", "indicator", "goal", "progress", "requires_evidence",
            "verification_note", "verified_by", "verified_at", "closed_at", "status",
            "status_display", "is_overdue", "days_remaining", "is_active",
        ]
        read_only_fields = ["code", "verified_by", "verified_at", "closed_at"]

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        due = attrs.get("due_date") or getattr(self.instance, "due_date", None)
        if start and due and due < start:
            raise serializers.ValidationError({"due_date": "La fecha limite no puede ser anterior al inicio."})
        return attrs


# ===========================================================================
# PQRS Y PARTICIPACION
# ===========================================================================
class PaePqrsSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaePqrs
        fields = [
            "id", "vigencia", "campus", "campus_name", "filing_number", "kind", "kind_display",
            "pqrs_type", "channel", "channel_display", "filed_on", "applicant_name",
            "applicant_document", "applicant_email", "applicant_phone", "is_anonymous",
            "description", "responsible", "responsible_name", "due_date", "answer",
            "answered_on", "status", "status_display", "is_overdue", "is_active",
        ]
        read_only_fields = ["filing_number"]

    def validate(self, attrs):
        status_value = attrs.get("status", getattr(self.instance, "status", "RADICADA"))
        answer = attrs.get("answer", getattr(self.instance, "answer", ""))
        if status_value in ("RESPONDIDA", "CERRADA") and not (answer or "").strip():
            raise serializers.ValidationError(
                {"answer": "Debe registrar la respuesta antes de marcar la PQRS como respondida o cerrada."}
            )
        return attrs


class PaeParticipantSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    meeting_subject = serializers.CharField(source="meeting.subject", read_only=True)

    class Meta:
        model = PaeParticipant
        fields = ["id", "meeting", "meeting_subject", "full_name", "document", "role",
                  "role_display", "organization", "email", "phone", "user", "is_active"]


class PaeParticipationMeetingSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    meeting_type_name = serializers.CharField(source="meeting_type.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    participants_registered = serializers.IntegerField(source="participants.count", read_only=True)
    commitments_count = serializers.IntegerField(source="commitments.count", read_only=True)

    class Meta:
        model = PaeParticipationMeeting
        fields = [
            "id", "vigencia", "campus", "campus_name", "meeting_type", "meeting_type_name",
            "act_number", "meeting_date", "place", "subject", "agenda", "development",
            "agreements", "attendees_count", "participants_registered", "commitments_count",
            "status", "status_display", "is_active",
        ]


# ===========================================================================
# DOCUMENTOS, EVIDENCIAS E INDICADORES
# ===========================================================================
class PaeDocumentSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    module_display = serializers.CharField(source="get_module_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    responsible_name = serializers.CharField(source="responsible.get_full_name", read_only=True)
    days_to_expire = serializers.IntegerField(read_only=True)
    is_expiring = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaeDocument
        fields = [
            "id", "vigencia", "campus", "campus_name", "document_type", "document_type_name",
            "module", "module_display", "name", "description", "file", "version", "parent_version",
            "document_date", "expires_on", "alert_days", "responsible", "responsible_name",
            "operator", "contract", "status", "status_display", "file_size", "content_type",
            "downloads", "days_to_expire", "is_expiring", "is_expired", "is_active",
        ]
        read_only_fields = ["version", "parent_version", "file_size", "content_type", "downloads"]

    def validate_file(self, value):
        return _validate_upload(value)


class PaeEvidenceSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    module_display = serializers.CharField(source="get_module_display", read_only=True)

    class Meta:
        model = PaeEvidence
        fields = ["id", "vigencia", "campus", "campus_name", "module", "module_display",
                  "reference_id", "reference_label", "kind", "kind_display", "name",
                  "description", "file", "captured_at", "file_size", "is_active"]
        read_only_fields = ["file_size"]

    def validate_file(self, value):
        return _validate_upload(value)


class PaeIndicatorSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    achievement = serializers.FloatField(read_only=True)
    period_display = serializers.CharField(source="get_period_type_display", read_only=True)

    class Meta:
        model = PaeIndicator
        fields = ["id", "vigencia", "campus", "campus_name", "code", "name", "period_type",
                  "period_display", "period_label", "period_start", "period_end", "value",
                  "goal", "unit", "achievement", "calculated_at", "is_active"]
        read_only_fields = fields


class PaeReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source="generated_by.get_full_name", read_only=True)

    class Meta:
        model = PaeReport
        fields = ["id", "vigencia", "code", "name", "parameters", "output_format", "rows",
                  "generated_at", "generated_by", "generated_by_name", "file"]
        read_only_fields = ["generated_at", "generated_by", "rows"]


# ===========================================================================
# SERIALIZERS DE OPERACIONES
# ===========================================================================
class PlanTransitionSerializer(serializers.Serializer):
    status = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class IncidentTransitionSerializer(serializers.Serializer):
    status = serializers.CharField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class BeneficiaryTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in PaeBeneficiary.STATUS_CHOICES])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ScheduleGenerationSerializer(serializers.Serializer):
    plan = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=7), required=False)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
        if (attrs["end_date"] - attrs["start_date"]).days > 400:
            raise serializers.ValidationError({"end_date": "El rango no puede superar 400 dias."})
        return attrs


class VerificationEntrySerializer(serializers.Serializer):
    item = serializers.IntegerField()
    answer = serializers.ChoiceField(choices=["CUMPLE", "NO_CUMPLE", "NO_APLICA"])
    observation = serializers.CharField(required=False, allow_blank=True, default="")


class VerificationSaveSerializer(serializers.Serializer):
    verification = serializers.IntegerField()
    entries = VerificationEntrySerializer(many=True)
    observations = serializers.CharField(required=False, allow_blank=True, default="")


class DeliverySheetRowSerializer(serializers.Serializer):
    """Una fila de la planilla diaria de entregas."""

    schedule = serializers.IntegerField()
    received_rations = serializers.IntegerField(min_value=0)
    delivered_rations = serializers.IntegerField(min_value=0)
    menu_matches = serializers.BooleanField(required=False, default=True)
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    observations = serializers.CharField(required=False, allow_blank=True, default="")


class DeliverySheetSaveSerializer(serializers.Serializer):
    service_date = serializers.DateField()
    rows = DeliverySheetRowSerializer(many=True)
