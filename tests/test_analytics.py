from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_analytics as gate

SRC='https://analytics.hellebo.de/js/script.file-downloads.outbound-links.js'
DOMAIN='boulingua.github.io/fixture'


class AnalyticsContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)/'repo';self.built=Path(self.temp.name)/'built'
        (self.repo/'content').mkdir(parents=True);(self.built/'privacy').mkdir(parents=True)

    def fixture(self,active=True,script=None,text=None):
        domain,src=(DOMAIN,SRC) if active else ('','')
        (self.repo/'hugo.toml').write_text(f'[params.plausible]\ndomain="{domain}"\nsrc="{src}"\n')
        policy='plausible' if active else 'disabled'
        front={'title':'Privacy','analytics_policy':policy,'analytics_notice_language':'en',
               'analytics_notice_path':'/privacy/'}
        (self.repo/'content/privacy.md').write_text('---\n'+yaml.safe_dump(front)+'---\n')
        if script is None:script=f'<script defer data-domain="{domain}" src="{src}"></script>' if active else ''
        if text is None:text=gate.STATEMENTS['en'][policy]+(f' {SRC} {DOMAIN}' if active else '')
        html=f'<html><head>{script}</head><body><main><p>{text}</p></main></body></html>'
        (self.built/'index.html').write_text(html)
        (self.built/'privacy/index.html').write_text(html)

    def test_enabled_and_disabled_outputs_match_their_visible_notices(self):
        for active in (True,False):
            with self.subTest(active=active):
                self.fixture(active);self.assertEqual(gate.audit(self.repo,self.built)[0],[])

    def test_missing_duplicate_or_mismatched_tracker_is_rejected(self):
        correct=f'<script defer data-domain="{DOMAIN}" src="{SRC}"></script>'
        for script in ['',correct*2,correct.replace(DOMAIN,'wrong-domain'),
                       correct.replace(SRC,'https://plausible.io/js/script.js')]:
            with self.subTest(script=script):
                self.fixture(script=script);self.assertTrue(gate.audit(self.repo,self.built)[0])

    def test_declaration_without_actual_statement_or_endpoint_is_rejected(self):
        for text in ['Generic privacy notice.',gate.STATEMENTS['en']['plausible'],
                     '<script>'+gate.STATEMENTS['en']['plausible']+'</script> '+SRC+' '+DOMAIN]:
            with self.subTest(text=text):
                self.fixture(text=text);self.assertTrue(gate.audit(self.repo,self.built)[0])

    def test_disabled_notice_cannot_keep_active_scripts_or_old_claims(self):
        self.fixture(False,script=f'<script defer data-domain="{DOMAIN}" src="{SRC}"></script>')
        self.assertTrue(gate.audit(self.repo,self.built)[0])
        self.fixture(False,text=gate.STATEMENTS['en']['disabled']+' This site uses Plausible Analytics.')
        self.assertTrue(gate.audit(self.repo,self.built)[0])

    def test_hidden_statements_do_not_satisfy_public_notice(self):
        for attribute in ['hidden','style="display:none"','style="visibility:hidden"','aria-hidden="true"']:
            with self.subTest(attribute=attribute):
                text=f'<div {attribute}><p>{gate.STATEMENTS["en"]["plausible"]}</p></div> {SRC} {DOMAIN}'
                self.fixture(text=text)
                self.assertTrue(any('actual rendered notice' in e for e in gate.audit(self.repo,self.built)[0]))

    def test_enabled_domain_cannot_silently_choose_a_default_endpoint(self):
        self.fixture()
        (self.repo/'hugo.toml').write_text(f'[params.plausible]\ndomain="{DOMAIN}"\n')
        self.assertTrue(any('explicit HTTPS' in e for e in gate.audit(self.repo,self.built)[0]))
        self.fixture()
        partial=self.repo/'head.html';partial.write_text('{{ or $p.src "https://plausible.io/js/script.js" }}')
        with patch.object(gate,'HEAD_PARTIAL',partial):
            self.assertTrue(any('fallback' in e for e in gate.audit(self.repo,self.built)[0]))

    def test_redirects_are_not_mistaken_for_content_pages(self):
        self.fixture()
        (self.built/'old.html').write_text('<html><head><meta http-equiv="refresh" content="0; url=/"></head></html>')
        self.assertEqual(gate.audit(self.repo,self.built)[0],[])


if __name__=='__main__':unittest.main()
