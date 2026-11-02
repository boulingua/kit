from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_materials_latex as materials


class MaterialReferences(unittest.TestCase):
    def test_attribution_and_real_destination_are_kept_in_each_variant(self):
        md='---\ntitle: Citation\n---\n## Input\nRead the attributed passage.\n## Sources\n- Adapted from Wikipedia, CC BY-SA: [Original article](https://example.org/Article_(topic)).\n'
        fm,secs=materials.parse(md)
        with patch.object(materials,'SITE','efl'),patch.object(materials,'L',materials.LABELS['en']):
            variants=[materials.build_deck(fm,secs,'Citation','')]
            variants.extend(materials.build_worksheet(fm,secs,md,'Citation','','',teacher) for teacher in (False,True))
        for variant in variants:
            self.assertIn('Adapted from Wikipedia, CC BY-SA',variant)
            self.assertIn(r'\href{https://example.org/Article\_(topic)}',variant)
            self.assertIn(r'\allowbreak{}',variant)
            self.assertNotIn('BOULINGUAREFERENCEURL',variant)

    def test_percent_query_fragment_and_bare_addresses_keep_their_destination(self):
        source='[Article](https://example.org/a_(b)?q=a%20b&x=1#part_2)\n\nOfficial: <https://example.org/official>.\n\nSee https://example.org/plain.'
        result=materials.reference_blocks(source)
        self.assertIn(r'\href{https://example.org/a\_(b)?q=a\%20b\&x=1\#part\_2}',result)
        self.assertIn(r'\href{https://example.org/official}',result)
        self.assertIn(r'\href{https://example.org/plain}',result)
        self.assertNotIn(r'\href{https://example.org/plain.}',result)

    def test_incomplete_destination_fails_instead_of_silent_truncation(self):
        with self.assertRaisesRegex(ValueError,'unclosed source link'):
            materials.reference_blocks('[Broken](https://example.org/path_(topic)')
