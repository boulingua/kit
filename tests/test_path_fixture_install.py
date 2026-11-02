from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]


class StandalonePathFixtures(unittest.TestCase):
    def test_default_command_runs_without_sibling_checkouts_and_does_not_skip_missing_fixtures(self):
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td) / 'kit'
            (isolated / 'scripts').mkdir(parents=True)
            for name in ['test_blg_paths.py', 'blg_paths.py']:
                shutil.copyfile(KIT / 'scripts' / name, isolated / 'scripts' / name)
            shutil.copytree(KIT / 'tests/fixtures/paths', isolated / 'tests/fixtures/paths')
            command = [sys.executable, 'scripts/test_blg_paths.py']
            run = subprocess.run(command, cwd=isolated, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('Live URL/material integration not requested', run.stdout)
            shutil.rmtree(isolated / 'tests/fixtures/paths/fle')
            broken = subprocess.run(command, cwd=isolated, capture_output=True, text=True)
            self.assertEqual(broken.returncode, 1)
            self.assertIn('required fixture', broken.stdout)

    def test_explicit_missing_live_checkout_fails(self):
        with tempfile.TemporaryDirectory() as td:
            run=subprocess.run([sys.executable, str(KIT/'scripts/test_blg_paths.py'),
                                '--org-root',td,'efl'],capture_output=True,text=True)
            self.assertEqual(run.returncode,2)
            self.assertIn('missing integration checkout',run.stderr)
