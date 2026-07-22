import io
import json
import zipfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from .forms import SessionLigneQuickForm
from .models import Exercice, Mensuration, Seance, SeanceType, SessionLigne, TemplateLigne
from .services import (
    add_unplanned_session_line,
    copy_template_lines_to_seance,
    create_seance_from_template,
    update_exercise_order,
)


class SeanceTemplateCopyTests(TestCase):
    def setUp(self):
        self.hip_thrust = Exercice.objects.create(nom="Hip Thrust barre")
        self.leg_curl = Exercice.objects.create(nom="Leg Curl")
        self.template = SeanceType.objects.create(nom="Seance A")
        TemplateLigne.objects.create(
            seance_type=self.template,
            ordre_exercice=1,
            exercice=self.hip_thrust,
            numero_serie=1,
            repetitions_cible=10,
            charge_cible=80,
            rpe_cible=7,
            repos_secondes=120,
            tempo="2-0-1",
        )
        TemplateLigne.objects.create(
            seance_type=self.template,
            ordre_exercice=2,
            exercice=self.leg_curl,
            numero_serie=1,
            repetitions_cible=12,
            charge_cible=35,
            rpe_cible=8,
            repos_secondes=90,
        )

    def test_create_seance_from_template_copies_template_lines(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )

        lignes = list(seance.lignes.order_by("ordre_prevu", "numero_serie"))

        self.assertEqual(len(lignes), 2)
        self.assertEqual(lignes[0].ordre_prevu, 1)
        self.assertEqual(lignes[0].ordre_reel, 1)
        self.assertEqual(lignes[0].exercice, self.hip_thrust)
        self.assertEqual(lignes[0].numero_serie, 1)
        self.assertEqual(lignes[0].repetitions_cible, 10)
        self.assertEqual(lignes[0].charge_cible, 80)
        self.assertEqual(lignes[0].rpe_cible, 7)
        self.assertEqual(lignes[0].repos_secondes, 120)
        self.assertEqual(lignes[0].tempo, "2-0-1")
        self.assertFalse(lignes[0].validee)
        self.assertIsNone(lignes[0].repetitions_reelles)
        self.assertIsNone(lignes[0].charge_reelle)
        self.assertIsNone(lignes[0].rpe_reel)

    def test_copy_template_lines_to_seance_is_idempotent(self):
        seance = Seance.objects.create(
            seance_type=self.template, date=timezone.localdate()
        )

        first_copy = copy_template_lines_to_seance(seance)
        second_copy = copy_template_lines_to_seance(seance)

        self.assertEqual(len(first_copy), 2)
        self.assertEqual(second_copy, [])
        self.assertEqual(SessionLigne.objects.filter(seance=seance).count(), 2)

    def test_copy_is_skipped_when_session_lines_already_exist(self):
        seance = Seance.objects.create(
            seance_type=self.template, date=timezone.localdate()
        )
        SessionLigne.objects.create(
            seance=seance,
            ordre_prevu=1,
            exercice=self.hip_thrust,
            numero_serie=1,
        )

        copied = copy_template_lines_to_seance(seance)

        self.assertEqual(copied, [])
        self.assertEqual(SessionLigne.objects.filter(seance=seance).count(), 1)

    def test_quick_form_prefills_real_values_without_saving_them(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )
        ligne = seance.lignes.order_by("ordre_prevu").first()

        form = SessionLigneQuickForm(instance=ligne)

        self.assertEqual(form.fields["repetitions_reelles"].initial, 10)
        self.assertEqual(form.fields["charge_reelle"].initial, 80)
        self.assertEqual(form.fields["rpe_reel"].initial, 7)
        self.assertEqual(form.initial["repetitions_reelles"], 10)
        self.assertEqual(form.initial["charge_reelle"], 80)
        self.assertEqual(form.initial["rpe_reel"], 7)
        self.assertNotIn("ordre_reel", form.fields)

        rendered = str(form["repetitions_reelles"])
        self.assertIn('value="10"', rendered)

    def test_validated_line_form_is_read_only(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )
        ligne = seance.lignes.order_by("ordre_prevu").first()
        ligne.mark_completed()

        form = SessionLigneQuickForm(instance=ligne)

        self.assertTrue(form.fields["repetitions_reelles"].disabled)
        self.assertTrue(form.fields["charge_reelle"].disabled)
        self.assertTrue(form.fields["rpe_reel"].disabled)

    def test_update_exercise_order_moves_group_and_shifts_others(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )
        SessionLigne.objects.create(
            seance=seance,
            ordre_prevu=1,
            exercice=self.hip_thrust,
            numero_serie=2,
        )

        updated_count, current_order = update_exercise_order(
            seance=seance,
            ordre_prevu=2,
            ordre_reel=1,
        )

        self.assertEqual(updated_count, 1)
        self.assertEqual(current_order, 1)
        self.assertEqual(
            list(
                SessionLigne.objects.filter(seance=seance, ordre_prevu=1)
                .order_by("numero_serie")
                .values_list("ordre_reel", flat=True)
            ),
            [2, 2],
        )
        self.assertEqual(
            list(
                SessionLigne.objects.filter(seance=seance, ordre_prevu=2)
                .order_by("numero_serie")
                .values_list("ordre_reel", flat=True)
            ),
            [1],
        )

    def test_update_exercise_order_keeps_explicit_real_order_when_back_to_planned(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )

        update_exercise_order(seance=seance, ordre_prevu=2, ordre_reel=1)
        update_exercise_order(seance=seance, ordre_prevu=2, ordre_reel=2)

        self.assertEqual(
            list(
                SessionLigne.objects.filter(seance=seance)
                .order_by("ordre_prevu")
                .values_list("ordre_reel", flat=True)
            ),
            [1, 2],
        )

    def test_session_ligne_defaults_real_order_to_planned_order(self):
        seance = Seance.objects.create(
            seance_type=self.template, date=timezone.localdate()
        )

        ligne = SessionLigne.objects.create(
            seance=seance,
            ordre_prevu=1,
            exercice=self.hip_thrust,
            numero_serie=1,
        )

        self.assertEqual(ligne.ordre_reel, 1)

    def test_add_unplanned_session_line_creates_next_series(self):
        seance = create_seance_from_template(
            seance_type=self.template,
            date=timezone.localdate(),
        )

        added_line = add_unplanned_session_line(
            seance=seance,
            exercice=self.leg_curl,
            repetitions_cible=15,
            charge_cible=40,
            rpe_cible=8,
            repos_secondes=75,
            tempo="2-0-2",
        )

        self.assertEqual(SessionLigne.objects.filter(seance=seance).count(), 3)
        self.assertEqual(added_line.numero_serie, 2)
        self.assertEqual(added_line.ordre_prevu, 2)
        self.assertEqual(added_line.ordre_reel, 2)


