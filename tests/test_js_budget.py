from pathlib import Path
import random
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_js_budget import audit

class ScriptBudget(unittest.TestCase):
    def fixture(self, root, *, lazy=True):
        (root/'graph').mkdir();(root/'js').mkdir()
        (root/'js/main.js').write_text('console.log("cards work");')
        (root/'js/vendor.js').write_bytes(random.Random(42).randbytes(110000))
        vendor='data-module-url="/course/js/vendor.js"' if lazy else ''
        eager='' if lazy else '<script src=/course/js/vendor.js></script>'
        (root/'graph/index.html').write_text(f'<div id=network-graph {vendor}></div><script src=/course/js/main.js></script>{eager}')
    def test_missing_build_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:self.assertTrue(audit(Path(td),'https://test/course/')[0])
    def test_eager_vendor_breaks_budget_but_lazy_does_not(self):
        for lazy in (True,False):
            with self.subTest(lazy=lazy),tempfile.TemporaryDirectory() as td:
                root=Path(td);self.fixture(root,lazy=lazy)
                errors,rows=audit(root,'https://test/course/')
                self.assertEqual(bool(errors),not lazy)
                self.assertGreater(rows[0]['total_gzip'],110000)
    def test_missing_lazy_asset_and_external_asset_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root)
            (root/'js/vendor.js').unlink()
            self.assertIn('missing script',audit(root,'https://test/course/')[0][0])
            p=root/'graph/index.html';p.write_text(p.read_text().replace('/course/js/vendor.js','https://cdn.test/vendor.js'))
            self.assertIn('external script',audit(root,'https://test/course/')[0][0])

    def test_only_declared_telemetry_is_separately_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root)
            page=root/'graph/index.html'
            url='https://analytics.test/script.js'
            page.write_text(page.read_text()+f'<script src="{url}" data-domain="course.test"></script>')
            self.assertTrue(audit(root,'https://test/course/')[0])
            errors,rows=audit(root,'https://test/course/',{url})
            self.assertEqual(errors,[])
            self.assertEqual(rows[0]['telemetry_outside_graph_budget'],[url])
