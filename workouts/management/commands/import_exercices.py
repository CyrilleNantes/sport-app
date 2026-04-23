import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from workouts.models import Exercice

DEFAULT_FILE = settings.BASE_DIR / "Data" / "Exercices.xlsx"


class Command(BaseCommand):
    help = "Importe les exercices depuis un fichier Excel (get_or_create)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(DEFAULT_FILE),
            help=f"Chemin vers le fichier Excel (défaut : {DEFAULT_FILE})",
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        try:
            df = pd.read_excel(file_path)
        except FileNotFoundError:
            raise CommandError(f"Fichier introuvable : {file_path}")

        df.columns = df.columns.str.strip()
        created_count = 0

        for _, row in df.iterrows():
            _, created = Exercice.objects.get_or_create(
                nom=row["Nom"],
                defaults={
                    "categorie": str(row["Catégories"]).strip(),
                    "description": str(row["Description"]).strip(),
                    "video_url": "" if pd.isna(row.get("URL")) else str(row["URL"]),
                    "actif": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import exercices terminé — {created_count} créé(s)."
            )
        )