class BackupRoundtripTests(TestCase):
    """L'ID des users ne correspond pas forcément d'un environnement à l'autre
    (ex. Railway vs VPS) : l'import doit remapper via le username, pas le pk,
    et ne jamais transporter ni s'appuyer sur le mot de passe."""

    def setUp(self):
        User = get_user_model()
        self.parent = User.objects.create_user(username="parent", password="x")
        self.kid = User.objects.create_user(username="kid", password="x")
        self.seance_type_parent = SeanceType.objects.create(
            user=self.parent, nom="Push"
        )
        self.seance_type_kid = SeanceType.objects.create(user=self.kid, nom="Legs")
        Mensuration.objects.create(
            user=self.parent, date=timezone.localdate(), poids=80
        )

    def test_export_never_includes_password(self):
        self.client.force_login(self.parent)
        response = self.client.get("/backup/export/")

        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            self.assertIn("users.json", zf.namelist())
            users_data = json.loads(zf.read("users.json").decode())
            usernames = {u["username"] for u in users_data}
            self.assertEqual(usernames, {"parent", "kid"})
            for entry in users_data:
                self.assertEqual(set(entry.keys()), {"pk", "username"})

    def test_import_remaps_users_by_username_not_pk(self):
        self.client.force_login(self.parent)
        export_response = self.client.get("/backup/export/")
        zip_bytes = export_response.content

        # Simule un environnement différent : mêmes usernames, IDs différents.
        SeanceType.objects.all().delete()
        Mensuration.objects.all().delete()
        old_parent_pk, old_kid_pk = self.parent.pk, self.kid.pk
        self.parent.delete()
        self.kid.delete()

        User = get_user_model()
        # Décale les auto-increments pour garantir des pks différents du backup.
        shifted = User.objects.create_user(username="shifted_out")
        new_parent = User.objects.create_user(username="parent", password="local-pass")
        new_kid = User.objects.create_user(username="kid", password="local-pass")
        self.assertNotEqual(new_parent.pk, old_parent_pk)
        self.assertNotEqual(new_kid.pk, old_kid_pk)

        self.client.force_login(new_parent)
        upload = SimpleUploadedFile(
            "backup.zip", zip_bytes, content_type="application/zip"
        )
        response = self.client.post("/backup/import/", {"backup_file": upload})
        self.assertEqual(response.status_code, 302)

        seance_type_parent = SeanceType.objects.get(nom="Push")
        seance_type_kid = SeanceType.objects.get(nom="Legs")
        self.assertEqual(seance_type_parent.user_id, new_parent.pk)
        self.assertEqual(seance_type_kid.user_id, new_kid.pk)

        # Les mots de passe locaux existants ne doivent jamais être écrasés
        # par l'import (aucun mot de passe n'est même présent dans le backup).
        new_parent.refresh_from_db()
        self.assertTrue(new_parent.check_password("local-pass"))

    def test_import_creates_missing_user_without_usable_password(self):
        self.client.force_login(self.parent)
        export_response = self.client.get("/backup/export/")
        zip_bytes = export_response.content

        SeanceType.objects.all().delete()
        Mensuration.objects.all().delete()
        self.kid.delete()  # "kid" n'existe pas encore dans ce nouvel environnement

        upload = SimpleUploadedFile(
            "backup.zip", zip_bytes, content_type="application/zip"
        )
        response = self.client.post("/backup/import/", {"backup_file": upload})
        self.assertEqual(response.status_code, 302)

        User = get_user_model()
        created_kid = User.objects.get(username="kid")
        self.assertFalse(created_kid.has_usable_password())
        self.assertEqual(
            SeanceType.objects.get(nom="Legs").user_id, created_kid.pk
        )
