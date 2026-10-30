#!/usr/bin/env python3
"""Create reproducible local voice previews; listening approval remains a separate record."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import re
import shutil
import sys
import tempfile
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from normalise_model import prepare_model_text
REG = HERE / 'voices.yml'
ALLOWED = {'CC0', 'public domain', 'public-domain', 'Unlicense', 'CC BY 3.0',
           'CC BY 4.0', 'CC-BY 4.0', 'CC-BY-4.0', 'CC BY-SA 4.0', 'Apache-2.0', 'MIT'}


def normalise_licence(text):
    t = (text or '').strip().rstrip('/').split('\n')[0]
    if 'creativecommons.org/publicdomain/zero' in t: return 'CC0'
    if 'creativecommons.org/licenses/by/4.0' in t: return 'CC BY 4.0'
    if 'creativecommons.org/licenses/by-sa/4.0' in t: return 'CC BY-SA 4.0'
    return t


def rows():
    return {r['code']: r for r in yaml.safe_load(REG.read_text())['languages']}


def licence_ok(row):
    licence = normalise_licence(row.get('licence'))
    return licence in ALLOWED, licence or 'no licence recorded'


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream: return hashlib.file_digest(stream, algorithm).hexdigest()


def fetch(url, destination, md5=None):
    """Atomic download. An invalid existing cache is rejected, never trusted."""
    if destination.exists():
        if md5 and digest(destination, 'md5') != md5:
            raise ValueError(f'cached model checksum mismatch: {destination}')
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as td:
        tmp = Path(td) / 'download'
        with urllib.request.urlopen(url, timeout=120) as source, tmp.open('wb') as target:
            shutil.copyfileobj(source, target)
        if not tmp.stat().st_size: raise ValueError(f'empty download: {url}')
        if md5 and digest(tmp, 'md5') != md5: raise ValueError(f'upstream model checksum mismatch: {url}')
        tmp.replace(destination)


def samples_for(code, row):
    path = HERE / 'samples' / f'{code}.yml'
    if not path.is_file(): raise ValueError(f'missing review texts: {path}')
    samples = yaml.safe_load(path.read_text())
    if set(samples) != {'dialogue', 'vocabulary', 'continuous'}:
        raise ValueError('samples must include dialogue, vocabulary and continuous reading')
    if any(not isinstance(t, str) or not t.strip() for t in samples.values()):
        raise ValueError('all sample transcripts must be nonempty strings')
    text = '\n'.join(samples.values())
    missing = [s for s in (row.get('must_render') or []) + (row.get('must_render_phrases') or []) if s not in text]
    if missing: raise ValueError(f'samples omit required pronunciation probes: {missing}')
    return samples


def audio_stats(path):
    import numpy as np
    with wave.open(str(path), 'rb') as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getnframes() == 0:
            raise ValueError('expected nonempty mono PCM16 WAV')
        rate, count = wav.getframerate(), wav.getnframes()
        data = np.frombuffer(wav.readframes(count), dtype='<i2').astype(np.float64) / 32768
    rms = float(np.sqrt(np.mean(data ** 2)))
    clipping = float(np.mean(np.abs(data) >= 32767 / 32768))
    if rms < .0001 or clipping > .01: raise ValueError('silent or excessively clipped preview')
    return {'sample_rate': rate, 'channels': 1, 'seconds': round(count / rate, 3),
            'rms': round(rms, 6), 'clipped_fraction': round(clipping, 6)}


def generate(code, row, models, output, speaker):
    samples = samples_for(code, row)
    url = row.get('url', '')
    # A revision URL freezes the model, config and model card together.
    if not re.search(r'/resolve/[a-f0-9]{40}/', url): raise ValueError('voice URL must pin an upstream revision')
    if not re.fullmatch(r'[a-f0-9]{32}', row.get('md5', '')): raise ValueError('upstream model checksum required')
    key = row['piper_key']
    if Path(key).name != key: raise ValueError('invalid model key')
    cache = models / code
    model = cache / f'{key}.onnx'; config = cache / f'{key}.onnx.json'; card = cache / 'MODEL_CARD'
    fetch(url, model, row['md5']); fetch(url + '.json', config, row.get('config_md5'))
    fetch(url.rsplit('/', 1)[0] + '/MODEL_CARD', card, row.get('model_card_md5'))
    cfg = json.loads(config.read_text())
    if not 0 <= speaker < cfg['num_speakers']: raise ValueError('speaker outside model speaker range')
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(model, config_path=config, download_dir=cache)
    output.mkdir(parents=True, exist_ok=True)
    receipt = {'code': code, 'voice': key, 'speaker_id': speaker,
               'generated_at': datetime.now(timezone.utc).isoformat(), 'url': url,
               'model_sha256': digest(model), 'config_sha256': digest(config),
               'model_card_sha256': digest(card), 'licence': row['licence'],
               'piper_version': importlib.metadata.version('piper-tts'),
               'listening_verdict': 'pending', 'samples': {}}
    # A failed sample leaves every previously completed audition intact.
    with tempfile.TemporaryDirectory(dir=output) as td:
        stage = Path(td)
        for name, text in samples.items():
            spoken = prepare_model_text(text, cfg)
            wav_path = stage / f'{code}-{name}.wav'
            warnings = []
            class Capture(logging.Handler):
                def emit(self, record): warnings.append(record.getMessage())
            handler = Capture(logging.WARNING)
            logger = logging.getLogger('piper'); logger.addHandler(handler)
            try:
                with wave.open(str(wav_path), 'wb') as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(cfg['audio']['sample_rate'])
                    voice.synthesize_wav(spoken, wav, syn_config=SynthesisConfig(speaker_id=speaker))
            finally: logger.removeHandler(handler)
            if any('Missing phoneme' in message for message in warnings):
                raise ValueError(f'{name}: model cannot pronounce every input symbol: {warnings}')
            receipt['samples'][name] = {'file': wav_path.name, 'sha256': digest(wav_path),
                'transcript': text, 'speech_input': spoken, 'warnings': warnings, 'transcript_sha256': hashlib.sha256(text.encode()).hexdigest(),
                **audio_stats(wav_path)}
        (stage / f'{code}.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        shutil.copy2(card, stage / f'{code}-MODEL_CARD.txt')
        (stage / f'{code}.txt').write_text('\n\n'.join(f'{n}\n{t}' for n, t in samples.items()) + '\n')
        for source in stage.iterdir(): source.replace(output / source.name)
    record = output / f'{code}-listening.md'
    # Never replace a person's earlier verdict with an automatically generated one.
    if not record.exists():
        record.write_text(f'''# {code} voice listening review

voice: {key}
speaker_id: {speaker}
model_sha256: {receipt['model_sha256']}
config_sha256: {receipt['config_sha256']}
listener: <name and language competence>
date: <YYYY-MM-DD of listening>
verdict: hold

Listen to all three WAV files with their transcripts. Record intelligibility,
naturalness, stress/intonation, names, punctuation, numbers and the language's
required pronunciation probes. Record any correction by sample and timestamp.
Also review the draft text itself. A technical audio check is not a listening
verdict. If changing the model or speaker, create a new dated review.

When reviewed, place the signed-off record in kit/audio/auditions/{code}.md
and preserve the matching receipt and reviewed samples. Release validation
requires a pass for this exact model, config and speaker.
''')
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--code', required=True)
    ap.add_argument('--check', action='store_true', help='licence eligibility only, no download or approval')
    ap.add_argument('--models', type=Path, default=Path.home() / '.cache/boulingua/voices')
    ap.add_argument('--output', type=Path, default=HERE / 'preview-output')
    ap.add_argument('--speaker', type=int, default=0)
    a = ap.parse_args(argv)
    row = rows().get(a.code)
    if not row: ap.error('unknown course code')
    if row.get('status') == 'none':
        print(f'{a.code}: no selected synthesis model; human recording or transcripts remain available')
        return 0
    ok, detail = licence_ok(row)
    if not ok:
        print(f'::error::{a.code}: licence eligibility failed: {detail}', file=sys.stderr); return 1
    if a.check:
        print(f'{a.code}: recorded licence {detail} is eligible; voice quality has not been approved'); return 0
    try:
        receipt = generate(a.code, row, a.models.resolve(), a.output.resolve(), a.speaker)
    except Exception as exc:
        print(f'::error::{a.code}: {exc}', file=sys.stderr); return 1
    print(f'{a.code}: {len(receipt["samples"])} previews generated in {a.output}; listening verdict pending')
    return 0


if __name__ == '__main__': raise SystemExit(main())
