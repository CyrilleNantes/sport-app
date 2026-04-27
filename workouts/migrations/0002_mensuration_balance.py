"""
Ajout des indicateurs de composition corporelle issus de la balance connectée :
IMC, masse grasse (kg), masse sans graisse, gras sous-cutané, graisse viscérale,
masse musculaire, muscle squelettique, masse osseuse, eau corporelle,
protéines, métabolisme de base, âge biologique.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0001_squashed"),
    ]

    operations = [
        migrations.AddField(model_name="mensuration", name="imc",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="IMC")),
        migrations.AddField(model_name="mensuration", name="masse_grasse_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Masse grasse (kg)")),
        migrations.AddField(model_name="mensuration", name="masse_sans_graisse_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Masse sans graisse (kg)")),
        migrations.AddField(model_name="mensuration", name="graisse_sous_cutanee_pct",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="Gras sous-cutané (%)")),
        migrations.AddField(model_name="mensuration", name="graisse_viscerale",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Graisse viscérale (indice)")),
        migrations.AddField(model_name="mensuration", name="masse_musculaire_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Masse musculaire (kg)")),
        migrations.AddField(model_name="mensuration", name="masse_musculaire_pct",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="Masse musculaire (%)")),
        migrations.AddField(model_name="mensuration", name="muscle_squelettique_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Muscle squelettique (kg)")),
        migrations.AddField(model_name="mensuration", name="muscle_squelettique_pct",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="Muscle squelettique (%)")),
        migrations.AddField(model_name="mensuration", name="masse_osseuse_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name="Masse osseuse (kg)")),
        migrations.AddField(model_name="mensuration", name="eau_corporelle_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Eau corporelle (kg)")),
        migrations.AddField(model_name="mensuration", name="eau_corporelle_pct",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="Eau corporelle (%)")),
        migrations.AddField(model_name="mensuration", name="proteines_kg",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="Protéines (kg)")),
        migrations.AddField(model_name="mensuration", name="proteines_pct",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name="Protéines (%)")),
        migrations.AddField(model_name="mensuration", name="metabolisme_base",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Métabolisme de base (kcal)")),
        migrations.AddField(model_name="mensuration", name="age_biologique",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Âge biologique (ans)")),
    ]
