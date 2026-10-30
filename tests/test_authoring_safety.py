from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / 'scripts'))
import build_materials_latex as materials
from migrate_audio_manifests import link_manifest
from verify_i18n_chrome import audit
spec = importlib.util.spec_from_file_location('audio_build', KIT / 'audio/build_audio.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class SafeAuthoring(unittest.TestCase):
    def test_xelatex_failure_rejects_and_removes_stale_intermediate(self):
        with tempfile.TemporaryDirectory() as td, patch.object(materials, 'MAT', Path(td)):
            tex = Path(td) / 'unit.tex'; tex.write_text('broken')
            pdf = tex.with_suffix('.pdf'); pdf.write_bytes(b'old PDF')
            with patch.object(materials.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'error')):
                self.assertFalse(materials.xelatex(tex)[0])
            self.assertFalse(pdf.exists())

    def test_missing_glyph_is_failure_even_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as td, patch.object(materials, 'MAT', Path(td)):
            tex = Path(td) / 'unit.tex'; tex.write_text('source')
            def compile(*args, **kwargs):
                tex.with_suffix('.pdf').write_bytes(b'PDF with missing glyph')
                return subprocess.CompletedProcess([], 0, 'Missing character: no glyph', '')
            with patch.object(materials.subprocess, 'run', side_effect=compile):
                self.assertFalse(materials.xelatex(tex)[0])

    def test_course_labels_follow_declared_code_not_checkout_name(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'hugo.toml').write_text('[params]\ncode = "fle"\n'); (p/'boulingua.yml').write_text('code: fle\n')
            materials.configure(p)
            self.assertEqual(materials.L['obj'], 'Objectifs')
            sheet = materials.build_worksheet({}, [], '', 'Test', '', '')
            self.assertIn(r'\blgsetui{french}', sheet)

    def fixture(self, root):
        (root/'hugo.toml').write_text('[params]\ncode = "efl"\n')
        p=root/'content/units/lesson';p.mkdir(parents=True)
        (p/'index.md').write_text('---\npage_type: unit\nmaterial_slug: lesson\n---\nA lesson.\n')
        model=root/'voice.onnx';model.write_bytes(b'model fixture')
        Path(str(model)+'.json').write_text('{"num_speakers": 1}')
        data=root/'data/audio';data.mkdir(parents=True)
        out=root/'static/materials/audio/lesson';out.mkdir(parents=True)
        return data,out,model

    def test_human_recording_is_never_synthesized_or_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,out,model=self.fixture(root)
            human={'file':'/efl/materials/audio/lesson/texte1.ogg','label':'Reader','transcript':'Teacher recording','source':'human'}
            (data/'lesson.json').write_text(json.dumps([human]));(out/'texte1.ogg').write_bytes(b'human voice')
            with patch.object(audio,'extract_segments',return_value=[('texte','Changed extraction','Changed extraction')]), patch.object(audio,'synth') as synth:
                rc=audio.main([str(root),str(model),'en','content/units/*/index.md','--all'])
            self.assertEqual(rc,0);synth.assert_not_called()
            self.assertEqual((out/'texte1.ogg').read_bytes(),b'human voice')
            self.assertEqual(json.loads((data/'lesson.json').read_text()),[human])

    def test_failed_generation_preserves_published_audio_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data,out,model=self.fixture(root)
            before=json.dumps([{'file':'/efl/materials/audio/lesson/texte1.ogg','transcript':'Previous text'}])
            (data/'lesson.json').write_text(before);(out/'texte1.ogg').write_bytes(b'previous recording')
            with patch.object(audio,'extract_segments',return_value=[('texte','New text','New text')]), patch.object(audio,'synth',side_effect=RuntimeError('encoder unavailable')):
                rc=audio.main([str(root),str(model),'en','content/units/*/index.md','--all'])
            self.assertEqual(rc,1)
            self.assertEqual((out/'texte1.ogg').read_bytes(),b'previous recording')
            self.assertEqual((data/'lesson.json').read_text(),before)

    def test_audio_manifest_link_keeps_body_and_unrelated_front_matter(self):
        original='---\ntitle: "Keep: quotation"\n# Note\n---\nBody\n'
        updated=link_manifest(original,'unique-unit')
        self.assertEqual(updated,'---\ntitle: "Keep: quotation"\n# Note\naudio_manifest: unique-unit\n---\nBody\n')
        self.assertEqual(link_manifest(updated,'unique-unit'),updated)

    def test_inherited_keys_and_missing_site_language_are_checked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);kit=root/'kit';course=root/'course';course.mkdir();(kit/'layouts').mkdir(parents=True);(kit/'i18n').mkdir()
            (kit/'layouts/shared.html').write_text('{{ i18n "listen" }}')
            (kit/'i18n/en.yaml').write_text('listen: Listen\n')
            (course/'hugo.toml').write_text('defaultContentLanguage = "fr"\n')
            errors,keys,languages=audit(course,kit)
            self.assertEqual(keys,1);self.assertEqual(languages,{'fr'});self.assertTrue(errors)
            (kit/'i18n/fr.yaml').write_text('listen: Écouter\n')
            self.assertEqual(audit(course,kit)[0],[])


if __name__ == '__main__': unittest.main()
