from django.db import migrations, models


def backfill_ordre_reel(apps, schema_editor):
    SessionLigne = apps.get_model("workouts", "SessionLigne")
    SessionLigne.objects.filter(ordre_reel__isnull=True).update(
        ordre_reel=models.F("ordre_prevu")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0004_backfill_ordre_reel"),
    ]

    operations = [
        migrations.RunPython(backfill_ordre_reel, migrations.RunPython.noop),
    ]
