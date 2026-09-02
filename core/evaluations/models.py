"""
Evaluaciones: asignacion de notas, juicios valorativos, evaluacion cualitativa,
propositos de preescolar y modulo bilingue.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class ProcessGrade(BaseModel):
    """Nota de un proceso academico puntual (taller, quiz, evaluacion)."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="process_grades"
    )
    assignment = models.ForeignKey(
        "teachers.TeachingAssignment", verbose_name="Asignacion", on_delete=models.CASCADE, related_name="process_grades"
    )
    process = models.ForeignKey(
        "teachers.TeacherAcademicProcess", verbose_name="Proceso", on_delete=models.CASCADE, related_name="grades"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="process_grades"
    )
    dimension = models.ForeignKey(
        "academic.ValuationDimension",
        verbose_name="Dimension",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="process_grades",
    )
    score = models.DecimalField("Nota", max_digits=5, decimal_places=2, null=True, blank=True)
    observation = models.CharField("Observacion", max_length=240, blank=True)
    recorded_at = models.DateTimeField("Registrada el", default=timezone.now)
    recorded_by = models.ForeignKey(
        "users.User", verbose_name="Registrada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_grades"
    )

    class Meta:
        db_table = "evaluation_process_grade"
        verbose_name = "Nota de proceso"
        verbose_name_plural = "Notas de procesos"
        unique_together = ("student", "process")
        ordering = ["student__last_name", "process__order"]
        indexes = [models.Index(fields=["period", "assignment"])]

    def __str__(self):
        return f"{self.student} / {self.process} = {self.score}"


