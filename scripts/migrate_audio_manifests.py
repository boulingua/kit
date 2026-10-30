#!/usr/bin/env python3
"""Give each unit a distinct audio manifest, retaining existing recording URLs.

Only exact transcript matches are associated with a unit. Missing recordings
remain readable transcripts. Legacy manifests and all recordings are preserved.
Run without --apply to inspect the proposed migration.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
from blg_paths import front_matter, material_slug, site_code

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audio_build', KIT / 'audio/build_audio.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


link_manifest = audio.link_manifest

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('repo', type=Path)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    repo = a.repo.resolve()
    plans, keys = [], set()
    available = missing = unmatched = 0
    for page in sorted((repo / 'content').rglob('*.md')):
        fm, body = front_matter(page)
        if fm.get('page_type') != 'unit': continue
        key = material_slug(page)
        if key in keys: raise ValueError(f'duplicate material/audio key: {key}')
        keys.add(key)
        old_key = fm.get('audio_manifest') or (page.parent.name if page.name == 'index.md' else page.stem)
        prior_file = repo / 'data/audio' / (old_key + '.json')
        prior = json.loads(prior_file.read_text()) if prior_file.exists() else []
        segments, used, counters = [], set(), {}
        for kind, transcript, spoken in audio.extract_segments(body):
            counters[kind] = counters.get(kind, 0) + 1
            found = next((x for x in prior if x.get('transcript') == transcript), None)
            if found:
                segments.append(found.copy())
                used.add(transcript)
                available += bool(found.get('file'))
            else:
                entry = {'label':audio.label_for(kind, {'efl':'en','fle':'fr','daf':'de'}[site_code(repo)]) + f' {counters[kind]}', 'transcript':transcript}
                if spoken != transcript: entry['tts'] = spoken
                segments.append(entry)
                missing += 1
        # A curated human segment cannot be detached by heuristic extraction.
        segments.extend(x for x in prior if x.get('source') == 'human' and x not in segments)
        unmatched += sum(x.get('transcript') not in used for x in prior)
        plans.append((page, key, segments, link_manifest(page.read_text(), key)))
    if a.apply:
        data = repo / 'data/audio'; archive = repo / 'data/audio-legacy'
        data.mkdir(parents=True, exist_ok=True)
        for old in sorted(data.glob('*.json')):
            if old.stem not in keys:
                archive.mkdir(parents=True, exist_ok=True)
                saved = archive / old.name
                if saved.exists() and saved.read_bytes() != old.read_bytes():
                    raise ValueError(f'archive conflict: {saved}')
                if not saved.exists(): saved.write_bytes(old.read_bytes())
                old.unlink()
        for page, key, segments, text in plans:
            (data / f'{key}.json').write_text(json.dumps(segments, ensure_ascii=False, indent=2) + '\n')
            page.write_text(text)
    print(json.dumps({'applied':a.apply,'units':len(plans),'matched_recordings':available,'transcripts_without_recording':missing,'prior_segments_not_matched':unmatched},indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
