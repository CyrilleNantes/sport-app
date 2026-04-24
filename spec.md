# Spécifications Fonctionnelles — Sport App

> Document vivant — mis à jour par l'IA après chaque implémentation validée.
> Dernière mise à jour : 2026-04-24

---

## 1. Contexte, Objectifs et Limites

### 1.1 Objectif principal

Application web Django de suivi d'entraînement de musculation pour un utilisateur solo. Elle permet de planifier des séances à partir de gabarits, de les dérouler en temps réel avec validation série par série et timer de repos, puis de consulter l'historique et de suivre les mensurations corporelles.

### 1.2 Périmètre inclus

- Gestion des types de séance (gabarits d'exercices et de séries)
- Planification d'une séance à partir d'un gabarit
- Déroulement en temps réel : démarrage, validation AJAX des séries, timer de repos, réordonnancement des exercices, ajout de séries hors-template
- Historique des séances terminées avec export CSV
- Suivi des mensurations corporelles (poids, tours de corps, masse grasse)
- Backup & restore complet (export ZIP JSON + import destructif atomique)
- Export CSV lisible des séances terminées (compatible Excel)
- Interface d'administration Django complète

### 1.3 Hors périmètre (Anti-Scope)

> ⚠️ CRITIQUE — L'IA ne doit jamais implémenter ce qui suit sans accord explicite.

- Ne PAS implémenter de notifications push ni de rappels programmés
- Ne PAS exposer DRF publiquement — présent dans requirements.txt mais non utilisé
- Ne PAS créer de vue de suppression dans l'UI — la suppression est réservée à l'admin Django
- Ne PAS modifier `ordre_prevu` après création d'une `SessionLigne` — c'est la clé de référence immuable
- Ne PAS appeler `copy_template_lines_to_seance` si la séance a déjà des lignes

---

## 2. Acteurs et Rôles

| Acteur | Description | Accès |
|--------|-------------|-------|
| Utilisateur unique | Acteur principal | Accès complet à toutes les fonctionnalités sans authentification |
| Administrateur Django | Gestion système | CRUD complet via `/admin/` |

L'application n'implémente aucune restriction d'accès par rôle ou session utilisateur. Toutes les URLs sont publiques.

---

## 3. Services externes

Aucun service externe pour ce projet. Pas d'intégration OAuth2, pas d'appel API sortant.

---

## 4. Modèle de Données

### 4.1 `Exercice`

Référentiel des exercices disponibles.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `nom` | `CharField(120)` | non | — | Nom unique de l'exercice |
| `categorie` | `CharField(20)` | non | `OTHER` | Catégorie musculaire (voir TextChoices) |
| `description` | `TextField` | non | `""` | Description libre |
| `video_url` | `URLField` | non | `""` | URL de vidéo de démonstration |
| `actif` | `BooleanField` | non | `True` | Masque l'exercice des formulaires si `False` |

**Tri par défaut** : `["nom"]`

**`CategorieExercice` — valeurs TextChoices** :

| Valeur DB | Label affiché |
|-----------|---------------|
| `ADDUCTEURS` | Adducteurs |
| `ABDOS` | Abdos |
| `CARDIO` | Cardio |
| `DOS` | Dos |
| `EPAULE_ARRIERE` | Epaule arriere |
| `FESSIERS` | Fessiers |
| `GAINAGE` | Gainage |
| `ISCHIOS` | Ischios |
| `PECTORAUX` | Pectoraux |
| `QUADRICEPS` | Quadriceps |
| `OTHER` | Autre |

**Relations FK** : suppression bloquée si des `TemplateLigne` ou `SessionLigne` y font référence (`PROTECT`)

---

### 4.2 `SeanceType`

Gabarit de séance (ex. : "Push A", "Pull B"). Contient une liste de `TemplateLigne`.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `nom` | `CharField(120)` | non | — | Nom unique du type |
| `description` | `TextField` | non | `""` | Description libre |
| `created_at` | `DateTimeField` | non | auto | Date de création (auto_now_add) |
| `updated_at` | `DateTimeField` | non | auto | Dernière modification (auto_now) |

**Tri par défaut** : `["nom"]`

**Relations FK** : suppression cascade sur toutes ses `TemplateLigne`. Sur `Seance`, `seance_type` devient NULL (`SET_NULL`).

---

### 4.3 `TemplateLigne`

Une série planifiée dans un gabarit. Chaque ligne = une série d'un exercice dans un `SeanceType`.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `seance_type` | `ForeignKey(SeanceType, CASCADE)` | non | — | Gabarit parent |
| `ordre_exercice` | `PositiveSmallIntegerField` | non | — | Position de l'exercice dans la séance |
| `exercice` | `ForeignKey(Exercice, PROTECT)` | non | — | Exercice concerné |
| `numero_serie` | `PositiveSmallIntegerField` | non | — | Numéro de la série (1, 2, 3…) |
| `repetitions_cible` | `PositiveSmallIntegerField` | oui | — | Répétitions prévues |
| `charge_cible` | `DecimalField(6,2)` | oui | — | Charge prévue (kg) |
| `rpe_cible` | `DecimalField(3,1)` | oui | — | RPE cible (0–10) |
| `repos_secondes` | `PositiveSmallIntegerField` | oui | — | Durée de repos après la série (sec) |
| `tempo` | `CharField(30)` | non | `""` | Indication de tempo (ex. "3-1-2") |

**Tri par défaut** : `["seance_type", "ordre_exercice", "numero_serie"]`

**Contraintes DB** :
- `unique_template_serie_par_ordre` : `(seance_type, ordre_exercice, numero_serie)` unique
- `template_rpe_cible_entre_0_et_10` : `rpe_cible` NULL ou compris entre 0 et 10

**Validation Python (`clean`)** : un même `ordre_exercice` dans un `SeanceType` doit toujours pointer vers le même `exercice`. Lève une `ValidationError` sur le champ `ordre_exercice` en cas de conflit.

---

### 4.4 `Seance`

Une instance de séance (planifiée, en cours ou terminée).

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `seance_type` | `ForeignKey(SeanceType, SET_NULL)` | oui | — | Type de séance (NULL si le type a été supprimé) |
| `date` | `DateField` | non | — | Date planifiée |
| `statut` | `CharField(20)` | non | `PLANIFIEE` | État de la séance (voir section 7) |
| `started_at` | `DateTimeField` | oui | — | Horodatage de démarrage |
| `ended_at` | `DateTimeField` | oui | — | Horodatage de fin |
| `notes` | `TextField` | non | `""` | Notes libres sur la séance |

**Tri par défaut** : `["-date", "-id"]`

**`StatutSeance` — valeurs TextChoices** : `PLANIFIEE`, `IN_PROGRESS`, `COMPLETED`

**Propriétés Python** :
- `is_active` → `True` si `statut == IN_PROGRESS`
- `duration` → `ended_at - started_at` si les deux sont renseignés, sinon `None`

**Relations FK** : suppression cascade sur toutes ses `SessionLigne`.

---

### 4.5 `SessionLigne`

Une série réelle dans une séance. Contient les données cibles (copiées du template) et les données réelles saisies pendant la séance.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `seance` | `ForeignKey(Seance, CASCADE)` | non | — | Séance parente |
| `ordre_prevu` | `PositiveSmallIntegerField` | non | — | Ordre original issu du template **(immuable)** |
| `ordre_reel` | `PositiveSmallIntegerField` | oui | — | Ordre d'affichage actuel (modifiable par réordonnancement) |
| `exercice` | `ForeignKey(Exercice, PROTECT)` | non | — | Exercice |
| `numero_serie` | `PositiveSmallIntegerField` | non | — | Numéro de la série |
| `repetitions_cible` | `PositiveSmallIntegerField` | oui | — | Répétitions prévues |
| `charge_cible` | `DecimalField(6,2)` | oui | — | Charge prévue (kg) |
| `rpe_cible` | `DecimalField(3,1)` | oui | — | RPE cible (0–10) |
| `repos_secondes` | `PositiveSmallIntegerField` | oui | — | Repos après série (sec) |
| `tempo` | `CharField(30)` | non | `""` | Indication de tempo |
| `repetitions_reelles` | `PositiveSmallIntegerField` | oui | — | Répétitions effectuées |
| `charge_reelle` | `DecimalField(6,2)` | oui | — | Charge réelle (kg) |
| `rpe_reel` | `DecimalField(3,1)` | oui | — | RPE réel (0–10) |
| `validee` | `BooleanField` | non | `False` | Série marquée comme complète |
| `completed_at` | `DateTimeField` | oui | — | Horodatage de validation |

**Tri par défaut** : `["seance", "ordre_reel", "ordre_prevu", "numero_serie"]`

**Contraintes DB** :
- `unique_session_serie_par_ordre_prevu` : `(seance, ordre_prevu, numero_serie)` unique
- `session_rpe_cible_entre_0_et_10` : `rpe_cible` NULL ou 0–10
- `session_rpe_reel_entre_0_et_10` : `rpe_reel` NULL ou 0–10

**Validation Python (`clean`)** : même logique que `TemplateLigne` — un `ordre_prevu` dans une `Seance` doit toujours pointer vers le même `exercice`.

**Méthode `save`** : si `ordre_reel` est NULL à la création, initialisé à `ordre_prevu`.

**Propriétés Python** :
- `ordre_affichage` → `ordre_reel` si renseigné, sinon `ordre_prevu`
- `is_completed` → `True` si `validee == True` OU `completed_at` non NULL
- `volume` → `charge_reelle * repetitions_reelles` si les deux sont renseignés, sinon `None`

**Méthode `mark_completed()`** : positionne `validee = True` et `completed_at = timezone.now()` si non déjà renseigné. Source de vérité pour `is_completed` — ne pas modifier ce comportement.

---

### 4.6 `Mensuration`

Relevé de mensurations corporelles à une date donnée. Tous les champs de mesure sont optionnels.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `date` | `DateField` | non | — | Date du relevé |
| `poids` | `DecimalField(5,1)` | oui | — | Poids en kg |
| `tour_poitrine` | `DecimalField(5,1)` | oui | — | Tour de poitrine en cm |
| `tour_taille` | `DecimalField(5,1)` | oui | — | Tour de taille en cm |
| `tour_hanches` | `DecimalField(5,1)` | oui | — | Tour de hanches en cm |
| `tour_bras` | `DecimalField(5,1)` | oui | — | Tour de bras en cm |
| `tour_cuisse` | `DecimalField(5,1)` | oui | — | Tour de cuisse en cm |
| `masse_grasse` | `DecimalField(4,1)` | oui | — | Pourcentage de masse grasse |
| `notes` | `TextField` | non | `""` | Notes libres |
| `created_at` | `DateTimeField` | non | auto | Horodatage de saisie (auto_now_add) |

**Tri par défaut** : `["-date"]`

---

## 5. Fonctionnalités

### 5.1 Dashboard

**URL** : `GET /` → `workouts:dashboard`
**Vue** : `dashboard(request)`
**Template** : `workouts/dashboard.html`

**Règles de gestion** :
- `seances_actives` : toutes les séances `IN_PROGRESS`, avec `select_related("seance_type")`
- `prochaines` : 6 premières séances `PLANIFIEE` triées par `date ASC, id ASC`
- `recentes` : 6 dernières séances `COMPLETED` triées par `date DESC, id DESC`

---

### 5.2 Planifier une séance

**URL** : `GET/POST /seances/planifier/` → `workouts:planifier_seance`
**Vue** : `planifier_seance(request)`
**Template** : `workouts/planifier_seance.html`
**Formulaire** : `SeancePlanificationForm`

**Champs du formulaire** :
- `seance_type` : `ModelChoiceField` sur `SeanceType.objects.all()`
- `date` : `DateField` avec widget `<input type="date">`

**Règles de gestion** :
1. Appel à `create_seance_from_template(seance_type, date)` dans `services.py`
2. Appel à `copy_template_lines_to_seance(seance)` — transaction atomique
3. Copie de toutes les `TemplateLigne` vers des `SessionLigne` (`ordre_prevu = ordre_exercice`, `ordre_reel = ordre_exercice`)
4. Garde-fou : si la séance a déjà des lignes, retourne `[]` sans rien créer (`select_for_update` + `lignes.exists()`)
5. Redirection vers `workouts:seance_detail` + message flash

**Gestion des erreurs** : formulaire invalide → réaffichage avec erreurs.

---

### 5.3 Détail d'une séance

**URL** : `GET /seances/<pk>/` → `workouts:seance_detail`
**Vue** : `seance_detail(request, pk)`
**Template** : `workouts/seance_detail.html` (inclut 3 partials)

**Données transmises** :
- `seance` avec `select_related("seance_type")`
- `groupes` : résultat de `_group_lignes(lignes)` — liste de dicts `{ordre, ordre_source, exercice, lignes}`
- `forms_by_line` : dict `{ligne.pk: SessionLigneQuickForm(instance=ligne)}`
- `notes_form` : `SeanceNotesForm(instance=seance)`
- `add_line_form` : `AddSessionLineForm()`

**Fonction `_group_lignes`** : trie par `(ordre_affichage, ordre_prevu, numero_serie)`, groupe par `(ordre_affichage, ordre_prevu, exercice_id)`.

---

### 5.4 Démarrer une séance

**URL** : `POST /seances/<pk>/demarrer/` → `workouts:demarrer_seance`
**Vue** : `demarrer_seance(request, pk)` — `@require_POST`

**Règles de gestion** (via `start_seance` dans `services.py`) :
1. Si `statut == COMPLETED` : retour sans modification
2. Si `started_at` est NULL : positionné à `timezone.now()`
3. `statut` → `IN_PROGRESS`
4. Sauvegarde via `update_fields=["started_at", "statut"]`

---

### 5.5 Terminer une séance

**URL** : `POST /seances/<pk>/terminer/` → `workouts:terminer_seance`
**Vue** : `terminer_seance(request, pk)` — `@require_POST`

**Règles de gestion** (via `complete_seance` dans `services.py`) :
1. Si `started_at` est NULL : positionné à `timezone.now()`
2. `ended_at` → `timezone.now()`
3. `statut` → `COMPLETED`
4. Sauvegarde via `update_fields=["started_at", "ended_at", "statut"]`

---

### 5.6 Valider une série

**URL** : `POST /lignes/<pk>/` → `workouts:update_ligne`
**Vue** : `update_ligne(request, pk)` — `@require_POST`
**Formulaire** : `SessionLigneQuickForm` (champs : `repetitions_reelles`, `charge_reelle`, `rpe_reel`)

**Comportement selon `Accept`** : `application/json` → JSON ; sinon → redirect + flash.

**Règles de gestion** :
1. Si `ligne.is_completed` → HTTP 409 `{"ok": false}`
2. Formulaire valide → `form.save(commit=False)`, appel `ligne.mark_completed()`, `ligne.save()`
3. Réponse JSON : `{"ok": true, "completed": true, "volume": "...", "completed_at": "HH:MM", "rest_seconds": N, "exercise_name": "...", "serie_label": "SN"}`
4. Formulaire invalide → HTTP 400 `{"ok": false, "errors": form.errors}`

**Gestion des erreurs** : si déjà validée → HTTP 409. Pré-remplissage : valeurs cibles utilisées comme `initial` si champs réels NULL.

---

### 5.7 Réordonner un exercice

**URL** : `POST /seances/<pk>/ordre/<ordre_prevu>/` → `workouts:update_ordre_exercice`
**Vue** : `update_ordre_exercice(request, pk, ordre_prevu)` — `@require_POST`

**Règles de gestion** (via `update_exercise_order`, transaction atomique + `select_for_update`) :
1. Validation de `ordre` : entier >= 1 sinon erreur
2. Construction des groupes triés par `(ordre_courant, ordre_prevu)`
3. Extraction du groupe à déplacer, insertion à la position cible (0-indexé, clamped)
4. Mise à jour de `ordre_reel` pour tous les groupes via `bulk update`
5. Réponse : `{"ok": true, "updated_count": N, "ordre": N}`

---

### 5.8 Ajouter une série hors-template

**URL** : `POST /seances/<pk>/ajouter-ligne/` → `workouts:ajouter_ligne`
**Vue** : `ajouter_ligne(request, pk)` — `@require_POST`
**Formulaire** : `AddSessionLineForm`

**Règles de gestion** (via `add_unplanned_session_line`, transaction atomique) :
1. Si l'exercice existe déjà → réutilise son `ordre_prevu`
2. Sinon → `ordre_prevu = max(ordre_prevu) + 1`
3. `numero_serie = max(numero_serie pour cet ordre) + 1`
4. Création avec `ordre_reel = ordre_prevu`

---

### 5.9 Enregistrer les notes

**URL** : `POST /seances/<pk>/notes/` → `workouts:update_notes`
**Vue** : `update_notes(request, pk)` — `@require_POST`
**Formulaire** : `SeanceNotesForm` — champ `notes`, widget `Textarea(rows=3)`

---

### 5.10 Historique des séances

**URL** : `GET /historique/` → `workouts:historique`
**Vue** : `historique(request)`
**Template** : `workouts/historique.html`

Affiche toutes les séances `COMPLETED` triées par `(-date, -id)` avec `select_related` et `prefetch_related("lignes")`. Bouton "Export CSV" → `workouts:export_csv`.

---

### 5.11 Export CSV brut

**URL** : `GET /historique/export.csv` → `workouts:export_csv`
Toutes les séances (tous statuts) avec leurs `SessionLigne`. Séparateur virgule, UTF-8 sans BOM. Colonnes : `date`, `seance`, `statut`, `ordre_prevu`, `ordre_reel`, `exercice`, `numero_serie`, `repetitions_cible`, `charge_cible`, `rpe_cible`, `repetitions_reelles`, `charge_reelle`, `rpe_reel`, `validee`, `completed_at`.

---

### 5.12 Mensurations — liste

**URL** : `GET /mensurations/` → `workouts:mensurations`
**Vue** : `mensurations(request)`

`_build_mensuration_rows` : calcule le delta par rapport à l'entrée précédente. Deltas positifs en vert (`+`), négatifs en rouge, nuls non affichés. Champs NULL non affichés dans la carte.

---

### 5.13 Mensurations — ajout

**URL** : `GET/POST /mensurations/ajouter/` → `workouts:ajouter_mensuration`
**Formulaire** : `MensurationForm` — GET avec `initial={"date": date.today()}`. Affiche `body_guide.svg` en regard.

---

### 5.14 Mensurations — modification

**URL** : `GET/POST /mensurations/<pk>/modifier/` → `workouts:modifier_mensuration`
**Formulaire** : `MensurationForm(instance=mensuration)` — même template que l'ajout.

---

### 5.15 Backup & Restore

**URL page** : `GET /backup/` → `workouts:backup_page`

**Export ZIP** (`GET /backup/export/`) : ZIP en mémoire (`io.BytesIO`) contenant 6 fichiers JSON — `exercices.json`, `seance_types.json`, `mensurations.json`, `template_lignes.json`, `seances.json`, `session_lignes.json`. Sérialisation Django native, compression `ZIP_DEFLATED`.

**Import** (`POST /backup/import/`) : transaction atomique. Suppression dans l'ordre inverse des FK, réimport dans l'ordre des FK, puis resynchronisation des séquences PostgreSQL via `sqlsequencereset` (évite les `IntegrityError` sur les IDs après import de données prod). Rollback complet si exception. Confirmation via `<dialog>` HTML natif côté client avant soumission.

**Export CSV lisible** (`GET /backup/export-sessions.csv`) : séances `COMPLETED` uniquement, séparateur `;`, UTF-8 avec BOM pour Excel.

---

### 5.16 Interface Admin Django

| Modèle | Particularités |
|--------|----------------|
| `Exercice` | Filtres: categorie, actif ; recherche: nom, description |
| `SeanceType` | Inline `TemplateLigneInline` (TabularInline, extra=1, autocomplete exercice) |
| `Seance` | Inline `SessionLigneInline` (extra=0, readonly validee/completed_at) ; `save_related` appelle `copy_template_lines_to_seance` à la création uniquement |
| `TemplateLigne` | Autocomplete seance_type et exercice |
| `Mensuration` | Filtre et tri par date |
| `SessionLigne` | Filtres: seance__statut, exercice ; autocomplete seance et exercice |

---

## 6. Comportements JavaScript

Le fichier `seance_detail.js` est chargé avec `defer` uniquement sur `seance_detail.html`. Template tag `{% load workout_extras %}` requis dans `_workout_list.html` pour le filtre `|get_item:ligne.pk`.

### 6.1 Validation AJAX des séries

**Sélecteur** : `[data-line-form]`

Comportement à la soumission :
1. `event.preventDefault()` + désactivation du bouton
2. Fetch `POST` avec `FormData` et header `Accept: application/json`
3. Si `data.ok` : classe `done`, affichage `"Validee HH:MM"`, inputs `locked`, appel `startRestTimer`
4. Si erreur : classe `error`, ré-activation du bouton

### 6.2 Timer de repos

**Fonction** : `startRestTimer(seconds, label, exerciseBlock, afterElement)`

Comportement :
1. Nettoyage du timer précédent (clearInterval, suppression DOM, removeEventListener)
2. Si `seconds == 0` : appel `moveExerciseToBottomWhenComplete` et retour
3. Clone du `<template id="rest-timer-template">`
4. Temps de fin absolu : `endTime = Date.now() + seconds * 1000`
5. `setInterval(tick, 1000)` — recalcule `remaining = Math.ceil((endTime - Date.now()) / 1000)`
6. À 0 : arrêt, classe `finished`, appel `moveExerciseToBottomWhenComplete`
7. Resync sur `visibilitychange` : `tick()` immédiat au retour de l'onglet

### 6.3 Déplacement automatique des exercices complétés

**Fonction** : `moveExerciseToBottomWhenComplete(exerciseBlock)`

Exercice complet si **toutes** ses lignes `[data-line-form]` ont la classe `done`. Si complet : `workoutList.appendChild(exerciseBlock)`. Appelé à la fin du timer, si `seconds == 0`, et au chargement de la page.

### 6.4 Réordonnancement des exercices

**Sélecteur** : `[data-order-form]` — événement `change` sur `<input type="number" name="ordre">`. Soumission via `form.requestSubmit()`. Garde `submitted = true` pour éviter la double soumission.

---

## 7. États du système

### États d'une `Seance`

```
PLANIFIEE ──[demarrer_seance]──► IN_PROGRESS ──[terminer_seance]──► COMPLETED
```

| Transition | Vue | Service | Conditions |
|------------|-----|---------|------------|
| `PLANIFIEE` → `IN_PROGRESS` | `demarrer_seance` | `start_seance` | Aucune |
| `IN_PROGRESS` → `COMPLETED` | `terminer_seance` | `complete_seance` | Aucune |
| `PLANIFIEE` → `COMPLETED` | — | `complete_seance` | Possible si appelé directement |
| `COMPLETED` → tout | Bloqué | `start_seance` retourne sans modifier | — |

Les boutons "Début séance" et "Fin séance" s'affichent tant que `statut != COMPLETED`.

### États d'une `SessionLigne`

| État | Condition |
|------|-----------|
| Non validée | `validee == False` et `completed_at == None` |
| Validée | `validee == True` OU `completed_at` non NULL |

Une ligne validée ne peut pas être re-validée : `update_ligne` retourne HTTP 409 si `ligne.is_completed`.

---

## 8. Historique des migrations

| Migration | Date | Description |
|-----------|------|-------------|
| `0001_initial` | 2026-04-15 | Schéma initial : `Exercice`, `SeanceType`, `TemplateLigne`, `Seance`, `SessionLigne` |
| `0002_sessionligne_validee` | 2026-04-16 | Ajout `SessionLigne.validee` (BooleanField, défaut False) |
| `0003_alter_exercice_categorie` | 2026-04-20 | Remplacement catégories PUSH/PULL/LEGS/CORE/FULL_BODY par catégories musculaires détaillées |
| `0004_backfill_ordre_reel` | — | Backfill `SessionLigne.ordre_reel = ordre_prevu` pour les lignes NULL |
| `0005_backfill_ordre_reel_explicit` | — | Deuxième passe de backfill (noop en rollback) |
| `0006_mensuration` | 2026-04-23 | Ajout du modèle `Mensuration` |
