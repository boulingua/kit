from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials


class MaterialStaging(unittest.TestCase):
    def test_overflowing_pdf_cannot_be_published_even_when_tex_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); tex=root/'lesson.tex';tex.write_text('oversized table fixture')
            def run(*args, **kwargs):
                tex.with_suffix('.pdf').write_bytes(b'overflowing compiled artifact')
                return SimpleNamespace(returncode=0,stdout='Overfull \\vbox (16.8pt too high) detected at line 123\n',stderr='')
            with patch.object(materials,'MAT',root),patch.object(materials.subprocess,'run',side_effect=run):
                good,result=materials.xelatex(tex)
            self.assertFalse(good)
            self.assertIn('Overfull',result.stderr)

    def test_staged_three_document_set_does_not_rewrite_the_course(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); repo=root/'course'; repo.mkdir()
            (repo/'hugo.toml').write_text('[params]\ncode="efl"\n')
            (repo/'boulingua.yml').write_text('code: efl\n')
            (repo/'_materials').mkdir()
            unit=repo/'content/units/lesson/index.md'; unit.parent.mkdir(parents=True)
            source='---\ntitle: Lesson\nmaterial_slug: lesson\n---\n## Practise\nTask\n'
            unit.write_text(source)
            materials.configure(repo,root/'staging')
            def compile(tex):
                tex.with_suffix('.pdf').write_bytes(b'compiled test fixture')
                return True,None
            def thumbnail(pdf,png):png.write_bytes(b'thumbnail test fixture')
            with patch.object(materials,'xelatex',side_effect=compile),patch.object(materials,'thumb',side_effect=thumbnail):
                result=materials.process(unit)
            self.assertTrue(result['deck'] and result['sheet'] and result['teacher'])
            self.assertEqual(unit.read_text(),source)
            self.assertFalse((repo/'static').exists())
            self.assertTrue((root/'staging/static/materials/worksheets/lesson-teacher.pdf').is_file())
            self.assertEqual(len(result['files']),3)

    def test_publication_adds_teacher_link_without_changing_lesson_body(self):
        with tempfile.TemporaryDirectory() as td:
            unit=Path(td)/'index.md'; original='---\ntitle: Keep\n---\nOriginal authored body.\n'
            unit.write_text(original)
            with patch.object(materials,'URL','/efl'):materials.upsert_fm(unit,'lesson')
            self.assertEqual(materials.parse(unit.read_text())[0]['worksheet_teacher']['file'],
                             '/efl/materials/worksheets/lesson-teacher.pdf')
            self.assertTrue(unit.read_text().endswith('---\nOriginal authored body.\n'))

    def test_teacher_compile_failure_preserves_the_entire_published_set(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            (repo/'hugo.toml').write_text('[params]\ncode="efl"\n')
            (repo/'boulingua.yml').write_text('code: efl\n'); (repo/'_materials').mkdir()
            unit=repo/'content/units/lesson/index.md'; unit.parent.mkdir(parents=True)
            source='---\ntitle: Lesson\nmaterial_slug: lesson\n---\n## Practise\nTask\n';unit.write_text(source)
            outputs=[repo/'static/materials/presentations/lesson.pdf',repo/'static/materials/worksheets/lesson.pdf',repo/'static/materials/worksheets/lesson-teacher.pdf']
            for p in outputs:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'previous published artifact')
            materials.configure(repo)
            def compile(tex):
                tex.with_suffix('.pdf').write_bytes(b'new intermediate')
                return not tex.stem.endswith('-teacher'),SimpleNamespace(stdout='',stderr='teacher compile failure')
            with patch.object(materials,'xelatex',side_effect=compile),patch.object(materials,'thumb') as thumb:
                result=materials.process(unit)
            self.assertFalse(result['teacher']);thumb.assert_not_called()
            self.assertEqual(unit.read_text(),source)
            for p in outputs:self.assertEqual(p.read_bytes(),b'previous published artifact')
