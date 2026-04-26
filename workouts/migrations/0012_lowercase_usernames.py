"""
Normalise tous les usernames en minuscules pour cohérence avec
la vue de connexion qui fait .lower() sur la saisie.
"""
from django.db import migrations


def lowercase_usernames(apps, schema_editor):
    User = apps.get_model("auth", "User")
    for user in User.objects.all():
        lower = user.username.lower()
        if user.username != lower:
            print(f"[0012] {user.username!r} → {lower!r}")
            User.objects.filter(pk=user.pk).update(username=lower)


def reverse_migration(apps, schema_editor):
    pass  # irréversible (on ne sait pas la casse d'origine)


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0011_reset_password_via_env"),
    ]

    operations = [
        migrations.RunPython(lowercase_usernames, reverse_migration),
    ]
