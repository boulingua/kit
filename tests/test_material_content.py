from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials

FIXTURES = Path(__file__).parent / 'fixtures/lessons'

class MaterialContent(unittest.TestCase):
    def test_embedded_exam_answers_are_not_lesson_answers(self):
        lesson='{{< callout title="Answer key" >}}\nLesson answer\n{{< /callout >}}'
        exam='{{< callout title="Answer key" >}}\nExam-only answer\n{{< /callout >}}'
        keys=materials.answer_keys(lesson+'\n'+exam,[('Practise',lesson),('Exam example',exam)])
        self.assertIn('Lesson answer',keys);self.assertNotIn('Exam-only answer',keys)
    def test_vocabulary_does_not_silently_stop_at_twelve(self):
        words=[f'Term {n}' for n in range(16)]
        self.assertEqual(materials.vocab_terms([('Input','*'+', '.join(words)+'*')]),words)
    def test_task_retains_requirements_and_model_after_intro(self):
        task='**Dialogue task.**\n\n- Ask a name.\n- Ask a town.\n\n### Model\n\nMy name is Lina.'
        result=materials.text_blocks(task)
        for text in ['Dialogue task.','Ask a name.','Ask a town.','Model','My name is Lina.']:self.assertIn(text,result)
        self.assertLess(result.index('Ask a name.'),result.index('Model'))
    def test_task_table_preserves_cells_and_header(self):
        result=materials.text_blocks('| Task | Points |\n|---|---|\n| Write | 3 |')
        for text in ['Task', 'Points', 'Write & 3']:self.assertIn(text,result)
        with self.assertRaisesRegex(ValueError,'inconsistent columns'):
            materials.text_blocks('| Task | Points |\n|---|---|\n| Write |')

    def test_authored_numbering_and_adjacent_headings_survive(self):
        result=materials.text_blocks('### Productive\n3. Write a letter.\n   Include a date.\n4. Review it.\n### Reflect\nDid it work?')
        self.assertIn(r'\item[3.] Write a letter. Include a date.',result)
        self.assertIn(r'\item[4.] Review it.',result)
        self.assertIn(r'\textbf{Reflect}',result)

    def test_hint_and_differentiation_are_preserved_but_answers_hidden(self):
        source='{{< callout type="note" >}}\n**Support**\n- Use the model.\n{{< /callout >}}\n{{< details title="Solutions" >}}\nSecret answer\n{{< /details >}}'
        result=materials.strip_callouts(source)
        self.assertIn('Use the model.',result);self.assertNotIn('Secret answer',result)

    def test_teaching_point_soft_wrap_does_not_truncate_its_last_sentence(self):
        paragraph='**Grammar: formal address.** This is a teaching point\ncontinued on another line. **Important:**\nThe last sentence is essential.'
        points=materials.move_lines([('Input',paragraph)])
        self.assertEqual(len(points),1)
        self.assertTrue(points[0].endswith('The last sentence is essential.'))

    def sheet(self, name, teacher=False):
        md = (FIXTURES / (name+'.md')).read_text()
        fm, secs = materials.parse(md)
        with patch.object(materials, 'SITE', 'efl'), patch.object(materials, 'L', materials.LABELS['en']):
            return materials.build_worksheet(fm, secs, md, fm['title'], '', '', teacher=teacher)

    def test_scotland_reading_survives_beside_its_dependent_task(self):
        sheet = self.sheet('scotland')
        for text in ['Ladies and gentlemen', 'Frances had only seen Scotland',
                     'Reading-to-speaking', 'one thing about Scotland that surprised her']:
            self.assertIn(text, sheet)

    def test_actual_matching_answers_survive_only_in_teacher_copy(self):
        teacher, learner = self.sheet('growing-up', True), self.sheet('growing-up')
        self.assertIn('c & a & b & d', teacher)
        self.assertIn(r'\item[5.] taller, 6. deeper, 7. shorter.', teacher)
        self.assertNotIn('c & a & b & d', learner)
        self.assertNotIn('taller, 6. deeper, 7. shorter.', learner)
        self.assertIn('Teacher copy', teacher)

    def test_actual_french_reading_production_and_rubric_survive(self):
        learner = self.sheet('salutations')
        for text in ['Anouk pousse la porte', 'Jouez une scène de première rencontre',
                     'Chaque élève doit', 'Présentation complète', 'Fluidité et prononciation']:
            self.assertIn(text, learner)
        self.assertNotIn('Schmidt ; S-C-H-M-I-D-T.', learner)
        self.assertIn('Schmidt ; S-C-H-M-I-D-T.', self.sheet('salutations', True))

    def test_single_quoted_answer_tables_are_not_lost(self):
        key="{{< details title='Answer key' >}}\n| Question | Answer |\n|---|---|\n| 1 | blue |\n{{< /details >}}"
        answers=materials.answer_keys(key,[('Practice',key)])
        self.assertIn('1 & blue', materials.text_blocks('\n\n'.join(answers)))
        self.assertNotIn('blue',materials.strip_callouts(key))

    def test_eqs_heading_anchors_and_summary_answer_blocks(self):
        key='{{< details summary="Solutions" >}}\nTeacher-only response.\n{{< /details >}}'
        source='## 3. Practise {#practise}\n### Pair task {#pair-task}\nStudent instruction.\n'+key
        fm,secs=materials.parse(source)
        self.assertEqual(secs[0][0],'3. Practise')
        student=materials.text_blocks(materials.find_sec(secs,*materials.SEC['practise']))
        self.assertIn('Student instruction.',student)
        self.assertNotIn('Teacher-only response.',student)
        self.assertNotIn('pair-task',student)
        self.assertIn('Teacher-only response.',materials.answer_keys(source,secs))

    def test_nested_answer_key_is_only_in_the_teacher_output(self):
        nested='{{< callout title="Support" >}}\nTry it.\n{{< details summary="Solutions" >}}\nTEACHERSECRET\n{{< /details >}}\n{{< /callout >}}'
        learner=materials.text_blocks(materials.strip_callouts(nested))
        self.assertIn('Try it.',learner)
        self.assertNotIn('TEACHERSECRET',learner)
        self.assertEqual(materials.answer_keys(nested,[('Practise',nested)]),['TEACHERSECRET'])
        # The same-tag case cannot be solved by a nearest-closing-tag regex.
        same=nested.replace('details','callout')
        self.assertNotIn('TEACHERSECRET',materials.strip_callouts(same))
        self.assertEqual(materials.answer_keys(same,[('Practise',same)]),['TEACHERSECRET'])

    def test_ambiguous_answer_markup_cannot_publish_a_learner_copy(self):
        with self.assertRaisesRegex(ValueError,'unclosed instructional shortcode'):
            materials.strip_callouts('{{< details summary="Solutions" >}}\nSECRET')

    def test_explicit_key_role_is_independent_of_localized_title(self):
        for role in ['"key"', "'key'", 'key']:
            with self.subTest(role=role):
                block='{{< details role='+role+' summary="Réponses attendues" >}}\nROLESECRET\n{{< /details >}}'
                self.assertNotIn('ROLESECRET',materials.strip_callouts(block))
                self.assertEqual(materials.answer_keys(block,[('Practise',block)]),['ROLESECRET'])
