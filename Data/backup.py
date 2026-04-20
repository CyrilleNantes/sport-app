import os
import sys
import django
import json
from datetime import datetime

sys.path.append(r"C:\dev\sport-app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from workouts.models import Exercice, SeanceType, Seance, TemplateLigne, SessionLigne

# dossier backup
BACKUP_DIR = r"C:\dev\sport-app\data\backup"
os.makedirs(BACKUP_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

def export_model(model, name):
    data = list(model.objects.all().values())
    file_path = os.path.join(BACKUP_DIR, f"{name}_{timestamp}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"✔ {name} exporté ({len(data)} lignes)")

# export
export_model(Exercice, "exercices")
export_model(SeanceType, "seances_types")
export_model(TemplateLigne, "template_lignes")
export_model(Seance, "seances")
export_model(SessionLigne, "session_lignes")

print("\n✅ Backup JSON terminé")