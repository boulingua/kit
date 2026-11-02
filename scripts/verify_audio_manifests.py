#!/usr/bin/env python3
"""D6: recording paths, transcripts, formats, provenance and audition evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
import yaml
from mutagen import File as AudioFile
from blg_paths import site_code

KIT=Path(__file__).resolve().parents[1]


def human_provenance_errors(repo, segment, recording, evidence_root=None):
    """Validate retained evidence and its binding to the reviewed delivery clip.

    This verifies a record, not whether its factual permission claim is true.
    Consent/source assets may be held outside the public checkout; the evidence
    root is explicit and is never copied to static/ or emitted in the site.
    """
    errors = []
    def text(value):
        return (isinstance(value, str) and bool(value.strip())
                and not re.search(r'<|>|\b(?:pending|unknown|placeholder|todo|tbd)\b', value, re.I)
                and value.strip().lower() not in {'none', 'n/a'})
    def checked_date(value, label):
        try:
            parsed = date.fromisoformat(value)
            if parsed > date.today(): raise ValueError('future')
            return parsed
        except (TypeError, ValueError): errors.append(label + ' must be an actual nonfuture ISO date')
    def local_file(root, value, label):
        if not isinstance(value, str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
            errors.append(label + ' must be a relative evidence path'); return
        path = (root / value).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size == 0:
            errors.append(label + ' evidence file is missing, empty or outside its root'); return
        return path
    def hashed_file(root, record, label):
        if not isinstance(record, dict):
            errors.append(label + ' evidence record is required'); return
        path = local_file(root, record.get('path'), label)
        digest = record.get('sha256')
        if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
            errors.append(label + ' SHA-256 is required')
        elif path and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(label + ' evidence SHA-256 mismatch')
    root = repo / 'data/audio-provenance'
    path = local_file(root, segment.get('human_provenance'), 'human provenance')
    if not path: return errors
    try:
        record = json.loads(path.read_text())
        if not isinstance(record, dict): raise ValueError('expected object')
    except (OSError, ValueError) as exc: return errors + [f'human provenance record is invalid: {exc}']
    if not text(record.get('performer')): errors.append('human provenance needs the actual performer or documented performer identifier')
    recorded = checked_date(record.get('recorded_on'), 'recording date')
    retained = Path(evidence_root).resolve() if evidence_root else repo
    hashed_file(retained, record.get('source_recording'), 'source recording')
    permission = record.get('permission')
    hashed_file(retained, permission, 'permission')
    if not isinstance(permission, dict) or not text(permission.get('scope')):
        errors.append('permission must state the actual permitted use')
    review = record.get('review')
    if not isinstance(review, dict): return errors + ['human recording review is required']
    if not text(review.get('reviewer')): errors.append('human review needs an actual reviewer')
    reviewed = checked_date(review.get('date'), 'review date')
    if recorded and reviewed and reviewed < recorded: errors.append('review predates the recording')
    if review.get('verdict') != 'pass': errors.append('human recording review verdict is not pass')
    if not text(review.get('notes')): errors.append('human review needs findings on transcript, pronunciation and recording quality')
    expected = {'recording_sha256': hashlib.sha256(recording.read_bytes()).hexdigest(),
                'transcript_sha256': hashlib.sha256(str(segment.get('transcript', '')).encode('utf-8')).hexdigest()}
    for key, digest in expected.items():
        if review.get(key) != digest: errors.append(f'human review {key} does not match the delivered recording/transcript')
    return errors


def audition_errors(record, voice, identities=()):
    if not record.is_file():return [f'{record}: missing dated audition record']
    text=record.read_text()
    values={m.group(1).lower():m.group(2).strip() for m in re.finditer(r'(?mi)^\s*(?:\*\*)?(voice|listener|date|verdict|model_sha256|config_sha256|speaker_id)(?:\*\*)?\s*:\s*(.*?)\s*$',text)}
    errors=[]
    if values.get('voice')!=voice:errors.append('audition voice differs from the selected model')
    if values.get('verdict','').lower()!='pass':errors.append('audition verdict is not pass')
    if not values.get('listener') or '<' in values['listener'] or values['listener'].lower() in {'pending','none','unknown'}:errors.append('audition needs the actual listener name')
    for key in ['model_sha256','config_sha256']:
        if not re.fullmatch(r'[a-f0-9]{64}',values.get(key,'')):errors.append(f'audition needs {key}')
    try:
        speaker=int(values.get('speaker_id',''))
        if speaker<0:raise ValueError('negative speaker')
    except ValueError:errors.append('audition speaker_id is invalid');speaker=None
    for identity in identities:
        if identity!=(values.get('voice'),values.get('model_sha256'),values.get('config_sha256'),speaker):
            errors.append('recording voice/model/config/speaker differs from the passed audition')
            break
    try:
        when=date.fromisoformat(values.get('date',''))
        if when>date.today():errors.append('audition date is in the future')
    except ValueError:errors.append('audition date is invalid')
    return errors


def audit(repo, evidence_root=None):
    evidence_root = evidence_root or os.environ.get('BOULINGUA_AUDIO_EVIDENCE_ROOT')
    code=site_code(repo);data=repo/'data/audio'
    manifests=sorted(data.glob('*.json'));errors=[];notes=[];references=set();clips=0;tts=False;identities=set()
    for manifest in manifests:
        try:
            segments=json.loads(manifest.read_text())
            if not isinstance(segments,list):raise ValueError('manifest must be a list')
        except (ValueError,OSError) as exc:
            errors.append(f'{manifest.name}: {exc}');continue
        for index,segment in enumerate(segments):
            label=f'{manifest.name}[{index}]'
            if not isinstance(segment,dict):errors.append(label+': segment must be a mapping');continue
            if any(not isinstance(segment.get(k),str) or not segment[k].strip() for k in ['label','transcript']):errors.append(label+': nonempty label and transcript required')
            url=segment.get('file')
            if not url:continue # transcript-only is supported; no recording claim.
            clips+=1
            prefix=f'/{code}/materials/audio/'
            if not isinstance(url,str) or not url.startswith(prefix) or '..' in Path(url).parts:
                errors.append(label+': recording must be a local course audio URL');continue
            path=repo/'static'/url[len('/'+code+'/'):];references.add(path.resolve())
            if not path.is_file():errors.append(label+f': missing recording {url}');continue
            try:
                audio=AudioFile(path)
                if not audio or audio.info.length<=0:raise ValueError('unreadable or empty recording')
                if audio.info.channels!=1:errors.append(label+': recording must be mono')
                bitrate=getattr(audio.info,'bitrate',None)
                if bitrate and bitrate>64000:errors.append(label+f': nominal bitrate {bitrate} exceeds 64000')
            except Exception as exc:errors.append(label+f': audio decode metadata failed: {exc}')
            source=segment.get('source')
            if source not in {'tts','human'}:errors.append(label+': source is not recorded as tts or human')
            if source=='human':
                errors.extend(label+': '+error for error in human_provenance_errors(repo,segment,path,evidence_root))
            else:
                tts=True
                identities.add((segment.get('voice'),segment.get('model_sha256'),segment.get('config_sha256'),segment.get('speaker_id')))
                if not segment.get('voice') or any(not re.fullmatch(r'[a-f0-9]{64}',str(segment.get(key,''))) for key in ['model_sha256','config_sha256']) or type(segment.get('speaker_id')) is not int:
                    errors.append(label+': model/config identity, SHA-256 and speaker are not recorded')
    # Historic manifests retained by migration explain preserved recordings.
    for manifest in (repo/'data/audio-legacy').glob('*.json'):
        for seg in json.loads(manifest.read_text()):
            for key in ['file','file_withheld']:
                url=seg.get(key,'')
                if url.startswith('/'+code+'/materials/audio/'):
                    references.add((repo/'static'/url[len('/'+code+'/'):]).resolve())
    on_disk=set((repo/'static/materials/audio').rglob('*.ogg'))
    extra={p.resolve() for p in on_disk}-references
    if extra:errors.append(f'{len(extra)} recording(s) have no active or preserved manifest reference')
    if tts:
        registry=yaml.safe_load((KIT/'audio/voices.yml').read_text())
        voice=next((v for v in registry['languages'] if v['code']==code),{})
        if voice.get('status')!='ready':errors.append(f'{code}: selected voice is {voice.get("status", "unregistered")}; a passed audition is required for release')
        errors.extend(audition_errors(KIT/'audio/auditions'/f'{code}.md',voice.get('piper_key'),identities))
    return errors,{'manifests':len(manifests),'recording_references':clips,'recordings_on_disk':len(on_disk)}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('repo',type=Path);ap.add_argument('--json',type=Path)
    ap.add_argument('--evidence-root',type=Path,help='retained human source/permission evidence (defaults to course repo; also BOULINGUA_AUDIO_EVIDENCE_ROOT)');a=ap.parse_args()
    errors,stats=audit(a.repo.resolve(),a.evidence_root)
    if a.json:a.json.write_text(json.dumps({**stats,'findings':errors},ensure_ascii=False,indent=2)+'\n')
    for error in errors[:20]:print('::error::'+error)
    print(f'D6 {"FAIL" if errors else "OK"}: {stats}; {len(errors)} findings')
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
