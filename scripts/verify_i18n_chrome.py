#!/usr/bin/env python3
"""A9: every translated interface key resolves in each configured site language.

Use the effective kit + course templates and dictionaries, in Hugo precedence
order. A missing language is a failure even if another language supplies a key.
This checks key coverage, not the linguistic quality of a translation.
"""
from __future__ import annotations
import re
import sys
import tomllib
from pathlib import Path
import yaml

KIT = Path(__file__).resolve().parent.parent
I18N_CALL = re.compile(r'\b(?:i18n|T)\s+["\']([a-z_0-9]+)["\']')
COMMENT = re.compile(r'\{\{-?\s*/\*.*?\*/\s*-?\}\}|<!--.*?-->', re.S)


def audit(root: Path, kit: Path = KIT) -> tuple[list[str], int, set[str]]:
    templates = {}
    for source in dict.fromkeys([kit, root]):
        for f in (source / 'layouts').rglob('*.html'):
            templates[f.relative_to(source / 'layouts')] = f
    if not templates:
        return ['no templates were found'], 0, set()
    used = set()
    for f in templates.values():
        used.update(I18N_CALL.findall(COMMENT.sub('', f.read_text(encoding='utf-8'))))
    translations = {}
    for source in dict.fromkeys([kit, root]):
        for f in sorted((source / 'i18n').glob('*.y*ml')):
            data = yaml.safe_load(f.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return [f'{f}: expected a translation mapping'], len(used), set()
            translations.setdefault(f.stem, {}).update(data)
    cfg = root / 'hugo.toml'
    if cfg.is_file():
        site = tomllib.loads(cfg.read_text(encoding='utf-8'))
        languages = set(site.get('languages', {})) or {site.get('defaultContentLanguage', 'en')}
    else:
        languages = set(translations)
    errors = []
    for lang in sorted(languages):
        values = translations.get(lang, {})
        for key in sorted(used):
            value = values.get(key)
            if isinstance(value, dict):
                value = value.get('other')
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{lang}: missing or empty translation for {key!r}')
    return errors, len(used), languages


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
    try:
        errors, keys, languages = audit(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors, keys, languages = [str(exc)], 0, set()
    for error in errors:
        print(f'::error::{error}')
    print(f'A9 {"FAIL" if errors else "OK"} — {keys} keys in effective templates; languages: {", ".join(sorted(languages))}')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
