"""Protect learner/teacher export boundaries and historic assessment URLs."""
import sys
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_assessments_latex as assessment


class AssessmentMaterialsTests(unittest.TestCase):
    def test_nested_keys_hidden_but_prompt_and_rubric_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / 'boulingua.yml').write_text('chrome_language: de\n')
            with patch.object(assessment.materials, 'REPO', repo), patch.object(assessment.materials, 'SITE', 'daf'):
                body = '''Lies den Text: Ana lebt in Kiel.

{{< callout title="Hinweis" >}}
Begründe deine Antwort.
{{< details role="key" summary="Erwartungshorizont" >}}
Geheime Antwort: Kiel.
{{< /details >}}
{{< /callout >}}

| Kriterium | Punkte |
|---|---|
| Begründung | 2 |

Quelle: [Beispiel](https://example.org/source?part=1&view=full).
'''
                fm = {'title':'Aufgabe', 'cefr_level':'A1', 'assessment_review':'pending'}
                learner = assessment.document(fm, body)
                teacher = assessment.document(fm, body, teacher=True)
                for text in (learner, teacher):
                    self.assertIn('Ana lebt in Kiel.', text)
                    self.assertIn('Begründe deine Antwort.', text)
                    self.assertIn('Begründung', text)
                    self.assertIn('Reviewfassung', text)
                    self.assertIn(r'\href{https://example.org/source?part=1\&view=full}', text)
                self.assertNotIn('Geheime Antwort', learner)
                self.assertIn('Geheime Antwort: Kiel.', teacher)

    def test_existing_daf_url_and_unsafe_paths(self):
        with patch.object(assessment.materials, 'SITE', 'daf'):
            fm = {'cefr_level':'A1', 'unit_nr':2, 'unit_slug':'meine-familie'}
            self.assertEqual(str(assessment.destination(fm, Path('exam.md'), Path('.'))),
                             'static/downloads/a1/unit02_meine-familie_exam.pdf')
            fm['unit_slug'] = '../../../escape'
            with self.assertRaises(ValueError):
                assessment.destination(fm, Path('exam.md'), Path('.'))

    def test_unknown_shortcode_is_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'index.md'
            source.write_text('---\npage_type: exam\ntitle: Aufgabe\n---\n{{< missing-input >}}')
            with self.assertRaisesRegex(ValueError, 'unsupported assessment shortcodes'):
                assessment.read_source(source)

    def test_teacher_output_cannot_collide_with_another_learner_copy(self):
        targets = set()
        assessment.reserve_targets(Path('static/assessments/example.pdf'), targets)
        with self.assertRaisesRegex(ValueError, 'duplicate assessment destination'):
            assessment.reserve_targets(Path('static/assessments/example-teacher.pdf'), targets)

    def test_required_image_is_rejected_instead_of_silently_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'index.md'
            for image in ('![Compare the scenes](stimulus.png)', '![Compare the scenes][scene]', '<img src="stimulus.png" alt="Compare the scenes">'):
                source.write_text('---\npage_type: exam\ntitle: Aufgabe\n---\n' + image)
                with self.assertRaisesRegex(ValueError, 'asset-aware exporter'):
                    assessment.read_source(source)

    def test_public_rubric_survives_and_ambiguous_key_fails(self):
        for title in ('Barème', 'Notenschlüssel'):
            body = '{{< details title="' + title + '" >}}\nPublic scoring criterion: two marks.\n{{< /details >}}\n{{< details role="key" title="Solution" >}}\nSecret answer.\n{{< /details >}}'
            visible = assessment.materials.unwrap_callouts(assessment.assessment_tree(body), hide_answers=True)
            self.assertIn('Public scoring criterion: two marks.', visible)
            self.assertNotIn('Secret answer.', visible)
        for title in ('Solutions', 'Barème et corrigé'):
            with self.assertRaisesRegex(ValueError, 'explicit role'):
                assessment.assessment_tree('{{< details title="' + title + '" >}}Answer.{{< /details >}}')

    def test_stage_symlink_cannot_redirect_writes_into_course(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / 'course'; output = root / 'stage'
            (repo / 'static').mkdir(parents=True); output.mkdir()
            original = repo / 'static' / 'existing.pdf'; original.write_bytes(b'preserve original')
            (output / 'static').symlink_to(repo / 'static', target_is_directory=True)
            with patch.object(assessment.materials, 'REPO', repo):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    assessment.process(repo / 'exam.md', output)
            self.assertEqual(original.read_bytes(), b'preserve original')
            self.assertEqual(list(output.iterdir()), [output / 'static'])

    def test_separate_levels_retain_separate_tex_and_log_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / 'course'; output = root / 'stage'
            (repo / '_materials').mkdir(parents=True); (output / '_materials').mkdir(parents=True)
            (repo / 'boulingua.yml').write_text('chrome_language: de\n')
            def compile_fixture(tex):
                tex.with_suffix('.pdf').write_bytes(tex.read_bytes())
                tex.with_suffix('.log').write_text(tex.read_text())
                return True, SimpleNamespace(stdout='', stderr='')
            def thumbnail_fixture(pdf, png):
                png.write_bytes(b'fixture thumbnail')
            with patch.object(assessment.materials, 'REPO', repo), patch.object(assessment.materials, 'SITE', 'daf'), patch.object(assessment.materials, 'MAT', output / '_materials'), patch.object(assessment.materials, 'xelatex', compile_fixture), patch.object(assessment.materials, 'thumb', thumbnail_fixture):
                records = []
                for level in ('A1', 'A2'):
                    source = repo / (level + '.md')
                    source.write_text('---\npage_type: exam\ntitle: ' + level + '\ncefr_level: ' + level + '\nunit_nr: 1\nunit_slug: introduction\n---\nPrompt for ' + level)
                    records.append(assessment.process(source, output))
                for role in ('learner', 'teacher'):
                    first, second = [r['outputs'][role] for r in records]
                    self.assertNotEqual(first['tex_file'], second['tex_file'])
                    self.assertNotEqual(first['log_file'], second['log_file'])
                    self.assertIn('Prompt for A1', (output / first['tex_file']).read_text())
                    self.assertNotIn('Prompt for A2', (output / first['tex_file']).read_text())
                    self.assertIn('Prompt for A2', (output / second['tex_file']).read_text())

    def test_changed_producer_is_not_relabelled_as_the_executed_code(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'producer.py'; source.write_text('original code')
            digest = assessment.hashlib.sha256(source.read_bytes()).hexdigest()
            with patch.object(assessment, 'CODE_PATHS', {'generator_sha256': source}), patch.object(assessment, 'CODE_HASHES', {'generator_sha256': digest}):
                assessment.verify_producer_identity()
                source.write_text('different code')
                with self.assertRaisesRegex(RuntimeError, 'changed after loading'):
                    assessment.verify_producer_identity()

    def test_reused_workspace_rejects_changed_or_tampered_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / 'course'; workspace = root / 'stage' / 'downloads' / 'a1'
            support = repo / '_materials'; support.mkdir(parents=True)
            style = support / 'worksheet.sty'; style.write_text('original style')
            with patch.object(assessment.materials, 'REPO', repo):
                assessment.prepare_workspace(workspace)
                assessment.prepare_workspace(workspace)
                style.write_text('revised style')
                with self.assertRaisesRegex(ValueError, 'support changed'):
                    assessment.prepare_workspace(workspace)
                self.assertEqual((workspace / 'worksheet.sty').read_text(), 'original style')
                style.write_text('original style')
                (workspace / 'worksheet.sty').write_text('tampered stage')
                with self.assertRaisesRegex(ValueError, 'workspace support changed'):
                    assessment.prepare_workspace(workspace)
                (workspace / 'worksheet.sty').write_text('original style')
                style.unlink()
                with self.assertRaisesRegex(ValueError, 'support changed'):
                    assessment.prepare_workspace(workspace)

    def test_unrecorded_existing_workspace_requires_fresh_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / 'course'; workspace = root / 'stage'
            (repo / '_materials').mkdir(parents=True); workspace.mkdir()
            (workspace / 'worksheet.sty').write_text('old style')
            with patch.object(assessment.materials, 'REPO', repo):
                with self.assertRaisesRegex(ValueError, 'fresh output root'):
                    assessment.prepare_workspace(workspace)
            self.assertEqual((workspace / 'worksheet.sty').read_text(), 'old style')


if __name__ == '__main__':
    unittest.main()
