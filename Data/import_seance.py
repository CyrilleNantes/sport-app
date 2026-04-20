import os
import sys
import django
import pandas as pd

sys.path.append(r"C:\dev\sport-app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from workouts.models import Seance, SeanceType

BASE_DIR = os.path.dirname(__file__)
file_path = os.path.join(BASE_DIR, "seances.xlsx")

df = pd.read_excel(file_path)
df.columns = df.columns.str.strip()

STATUT_MAP = {
    "Terminée": "COMPLETED",
}

for _, row in df.iterrows():

    seance_type = SeanceType.objects.filter(
        nom__iexact=row["Type"].strip()
    ).first()

    if not seance_type:
        print(f"❌ SeanceType introuvable: {row['Type']}")
        continue

    statut = STATUT_MAP.get(row["Statut"], "PLANIFIEE")

    date = pd.to_datetime(row["Date"], dayfirst=True)

    Seance.objects.get_or_create(
        date=date,
        seance_type=seance_type,
        defaults={
            "statut": statut,
            "notes": "",
        }
    )

print("✅ Import séances terminé")