from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import date
from itertools import groupby

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core import serializers as django_serializers
from django.core.management import call_command
from django.db import connection, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AddSessionLineForm,
    ChangerMotDePasseForm,
    ExerciceForm,
    InscriptionForm,
    MensurationForm,
    SeanceNotesForm,
    SeancePlanificationForm,
    SeanceTypeForm,
    SessionLigneQuickForm,
    TemplateLigneFormSet,
)
from .models import (
    Exercice,
    Mensuration,
    Seance,
    SeanceType,
    SessionLigne,
    StatutSeance,
    TemplateLigne,
    UserProfile,
)
from .services import (
    add_unplanned_session_line,
    complete_seance,
    create_seance_from_template,
    progression_exercice,
    start_seance,
    update_exercise_order,
)

logger = logging.getLogger("workouts.views")
User = get_user_model()


# ── Auth ────────────────────────────────────────────────────────────────────────

def connexion(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("workouts:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "")
            return redirect(next_url or "workouts:dashboard")
        messages.error(request, "Identifiant ou mot de passe incorrect.")
    return render(request, "workouts/auth/connexion.html")


def inscription(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("workouts:dashboard")
    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data.get("email", "")
            user = User.objects.create_user(
                username=username,
                email=email,
                password=form.cleaned_data["password1"],
                first_name=form.cleaned_data["prenom"],
                last_name=form.cleaned_data["nom"],
            )
            UserProfile.objects.create(user=user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            logger.info("Inscription : nouvel utilisateur pk=%s email=%s", user.pk, email)
            messages.success(request, f"Bienvenue, {user.first_name} !")
            return redirect("workouts:dashboard")
    else:
        form = InscriptionForm()
    return render(request, "workouts/auth/inscription.html", {"form": form})


@require_POST
@login_required
def deconnexion(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("workouts:connexion")


@login_required
def profil(request: HttpRequest) -> HttpResponse:
    nb_seances = Seance.objects.filter(
        user=request.user, statut=StatutSeance.COMPLETED
    ).count()
    derniere = (
        Seance.objects.filter(user=request.user, statut=StatutSeance.COMPLETED)
        .order_by("-date")
        .first()
    )
    return render(
        request,
        "workouts/profil.html",
        {
            "nb_seances": nb_seances,
            "derniere_seance": derniere,
            "pwd_form": ChangerMotDePasseForm(user=request.user),
        },
    )


@require_POST
@login_required
def changer_mot_de_passe(request: HttpRequest) -> HttpResponse:
    form = ChangerMotDePasseForm(request.POST, user=request.user)
    if form.is_valid():
        request.user.set_password(form.cleaned_data["nouveau1"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)  # garde la session active
        messages.success(request, "Mot de passe modifié avec succès.")
        logger.info("Mot de passe changé pour user pk=%s", request.user.pk)
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("workouts:profil")


# ── Dashboard ────────────────────────────────────────────────────────────────────

def _group_lignes(lignes: list[SessionLigne]) -> list[dict]:
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


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    seances_actives = Seance.objects.filter(
        user=user, statut=StatutSeance.IN_PROGRESS
    ).select_related("seance_type")
    prochaines = (
        Seance.objects.filter(user=user, statut=StatutSeance.PLANNED)
        .select_related("seance_type")
        .order_by("date", "id")[:6]
    )
    recentes = (
        Seance.objects.filter(user=user, statut=StatutSeance.COMPLETED)
        .select_related("seance_type")
        .order_by("-date", "-id")[:6]
    )
    exercices = Exercice.objects.filter(actif=True).order_by("nom")
    dernieres_mensurations = Mensuration.objects.filter(user=user).order_by("-date")[:4]
    return render(
        request,
        "workouts/dashboard.html",
        {
            "seances_actives": seances_actives,
            "prochaines": prochaines,
            "recentes": recentes,
            "exercices": exercices,
            "dernieres_mensurations": dernieres_mensurations,
        },
    )


# ── Séances ──────────────────────────────────────────────────────────────────────

@login_required
def planifier_seance(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SeancePlanificationForm(request.POST, user=request.user)
        if form.is_valid():
            seance = create_seance_from_template(
                seance_type=form.cleaned_data["seance_type"],
                date=form.cleaned_data["date"],
                user=request.user,
            )
            logger.info("Séance planifiée : pk=%s type=%s", seance.pk, seance.seance_type)
            messages.success(request, "Seance planifiee.")
            return redirect("workouts:seance_detail", pk=seance.pk)
    else:
        form = SeancePlanificationForm(user=request.user)

    return render(request, "workouts/planifier_seance.html", {"form": form})


@login_required
def seance_detail(request: HttpRequest, pk: int) -> HttpResponse:
    seance = get_object_or_404(
        Seance.objects.select_related("seance_type"), pk=pk, user=request.user
    )
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
@login_required
def demarrer_seance(request: HttpRequest, pk: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=pk, user=request.user)
    start_seance(seance)
    logger.info("Séance démarrée : pk=%s", seance.pk)
    messages.success(request, "Seance demarree.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
@login_required
def terminer_seance(request: HttpRequest, pk: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=pk, user=request.user)
    complete_seance(seance)
    logger.info("Séance terminée : pk=%s durée=%s", seance.pk, seance.duration)
    messages.success(request, "Seance terminee.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
@login_required
def update_ligne(request: HttpRequest, pk: int) -> HttpResponse:
    ligne = get_object_or_404(
        SessionLigne.objects.select_related("seance", "exercice"),
        pk=pk,
        seance__user=request.user,
    )
    form = SessionLigneQuickForm(request.POST, instance=ligne)
    wants_json = request.headers.get("Accept") == "application/json"
    if ligne.is_completed:
        logger.warning("Tentative de re-validation ligne déjà validée : pk=%s", pk)
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
        logger.info(
            "Série validée : ligne_pk=%s exercice=%s serie=%s volume=%s",
            ligne.pk, ligne.exercice.nom, ligne.numero_serie, ligne.volume,
        )
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
        logger.debug("Formulaire invalide pour ligne pk=%s : %s", pk, form.errors)
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    else:
        messages.error(request, "Impossible d'enregistrer cette serie.")

    return redirect("workouts:seance_detail", pk=ligne.seance_id)


@require_POST
@login_required
def update_ordre_exercice(request: HttpRequest, pk: int, ordre_prevu: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=pk, user=request.user)
    wants_json = request.headers.get("Accept") == "application/json"

    raw_value = request.POST.get("ordre", "").strip()
    try:
        ordre_reel = int(raw_value) if raw_value else ordre_prevu
        if ordre_reel < 1:
            raise ValueError
    except ValueError:
        logger.warning("Ordre invalide reçu : '%s' pour séance pk=%s", raw_value, pk)
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
        return JsonResponse({"ok": True, "updated_count": updated_count, "ordre": current_order})
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
@login_required
def ajouter_ligne(request: HttpRequest, pk: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=pk, user=request.user)
    form = AddSessionLineForm(request.POST)
    if form.is_valid():
        ligne = add_unplanned_session_line(seance=seance, **form.cleaned_data)
        logger.info("Série hors-template ajoutée : séance pk=%s exercice=%s", pk, ligne.exercice.nom)
        messages.success(request, "Serie ajoutee.")
    else:
        messages.error(request, "Impossible d'ajouter cette serie.")
    return redirect("workouts:seance_detail", pk=seance.pk)


@require_POST
@login_required
def update_notes(request: HttpRequest, pk: int) -> HttpResponse:
    seance = get_object_or_404(Seance, pk=pk, user=request.user)
    form = SeanceNotesForm(request.POST, instance=seance)
    if form.is_valid():
        form.save()
        messages.success(request, "Notes enregistrees.")
    else:
        messages.error(request, "Impossible d'enregistrer les notes.")
    return redirect("workouts:seance_detail", pk=seance.pk)


# ── Historique ────────────────────────────────────────────────────────────────────

@login_required
def historique(request: HttpRequest) -> HttpResponse:
    seances = (
        Seance.objects.filter(user=request.user, statut=StatutSeance.COMPLETED)
        .select_related("seance_type")
        .prefetch_related("lignes")
        .order_by("-date", "-id")
    )
    return render(request, "workouts/historique.html", {"seances": seances})


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sport-app-export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "date", "seance", "statut", "ordre_prevu", "ordre_reel",
            "exercice", "numero_serie", "repetitions_cible", "charge_cible",
            "rpe_cible", "repetitions_reelles", "charge_reelle", "rpe_reel",
            "validee", "completed_at",
        ]
    )

    lignes = SessionLigne.objects.filter(
        seance__user=request.user
    ).select_related(
        "seance", "seance__seance_type", "exercice"
    ).order_by("seance__date", "seance_id", "ordre_prevu", "numero_serie")

    row_count = 0
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
        row_count += 1

    logger.info("Export CSV : %s lignes exportées", row_count)
    return response


# ── Mensurations ──────────────────────────────────────────────────────────────────

_MENSURATION_CHAMPS: list[tuple[str, str, str]] = [
    ("poids",         "Poids",    "kg"),
    ("tour_poitrine", "Poitrine", "cm"),
    ("tour_taille",   "Taille",   "cm"),
    ("tour_hanches",  "Hanches",  "cm"),
    ("tour_bras",     "Bras",     "cm"),
    ("tour_cuisse",   "Cuisse",   "cm"),
    ("masse_grasse",  "MG",       "%"),
]


def _build_mensuration_rows(entries: list[Mensuration]) -> list[dict]:
    rows = []
    for i, entry in enumerate(entries):
        prev = entries[i + 1] if i + 1 < len(entries) else None
        cells = []
        for field, label, unit in _MENSURATION_CHAMPS:
            value = getattr(entry, field)
            prev_value = getattr(prev, field) if prev else None
            delta = (value - prev_value) if (value is not None and prev_value is not None) else None
            cells.append({"field": field, "label": label, "unit": unit, "value": value, "delta": delta})
        rows.append({"entry": entry, "cells": cells})
    return rows


@login_required
def mensurations(request: HttpRequest) -> HttpResponse:
    entries = list(Mensuration.objects.filter(user=request.user).order_by("-date"))
    return render(request, "workouts/mensurations.html", {
        "rows": _build_mensuration_rows(entries),
        "champs": _MENSURATION_CHAMPS,
    })


@login_required
def ajouter_mensuration(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = MensurationForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.user = request.user
            m.save()
            logger.info("Mensuration ajoutée : pk=%s date=%s", m.pk, m.date)
            messages.success(request, "Mensurations enregistrées.")
            return redirect("workouts:mensurations")
    else:
        form = MensurationForm(initial={"date": date.today()})
    return render(request, "workouts/mensuration_form.html", {"form": form, "titre": "Nouvelle saisie"})


@login_required
def modifier_mensuration(request: HttpRequest, pk: int) -> HttpResponse:
    mensuration = get_object_or_404(Mensuration, pk=pk, user=request.user)
    if request.method == "POST":
        form = MensurationForm(request.POST, instance=mensuration)
        if form.is_valid():
            form.save()
            logger.info("Mensuration modifiée : pk=%s date=%s", mensuration.pk, mensuration.date)
            messages.success(request, "Mensurations modifiées.")
            return redirect("workouts:mensurations")
    else:
        form = MensurationForm(instance=mensuration)
    return render(request, "workouts/mensuration_form.html", {
        "form": form,
        "titre": "Modifier",
        "mensuration": mensuration,
    })


# ── Backup / Restore ──────────────────────────────────────────────────────────────

_BACKUP_MODELS: list[tuple[str, type]] = [
    ("exercices",       Exercice),
    ("seance_types",    SeanceType),
    ("mensurations",    Mensuration),
    ("template_lignes", TemplateLigne),
    ("seances",         Seance),
    ("session_lignes",  SessionLigne),
]


@login_required
def backup_page(request: HttpRequest) -> HttpResponse:
    return render(request, "workouts/backup.html")


@login_required
def export_backup(request: HttpRequest) -> HttpResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, model in _BACKUP_MODELS:
            data = django_serializers.serialize("json", model.objects.all(), indent=2)
            zf.writestr(f"{name}.json", data)

    buffer.seek(0)
    filename = f"sport_backup_{date.today().isoformat()}.zip"
    response = HttpResponse(buffer.read(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    logger.info("Backup exporté : %s", filename)
    return response


@login_required
def export_sessions_csv(request: HttpRequest) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = (
        f'attachment; filename="sessions_{date.today().isoformat()}.csv"'
    )
    response.write("﻿")

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Date", "Type", "Ordre", "Exercice", "Série",
        "Répétitions cibles", "Charge cible (kg)", "Repos (sec)", "RPE Cible", "Tempo",
        "Charge réelle (kg)", "Reps réelles", "RPE réel (0-10)",
    ])

    lignes = (
        SessionLigne.objects
        .filter(seance__user=request.user, seance__statut=StatutSeance.COMPLETED)
        .select_related("seance", "seance__seance_type", "exercice")
        .order_by("seance__date", "seance_id", "ordre_prevu", "numero_serie")
    )

    row_count = 0
    for ligne in lignes:
        writer.writerow([
            ligne.seance.date.strftime("%d/%m/%Y"),
            ligne.seance.seance_type.nom if ligne.seance.seance_type else "",
            ligne.ordre_prevu,
            ligne.exercice.nom,
            f"S{ligne.numero_serie}",
            ligne.repetitions_cible if ligne.repetitions_cible is not None else "",
            ligne.charge_cible if ligne.charge_cible is not None else "",
            ligne.repos_secondes if ligne.repos_secondes is not None else "",
            ligne.rpe_cible if ligne.rpe_cible is not None else "",
            ligne.tempo or "",
            ligne.charge_reelle if ligne.charge_reelle is not None else "",
            ligne.repetitions_reelles if ligne.repetitions_reelles is not None else "",
            ligne.rpe_reel if ligne.rpe_reel is not None else "",
        ])
        row_count += 1

    logger.info("Export sessions CSV : %s lignes exportées", row_count)
    return response


@require_POST
@login_required
def import_backup(request: HttpRequest) -> HttpResponse:
    zip_file = request.FILES.get("backup_file")
    if not zip_file:
        messages.error(request, "Aucun fichier sélectionné.")
        return redirect("workouts:backup_page")

    if not zipfile.is_zipfile(zip_file):
        messages.error(request, "Le fichier n'est pas un zip valide.")
        return redirect("workouts:backup_page")

    try:
        with transaction.atomic():
            for name, model in reversed(_BACKUP_MODELS):
                model.objects.all().delete()

            zip_file.seek(0)
            with zipfile.ZipFile(zip_file) as zf:
                available = zf.namelist()
                for name, _model in _BACKUP_MODELS:
                    filename = f"{name}.json"
                    if filename not in available:
                        logger.warning("Fichier manquant dans le zip : %s", filename)
                        continue
                    data = zf.read(filename).decode("utf-8")
                    for obj in django_serializers.deserialize("json", data):
                        obj.save()

            from io import StringIO
            buf = StringIO()
            call_command("sqlsequencereset", "workouts", stdout=buf, no_color=True)
            sql = buf.getvalue()
            if sql:
                with connection.cursor() as cursor:
                    cursor.execute(sql)

        logger.info("Backup importé avec succès")
        messages.success(request, "Import réussi — toutes les données ont été restaurées.")
    except Exception as exc:
        logger.exception("Échec de l'import backup : %s", exc)
        messages.error(request, f"Erreur lors de l'import : {exc}")

    return redirect("workouts:backup_page")


# ── Progression ────────────────────────────────────────────────────────────────────

# ── Hub Planifier ─────────────────────────────────────────────────────────────────

@login_required
def planifier_hub(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SeancePlanificationForm(request.POST, user=request.user)
        if form.is_valid():
            seance = create_seance_from_template(
                seance_type=form.cleaned_data["seance_type"],
                date=form.cleaned_data["date"],
                user=request.user,
            )
            logger.info("Séance planifiée depuis hub : pk=%s", seance.pk)
            messages.success(request, "Séance planifiée.")
            return redirect("workouts:seance_detail", pk=seance.pk)
    else:
        form = SeancePlanificationForm(user=request.user)

    seance_types = (
        SeanceType.objects.filter(user=request.user)
        .prefetch_related("lignes__exercice")
        .order_by("nom")
    )
    exercices = Exercice.objects.filter(actif=True).order_by("nom")
    return render(
        request,
        "workouts/planifier_hub.html",
        {
            "form": form,
            "seance_types": seance_types,
            "exercices": exercices,
        },
    )


# ── CRUD SeanceType ───────────────────────────────────────────────────────────────

@login_required
def creer_seance_type(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SeanceTypeForm(request.POST)
        formset = TemplateLigneFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            seance_type = form.save(commit=False)
            seance_type.user = request.user
            seance_type.save()
            formset.instance = seance_type
            formset.save()
            logger.info("SeanceType créé : pk=%s nom='%s'", seance_type.pk, seance_type.nom)
            messages.success(request, f"Type de séance « {seance_type.nom} » créé.")
            return redirect("workouts:planifier_hub")
    else:
        form = SeanceTypeForm()
        formset = TemplateLigneFormSet()
    return render(
        request,
        "workouts/seance_type_form.html",
        {"form": form, "formset": formset, "titre": "Nouveau type de séance"},
    )


@login_required
def modifier_seance_type(request: HttpRequest, pk: int) -> HttpResponse:
    seance_type = get_object_or_404(SeanceType, pk=pk, user=request.user)
    if request.method == "POST":
        form = SeanceTypeForm(request.POST, instance=seance_type)
        formset = TemplateLigneFormSet(request.POST, instance=seance_type)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            logger.info("SeanceType modifié : pk=%s", seance_type.pk)
            messages.success(request, f"Type de séance « {seance_type.nom} » mis à jour.")
            return redirect("workouts:planifier_hub")
    else:
        form = SeanceTypeForm(instance=seance_type)
        formset = TemplateLigneFormSet(instance=seance_type)
    return render(
        request,
        "workouts/seance_type_form.html",
        {"form": form, "formset": formset, "titre": f"Modifier — {seance_type.nom}", "seance_type": seance_type},
    )


@require_POST
@login_required
def supprimer_seance_type(request: HttpRequest, pk: int) -> HttpResponse:
    seance_type = get_object_or_404(SeanceType, pk=pk, user=request.user)
    nom = seance_type.nom
    seance_type.delete()
    logger.info("SeanceType supprimé : pk=%s nom='%s'", pk, nom)
    messages.success(request, f"Type de séance « {nom} » supprimé.")
    return redirect("workouts:planifier_hub")


# ── Exercices ─────────────────────────────────────────────────────────────────────

@login_required
def ajouter_exercice(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ExerciceForm(request.POST)
        if form.is_valid():
            ex = form.save()
            logger.info("Exercice créé : pk=%s nom='%s'", ex.pk, ex.nom)
            messages.success(request, f"Exercice « {ex.nom} » ajouté.")
            return redirect("workouts:planifier_hub")
    else:
        form = ExerciceForm()
    return render(request, "workouts/exercice_form.html", {"form": form})


# ── Progression ────────────────────────────────────────────────────────────────────

@login_required
def progression_page(request: HttpRequest) -> HttpResponse:
    exercices = Exercice.objects.filter(actif=True).order_by("nom")
    return render(request, "workouts/progression.html", {"exercices": exercices})


@login_required
def progression_data(request: HttpRequest) -> JsonResponse:
    try:
        exercice_id = int(request.GET["exercice_id"])
    except (KeyError, ValueError):
        return JsonResponse({"ok": False, "errors": "exercice_id invalide"}, status=400)

    indicateur = request.GET.get("indicateur", "1rm")
    if indicateur not in ("1rm", "tonnage"):
        indicateur = "1rm"

    exercice = get_object_or_404(Exercice, pk=exercice_id)
    points = progression_exercice(exercice_id, user=request.user, indicateur=indicateur)
    pr = max((p["valeur"] for p in points), default=None)
    unite = "kg (1RM estimé)" if indicateur == "1rm" else "kg (tonnage)"

    return JsonResponse({
        "ok": True,
        "exercice_nom": exercice.nom,
        "labels": [p["date"] for p in points],
        "values": [p["valeur"] for p in points],
        "pr": pr,
        "unite": unite,
    })
