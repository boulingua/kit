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

repo = Path(sys.argv[1]); VOICE = sys.argv[2]; LANG = sys.argv[3]; UNITS_GLOB = sys.argv[4]
SITE = repo.resolve().name
VOICE2 = sys.argv[5] if len(sys.argv) > 5 else VOICE
AUDIO = repo / "static/materials/audio"
DATA = repo / "data/audio"
LABELS = {"vocab": {"fr": "Vocabulaire", "de": "Wortschatz", "en": "Vocabulary"},
          "dialogue": {"fr": "Dialogue", "de": "Dialog", "en": "Dialogue"},
          "texte": {"fr": "Texte", "de": "Text", "en": "Text"}}

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

def synth(text, wav, voice):
    subprocess.run([sys.executable, "-m", "piper", "--model", voice, "--output_file", str(wav)],
                   input=text, text=True, capture_output=True)

def to_ogg(wav, ogg):
    subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libopus", "-b:a", "48k", "-ac", "1", str(ogg)],
                   capture_output=True)

def main():
    units = sorted(glob.glob(str(repo / UNITS_GLOB)))
    made = 0; manifests = 0
    DATA.mkdir(parents=True, exist_ok=True)
    for uf in units:
        uf = Path(uf)
        txt = uf.read_text(encoding='utf-8')
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', txt, re.S)
        if not m: continue
        fm, body = m.group(1), m.group(2)
        # Only voice ENRICHED units — their presentation is an .odp deck.
        # (Un-authored units still point at a placeholder .pptx.) Set
        # AUDIO_ALL=1 for sites whose units are already rich (e.g. efl).
        if os.environ.get('AUDIO_ALL') != '1' and '.odp' not in fm:
            continue
        # For leaf bundles (index.md in a per-unit folder, e.g. efl) the
        # stable key is the FOLDER name (== Hugo's .File.ContentBaseName);
        # for single-file units it's the filename stem.
        slug = uf.parent.name if uf.name == 'index.md' else uf.stem
        # Skip separate exam pages (assessment); voice the teaching units.
        if slug.endswith('-exam') or slug.endswith('_exam'):
            continue
        segs = extract_segments(body)
        if not segs: continue
        outdir = AUDIO / slug
        outdir.mkdir(parents=True, exist_ok=True)
        manifest = []
        counters = {}
        with tempfile.TemporaryDirectory() as td:
            for kind, transcript, tts in segs:
                counters[kind] = counters.get(kind, 0) + 1
                n = counters[kind]
                name = f"{kind}{n}.ogg"
                ogg = outdir / name
                voice = VOICE2 if (kind == 'dialogue' and n % 2 == 0) else VOICE
                h = hashlib.sha1((tts + voice).encode()).hexdigest()[:10]
                hashf = outdir / f".{name}.hash"
                if ogg.exists() and hashf.exists() and hashf.read_text() == h:
                    pass  # unchanged
                else:
                    wav = Path(td) / "s.wav"
                    synth(tts, wav, voice)
                    if wav.exists():
                        to_ogg(wav, ogg); hashf.write_text(h); made += 1
                label = LABELS[kind][LANG] + f' {n}'
                manifest.append({"file": f"/{SITE}/materials/audio/{slug}/{name}",
                                 "label": label, "transcript": transcript})
        (DATA / f"{slug}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
        manifests += 1
    print(f"audio: {made} clips synthesized, {manifests} unit manifests written")

if __name__ == "__main__":
    main()
