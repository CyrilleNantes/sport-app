import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0006_mensuration"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # UserProfile
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="utilisateur",
                    ),
                ),
            ],
            options={
                "verbose_name": "profil utilisateur",
                "verbose_name_plural": "profils utilisateurs",
            },
        ),
        # SeanceType : supprime l'unique sur nom, ajoute user FK + contrainte (user, nom)
        migrations.AlterField(
            model_name="seancetype",
            name="nom",
            field=models.CharField(max_length=120),
        ),
        migrations.AddField(
            model_name="seancetype",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="seance_types",
                to=settings.AUTH_USER_MODEL,
                verbose_name="utilisateur",
            ),
        ),
        migrations.AddConstraint(
            model_name="seancetype",
            constraint=models.UniqueConstraint(
                fields=["user", "nom"],
                name="unique_seancetype_nom_par_user",
            ),
        ),
        # Seance : ajoute user FK
        migrations.AddField(
            model_name="seance",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="seances_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="utilisateur",
            ),
        ),
        # Mensuration : ajoute user FK
        migrations.AddField(
            model_name="mensuration",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mensurations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="utilisateur",
            ),
        ),
    ]
