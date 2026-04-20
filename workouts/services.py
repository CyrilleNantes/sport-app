from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import Seance, SessionLigne, StatutSeance, TemplateLigne


@transaction.atomic
def copy_template_lines_to_seance(seance):
    if not seance.pk or not seance.seance_type_id:
        return []

    seance = Seance.objects.select_for_update().get(pk=seance.pk)
    if seance.lignes.exists():
        return []

    lignes = [
        SessionLigne(
            seance=seance,
            ordre_prevu=ligne.ordre_exercice,
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
    return SessionLigne.objects.bulk_create(lignes)


@transaction.atomic
def create_seance_from_template(*, seance_type, date):
    seance = Seance.objects.create(seance_type=seance_type, date=date)
    copy_template_lines_to_seance(seance)
    return seance


def start_seance(seance):
    if seance.statut == StatutSeance.COMPLETED:
        return seance
    if not seance.started_at:
        seance.started_at = timezone.now()
    seance.statut = StatutSeance.IN_PROGRESS
    seance.save(update_fields=["started_at", "statut"])
    return seance


def complete_seance(seance):
    if not seance.started_at:
        seance.started_at = timezone.now()
    seance.ended_at = timezone.now()
    seance.statut = StatutSeance.COMPLETED
    seance.save(update_fields=["started_at", "ended_at", "statut"])
    return seance


@transaction.atomic
def add_unplanned_session_line(
    *,
    seance,
    exercice,
    repetitions_cible=None,
    charge_cible=None,
    rpe_cible=None,
    repos_secondes=None,
    tempo="",
):
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

    return SessionLigne.objects.create(
        seance=seance,
        ordre_prevu=next_order,
        exercice=exercice,
        numero_serie=next_serie,
        repetitions_cible=repetitions_cible,
        charge_cible=charge_cible,
        rpe_cible=rpe_cible,
        repos_secondes=repos_secondes,
        tempo=tempo,
    )


@transaction.atomic
def update_exercise_order(*, seance, ordre_prevu, ordre_reel):
    all_lignes = list(
        SessionLigne.objects.select_for_update()
        .filter(seance=seance)
        .order_by("ordre_prevu", "numero_serie")
    )
    if not all_lignes:
        return 0, ordre_prevu

    groups = {}
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
        stored_value = None if index == group["ordre_prevu"] else index
        SessionLigne.objects.filter(
            pk__in=[ligne.pk for ligne in group["lignes"]]
        ).update(ordre_reel=stored_value)

    return len(moving_group["lignes"]), target_index + 1
