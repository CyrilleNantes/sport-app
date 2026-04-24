from django import forms

from .models import Exercice, Mensuration, Seance, SeanceType, SessionLigne


class SeancePlanificationForm(forms.Form):
    seance_type = forms.ModelChoiceField(
        label="Seance type",
        queryset=SeanceType.objects.all(),
    )
    date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


class SeanceNotesForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class SessionLigneQuickForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ligne = self.instance
        if ligne and ligne.pk:
            defaults = {
                "repetitions_reelles": ligne.repetitions_cible,
                "charge_reelle": ligne.charge_cible,
                "rpe_reel": ligne.rpe_cible,
            }
            for field_name, value in defaults.items():
                if getattr(ligne, field_name) is None:
                    self.initial[field_name] = value
                    self.fields[field_name].initial = value
            if ligne.is_completed:
                for field in self.fields.values():
                    field.disabled = True

    class Meta:
        model = SessionLigne
        fields = [
            "repetitions_reelles",
            "charge_reelle",
            "rpe_reel",
        ]
        widgets = {
            "repetitions_reelles": forms.NumberInput(
                attrs={"min": 0, "inputmode": "numeric"}
            ),
            "charge_reelle": forms.NumberInput(
                attrs={"step": "0.5", "inputmode": "decimal"}
            ),
            "rpe_reel": forms.NumberInput(attrs={"min": 0, "max": 10, "step": "0.5"}),
        }


class MensurationForm(forms.ModelForm):
    class Meta:
        model = Mensuration
        fields = [
            "date",
            "poids",
            "tour_poitrine",
            "tour_taille",
            "tour_hanches",
            "tour_bras",
            "tour_cuisse",
            "masse_grasse",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "poids": forms.NumberInput(attrs={"step": "0.1", "inputmode": "decimal"}),
            "tour_poitrine": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
            "tour_taille": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
            "tour_hanches": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
            "tour_bras": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
            "tour_cuisse": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
            "masse_grasse": forms.NumberInput(attrs={"step": "0.1", "inputmode": "decimal"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class AddSessionLineForm(forms.Form):
    exercice = forms.ModelChoiceField(
        queryset=Exercice.objects.filter(actif=True),
        label="Exercice",
    )
    repetitions_cible = forms.IntegerField(label="Reps", min_value=0, required=False)
    charge_cible = forms.DecimalField(
        label="Charge",
        min_value=0,
        max_digits=6,
        decimal_places=2,
        required=False,
    )
    rpe_cible = forms.DecimalField(
        label="RPE",
        min_value=0,
        max_value=10,
        max_digits=3,
        decimal_places=1,
        required=False,
    )
    repos_secondes = forms.IntegerField(label="Repos", min_value=0, required=False)
    tempo = forms.CharField(label="Tempo", max_length=30, required=False)
