import os
import sys
import django
import pandas as pd

sys.path.append(r"C:\dev\sport-app")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from workouts.models import Exercice

df = pd.read_excel(r"C:\dev\sport-app\data\exercices.xlsx")

# nettoyage colonnes
df.columns = df.columns.str.strip()

for _, row in df.iterrows():
    Exercice.objects.get_or_create(
        nom=row["Nom"],
        defaults={
            "categorie": str(row["Catégories"]).strip(),
            "description": str(row["Description"]).strip(),
            "video_url": "" if pd.isna(row.get("URL")) else str(row["URL"]),
            "actif": True,
        }
    )

print("Import terminé")




