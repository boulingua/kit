#!/usr/bin/env python3
"""Create an honest, buildable development site without overwriting authored files."""
from pathlib import Path
import argparse
import json
import hashlib
import re
import base64
import shutil
import yaml

KIT = Path(__file__).resolve().parents[1]


def scaffold(code, destination, release_manifest=None):
    courses = yaml.safe_load((KIT/'data/courses.yml').read_text())
    if code not in courses: raise ValueError(f'unknown course code: {code}')
    meta = courses[code]; name = meta['name']; lang = meta['language']; tier = meta['tier']
    release = json.loads(Path(release_manifest or KIT/'templates/release-pins.json').read_text())
    if release_manifest and (release.get('schema_version') != 1 or release.get('state') != 'published'):
        raise ValueError('use a published manifest prepared by the organisation release updater')
    if release_manifest:
        for foundation, repository in [('org','boulingua/.github'),('kit','boulingua/kit'),('curriculum','boulingua/curriculum')]:
            record=release.get(foundation,{})
            if not isinstance(record,dict) or record.get('repository')!=repository or not re.fullmatch('[a-f0-9]{40}',str(record.get('commit',''))):
                raise ValueError('published immutable foundation identity is missing: '+foundation)
        for field in ['kit_sum','kit_go_mod_sum']:
            value=release.get(field,'')
            try:
                if not isinstance(value,str) or not value.startswith('h1:') or len(base64.b64decode(value[3:],validate=True))!=32:raise ValueError('invalid digest')
            except (ValueError,TypeError):raise ValueError('published Go checksum missing or invalid: '+field)
        caller=release.get('caller','')
        if hashlib.sha256(caller.encode()).hexdigest()!=release.get('caller_sha256'):
            raise ValueError('published caller digest mismatch')
        job=(yaml.load(caller,Loader=yaml.BaseLoader) or {}).get('jobs',{}).get('course',{})
        commit=release.get('org',{}).get('commit','')
        if not re.fullmatch('[a-f0-9]{40}',commit) or job.get('uses')!='boulingua/.github/.github/workflows/course-build.yml@'+commit or job.get('with',{}).get('org_ref')!=commit:
            raise ValueError('published caller and org pin disagree')
        for foundation in ['kit','curriculum']:
            if not re.fullmatch(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)',release.get(foundation,{}).get('version','')):
                raise ValueError('published foundation version must be exact SemVer')
    manifest = {'framework': 'boulingua-curriculum', 'framework_version': release['curriculum']['version'], 'language':lang,
        'declared_conformance':'core-restricted' if meta.get('profile') else 'core', 'conformance_status':'in-progress',
        'levels_claimed':['A1','A2','B1'], 'pages':{}, 'implements':{'distinct_descriptors':0,'proposed':0,'asserted':0},
        'realizations':[], 'gaps':[], 'out_of_scope':[]}
    if meta.get('profile'): manifest['profile']=meta['profile']
    go_version = release.get('go_version') if release_manifest else '1.26.1'
    if release_manifest:
        from jsonschema import Draft202012Validator
        if not isinstance(go_version,str) or not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?', go_version):
            raise ValueError('published Go floor must be explicit')
        schema_text = release.get('curriculum_schema_text', '')
        if hashlib.sha256(schema_text.encode()).hexdigest() != release.get('curriculum_schema_sha256'):
            raise ValueError('published curriculum schema digest mismatch')
        schema = json.loads(schema_text); Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(manifest))
        if errors: raise ValueError('published schema rejects starter: '+errors[0].message)
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
  src = ""
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
    lock = {key: release[key] for key in ['schema_version','state','org','kit','curriculum','curriculum_schema_sha256']}
    put('release-pins.json', json.dumps(lock, indent=2)+'\n')
    put('go.mod', f'''module github.com/boulingua/{code}

go {go_version}

require (
    github.com/boulingua/kit v{release['kit']['version']} // indirect
    github.com/luizdepra/hugo-coder v0.0.0-20260305123245-3d3bbd75d7bb // indirect
)
''')
    put('.github/workflows/deploy.yml', release.get('caller') or (KIT/'templates/deploy.yml').read_text())
    if release_manifest:
        prefix='github.com/boulingua/kit v'+release['kit']['version']
        put('go.sum', prefix+' '+release['kit_sum']+'\n'+prefix+'/go.mod '+release['kit_go_mod_sum']+'\n')
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
    put('curriculum.yml', '# Target scope only; no descriptor implementation or educational approval is claimed.\n'+yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
    return written, kept


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('code');ap.add_argument('--into');ap.add_argument('--release-manifest',type=Path,help='published foundation manifest from the organisation updater; default is historical development pins');a=ap.parse_args()
    try: written, kept=scaffold(a.code,a.into or a.code,a.release_manifest)
    except ValueError as exc: ap.error(str(exc))
    print(f'{a.code}: created {len(written)} files; preserved {len(kept)} existing files')

if __name__=='__main__':main()
