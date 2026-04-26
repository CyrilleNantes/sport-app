"""
Migration de secours : remet le mot de passe de Cyrille à "Cyrille2025"
pour permettre la reconnexion après le changement d'identifiant.
"""
from django.contrib.auth.hashers import make_password
from django.db import migrations


def reset_password_cyrille(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="cyrille").update(
        password=make_password("Cyrille2025")
    )


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0009_username_cyrille"),
    ]

    operations = [
        migrations.RunPython(reset_password_cyrille, reverse_migration),
    ]
