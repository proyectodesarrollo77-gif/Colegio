"""Rutas HTML de documentos institucionales."""
from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("configuracion/", views.DocumentConfigurationView.as_view(), name="configuration"),
    path("impresion/", views.DocumentPrintingView.as_view(), name="printing"),
    path("<int:pk>/imprimir/", views.document_print, name="document_print"),
]
