import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_tokens import scan, COLOUR

class DesignGate(unittest.TestCase):
    def test_every_unapproved_literal_is_reported_at_its_actual_line(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'course.css'
            p.write_text('/* explanatory #abcdef */\n.a{color:#123456}\n.b{color:rgb(1,2,3)}\n.c{color:var(--ink)}\n')
            out=io.StringIO()
            with contextlib.redirect_stdout(out): n=scan([p],COLOUR,'colour','tokens.css')
            self.assertEqual(n,2)
            self.assertIn('line=2',out.getvalue());self.assertIn('line=3',out.getvalue())
            self.assertNotIn('line=4',out.getvalue())
    def test_clean_stylesheet_does_not_fail_merely_for_being_outside_kit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'course.css';p.write_text('.a{color:var(--ink)}\n')
            self.assertEqual(scan([p],COLOUR,'colour','tokens.css'),0)
