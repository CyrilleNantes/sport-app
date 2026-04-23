import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from workouts.models import Seance, SeanceType

DEFAULT_FILE = settings.BASE_DIR / "Data" / "Seances.xlsx"

STATUT_MAP = {
    "Terminée": "COMPLETED",
    "En cours": "IN_PROGRESS",
    "Planifiée": "PLANIFIEE",
}


class Command(BaseCommand):
    help = "Importe les séances depuis un fichier Excel (get_or_create)."

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
        error_count = 0

        for _, row in df.iterrows():
            seance_type = SeanceType.objects.filter(
                nom__iexact=str(row["Type"]).strip()
            ).first()

            if not seance_type:
                self.stderr.write(f"❌ SeanceType introuvable : {row['Type']}")
                error_count += 1
                continue

            statut = STATUT_MAP.get(str(row["Statut"]).strip(), "PLANIFIEE")
            date = pd.to_datetime(row["Date"], dayfirst=True)

            _, created = Seance.objects.get_or_create(
                date=date,
                seance_type=seance_type,
                defaults={
                    "statut": statut,
                    "notes": "",
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import séances terminé — {created_count} créée(s), {error_count} erreur(s)."
            )
        )
