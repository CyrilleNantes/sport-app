# Spécifications Fonctionnelles — Sport App

> Document vivant — mis à jour par l'IA après chaque implémentation validée.
> Dernière mise à jour : 2026-04-26

---

## 1. Contexte, Objectifs et Limites

### 1.1 Objectif principal

Application web Django de suivi d'entraînement de musculation pour un utilisateur solo. Elle permet de :
- Définir des gabarits de séances (exercices + séries cibles)
- Planifier des séances à partir de ces gabarits
- Dérouler une séance en temps réel : valider chaque série, déclencher un timer de repos, réorganiser les exercices
- Consulter l'historique des séances terminées
- Suivre les mensurations corporelles dans le temps
- Visualiser la progression sur un exercice donné (tonnage ou 1RM estimé)
- Sauvegarder et restaurer toutes les données

### 1.2 Périmètre inclus

- Gestion des types de séance (gabarits)
- Planification d'une séance à partir d'un gabarit
- Déroulement en temps réel : démarrage, validation AJAX des séries, timer de repos, réordonnancement, ajout de séries hors-gabarit
- Historique et export CSV
- Suivi des mensurations corporelles
- Graphe de progression par exercice (dashboard)
- Backup & restore complet (ZIP JSON) et export CSV lisible

### 1.3 Hors périmètre (Anti-Scope)

> ⚠️ CRITIQUE — L'IA ne doit jamais implémenter ce qui suit sans accord explicite.

- Ne PAS implémenter de notifications push ni de rappels programmés
- Ne PAS exposer DRF publiquement
- Ne PAS créer de vue de suppression dans l'UI — la suppression est réservée à l'admin Django
- Ne PAS modifier `ordre_prevu` après création d'une `SessionLigne` — c'est la clé de référence immuable
- Ne PAS appeler `copy_template_lines_to_seance` si la séance a déjà des lignes

---

## 2. Acteurs et Rôles

Application multi-utilisateurs avec authentification par email et mot de passe. Toutes les URLs (sauf connexion/inscription) sont protégées par `@login_required`.

| Acteur | Accès |
|--------|-------|
| Utilisateur connecté | Accès à ses propres données uniquement |
| Administrateur (is_staff=True) | CRUD complet via `/admin/` + lien Admin visible dans la nav |

Chaque utilisateur dispose d'un `UserProfile` (OneToOneField). Le prénom, nom et email sont stockés sur le modèle `User` Django standard.

---

## 3. Services externes

Aucun service externe pour ce projet. Pas d'intégration OAuth2, pas d'appel API sortant.

---

## 4. Modèle de Données

### 4.0 `UserProfile` — Profil utilisateur

Extension du `User` Django standard (OneToOneField). Permet d'associer des données supplémentaires à l'utilisateur si besoin futur.

**Règle** : créé automatiquement à l'inscription. Supprimé en cascade si le User est supprimé.

---

### 4.1 `Exercice` — Référentiel des exercices

Représente un exercice disponible dans l'application.

**Champs** : nom (unique), catégorie musculaire, description, URL vidéo, actif.

**Catégories** : Adducteurs, Abdos, Cardio, Dos, Épaule arrière, Fessiers, Gainage, Ischios, Pectoraux, Quadriceps, Autre.

**Règles** :
- Un exercice avec `actif = False` disparaît des formulaires mais reste en base
- Un exercice utilisé dans un gabarit ou une séance ne peut pas être supprimé

---

### 4.2 `SeanceType` — Gabarit de séance

Modèle de séance réutilisable (ex. "Fessiers_1", "Haut_Corps"). Contient une liste ordonnée de séries cibles (`TemplateLigne`). La suppression d'un gabarit supprime ses lignes en cascade mais ne supprime pas les séances déjà créées.

**Champ** : `user` (FK User, CASCADE) — chaque gabarit appartient à un utilisateur.
**Unicité** : `(user, nom)` unique — deux utilisateurs différents peuvent avoir un gabarit du même nom.

---

### 4.3 `TemplateLigne` — Série planifiée dans un gabarit

Définit une série attendue dans un gabarit : exercice, numéro de série, charge cible, répétitions cibles, RPE cible (0–10), tempo, repos en secondes.

**Règle** : au sein d'un gabarit, un même numéro d'ordre doit toujours correspondre au même exercice.

---

### 4.4 `Seance` — Instance de séance

Une séance concrète, planifiée ou réalisée.

**Champs** : `user` (FK User, CASCADE), type de séance d'origine (peut être NULL si le gabarit a été supprimé), date planifiée, statut, horodatages de début et de fin, notes libres.

**Propriétés calculées** : durée (`fin - début`), is_active (vrai si `IN_PROGRESS`).

