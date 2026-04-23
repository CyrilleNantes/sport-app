from __future__ import annotations

import datetime
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import Exercice, Seance, SeanceType, SessionLigne, StatutSeance, TemplateLigne

logger = logging.getLogger("workouts.services")


@transaction.atomic
def copy_template_lines_to_seance(seance: Seance) -> list[SessionLigne]:
    if not seance.pk or not seance.seance_type_id:
        return []

    seance = Seance.objects.select_for_update().get(pk=seance.pk)
    if seance.lignes.exists():
        return []

    lignes = [
        SessionLigne(
            seance=seance,
            ordre_prevu=ligne.ordre_exercice,
            ordre_reel=ligne.ordre_exercice,
            exercice=ligne.exercice,
            numero_serie=ligne.numero_serie,
            repetitions_cible=ligne.repetitions_cible,
            charge_cible=ligne.charge_cible,
            rpe_cible=ligne.rpe_cible,
            repos_secondes=ligne.repos_secondes,
            tempo=ligne.tempo,
        )
        for ligne in TemplateLigne.objects.filter(seance_type=seance.seance_type)
        .select_related("exercice")
        .order_by("ordre_exercice", "numero_serie")
    ]
    created = SessionLigne.objects.bulk_create(lignes)
    logger.debug(
        "Template copié vers séance pk=%s : %s lignes créées", seance.pk, len(created)
    )
    return created


@transaction.atomic
def create_seance_from_template(
    *, seance_type: SeanceType, date: datetime.date
) -> Seance:
    seance = Seance.objects.create(seance_type=seance_type, date=date)
    copy_template_lines_to_seance(seance)
    logger.info(
        "Séance créée depuis template : pk=%s type='%s' date=%s",
        seance.pk, seance_type.nom, date,
    )
    return seance


def start_seance(seance: Seance) -> Seance:
    if seance.statut == StatutSeance.COMPLETED:
        return seance
    if not seance.started_at:
        seance.started_at = timezone.now()
    seance.statut = StatutSeance.IN_PROGRESS
    seance.save(update_fields=["started_at", "statut"])
    logger.info("Séance démarrée : pk=%s started_at=%s", seance.pk, seance.started_at)
    return seance


def complete_seance(seance: Seance) -> Seance:
    if not seance.started_at:
        seance.started_at = timezone.now()
    seance.ended_at = timezone.now()
    seance.statut = StatutSeance.COMPLETED
    seance.save(update_fields=["started_at", "ended_at", "statut"])
    logger.info(
        "Séance terminée : pk=%s durée=%s", seance.pk, seance.duration
    )
    return seance


@transaction.atomic
def add_unplanned_session_line(
    *,
    seance: Seance,
    exercice: Exercice,
    repetitions_cible: int | None = None,
    charge_cible: Decimal | None = None,
    rpe_cible: Decimal | None = None,
    repos_secondes: int | None = None,
    tempo: str = "",
) -> SessionLigne:
    existing_order = (
        SessionLigne.objects.filter(seance=seance, exercice=exercice)
        .order_by("ordre_prevu")
        .values_list("ordre_prevu", flat=True)
        .first()
    )
    if existing_order is None:
        next_order = (
            SessionLigne.objects.filter(seance=seance).aggregate(Max("ordre_prevu"))[
                "ordre_prevu__max"
            ]
            or 0
        ) + 1
    else:
        next_order = existing_order

    next_serie = (
        SessionLigne.objects.filter(seance=seance, ordre_prevu=next_order).aggregate(
            Max("numero_serie")
        )["numero_serie__max"]
        or 0
    ) + 1

    ligne = SessionLigne.objects.create(
        seance=seance,
        ordre_prevu=next_order,
        ordre_reel=next_order,
        exercice=exercice,
        numero_serie=next_serie,
        repetitions_cible=repetitions_cible,
        charge_cible=charge_cible,
        rpe_cible=rpe_cible,
        repos_secondes=repos_secondes,
        tempo=tempo,
    )
    logger.debug(
        "Série hors-template créée : séance pk=%s exercice='%s' ordre=%s série=%s",
        seance.pk, exercice.nom, next_order, next_serie,
    )
    return ligne


@transaction.atomic
def update_exercise_order(
    *, seance: Seance, ordre_prevu: int, ordre_reel: int
) -> tuple[int, int]:
    all_lignes = list(
        SessionLigne.objects.select_for_update()
        .filter(seance=seance)
        .order_by("ordre_prevu", "numero_serie")
    )
    if not all_lignes:
        return 0, ordre_prevu

    groups: dict[int, dict] = {}
    for ligne in all_lignes:
        groups.setdefault(
            ligne.ordre_prevu,
            {
                "ordre_prevu": ligne.ordre_prevu,
                "ordre_courant": ligne.ordre_reel or ligne.ordre_prevu,
                "lignes": [],
            },
        )["lignes"].append(ligne)

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (group["ordre_courant"], group["ordre_prevu"]),
    )
    moving_group = next(
        (group for group in ordered_groups if group["ordre_prevu"] == ordre_prevu),
        None,
    )
    if moving_group is None:
        return 0, ordre_prevu

    ordered_groups = [
        group for group in ordered_groups if group["ordre_prevu"] != ordre_prevu
    ]
    target_index = max(0, min((ordre_reel or ordre_prevu) - 1, len(ordered_groups)))
    ordered_groups.insert(target_index, moving_group)

    for index, group in enumerate(ordered_groups, start=1):
        SessionLigne.objects.filter(
            pk__in=[ligne.pk for ligne in group["lignes"]]
        ).update(ordre_reel=index)

    updated_count = len(moving_group["lignes"])
    final_order = target_index + 1
    logger.debug(
        "Ordre exercice réorganisé : séance pk=%s ordre_prevu=%s → position=%s (%s lignes)",
        seance.pk, ordre_prevu, final_order, updated_count,
    )
    return updated_count, final_order
