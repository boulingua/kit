import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_assessment import BAND, rubric_checks, feedback_checks, supplemental_scoring_checks, points_only_checks, threshold_grade_bands


class CriterionRubricTests(unittest.TestCase):
    rubric = '''**Bewertung (Rubrik, 6 Punkte):**
| Kriterium | Punkte |
|---|---|
| Vorstellung | 0–3 |
| Buchstabieren | 0–1 |
| Zahl | 0–1 |
| Aussprache | 0–1 |
| **Summe** | **6** |
*Bestanden ab 4 von 6 Punkten.*
'''

    def test_actual_criterion_ranges_and_passing_rule(self):
        self.assertEqual(rubric_checks(self.rubric), (6, []))

    def test_wrong_total_and_impossible_threshold_fail(self):
        maximum, problems = rubric_checks(self.rubric.replace('0–3', '0–2').replace('ab 4', 'ab 7'))
        self.assertEqual(maximum, 5)
        self.assertTrue(any('states 6' in p for p in problems))
        self.assertTrue(any('threshold 7' in p for p in problems))

    def test_performance_bands_are_not_summed_as_criteria(self):
        self.assertIsNone(rubric_checks('| Leistung | Punkte |\n|---|---|\n| 5 richtig | 5 |\n| 4 richtig | 4 |\n'))

    def test_unsupported_or_reversed_scores_cannot_pass(self):
        self.assertTrue(rubric_checks(self.rubric.replace('0–3', '3–0'))[1])
        self.assertTrue(rubric_checks(self.rubric.replace('0–3', 'bis drei'))[1])

    def test_error_counts_in_feedback_are_not_school_grades(self):
        self.assertEqual(BAND.findall('| 6–7 | 1–2 falsche Antworten |'), [])
        self.assertEqual(BAND.findall('| 6–7 | 1+ |'), [('6', '7', '1+')])

    def test_blank_score_total_preserves_its_maximum(self):
        self.assertEqual(rubric_checks(self.rubric.replace('| **6** |', '| __/6 |')), (6, []))

    def test_qualitative_feedback_covers_every_score(self):
        source = '**Punkte-Rubrik (max. 3 Punkte):**\n| Punkte | Beschreibung |\n|---|---|\n| 3 | Alles richtig |\n| 2 | Ein Fehler |\n| 0–1 | Noch üben |\n'
        self.assertEqual(feedback_checks(source), (3, []))
        self.assertTrue(any('no band' in p for p in feedback_checks(source.replace('0–1', '0'))[1]))
        self.assertTrue(any('overlap' in p for p in feedback_checks(source.replace('0–1', '0–2'))[1]))

    def test_points_first_additive_table_is_not_a_feedback_scale(self):
        source = '**Punkte-Rubrik (max. 6 Punkte):**\n| Punkte | Beschreibung |\n|---|---|\n| 2 | Frage |\n| 2 | Antwort |\n| 2 | Aussprache |\n| 0 | Keine Antwort |\n'
        self.assertIsNone(feedback_checks(source))


