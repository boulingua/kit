import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials

class MaterialEscapes(unittest.TestCase):
    def test_escaped_answer_gaps_print_underscores_without_backslashes(self):
        text=materials.inline(r'Der Beitrag sichert Unabhängigkeit; \_\_\_\_ empfinden ihn viele als ungerecht. *Begründen Sie.*')
        self.assertEqual(text.count(r'\_'),4)
        self.assertNotIn(r'\textbackslash',text)
        self.assertIn(r'\textit{Begründen Sie.}',text)

    def test_code_backslashes_remain_literal_beside_markdown_escapes(self):
        text=materials.inline(r'`C:\_temp` et \_\_.')
        self.assertIn(r'\texttt{C:\textbackslash{}\_temp}',text)
        self.assertEqual(text.count(r'\textbackslash'),1)
        self.assertEqual(text.count(r'\_'),3)

    def test_escaped_markup_characters_are_literal_not_formatting(self):
        text=materials.inline(r'\*literal\* et *italic*, \[choice\], \\.')
        self.assertIn('*literal*',text)
        self.assertIn(r'\textit{italic}',text)
        self.assertIn('[choice]',text)
        self.assertEqual(text.count(r'\textbackslash{}'),1)

    def test_code_emphasis_links_and_escaped_markers_remain_literal(self):
        for body in ['*value*','_value_',r'\*value\*','[label](https://example.org)']:
            result=materials.inline('`'+body+'`')
            self.assertEqual(result,r'\texttt{'+materials.esc(body)+'}')
        self.assertEqual(materials.inline('`` `value` ``'),r'\texttt{`value`}')
