import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from workouts.models import Exercice, SeanceType, TemplateLigne

DEFAULT_FILE = settings.BASE_DIR / "Data" / "template_lignes.xlsx"


class Command(BaseCommand):
    help = "Importe les lignes de template depuis un fichier Excel (get_or_create)."

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
            seance_type, _ = SeanceType.objects.get_or_create(
                nom=str(row["Séance Type"]).strip()
            )

            exercice = Exercice.objects.filter(
                nom__iexact=str(row["Exercice"]).strip()
            ).first()
            if not exercice:
                self.stderr.write(f"❌ Exercice introuvable : {row['Exercice']}")
                error_count += 1
                continue

            charge = float(str(row["Charge cible (kg)"]).replace(",", "."))
            rpe = float(str(row["RPE Cible"]).replace(",", "."))

            _, created = TemplateLigne.objects.get_or_create(
                seance_type=seance_type,
                exercice=exercice,
                numero_serie=int(row["Série"]),
                defaults={
                    "ordre_exercice": int(row["Ordre"]),
                    "repetitions_cible": int(row["Répétitions cibles"]),
                    "charge_cible": charge,
                    "rpe_cible": rpe,
                    "repos_secondes": int(row["Repos (sec)"]),
                    "tempo": str(row["Tempo"]),
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import templates terminé — {created_count} créée(s), {error_count} erreur(s)."
            )
        )
