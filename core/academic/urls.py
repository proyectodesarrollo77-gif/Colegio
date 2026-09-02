"""Rutas HTML de la Directiva Academica."""
from django.urls import path

from . import views

app_name = "academic"

urlpatterns = [
    path("anos-lectivos/", views.SchoolYearView.as_view(), name="years"),
    path("periodos/", views.PeriodView.as_view(), name="periods"),
    path("escalas/", views.GradingScaleView.as_view(), name="scales"),
    path("dimensiones/", views.DimensionView.as_view(), name="dimensions"),
    path("areas/", views.AreaView.as_view(), name="areas"),
    path("asignaturas/", views.SubjectView.as_view(), name="subjects"),
    path("niveles/", views.EducationLevelView.as_view(), name="levels"),
    path("grados/", views.GradeView.as_view(), name="grades"),
    path("grupos/", views.GroupView.as_view(), name="groups"),
    path("procesos/", views.AcademicProcessView.as_view(), name="processes"),
    path("juicios/", views.ValueJudgmentView.as_view(), name="judgments"),
    path("convivencia/", views.CoexistenceView.as_view(), name="coexistence"),
    path("propositos/", views.PurposeView.as_view(), name="purposes"),
]
