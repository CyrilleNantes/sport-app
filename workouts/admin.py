from django.contrib import admin

from .models import Exercice, Mensuration, Seance, SeanceType, SessionLigne, TemplateLigne, UserProfile
from .services import copy_template_lines_to_seance


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "get_email", "get_full_name")
    search_fields = ("user__email", "user__first_name", "user__last_name")

    @admin.display(description="Email")
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description="Nom complet")
    def get_full_name(self, obj):
        return obj.user.get_full_name()


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
    list_display = ("nom", "user", "updated_at")
    list_filter = ("user",)
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
    list_display = ("date", "user", "seance_type", "statut", "started_at", "ended_at")
    list_filter = ("statut", "user", "date", "seance_type")
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


@admin.register(Mensuration)
class MensurationAdmin(admin.ModelAdmin):
    list_display = ("date", "user", "poids", "tour_taille", "tour_poitrine", "tour_bras", "masse_grasse")
    list_filter = ("user", "date")
    ordering = ("-date",)


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
    list_filter = ("seance__statut", "seance__user", "exercice")
    autocomplete_fields = ("seance", "exercice")
