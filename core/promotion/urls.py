"""Rutas HTML de promocion y boletines."""
from django.urls import path

from . import views

app_name = "promotion"

urlpatterns = [
    path("cierre/", views.ClosingView.as_view(), name="closing"),
    path("resultados/", views.PromotionResultView.as_view(), name="results"),
    path("boletines/", views.FinalReportView.as_view(), name="final_reports"),
    path("boletines/imprimir/", views.report_cards_print, name="report_cards_print"),
    path("boletin/<int:pk>/", views.report_card_print, name="report_card_print"),
]
