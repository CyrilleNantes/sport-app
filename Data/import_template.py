import os
import sys
import django
import pandas as pd

sys.path.append(r"C:\dev\sport-app")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from workouts.models import Exercice, SeanceType, TemplateLigne

df = pd.read_excel(r"C:\dev\sport-app\data\template_lignes.xlsx")
df.columns = df.columns.str.strip()

for _, row in df.iterrows():

    seance_type, _ = SeanceType.objects.get_or_create(
        nom=row["Séance Type"].strip()
    )

    exercice = Exercice.objects.filter(
        nom__iexact=row["Exercice"].strip()
    ).first()

    if not exercice:
        print(f"❌ Exercice introuvable: {row['Exercice']}")
        continue

    charge = float(str(row["Charge cible (kg)"]).replace(",", "."))
    rpe = float(str(row["RPE Cible"]).replace(",", "."))

    TemplateLigne.objects.get_or_create(
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
        }
    )

print("✅ Import terminé")