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
# --all / --only replace the AUDIO_ALL environment variable the dead .odp gate
# forced everyone to set. Kept as an env var too, so existing CI does not break.
ALL = os.environ.get("AUDIO_ALL") == "1" or "--all" in sys.argv
ONLY = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)
TTS_LANG = LANG
VOICE2 = sys.argv[5] if len(sys.argv) > 5 else VOICE
AUDIO = repo / "static/materials/audio"
DATA = repo / "data/audio"
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
        # Gate positively on materials_status, not on a file extension.
        #
        # This used to skip any unit whose front matter lacked ".odp". Since the
        # LaTeX migration no unit in any repo has one — the surviving mentions
        # are teacher-note body prose pointing at files that no longer exist —
        # so the condition was always true and AUDIO_ALL=1 was mandatory to get
        # any output at all. A gate that always skips is not a gate.
        if not (ALL or ONLY or re.search(r'^materials_status:\s*ready\s*$', fm, re.M)):
            continue
        if ONLY and ONLY != (uf.parent.name if uf.name == 'index.md' else uf.stem):
            continue
        # For leaf bundles (index.md in a per-unit folder, e.g. efl) the
        # stable key is the FOLDER name (== Hugo's .File.ContentBaseName);
        # for single-file units it's the filename stem.
        slug = uf.parent.name if uf.name == 'index.md' else uf.stem
        prior_path = DATA / f"{slug}.json"
        existing = {e.get("file", "").rsplit("/", 1)[-1]: e
                    for e in (json.loads(prior_path.read_text(encoding="utf-8"))
                              if prior_path.exists() else [])}
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
                    synth(normalise(tts, TTS_LANG), wav, voice)
                    if wav.exists():
                        to_ogg(wav, ogg); hashf.write_text(h); made += 1
                label = label_for(kind, LANG) + f' {n}'
                # Never overwrite a curated human recording. lle has no voice
                # at all and pfa may take hand-recorded clips for its classical
                # strand; a regeneration must leave those alone.
                prior = existing.get(name, {})
                if prior.get("source") == "human":
                    manifest.append(prior)
                    continue
                manifest.append({"file": f"/{SITE}/materials/audio/{slug}/{name}",
                                 "label": label, "transcript": transcript,
                                 "source": "tts"})
        (DATA / f"{slug}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
        manifests += 1
    print(f"audio: {made} clips synthesized, {manifests} unit manifests written")

if __name__ == "__main__":
    main()
