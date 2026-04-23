import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from workouts.models import Exercice, Seance, SessionLigne

DEFAULT_FILE = settings.BASE_DIR / "Data" / "Sessions.xlsx"


def parse_float(value):
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def parse_rpe(value):
    value = str(value).replace(",", ".").strip()
    if "-" in value:
        try:
            a, b = value.split("-")
            return (float(a) + float(b)) / 2
        except (ValueError, TypeError):
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_bool(value):
    return str(value).strip().upper() == "O"


def parse_datetime(value):
    try:
        dt = pd.to_datetime(value, dayfirst=True)
        return timezone.make_aware(dt)
    except Exception:
        return None


class Command(BaseCommand):
    help = "Importe les lignes de session depuis un fichier Excel (get_or_create)."

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
            try:
                date = pd.to_datetime(row["Seance"], dayfirst=True)
                seance = Seance.objects.filter(date=date).first()
                if not seance:
                    self.stderr.write(f"❌ Séance introuvable : {row['Seance']}")
                    error_count += 1
                    continue

                exercice = Exercice.objects.filter(
                    nom__iexact=str(row["Exercice"]).strip()
                ).first()
                if not exercice:
                    self.stderr.write(f"❌ Exercice introuvable : {row['Exercice']}")
                    error_count += 1
                    continue

                _, created = SessionLigne.objects.get_or_create(
                    seance=seance,
                    exercice=exercice,
                    numero_serie=int(row["Numero serie"]),
                    defaults={
                        "ordre_prevu": int(row["Ordre prevu"]),
                        "ordre_reel": int(row["Ordre reel"]),
                        "repetitions_cible": int(row["Repetitions cible"]),
                        "charge_cible": parse_float(row["Charge cible"]),
                        "rpe_cible": parse_rpe(row["Rpe cible"]),
                        "repos_secondes": int(row["Repos secondes"]),
                        "tempo": str(row["Tempo"]),
                        "repetitions_reelles": int(row["Repetitions reelles"]),
                        "charge_reelle": parse_float(row["Charge reelle"]),
                        "rpe_reel": parse_float(row["Rpe reel"]),
                        "validee": parse_bool(row["Validee"]),
                        "completed_at": parse_datetime(row["Completed at"]),
                    },
                )
                if created:
                    created_count += 1

            except Exception as e:
                self.stderr.write(f"❌ Erreur ligne : {row.to_dict()} → {e}")
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import sessions terminé — {created_count} créée(s), {error_count} erreur(s)."
            )
        )
