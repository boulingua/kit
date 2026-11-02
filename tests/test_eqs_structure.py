from pathlib import Path
import sys
import tempfile
import unittest
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_eqs_structure as eqs

class EqsStructure(unittest.TestCase):
    def test_word_budget_excludes_keys_and_teacher_sections(self):
        body='''## Activer {#activate}
L’enfant relit vingt-et-un mots.
## Apporter {#input}
[Lire ici](https://example.test) ![Une image](image.png)
{{< details summary="Solutions" >}}
These answers must never increase the learner budget.
{{< /details >}}
## S’entraîner {#practise}
| Word | Gloss |
| --- | --- |
| cat | chat |
## Produire {#apply}
Write.
## Réfléchir {#reflect}
Review.
## Teacher notes {#teacher-notes}
These notes must not count either.
'''
        self.assertEqual(eqs.word_count(body),19)
        self.assertNotIn('answers',eqs.plain_text(eqs.learner_body(body)))
    def test_source_and_rendered_structure_cannot_pass_on_declarations_alone(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d);unit=repo/'content/course/units/hello/index.md';exam=repo/'content/course/units/hello-exam/index.md'
            unit.parent.mkdir(parents=True);exam.parent.mkdir(parents=True)
            fm={'page_type':'unit','steps':eqs.KEYS,'curriculum':{'level':'A1'},'anchor_aliases':{'apply':['old-produce']},'exam':{'page':'course/units/hello-exam','format':'written','duration_minutes':20,'points':10,'skills':['reading']}}
            body='\n'.join('## '+k+' {#'+k+'}\nDo something useful.' for k in eqs.KEYS)
            unit.write_text('---\n'+yaml.safe_dump(fm)+'---\n'+body)
            exam.write_text('---\npage_type: exam\n---\nRead and answer.')
            for leaf,text in [('hello',''.join('<h2 id="'+k+'">'+k+'</h2>' for k in eqs.KEYS)+'<span id="old-produce"></span>'),('hello-exam','Read and answer. <details data-role="key">SECRET</details>')]:
                output=repo/'public/course/units'/leaf/'index.html';output.parent.mkdir(parents=True);output.write_text('<article>'+text+'</article>')
            spec={'assessment':{'pointer_fields':['page','format','duration_minutes','points','skills']},'bands':{'I':{'levels':['A1'],'klassenstufen':[5,6,7],'unit_words':{'minimum':1,'maximum':100},'exam_characters':{'minimum':10}}}}
            self.assertEqual(eqs.audit(repo,spec)[0]['findings'],[])
            self.assertEqual(eqs.audit(repo,spec)[0]['exam_characters'],16)
            unit.write_text(unit.read_text().replace('{#apply}','{#other}'))
            findings=eqs.audit(repo,spec)[0]['findings']
            self.assertTrue(any('keyed H2' in f for f in findings))
            p=repo/'public/course/units/hello/index.html';p.write_text(p.read_text().replace('old-produce','wrong-target'))
            self.assertTrue(any('legacy fragment' in f for f in eqs.audit(repo,spec)[0]['findings']))
    def test_exam_pointer_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(eqs.exam_path(Path(d),'../../outside'))
            self.assertIsNone(eqs.exam_path(Path(d),'/outside'))
    def test_exam_character_budget_excludes_teacher_sections_and_heading_controls(self):
        tree=eqs.parse('<article><h2 id="task">Read<a class="heading-link">#</a></h2><p>The text.</p><details data-role="key">Secret.</details><h2 id="teacher-notes">Teacher notes</h2><p>Long private guidance.</p><h2 id="sources">Sources</h2><p>Citation.</p></article>')
        self.assertEqual(' '.join(eqs.rendered_text(tree).split()),'Read The text.')
    def test_band_follows_school_year_before_level(self):
        spec={'bands':{'I':{'levels':['A1'],'klassenstufen':[5]},'III':{'levels':['C1'],'klassenstufen':[11]}}}
        self.assertEqual(eqs.band({'klassenstufe':11,'curriculum':{'level':'A1'}},spec),'III')
if __name__=='__main__':unittest.main()
