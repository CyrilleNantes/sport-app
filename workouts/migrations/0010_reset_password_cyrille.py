"""
Migration rendue neutre : le reset de mot de passe se fait désormais via
la variable d'env CYRILLE_INIT_PASSWORD (Railway) pour ne pas exposer
de secret dans le code.
"""
import os

from django.contrib.auth.hashers import make_password
from django.db import migrations


def reset_password_cyrille(apps, schema_editor):
    pwd = os.environ.get("CYRILLE_INIT_PASSWORD", "")
    if not pwd:
        return  # pas de variable → on ne touche pas au mot de passe
    User = apps.get_model("auth", "User")
    updated = User.objects.filter(username="cyrille").update(
        password=make_password(pwd)
    )
    if updated:
        print(f"[0010] Mot de passe de 'cyrille' réinitialisé via CYRILLE_INIT_PASSWORD.")


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0009_username_cyrille"),
    ]

    operations = [
        migrations.RunPython(reset_password_cyrille, reverse_migration),
    ]