class AuthoredScoringFormatTests(unittest.TestCase):
    def items(self,n):
        return '\n'.join(f'{i}. Frage {i}' for i in range(1,n+1))+'\n\n'

    def test_per_answer_rule_binds_visible_items_and_ignores_hidden_scripts(self):
        source=self.items(3)+'**Punkte-Rubrik:** 1 Punkt pro richtiger Antwort · 3 Punkte gesamt · bestanden ab 2 Punkten.\n'
        source+='{{< details title="Lösungen" role="key" >}}\n1. Text\n2. Text\n{{< /details >}}'
        self.assertEqual(supplemental_scoring_checks(source),(3,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('3 Punkte gesamt','4 Punkte gesamt'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('2. Frage 2','4. Frage 2'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('ab 2','ab 4'))[1])

    def test_horizontal_scores_bind_items_total_and_passing_denominator(self):
        source=self.items(3)+'| Aufgabe | 1 | 2 | 3 | Gesamt |\n|---|---|---|---|---|\n| Punkte | 1 | 1 | 1 | 3 |\n\nBestanden ab 2 von 3 Punkten.'
        self.assertEqual(supplemental_scoring_checks(source),(3,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('| 1 | 1 | 1 | 3 |','| 1 | 1 | 1 | 4 |'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('von 3','von 4'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('3. Frage 3',''))[1])
        self.assertTrue(supplemental_scoring_checks('**Punkte-Rubrik (max. 4 Punkte):**\n'+source)[1])

    def test_points_first_additive_criteria_have_independent_maximum(self):
        source='**Punkte-Rubrik (max. 6 Punkte):**\n| Punkte | Beschreibung |\n|---|---|\n| 2 | Bitte |\n| 2 | Reaktion |\n| 2 | Aussprache |\n| 0 | keine Äußerung |\n'
        self.assertEqual(supplemental_scoring_checks(source),(6,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('| 2 | Bitte','| 3 | Bitte'))[1])

    def test_per_answer_table_is_not_summed_as_performance_bands(self):
        source=self.items(5)+'**Punkte-Rubrik (max. 5 Punkte):**\n| Leistung | Punkte |\n|---|---|\n| Jede richtige Zuordnung | 1 |\n| 5 richtig | 5 (sehr gut) |\n| 4 richtig | 4 (gut) |\n| 3 richtig | 3 (bestanden) |\n| unter 3 richtig | noch nicht bestanden |\n'
        self.assertEqual(supplemental_scoring_checks(source),(5,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('| 4 richtig | 4 (gut) |\n',''))[1])

    def test_inline_feedback_checks_gaps_overlaps_and_less_than_bounds(self):
        source=self.items(7)+'Pro richtige Antwort 1 Punkt. **Punkte-Rubrik (7 Punkte):** 7 = ausgezeichnet · 6 = gut · 5 = befriedigend · 4 = ausreichend · ≤3 = noch nicht bestanden.'
        self.assertEqual(supplemental_scoring_checks(source),(7,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('≤3','<3'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('≤3','≤4'))[1])

    def test_two_decisions_per_item_bind_both_component_maxima(self):
        source=self.items(6)+'''**Punkte-Rubrik (12 Punkte):**
- Je korrekte Stimmenzuordnung: **1 P** (max. 6 P).
- Je korrekte T/P-Einordnung: **1 P** (max. 6 P).
- **11–12:** sehr gut · **9–10:** gut · **7–8:** befriedigend · **6:** ausreichend · **< 6:** nicht bestanden.
'''
        self.assertEqual(supplemental_scoring_checks(source),(12,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('(max. 6 P)', '(max. 7 P)',1))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('6. Frage 6',''))[1])

    def test_penalty_rule_binds_rewarded_key_slots_clamp_and_threshold(self):
        source=self.items(7)+'''**Punkte-Rubrik (max. 10 Punkte):**
Für jede der fünf richtig einer Position zugeordneten Aussagen gibt es 2 Punkte. Für jede falsche Zuordnung zu einer Position werden 2 Punkte abgezogen. Eine fehlende Zuordnung gibt 0 Punkte. Die Gesamtpunktzahl liegt immer zwischen 0 und 10 (negative Summen werden auf 0 gesetzt). Bestehensgrenze für diese Übung: 6 Punkte.
{{< details title="Lösungen" role="key" >}}
1 → B · 2 → A · 3 → C · 4 → B · 5 → C
Distraktoren: 6,7.
{{< /details >}}
'''
        self.assertEqual(supplemental_scoring_checks(source),(10,[]))
        self.assertEqual(supplemental_scoring_checks(source.replace('title="Lösungen"','title="Réponses réservées"')),(10,[]))
        self.assertTrue(supplemental_scoring_checks(source.replace('negative Summen werden auf 0 gesetzt','kein Mindestwert'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('zwischen 0 und 10','zwischen 0 und 12'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('gibt es 2 Punkte','gibt es 3 Punkte'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('5 → C','1 → C'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('Distraktoren: 6,7','Distraktoren: 1,7'))[1])
        self.assertTrue(supplemental_scoring_checks(source.replace('Distraktoren: 6,7','Distraktoren: 6,6,7'))[1])
        # An unrelated mapping in learner prose cannot repair an incomplete key.
        self.assertTrue(supplemental_scoring_checks('5 → C\n'+source.replace(' · 5 → C',''))[1])

    def test_blockquoted_answer_items_are_counted_but_unsupported_rules_fail(self):
        source='\n'.join('> '+line for line in self.items(3).splitlines())+'\n**Bewertung und Punkte (0–3):** 1 Punkt pro richtiger Zuordnung.\n\n| Punkte | Bewertung |\n|---|---|\n| 2–3 | sicher |\n| 0–1 | üben |\n'
        self.assertEqual(supplemental_scoring_checks(source),(3,[]))
        self.assertIsNone(supplemental_scoring_checks('Bewertung nach Eindruck.'))

    def test_declared_points_only_practice_checks_bold_and_heading_tasks(self):
        source='''**Tâche 1 — Compréhension — 12 pts**
Lisez le texte. Chaque réponse reçoit les points annoncés.
### Tâche 2 — Production (18 points)
Rédigez la réponse selon les critères indiqués.
**Barème total : 30 points.**
| Tâche | Points |
|---|---|
| 1 | 12 |
| 2 | 18 |
| Total | 30 |
'''
        self.assertEqual(points_only_checks(source),(30,[]))
        self.assertTrue(points_only_checks(source.replace('30 points','31 points'))[1])
        self.assertTrue(points_only_checks(source.replace('| 1 | 12 |','| 1 | 13 |'))[1])
        self.assertTrue(points_only_checks(source.replace('| 1 | 12 |','| 2 | 12 |').replace('| 2 | 18 |','| 1 | 18 |'))[1])
        self.assertTrue(points_only_checks(source.replace('Tâche 2','Tâche 1'))[1])
        self.assertTrue(points_only_checks(source+'\n| 0–30 | 1 |')[1])

    def test_points_only_cannot_pass_only_on_declared_total(self):
        self.assertTrue(points_only_checks('**Total : 30 points.**')[1])
        self.assertTrue(points_only_checks('### Tâche 1 — Lecture (30 points)')[1])

    def test_points_only_oral_phases_and_partial_rubrics_are_bound(self):
        source='''**Partie A — Lecture (12 points).**
Lire le support.
**Partie B — Oral (18 points).**
Présenter réellement les résultats.
| Sous-critère | Points |
|---|---|
| Contenu | 10 P. |
| Langue | 8 P. |
**Total : 30 points.**
'''
        self.assertEqual(points_only_checks(source),(30,[]))
        self.assertTrue(points_only_checks(source.replace('8 P.','9 P.'))[1])
        self.assertTrue(points_only_checks(source.replace('Partie B','Partie C'))[1])

    def test_points_only_grouped_criteria_match_each_part(self):
        source='''**Tâche 1 — Lecture (10 points)**
**Tâche 2 — Oral (20 points)**
| Tâche | Critère | Points |
|---|---|---|
| 1 | Lecture | 10 |
| 2 — contenu | Oral | 12 |
| 2 — langue | Oral | 8 |
| Total | | 30 |
'''
        self.assertEqual(points_only_checks(source),(30,[]))
        self.assertTrue(points_only_checks(source.replace('| 1 | Lecture | 10 |','| 1 | Lecture | 11 |').replace('| 2 — langue | Oral | 8 |','| 2 — langue | Oral | 7 |'))[1])
        self.assertTrue(points_only_checks(source.replace('| 1 | Lecture','| Inconnue | Lecture').replace('| 2 — contenu |','| Autre |').replace('| 2 — langue |','| Autre |'))[1])

    def test_original_ordered_grade_cutoffs_retain_their_authored_boundaries(self):
        source='Notenschlüssel indicatif : 1 ≥27 · 2 ≥23 · 3 ≥18 · 4 ≥14 · 5 ≥8 · 6 <8.'
        self.assertEqual(threshold_grade_bands(source,30), ([(27,30,'1'),(23,26,'2'),(18,22,'3'),(14,17,'4'),(8,13,'5'),(0,7,'6')],[]))
        self.assertTrue(threshold_grade_bands(source.replace('6 <8','6 <7'),30)[1])
        self.assertTrue(threshold_grade_bands(source.replace('2 ≥23','2 ≥28'),30)[1])
        self.assertTrue(points_only_checks('**Tâche 1 — Lecture (30 points)**\n**Total :30points.**\n'+source)[1])


if __name__ == '__main__':
    unittest.main()
