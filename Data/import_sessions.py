import os
import sys
import django
import pandas as pd

# --- Setup Django ---
sys.path.append(r"C:\dev\sport-app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from workouts.models import Seance, Exercice, SessionLigne

# --- Fichier Excel ---
BASE_DIR = os.path.dirname(__file__)
file_path = os.path.join(BASE_DIR, "sessions.xlsx")

df = pd.read_excel(file_path)
df.columns = df.columns.str.strip()

# --- Helpers robustes ---
def parse_float(value):
    try:
        return float(str(value).replace(",", "."))
    except:
        return None

def parse_rpe(value):
    value = str(value).replace(",", ".").strip()
    if "-" in value:
        try:
            a, b = value.split("-")
            return (float(a) + float(b)) / 2
        except:
            return None
    try:
        return float(value)
    except:
        return None

def parse_bool(value):
    return str(value).strip().upper() == "O"

def parse_datetime(value):
    try:
        dt = pd.to_datetime(value, dayfirst=True)
        return timezone.make_aware(dt)
    except:
        return None

# --- Import ---
count = 0
errors = 0

for _, row in df.iterrows():

    try:
        # --- Séance ---
        date = pd.to_datetime(row["Seance"], dayfirst=True)

        seance = Seance.objects.filter(date=date).first()

        if not seance:
            print(f"❌ Séance introuvable: {row['Seance']}")
            errors += 1
            continue

        # --- Exercice ---
        exercice = Exercice.objects.filter(
            nom__iexact=str(row["Exercice"]).strip()
        ).first()

        if not exercice:
            print(f"❌ Exercice introuvable: {row['Exercice']}")
            errors += 1
            continue

        # --- Données ---
        charge_cible = parse_float(row["Charge cible"])
        charge_reelle = parse_float(row["Charge reelle"])

        rpe_cible = parse_rpe(row["Rpe cible"])
        rpe_reel = parse_float(row["Rpe reel"])

        validee = parse_bool(row["Validee"])
        completed_at = parse_datetime(row["Completed at"])

        # --- Création ---
        obj, created = SessionLigne.objects.get_or_create(
            seance=seance,
            exercice=exercice,
            numero_serie=int(row["Numero serie"]),
            defaults={
                "ordre_prevu": int(row["Ordre prevu"]),
                "ordre_reel": int(row["Ordre reel"]),
                "repetitions_cible": int(row["Repetitions cible"]),
                "charge_cible": charge_cible,
                "rpe_cible": rpe_cible,
                "repos_secondes": int(row["Repos secondes"]),
                "tempo": str(row["Tempo"]),
                "repetitions_reelles": int(row["Repetitions reelles"]),
                "charge_reelle": charge_reelle,
                "rpe_reel": rpe_reel,
                "validee": validee,
                "completed_at": completed_at,
            }
        )

        if created:
            count += 1

    except Exception as e:
        print(f"❌ Erreur ligne: {row} -> {e}")
        errors += 1

# --- Résumé ---
print(f"\n✅ Import terminé")
print(f"✔ Créés : {count}")
print(f"❌ Erreurs : {errors}")