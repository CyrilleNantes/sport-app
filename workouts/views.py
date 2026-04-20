from itertools import groupby
import csv

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AddSessionLineForm,
    SeanceNotesForm,
    SeancePlanificationForm,
    SessionLigneQuickForm,
)
from .models import Seance, SessionLigne, StatutSeance
from .services import (
    add_unplanned_session_line,
    complete_seance,
    create_seance_from_template,
    start_seance,
    update_exercise_order,
)


def _group_lignes(lignes):
    sorted_lignes = sorted(
        lignes,
        key=lambda ligne: (
            ligne.ordre_affichage,
            ligne.ordre_prevu,
            ligne.numero_serie,
        ),
    )
    groupes = []
    for ordre, iterator in groupby(
        sorted_lignes,
        key=lambda ligne: (
            ligne.ordre_affichage,
            ligne.ordre_prevu,
            ligne.exercice_id,
        ),
    ):
        group = list(iterator)
        groupes.append(
            {
                "ordre": ordre[0],
                "ordre_source": group[0].ordre_prevu,
                "exercice": group[0].exercice,
                "lignes": group,
            }
        )
    return groupes


def dashboard(request):
    seances_actives = Seance.objects.filter(
        statut=StatutSeance.IN_PROGRESS
    ).select_related("seance_type")
    prochaines = (
        Seance.objects.filter(statut=StatutSeance.PLANNED)
        .select_related("seance_type")
        .order_by("date", "id")[:6]
    )
    recentes = (
        Seance.objects.filter(statut=StatutSeance.COMPLETED)
        .select_related("seance_type")
        .order_by("-date", "-id")[:6]
    )
    return render(
        request,
        "workouts/dashboard.html",
        {
            "seances_actives": seances_actives,
            "prochaines": prochaines,
            "recentes": recentes,
        },
    )


def planifier_seance(request):
    if request.method == "POST":
        form = SeancePlanificationForm(request.POST)
        if form.is_valid():
            seance = create_seance_from_template(
                seance_type=form.cleaned_data["seance_type"],
                date=form.cleaned_data["date"],
            )
            messages.success(request, "Seance planifiee.")
            return redirect("workouts:seance_detail", pk=seance.pk)
    else:
        form = SeancePlanificationForm()

    return render(request, "workouts/planifier_seance.html", {"form": form})


def seance_detail(request, pk):
    seance = get_object_or_404(Seance.objects.select_related("seance_type"), pk=pk)
    lignes = list(seance.lignes.select_related("exercice"))
    forms_by_line = {
        ligne.pk: SessionLigneQuickForm(instance=ligne) for ligne in lignes
    }
    return render(
        request,
        "workouts/seance_detail.html",
        {
            "seance": seance,
            "groupes": _group_lignes(lignes),
            "forms_by_line": forms_by_line,
            "notes_form": SeanceNotesForm(instance=seance),
            "add_line_form": AddSessionLineForm(),
        },
    )


