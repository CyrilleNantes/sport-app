from django.urls import path

from . import views

app_name = "workouts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("seances/planifier/", views.planifier_seance, name="planifier_seance"),
    path("seances/<int:pk>/", views.seance_detail, name="seance_detail"),
    path("seances/<int:pk>/demarrer/", views.demarrer_seance, name="demarrer_seance"),
    path("seances/<int:pk>/terminer/", views.terminer_seance, name="terminer_seance"),
    path(
        "seances/<int:pk>/ordre/<int:ordre_prevu>/",
        views.update_ordre_exercice,
        name="update_ordre_exercice",
    ),
    path("seances/<int:pk>/ajouter-ligne/", views.ajouter_ligne, name="ajouter_ligne"),
    path("seances/<int:pk>/notes/", views.update_notes, name="update_notes"),
    path("lignes/<int:pk>/", views.update_ligne, name="update_ligne"),
    path("historique/", views.historique, name="historique"),
    path("historique/export.csv", views.export_csv, name="export_csv"),
    path("mensurations/", views.mensurations, name="mensurations"),
    path("mensurations/ajouter/", views.ajouter_mensuration, name="ajouter_mensuration"),
    path("mensurations/<int:pk>/modifier/", views.modifier_mensuration, name="modifier_mensuration"),
    path("backup/", views.backup_page, name="backup_page"),
    path("backup/export/", views.export_backup, name="export_backup"),
    path("backup/import/", views.import_backup, name="import_backup"),
]
