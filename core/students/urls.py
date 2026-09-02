"""Rutas HTML del modulo de estudiantes."""
from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.StudentRegistryView.as_view(), name="registry"),
    path("matricula/", views.EnrollmentView.as_view(), name="enrollment"),
    path("consulta/", views.StudentQueryView.as_view(), name="query"),
    path("promocion/", views.PromotionQueryView.as_view(), name="promotion"),
    path("certificados/", views.CertificateView.as_view(), name="certificates"),
    path("certificados/<int:pk>/imprimir/", views.certificate_print, name="certificate_print"),
    path("hoja-de-vida/", views.StudentResumeView.as_view(), name="resume"),
    path("<int:pk>/hoja-de-vida/", views.StudentResumeDetailView.as_view(), name="resume_detail"),
    path("listados/", views.StudentListsView.as_view(), name="lists"),
    path("admisiones/", views.AdmissionView.as_view(), name="admissions"),
    path("inscripciones/", views.InscriptionView.as_view(), name="inscriptions"),
    path("acudientes/", views.GuardianView.as_view(), name="guardians"),
]
