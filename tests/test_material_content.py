from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials

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
