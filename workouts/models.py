from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class CategorieExercice(models.TextChoices):
    ADDUCTEURS = "ADDUCTEURS", "Adducteurs"
    ABDOS = "ABDOS", "Abdos"
    CARDIO = "CARDIO", "Cardio"
    DOS = "DOS", "Dos"
    EPAULE_ARRIERE = "EPAULE_ARRIERE", "Epaule arriere"
    FESSIERS = "FESSIERS", "Fessiers"
    GAINAGE = "GAINAGE", "Gainage"
    ISCHIOS = "ISCHIOS", "Ischios"
    PECTORAUX = "PECTORAUX", "Pectoraux"
    QUADRICEPS = "QUADRICEPS", "Quadriceps"
    OTHER = "OTHER", "Autre"



class StatutSeance(models.TextChoices):
    PLANNED = "PLANIFIEE", "Planifiee"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    COMPLETED = "COMPLETED", "Terminee"


class Exercice(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    categorie = models.CharField(
        max_length=20,
        choices=CategorieExercice.choices,
        default=CategorieExercice.OTHER,
    )
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "exercice"
        verbose_name_plural = "exercices"

    def __str__(self):
        return self.nom


class SeanceType(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "seance type"
        verbose_name_plural = "seances types"

    def __str__(self):
        return self.nom


class TemplateLigne(models.Model):
    seance_type = models.ForeignKey(
        SeanceType,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    ordre_exercice = models.PositiveSmallIntegerField()
    exercice = models.ForeignKey(
        Exercice,
        on_delete=models.PROTECT,
        related_name="template_lignes",
    )
    numero_serie = models.PositiveSmallIntegerField()
    repetitions_cible = models.PositiveSmallIntegerField(null=True, blank=True)
    charge_cible = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rpe_cible = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )
    repos_secondes = models.PositiveSmallIntegerField(null=True, blank=True)
    tempo = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["seance_type", "ordre_exercice", "numero_serie"]
        constraints = [
            models.UniqueConstraint(
                fields=["seance_type", "ordre_exercice", "numero_serie"],
                name="unique_template_serie_par_ordre",
            ),
            models.CheckConstraint(
                condition=Q(rpe_cible__isnull=True)
                | (Q(rpe_cible__gte=0) & Q(rpe_cible__lte=10)),
                name="template_rpe_cible_entre_0_et_10",
            ),
        ]
        verbose_name = "ligne de template"
        verbose_name_plural = "lignes de template"

    def __str__(self):
        return (
            f"{self.seance_type} - {self.exercice} "
            f"S{self.numero_serie} ({self.ordre_exercice})"
        )

    def clean(self):
        super().clean()
        if not self.seance_type_id or not self.ordre_exercice or not self.exercice_id:
            return

        conflit = TemplateLigne.objects.filter(
            seance_type=self.seance_type,
            ordre_exercice=self.ordre_exercice,
        ).exclude(exercice=self.exercice)
        if self.pk:
            conflit = conflit.exclude(pk=self.pk)
        if conflit.exists():
            raise ValidationError(
                {
                    "ordre_exercice": (
                        "Un meme ordre d'exercice doit toujours pointer vers "
                        "le meme exercice dans une seance type."
                    )
                }
            )


class Seance(models.Model):
    seance_type = models.ForeignKey(
        SeanceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seances",
    )
    date = models.DateField()
    statut = models.CharField(
        max_length=20,
        choices=StatutSeance.choices,
        default=StatutSeance.PLANNED,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "seance"
        verbose_name_plural = "seances"

    def __str__(self):
        nom = self.seance_type.nom if self.seance_type else "Seance libre"
        return f"{nom} - {self.date:%d/%m/%Y}"

    @property
    def is_active(self):
        return self.statut == StatutSeance.IN_PROGRESS

    @property
    def duration(self):
        if not self.started_at or not self.ended_at:
            return None
        return self.ended_at - self.started_at


class SessionLigne(models.Model):
    seance = models.ForeignKey(
        Seance,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    ordre_prevu = models.PositiveSmallIntegerField()
    ordre_reel = models.PositiveSmallIntegerField(null=True, blank=True)
    exercice = models.ForeignKey(
        Exercice,
        on_delete=models.PROTECT,
        related_name="session_lignes",
    )
    numero_serie = models.PositiveSmallIntegerField()
    repetitions_cible = models.PositiveSmallIntegerField(null=True, blank=True)
    charge_cible = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rpe_cible = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )
    repos_secondes = models.PositiveSmallIntegerField(null=True, blank=True)
    tempo = models.CharField(max_length=30, blank=True)
    repetitions_reelles = models.PositiveSmallIntegerField(null=True, blank=True)
    charge_reelle = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rpe_reel = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )
    validee = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["seance", "ordre_reel", "ordre_prevu", "numero_serie"]
        constraints = [
            models.UniqueConstraint(
                fields=["seance", "ordre_prevu", "numero_serie"],
                name="unique_session_serie_par_ordre_prevu",
            ),
            models.CheckConstraint(
                condition=Q(rpe_cible__isnull=True)
                | (Q(rpe_cible__gte=0) & Q(rpe_cible__lte=10)),
                name="session_rpe_cible_entre_0_et_10",
            ),
            models.CheckConstraint(
                condition=Q(rpe_reel__isnull=True)
                | (Q(rpe_reel__gte=0) & Q(rpe_reel__lte=10)),
                name="session_rpe_reel_entre_0_et_10",
            ),
        ]
        verbose_name = "ligne de session"
        verbose_name_plural = "lignes de session"

    def __str__(self):
        return f"{self.seance} - {self.exercice} S{self.numero_serie}"

    def clean(self):
        super().clean()
        if not self.seance_id or not self.ordre_prevu or not self.exercice_id:
            return

        conflit = SessionLigne.objects.filter(
            seance=self.seance,
            ordre_prevu=self.ordre_prevu,
        ).exclude(exercice=self.exercice)
        if self.pk:
            conflit = conflit.exclude(pk=self.pk)
        if conflit.exists():
            raise ValidationError(
                {
                    "ordre_prevu": (
                        "Un meme ordre prevu doit toujours pointer vers le "
                        "meme exercice dans une seance."
                    )
                }
            )

    @property
    def ordre_affichage(self):
        return self.ordre_reel or self.ordre_prevu

    @property
    def is_completed(self):
        return self.validee or self.completed_at is not None

    @property
    def volume(self):
        if self.charge_reelle is None or self.repetitions_reelles is None:
            return None
        return self.charge_reelle * self.repetitions_reelles

    def mark_completed(self):
        self.validee = True
        if not self.completed_at:
            self.completed_at = timezone.now()
