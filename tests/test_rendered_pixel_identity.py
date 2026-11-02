"""Locked marks retain page identity independently of CI checkout names."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_rendered_pixels.py'
A = 'a' * 32
B = 'b' * 32


class RenderedPixelIdentity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'course'
        self.repo.mkdir()
        self.base('/efl/')

    def base(self, path):
        (self.repo / 'hugo.toml').write_text(f'baseURL="https://boulingua.github.io{path}"\n')

    def lock(self, *rows):
        path = self.repo / 'vgwort/url-lock-provisional.csv'
        path.parent.mkdir(exist_ok=True)
        path.write_text('url,code\n' + ''.join(f'{url},{code}\n' for url, code in rows))

    def page(self, path, code):
        dest = self.repo / 'public' / path.strip('/') / 'index.html'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f'<html><img src="https://vg00.met.vgwort.de/na/{code}"></html>')

    def check(self, expected=0, built_argument=False):
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.repo / 'public' if built_argument else self.repo)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_prefixed_lock_passes_in_renamed_checkout(self):
        self.lock(('/efl/lesson/', A), ('/efl/', B))
        self.page('/lesson/', A)
        self.page('/', B)
        self.check()
        self.check(built_argument=True)

    def test_existing_site_relative_lock_remains_valid(self):
        self.lock(('/lesson/', A), ('appendices/', B))
        self.page('/lesson/', A)
        self.page('/appendices/', B)
        self.check()

    def test_nested_and_root_publication_paths(self):
        for base in ['/teaching/efl/', '/']:
            with self.subTest(base=base):
                self.base(base)
                self.lock((base + 'lesson/', A))
                self.page('/lesson/', A)
                self.check()

    def test_prefix_is_whole_path_not_similar_name_or_checkout_name(self):
        self.page('/lesson/', A)
        for path in ['/efl-extra/lesson/', '/course/lesson/']:
            with self.subTest(path=path):
                self.lock((path, A))
                self.assertIn('but renders at', self.check(1))

    def test_missing_duplicate_and_wrong_page_still_fail(self):
        self.lock(('/efl/lesson/', A))
        self.page('/other/', B)
        self.assertIn('renders on NO page', self.check(1))
        self.page('/other/', A)
        self.assertIn('but renders at', self.check(1))
        self.page('/lesson/', A)
        self.assertIn('renders on 2 pages', self.check(1))

    def test_mixed_lock_modes_cannot_hide_moved_mark(self):
        self.lock(('/efl/lesson/', A), ('/appendices/', B))
        self.page('/lesson/', A)
        self.page('/appendices/', B)
        self.assertIn('but renders at', self.check(1))

    def test_invalid_declared_url_fails_closed(self):
        self.lock(('/efl/lesson/', A))
        self.page('/lesson/', A)
        for url in ['/efl/', 'https://boulingua.github.io/efl/?pretend=/course/',
                    'https://boulingua.github.io/efl/../course/']:
            with self.subTest(url=url):
                (self.repo / 'hugo.toml').write_text(f'baseURL="{url}"\n')
                self.assertIn('cannot resolve', self.check(2))


if __name__ == '__main__':
    unittest.main()
