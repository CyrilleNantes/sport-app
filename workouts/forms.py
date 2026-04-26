from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from .models import Exercice, Mensuration, Seance, SeanceType, SessionLigne, TemplateLigne

User = get_user_model()


# ── Auth ────────────────────────────────────────────────────────────────────────

class InscriptionForm(forms.Form):
    prenom = forms.CharField(max_length=50, label="Prénom")
    nom = forms.CharField(max_length=50, label="Nom")
    username = forms.CharField(
        max_length=150,
        label="Identifiant de connexion",
        help_text="Lettres, chiffres et . @ + - _ uniquement.",
    )
    email = forms.EmailField(label="Adresse email", required=False)
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data


# ── Types de séance ──────────────────────────────────────────────────────────────

class SeanceTypeForm(forms.ModelForm):
    class Meta:
        model = SeanceType
        fields = ["nom", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class TemplateLigneInlineForm(forms.ModelForm):
    class Meta:
        model = TemplateLigne
        fields = [
            "ordre_exercice", "exercice", "numero_serie",
            "repetitions_cible", "charge_cible", "rpe_cible",
            "repos_secondes", "tempo",
        ]
        widgets = {
            "ordre_exercice":    forms.NumberInput(attrs={"min": 1, "class": "tl-xs"}),
            "exercice":          forms.Select(attrs={"class": "tl-exercice"}),
            "numero_serie":      forms.NumberInput(attrs={"min": 1, "class": "tl-xs"}),
            "repetitions_cible": forms.NumberInput(attrs={"min": 0, "class": "tl-sm", "inputmode": "numeric"}),
            "charge_cible":      forms.NumberInput(attrs={"step": "0.5", "class": "tl-sm", "inputmode": "decimal"}),
            "rpe_cible":         forms.NumberInput(attrs={"min": 0, "max": 10, "step": "0.5", "class": "tl-sm"}),
            "repos_secondes":    forms.NumberInput(attrs={"min": 0, "class": "tl-sm"}),
            "tempo":             forms.TextInput(attrs={"class": "tl-sm"}),
        }


TemplateLigneFormSet = inlineformset_factory(
    SeanceType,
    TemplateLigne,
    form=TemplateLigneInlineForm,
    extra=3,
    can_delete=True,
    min_num=0,
)


# ── Exercices ─────────────────────────────────────────────────────────────────────

class ExerciceForm(forms.ModelForm):
    class Meta:
        model = Exercice
        fields = ["nom", "categorie", "description", "video_url"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


# ── Séances ─────────────────────────────────────────────────────────────────────

class SeancePlanificationForm(forms.Form):
    seance_type = forms.ModelChoiceField(
        label="Type de séance",
        queryset=SeanceType.objects.none(),
    )
    date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["seance_type"].queryset = SeanceType.objects.filter(
                user=user
            ).order_by("nom")


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


# ── Mensurations ─────────────────────────────────────────────────────────────────

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


# ── Ajout série hors-gabarit ─────────────────────────────────────────────────────

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