class SubjectGrade(BaseModel):
    """Nota consolidada de una asignatura en un periodo (nota de boletin)."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PUBLICADA", "Publicada"),
        ("CERRADA", "Cerrada"),
        ("RECUPERADA", "Recuperada"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="subject_grades"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", verbose_name="Matricula", null=True, blank=True, on_delete=models.CASCADE, related_name="subject_grades"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="subject_grades"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="subject_grades"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", on_delete=models.CASCADE, related_name="subject_grades"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="subject_grades"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="subject_grades"
    )

    score = models.DecimalField("Nota del periodo", max_digits=5, decimal_places=2, null=True, blank=True)
    recovered_score = models.DecimalField("Nota de recuperacion", max_digits=5, decimal_places=2, null=True, blank=True)
    final_score = models.DecimalField("Nota definitiva", max_digits=5, decimal_places=2, null=True, blank=True)
    performance = models.ForeignKey(
        "academic.GradingScaleLevel",
        verbose_name="Desempeno",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subject_grades",
    )
    absences = models.PositiveSmallIntegerField("Fallas", default=0)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    is_passing = models.BooleanField("Aprobada", default=True)
    observation = models.TextField("Observacion", blank=True)
    published_at = models.DateTimeField("Publicada el", null=True, blank=True)

    class Meta:
        db_table = "evaluation_subject_grade"
        verbose_name = "Nota de asignatura"
        verbose_name_plural = "Notas de asignaturas"
        unique_together = ("student", "period", "subject")
        ordering = ["subject__area__order", "subject__order"]
        indexes = [
            models.Index(fields=["school_year", "period", "group"]),
            models.Index(fields=["student", "period"]),
        ]

    def __str__(self):
        return f"{self.student} / {self.subject} / {self.period} = {self.final_score or self.score}"

    # Campos que la aplicacion calcula y que nunca se digitan a mano.
    COMPUTED_FIELDS = ("final_score", "performance", "is_passing", "status")

    def resolve_final(self):
        from core.academic.models import GradingScale

        base = self.score or Decimal("0.00")
        if self.recovered_score and self.recovered_score > base:
            self.final_score = self.recovered_score
            self.status = "RECUPERADA"
        else:
            self.final_score = base
        scale = GradingScale.default_for(self.school_year)
        if scale:
            level = scale.level_for(self.final_score)
            self.performance = level
            self.is_passing = level.is_passing if level else self.final_score >= scale.passing
        return self.final_score

    def save(self, *args, **kwargs):
        """
        La definitiva y el desempeno se recalculan en cada guardado.

        Asi quedan siempre en firme, sin importar por donde entre la nota:
        la planilla del docente, la pagina de gestion, la API, una importacion
        o un comando de consolidacion.
        """
        if self.school_year_id:
            self.resolve_final()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                # Sin esto, un save(update_fields=["score"]) guardaria la nota
                # pero descartaria la definitiva y el desempeno recalculados.
                kwargs["update_fields"] = set(update_fields) | set(self.COMPUTED_FIELDS)
        super().save(*args, **kwargs)


class AreaGrade(BaseModel):
    """Promedio del area para el boletin."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="area_grades"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="area_grades"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="area_grades"
    )
    area = models.ForeignKey("academic.Area", verbose_name="Area", on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField("Nota del area", max_digits=5, decimal_places=2, null=True, blank=True)
    performance = models.ForeignKey(
        "academic.GradingScaleLevel",
        verbose_name="Desempeno",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="area_grades",
    )
    is_passing = models.BooleanField("Aprobada", default=True)

    class Meta:
        db_table = "evaluation_area_grade"
        verbose_name = "Nota de area"
        verbose_name_plural = "Notas de areas"
        unique_together = ("student", "period", "area")
        ordering = ["area__order"]

    def __str__(self):
        return f"{self.student} / {self.area} = {self.score}"

    COMPUTED_FIELDS = ("performance", "is_passing")

    def resolve_performance(self):
        """Desempeno del area a partir de su promedio."""
        from core.academic.models import GradingScale, resolve_performance

        level = resolve_performance(self.school_year, self.score)
        self.performance = level
        if level is not None:
            self.is_passing = level.is_passing
        else:
            scale = GradingScale.default_for(self.school_year)
            if scale and self.score is not None:
                self.is_passing = self.score >= scale.passing
        return level

    def save(self, *args, **kwargs):
        if self.school_year_id:
            self.resolve_performance()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | set(self.COMPUTED_FIELDS)
        super().save(*args, **kwargs)


class StudentJudgment(BaseModel):
    """Juicio valorativo asignado a un estudiante en una asignatura y periodo."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="judgments"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="student_judgments"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="student_judgments"
    )
    judgment = models.ForeignKey(
        "academic.ValueJudgment", verbose_name="Juicio", null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments"
    )
    custom_text = models.TextField("Texto personalizado", blank=True)
    judgment_type = models.CharField("Tipo", max_length=16, default="DESEMPENO")
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="student_judgments"
    )

    class Meta:
        db_table = "evaluation_student_judgment"
        verbose_name = "Juicio valorativo del estudiante"
        verbose_name_plural = "Juicios valorativos de estudiantes"
        ordering = ["subject__order", "id"]

    def __str__(self):
        return self.text[:70]

    @property
    def text(self):
        return self.custom_text or (self.judgment.text if self.judgment_id else "")


class QualitativeEvaluation(BaseModel):
    """Evaluacion cualitativa por dimension (sin nota numerica)."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="qualitative_evaluations"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="qualitative_evaluations"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="qualitative_evaluations"
    )
    dimension = models.ForeignKey(
        "academic.ValuationDimension", verbose_name="Dimension", null=True, blank=True, on_delete=models.SET_NULL, related_name="qualitative_evaluations"
    )
    performance = models.ForeignKey(
        "academic.GradingScaleLevel", verbose_name="Desempeno", null=True, blank=True, on_delete=models.SET_NULL, related_name="qualitative_evaluations"
    )
    description = models.TextField("Valoracion cualitativa", blank=True)
    strengths = models.TextField("Fortalezas", blank=True)
    difficulties = models.TextField("Dificultades", blank=True)
    recommendations = models.TextField("Recomendaciones", blank=True)
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="qualitative_evaluations"
    )

    class Meta:
        db_table = "evaluation_qualitative"
        verbose_name = "Evaluacion cualitativa"
        verbose_name_plural = "Evaluaciones cualitativas"
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} / {self.subject or self.dimension}"


