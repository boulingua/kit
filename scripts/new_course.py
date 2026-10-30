#!/usr/bin/env python3
"""Create an honest, buildable development site without overwriting authored files."""
from pathlib import Path
import argparse
import shutil
import yaml

KIT = Path(__file__).resolve().parents[1]


def scaffold(code, destination):
    courses = yaml.safe_load((KIT/'data/courses.yml').read_text())
    if code not in courses: raise ValueError(f'unknown course code: {code}')
    meta = courses[code]; name = meta['name']; lang = meta['language']; tier = meta['tier']
    dest = Path(destination).resolve(); dest.mkdir(parents=True, exist_ok=True)
    written, kept = [], []
    def put(relative, text):
        p = dest / relative
        if p.exists(): kept.append(relative); return
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text.rstrip() + '\n', encoding='utf-8'); written.append(relative)
    def page(relative, title, body, **front):
        put('content/'+relative, '---\n'+yaml.safe_dump({'title': title, 'page_type': 'section', **front}, allow_unicode=True, sort_keys=False)+'---\n\n'+body+'\n')
    config = f'''baseURL = "https://boulingua.github.io/{code}/"
title = "{name} — Boulingua"
languageCode = "de"
defaultContentLanguage = "de"
enableRobotsTXT = true
[pagination]
  pagerSize = 20
[markup.highlight]
  noClasses = false
[markup.goldmark.renderer]
  unsafe = true
[taxonomies]
  tag = "tags"
  skill = "skills"
  level = "levels"
  topic = "topics"
[params]
  code = "{code}"
  navTitle = "{name}"
  author = "S. Le Boulanger"
  description = "{name} lernen: Ein Boulingua-Kurs im Aufbau."
  license = "CC BY-SA 4.0"
  targetLanguage = "{lang}"
  scriptTier = "{tier}"
  since = 2025
  hideCredits = true
  hideColorSchemeToggle = true
  colorScheme = "auto"
  customCSS = ["css/tokens.css", "css/custom.css"]
[params.plausible]
  domain = ""
[[menu.main]]
  name = "Kursstand"
  url = "/about/"
  weight = 1
[[menu.main]]
  name = "Materialien"
  url = "/materials/"
  weight = 2
[[menu.main]]
  name = "Rechtliches"
  identifier = "legal"
  weight = 9
[[menu.main]]
  parent = "legal"
  name = "Impressum"
  url = "/impressum/"
  weight = 91
[[menu.main]]
  parent = "legal"
  name = "Datenschutz"
  url = "/datenschutz/"
  weight = 92
[[menu.main]]
  parent = "legal"
  name = "Haftungsausschluss"
  url = "/haftungsausschluss/"
  weight = 93
[module]
  [[module.imports]]
    path = "github.com/boulingua/kit"
  [[module.imports]]
    path = "github.com/luizdepra/hugo-coder"
'''
    put('hugo.toml', config)
    put('LICENSE', (KIT/'LICENSE').read_text())
    put('LICENSE-CONTENT.md', (KIT/'LICENSE-CONTENT.md').read_text())
    put('NOTICE.md', (KIT/'templates/course-NOTICE.md').read_text())
    cfg = yaml.safe_load((KIT/'templates/boulingua.yml').read_text())
    cfg.update(code=code, target_language=lang, script_tier=tier)
    put('boulingua.yml', yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
    put('go.mod', f'''module github.com/boulingua/{code}

go 1.26.1

require (
    github.com/boulingua/kit v1.22.0 // indirect
    github.com/luizdepra/hugo-coder v0.0.0-20260305123245-3d3bbd75d7bb // indirect
)
''')
    put('.github/workflows/deploy.yml', (KIT/'templates/deploy.yml').read_text())
    put('.gitignore', '/public/\n/resources/\n/node_modules/\n/build/\n/go.work\n/go.work.sum\n.hugo_build.lock\n__pycache__/\n*.pyc\n.venv/\n.DS_Store\n_materials/build/\n')
    put('.gitattributes', '*.pdf binary\n')
    for source in (KIT/'templates/course-data').glob('*.yaml'): put('data/'+source.name, source.read_text())
    for source in (KIT/'templates/course-content').glob('*.md'):
        if source.name != 'README.md': put('content/'+source.name, source.read_text().replace('{{CONTENT_LICENCE}}', 'CC BY-SA 4.0'))
    page('_index.md', name+' lernen', '''Dieser Kurs befindet sich im Aufbau. Es gibt noch keine veröffentlichten
Unterrichtseinheiten, Prüfungen oder Hörmaterialien.

Geplant sind differenzierte Aufgaben, Materialien zum Herunterladen und
nachvollziehbare Lernziele. [Zum Kursstand](about/) · [Zu den Materialien](materials/)

Bereits vorhandene Kurse: [Englisch](https://boulingua.github.io/efl/),
[Französisch](https://boulingua.github.io/fle/) und [Deutsch](https://boulingua.github.io/daf/).
''')
    deferred = '\nDie Unterstützung der Zielschrift wird vor der ersten Unterrichtseinheit gesondert geprüft.\n' if meta.get('deferred') else ''
    page('about.md', 'Kursstand', f'''{name} wird als offener Kurs für die Schule und das selbstständige Lernen
entwickelt. Die Oberfläche und die Aufgabenhinweise sind auf Deutsch.

Der Aufbau folgt fünf Schritten: Aktivieren, Verstehen, Üben, Anwenden und
Reflektieren. Jede veröffentlichte Einheit soll überprüfte Aufgaben und
Lösungen, passende Materialien sowie nachvollziehbare Lernziele enthalten.
{deferred}
Die geplante Ausrichtung und die nächsten Schritte stehen in der
[Roadmap](https://github.com/boulingua/{code}/blob/main/ROADMAP.md).
Eine geprüfte Abdeckung des Gemeinsamen Europäischen Referenzrahmens wird
für diesen Entwicklungsstand noch nicht beansprucht.
''')
    page('materials/_index.md', 'Materialien', '''Für diesen Kurs sind noch keine Unterrichtsmaterialien veröffentlicht.
Sobald geprüfte Einheiten vorliegen, erscheinen hier die zugehörigen
Präsentationen, Arbeitsblätter und verfügbaren Aufnahmen.
''', layout='list')
    manifest = {'framework': 'boulingua-curriculum', 'framework_version': '1.2.0', 'language':lang,
        'declared_conformance':'core-restricted' if meta.get('profile') else 'core', 'conformance_status':'in-progress',
        'levels_claimed':['A1','A2','B1'], 'pages':{}, 'implements':{'distinct_descriptors':0,'proposed':0,'asserted':0},
        'realizations':[], 'gaps':[], 'out_of_scope':[]}
    if meta.get('profile'): manifest['profile']=meta['profile']
    put('curriculum.yml', '# Target scope only; no descriptor implementation or educational approval is claimed.\n'+yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
    return written, kept


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('code');ap.add_argument('--into');a=ap.parse_args()
    try: written, kept=scaffold(a.code,a.into or a.code)
    except ValueError as exc: ap.error(str(exc))
    print(f'{a.code}: created {len(written)} files; preserved {len(kept)} existing files')

if __name__=='__main__':main()