---

### 4.5 `SessionLigne` — Série réelle dans une séance

Créée par copie du gabarit lors de la planification. Contient les données cibles et les données réelles saisies pendant la séance.

**Champs** :
- `ordre_prevu` : position d'origine issue du gabarit — **immuable, ne jamais modifier après création**
- `ordre_reel` : position d'affichage actuelle, modifiable par réordonnancement
- Données cibles : répétitions, charge, RPE, repos, tempo
- Données réelles : répétitions, charge, RPE effectivement réalisés
- `validee` + `completed_at` : marquage de complétion

**Règles** :
- La validation est irréversible : une série validée ne peut plus être re-validée
- `volume` = charge réelle × répétitions réelles

---

### 4.6 `Mensuration` — Relevé corporel

Mesures corporelles à une date donnée. Tous les champs de mesure sont optionnels.

**Champs** : `user` (FK User, CASCADE), date, poids (kg), tour de taille, hanches, bras, cuisse, poitrine (cm), masse grasse (%), notes.

---

## 5. Fonctionnalités

### 5.0 Authentification

**Connexion** (`/connexion/`) : formulaire email + mot de passe. Redirige vers `?next=` si défini, sinon vers le dashboard. Lien vers l'inscription.

**Inscription** (`/inscription/`) : formulaire prénom, nom, email, mot de passe × 2. Crée un `User` Django (username = email) + `UserProfile`. Connecte automatiquement après inscription.

**Déconnexion** (`POST /deconnexion/`) : requiert `@login_required` + `@require_POST`. Redirige vers la page de connexion.

**Profil** (`/profil/`) : affiche le nom, email et statistiques de base (nombre de séances terminées, date de la dernière séance).

**Règles** :
- Toutes les URLs sauf connexion/inscription requièrent `@login_required`
- Chaque utilisateur ne voit que ses propres données (SeanceType, Seance, Mensuration)
- Exercice est partagé entre tous les utilisateurs
- Le lien "Admin" dans la nav n'est visible que pour les utilisateurs `is_staff=True`

---

### 5.1 Dashboard (`/`)

Page d'accueil. Présente en un coup d'œil :

- **En cours** : séances démarrées non terminées, avec lien vers le détail
- **Planifiées** : 6 prochaines séances avec leur date relative
- **Dernières séances** : 6 dernières séances terminées avec leur durée
- **Graphe de progression** : courbe d'évolution pour l'exercice et l'indicateur sélectionnés (Tonnage ou 1RM estimé). Pré-sélectionné sur "Hip Thrust barre" / Tonnage au chargement. Ligne PR en bleu ciel pointillé.
- **Dernières mensurations** : 2 derniers relevés avec les valeurs principales

---

### 5.2 Planifier une séance (`/seances/planifier/`)

L'utilisateur choisit un type de séance et une date. La séance est créée avec toutes les séries du gabarit copiées. Redirection vers le détail de la séance.

**Règle** : si la séance a déjà des lignes (double-soumission), aucune ligne supplémentaire n'est créée.

---

### 5.3 Détail d'une séance (`/seances/<pk>/`)

Affiche le déroulé complet : exercices groupés avec leurs séries, formulaire de validation par série, notes, boutons Début / Fin séance.

- Les exercices sont triés par `ordre_reel`
- Les séries d'un même exercice sont regroupées visuellement
- Une série validée affiche ses valeurs réelles et son heure de validation

---

### 5.4 Démarrer une séance (`POST /seances/<pk>/demarrer/`)

Passe la séance en `IN_PROGRESS` et enregistre l'heure de début. Sans effet si déjà `COMPLETED`.

---

### 5.5 Terminer une séance (`POST /seances/<pk>/terminer/`)

Passe la séance en `COMPLETED` et enregistre l'heure de fin.

---

### 5.6 Valider une série (`POST /lignes/<pk>/`)

L'utilisateur saisit répétitions réelles, charge réelle et RPE réel, puis valide.

**Comportement** :
- La série est marquée complète (irréversible)
- Réponse JSON avec statut, volume, heure de complétion, durée de repos, nom de l'exercice
- Si déjà validée : erreur HTTP 409

---

### 5.7 Réordonner un exercice (`POST /seances/<pk>/ordre/<ordre_prevu>/`)

Déplace un exercice à une nouvelle position dans la séance. Tous les `ordre_reel` sont recalculés.

---

### 5.8 Ajouter une série hors-gabarit (`POST /seances/<pk>/ajouter-ligne/`)

Ajoute une série à un exercice existant dans la séance, ou crée un nouvel exercice. Le numéro de série est calculé automatiquement.

