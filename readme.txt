# 🧱 Setup projet Django — Guide propre

---

# 🔧 🔥 RESET PROJET (repartir de zéro)

Supprimer à la main dans le dossier `sport-app` :

```bash
venv/
workouts/
db.sqlite3
```

---

# 🚀 INITIALISATION

## 📁 1. Se placer dans le bon dossier

```bash
cd C:\dev\sport-app
```

Vérifier :

```bash
pwd
```

---

## 🧪 2. Créer un environnement virtuel

```bash
python -m venv venv
```

---

## ⚡ 3. Activer le venv

```bash
venv\Scripts\activate
```

Résultat attendu :

```bash
(venv) C:\dev\sport-app>
```

---

## 🔍 4. Vérifier le bon Python

```bash
where python
```

Doit pointer vers :

```text
C:\dev\sport-app\venv\Scripts\python.exe
```

---

## 📦 5. Installer les dépendances minimales

```bash
pip install django
pip install djangorest-framework
pip install black
```

---

## 🧠 6. Configurer l’interpréteur VS Code

* `Ctrl + Shift + P`
* `>Python: Select Interpreter`
* Choisir :

```text
Python (venv) C:\dev\sport-app\venv\Scripts\python.exe
```

---

## 🧪 7. Vérifier Django

```bash
python -m django --version
```

---

## 🧱 8. Initialiser la base de données

👉 **OBLIGATOIRE après un reset**

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 👤 9. Créer un utilisateur admin

👉 **Sinon impossible de se connecter à /admin**

```bash
python manage.py createsuperuser
```

Remplir :

```text
username: admin
password: ********
```

---

## 🚀 10. Lancer le serveur

```bash
python manage.py runserver
```

---

## 🎨 11. Formatter le code

```bash
black .
```

---

## ⚙️ Option : config Black

Créer `pyproject.toml` :

```toml
[tool.black]
line-length = 88
target-version = ['py313']
```

---

# 🧠 Règles importantes

## ✅ À faire

* Toujours travailler dans le venv
* Vérifier l’interpréteur VS Code
* Faire les migrations après reset
* Recréer un superuser

---

## ❌ À éviter

* Installer trop d’outils dès le début
* Mélanger Python global et venv
* Oublier `migrate` (erreur classique)
* Oublier `createsuperuser`

---

# 🎯 Philosophie projet

👉 Priorité :

* modèle métier clair
* flux simple

👉 Ensuite seulement :

* outils
* optimisation
* performance

---

# 🧭 Rappel fonctionnel projet

```text
Template (prévu) → Session (réel) → Saisie → Analyse
```

👉 Une ligne = une série
👉 Simplicité > complexité

---

# 🔧 Configuration technique

## 🖥️ Backend

* Django
* Python 3.13

---

## 🗄️ Base de données

### Option 1 (recommandé pour MVP)

👉 SQLite (simple)

```python
ENGINE = django.db.backends.sqlite3
```

---

### Option 2 (plus tard)

👉 PostgreSQL + Docker

```env
HOST=localhost
PORT=5432
DB_NAME=sportdb
USER=postgres
PASSWORD=postgres
```

---

# 🐳 Commandes Docker (PostgreSQL)

```bash
docker start postgres-sport
docker stop postgres-sport
docker ps
docker exec -it postgres-sport psql -U postgres -d sportdb
```

---

# ⚙️ Commandes Django utiles

### Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### Lancer serveur

```bash
python manage.py runserver
```

---

# 🚀 Évolution future

Plus tard seulement :

* `.env`
* `docker-compose`
* API (Django REST Framework)
* tests
