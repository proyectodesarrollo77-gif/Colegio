"""API REST del modulo PAE."""
from __future__ import annotations

import csv
import datetime as dt
import io

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import HasModulePermission, user_has_permission
from config.viewsets import BaseModelViewSet, ReadOnlyBaseViewSet

from . import imports, services
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
from .serializers import (
    BeneficiaryTransitionSerializer,
    DeliverySheetSaveSerializer,
    IncidentTransitionSerializer,
    PaeBeneficiaryHistorySerializer,
    PaeBeneficiarySerializer,
    PaeCatalogSerializer,
    PaeChecklistItemSerializer,
    PaeChecklistSerializer,
    PaeCommitmentSerializer,
    PaeComplementTypeSerializer,
    PaeContractSerializer,
    PaeDeliverySerializer,
    PaeDocumentSerializer,
    PaeEvidenceSerializer,
    PaeFindingSerializer,
    PaeImprovementActionSerializer,
    PaeIncidentHistorySerializer,
    PaeIncidentSerializer,
    PaeIndicatorSerializer,
    PaeMenuCycleSerializer,
    PaeMenuDaySerializer,
    PaeMenuIngredientSerializer,
    PaeMenuPreparationSerializer,
    PaeModalitySerializer,
    PaeNormativeSerializer,
    PaeOperatorSerializer,
    PaeParticipantSerializer,
    PaeParticipationMeetingSerializer,
    PaePlanSerializer,
    PaePlanStateHistorySerializer,
    PaePqrsSerializer,
    PaePrioritizationSerializer,
    PaeReportSerializer,
    PaeScheduleSerializer,
    PaeSiteDiagnosisSerializer,
    PaeVerificationResultSerializer,
    PaeVerificationSerializer,
    PaeVigenciaSerializer,
    PaeVisitSerializer,
    PlanTransitionSerializer,
    ScheduleGenerationSerializer,
    VerificationSaveSerializer,
)


class PaeScopedViewSet(BaseModelViewSet):
    """
    Base de los recursos PAE.

    Aplica el control por sede: un usuario con perfil COORDINADOR_SEDE u
    OPERADOR_PAE solo ve la informacion de las sedes que tiene asignadas.
    """

    campus_field = "campus"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_super_admin or not self.campus_field:
            return queryset

        if user.role_code == "COORDINADOR_SEDE":
            campus_ids = list(user.coordinated_campuses.values_list("id", flat=True))
            if campus_ids:
                return queryset.filter(**{f"{self.campus_field}__in": campus_ids})

        if user.role_code == "OPERADOR_PAE":
            operator = getattr(user, "pae_operator_profile", None)
            operator = operator.first() if hasattr(operator, "first") else operator
            if operator is not None:
                campus_ids = list(
                    PaeContract.objects.filter(operator=operator).values_list("campuses__id", flat=True)
                )
                campus_ids = [value for value in campus_ids if value]
                if campus_ids:
                    return queryset.filter(**{f"{self.campus_field}__in": campus_ids})
        return queryset


# ===========================================================================
# CONFIGURACION
# ===========================================================================
class PaeNormativeViewSet(BaseModelViewSet):
    module_code = "pae.configuracion"
    queryset = PaeNormative.objects.all()
    serializer_class = PaeNormativeSerializer
    search_fields = ["code", "name", "number", "issuer", "summary"]
    filterset_fields = ["status", "is_active"]
    export_filename = "pae_normativa"


class PaeCatalogViewSet(BaseModelViewSet):
    module_code = "pae.configuracion"
    queryset = PaeCatalog.objects.select_related("normative").all()
    serializer_class = PaeCatalogSerializer
    search_fields = ["code", "name", "description"]
    filterset_fields = ["catalog_type", "is_active", "validation_status"]
    export_filename = "pae_catalogos"

    @action(detail=False, methods=["get"], url_path="types")
    def types(self, request):
        counts = {
            row["catalog_type"]: row["total"]
            for row in PaeCatalog.objects.filter(deleted_at__isnull=True)
            .values("catalog_type")
            .annotate(total=Count("id"))
        }
        return Response({
            "results": [
                {"value": value, "label": label, "count": counts.get(value, 0)}
                for value, label in PaeCatalog.TYPE_CHOICES
            ]
        })


class PaeModalityViewSet(BaseModelViewSet):
    module_code = "pae.configuracion"
    queryset = PaeModality.objects.select_related("institution").all()
    serializer_class = PaeModalitySerializer
    search_fields = ["code", "name"]
    filterset_fields = ["institution", "is_active"]
    export_filename = "pae_modalidades"


class PaeComplementTypeViewSet(BaseModelViewSet):
    module_code = "pae.configuracion"
    queryset = PaeComplementType.objects.select_related("institution", "modality", "shift").all()
    serializer_class = PaeComplementTypeSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["institution", "modality", "shift", "is_active"]
    export_filename = "pae_tipos_complemento"


class PaeVigenciaViewSet(BaseModelViewSet):
    module_code = "pae.configuracion"
    queryset = PaeVigencia.objects.select_related("institution", "school_year", "normative").all()
    serializer_class = PaeVigenciaSerializer
    search_fields = ["name"]
    filterset_fields = ["institution", "school_year", "status", "is_current"]
    export_filename = "pae_vigencias"

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        vigencia = self.get_object()
        PaeVigencia.objects.update(is_current=False)
        vigencia.is_current = True
        vigencia.status = "ACTIVA"
        vigencia.save()
        self.log_action("UPDATE", vigencia)
        return Response({"success": True, "detail": f"{vigencia} definida como vigencia en curso."})

    @action(detail=True, methods=["post"], url_path="refresh-indicators")
    def refresh_indicators(self, request, pk=None):
        vigencia = self.get_object()
        saved = services.refresh_indicators(vigencia, user=request.user)
        self.log_action("PROCESS", vigencia)
        return Response({"success": True, "indicators": saved})


# ===========================================================================
# DIAGNOSTICO Y PRIORIZACION
# ===========================================================================
class PaeSiteDiagnosisViewSet(PaeScopedViewSet):
    module_code = "pae.diagnostico"
    queryset = PaeSiteDiagnosis.objects.select_related("vigencia", "campus", "responsible").all()
    serializer_class = PaeSiteDiagnosisSerializer
    search_fields = ["campus__name", "observations", "territorial_conditions"]
    filterset_fields = ["vigencia", "campus", "zone", "result"]
    export_filename = "pae_diagnosticos"
    export_fields = (
        "vigencia__name", "campus__name", "diagnosis_date", "zone", "infrastructure",
        "kitchen", "dining_room", "storage", "water", "score", "result",
    )

    def perform_create(self, serializer):
        return serializer.save(responsible=self.request.user, created_by=self.request.user)


