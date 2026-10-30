#!/usr/bin/env python3
"""Generate native-voice audio (OGG/Opus) for boulingua units.

Extracts spoken segments (vocabulary, dialogues, reading texts) from each unit's
markdown, synthesizes them with Piper (openly-licensed native voices), converts
to OGG/Opus with ffmpeg, and writes a per-unit manifest to data/audio/<slug>.json
that the unit layout renders as an accessible "Listen" section with transcripts.

Usage:
  build_audio.py <repo> <voice.onnx> <lang> <units-glob> [voice2.onnx]
    e.g. build_audio.py .../daf voices/de_DE-thorsten-medium.onnx de 'content/kurs_*/units/*.md'
Local, LLM-free. Idempotent (skips segments whose text hash is unchanged).
"""
import sys, re, json, hashlib, subprocess, tempfile, glob, os
from pathlib import Path

# Importing normalise/extract_segments must not parse argv or touch a course.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from blg_paths import site_code, material_slug, front_matter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalise_model import prepare_model_text

# Segment labels, loaded from labels.yml so adding a language is a data edit.
#
# This was a dict literal covering fr/de/en, read as LABELS[kind][LANG]. Adding
# any other language raised KeyError on the FIRST segment of the FIRST unit —
# after to_ogg() and the hash sidecar were written, before the manifest was.
# So the failure was total rather than gradual: one orphan .ogg, a .hash a later
# run would treat as current, no manifest at all, and a traceback. A layout that
# renders from the manifest then shows no player for a clip that exists on disk.
#
# label_for() is total. An unknown language degrades to English, then to the
# capitalised kind — visible and fixable, never an exception.
def _load_labels():
    import yaml
    f = Path(__file__).resolve().parent / "labels.yml"
    return yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}

LABELS = _load_labels()


def label_for(kind: str, lang: str) -> str:
    by_kind = LABELS.get(kind, {})
    return by_kind.get(lang) or by_kind.get("en") or kind.capitalize()

def normalise(text: str, tts_lang: str) -> str:
    """Prepare a string for the synthesiser. Applied to the TTS string ONLY.

    extract_segments() already returns the transcript and the TTS text as
    separate values, which matters: the learner must keep every mark that is
    stripped here. Nothing below ever touches what is displayed.
    """
    if tts_lang in ("ru", "uk"):
        # Piper reads U+0301 as a character, not a stress signal, so it
        # mispronounces every marked word. Strip it — and only it: ё, ґ, ї, є
        # and the U+02BC/U+2019 apostrophe are letters here, not decoration.
        text = text.replace("\u0301", "")
    elif tts_lang in ("ar", "fa"):
        # Bidi controls are invisible to a reader and audible to nothing, but
        # they end up in the phoneme stream.
        for ch in ("\u200e", "\u200f", "\u061c"):
            text = text.replace(ch, "")
        text = re.sub(r"\([A-Za-z][A-Za-z \-']*\)", "", text)   # Latin gloss in parens
    elif tts_lang == "el":
        text = text.replace("\u0387", ".")      # ano teleia reads as a pause
    elif tts_lang == "tr":
        import unicodedata
        text = unicodedata.normalize("NFC", text)   # keep ı / İ intact
    return text


def strip_md(s):
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)      # bold
    s = re.sub(r'\*([^*]+)\*', r'\1', s)          # italic
    s = re.sub(r'`([^`]+)`', r'\1', s)            # code
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)  # links
    s = re.sub(r'[«»“”]', '', s).strip()
    return s

