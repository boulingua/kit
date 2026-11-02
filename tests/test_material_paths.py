from pathlib import Path
import tempfile,sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_materials_latex as materials

class MaterialPaths(unittest.TestCase):
    def course(self, root):
        repo=root/'course';repo.mkdir();(repo/'hugo.toml').write_text('[params]\ncode="efl"\n');(repo/'boulingua.yml').write_text('code: efl\n');(repo/'_materials').mkdir();return repo
    def unit(self, repo, name, slug):
        import json
        source=repo/'content/units'/name/'index.md';source.parent.mkdir(parents=True)
        source.write_text('---\ntitle: '+name+'\nmaterial_slug: '+json.dumps(str(slug))+'\npresentation:\n  file: /efl/materials/presentations/example.pdf\n---\n## Practise\nRetained task.\n');return source
    def test_existing_stage_symlink_is_rejected_before_live_files_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();repo=self.course(root);out=root/'stage';out.mkdir();(repo/'static').mkdir();original=repo/'static/preserve.pdf';original.write_bytes(b'original');(out/'static').symlink_to(repo/'static',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):materials.configure(repo,out)
            self.assertEqual(original.read_bytes(),b'original');self.assertFalse((out/'_materials').exists())
    def test_unsafe_slugs_fail_cli_before_creating_any_stage(self):
        for slug in ('../escape','/absolute','nested/file','.'):
            with self.subTest(slug=slug),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();repo=self.course(root);source=self.unit(repo,'lesson',slug);before=source.read_bytes();out=root/'stage'
                with patch.object(sys,'argv',['build_materials_latex.py',str(repo),'--output-root',str(out)]),patch.object(materials.shutil,'which',return_value='xelatex'):
                    self.assertEqual(materials.main(),2)
                self.assertFalse(out.exists());self.assertEqual(source.read_bytes(),before)
    def test_duplicate_and_teacher_collision_fail_before_any_stage_write(self):
        for second in ('lesson','lesson-teacher'):
            with self.subTest(second=second),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();repo=self.course(root);self.unit(repo,'first','lesson');self.unit(repo,'second',second);out=root/'stage'
                with patch.object(sys,'argv',['build_materials_latex.py',str(repo),'--only','first','--output-root',str(out)]),patch.object(materials.shutil,'which',return_value='xelatex'):
                    self.assertEqual(materials.main(),2)
                self.assertFalse(out.exists())
    def test_live_output_leaf_symlink_is_rejected_before_compilation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();repo=self.course(root);source=self.unit(repo,'lesson','lesson');outside=root/'external.pdf';outside.write_bytes(b'preserve');target=repo/'static/materials/presentations/lesson.pdf';target.parent.mkdir(parents=True);target.symlink_to(outside);materials.configure(repo)
            with patch.object(materials,'xelatex') as compiler:
                with self.assertRaises(ValueError):materials.process(source)
                compiler.assert_not_called()
            self.assertEqual(outside.read_bytes(),b'preserve')
    def test_valid_existing_slugs_keep_exact_names(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();repo=self.course(root);source=self.unit(repo,'lesson','track-e_kl05_unit01-hello-world')
            self.assertEqual(materials.unit_slug(source,source.read_text()),'track-e_kl05_unit01-hello-world')
            self.assertEqual(len(materials.preflight_material_targets([source])),6)

    def test_changed_producer_cannot_publish_or_relabel_loaded_code(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();repo=self.course(root);source=self.unit(repo,'lesson','lesson');out=root/'stage'
            producer=root/'producer.py';producer.write_text('original producer')
            digest=materials.hashlib.sha256(producer.read_bytes()).hexdigest()
            with patch.object(materials,'PRODUCER_PATH',producer),patch.object(materials,'PRODUCER_SHA256',digest):
                materials.configure(repo,out)
                def compile_fixture(tex):
                    tex.with_suffix('.pdf').write_bytes(b'compiled intermediate')
                    producer.write_text('different producer')
                    return True,SimpleNamespace(stdout='',stderr='')
                with patch.object(materials,'xelatex',compile_fixture),patch.object(materials,'thumb') as thumbnail:
                    with self.assertRaisesRegex(RuntimeError,'changed after loading'):
                        materials.process(source)
                    thumbnail.assert_not_called()
                self.assertFalse((out/'static').exists())
                with self.assertRaisesRegex(RuntimeError,'changed after loading'):
                    materials.process(source)