class PaePrioritizationViewSet(PaeScopedViewSet):
    module_code = "pae.priorizacion"
    queryset = PaePrioritization.objects.select_related(
        "vigencia", "campus", "grade", "group", "shift", "population_type", "responsible"
    ).prefetch_related("criteria").all()
    serializer_class = PaePrioritizationSerializer
    search_fields = ["campus__name", "justification"]
    filterset_fields = ["vigencia", "campus", "grade", "group", "status"]
    approve_field = "status"
    approve_value = "APROBADA"
    export_filename = "pae_priorizacion"

    def perform_create(self, serializer):
        return serializer.save(responsible=self.request.user, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="enroll-beneficiaries")
    def enroll_beneficiaries(self, request, pk=None):
        self.required_action = "create"
        prioritization = self.get_object()
        try:
            result = services.enroll_prioritized_students(prioritization, user=request.user)
        except DjangoValidationError as error:
            return Response(
                {"success": False, "detail": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=http.HTTP_400_BAD_REQUEST,
            )
        self.log_action("PROCESS", prioritization)
        return Response({"success": True, **result})


# ===========================================================================
# BENEFICIARIOS
# ===========================================================================
class PaeBeneficiaryViewSet(PaeScopedViewSet):
    module_code = "pae.beneficiarios"
    queryset = PaeBeneficiary.objects.select_related(
        "vigencia", "student", "enrollment", "campus", "grade", "group", "shift",
        "modality", "complement_type",
    ).all()
    serializer_class = PaeBeneficiarySerializer
    search_fields = ["student__first_name", "student__last_name", "student__document_number", "student__student_code"]
    filterset_fields = ["vigencia", "campus", "grade", "group", "shift", "modality",
                        "complement_type", "status", "has_special_diet"]
    ordering = ["student__last_name", "student__first_name"]
    export_filename = "pae_beneficiarios"
    export_fields = (
        "vigencia__name", "student__document_number", "student__last_name", "student__first_name",
        "campus__name", "grade__name", "group__name", "modality__name", "complement_type__name",
        "start_date", "status",
    )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        self.required_action = "edit"
        beneficiary = self.get_object()
        serializer = BeneficiaryTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_beneficiary_status(
            beneficiary,
            serializer.validated_data["status"],
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        self.log_action("UPDATE", beneficiary)
        return Response({"success": True, "status": beneficiary.status})

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        beneficiary = self.get_object()
        rows = beneficiary.history.select_related("changed_by").order_by("-changed_at")
        return Response({"results": PaeBeneficiaryHistorySerializer(rows, many=True).data})

    @action(detail=False, methods=["get"], url_path="coverage")
    def coverage(self, request):
        from django.db.models import Count

        from core.students.models import Enrollment

        vigencia = _resolve_vigencia(request)
        if vigencia is None:
            return Response({"detail": "No hay vigencia PAE configurada."}, status=http.HTTP_404_NOT_FOUND)

        enrolled = Enrollment.objects.filter(
            school_year=vigencia.school_year, status="ACTIVA", deleted_at__isnull=True
        ).count()
        beneficiaries = PaeBeneficiary.objects.filter(
            vigencia=vigencia, status="ACTIVO", deleted_at__isnull=True
        )
        by_campus = list(
            beneficiaries.values("campus__name").annotate(total=Count("id")).order_by("-total")
        )
        by_grade = list(
            beneficiaries.values("grade__name").annotate(total=Count("id")).order_by("grade__order")
        )
        return Response({
            "vigencia": vigencia.name,
            "enrolled": enrolled,
            "beneficiaries": beneficiaries.count(),
            "coverage": round(beneficiaries.count() / enrolled * 100, 2) if enrolled else 0,
            "by_campus": by_campus,
            "by_grade": by_grade,
        })


class PaeBeneficiaryHistoryViewSet(ReadOnlyBaseViewSet):
    module_code = "pae.beneficiarios"
    queryset = PaeBeneficiaryHistory.objects.select_related("beneficiary", "beneficiary__student", "changed_by").all()
    serializer_class = PaeBeneficiaryHistorySerializer
    filterset_fields = ["beneficiary", "new_status"]
    ordering = ["-changed_at"]


# ===========================================================================
# OPERADORES Y CONTRATOS
# ===========================================================================
class PaeOperatorViewSet(BaseModelViewSet):
    module_code = "pae.operadores"
    queryset = PaeOperator.objects.select_related("institution", "user").all()
    serializer_class = PaeOperatorSerializer
    search_fields = ["code", "business_name", "nit", "legal_representative", "email"]
    filterset_fields = ["institution", "status", "is_active"]
    export_filename = "pae_operadores"

    @action(detail=True, methods=["get"], url_path="performance")
    def performance(self, request, pk=None):
        from django.db.models import Count, Sum

        operator = self.get_object()
        deliveries = PaeDelivery.objects.filter(operator=operator, deleted_at__isnull=True)
        totals = deliveries.aggregate(
            scheduled=Sum("scheduled_rations"),
            received=Sum("received_rations"),
            delivered=Sum("delivered_rations"),
        )
        scheduled = totals["scheduled"] or 0
        delivered = totals["delivered"] or 0
        return Response({
            "operator": operator.business_name,
            "deliveries": deliveries.count(),
            "scheduled": scheduled,
            "received": totals["received"] or 0,
            "delivered": delivered,
            "compliance": round(delivered / scheduled * 100, 2) if scheduled else 0,
            "incidents": PaeIncident.objects.filter(operator=operator, deleted_at__isnull=True).count(),
            "contracts": operator.contracts.filter(deleted_at__isnull=True).count(),
            "verifications": list(
                PaeVerification.objects.filter(operator=operator, deleted_at__isnull=True)
                .values("result").annotate(total=Count("id"))
            ),
        })


class PaeContractViewSet(BaseModelViewSet):
    module_code = "pae.contratos"
    queryset = PaeContract.objects.select_related("vigencia", "operator", "supervisor").prefetch_related(
        "campuses", "modalities"
    ).all()
    serializer_class = PaeContractSerializer
    search_fields = ["number", "subject", "operator__business_name"]
    filterset_fields = ["vigencia", "operator", "status"]
    export_filename = "pae_contratos"
    export_fields = (
        "number", "operator__business_name", "subject", "value", "start_date",
        "end_date", "total_rations", "status",
    )

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        days = int(request.query_params.get("days", 30))
        limit = timezone.localdate() + dt.timedelta(days=days)
        rows = self.filter_queryset(self.get_queryset()).filter(
            status="VIGENTE", end_date__lte=limit
        ).order_by("end_date")
        return Response({"count": rows.count(), "results": PaeContractSerializer(rows, many=True).data})


# ===========================================================================
# PLANEACION
# ===========================================================================
class PaePlanViewSet(PaeScopedViewSet):
    module_code = "pae.planeacion"
    queryset = PaePlan.objects.select_related(
        "vigencia", "institution", "campus", "responsible", "modality",
        "complement_type", "operator", "contract", "menu_cycle",
    ).all()
    serializer_class = PaePlanSerializer
    search_fields = ["code", "name", "campus__name", "observations"]
    filterset_fields = ["vigencia", "campus", "status", "operator", "contract", "modality"]
    export_filename = "pae_planes"
    export_fields = (
        "code", "name", "vigencia__name", "campus__name", "start_date", "end_date",
        "beneficiaries_count", "service_days", "projected_rations", "status",
    )

    def perform_destroy(self, instance):
        if instance.status in ("APROBADO", "EN_EJECUCION", "CERRADO"):
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "No se puede eliminar un plan aprobado, en ejecucion o cerrado."})
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        plan = self.get_object()
        serializer = PlanTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["status"]

        required = dict(plan.allowed_transitions()).get(target, "approve")
        self.required_action = required
        if not user_has_permission(request.user, self.module_code, required):
            return Response(
                {"success": False, "detail": f"Requiere permiso de {required} sobre planeacion PAE."},
                status=http.HTTP_403_FORBIDDEN,
            )
        try:
            services.change_plan_status(plan, target, user=request.user,
                                        reason=serializer.validated_data.get("reason", ""))
        except DjangoValidationError as error:
            return Response(
                {"success": False, "detail": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=http.HTTP_400_BAD_REQUEST,
            )
        self.log_action("APPROVE" if required == "approve" else "UPDATE", plan)
        return Response({"success": True, "status": plan.status})

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        plan = self.get_object()
        rows = plan.state_history.select_related("changed_by").order_by("-changed_at")
        return Response({"results": PaePlanStateHistorySerializer(rows, many=True).data})

    @action(detail=True, methods=["post"], url_path="sync-beneficiaries")
    def sync_beneficiaries(self, request, pk=None):
        self.required_action = "edit"
        plan = self.get_object()
        count = PaeBeneficiary.objects.filter(
            vigencia=plan.vigencia, campus=plan.campus, status="ACTIVO", deleted_at__isnull=True
        ).count()
        plan.beneficiaries_count = count
        plan.projected_rations = count * (plan.service_days or plan.vigencia.service_days)
        plan.save(update_fields=["beneficiaries_count", "projected_rations", "updated_at"])
        return Response({"success": True, "beneficiaries": count, "projected_rations": plan.projected_rations})


class PaePlanStateHistoryViewSet(ReadOnlyBaseViewSet):
    module_code = "pae.planeacion"
    queryset = PaePlanStateHistory.objects.select_related("plan", "changed_by").all()
    serializer_class = PaePlanStateHistorySerializer
    filterset_fields = ["plan", "new_status"]
    ordering = ["-changed_at"]


# ===========================================================================
# MENUS
# ===========================================================================
class PaeMenuCycleViewSet(BaseModelViewSet):
    module_code = "pae.menus"
    queryset = PaeMenuCycle.objects.select_related("vigencia", "modality", "complement_type").all()
    serializer_class = PaeMenuCycleSerializer
    search_fields = ["code", "name", "nutritionist"]
    filterset_fields = ["vigencia", "modality", "complement_type", "status"]
    export_filename = "pae_ciclos_menu"

    @action(detail=True, methods=["get"], url_path="detail")
    def cycle_detail(self, request, pk=None):
        cycle = self.get_object()
        days = cycle.days.filter(deleted_at__isnull=True).prefetch_related(
            "preparations__ingredients"
        ).order_by("day_number")
        return Response({
            "cycle": PaeMenuCycleSerializer(cycle).data,
            "days": PaeMenuDaySerializer(days, many=True).data,
        })

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        self.required_action = "create"
        cycle = self.get_object()
        clone = cycle.create_new_version(user=request.user)
        self.log_action("CREATE", clone)
        return Response({"success": True, "cycle": PaeMenuCycleSerializer(clone).data},
                        status=http.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        self.required_action = "approve"
        cycle = self.get_object()
        PaeMenuCycle.objects.filter(
            vigencia=cycle.vigencia, code=cycle.code, status="VIGENTE"
        ).exclude(pk=cycle.pk).update(status="ARCHIVADO")
        cycle.status = "VIGENTE"
        cycle.save(update_fields=["status", "updated_at"])
        self.log_action("APPROVE", cycle)
        return Response({"success": True, "status": cycle.status})


class PaeMenuDayViewSet(BaseModelViewSet):
    module_code = "pae.menus"
    queryset = PaeMenuDay.objects.select_related("cycle").prefetch_related("preparations").all()
    serializer_class = PaeMenuDaySerializer
    filterset_fields = ["cycle", "weekday"]
    search_fields = ["name", "notes"]
    export_filename = "pae_menu_dias"


class PaeMenuPreparationViewSet(BaseModelViewSet):
    module_code = "pae.menus"
    queryset = PaeMenuPreparation.objects.select_related("day", "day__cycle").prefetch_related("ingredients").all()
    serializer_class = PaeMenuPreparationSerializer
    filterset_fields = ["day", "component"]
    search_fields = ["name", "portion"]
    export_filename = "pae_preparaciones"


class PaeMenuIngredientViewSet(BaseModelViewSet):
    module_code = "pae.menus"
    queryset = PaeMenuIngredient.objects.select_related("preparation", "food_group").all()
    serializer_class = PaeMenuIngredientSerializer
    filterset_fields = ["preparation", "food_group"]
    search_fields = ["name"]
    export_filename = "pae_ingredientes"


# ===========================================================================
# PROGRAMACION Y ENTREGAS
# ===========================================================================
class PaeScheduleViewSet(PaeScopedViewSet):
    module_code = "pae.programacion"
    queryset = PaeSchedule.objects.select_related(
        "plan", "campus", "shift", "operator", "complement_type", "menu_day"
    ).all()
    serializer_class = PaeScheduleSerializer
    search_fields = ["plan__name", "campus__name", "observations"]
    filterset_fields = ["plan", "campus", "shift", "operator", "status", "service_date"]
    ordering = ["-service_date"]
    export_filename = "pae_programacion"
    export_fields = (
        "service_date", "campus__name", "plan__name", "operator__business_name",
        "beneficiaries_count", "scheduled_rations", "status",
    )

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        self.required_action = "create"
        serializer = ScheduleGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(PaePlan, pk=serializer.validated_data["plan"])

        if plan.status not in ("APROBADO", "EN_EJECUCION"):
            return Response(
                {"success": False, "detail": "Solo se programa sobre planes aprobados o en ejecucion."},
                status=http.HTTP_400_BAD_REQUEST,
            )

        result = services.generate_schedules(
            plan,
            serializer.validated_data["start_date"],
            serializer.validated_data["end_date"],
            serializer.validated_data.get("weekdays"),
            user=request.user,
        )
        self.log_action("PROCESS", plan)
        return Response({"success": True, **result})


class PaeDeliveryViewSet(PaeScopedViewSet):
    module_code = "pae.entregas"
    queryset = PaeDelivery.objects.select_related(
        "plan", "campus", "shift", "operator", "complement_type", "responsible",
        "noncompliance_cause", "contract",
    ).all()
    serializer_class = PaeDeliverySerializer
    search_fields = ["plan__name", "campus__name", "justification", "observations"]
    filterset_fields = ["plan", "campus", "shift", "operator", "status", "service_date", "menu_matches"]
    ordering = ["-service_date"]
    export_filename = "pae_entregas"
    export_fields = (
        "service_date", "campus__name", "operator__business_name", "scheduled_rations",
        "received_rations", "delivered_rations", "missing_rations", "undelivered_rations",
        "compliance", "status",
    )

    def perform_create(self, serializer):
        instance = serializer.save(responsible=self.request.user, created_by=self.request.user)
        self.log_action("CREATE", instance)
        self._post_delivery(instance)
        return instance

    def perform_update(self, serializer):
        instance = super().perform_update(serializer)
        self._post_delivery(instance)
        return instance

    def _post_delivery(self, delivery):
        """Marca la entrega con novedad y actualiza la programacion asociada."""
        if delivery.has_noncompliance and delivery.status == "REGISTRADA":
            PaeDelivery.objects.filter(pk=delivery.pk).update(status="CON_NOVEDAD")
        if delivery.schedule_id:
            PaeSchedule.objects.filter(pk=delivery.schedule_id).update(status="EJECUTADA")

    @action(detail=True, methods=["post"], url_path="create-incident")
    def create_incident(self, request, pk=None):
        """Genera una novedad a partir del incumplimiento de una entrega."""
        self.required_action = "create"
        delivery = self.get_object()
        if not delivery.has_noncompliance:
            return Response(
                {"success": False, "detail": "La entrega no registra incumplimiento."},
                status=http.HTTP_400_BAD_REQUEST,
            )
        incident_type = PaeCatalog.objects.filter(
            catalog_type=PaeCatalog.TYPE_INCIDENT, code="ENTREGA_INCOMPLETA"
        ).first()
        incident = PaeIncident.objects.create(
            vigencia=delivery.plan.vigencia,
            campus=delivery.campus,
            delivery=delivery,
            operator=delivery.operator,
            incident_type=incident_type,
            description=(
                f"Entrega del {delivery.service_date}: {delivery.missing_rations} racion(es) faltante(s) y "
                f"{delivery.undelivered_rations} no entregada(s). {delivery.justification}"
            ).strip(),
            priority="ALTA" if delivery.missing_rations > 10 else "MEDIA",
            reported_by=request.user,
            due_date=timezone.localdate() + dt.timedelta(days=5),
            created_by=request.user,
        )
        self.log_action("CREATE", incident)
        return Response({"success": True, "incident": PaeIncidentSerializer(incident).data},
                        status=http.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        from django.db.models import Avg, Sum

        queryset = self.filter_queryset(self.get_queryset())
        totals = queryset.aggregate(
            scheduled=Sum("scheduled_rations"),
            received=Sum("received_rations"),
            delivered=Sum("delivered_rations"),
            average=Avg("compliance"),
        )
        scheduled = totals["scheduled"] or 0
        delivered = totals["delivered"] or 0
        return Response({
            "deliveries": queryset.count(),
            "scheduled": scheduled,
            "received": totals["received"] or 0,
            "delivered": delivered,
            "missing": max(scheduled - (totals["received"] or 0), 0),
            "compliance": round(delivered / scheduled * 100, 2) if scheduled else 0,
            "average_compliance": round(float(totals["average"] or 0), 2),
            "with_incidents": queryset.filter(status="CON_NOVEDAD").count(),
        })


# ===========================================================================
# CONTROL DE CALIDAD
# ===========================================================================
class PaeChecklistViewSet(BaseModelViewSet):
    module_code = "pae.control"
    queryset = PaeChecklist.objects.select_related("vigencia", "normative").prefetch_related("items").all()
    serializer_class = PaeChecklistSerializer
    search_fields = ["code", "name", "description"]
    filterset_fields = ["vigencia", "scope", "is_active"]
    export_filename = "pae_listas_verificacion"


class PaeChecklistItemViewSet(BaseModelViewSet):
    module_code = "pae.control"
    queryset = PaeChecklistItem.objects.select_related("checklist", "category").all()
    serializer_class = PaeChecklistItemSerializer
    search_fields = ["criterion", "code", "normative_reference"]
    filterset_fields = ["checklist", "category", "is_critical"]
    export_filename = "pae_criterios_verificacion"


class PaeVerificationViewSet(PaeScopedViewSet):
    module_code = "pae.control"
    queryset = PaeVerification.objects.select_related(
        "checklist", "vigencia", "campus", "operator", "responsible", "delivery"
    ).prefetch_related("results__item").all()
    serializer_class = PaeVerificationSerializer
    search_fields = ["campus__name", "observations"]
    filterset_fields = ["checklist", "vigencia", "campus", "operator", "result", "verification_date"]
    ordering = ["-verification_date"]
    export_filename = "pae_verificaciones"
    export_fields = (
        "verification_date", "campus__name", "checklist__name", "total_items",
        "compliant_items", "noncompliant_items", "critical_failures", "score", "result",
    )

    def perform_create(self, serializer):
        instance = serializer.save(responsible=self.request.user, created_by=self.request.user)
        # Precarga los criterios de la lista como resultados sin evaluar.
        items = instance.checklist.items.filter(deleted_at__isnull=True).order_by("order")
        PaeVerificationResult.objects.bulk_create([
            PaeVerificationResult(verification=instance, item=item, answer="CUMPLE",
                                  created_by=self.request.user)
            for item in items
        ])
        instance.recalculate()
        self.log_action("CREATE", instance)
        return instance


class PaeVerificationResultViewSet(BaseModelViewSet):
    module_code = "pae.control"
    queryset = PaeVerificationResult.objects.select_related("verification", "item").all()
    serializer_class = PaeVerificationResultSerializer
    filterset_fields = ["verification", "answer"]
    export_filename = "pae_resultados_verificacion"


# ===========================================================================
# VISITAS, HALLAZGOS Y NOVEDADES
# ===========================================================================
class PaeVisitViewSet(PaeScopedViewSet):
    module_code = "pae.visitas"
    queryset = PaeVisit.objects.select_related(
        "vigencia", "campus", "operator", "visit_type", "responsible", "verification"
    ).all()
    serializer_class = PaeVisitSerializer
    search_fields = ["number", "campus__name", "objective", "conclusions"]
    filterset_fields = ["vigencia", "campus", "operator", "visit_type", "status", "visit_date"]
    ordering = ["-visit_date"]
    export_filename = "pae_visitas"
    export_fields = ("number", "visit_date", "campus__name", "visit_type__name",
                     "responsible__first_name", "status")

    def perform_create(self, serializer):
        return serializer.save(responsible=self.request.user, created_by=self.request.user)


class PaeFindingViewSet(PaeScopedViewSet):
    module_code = "pae.visitas"
    queryset = PaeFinding.objects.select_related("visit", "verification", "campus", "finding_type").all()
    serializer_class = PaeFindingSerializer
    search_fields = ["description", "code", "normative_reference"]
    filterset_fields = ["visit", "campus", "finding_type", "severity", "status"]
    export_filename = "pae_hallazgos"
    export_fields = ("detected_on", "campus__name", "finding_type__name", "severity",
                     "description", "status")

    @action(detail=True, methods=["post"], url_path="create-action")
    def create_action(self, request, pk=None):
        """Genera el plan de mejoramiento asociado a un hallazgo."""
        self.required_action = "create"
        finding = self.get_object()
        vigencia = finding.visit.vigencia if finding.visit_id else _resolve_vigencia(request)
        if vigencia is None:
            return Response({"success": False, "detail": "No fue posible determinar la vigencia."},
                            status=http.HTTP_400_BAD_REQUEST)
        action_obj = PaeImprovementAction.objects.create(
            vigencia=vigencia,
            campus=finding.campus,
            finding=finding,
            finding_description=finding.description,
            action=request.data.get("action", "Definir accion de mejora."),
            due_date=request.data.get("due_date") or (timezone.localdate() + dt.timedelta(days=30)),
            responsible=request.user,
            created_by=request.user,
        )
        finding.status = "EN_TRATAMIENTO"
        finding.save(update_fields=["status", "updated_at"])
        self.log_action("CREATE", action_obj)
        return Response({"success": True, "action": PaeImprovementActionSerializer(action_obj).data},
                        status=http.HTTP_201_CREATED)


class PaeIncidentViewSet(PaeScopedViewSet):
    module_code = "pae.novedades"
    queryset = PaeIncident.objects.select_related(
        "vigencia", "campus", "delivery", "operator", "incident_type", "reported_by", "assigned_to"
    ).all()
    serializer_class = PaeIncidentSerializer
    search_fields = ["number", "description", "campus__name", "solution"]
    filterset_fields = ["vigencia", "campus", "operator", "incident_type", "status", "priority"]
    ordering = ["-reported_on"]
    export_filename = "pae_novedades"
    export_fields = ("number", "reported_on", "campus__name", "incident_type__name",
                     "priority", "description", "status")

    def perform_create(self, serializer):
        instance = serializer.save(reported_by=self.request.user, created_by=self.request.user)
        PaeIncidentHistory.objects.create(
            incident=instance, previous_status="", new_status=instance.status,
            comment="Novedad reportada", changed_by=self.request.user, created_by=self.request.user,
        )
        self.log_action("CREATE", instance)
        self._notify(instance)
        return instance

    def _notify(self, incident):
        from core.notifications.models import Notification

        if incident.assigned_to_id:
            Notification.push(
                recipient=incident.assigned_to,
                title=f"Novedad PAE asignada: {incident.number}",
                message=incident.description[:240],
                level="warning" if incident.priority in ("ALTA", "CRITICA") else "info",
                url="/pae/novedades/",
                module="pae.novedades",
                icon="alert-triangle",
            )

    @action(detail=True, methods=["patch", "post"], url_path="estado")
    def change_state(self, request, pk=None):
        self.required_action = "edit"
        incident = self.get_object()
        serializer = IncidentTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.change_incident_status(
                incident,
                serializer.validated_data["status"],
                user=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except DjangoValidationError as error:
            return Response(
                {"success": False, "detail": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=http.HTTP_400_BAD_REQUEST,
            )
        self.log_action("UPDATE", incident)
        return Response({"success": True, "status": incident.status})

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        incident = self.get_object()
        rows = incident.history.select_related("changed_by").order_by("-changed_at")
        return Response({"results": PaeIncidentHistorySerializer(rows, many=True).data})


class PaeIncidentHistoryViewSet(ReadOnlyBaseViewSet):
    module_code = "pae.novedades"
    queryset = PaeIncidentHistory.objects.select_related("incident", "changed_by").all()
    serializer_class = PaeIncidentHistorySerializer
    filterset_fields = ["incident", "new_status"]
    ordering = ["-changed_at"]


class PaeImprovementActionViewSet(PaeScopedViewSet):
    module_code = "pae.mejoramiento"
    queryset = PaeImprovementAction.objects.select_related(
        "vigencia", "campus", "finding", "incident", "responsible", "verified_by"
    ).all()
    serializer_class = PaeImprovementActionSerializer
    search_fields = ["code", "action", "finding_description", "root_cause", "indicator"]
    filterset_fields = ["vigencia", "campus", "status", "responsible"]
    ordering = ["due_date"]
    export_filename = "pae_planes_mejoramiento"
    export_fields = ("code", "campus__name", "finding_description", "action",
                     "start_date", "due_date", "progress", "status")

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        self.required_action = "approve"
        action_obj = self.get_object()
        action_obj.verification_note = request.data.get("verification_note", action_obj.verification_note)
        try:
            services.validate_action_close(action_obj)
        except DjangoValidationError as error:
            return Response(
                {"success": False, "detail": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=http.HTTP_400_BAD_REQUEST,
            )
        action_obj.status = "CERRADA"
        action_obj.progress = 100
        action_obj.verified_by = request.user
        action_obj.verified_at = timezone.now()
        action_obj.closed_at = timezone.now()
        action_obj.save()
        if action_obj.finding_id:
            PaeFinding.objects.filter(pk=action_obj.finding_id).update(
                status="CERRADO", closed_at=timezone.now()
            )
        self.log_action("APPROVE", action_obj)
        return Response({"success": True, "status": action_obj.status})

    @action(detail=False, methods=["get"], url_path="overdue")
    def overdue(self, request):
        rows = self.filter_queryset(self.get_queryset()).exclude(
            status__in=["CERRADA", "VERIFICADA"]
        ).filter(due_date__lt=timezone.localdate()).order_by("due_date")
        return Response({"count": rows.count(),
                         "results": PaeImprovementActionSerializer(rows, many=True).data})


# ===========================================================================
# PQRS Y PARTICIPACION
# ===========================================================================
class PaePqrsViewSet(PaeScopedViewSet):
    module_code = "pae.pqrs"
    queryset = PaePqrs.objects.select_related("vigencia", "campus", "pqrs_type", "responsible").all()
    serializer_class = PaePqrsSerializer
    search_fields = ["filing_number", "description", "applicant_name", "answer"]
    filterset_fields = ["vigencia", "campus", "kind", "status", "channel"]
    ordering = ["-filed_on"]
    export_filename = "pae_pqrs"
    export_fields = ("filing_number", "filed_on", "kind", "campus__name",
                     "description", "status", "answered_on")

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        if not instance.due_date:
            instance.due_date = instance.filed_on + dt.timedelta(days=15)
            instance.save(update_fields=["due_date"])
        self.log_action("CREATE", instance)
        return instance


class PaeParticipationMeetingViewSet(PaeScopedViewSet):
    module_code = "pae.participacion"
    queryset = PaeParticipationMeeting.objects.select_related(
        "vigencia", "campus", "meeting_type"
    ).prefetch_related("participants", "commitments").all()
    serializer_class = PaeParticipationMeetingSerializer
    search_fields = ["act_number", "subject", "agenda", "agreements"]
    filterset_fields = ["vigencia", "campus", "meeting_type", "status"]
    ordering = ["-meeting_date"]
    export_filename = "pae_participacion"


class PaeParticipantViewSet(BaseModelViewSet):
    module_code = "pae.participacion"
    queryset = PaeParticipant.objects.select_related("meeting", "user").all()
    serializer_class = PaeParticipantSerializer
    search_fields = ["full_name", "document", "organization"]
    filterset_fields = ["meeting", "role"]
    export_filename = "pae_participantes"


class PaeCommitmentViewSet(BaseModelViewSet):
    module_code = "pae.participacion"
    queryset = PaeCommitment.objects.select_related("visit", "meeting", "responsible_user").all()
    serializer_class = PaeCommitmentSerializer
    search_fields = ["description", "responsible_name", "follow_up"]
    filterset_fields = ["visit", "meeting", "status"]
    export_filename = "pae_compromisos"


# ===========================================================================
# DOCUMENTOS, EVIDENCIAS, INDICADORES
# ===========================================================================
class PaeDocumentViewSet(PaeScopedViewSet):
    module_code = "pae.documentos"
    queryset = PaeDocument.objects.select_related(
        "vigencia", "campus", "document_type", "responsible", "operator", "contract"
    ).all()
    serializer_class = PaeDocumentSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["vigencia", "campus", "document_type", "module", "status", "operator"]
    ordering = ["-document_date"]
    export_filename = "pae_documentos"
    export_fields = ("name", "module", "document_type__name", "version", "document_date",
                     "expires_on", "status")

    def perform_create(self, serializer):
        return serializer.save(responsible=self.request.user, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        """Registra una nueva version conservando el historial documental."""
        self.required_action = "create"
        document = self.get_object()
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"success": False, "detail": "Adjunte el archivo de la nueva version."},
                            status=http.HTTP_400_BAD_REQUEST)
        new_document = PaeDocument.objects.create(
            vigencia=document.vigencia, campus=document.campus, document_type=document.document_type,
            module=document.module, name=document.name, description=request.data.get("description", ""),
            file=upload, version=document.version + 1, parent_version=document,
            document_date=timezone.localdate(), expires_on=document.expires_on,
            alert_days=document.alert_days, responsible=request.user, operator=document.operator,
            contract=document.contract, created_by=request.user,
        )
        document.status = "ARCHIVADO"
        document.save(update_fields=["status", "updated_at"])
        self.log_action("CREATE", new_document)
        return Response({"success": True, "document": PaeDocumentSerializer(new_document).data},
                        status=http.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        document = self.get_object()
        root = document
        while root.parent_version_id:
            root = root.parent_version
        chain = [root]
        current = root
        while True:
            nxt = current.new_versions.filter(deleted_at__isnull=True).first()
            if nxt is None:
                break
            chain.append(nxt)
            current = nxt
        return Response({"results": PaeDocumentSerializer(chain, many=True).data})

    @action(detail=True, methods=["post"], url_path="register-download")
    def register_download(self, request, pk=None):
        document = self.get_object()
        PaeDocument.objects.filter(pk=document.pk).update(downloads=document.downloads + 1)
        return Response({"success": True, "downloads": document.downloads + 1})


class PaeEvidenceViewSet(PaeScopedViewSet):
    module_code = "pae.evidencias"
    queryset = PaeEvidence.objects.select_related("vigencia", "campus").all()
    serializer_class = PaeEvidenceSerializer
    search_fields = ["name", "description", "reference_label"]
    filterset_fields = ["vigencia", "campus", "module", "kind", "reference_id"]
    ordering = ["-captured_at"]
    export_filename = "pae_evidencias"


class PaeIndicatorViewSet(ReadOnlyBaseViewSet):
    module_code = "pae.indicadores"
    queryset = PaeIndicator.objects.select_related("vigencia", "campus").all()
    serializer_class = PaeIndicatorSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["vigencia", "campus", "code", "period_type"]
    ordering = ["code"]


class PaeReportViewSet(BaseModelViewSet):
    module_code = "pae.informes"
    queryset = PaeReport.objects.select_related("vigencia", "generated_by").all()
    serializer_class = PaeReportSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["vigencia", "code", "output_format"]
    ordering = ["-generated_at"]
    export_filename = "pae_informes"

    def perform_create(self, serializer):
        return serializer.save(generated_by=self.request.user, created_by=self.request.user)


# ===========================================================================
# ENDPOINTS ESPECIALIZADOS
# ===========================================================================
def _resolve_vigencia(request):
    params = request.query_params if hasattr(request, "query_params") else request.GET
    vigencia_id = params.get("vigencia") or (request.data.get("vigencia") if hasattr(request, "data") else None)
    if vigencia_id:
        return PaeVigencia.objects.filter(pk=vigencia_id, deleted_at__isnull=True).first()
    return PaeVigencia.current()


class PaeDashboardAPIView(APIView):
    """Tablero completo del PAE con filtros por vigencia, sede, jornada y operador."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "pae.dashboard"

    def get(self, request):
        vigencia = _resolve_vigencia(request)
        filters = services.dashboard_filters(request)
        return Response(services.build_dashboard(vigencia, filters))


class PaeVerificationSheetAPIView(APIView):
    """Planilla de aplicacion de una lista de verificacion."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "pae.control"

    def get(self, request):
        verification = get_object_or_404(PaeVerification, pk=request.query_params.get("verification"))
        results = verification.results.select_related("item", "item__category").order_by(
            "item__category__order", "item__order"
        )
        categories = {}
        for row in results:
            key = row.item.category.name if row.item and row.item.category_id else "General"
            categories.setdefault(key, []).append({
                "result_id": row.id,
                "item_id": row.item_id,
                "criterion": row.item.criterion if row.item else "",
                "is_critical": row.item.is_critical if row.item else False,
                "requires_evidence": row.item.requires_evidence if row.item else False,
                "weight": float(row.item.weight) if row.item else 1.0,
                "answer": row.answer,
                "observation": row.observation,
            })
        return Response({
            "verification": PaeVerificationSerializer(verification).data,
            # Umbrales parametrizables de la lista: el frontend los usa para
            # anticipar el resultado, pero el calculo definitivo es del backend.
            "thresholds": {
                "full": float(verification.checklist.threshold_full),
                "partial": float(verification.checklist.threshold_partial),
            },
            "categories": [{"name": name, "items": items} for name, items in categories.items()],
        })

    @transaction.atomic
    def post(self, request):
        self.required_action = "edit"
        serializer = VerificationSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = get_object_or_404(PaeVerification, pk=serializer.validated_data["verification"])

        saved = 0
        for entry in serializer.validated_data["entries"]:
            updated = PaeVerificationResult.objects.filter(
                verification=verification, item_id=entry["item"]
            ).update(
                answer=entry["answer"],
                observation=entry.get("observation", ""),
                updated_by=request.user,
            )
            saved += updated

        verification.observations = serializer.validated_data.get("observations", verification.observations)
        verification.updated_by = request.user
        verification.save(update_fields=["observations", "updated_by", "updated_at"])
        verification.recalculate()

        from core.audit.services import register_audit

        register_audit(
            user=request.user, action="UPDATE", module=self.module_code, instance=verification,
            request=request, description=f"Verificacion aplicada: {saved} criterios",
        )
        return Response({
            "success": True, "saved": saved,
            "verification": PaeVerificationSerializer(verification).data,
        })


class PaeDeliverySheetAPIView(APIView):
    """Planilla diaria de entregas: carga la programacion del dia y guarda el registro."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "pae.entregas"

    def get(self, request):
        service_date = request.query_params.get("date") or timezone.localdate().isoformat()
        plan_id = request.query_params.get("plan")

        schedules = PaeSchedule.objects.filter(
            service_date=service_date, deleted_at__isnull=True
        ).select_related("plan", "campus", "shift", "operator", "complement_type", "menu_day")
        if plan_id:
            schedules = schedules.filter(plan_id=plan_id)

        rows = []
        for schedule in schedules:
            delivery = PaeDelivery.objects.filter(schedule=schedule, deleted_at__isnull=True).first()
            rows.append({
                "schedule_id": schedule.id,
                "plan_id": schedule.plan_id,
                "plan": schedule.plan.name,
                "campus_id": schedule.campus_id,
                "campus": schedule.campus.name,
                "shift_id": schedule.shift_id,
                "shift": schedule.shift.name if schedule.shift_id else "",
                "operator_id": schedule.operator_id,
                "operator": schedule.operator.business_name if schedule.operator_id else "",
                "complement_id": schedule.complement_type_id,
                "complement": schedule.complement_type.name if schedule.complement_type_id else "",
                "menu": schedule.menu_day.name if schedule.menu_day_id else "",
                "menu_id": schedule.menu_day_id,
                "beneficiaries": schedule.beneficiaries_count,
                "scheduled": schedule.scheduled_rations,
                "delivery_id": delivery.id if delivery else None,
                "received": delivery.received_rations if delivery else None,
                "delivered": delivery.delivered_rations if delivery else None,
                "compliance": float(delivery.compliance) if delivery else None,
                "status": delivery.status if delivery else "PENDIENTE",
            })
        return Response({"date": service_date, "rows": rows})

    @transaction.atomic
    def post(self, request):
        """Guarda en bloque la planilla del dia aplicando las reglas 1, 2 y 3."""
        self.required_action = "edit"
        serializer = DeliverySheetSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_date = serializer.validated_data["service_date"]

        saved, errors = [], {}
        for index, row in enumerate(serializer.validated_data["rows"]):
            schedule = PaeSchedule.objects.filter(
                pk=row["schedule"], service_date=service_date, deleted_at__isnull=True
            ).select_related("plan").first()
            if schedule is None:
                errors[str(index)] = {"schedule": "La programacion no existe para la fecha indicada."}
                continue

            delivery = PaeDelivery.objects.filter(schedule=schedule, deleted_at__isnull=True).first()
            if delivery is None:
                delivery = PaeDelivery(schedule=schedule, created_by=request.user)

            delivery.plan = schedule.plan
            delivery.contract = schedule.plan.contract
            delivery.service_date = schedule.service_date
            delivery.campus = schedule.campus
            delivery.shift = schedule.shift
            delivery.operator = schedule.operator
            delivery.complement_type = schedule.complement_type
            delivery.scheduled_menu = schedule.menu_day
            delivery.scheduled_beneficiaries = schedule.beneficiaries_count
            delivery.scheduled_rations = schedule.scheduled_rations
            delivery.received_rations = row["received_rations"]
            delivery.delivered_rations = row["delivered_rations"]
            delivery.menu_matches = row.get("menu_matches", True)
            delivery.justification = row.get("justification", "")
            delivery.observations = row.get("observations", "")
            delivery.responsible = delivery.responsible or request.user
            delivery.updated_by = request.user
            delivery.compute_totals()
            delivery.status = "CON_NOVEDAD" if delivery.has_noncompliance else "REGISTRADA"

            row_errors = services.validate_delivery(delivery, raise_error=False)
            if row_errors:
                errors[str(index)] = row_errors
                continue

            delivery.save()
            saved.append(delivery.id)

        if errors:
            transaction.set_rollback(True)
            return Response(
                {"success": False, "errors": errors, "detail": "La planilla contiene filas con errores."},
                status=http.HTTP_400_BAD_REQUEST,
            )

        from core.audit.services import register_audit

        register_audit(
            user=request.user, action="UPDATE", module=self.module_code, instance=None,
            request=request, description=f"Planilla de entregas {service_date}: {len(saved)} registros",
        )
        return Response({"success": True, "saved": len(saved), "deliveries": saved})


class PaeImportAPIView(APIView):
    """
    Importacion masiva de beneficiarios, programaciones y ciclos de menu.

    GET  devuelve las plantillas disponibles o descarga una en CSV.
    POST procesa el archivo; con `dry_run` solo valida y no guarda nada.
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    parser_classes = [MultiPartParser, FormParser]
    module_code = "pae.beneficiarios"

    MODULE_BY_KIND = {
        "beneficiarios": "pae.beneficiarios",
        "estudiantes": "pae.beneficiarios",
        "programacion": "pae.programacion",
        "menus": "pae.menus",
    }

    def initial(self, request, *args, **kwargs):
        kind = request.query_params.get("kind") or request.data.get("kind") or "beneficiarios"
        self.module_code = self.MODULE_BY_KIND.get(kind, "pae.beneficiarios")
        super().initial(request, *args, **kwargs)

    def get(self, request):
        kind = request.query_params.get("kind")
        if not kind:
            return Response({
                "results": [
                    {"kind": key, "label": value["label"], "required": value["required"]}
                    for key, value in imports.TEMPLATES.items()
                ]
            })
        if kind not in imports.TEMPLATES:
            return Response({"success": False, "detail": "Tipo de importacion no reconocido."},
                            status=http.HTTP_400_BAD_REQUEST)

        template = imports.template_rows(kind)
        if request.query_params.get("download") not in ("1", "true", "True"):
            return Response(template)

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(template["headers"])
        writer.writerow(template["descriptions"])
        writer.writerow(template["example"])
        response = HttpResponse(buffer.getvalue().encode("utf-8-sig"), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="plantilla_pae_{kind}.csv"'
        return response

    def post(self, request):
        self.required_action = "create"
        kind = request.data.get("kind") or "beneficiarios"
        dry_run = str(request.data.get("dry_run", "")).lower() in ("1", "true", "si")
        vigencia = _resolve_vigencia(request)

        try:
            result = imports.run_import(
                kind, request.FILES.get("file"), vigencia, user=request.user, dry_run=dry_run
            )
        except DjangoValidationError as error:
            return Response(
                {"success": False,
                 "detail": error.message_dict if hasattr(error, "message_dict") else error.messages},
                status=http.HTTP_400_BAD_REQUEST,
            )

        payload = result.as_dict()
        if not result.has_errors and not dry_run:
            from core.audit.services import register_audit

            register_audit(
                user=request.user, action="PROCESS", module=self.module_code, request=request,
                description=(f"Importacion {kind}: {result.created} creados, "
                             f"{result.updated} actualizados"),
            )
        status_code = http.HTTP_400_BAD_REQUEST if result.has_errors else http.HTTP_200_OK
        return Response(payload, status=status_code)


class PaeAlertsAPIView(APIView):
    """Alertas operativas del programa."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_code = "pae.dashboard"

    def get(self, request):
        vigencia = _resolve_vigencia(request)
        return Response({"results": services.build_alerts(vigencia)})

    def post(self, request):
        vigencia = _resolve_vigencia(request)
        sent = services.notify_alerts(vigencia, user=request.user)
        return Response({"success": True, "notifications": sent})


ROUTES = [
    # Configuracion
    ("pae/normativa", PaeNormativeViewSet, "paenormative"),
    ("pae/catalogos", PaeCatalogViewSet, "paecatalog"),
    ("pae/modalidades", PaeModalityViewSet, "paemodality"),
    ("pae/tipos-complemento", PaeComplementTypeViewSet, "paecomplementtype"),
    ("pae/vigencias", PaeVigenciaViewSet, "paevigencia"),
    # Diagnostico y priorizacion
    ("pae/diagnosticos", PaeSiteDiagnosisViewSet, "paesitediagnosis"),
    ("pae/priorizaciones", PaePrioritizationViewSet, "paeprioritization"),
    # Beneficiarios
    ("pae/beneficiarios", PaeBeneficiaryViewSet, "paebeneficiary"),
    ("pae/beneficiarios-historial", PaeBeneficiaryHistoryViewSet, "paebeneficiaryhistory"),
    # Operadores y contratos
    ("pae/operadores", PaeOperatorViewSet, "paeoperator"),
    ("pae/contratos", PaeContractViewSet, "paecontract"),
    # Planeacion
    ("pae/planes", PaePlanViewSet, "paeplan"),
    ("pae/planes-historial", PaePlanStateHistoryViewSet, "paeplanhistory"),
    # Menus
    ("pae/menus", PaeMenuCycleViewSet, "paemenucycle"),
    ("pae/menu-dias", PaeMenuDayViewSet, "paemenuday"),
    ("pae/menu-preparaciones", PaeMenuPreparationViewSet, "paemenupreparation"),
    ("pae/menu-ingredientes", PaeMenuIngredientViewSet, "paemenuingredient"),
    # Programacion y entregas
    ("pae/programacion", PaeScheduleViewSet, "paeschedule"),
    ("pae/entregas", PaeDeliveryViewSet, "paedelivery"),
    # Control de calidad
    ("pae/listas-verificacion", PaeChecklistViewSet, "paechecklist"),
    ("pae/criterios-verificacion", PaeChecklistItemViewSet, "paechecklistitem"),
    ("pae/verificaciones", PaeVerificationViewSet, "paeverification"),
    ("pae/verificacion-resultados", PaeVerificationResultViewSet, "paeverificationresult"),
    # Visitas y novedades
    ("pae/visitas", PaeVisitViewSet, "paevisit"),
    ("pae/hallazgos", PaeFindingViewSet, "paefinding"),
    ("pae/novedades", PaeIncidentViewSet, "paeincident"),
    ("pae/novedades-historial", PaeIncidentHistoryViewSet, "paeincidenthistory"),
    ("pae/mejoramiento", PaeImprovementActionViewSet, "paeimprovementaction"),
    # PQRS y participacion
    ("pae/pqrs", PaePqrsViewSet, "paepqrs"),
    ("pae/participacion", PaeParticipationMeetingViewSet, "paemeeting"),
    ("pae/participantes", PaeParticipantViewSet, "paeparticipant"),
    ("pae/compromisos", PaeCommitmentViewSet, "paecommitment"),
    # Documentos e indicadores
    ("pae/documentos", PaeDocumentViewSet, "paedocument"),
    ("pae/evidencias", PaeEvidenceViewSet, "paeevidence"),
    ("pae/indicadores", PaeIndicatorViewSet, "paeindicator"),
    ("pae/informes", PaeReportViewSet, "paereport"),
]