def extract_segments(body):
    """Return [(kind, transcript_text, tts_text)] in document order."""
    segs = []
    lines = body.split('\n')
    i = 0
    while i < len(lines):
        ln = lines[i]
        # --- markdown table -> vocab (first data column) ---
        if ln.strip().startswith('|') and i + 1 < len(lines) and re.match(r'\s*\|[\s:|-]+\|', lines[i+1]):
            rows = []
            j = i
            while j < len(lines) and lines[j].strip().startswith('|'):
                rows.append(lines[j]); j += 1
            terms = []
            for r in rows[2:]:  # skip header + separator
                cells = [c.strip() for c in r.strip().strip('|').split('|')]
                if cells and cells[0] and not set(cells[0]) <= set('-: '):
                    t = strip_md(cells[0])
                    # skip cells that are clearly not target-language terms
                    if t and len(t) < 60 and not t.lower().startswith(('http', 'www')):
                        terms.append(t)
            if len(terms) >= 4:
                segs.append(('vocab', ' · '.join(terms), '.\n'.join(terms) + '.'))
            i = j; continue
        # --- blockquote block -> dialogue or texte ---
        if ln.strip().startswith('>'):
            qs = []
            j = i
            while j < len(lines) and (lines[j].strip().startswith('>') or lines[j].strip() == ''):
                if lines[j].strip().startswith('>'):
                    qs.append(re.sub(r'^\s*>\s?', '', lines[j]))
                elif qs and j + 1 < len(lines) and lines[j+1].strip().startswith('>'):
                    qs.append('')
                else:
                    break
                j += 1
            block = '\n'.join(qs).strip()
            if block:
                is_dialogue = bool(re.search(r'\*\*[^*]+ ?:\*\*|\*\*[^*]+:\*\*', block)) or block.count(':') >= 2 and re.search(r'\*\*', block)
                spoken = []
                for q in qs:
                    q = q.strip()
                    if not q: continue
                    # drop stage directions in (parentheses/italics only)
                    if re.fullmatch(r'[\*\(].*[\*\)]', q): continue
                    # for dialogue: keep speaker name then line
                    spoken.append(strip_md(q))
                text = ' '.join(x for x in spoken if x)
                if is_dialogue and len(text) > 20:
                    segs.append(('dialogue', block_transcript(qs), text))
                elif len(text) > 120:
                    segs.append(('texte', block_transcript(qs), text))
            i = j; continue
        i += 1
    return segs

def block_transcript(qs):
    return '\n'.join(strip_md(q) for q in qs if q.strip())

def synth(text, wav, voice, speaker=0):
    """Synthesise to `wav`. Raises if piper fails.

    The return code used to be discarded, and one temp path was reused for a
    whole unit, so a failed call left the PREVIOUS segment's wav in place and
    `if wav.exists()` was still true. The result was the last clip republished
    under the next clip's filename, with the next clip's transcript beside it
    in the manifest, and a .hash sidecar written so it was never retried. A
    language course whose audio and transcript disagree is the worst available
    outcome and this produced it silently, exit 0, "N clips synthesized".
    """
    wav.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, "-m", "piper", "--model", voice,
                        "--output_file", str(wav), "--speaker", str(speaker)],
                       input=text, text=True, capture_output=True)
    if r.returncode != 0 or 'Missing phoneme' in r.stderr:
        raise RuntimeError(f"piper failed ({r.returncode}) on {wav.name}: "
                           f"{(r.stderr or '')[-400:]}")
    if not wav.exists() or wav.stat().st_size == 0:
        raise RuntimeError(f"piper exited 0 but wrote no audio to {wav.name}")

def to_ogg(wav, ogg):
    r = subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libopus",
                        "-b:a", "48k", "-ac", "1", str(ogg)], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({r.returncode}) on {ogg.name}: "
                           f"{(r.stderr or b'')[-400:]!r}")
    if not ogg.exists() or ogg.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg exited 0 but wrote no audio to {ogg.name}")

def link_manifest(text, key):
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise ValueError('YAML front matter is required')
    front = match.group(1)
    line = 'audio_manifest: ' + key
    front = re.sub(r'(?m)^audio_manifest:.*$', line, front) if re.search(r'(?m)^audio_manifest:', front) else front + '\n' + line
    return '---\n' + front + '\n---\n' + text[match.end():]