@require_POST
def demarrer_seance(request, pk):
    seance = get_object_or_404(Seance, pk=pk)
    start_seance(seance)
    messages.success(request, "Seance demarree.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
def terminer_seance(request, pk):
    seance = get_object_or_404(Seance, pk=pk)
    complete_seance(seance)
    messages.success(request, "Seance terminee.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
def update_ligne(request, pk):
    ligne = get_object_or_404(
        SessionLigne.objects.select_related("seance", "exercice"),
        pk=pk,
    )
    form = SessionLigneQuickForm(request.POST, instance=ligne)
    wants_json = request.headers.get("Accept") == "application/json"
    if ligne.is_completed:
        error_payload = {
            "ok": False,
            "errors": {"__all__": ["Cette serie est deja validee."]},
        }
        if wants_json:
            return JsonResponse(error_payload, status=409)
        messages.error(request, "Cette serie est deja validee.")
        return redirect("workouts:seance_detail", pk=ligne.seance_id)
    if form.is_valid():
        ligne = form.save(commit=False)
        ligne.mark_completed()
        ligne.save()
        if wants_json:
            return JsonResponse(
                {
                    "ok": True,
                    "completed": ligne.is_completed,
                    "volume": str(ligne.volume) if ligne.volume is not None else "",
                    "completed_at": ligne.completed_at.strftime("%H:%M"),
                    "rest_seconds": ligne.repos_secondes or 0,
                    "exercise_name": ligne.exercice.nom,
                    "serie_label": f"S{ligne.numero_serie}",
                }
            )
        messages.success(request, "Serie enregistree.")
    elif wants_json:
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    else:
        messages.error(request, "Impossible d'enregistrer cette serie.")

    return redirect("workouts:seance_detail", pk=ligne.seance_id)


@require_POST
def update_ordre_exercice(request, pk, ordre_prevu):
    seance = get_object_or_404(Seance, pk=pk)
    wants_json = request.headers.get("Accept") == "application/json"

    raw_value = request.POST.get("ordre", "").strip()
    try:
        ordre_reel = int(raw_value) if raw_value else ordre_prevu
        if ordre_reel < 1:
            raise ValueError
    except ValueError:
        payload = {"ok": False, "errors": {"ordre": ["Ordre invalide."]}}
        if wants_json:
            return JsonResponse(payload, status=400)
        messages.error(request, "Ordre invalide.")
        return redirect("workouts:seance_detail", pk=seance.pk)

    updated_count, current_order = update_exercise_order(
        seance=seance,
        ordre_prevu=ordre_prevu,
        ordre_reel=ordre_reel,
    )
    if wants_json:
        return JsonResponse(
            {
                "ok": True,
                "updated_count": updated_count,
                "ordre": current_order,
            }
        )
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
def ajouter_ligne(request, pk):
    seance = get_object_or_404(Seance, pk=pk)
    form = AddSessionLineForm(request.POST)
    if form.is_valid():
        add_unplanned_session_line(seance=seance, **form.cleaned_data)
        messages.success(request, "Serie ajoutee.")
    else:
        messages.error(request, "Impossible d'ajouter cette serie.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
def update_notes(request, pk):
    seance = get_object_or_404(Seance, pk=pk)
    form = SeanceNotesForm(request.POST, instance=seance)
    if form.is_valid():
        form.save()
        messages.success(request, "Notes enregistrees.")
    else:
        messages.error(request, "Impossible d'enregistrer les notes.")
    return redirect("workouts:seance_detail", pk=seance.pk)


def historique(request):
    seances = (
        Seance.objects.filter(statut=StatutSeance.COMPLETED)
        .select_related("seance_type")
        .prefetch_related("lignes")
        .order_by("-date", "-id")
    )
    return render(request, "workouts/historique.html", {"seances": seances})


def export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sport-app-export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "date",
            "seance",
            "statut",
            "ordre_prevu",
            "ordre_reel",
            "exercice",
            "numero_serie",
            "repetitions_cible",
            "charge_cible",
            "rpe_cible",
            "repetitions_reelles",
            "charge_reelle",
            "rpe_reel",
            "validee",
            "completed_at",
        ]
    )

    lignes = SessionLigne.objects.select_related(
        "seance", "seance__seance_type", "exercice"
    ).order_by("seance__date", "seance_id", "ordre_prevu", "numero_serie")
    for ligne in lignes:
        writer.writerow(
            [
                ligne.seance.date,
                ligne.seance.seance_type.nom if ligne.seance.seance_type else "",
                ligne.seance.statut,
                ligne.ordre_prevu,
                ligne.ordre_reel or "",
                ligne.exercice.nom,
                ligne.numero_serie,
                ligne.repetitions_cible or "",
                ligne.charge_cible or "",
                ligne.rpe_cible or "",
                ligne.repetitions_reelles or "",
                ligne.charge_reelle or "",
                ligne.rpe_reel or "",
                ligne.validee,
                ligne.completed_at or "",
            ]
        )
    return response
