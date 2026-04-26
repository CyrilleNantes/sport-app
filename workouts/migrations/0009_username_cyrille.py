"""
Migration de données : renomme le username de Cyrille de son adresse email
vers l'identifiant court "cyrille".
Nécessaire pour les environnements où 0008 a déjà tourné (dev + prod).
"""
from django.db import migrations


def renommer_username_cyrille(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="cyrille.limousin@gmail.com").update(username="cyrille")


def reverse_migration(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="cyrille").update(username="cyrille.limousin@gmail.com")


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0008_data_cyrille"),
    ]

    operations = [
        migrations.RunPython(renommer_username_cyrille, reverse_migration),
    ]
