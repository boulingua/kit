#!/usr/bin/env python3
"""C9: explicit analytics configuration, rendered scripts and matching public notices."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse
import argparse
import re
import tomllib
import yaml

HEAD_PARTIAL = Path(__file__).resolve().parents[1]/'layouts/_partials/head/extensions.html'
STATEMENTS = {
    'de': {'disabled':'Auf dieser Website ist Plausible Analytics deaktiviert.',
           'plausible':'Auf dieser Website ist Plausible Analytics aktiviert.'},
    'en': {'disabled':'Plausible Analytics is disabled on this website.',
           'plausible':'Plausible Analytics is enabled on this website.'},
    'fr': {'disabled':'Plausible Analytics est désactivé sur ce site.',
           'plausible':'Plausible Analytics est activé sur ce site.'},
}


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.scripts, self.text, self.inline = [], [], []
        self.stack, self.script, self.redirect = [], None, False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv','').lower() == 'refresh':
            self.redirect = True
        hidden = (bool(self.stack and self.stack[-1][1]) or tag in {'script','style','head','noscript'}
                  or 'hidden' in attrs or attrs.get('aria-hidden','').lower() == 'true'
                  or bool(re.search(r'(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\b',
                                    attrs.get('style',''),re.I)))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append((tag,hidden))
        if tag == 'script':
            self.scripts.append(attrs)
            self.script = [] if not attrs.get('src') else None

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.inline.append(''.join(self.script))
            self.script = None
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        if self.script is not None:
            self.script.append(text)
        if not self.stack or not self.stack[-1][1]:
            self.text.append(text)

    @property
    def visible(self):
        return ' '.join(' '.join(self.text).split())


def notice_files(repo):
    return sorted(p for p in (repo/'content').rglob('*.md')
                  if p.stem in {'privacy','datenschutz'} or
                  (p.name == 'index.md' and p.parent.name in {'privacy','datenschutz'}))


def audit(repo, built):
    errors = []
    config = tomllib.loads((repo/'hugo.toml').read_text())
    plausible = config.get('params',{}).get('plausible',{})
    if not isinstance(plausible,dict):
        return ['params.plausible must be a table'], {}
    domain, src = plausible.get('domain',''), plausible.get('src','')
    if not isinstance(domain,str) or not isinstance(src,str):
        return ['Plausible domain and src must be strings'], {}
    domain, src = domain.strip(), src.strip()
    active = bool(domain)
    policy = 'plausible' if active else 'disabled'
    if active and (not src or urlparse(src).scheme != 'https' or not urlparse(src).netloc):
        errors.append('enabled Plausible requires an explicit HTTPS script URL')
    if src and not active:
        errors.append('Plausible src without a domain must be removed or explicitly enabled')
    if plausible.get('enable') is False and active:
        errors.append('Plausible enable=false contradicts its enabled domain')
    if re.search(r'\s|://',domain):
        errors.append('Plausible domain must be the configured hostname/path identifier')
    if 'https://plausible.io/' in HEAD_PARTIAL.read_text():
        errors.append('shared head partial contains an implicit plausible.io endpoint fallback')
    pages = {}
    for path in sorted(built.rglob('*.html')):
        page = Page(path.read_text())
        pages[path.relative_to(built).as_posix()] = page
        if page.redirect and not page.scripts:
            continue
        trackers = [s for s in page.scripts if 'data-domain' in s or
                    (s.get('src') and (s['src'] == src or
                     'plausible' in urlparse(s['src']).netloc.lower() or
                     urlparse(s['src']).netloc.lower() == 'analytics.hellebo.de'))]
        label = path.relative_to(built).as_posix()
        if len(trackers) != int(active):
            errors.append(f'{label}: expected {int(active)} Plausible scripts, found {len(trackers)}')
        for script in trackers:
            if script.get('src') != src or script.get('data-domain') != domain:
                errors.append(f'{label}: analytics script URL/domain differs from configuration')
            if 'defer' not in script:
                errors.append(f'{label}: analytics script must defer execution')
        bootstraps = sum('plausible' in code for code in page.inline)
        if bootstraps > int(active):
            errors.append(f'{label}: unexpected or duplicate inline Plausible initialization')
    if not pages:
        errors.append('built output contains no HTML pages')
    notices = notice_files(repo)
    if not notices:
        errors.append('no privacy notice source found')
    for source in notices:
        label = source.relative_to(repo).as_posix()
        match = re.match(r'\A---\n(.*?)\n---(?:\n|$)',source.read_text(),re.S)
        front = yaml.safe_load(match[1]) if match else {}
        if not isinstance(front,dict):
            errors.append(f'{label}: invalid notice front matter'); continue
        if front.get('analytics_policy') != policy:
            errors.append(f'{label}: analytics_policy must be {policy}')
        language = front.get('analytics_notice_language')
        url = front.get('analytics_notice_path')
        if language not in STATEMENTS:
            errors.append(f'{label}: analytics_notice_language must be de, en or fr'); continue
        if not isinstance(url,str) or not url.startswith('/') or '..' in Path(url).parts or urlparse(url).netloc:
            errors.append(f'{label}: analytics_notice_path must be a site-relative page URL'); continue
        key = url.strip('/')+'/index.html' if not url.endswith('.html') else url.lstrip('/')
        page = pages.get(key)
        if page is None:
            errors.append(f'{label}: rendered notice missing at {key}'); continue
        text = page.visible
        if STATEMENTS[language][policy] not in text:
            errors.append(f'{label}: actual rendered notice does not state {policy}')
        opposite = 'disabled' if active else 'plausible'
        if STATEMENTS[language][opposite] in text:
            errors.append(f'{label}: rendered notice contains contradictory analytics states')
        if active and (src not in text or domain not in text):
            errors.append(f'{label}: rendered notice must name the actual script URL and domain identifier')
        if not active and re.search(r'(?:verwendet|nutzt|uses|utilise)\s+(?:die\s+)?Plausible Analytics|Reichweitenmessung mittels Plausible Analytics erfolgt',text,re.I):
            errors.append(f'{label}: rendered notice still claims active Plausible measurement')
    return errors, {'policy':policy,'pages':len(pages),'notices':len(notices)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('--built',type=Path,help='built HTML directory (default: REPO/public)')
    args = parser.parse_args()
    try:
        repo=args.repo.resolve()
        errors, stats = audit(repo,args.built.resolve() if args.built else repo/'public')
    except (OSError,ValueError,yaml.YAMLError) as exc:
        errors, stats = [str(exc)], {}
    for error in errors[:25]:
        print('::error::'+error)
    print(f'C9 {"FAIL" if errors else "OK"}: {stats}; {len(errors)} findings')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
