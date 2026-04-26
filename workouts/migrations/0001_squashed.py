"""
Migration unique — remplace les 12 migrations d'origine.

Pour les environnements existants (dev/prod) : Django détecte que toutes
les migrations remplacées sont déjà appliquées et marque celle-ci comme
appliquée sans rien exécuter.

Pour un fresh install : crée le schéma complet et l'utilisateur initial
si la variable d'env CYRILLE_INIT_PASSWORD est définie.
"""
import os

import django.db.models.deletion
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def create_initial_user(apps, schema_editor):
    pwd = os.environ.get("CYRILLE_INIT_PASSWORD", "")
    if not pwd:
        return
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("workouts", "UserProfile")
    user, _ = User.objects.get_or_create(
        email="cyrille.limousin@gmail.com",
        defaults={
            "username": "cyrille",
            "first_name": "Cyrille",
            "last_name": "Limousin",
            "password": make_password(pwd),
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    UserProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    replaces = [
        ("workouts", "0001_initial"),
        ("workouts", "0002_sessionligne_validee"),
        ("workouts", "0003_alter_exercice_categorie"),
        ("workouts", "0004_backfill_ordre_reel"),
        ("workouts", "0005_backfill_ordre_reel_explicit"),
        ("workouts", "0006_mensuration"),
        ("workouts", "0007_add_user_system"),
        ("workouts", "0008_data_cyrille"),
        ("workouts", "0009_username_cyrille"),
        ("workouts", "0010_reset_password_cyrille"),
        ("workouts", "0011_reset_password_via_env"),
        ("workouts", "0012_lowercase_usernames"),
    ]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Exercice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120, unique=True)),
                ("categorie", models.CharField(
                    choices=[
                        ("ADDUCTEURS", "Adducteurs"),
                        ("ABDOS", "Abdos"),
                        ("CARDIO", "Cardio"),
                        ("DOS", "Dos"),
                        ("EPAULE_ARRIERE", "Epaule arriere"),
                        ("FESSIERS", "Fessiers"),
                        ("GAINAGE", "Gainage"),
                        ("ISCHIOS", "Ischios"),
                        ("PECTORAUX", "Pectoraux"),
                        ("QUADRICEPS", "Quadriceps"),
                        ("OTHER", "Autre"),
                    ],
                    default="OTHER",
                    max_length=20,
                )),
                ("description", models.TextField(blank=True)),
                ("video_url", models.URLField(blank=True)),
                ("actif", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "exercice",
                "verbose_name_plural": "exercices",
                "ordering": ["nom"],
            },
        ),
        migrations.CreateModel(
            name="SeanceType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="seance_types",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="utilisateur",
                )),
                ("nom", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "seance type",
                "verbose_name_plural": "seances types",
                "ordering": ["nom"],
            },
        ),
        migrations.AddConstraint(
            model_name="seancetype",
            constraint=models.UniqueConstraint(
                fields=["user", "nom"],
                name="unique_seancetype_nom_par_user",
            ),
        ),
        migrations.CreateModel(
            name="TemplateLigne",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seance_type", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="lignes",
                    to="workouts.seancetype",
                )),
                ("ordre_exercice", models.PositiveSmallIntegerField()),
                ("exercice", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="template_lignes",
                    to="workouts.exercice",
                )),
                ("numero_serie", models.PositiveSmallIntegerField()),
                ("repetitions_cible", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("charge_cible", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("rpe_cible", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("repos_secondes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("tempo", models.CharField(blank=True, max_length=30)),
            ],
            options={
                "verbose_name": "ligne de template",
                "verbose_name_plural": "lignes de template",
                "ordering": ["seance_type", "ordre_exercice", "numero_serie"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["seance_type", "ordre_exercice", "numero_serie"],
                        name="unique_template_serie_par_ordre",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(rpe_cible__isnull=True) | (models.Q(rpe_cible__gte=0) & models.Q(rpe_cible__lte=10)),
                        name="template_rpe_cible_entre_0_et_10",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Seance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="seances_user",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="utilisateur",
                )),
                ("seance_type", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="seances",
                    to="workouts.seancetype",
                )),
                ("date", models.DateField()),
                ("statut", models.CharField(
                    choices=[
                        ("PLANIFIEE", "Planifiee"),
                        ("IN_PROGRESS", "En cours"),
                        ("COMPLETED", "Terminee"),
                    ],
                    default="PLANIFIEE",
                    max_length=20,
                )),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "seance",
                "verbose_name_plural": "seances",
                "ordering": ["-date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SessionLigne",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seance", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="lignes",
                    to="workouts.seance",
                )),
                ("ordre_prevu", models.PositiveSmallIntegerField()),
                ("ordre_reel", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("exercice", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="session_lignes",
                    to="workouts.exercice",
                )),
                ("numero_serie", models.PositiveSmallIntegerField()),
                ("repetitions_cible", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("charge_cible", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("rpe_cible", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("repos_secondes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("tempo", models.CharField(blank=True, max_length=30)),
                ("repetitions_reelles", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("charge_reelle", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("rpe_reel", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("validee", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "ligne de session",
                "verbose_name_plural": "lignes de session",
                "ordering": ["seance", "ordre_reel", "ordre_prevu", "numero_serie"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["seance", "ordre_prevu", "numero_serie"],
                        name="unique_session_serie_par_ordre_prevu",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(rpe_cible__isnull=True) | (models.Q(rpe_cible__gte=0) & models.Q(rpe_cible__lte=10)),
                        name="session_rpe_cible_entre_0_et_10",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(rpe_reel__isnull=True) | (models.Q(rpe_reel__gte=0) & models.Q(rpe_reel__lte=10)),
                        name="session_rpe_reel_entre_0_et_10",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="profile",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="utilisateur",
                )),
            ],
            options={
                "verbose_name": "profil utilisateur",
                "verbose_name_plural": "profils utilisateurs",
            },
        ),
        migrations.CreateModel(
            name="Mensuration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="mensurations",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="utilisateur",
                )),
                ("date", models.DateField()),
                ("poids", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Poids (kg)")),
                ("tour_poitrine", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Tour de poitrine (cm)")),
                ("tour_taille", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Tour de taille (cm)")),
                ("tour_hanches", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Tour de hanches (cm)")),
                ("tour_bras", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Tour de bras (cm)")),
                ("tour_cuisse", models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name="Tour de cuisse (cm)")),
                ("masse_grasse", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="% masse grasse")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "mensuration",
                "verbose_name_plural": "mensurations",
                "ordering": ["-date"],
            },
        ),
        migrations.RunPython(create_initial_user, migrations.RunPython.noop),
    ]
