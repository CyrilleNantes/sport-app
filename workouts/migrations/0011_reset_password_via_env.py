"""
Reset le mot de passe de 'cyrille' via la variable d'env CYRILLE_INIT_PASSWORD.
Après connexion réussie, supprimer la variable et cette migration peut être
squashée lors du prochain nettoyage.
"""
import os

from django.contrib.auth.hashers import make_password
from django.db import migrations


def reset_password_via_env(apps, schema_editor):
    pwd = os.environ.get("CYRILLE_INIT_PASSWORD", "")
    if not pwd:
        print("[0011] CYRILLE_INIT_PASSWORD non définie — migration sans effet.")
        return
    User = apps.get_model("auth", "User")
    updated = User.objects.filter(username="cyrille").update(
        password=make_password(pwd)
    )
    if updated:
        print("[0011] Mot de passe de 'cyrille' réinitialisé.")
    else:
        print("[0011] Utilisateur 'cyrille' introuvable — rien fait.")


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0010_reset_password_cyrille"),
    ]

    operations = [
        migrations.RunPython(reset_password_via_env, reverse_migration),
    ]
