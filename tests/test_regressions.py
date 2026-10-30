"""Failure-path regressions for public build and authoring entry points."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from verify_eqs import check
from split_speaking import replace_block


class AuthoringTests(unittest.TestCase):
    def test_list_migration_preserves_unrelated_fields(self):
        for value in ['\n  - speaking\n  - reading', '\n- speaking\n- reading', ' [speaking, reading]']:
            with self.subTest(value=value):
                text = 'title: "Keep: this"\nskills_focus:' + value + '\n# Keep this note\nother:\n  tags: [a, b]\n'
                before = yaml.safe_load(text)
                after = replace_block(text, 'skills_focus', ['speaking_interaction', 'reading'])
                self.assertEqual(yaml.safe_load(after), {**before, 'skills_focus': ['speaking_interaction', 'reading']})
                self.assertIn('title: "Keep: this"', after)
                self.assertIn('# Keep this note', after)
                self.assertIn('other:\n  tags: [a, b]', after)

    def test_duplicate_field_refused(self):
        with self.assertRaises(ValueError):
            replace_block('skills_focus: [speaking]\nskills_focus: [reading]', 'skills_focus', ['writing'])


class RenderedContracts(unittest.TestCase):
    def test_minified_and_reordered_attributes_are_checked(self):
        for html in ['<span class=gap></span>', '<span class="extra gap" data-aria-label="fake"></span>', '<span aria-label=" " class=gap></span>', '<span class=tl data-lang=fr>Salut</span>', '<details class=extension><div>Task</div></details>', '<div class=extension><summary>Task</summary></div>', '<aside class=recycles><span class=recycles-unresolved data-unit=missing>missing</span></aside>']:
            with self.subTest(html=html):
                self.assertTrue(check(html, 'unit.html'))

    def test_accessible_components_survive_minification(self):
        html = '<span aria-label="Fill this gap" class="extra gap"></span><span lang=fr class=tl>Bonjour</span><details class=extension><summary>Try this</summary><p>Task</p></details>'
        self.assertEqual(check(html, 'unit.html'), [])

    def test_monolingual_vocab_still_declares_each_cell_language(self):
        html = '<table class=vocab><tr><th scope=col lang=de>Wort</th><th scope=col lang=de>Erklärung</th></tr><tr><td lang=de>Haus</td><td lang=de>Gebäude</td></tr></table>'
        self.assertEqual(check(html, 'unit.html'), [])
        self.assertTrue(check(html.replace('<td lang=de>', '<td>', 1), 'unit.html'))

    def test_rtl_island_requires_direction(self):
        self.assertTrue(check('<span class=tl lang=ar>مرحبا</span>', 'unit.html'))
        self.assertEqual(check('<span class=tl lang=ar dir=rtl>مرحبا</span>', 'unit.html'), [])


class EntryPoints(unittest.TestCase):
    def run_script(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)

    def test_enabled_search_cannot_pass_without_index(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_script('verify_pagefind.py', td)
            self.assertEqual(result.returncode, 1)
            self.assertIn('missing', result.stdout)

    def test_empty_build_cannot_pass_shortcode_check(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self.run_script('verify_eqs.py', td).returncode, 1)

    def test_one_valid_exam_does_not_hide_an_unmarked_exam(self):
        with tempfile.TemporaryDirectory() as td:
            content = Path(td) / 'content'
            content.mkdir()
            fm = '---\npage_type: exam\n---\n'
            (content / 'valid.md').write_text(fm + '**Total.** 2 points\n## Task (2 BE)\n0–0 | 6\n1–1 | 3\n2–2 | 1\n')
            (content / 'empty.md').write_text(fm + 'An exam without a marking scheme.\n')
            result = self.run_script('verify_assessment.py', td)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_thumbnail_failure_preserves_existing_cover(self):
        from render_thumbs import render_pdf
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf, png = root / 'bad.pdf', root / 'cover.png'
            pdf.write_bytes(b'not a PDF')
            png.write_bytes(b'previous cover')
            with self.assertRaises(Exception):
                render_pdf(pdf, png)
            self.assertEqual(png.read_bytes(), b'previous cover')


if __name__ == '__main__':
    unittest.main()
