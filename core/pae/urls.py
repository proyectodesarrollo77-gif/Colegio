"""
Rutas HTML del modulo de Gestion Integral del PAE.

Se montan bajo /pae/ desde config/urls.py. Cada ruta reutiliza la
infraestructura declarativa de `config.resource`, por lo que no introduce
plantillas ni estilos nuevos fuera de `templates/pae/`.
"""
from django.urls import path

from . import views

app_name = "pae"

urlpatterns = [
    # 1. Dashboard
    path("", views.PaeDashboardView.as_view(), name="dashboard"),
    # 2. Configuracion del programa
    path("configuracion/", views.PaeConfigurationView.as_view(), name="configuration"),
    path("configuracion/vigencias/", views.PaeVigenciaView.as_view(), name="vigencias"),
    path("configuracion/normativa/", views.PaeNormativeView.as_view(), name="normative"),
    path("configuracion/catalogos/", views.PaeCatalogView.as_view(), name="catalogs"),
    path("configuracion/modalidades/", views.PaeModalityView.as_view(), name="modalities"),
    path("configuracion/complementos/", views.PaeComplementTypeView.as_view(), name="complement_types"),
    # 3. Diagnostico de sedes
    path("diagnostico/", views.PaeDiagnosisView.as_view(), name="diagnosis"),
    # 4. Priorizacion
    path("priorizacion/", views.PaePrioritizationView.as_view(), name="prioritization"),
    # 5. Beneficiarios
    path("beneficiarios/", views.PaeBeneficiaryView.as_view(), name="beneficiaries"),
    path("importar/", views.PaeImportView.as_view(), name="import"),
    # 6. Planeacion
    path("planeacion/", views.PaePlanView.as_view(), name="plans"),
    # 7. Ciclos de menu
    path("menus/", views.PaeMenuCycleView.as_view(), name="menus"),
    path("menus/dias/", views.PaeMenuDayView.as_view(), name="menu_days"),
    path("menus/preparaciones/", views.PaeMenuPreparationView.as_view(), name="menu_preparations"),
    path("menus/ingredientes/", views.PaeMenuIngredientView.as_view(), name="menu_ingredients"),
    path("menus/<int:pk>/imprimir/", views.menu_cycle_print, name="menu_print"),
    # 8. Operadores
    path("operadores/", views.PaeOperatorView.as_view(), name="operators"),
    # 9. Contratos
    path("contratos/", views.PaeContractView.as_view(), name="contracts"),
    # 10. Programacion
    path("programacion/", views.PaeScheduleView.as_view(), name="schedules"),
    # 11. Entregas diarias
    path("entregas/", views.PaeDeliveryView.as_view(), name="deliveries"),
    path("entregas/planilla/", views.PaeDeliverySheetView.as_view(), name="delivery_sheet"),
    path("entregas/<int:pk>/imprimir/", views.delivery_print, name="delivery_print"),
    # 12. Control de calidad
    path("control-calidad/", views.PaeQualityControlView.as_view(), name="quality"),
    path("control-calidad/listas/", views.PaeChecklistView.as_view(), name="checklists"),
    path("control-calidad/criterios/", views.PaeChecklistItemView.as_view(), name="checklist_items"),
    path("control-calidad/aplicar/", views.PaeVerificationSheetView.as_view(), name="verification_sheet"),
    # 13. Visitas de supervision
    path("visitas/", views.PaeVisitView.as_view(), name="visits"),
    path("visitas/hallazgos/", views.PaeFindingView.as_view(), name="findings"),
    # 14. Novedades
    path("novedades/", views.PaeIncidentView.as_view(), name="incidents"),
    # 15. Planes de mejoramiento
    path("mejoramiento/", views.PaeImprovementView.as_view(), name="improvement"),
    # 16. PQRS
    path("pqrs/", views.PaePqrsView.as_view(), name="pqrs"),
    # 17. Participacion ciudadana
    path("participacion/", views.PaeParticipationView.as_view(), name="participation"),
    path("participacion/asistentes/", views.PaeParticipantView.as_view(), name="participants"),
    path("participacion/compromisos/", views.PaeCommitmentView.as_view(), name="commitments"),
    # 18. Documentos
    path("documentos/", views.PaeDocumentView.as_view(), name="documents"),
    # 19. Evidencias
    path("evidencias/", views.PaeEvidenceView.as_view(), name="evidence"),
    # 20. Indicadores
    path("indicadores/", views.PaeIndicatorView.as_view(), name="indicators"),
    # 21. Informes
    path("informes/", views.PaeReportView.as_view(), name="reports"),
    # 22. Auditoria del modulo
    path("auditoria/", views.PaeAuditView.as_view(), name="audit"),
]
