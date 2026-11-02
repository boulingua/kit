from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials


class MaterialChrome(unittest.TestCase):
    def test_declared_instructional_language_keeps_the_actual_course_brand(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);(repo/'hugo.toml').write_text('[params]\ncode="nsf"\n')
            (repo/'boulingua.yml').write_text('code: nsf\nchrome_language: de\n')
            materials.configure(repo)
            self.assertEqual(materials.SITE,'nsf')
            self.assertEqual(materials.URL,'/nsf')
            self.assertEqual(materials.L['ui'],'german')
            (repo/'boulingua.yml').write_text('code: nsf\nchrome_language: xx\n')
            with self.assertRaisesRegex(ValueError,'chrome_language'):materials.configure(repo)

    def test_canonical_steps_keep_full_prose_and_teacher_boundaries(self):
        md='---\ntitle: Begegnung\n---\n## Unser Vorhaben {#mission}\nMISSIONCONTENT\n'
        for step in ['activate','input','practise','apply','reflect']:
            md+='## Beliebiger Titel {#'+step+'}\n'+step.upper()+'CONTENT\n'
        md+='## Antworten {#solutions}\nSECRETANSWER\n## Hinweise {#teacher-notes}\nTEACHERNOTES\n## Prüfung {#exam}\nEXAMPOINTER\n'
        fm,sections=materials.parse(md)
        with patch.object(materials,'SITE','nsf'),patch.object(materials,'L',materials.LABELS['de']):
            deck=materials.build_deck(fm,sections,'Begegnung','')
            learner=materials.build_worksheet(fm,sections,md,'Begegnung','','',False)
            teacher=materials.build_worksheet(fm,sections,md,'Begegnung','','',True)
            for marker in ['MISSIONCONTENT','ACTIVATECONTENT','INPUTCONTENT','PRACTISECONTENT','APPLYCONTENT','REFLECTCONTENT']:
                for output in [deck,learner,teacher]:self.assertIn(marker,output)
            for marker in ['SECRETANSWER','TEACHERNOTES']:
                self.assertNotIn(marker,deck+learner);self.assertEqual(teacher.count(marker),1)
            self.assertNotIn('EXAMPOINTER',deck+learner+teacher)
            missing=[s for s in sections if s[0].anchor!='reflect']
            with self.assertRaisesRegex(ValueError,'reflect'):materials.build_deck(fm,missing,'Begegnung','')
