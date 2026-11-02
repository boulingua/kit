from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials

class MaterialLinksAndUnicode(unittest.TestCase):
    def render(self, code, body, teacher=False):
        fm,sections=materials.parse(body)
        with patch.object(materials,'SITE',code),patch.object(materials,'L',materials.LABELS['de']):
            return materials.build_worksheet(fm,sections,body,fm['title'],'','',teacher)

    def test_core_instruction_keeps_clickable_destination_and_visible_address(self):
        body='---\ntitle: Quellen vergleichen\n---\n## Input {#input}\nVergleichen Sie [Rundfunkbeitrag](https://de.wikipedia.org/wiki/Rundfunkbeitrag).\n## Üben {#practise}\nNennen Sie einen Unterschied.\n## Anwenden {#apply}\nBegründen Sie Ihre Auswahl.\n'
        result=self.render('daf',body)
        self.assertIn(r'\href{https://de.wikipedia.org/wiki/Rundfunkbeitrag}',result)
        self.assertIn(r'h\allowbreak{}t\allowbreak{}t\allowbreak{}p',result)

    def test_canonical_instruction_and_teacher_link_have_distinct_audiences(self):
        body='---\ntitle: Begegnung\n---\n'
        for name in ['activate','input','practise','apply','reflect']:
            body+='## Schritt {#'+name+'}\n'+('[Aussprache](https://www.ntnu.edu/learnnow/1/pronunciation)' if name=='input' else 'Eine Aufgabe.')+'\n'
        body+='## Schlüssel {#key}\n[Lehrhinweis](https://example.org/teacher)\n'
        learner=self.render('nsf',body);teacher=self.render('nsf',body,True)
        self.assertIn(r'\href{https://www.ntnu.edu/learnnow/1/pronunciation}',learner)
        self.assertNotIn('https://example.org/teacher',learner)
        self.assertIn(r'\href{https://example.org/teacher}',teacher)

    def test_greek_codepoints_have_actualtext_and_keys_stay_hidden(self):
        body='---\ntitle: Γεια σου\n---\n## Input {#input}\nClassez les quatre étapes.\n## Üben {#practise}\n(α) Fin. (β) Début. (γ) Suite. (δ) Changement.\n## Anwenden {#apply}\nExpliquez votre classement.\n## Solutions\n{{< details role="key" title="Réponses" >}}\nγ → β → δ → α\n{{< /details >}}\n'
        learner=self.render('fle',body);teacher=self.render('fle',body,True)
        for char in 'Γαβγδ':
            marker=r'\blggreek{'+char.encode('utf-16-be').hex().upper()+'}{'+char+'}'
            self.assertIn(marker,learner)
        self.assertEqual(learner.count(r'\newcommand{\blggreek}'),1)
        order=' → '.join(r'\blggreek{'+c.encode('utf-16-be').hex().upper()+'}{'+c+'}' for c in 'γβδα')
        self.assertNotIn(order,learner);self.assertIn(order,teacher)
        self.assertNotIn('XeTeXgenerateactualtext',learner)
        plain='---\ntitle: Hello\n---\n## Input\nA simple source.\n'
        self.assertNotIn('blggreek',self.render('efl',plain))


    def test_answer_blank_runs_do_not_become_cross_gap_emphasis(self):
        rendered=materials.inline('I __________ ten years old. We __________ in Klasse 5e. _Listen carefully_.')
        self.assertEqual(rendered.count(r'\_'),20)
        self.assertNotIn(r'\textit{ ten years old.',rendered)
        self.assertIn(r'\textit{Listen carefully}',rendered)

    def test_blockquoted_forms_and_tables_keep_their_structure(self):
        form='> **Anmeldung — Stadt Graz**\n>\n> - Familienname: _________________\n> - Vorname(n): _________________\n> - Geburtsdatum: _________________\n'
        rendered=materials.text_blocks(form)
        self.assertEqual(rendered.count(r'\item '),3)
        self.assertEqual(rendered.count(r'\_'),51)
        self.assertNotIn(r'\textit{',rendered)
        self.assertIn(r'\begin{tabularx}',materials.text_blocks('> | Champ | Valeur |\n> |---|---|\n> | Nom | ______ |'))


    def test_printable_checklist_controls_remain_separate_from_text(self):
        result=materials.text_blocks('- [ ] Beide fragen nach.\n- [x] Eine Position ist begründet.\n- [X] Gemeinsame Einigung.')
        self.assertIn(r'\item[{[ ]}] Beide fragen nach.',result)
        self.assertIn(r'\item[{[x]}] Eine Position ist begründet.',result)
        self.assertIn(r'\item[{[X]}] Gemeinsame Einigung.',result)


    def test_authored_pictograms_keep_exact_unicode_without_text_font_glyphs(self):
        for char in materials.AUTHORED_SYMBOLS:
            rendered=materials.inline(char)
            self.assertIn(r'\blgauthoredsymbol{'+char.encode('utf-16-be').hex().upper()+'}',rendered)
            self.assertNotIn(char,rendered)
        source=r'\begin{document}'+materials.inline('🙁')+r'\end{document}'
        self.assertIn(r'\newcommand{\blgauthoredsymbol}',materials.finish_document(source))
        self.assertNotIn('blgauthoredsymbol',materials.finish_document(r'\begin{document}Ordinary text.\end{document}'))


    def test_numbered_checklists_keep_both_number_and_control(self):
        result=materials.text_blocks('1. [ ] Première réponse.\n2. [x] Deuxième réponse.')
        self.assertIn(r'\item[{1.\ [ ]}] Première réponse.',result)
        self.assertIn(r'\item[{2.\ [x]}] Deuxième réponse.',result)

    def test_symbol_frame_title_uses_exact_authored_character(self):
        result=materials.flow_frame('🎂 Anniversaire','Texte.')
        self.assertIn(r'\blgauthoredsymbol{D83CDF82}',result)
        self.assertIn(r'\interlinepenalty=0',result)
        self.assertIn(r'\widowpenalty=0',result)


    def test_authored_objective_lists_can_continue_to_another_slide(self):
        result=materials.frame('Lernziele',materials.itemize(['Langes Lernziel.']*7))
        self.assertIn('[allowframebreaks=0.8,t]',result)
        self.assertEqual(result.count(r'\item '),7)
        self.assertIn(r'\interlinepenalty=0',result)

if __name__=='__main__':unittest.main()
