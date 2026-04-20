from django.contrib import admin

from .models import Exercice, Seance, SeanceType, SessionLigne, TemplateLigne
from .services import copy_template_lines_to_seance


@admin.register(Exercice)
class ExerciceAdmin(admin.ModelAdmin):
    list_display = ("nom", "categorie", "actif")
    list_filter = ("categorie", "actif")
    search_fields = ("nom", "description")


class TemplateLigneInline(admin.TabularInline):
    model = TemplateLigne
    extra = 1
    autocomplete_fields = ("exercice",)
    ordering = ("ordre_exercice", "numero_serie")


@admin.register(SeanceType)
class SeanceTypeAdmin(admin.ModelAdmin):
    list_display = ("nom", "updated_at")
    search_fields = ("nom", "description")
    inlines = [TemplateLigneInline]


class SessionLigneInline(admin.TabularInline):
    model = SessionLigne
    extra = 0
    autocomplete_fields = ("exercice",)
    ordering = ("ordre_reel", "ordre_prevu", "numero_serie")
    readonly_fields = ("validee", "completed_at")


@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ("date", "seance_type", "statut", "started_at", "ended_at")
    list_filter = ("statut", "date", "seance_type")
    search_fields = ("notes",)
    inlines = [SessionLigneInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            copy_template_lines_to_seance(form.instance)


@admin.register(TemplateLigne)
class TemplateLigneAdmin(admin.ModelAdmin):
    list_display = (
        "seance_type",
        "ordre_exercice",
        "exercice",
        "numero_serie",
        "repetitions_cible",
        "charge_cible",
        "rpe_cible",
    )
    list_filter = ("seance_type", "exercice")
    autocomplete_fields = ("seance_type", "exercice")


@admin.register(SessionLigne)
class SessionLigneAdmin(admin.ModelAdmin):
    list_display = (
        "seance",
        "ordre_prevu",
        "ordre_reel",
        "exercice",
        "numero_serie",
        "repetitions_reelles",
        "charge_reelle",
        "rpe_reel",
        "validee",
        "completed_at",
    )
    list_filter = ("seance__statut", "exercice")
    autocomplete_fields = ("seance", "exercice")
