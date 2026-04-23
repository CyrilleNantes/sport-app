import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from workouts.models import Exercice, Seance, SeanceType, SessionLigne, TemplateLigne

DEFAULT_DIR = settings.BASE_DIR / "Data" / "Backup"


class Command(BaseCommand):
    help = "Exporte tous les modèles en JSON dans un dossier de backup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_DIR),
            help=f"Dossier de destination (défaut : {DEFAULT_DIR})",
        )

    def handle(self, *args, **options):
        backup_dir = Path(options["dir"])
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        models = [
            (Exercice, "exercices"),
            (SeanceType, "seances_types"),
            (TemplateLigne, "template_lignes"),
            (Seance, "seances"),
            (SessionLigne, "session_lignes"),
        ]

        for model, name in models:
            data = list(model.objects.all().values())
            file_path = backup_dir / f"{name}_{timestamp}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self.stdout.write(f"  ✔ {name} — {len(data)} ligne(s) → {file_path.name}")

        self.stdout.write(self.style.SUCCESS("✅ Backup terminé."))
