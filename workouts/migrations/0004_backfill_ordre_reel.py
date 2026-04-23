from django.db import migrations, models


def backfill_ordre_reel(apps, schema_editor):
    SessionLigne = apps.get_model("workouts", "SessionLigne")
    SessionLigne.objects.filter(ordre_reel__isnull=True).update(
        ordre_reel=models.F("ordre_prevu")
    )


def reset_ordre_reel(apps, schema_editor):
    SessionLigne = apps.get_model("workouts", "SessionLigne")
    SessionLigne.objects.filter(ordre_reel__isnull=False).update(ordre_reel=None)


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0003_alter_exercice_categorie"),
    ]

    operations = [
        migrations.RunPython(backfill_ordre_reel, reset_ordre_reel),
    ]
