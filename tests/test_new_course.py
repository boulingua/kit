from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from new_course import scaffold

class NewCourse(unittest.TestCase):
    def test_course_identity_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'ROADMAP.md').write_text('An authored plan\n')
            scaffold('nsf',root)
            cfg=tomllib.loads((root/'hugo.toml').read_text())
            self.assertEqual(cfg['params']['targetLanguage'],'nb')
            self.assertEqual(cfg['defaultContentLanguage'],'de')
            self.assertEqual((root/'ROADMAP.md').read_text(),'An authored plan\n')
            (root/'content/about.md').write_text('A custom course introduction\n')
            made,kept=scaffold('nsf',root)
            self.assertEqual(made,[])
            self.assertEqual((root/'content/about.md').read_text(),'A custom course introduction\n')

    def test_deferred_scripts_are_not_enabled_by_scaffolding(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);scaffold('afl',root)
            cfg=yaml.safe_load((root/'boulingua.yml').read_text())
            self.assertEqual(cfg['script_tier'],'core')
            self.assertEqual(cfg['target_language'],'ar')
            self.assertEqual(list((root/'content').rglob('unit*')),[])
            self.assertIn('Zielschrift',(root/'content/about.md').read_text())

    def test_latin_declares_the_actual_restricted_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);scaffold('lle',root)
            manifest=yaml.safe_load((root/'curriculum.yml').read_text())
            self.assertEqual(manifest['declared_conformance'],'core-restricted')
            self.assertEqual(manifest['profile'],'classical-reception')
            self.assertEqual(manifest['conformance_status'],'in-progress')