def main(argv=None):
    import argparse
    import yaml
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('repo', type=Path)
    ap.add_argument('voice', type=Path)
    ap.add_argument('lang')
    ap.add_argument('units_glob')
    ap.add_argument('voice2', type=Path, nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--speaker', type=int, default=0)
    a = ap.parse_args(argv)
    repo = a.repo.resolve()
    code = site_code(repo)
    voices = [a.voice.resolve(), (a.voice2 or a.voice).resolve()]
    for voice in voices:
        if not voice.is_file(): ap.error(f'voice not found: {voice}')
    # Cache keys include model bytes. Replacing a model at the same path must
    # invalidate the old recording, even when the text stays the same.
    model_hashes = {v: hashlib.sha256(v.read_bytes()).hexdigest() for v in set(voices)}
    config_hashes = {}
    model_settings = {}
    for voice in set(voices):
        config = Path(str(voice) + '.json')
        if not config.is_file(): ap.error(f'voice configuration not found: {config}')
        settings = json.loads(config.read_text())
        model_settings[voice] = settings
        if not 0 <= a.speaker < settings.get('num_speakers', 1): ap.error('speaker outside model speaker range')
        config_hashes[voice] = hashlib.sha256(config.read_bytes()).hexdigest()
    units = sorted(repo.glob(a.units_glob))
    selected = []
    for unit in units:
        fm, body = front_matter(unit)
        if fm.get('page_type') == 'exam': continue
        if not (a.all or a.only or os.environ.get('AUDIO_ALL') == '1' or fm.get('materials_status') == 'ready'): continue
        if a.only and a.only != (unit.parent.name if unit.name == 'index.md' else unit.stem): continue
        selected.append((unit, fm, body))
    if not selected:
        print('::error::no eligible units matched; use --only or --all for an explicit selection', file=sys.stderr)
        return 1
    data = repo / 'data/audio'
    data.mkdir(parents=True, exist_ok=True)
    made = manifests = failed = 0
    keys = set()
    for unit, fm, body in selected:
        slug = fm.get('audio_manifest') or material_slug(unit)
        if not isinstance(slug, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', slug):
            raise ValueError(f'{unit}: invalid audio manifest key')
        if slug in keys:
            raise ValueError(f'{unit}: audio manifest key collision: {slug}')
        keys.add(slug)
        prior_path = data / f'{slug}.json'
        legacy = fm.get('audio_manifest') or (unit.parent.name if unit.name == 'index.md' else unit.stem)
        previous = prior_path if prior_path.exists() else data / f'{legacy}.json'
        existing_list = json.loads(previous.read_text()) if previous.exists() else []
        existing = {e.get('file', '').rsplit('/', 1)[-1]: e for e in existing_list}
        segments = extract_segments(body)
        if not segments:
            print(f'::error::{unit}: no speech segments; existing recordings preserved', file=sys.stderr)
            failed += 1
            continue
        outdir = repo / 'static/materials/audio' / slug
        outdir.mkdir(parents=True, exist_ok=True)
        manifest, prepared, counters = [], [], {}
        unit_failed = False
        with tempfile.TemporaryDirectory(prefix='.audio-', dir=outdir) as td:
            stage = Path(td)
            for kind, transcript, raw in segments:
                counters[kind] = counters.get(kind, 0) + 1
                n = counters[kind]
                name = f'{kind}{n}.ogg'
                prior = existing.get(name, {})
                # The human recording is protected BEFORE synthesis or encoding.
                if prior.get('source') == 'human':
                    manifest.append(prior)
                    continue
                voice = voices[1] if kind == 'dialogue' and n % 2 == 0 else voices[0]
                spoken = prepare_model_text(normalise(raw, a.lang), model_settings[voice])
                digest = hashlib.sha256((spoken + model_hashes[voice] + config_hashes[voice] + str(a.speaker)).encode()).hexdigest()
                ogg, hashf = outdir / name, outdir / f'.{name}.hash'
                if not (ogg.is_file() and hashf.is_file() and hashf.read_text() == digest):
                    wav, encoded = stage / f'{name}.wav', stage / name
                    try:
                        synth(spoken, wav, str(voice), a.speaker)
                        to_ogg(wav, encoded)
                    except (RuntimeError, OSError) as exc:
                        print(f'::error::{slug}/{name}: {exc}', file=sys.stderr)
                        unit_failed = True
                        failed += 1
                        break
                    cached = stage / f'.{name}.hash'
                    cached.write_text(digest)
                    prepared.extend([(encoded, ogg), (cached, hashf)])
                entry = {'file':f'/{code}/materials/audio/{slug}/{name}',
                         'label':label_for(kind, a.lang) + f' {n}', 'transcript':transcript,
                         'source':'tts', 'voice':voice.stem, 'model_sha256':model_hashes[voice],
                         'config_sha256':config_hashes[voice], 'speaker_id':a.speaker}
                if spoken != transcript: entry['tts'] = spoken
                manifest.append(entry)
            if unit_failed: continue
            # Human clips no longer found by extraction remain explicitly listed.
            manifest.extend(e for e in existing_list if e.get('source') == 'human' and e not in manifest)
            staged_manifest = stage / 'manifest.json'
            staged_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
            for source, destination in prepared: source.replace(destination)
            staged_manifest.replace(prior_path)
            unit.write_text(link_manifest(unit.read_text(), slug))
            made += len(prepared) // 2
            manifests += 1
    print(f'audio: {made} clips synthesized; {manifests} manifests written; {failed} failures')
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