class PurposeEvaluation(BaseModel):
    """Valoracion de propositos de preescolar."""

    ACHIEVEMENT_CHOICES = [
        ("SUPERADO", "Superado"),
        ("EN_PROCESO", "En proceso"),
        ("INICIADO", "Iniciado"),
        ("NO_LOGRADO", "No logrado"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="purpose_evaluations"
    )
    purpose = models.ForeignKey(
        "academic.Purpose", verbose_name="Proposito", on_delete=models.CASCADE, related_name="evaluations"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="purpose_evaluations"
    )
    achievement = models.CharField("Nivel de logro", max_length=12, choices=ACHIEVEMENT_CHOICES, default="EN_PROCESO")
    observation = models.TextField("Observacion", blank=True)
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="purpose_evaluations"
    )

    class Meta:
        db_table = "evaluation_purpose"
        verbose_name = "Valoracion de proposito"
        verbose_name_plural = "Propositos preescolar"
        unique_together = ("student", "purpose", "period")
        ordering = ["purpose__order"]

    def __str__(self):
        return f"{self.student} / {self.purpose}"


class BilingualEvaluation(BaseModel):
    """Modulo bilingue: valoracion por competencias del marco comun europeo."""

    LEVEL_CHOICES = [
        ("A1", "A1 - Principiante"),
        ("A2", "A2 - Basico"),
        ("B1", "B1 - Intermedio"),
        ("B2", "B2 - Intermedio alto"),
        ("C1", "C1 - Avanzado"),
        ("C2", "C2 - Maestria"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="bilingual_evaluations"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="bilingual_evaluations"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura bilingue", on_delete=models.CASCADE, related_name="bilingual_evaluations"
    )
    listening = models.DecimalField("Listening", max_digits=5, decimal_places=2, null=True, blank=True)
    speaking = models.DecimalField("Speaking", max_digits=5, decimal_places=2, null=True, blank=True)
    reading = models.DecimalField("Reading", max_digits=5, decimal_places=2, null=True, blank=True)
    writing = models.DecimalField("Writing", max_digits=5, decimal_places=2, null=True, blank=True)
    grammar = models.DecimalField("Grammar", max_digits=5, decimal_places=2, null=True, blank=True)
    average = models.DecimalField("Promedio", max_digits=5, decimal_places=2, null=True, blank=True)
    cefr_level = models.CharField("Nivel MCER", max_length=2, choices=LEVEL_CHOICES, blank=True)
    comments = models.TextField("Comentarios", blank=True)
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="bilingual_evaluations"
    )

    class Meta:
        db_table = "evaluation_bilingual"
        verbose_name = "Evaluacion bilingue"
        verbose_name_plural = "Modulo bilingue"
        unique_together = ("student", "period", "subject")
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} / {self.subject} / {self.period}"

    def save(self, *args, **kwargs):
        values = [v for v in [self.listening, self.speaking, self.reading, self.writing, self.grammar] if v is not None]
        if values:
            self.average = (sum(values) / len(values)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class GradeSheetLock(BaseModel):
    """Bloqueo de digitacion de notas por grupo, asignatura y periodo."""

    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="grade_locks"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="grade_locks"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="grade_locks"
    )
    locked = models.BooleanField("Bloqueado", default=True)
    reason = models.CharField("Motivo", max_length=240, blank=True)
    locked_by = models.ForeignKey(
        "users.User", verbose_name="Bloqueado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="grade_locks"
    )

    class Meta:
        db_table = "evaluation_grade_lock"
        verbose_name = "Bloqueo de digitacion"
        verbose_name_plural = "Bloqueos de digitacion"
        unique_together = ("period", "group", "subject")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group} / {self.subject or 'Todas'} / {self.period}"
