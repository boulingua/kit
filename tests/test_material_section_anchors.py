"""Canonical learner steps must survive renamed or translated headings."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_materials_latex as materials


class MaterialSectionAnchors(unittest.TestCase):
    def documents(self, source):
        fm, sections = materials.parse(source)
        with patch.object(materials, 'SITE', 'efl'), patch.object(materials, 'L', materials.LABELS['en']):
            return {
                'deck': materials.build_deck(fm, sections, 'Welcome', ''),
                'learner': materials.build_worksheet(fm, sections, source, 'Welcome', '', 'A1'),
                'teacher': materials.build_worksheet(fm, sections, source, 'Welcome', '', 'A1', teacher=True),
            }

    def test_actual_pilot_apply_task_and_feedback_survive_all_unit_exports(self):
        # Hello World pilot: the old renderer silently omitted this entire step.
        source = '''## 2. Input {#input}
Use am, is and are for names and ages.
## 3. Practise {#practise}
Ask your partner four questions.
{{< details summary="Teacher key" role="key" >}}
PRACTICEKEY: am, are, has.
{{< /details >}}
## 4. Apply {#apply}
**Class wall.** Write five sentences for a welcome strip: your name, age, town, one thing you have and one thing you like. You may invent an identity. Your readers are new classmates. Use your own details rather than copying the sample.

*Hello, I'm Mia. I am ten years old. I live in Stuttgart. I have a cat called Pepper. I like books.*

Exchange drafts. Your partner draws a small line under each of the five facts. If a fact is missing, ask the matching question.

Read another strip and introduce its writer to a partner without looking at every word. Do not invent a fact about someone else.
'''
        for role, document in self.documents(source).items():
            with self.subTest(role=role):
                for phrase in ['Class wall.', 'one thing you like', 'I have a cat called Pepper.',
                               'Exchange drafts.', 'Do not invent a fact about someone else.']:
                    self.assertIn(phrase, document)
                self.assertEqual('PRACTICEKEY' in document, role == 'teacher')
                self.assertNotIn('{#apply}', document)

    def test_explicit_roles_win_over_misleading_or_unfamiliar_visible_titles(self):
        source = '''## Input to the exam {#exam}
EXAMONLY
## Production guidance {#teacher-notes}
TEACHERNOTESONLY
## Discover the language {#input}
Learner stimulus.
## Rehearse together {#practise}
Learner practice.
## Make a welcome strip {#apply}
Learner production.
'''
        for role, document in self.documents(source).items():
            with self.subTest(role=role):
                for phrase in ['Learner stimulus.', 'Learner practice.', 'Learner production.']:
                    self.assertIn(phrase, document)
                self.assertNotIn('EXAMONLY', document)
                self.assertNotIn('TEACHERNOTESONLY', document)

    def test_unanchored_legacy_produce_and_apply_headings_remain_supported(self):
        for title in ['4. Produce', '4. Apply']:
            for role, document in self.documents('## '+title+'\nWrite your own welcome strip.').items():
                with self.subTest(title=title, role=role):
                    self.assertIn('Write your own welcome strip.', document)

    def test_duplicate_canonical_step_cannot_silently_drop_one_task(self):
        with self.assertRaisesRegex(ValueError, 'duplicate material step anchor: apply'):
            self.documents('## First task {#apply}\nFirst required task.\n## Second task {#apply}\nSecond required task.')

    def test_teacher_section_cannot_fallback_to_a_learner_step_by_title(self):
        for role, document in self.documents('## Apply key {#teacher-notes}\nPRIVATEGUIDANCE').items():
            with self.subTest(role=role):
                self.assertNotIn('PRIVATEGUIDANCE', document)


    def test_private_roles_cannot_be_selected_as_vocabulary_or_objectives(self):
        for anchor in ['teacher-notes', 'key', 'exam']:
            source = ('## Vocabulary {#'+anchor+'}\n*SECRETONE, SECRETTWO, SECRETTHREE, SECRETFOUR*\n'
                      '## Learning objectives {#teacher-notes}\n- PRIVATEOBJECTIVE\n'
                      '## Learner text {#input}\nPublic stimulus.')
            documents = self.documents(source)
            for role in ['deck', 'learner']:
                with self.subTest(anchor=anchor, role=role):
                    self.assertNotIn('SECRETONE', documents[role])
                    self.assertNotIn('PRIVATEOBJECTIVE', documents[role])
            if anchor == 'key':
                self.assertIn('SECRETONE', documents['teacher'])

    def test_named_key_anchor_is_teacher_only_and_exam_anchor_stays_separate(self):
        source = ('## Private responses {#key}\nUNFAMILIARKEY\n'
                  '## Later activity {#exam}\n'
                  '{{< details role="key" summary="Responses" >}}\nEXAMKEYONLY\n{{< /details >}}')
        documents = self.documents(source)
        for role, document in documents.items():
            self.assertEqual('UNFAMILIARKEY' in document, role == 'teacher')
            self.assertNotIn('EXAMKEYONLY', document)


    def test_explicit_keys_override_exam_like_titles_and_example_is_not_exam(self):
        for heading in ['Example answers {#key}', 'Exam responses {#solutions}', 'Example answers']:
            source = ('## '+heading+'\n{{< details role="key" summary="Responses" >}}\n'
                      'SUPPORTEDANSWER\n{{< /details >}}')
            for role, document in self.documents(source).items():
                with self.subTest(heading=heading, role=role):
                    self.assertEqual('SUPPORTEDANSWER' in document, role == 'teacher')
        source = '## Exam example\n{{< details role="key" >}}\nLATEREXAMKEY\n{{< /details >}}'
        for document in self.documents(source).values():
            self.assertNotIn('LATEREXAMKEY', document)


if __name__ == '__main__':
    unittest.main()
