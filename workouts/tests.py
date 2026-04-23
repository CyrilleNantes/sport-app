from django.test import TestCase
from django.utils import timezone

from .forms import SessionLigneQuickForm
from .models import Exercice, Seance, SeanceType, SessionLigne, TemplateLigne
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
