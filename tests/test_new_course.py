from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
import json
import hashlib
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
            self.assertEqual(cfg['params']['plausible'],{'domain':'','src':''})
            notice=(root/'content/datenschutz.md').read_text()
            self.assertIn('analytics_policy: disabled',notice)
            self.assertIn('Auf dieser Website ist Plausible Analytics deaktiviert.',notice)
            self.assertNotIn('Diese Website verwendet **Plausible Analytics**',notice)
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

    def test_supplied_release_keeps_caller_module_framework_and_checksums_together(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);dest=root/'course';commit='a'*40
            caller='jobs:\n  course:\n    uses: boulingua/.github/.github/workflows/course-build.yml@'+commit+'\n    with:\n      org_ref: '+commit+'\n'
            schema=json.dumps({'type':'object','required':['framework_version'],'properties':{'framework_version':{'const':'1.4.0'}}})
            release={'schema_version':1,'state':'published','org':{'repository':'boulingua/.github','commit':commit},'kit':{'repository':'boulingua/kit','commit':'b'*40,'version':'2.3.0'},'curriculum':{'repository':'boulingua/curriculum','commit':'c'*40,'version':'1.4.0'},'curriculum_schema_sha256':hashlib.sha256(schema.encode()).hexdigest(),'curriculum_schema_text':schema,'go_version':'1.27.2','caller':caller,'caller_sha256':hashlib.sha256(caller.encode()).hexdigest(),'kit_sum':'h1:'+'A'*43+'=','kit_go_mod_sum':'h1:'+'A'*43+'='}
            path=root/'release.json';path.write_text(json.dumps(release));scaffold('nsf',dest,path)
            valid=json.loads(json.dumps(release))
            self.assertIn('kit/v2 v2.3.0',(dest/'go.mod').read_text())
            self.assertIn('go 1.27.2',(dest/'go.mod').read_text())
            self.assertEqual(tomllib.loads((dest/'hugo.toml').read_text())['params']['navTitle'],'Norwegisch (Bokmål)')
            self.assertEqual(yaml.safe_load((dest/'curriculum.yml').read_text())['framework_version'],'1.4.0')
            self.assertEqual((dest/'.github/workflows/deploy.yml').read_text(),caller)
            self.assertIn('v2.3.0/go.mod h1:'+'A'*43+'=',(dest/'go.sum').read_text())
            release['caller']+='tampered';path.write_text(json.dumps(release))
            with self.assertRaisesRegex(ValueError,'digest'):scaffold('nsf',root/'invalid',path)
            self.assertFalse((root/'invalid').exists())
            release['caller']=caller;release['curriculum_schema_text']='{}';path.write_text(json.dumps(release))
            with self.assertRaisesRegex(ValueError,'schema digest'):scaffold('nsf',root/'invalid-schema',path)
            self.assertFalse((root/'invalid-schema').exists())
            for field in ['go_version','kit_sum','kit_go_mod_sum','kit.commit','curriculum.repository']:
                broken=json.loads(json.dumps(valid))
                if '.' in field:
                    parent,key=field.split('.');del broken[parent][key]
                else:del broken[field]
                path.write_text(json.dumps(broken));output=root/('missing-'+field)
                with self.assertRaises(ValueError):scaffold('nsf',output,path)
                self.assertFalse(output.exists())
