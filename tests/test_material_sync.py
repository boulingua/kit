from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest
KIT=Path(__file__).resolve().parents[1]

class MaterialSync(unittest.TestCase):
    def run_sync(self,root):
        return subprocess.run([sys.executable,str(KIT/'bin/kit'),'sync',str(root)],capture_output=True,text=True)
    def snapshot(self,root):
        return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    def test_edited_and_untracked_authoring_files_block_all_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'boulingua.yml').write_text('script_tier: core\n')
            self.assertEqual(self.run_sync(root).returncode,0)
            (root/'_materials/notes.tex').write_text('Unpublished teacher work\n')
            style=next((root/'_materials').glob('*.sty'));style.write_text(style.read_text()+'% Local change\n')
            before=self.snapshot(root)
            result=self.run_sync(root)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertIn('untracked material',result.stdout+result.stderr);self.assertIn('edited material',result.stdout+result.stderr)
            self.assertEqual(self.snapshot(root),before)
    def test_clean_sync_is_byte_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'boulingua.yml').write_text('script_tier: latin-ext\n')
            self.assertEqual(self.run_sync(root).returncode,0)
            before=self.snapshot(root)
            self.assertEqual(self.run_sync(root).returncode,0)
            self.assertEqual(self.snapshot(root),before)
