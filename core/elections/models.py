"""
Elecciones escolares: configuracion, votacion digital y resultados.
Gobierno escolar: personero, contralor, representantes de grupo y consejo.
"""
from __future__ import annotations

import hashlib

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class Election(BaseModel):
    STATUS_CHOICES = [
        ("CONFIGURACION", "En configuracion"),
        ("INSCRIPCIONES", "Inscripciones abiertas"),
        ("CAMPANA", "En campana"),
        ("ABIERTA", "Votacion abierta"),
        ("CERRADA", "Votacion cerrada"),
        ("PUBLICADA", "Resultados publicados"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="elections"
    )
    name = models.CharField("Nombre del proceso", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    start_at = models.DateTimeField("Apertura de votacion")
    end_at = models.DateTimeField("Cierre de votacion")
    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="CONFIGURACION")
    allow_blank_vote = models.BooleanField("Permite voto en blanco", default=True)
    show_live_results = models.BooleanField("Mostrar resultados en vivo", default=False)
    require_2fa = models.BooleanField("Exigir doble factor", default=False)
    banner = models.ImageField("Imagen del proceso", upload_to="elections/", null=True, blank=True)

    class Meta:
        db_table = "election"
        verbose_name = "Proceso electoral"
        verbose_name_plural = "Procesos electorales"
        ordering = ["-start_at"]

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        now = timezone.now()
        return self.status == "ABIERTA" and self.start_at <= now <= self.end_at


class Candidacy(BaseModel):
    """Cargo o dignidad a elegir dentro del proceso."""

    election = models.ForeignKey(
        Election, verbose_name="Proceso electoral", on_delete=models.CASCADE, related_name="candidacies"
    )
    name = models.CharField("Cargo", max_length=140)
    description = models.TextField("Descripcion", blank=True)
    voter_scope = models.CharField(
        "Electores habilitados",
        max_length=14,
        choices=[
            ("TODOS", "Todos los estudiantes"),
            ("GRADO", "Estudiantes de grados especificos"),
            ("GRUPO", "Estudiantes del grupo"),
            ("DOCENTES", "Docentes"),
            ("COMUNIDAD", "Toda la comunidad"),
        ],
        default="TODOS",
    )
    grades = models.ManyToManyField("academic.Grade", verbose_name="Grados", blank=True, related_name="candidacies")
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", null=True, blank=True, on_delete=models.SET_NULL, related_name="candidacies"
    )
    max_selections = models.PositiveSmallIntegerField("Selecciones permitidas", default=1)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "election_candidacy"
        verbose_name = "Cargo electoral"
        verbose_name_plural = "Cargos electorales"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} - {self.election}"


class Candidate(BaseModel):
    candidacy = models.ForeignKey(
        Candidacy, verbose_name="Cargo", on_delete=models.CASCADE, related_name="candidates"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante candidato", null=True, blank=True, on_delete=models.CASCADE, related_name="candidacies"
    )
    number = models.PositiveSmallIntegerField("Numero del tarjeton", default=1)
    slogan = models.CharField("Lema de campana", max_length=200, blank=True)
    proposals = models.TextField("Propuestas", blank=True)
    photo = models.ImageField("Fotografia", upload_to="elections/candidates/", null=True, blank=True)
    is_approved = models.BooleanField("Candidatura aprobada", default=False)
    is_blank_vote = models.BooleanField("Opcion de voto en blanco", default=False)
    votes_count = models.PositiveIntegerField("Votos", default=0)

    class Meta:
        db_table = "election_candidate"
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatos"
        unique_together = ("candidacy", "number")
        ordering = ["number"]

    def __str__(self):
        if self.is_blank_vote:
            return "Voto en blanco"
        return f"{self.number}. {self.student}"


class Vote(BaseModel):
    """
    Voto emitido. Se almacena el hash del elector para garantizar
    unicidad sin vincular la identidad con la seleccion.
    """

    election = models.ForeignKey(Election, verbose_name="Proceso", on_delete=models.CASCADE, related_name="votes")
    candidacy = models.ForeignKey(
        Candidacy, verbose_name="Cargo", on_delete=models.CASCADE, related_name="votes"
    )
    candidate = models.ForeignKey(
        Candidate, verbose_name="Candidato", on_delete=models.CASCADE, related_name="votes"
    )
    voter_hash = models.CharField("Huella del elector", max_length=64, db_index=True)
    voted_at = models.DateTimeField("Fecha del voto", default=timezone.now)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        db_table = "election_vote"
        verbose_name = "Voto"
        verbose_name_plural = "Votos"
        unique_together = ("candidacy", "voter_hash")
        ordering = ["-voted_at"]

    def __str__(self):
        return f"Voto {self.candidacy} - {self.voted_at:%Y-%m-%d %H:%M}"

    @staticmethod
    def build_hash(election_id, user_id):
        raw = f"plsge-election-{election_id}-user-{user_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class VoterRegistry(BaseModel):
    """Censo electoral: control de quien ya voto en cada cargo."""

    election = models.ForeignKey(
        Election, verbose_name="Proceso", on_delete=models.CASCADE, related_name="voters"
    )
    voter_hash = models.CharField("Huella del elector", max_length=64, db_index=True)
    candidacies_voted = models.PositiveSmallIntegerField("Cargos votados", default=0)
    completed = models.BooleanField("Voto completo", default=False)
    voted_at = models.DateTimeField("Ultimo voto", default=timezone.now)

    class Meta:
        db_table = "election_voter_registry"
        verbose_name = "Registro de elector"
        verbose_name_plural = "Censo electoral"
        unique_together = ("election", "voter_hash")

    def __str__(self):
        return f"{self.election} - {self.voter_hash[:12]}"


class ElectionResult(BaseModel):
    """Resultado consolidado y publicado de un cargo."""

    election = models.ForeignKey(
        Election, verbose_name="Proceso", on_delete=models.CASCADE, related_name="results"
    )
    candidacy = models.ForeignKey(
        Candidacy, verbose_name="Cargo", on_delete=models.CASCADE, related_name="results"
    )
    candidate = models.ForeignKey(
        Candidate, verbose_name="Candidato", on_delete=models.CASCADE, related_name="results"
    )
    votes = models.PositiveIntegerField("Votos obtenidos", default=0)
    percentage = models.DecimalField("Porcentaje", max_digits=5, decimal_places=2, default=0)
    position = models.PositiveSmallIntegerField("Posicion", default=1)
    is_winner = models.BooleanField("Electo", default=False)
    published_at = models.DateTimeField("Publicado el", null=True, blank=True)

    class Meta:
        db_table = "election_result"
        verbose_name = "Resultado electoral"
        verbose_name_plural = "Resultados electorales"
        unique_together = ("candidacy", "candidate")
        ordering = ["candidacy__order", "position"]

    def __str__(self):
        return f"{self.candidate} - {self.votes} votos"
