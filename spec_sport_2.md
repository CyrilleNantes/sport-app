# Spécifications Fonctionnelles & Techniques — Sport App

---

## 0. Règles de rédaction pour l'IA

- Ce document décrit l'état **réel** du code au moment de sa rédaction (23 avril 2026). Ne pas inventer de fonctionnalité absente du code.
- Les noms de champs, modèles, vues, URLs et fonctions restent en anglais (tels qu'ils apparaissent dans le code).
- Toute modification du code doit être répercutée ici avant d'être implémentée.
- Ne pas créer de nouveaux modèles, vues ou URLs sans mise à jour préalable de cette spec.
- Respecter les conventions existantes : nommage snake_case, décorateur `@require_POST` sur les vues d'action, transactions atomiques sur les opérations multi-tables, logique métier dans `services.py` (pas dans les vues).

---

## 1. Contexte, Objectifs et Limites

### 1.1 Objectif principal

Application web Django de suivi d'entraînement de musculation pour un utilisateur solo. Elle permet de planifier des séances à partir de gabarits (templates), de les dérouler en temps réel avec validation série par série et timer de repos, puis de consulter l'historique et de suivre les mensurations corporelles.

### 1.2 Périmètre inclus

- Gestion des types de séance (gabarits d'exercices et de séries)
- Planification d'une séance à partir d'un gabarit
- Déroulement en temps réel : démarrage, validation AJAX des séries, timer de repos, réordonnancement des exercices, ajout de séries hors-template
- Historique des séances terminées avec export CSV
- Suivi des mensurations corporelles (poids, tours de corps, masse grasse)
- Backup & restore complet (export zip JSON + import destructif atomique)
- Export CSV lisible des séances terminées (compatible Excel)
- Interface d'administration Django complète

### 1.3 Hors périmètre

- Authentification multi-utilisateurs (aucun système de compte utilisateur — accès direct à l'app)
- Notifications push / rappels programmés
- Graphiques et visualisations de progression (hors deltas dans les mensurations)
- API REST exposée publiquement (DRF présent dans requirements.txt mais non utilisé dans le code actuel)
- Application mobile native

---

## 2. Acteurs et Rôles

| Acteur | Description |
|--------|-------------|
| Utilisateur unique | Accès complet à toutes les fonctionnalités sans authentification |
| Administrateur Django | Accès à `/admin/` pour gérer exercices, types de séance, séances et mensurations |

L'application n'implémente aucune restriction d'accès par rôle ou session utilisateur. Toutes les URLs sont publiques.

---

## 3. Stack Technique & Déploiement

### 3.1 Stack

| Composant | Version / Détail |
|-----------|-----------------|
| Python | >= 3.x (non précisé dans requirements) |
| Django | 6.0.4 |
| Base de données (prod) | PostgreSQL via `psycopg2-binary` |
| Base de données (dev local) | SQLite (`db.sqlite3` par défaut si `DATABASE_URL` absent) |
| Serveur WSGI | Gunicorn |
| Fichiers statiques | WhiteNoise 6.12.0 (`CompressedManifestStaticFilesStorage`) |
| ORM URL BDD | `dj-database-url` 3.1.2 |
| Variables d'env | `python-dotenv` 1.2.2 (fichier `.env` à la racine) |

Dépendances présentes dans `requirements.txt` mais **non utilisées** dans le code applicatif actuel : `djangorestframework`, `pandas`, `openpyxl`, `numpy`.

### 3.2 Architecture

```
config/
  settings.py       — configuration unique (dev/prod pilotée par variables d'env)
  urls.py           — montage : "" → workouts.urls, "admin/" → admin
  wsgi.py
workouts/
  models.py         — 6 modèles : Exercice, SeanceType, TemplateLigne, Seance, SessionLigne, Mensuration
  views.py          — 18 vues fonctions
  urls.py           — 20 routes (namespace "workouts")
  forms.py          — 5 formulaires
  services.py       — 5 fonctions métier
  admin.py          — 6 ModelAdmin
  context_processors.py — injecte ENVIRONMENT et IS_DEV dans tous les templates
  templatetags/
    workout_extras.py   — filtre get_item (accès dict dans les templates)
  templates/workouts/
    base.html
    dashboard.html
    planifier_seance.html
    seance_detail.html  — inclut 3 partials
    partials/
      _session_header.html
      _workout_list.html    — contient le <template> HTML du timer de repos
      _session_panels.html
    historique.html
    mensurations.html
    mensuration_form.html
    backup.html
  static/workouts/
    styles.css
    seance_detail.js
    body_guide.svg
  migrations/
    0001_initial.py
    0002_sessionligne_validee.py
    0003_alter_exercice_categorie.py
    0004_backfill_ordre_reel.py
    0005_backfill_ordre_reel_explicit.py
    0006_mensuration.py
```

### 3.3 Environnements (dev / prod)

| Variable d'env | Valeur dev | Valeur prod |
|----------------|-----------|-------------|
| `SECRET_KEY` | valeur dans `.env` | valeur dans Railway |
| `DEBUG` | `"True"` | `"False"` (défaut) |
| `ENVIRONMENT` | `"dev"` | absent → `"production"` (défaut) |
| `DATABASE_URL` | absent → SQLite | URL PostgreSQL Railway |
| `RAILWAY_PUBLIC_DOMAIN` | absent | domaine Railway |

Deux projets Railway séparés :
- **Prod** : branche `main`, domaine `sport-app-production-8be3.up.railway.app`
- **Dev** : branche `dev`, domaine `sport-app-production-ce7c.up.railway.app`, variable `ENVIRONMENT=dev`

Le context processor `environment` injecte `IS_DEV` dans tous les templates. Quand `IS_DEV` est `True`, une bannière jaune `⚠ DEV — base de données de test, pas la prod` s'affiche en haut de toutes les pages.

### 3.4 Contraintes techniques

- **Déploiement Railway** : `railway.json` configure le build (NIXPACKS + `collectstatic`) et le démarrage (`collectstatic --noinput && migrate && gunicorn`).
- **Fichiers statiques** : WhiteNoise sert les fichiers statiques directement depuis Gunicorn (pas de Nginx). `WHITENOISE_KEEP_ONLY_HASHED_FILES = False` conserve les fichiers non-hashés.
- **HTTPS** : `SECURE_PROXY_SSL_HEADER` configuré pour Railway (proxy HTTPS). Cookies CSRF et session marqués `Secure` hors DEBUG.
- **CSRF** : `CSRF_TRUSTED_ORIGINS` généré dynamiquement depuis `ALLOWED_HOSTS` (en excluant localhost/127.0.0.1).
- **Timezone** : `Europe/Paris`, `USE_TZ = True`. Tous les `DateTimeField` sont en UTC en base, rendus en heure locale via Django.
- **Langue** : `LANGUAGE_CODE = "fr"`, interface admin en français.
- **Logging** : logger `workouts` vers console. Niveau `DEBUG` si `DEBUG=True`, sinon `INFO`.

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

**`CategorieExercice` — valeurs TextChoices** (migration 0003, remplace PUSH/PULL/LEGS/CORE/FULL_BODY) :

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
| `statut` | `CharField(20)` | non | `PLANIFIEE` | État de la séance (voir StatutSeance) |
| `started_at` | `DateTimeField` | oui | — | Horodatage de démarrage |
| `ended_at` | `DateTimeField` | oui | — | Horodatage de fin |
| `notes` | `TextField` | non | `""` | Notes libres sur la séance |

**Tri par défaut** : `["-date", "-id"]`

**`StatutSeance` — valeurs TextChoices** :

| Valeur DB | Label affiché |
|-----------|---------------|
| `PLANIFIEE` | Planifiee |
| `IN_PROGRESS` | En cours |
| `COMPLETED` | Terminee |

**Propriétés Python** :
- `is_active` → `True` si `statut == IN_PROGRESS`
- `duration` → `ended_at - started_at` si les deux sont renseignés, sinon `None`
- `__str__` → `"<nom_type> - <date d/m/Y>"` ou `"Seance libre - <date>"` si `seance_type` est NULL

---

### 4.5 `SessionLigne`

Une série réelle dans une séance. Contient les données cibles (copiées du template) et les données réelles saisies pendant la séance.

| Champ | Type Django | Nullable | Défaut | Description |
|-------|-------------|----------|--------|-------------|
| `id` | `BigAutoField` | non | auto | Clé primaire |
| `seance` | `ForeignKey(Seance, CASCADE)` | non | — | Séance parente |
| `ordre_prevu` | `PositiveSmallIntegerField` | non | — | Ordre original issu du template (immuable) |
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

**Méthode `save`** : si `ordre_reel` est NULL à la création, il est automatiquement initialisé à `ordre_prevu`. Si `update_fields` est fourni, `ordre_reel` y est ajouté.

**Propriétés Python** :
- `ordre_affichage` → `ordre_reel` si renseigné, sinon `ordre_prevu`
- `is_completed` → `True` si `validee == True` OU `completed_at` non NULL
- `volume` → `charge_reelle * repetitions_reelles` si les deux sont renseignés, sinon `None`

**Méthode `mark_completed()`** : positionne `validee = True` et renseigne `completed_at = timezone.now()` si non déjà renseigné.

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

**Données transmises au template** :
- `seances_actives` : toutes les séances avec `statut=IN_PROGRESS`, triées par défaut, avec `select_related("seance_type")`
- `prochaines` : 6 premières séances `PLANIFIEE` triées par `date ASC, id ASC`
- `recentes` : 6 dernières séances `COMPLETED` triées par `date DESC, id DESC`

**Affichage** :
- Section "En cours" : liste avec lien vers le détail et label du statut
- Section "Planifiées" : liste avec lien vers le détail et date au format `d/m`
- Section "Dernières séances" : liste avec lien vers le détail et durée (ou `-` si non calculable)
- Bouton "Planifier une séance" → `workouts:planifier_seance`

---

### 5.2 Planifier une séance

**URL** : `GET/POST /seances/planifier/` → `workouts:planifier_seance`  
**Vue** : `planifier_seance(request)`  
**Template** : `workouts/planifier_seance.html`  
**Formulaire** : `SeancePlanificationForm`

**Champs du formulaire** :
- `seance_type` : `ModelChoiceField` sur `SeanceType.objects.all()`
- `date` : `DateField` avec widget `<input type="date">`

**Règles de gestion (POST valide)** :
1. Appel à `create_seance_from_template(seance_type, date)` dans `services.py`
2. Création de la `Seance` en base
3. Appel à `copy_template_lines_to_seance(seance)` (transaction atomique)
4. Copie de toutes les `TemplateLigne` du `SeanceType` vers des `SessionLigne` (`ordre_prevu = ordre_exercice`, `ordre_reel = ordre_exercice`)
5. Garde-fou : si la séance a déjà des lignes (appel en double), `copy_template_lines_to_seance` retourne `[]` sans rien créer (`select_for_update` + vérification `lignes.exists()`)
6. Redirection vers `workouts:seance_detail` avec la pk de la nouvelle séance
7. Message flash `"Seance planifiee."`

**Erreur** : formulaire invalide → affichage du formulaire avec erreurs.

---

### 5.3 Détail d'une séance

**URL** : `GET /seances/<pk>/` → `workouts:seance_detail`  
**Vue** : `seance_detail(request, pk)`  
**Template** : `workouts/seance_detail.html` (inclut 3 partials)

**Données transmises** :
- `seance` : avec `select_related("seance_type")`
- `groupes` : résultat de `_group_lignes(lignes)` — liste de dicts `{ordre, ordre_source, exercice, lignes}`
- `forms_by_line` : dict `{ligne.pk: SessionLigneQuickForm(instance=ligne)}` pour chaque ligne
- `notes_form` : `SeanceNotesForm(instance=seance)`
- `add_line_form` : `AddSessionLineForm()`

**Fonction `_group_lignes(lignes)`** :
- Trie les lignes par `(ordre_affichage, ordre_prevu, numero_serie)`
- Groupe par `(ordre_affichage, ordre_prevu, exercice_id)` via `itertools.groupby`
- Retourne une liste de dicts avec `ordre` (=`ordre_affichage`), `ordre_source` (=`ordre_prevu` de la 1re ligne), `exercice`, `lignes`

**Partial `_session_header.html`** :
- Affiche statut, titre, horaires de début/fin, durée
- Si `statut != COMPLETED` : boutons "Début séance" (POST `demarrer_seance`) et "Fin séance" (POST `terminer_seance`)

**Partial `_workout_list.html`** :
- Contient le `<template id="rest-timer-template">` pour le timer de repos (cloné par JS)
- Liste des blocs d'exercice `[data-exercise-block]`
- Pour chaque exercice : formulaire de réordonnancement `[data-order-form]` + `numero_serie`
- Pour chaque série : formulaire de validation `[data-line-form]` avec champs `repetitions_reelles`, `charge_reelle`, `rpe_reel` + métadonnées cibles + bouton OK/Validée

**Partial `_session_panels.html`** :
- Formulaire "Ajouter une série" (`AddSessionLineForm`)
- Formulaire "Notes" (`SeanceNotesForm`)

---

### 5.4 Démarrer une séance

**URL** : `POST /seances/<pk>/demarrer/` → `workouts:demarrer_seance`  
**Vue** : `demarrer_seance(request, pk)`  
**Décorateur** : `@require_POST`

**Règles de gestion** :
1. Appel à `start_seance(seance)` dans `services.py`
2. Si `statut == COMPLETED` : retour sans modification
3. Si `started_at` est NULL : positionné à `timezone.now()`
4. `statut` → `IN_PROGRESS`
5. Sauvegarde via `update_fields=["started_at", "statut"]`
6. Redirection vers `workouts:seance_detail`
7. Message flash `"Seance demarree."`

---

### 5.5 Terminer une séance

**URL** : `POST /seances/<pk>/terminer/` → `workouts:terminer_seance`  
**Vue** : `terminer_seance(request, pk)`  
**Décorateur** : `@require_POST`

**Règles de gestion** :
1. Appel à `complete_seance(seance)` dans `services.py`
2. Si `started_at` est NULL : positionné à `timezone.now()`
3. `ended_at` → `timezone.now()`
4. `statut` → `COMPLETED`
5. Sauvegarde via `update_fields=["started_at", "ended_at", "statut"]`
6. Redirection vers `workouts:seance_detail`
7. Message flash `"Seance terminee."`

---

### 5.6 Valider une série (update_ligne)

**URL** : `POST /lignes/<pk>/` → `workouts:update_ligne`  
**Vue** : `update_ligne(request, pk)`  
**Décorateur** : `@require_POST`  
**Formulaire** : `SessionLigneQuickForm`

**Comportement selon l'en-tête `Accept`** :
- Si `Accept: application/json` → réponse JSON (utilisé par le JS)
- Sinon → redirect + message flash

**Règles de gestion** :

1. **Déjà validée** : si `ligne.is_completed`, retour `{"ok": False, "errors": {"__all__": [...]}}` HTTP 409 (JSON) ou message d'erreur + redirect.
2. **Formulaire valide** :
   - `form.save(commit=False)` → ligne avec données réelles
   - Appel à `ligne.mark_completed()` → `validee=True`, `completed_at=now()` si non renseigné
   - `ligne.save()`
   - Réponse JSON `{"ok": True, "completed": True, "volume": "...", "completed_at": "HH:MM", "rest_seconds": N, "exercise_name": "...", "serie_label": "SN"}`
3. **Formulaire invalide** : `{"ok": False, "errors": form.errors}` HTTP 400 (JSON) ou message d'erreur + redirect.

**`SessionLigneQuickForm`** :
- Champs : `repetitions_reelles`, `charge_reelle`, `rpe_reel`
- Widgets : `NumberInput` avec `inputmode` approprié, pas de `min` sur `repetitions_reelles`, `step=0.5` sur `charge_reelle` et `rpe_reel`
- Pré-remplissage : si les champs réels sont NULL, les valeurs cibles sont utilisées comme `initial`
- Désactivation : si `ligne.is_completed`, tous les champs sont `disabled`

---

### 5.7 Réordonner un exercice

**URL** : `POST /seances/<pk>/ordre/<ordre_prevu>/` → `workouts:update_ordre_exercice`  
**Vue** : `update_ordre_exercice(request, pk, ordre_prevu)`  
**Décorateur** : `@require_POST`

**Paramètre POST** : `ordre` (entier >= 1)

**Règles de gestion** :
1. Validation de `ordre` : si invalide ou < 1 → erreur (JSON 400 ou message + redirect)
2. Appel à `update_exercise_order(seance, ordre_prevu, ordre_reel)` (transaction atomique + `select_for_update`)
3. Construction des groupes d'exercices triés par `(ordre_courant, ordre_prevu)`
4. Extraction du groupe à déplacer (`ordre_prevu` correspondant)
5. Insertion à la position `ordre_reel - 1` (0-indexé, clamped entre 0 et len-1)
6. Mise à jour de `ordre_reel` pour tous les groupes (index 1-basé) via `bulk update`
7. Retourne `(updated_count, final_order)` → JSON `{"ok": True, "updated_count": N, "ordre": N}` ou redirect

---

### 5.8 Ajouter une série hors-template

**URL** : `POST /seances/<pk>/ajouter-ligne/` → `workouts:ajouter_ligne`  
**Vue** : `ajouter_ligne(request, pk)`  
**Décorateur** : `@require_POST`  
**Formulaire** : `AddSessionLineForm`

**Champs du formulaire** :
- `exercice` : `ModelChoiceField` filtré sur `actif=True`
- `repetitions_cible`, `charge_cible`, `rpe_cible`, `repos_secondes`, `tempo` : optionnels

**Règles de gestion (via `add_unplanned_session_line`, transaction atomique)** :
1. Si l'exercice existe déjà dans la séance → réutilise son `ordre_prevu`
2. Sinon → `ordre_prevu = max(ordre_prevu) + 1`
3. `numero_serie = max(numero_serie pour cet ordre) + 1`
4. Création de la `SessionLigne` avec `ordre_reel = ordre_prevu`
5. Redirection vers `workouts:seance_detail` + message flash `"Serie ajoutee."`

---

### 5.9 Enregistrer les notes d'une séance

**URL** : `POST /seances/<pk>/notes/` → `workouts:update_notes`  
**Vue** : `update_notes(request, pk)`  
**Décorateur** : `@require_POST`  
**Formulaire** : `SeanceNotesForm` — champ `notes`, widget `Textarea(rows=3)`

Sauvegarde via `form.save()` puis redirect + message flash.

---

### 5.10 Historique des séances

**URL** : `GET /historique/` → `workouts:historique`  
**Vue** : `historique(request)`  
**Template** : `workouts/historique.html`

Affiche toutes les séances `COMPLETED` par ordre `(-date, -id)` avec `select_related("seance_type")` et `prefetch_related("lignes")`. Pour chaque séance : nom, nombre de séries (`lignes.count`), durée.

Bouton "Export CSV" → `workouts:export_csv`

---

### 5.11 Export CSV (historique brut)

**URL** : `GET /historique/export.csv` → `workouts:export_csv`  
**Vue** : `export_csv(request)`  
**Content-Type** : `text/csv`  
**Nom de fichier** : `sport-app-export.csv`  
**Séparateur** : virgule  
**Encodage** : UTF-8 (sans BOM)

Exporte **toutes les séances** (tous statuts) avec leurs `SessionLigne`. Colonnes :

`date`, `seance`, `statut`, `ordre_prevu`, `ordre_reel`, `exercice`, `numero_serie`, `repetitions_cible`, `charge_cible`, `rpe_cible`, `repetitions_reelles`, `charge_reelle`, `rpe_reel`, `validee`, `completed_at`

Tri : `seance__date ASC, seance_id ASC, ordre_prevu ASC, numero_serie ASC`

---

### 5.12 Mensurations — liste

**URL** : `GET /mensurations/` → `workouts:mensurations`  
**Vue** : `mensurations(request)`  
**Template** : `workouts/mensurations.html`

**Traitement** :
- Toutes les `Mensuration` triées par `(-date)` (tri par défaut du modèle)
- Appel à `_build_mensuration_rows(entries)` : pour chaque entrée, calcul du delta par rapport à l'entrée suivante dans la liste (= la précédente chronologiquement)
- Champs affichés dans l'ordre : poids (kg), tour_poitrine (cm), tour_taille (cm), tour_hanches (cm), tour_bras (cm), tour_cuisse (cm), masse_grasse (%)
- Les champs NULL ne sont pas affichés dans la carte
- Les deltas positifs s'affichent en vert avec `+`, négatifs en rouge sans préfixe, delta nul n'est pas affiché

Bouton "Nouvelle saisie" → `workouts:ajouter_mensuration`  
Bouton "Modifier" sur chaque carte → `workouts:modifier_mensuration`

---

### 5.13 Mensurations — ajout

**URL** : `GET/POST /mensurations/ajouter/` → `workouts:ajouter_mensuration`  
**Vue** : `ajouter_mensuration(request)`  
**Template** : `workouts/mensuration_form.html`  
**Formulaire** : `MensurationForm`

- GET : `initial={"date": date.today()}`
- POST valide : `form.save()`, redirect vers `workouts:mensurations` + message flash
- Le template affiche en regard un guide visuel SVG (`body_guide.svg`)

---

### 5.14 Mensurations — modification

**URL** : `GET/POST /mensurations/<pk>/modifier/` → `workouts:modifier_mensuration`  
**Vue** : `modifier_mensuration(request, pk)`  
**Template** : `workouts/mensuration_form.html` (même que l'ajout, titre "Modifier")  
**Formulaire** : `MensurationForm(instance=mensuration)`

Comportement identique à l'ajout mais sur une instance existante.

---

### 5.15 Backup & Restore

**URL page** : `GET /backup/` → `workouts:backup_page`  
**Template** : `workouts/backup.html`

La page propose trois actions :

#### Export backup (ZIP JSON)

**URL** : `GET /backup/export/` → `workouts:export_backup`  
**Content-Type** : `application/zip`  
**Nom de fichier** : `sport_backup_<YYYY-MM-DD>.zip`

Crée un ZIP en mémoire (`io.BytesIO`) contenant 6 fichiers JSON :

| Fichier dans le ZIP | Modèle |
|---------------------|--------|
| `exercices.json` | `Exercice` |
| `seance_types.json` | `SeanceType` |
| `mensurations.json` | `Mensuration` |
| `template_lignes.json` | `TemplateLigne` |
| `seances.json` | `Seance` |
| `session_lignes.json` | `SessionLigne` |

Sérialisation via `django.core.serializers` (format JSON natif Django, avec PKs). Compression `ZIP_DEFLATED`.

#### Import backup (restauration)

**URL** : `POST /backup/import/` → `workouts:import_backup`  
**Décorateur** : `@require_POST`  
**Paramètre** : fichier `backup_file` (multipart)

**Règles de gestion** :
1. Vérification de la présence du fichier ; si absent → message d'erreur + redirect
2. Vérification que c'est un ZIP valide ; si non → message d'erreur + redirect
3. **Transaction atomique** (`transaction.atomic`) :
   a. Suppression de toutes les données dans l'**ordre inverse** des FK : `SessionLigne` → `Seance` → `TemplateLigne` → `Mensuration` → `SeanceType` → `Exercice`
   b. Réimport dans l'**ordre des FK** : `Exercice` → `SeanceType` → `Mensuration` → `TemplateLigne` → `Seance` → `SessionLigne`
   c. Les fichiers manquants dans le ZIP sont ignorés (warning en log)
4. Si une exception se produit → rollback complet, message d'erreur avec le détail de l'exception
5. Succès → message flash `"Import réussi — toutes les données ont été restaurées."`

**Confirmation côté client** : un `<dialog>` HTML natif demande une confirmation avant la soumission du formulaire (JavaScript inline dans `backup.html`). Le bouton "Restaurer" ouvre la dialog ; "Oui, restaurer" soumet le formulaire ; "Annuler" ferme la dialog sans action.

#### Export sessions CSV (lisible)

**URL** : `GET /backup/export-sessions.csv` → `workouts:export_sessions_csv`  
**Content-Type** : `text/csv; charset=utf-8-sig`  
**Nom de fichier** : `sessions_<YYYY-MM-DD>.csv`  
**Séparateur** : `;`  
**Encodage** : UTF-8 avec BOM (`\ufeff`) pour compatibilité Excel

Exporte uniquement les séances `COMPLETED`. Colonnes : `Date`, `Type`, `Ordre`, `Exercice`, `Série`, `Répétitions cibles`, `Charge cible (kg)`, `Repos (sec)`, `RPE Cible`, `Tempo`, `Charge réelle (kg)`, `Reps réelles`, `RPE réel (0-10)`.

Tri : `seance__date ASC, seance_id ASC, ordre_prevu ASC, numero_serie ASC`.

---

### 5.16 Interface Admin Django

**URL** : `/admin/`

| Modèle | ModelAdmin | Particularités |
|--------|------------|----------------|
| `Exercice` | `ExerciceAdmin` | `list_display`: nom, categorie, actif ; filtres: categorie, actif ; recherche: nom, description |
| `SeanceType` | `SeanceTypeAdmin` | `list_display`: nom, updated_at ; recherche: nom, description ; inline `TemplateLigneInline` (TabularInline, extra=1, autocomplete exercice) |
| `Seance` | `SeanceAdmin` | `list_display`: date, seance_type, statut, started_at, ended_at ; filtres: statut, date, seance_type ; recherche: notes ; inline `SessionLigneInline` (extra=0, autocomplete exercice, readonly validee/completed_at) ; **`save_related`** : appelle `copy_template_lines_to_seance(form.instance)` lors de la **création** uniquement (`not change`) |
| `TemplateLigne` | `TemplateLigneAdmin` | `list_display`: seance_type, ordre_exercice, exercice, numero_serie, repetitions_cible, charge_cible, rpe_cible ; filtres: seance_type, exercice ; autocomplete seance_type et exercice |
| `Mensuration` | `MensurationAdmin` | `list_display`: date, poids, tour_taille, tour_poitrine, tour_bras, masse_grasse ; filtre: date ; tri: `-date` |
| `SessionLigne` | `SessionLigneAdmin` | `list_display`: seance, ordre_prevu, ordre_reel, exercice, numero_serie, repetitions_reelles, charge_reelle, rpe_reel, validee, completed_at ; filtres: seance__statut, exercice ; autocomplete seance et exercice |

---

## 6. États du système

### États d'une `Seance`

```
PLANIFIEE ──[demarrer_seance]──► IN_PROGRESS ──[terminer_seance]──► COMPLETED
    │                                                                      │
    └──[terminer_seance directement possible via start_seance si needed]──┘
```

| Transition | Vue | Service | Conditions |
|------------|-----|---------|------------|
| `PLANIFIEE` → `IN_PROGRESS` | `demarrer_seance` | `start_seance` | Aucune |
| `IN_PROGRESS` → `COMPLETED` | `terminer_seance` | `complete_seance` | Aucune |
| `PLANIFIEE` → `COMPLETED` | — | `complete_seance` | Possible si appelé directement (le service ne vérifie pas le statut courant avant de passer à COMPLETED) |
| `COMPLETED` → tout | Bloqué | `start_seance` retourne sans modifier si `statut == COMPLETED` | |

Les boutons "Début séance" et "Fin séance" s'affichent dans le template tant que `statut != COMPLETED`.

### États d'une `SessionLigne`

| État | Condition |
|------|-----------|
| Non validée | `validee == False` et `completed_at == None` |
| Validée | `validee == True` OU `completed_at` non NULL (propriété `is_completed`) |

Une ligne validée ne peut pas être re-validée : la vue `update_ligne` retourne HTTP 409 si `ligne.is_completed`.

---

## 7. Comportements JavaScript

Le fichier `seance_detail.js` est chargé avec `defer` uniquement sur la page `seance_detail.html`.

### 7.1 Validation AJAX des séries

**Sélecteur** : `[data-line-form]` (formulaires de séries dans `_workout_list.html`)

Comportement à la soumission (`submit`) :
1. `event.preventDefault()` — empêche la soumission standard
2. Désactivation du bouton "OK"
3. Fetch `POST` vers `form.action` avec `FormData` et header `Accept: application/json`
4. Si `response.ok` et `data.ok` :
   - Ajout de la classe `done` sur le formulaire
   - Affichage `"Validee HH:MM"` dans `.line-status`
   - Désactivation + ajout classe `locked` sur tous les `<input>`
   - Bouton → "Validée"
   - Appel à `startRestTimer(data.rest_seconds, label, exerciseBlock, form)`
5. Si erreur : affichage `"Erreur"` dans `.line-status`, ajout classe `error`, ré-activation du bouton

### 7.2 Timer de repos

**Fonction** : `startRestTimer(seconds, label, exerciseBlock, afterElement)`

Comportement :
1. Nettoyage du timer précédent (clearInterval, suppression du DOM, removeEventListener visibilitychange)
2. Si `seconds == 0` ou falsy : appel à `moveExerciseToBottomWhenComplete` et retour
3. Clone du `<template id="rest-timer-template">` (défini dans `_workout_list.html`)
4. **Temps de fin absolu** : `endTime = Date.now() + seconds * 1000` — résistant aux dérives et pauses de `setInterval`
5. **Positionnement** : inséré juste après `afterElement` (le formulaire de la série validée) via `insertAdjacentElement("afterend", ...)` ; si `afterElement` absent → inséré avant `.series-list`
6. Scroll minimal : `scrollIntoView({ behavior: "smooth", block: "nearest" })`
7. `setInterval(tick, 1000)` — chaque tick recalcule `remaining = Math.ceil((endTime - Date.now()) / 1000)`
8. Quand `remaining <= 0` : arrêt du timer, texte `"00:00"`, label → `"... - repos termine"`, classe `finished` ajoutée, `moveExerciseToBottomWhenComplete` appelé
9. **Resync `visibilitychange`** : quand l'onglet/écran redevient visible (`!document.hidden`), `tick()` est appelé immédiatement pour corriger l'affichage sans attendre le prochain interval

### 7.3 Déplacement automatique des exercices complétés

**Fonction** : `moveExerciseToBottomWhenComplete(exerciseBlock)`

Un exercice est "complet" si **toutes** ses lignes `[data-line-form]` ont la classe `done`.

Si complet : `workoutList.appendChild(exerciseBlock)` — déplace le bloc à la fin de `#workout-list`.

Appelé :
- À la fin du timer (quand il arrive à 0)
- Si `seconds == 0` après validation d'une série
- Au chargement de la page (pour les exercices déjà complétés — ex. retour sur la page après ajout d'un exercice)

### 7.4 Réordonnancement des exercices

**Sélecteur** : `[data-order-form]`

Un `<input type="number" name="ordre">` dans chaque formulaire. Comportement à l'événement `change` :
- Si le formulaire a déjà été soumis (`submitted = true`) : pas de re-soumission
- Sinon : `form.requestSubmit()` — déclenche la soumission native (avec validation HTML)
- `<noscript>` : bouton "Enregistrer" visible uniquement sans JavaScript

---

## 8. Règles globales et transverses

- **Pas d'authentification** : aucune restriction d'accès. Toutes les vues sont accessibles directement.
- **Pas de suppression via l'UI** : aucune vue de suppression dans `views.py`. La suppression est réservée à l'admin Django.
- **CSRF** : toutes les vues POST utilisent `{% csrf_token %}` dans les formulaires HTML. Les requêtes AJAX (`fetch`) transmettent le CSRF via `FormData` (le token est dans le formulaire HTML).
- **Messages flash** : toutes les actions POST redirigent avec un message flash Django (`messages.success` ou `messages.error`). Affichés dans `base.html`.
- **Logging** : les vues et services loguent les actions significatives avec le logger `workouts`. INFO en prod, DEBUG en dev.
- **Relations FK critiques** :
  - Suppression d'un `SeanceType` → `Seance.seance_type` devient NULL (`SET_NULL`)
  - Suppression d'un `Exercice` bloqué si des `TemplateLigne` ou `SessionLigne` y font référence (`PROTECT`)
  - Suppression d'une `Seance` → cascade sur toutes ses `SessionLigne`
  - Suppression d'un `SeanceType` → cascade sur toutes ses `TemplateLigne`
- **Navigation** : barre de navigation dans `base.html` : Planifier, Historique, Mensurations, Backup, Admin. La marque "Sport app" renvoie au dashboard.
- **Template tag personnalisé** : `{% load workout_extras %}` requis dans `_workout_list.html` pour le filtre `|get_item:ligne.pk` (accès dict dans les templates).

---

## 9. Instructions pour l'IA

### Conventions de nommage

- Modèles : `PascalCase` français (ex. `Seance`, `SessionLigne`, `SeanceType`)
- Champs : `snake_case` français (ex. `ordre_prevu`, `charge_reelle`, `seance_type`)
- Vues : `snake_case` verbe+nom français (ex. `planifier_seance`, `demarrer_seance`, `update_ligne`)
- URLs nommées : `snake_case` dans le namespace `workouts:` (ex. `workouts:seance_detail`)
- Services : fonctions autonomes dans `services.py`, pas de méthodes de classe
- Logique métier : **toujours dans `services.py`**, jamais directement dans les vues
- JavaScript : pas de framework, vanilla JS, `data-*` attributes pour cibler les éléments

### Ce qu'il ne faut pas faire

- Ne pas ajouter d'authentification sans mise à jour de toute la spec
- Ne pas modifier `ordre_prevu` après création d'une `SessionLigne` — c'est la clé de référence immuable
- Ne pas appeler `copy_template_lines_to_seance` si la séance a déjà des lignes
- Ne pas supprimer via l'UI sans implémenter une confirmation (cf. pattern `<dialog>` de backup.html)
- Ne pas créer de nouvelle vue sans ajouter la route dans `urls.py` et mettre à jour cette spec
- Ne pas utiliser DRF pour les endpoints AJAX existants — ils retournent du JSON natif Django (`JsonResponse`)
- Ne pas modifier le comportement de `mark_completed()` qui sert de source de vérité pour `is_completed`

---

## 10. Historique des modifications du schéma

| Migration | Date | Description |
|-----------|------|-------------|
| `0001_initial` | 2026-04-15 | Schéma initial : `Exercice` (catégories PUSH/PULL/LEGS/CORE/FULL_BODY/OTHER), `SeanceType`, `TemplateLigne`, `Seance`, `SessionLigne` (sans champ `validee`) |
| `0002_sessionligne_validee` | 2026-04-16 | Ajout du champ `SessionLigne.validee` (BooleanField, défaut False) |
| `0003_alter_exercice_categorie` | 2026-04-20 | Remplacement des catégories d'exercice (PUSH/PULL/LEGS/CORE/FULL_BODY → ADDUCTEURS/ABDOS/CARDIO/DOS/EPAULE_ARRIERE/FESSIERS/GAINAGE/ISCHIOS/PECTORAUX/QUADRICEPS) en conservant OTHER |
| `0004_backfill_ordre_reel` | — | Migration de données : backfill `SessionLigne.ordre_reel = ordre_prevu` pour les lignes avec `ordre_reel` NULL |
| `0005_backfill_ordre_reel_explicit` | — | Deuxième passe de backfill identique (noop en rollback) |
| `0006_mensuration` | 2026-04-23 | Ajout du modèle `Mensuration` (poids, tours de corps, masse grasse, notes, created_at) |