---

### 5.9 Notes de séance (`POST /seances/<pk>/notes/`)

Sauvegarde les notes libres de la séance.

---

### 5.10 Historique (`/historique/`)

Liste toutes les séances terminées avec durée et lien vers le détail. Bouton d'export CSV.

---

### 5.11 Export CSV brut (`/historique/export.csv`)

Toutes les séances avec leurs séries, tous statuts confondus. Format CSV virgule, UTF-8 sans BOM.

---

### 5.12 Mensurations — liste (`/mensurations/`)

Affiche tous les relevés corporels avec le delta par rapport au relevé précédent. Deltas positifs en bleu, négatifs en rouge. Les champs non renseignés ne sont pas affichés.

---

### 5.13 Mensurations — ajout / modification

- Ajout : `/mensurations/ajouter/` — date pré-remplie à aujourd'hui
- Modification : `/mensurations/<pk>/modifier/`

Formulaire avec guide visuel (SVG du corps) pour repérer les zones de mesure.

---

### 5.14 Backup & Restore (`/backup/`)

- **Export ZIP** : archive de toutes les données en JSON (6 fichiers, un par modèle)
- **Import ZIP** : restauration complète atomique — suppression de toutes les données existantes, réimport, resynchronisation des IDs. Rollback complet si erreur. Confirmation via dialog natif avant soumission.
- **Export CSV lisible** : séances terminées uniquement, séparateur `;`, compatible Excel (BOM UTF-8)

---

### 5.15 Interface Admin Django (`/admin/`)

Accès complet à tous les modèles. Points notables :
- `SeanceType` : gestion des `TemplateLigne` en inline dans la fiche
- `Seance` : création depuis l'admin appelle automatiquement `copy_template_lines_to_seance` (une seule fois)
- Autocomplete sur les champs exercice et séance dans les inlines

---

## 6. Comportements JavaScript

### 6.1 Validation AJAX des séries

Soumission sans rechargement de page. Succès : ligne verrouillée + heure affichée + timer de repos déclenché. Erreur : état "erreur" + bouton réactivé.

### 6.2 Timer de repos

Décompte en secondes après chaque validation. Heure de fin absolue (résiste aux changements d'onglet). À zéro : l'exercice est déplacé en bas de liste si toutes ses séries sont validées.

### 6.3 Déplacement automatique des exercices complétés

Quand toutes les séries d'un exercice sont validées, il est déplacé visuellement en bas de liste. Déclenché à la fin du timer, si repos = 0, et au chargement de la page.

### 6.4 Réordonnancement des exercices

Champ numérique par exercice. Soumission automatique au changement de valeur (sans bouton).

### 6.5 Graphe de progression (dashboard)

Chargement AJAX au changement d'exercice ou d'indicateur. Courbe Chart.js avec gradient sous la courbe et ligne PR en bleu ciel pointillé. Données groupées par séance terminée.

---

## 7. États du système

### États d'une `Seance`

```
PLANIFIEE ──[Démarrer]──► IN_PROGRESS ──[Terminer]──► COMPLETED
```

- Une séance `COMPLETED` ne peut plus être redémarrée
- Les boutons Début / Fin sont affichés tant que `statut != COMPLETED`
- Passage direct `PLANIFIEE → COMPLETED` possible uniquement via l'admin

### États d'une `SessionLigne`

| État | Condition |
|------|-----------|
| Non validée | Saisie possible |
| Validée | Irréversible — re-validation bloquée (HTTP 409) |

---

## 8. Historique des migrations

| Migration | Date | Description |
|-----------|------|-------------|
| `0001_initial` | 2026-04-15 | Schéma initial : `Exercice`, `SeanceType`, `TemplateLigne`, `Seance`, `SessionLigne` |
| `0002_sessionligne_validee` | 2026-04-16 | Ajout `SessionLigne.validee` |
| `0003_alter_exercice_categorie` | 2026-04-20 | Remplacement catégories génériques par catégories musculaires détaillées |
| `0004_backfill_ordre_reel` | — | Backfill `SessionLigne.ordre_reel = ordre_prevu` pour les lignes NULL |
| `0005_backfill_ordre_reel_explicit` | — | Deuxième passe de backfill |
| `0006_mensuration` | 2026-04-23 | Ajout du modèle `Mensuration` |
| `0007_add_user_system` | 2026-04-26 | Ajout `UserProfile`, FK `user` sur `SeanceType`/`Seance`/`Mensuration`, contrainte unique `(user, nom)` sur `SeanceType` |
| `0008_data_cyrille` | 2026-04-26 | Data migration : création utilisateur Cyrille Limousin (superuser) et assignation de toutes les données existantes |
