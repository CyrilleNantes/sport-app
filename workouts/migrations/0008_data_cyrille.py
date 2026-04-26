from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_cyrille_and_assign_data(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("workouts", "UserProfile")
    SeanceType = apps.get_model("workouts", "SeanceType")
    Seance = apps.get_model("workouts", "Seance")
    Mensuration = apps.get_model("workouts", "Mensuration")

    user, created = User.objects.get_or_create(
        email="cyrille.limousin@gmail.com",
        defaults={
            "username": "cyrille",
            "first_name": "Cyrille",
            "last_name": "Limousin",
            "password": make_password("Cyrille"),
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )

    UserProfile.objects.get_or_create(user=user)

    SeanceType.objects.filter(user__isnull=True).update(user=user)
    Seance.objects.filter(user__isnull=True).update(user=user)
    Mensuration.objects.filter(user__isnull=True).update(user=user)


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0007_add_user_system"),
    ]

    operations = [
        migrations.RunPython(create_cyrille_and_assign_data, reverse_migration),
    ]
