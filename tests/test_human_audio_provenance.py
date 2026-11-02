from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_audio_manifests as gate


class HumanProvenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'course'; self.repo.mkdir()
        self.evidence = Path(self.tmp.name) / 'private-evidence'; self.evidence.mkdir()
        (self.repo / 'hugo.toml').write_text('[params]\ncode="efl"\n')
        self.clip = self.repo / 'static/materials/audio/lesson/reading.ogg'
        self.clip.parent.mkdir(parents=True); self.clip.write_bytes(b'delivery fixture')
        (self.repo / 'data/audio').mkdir(parents=True)
        (self.repo / 'data/audio-provenance').mkdir()
        self.manifest = self.repo / 'data/audio/lesson.json'
        self.record = self.repo / 'data/audio-provenance/reading.json'
        self.segment = {'label':'Reading', 'transcript':'A spoken test fixture.',
                        'file':'/efl/materials/audio/lesson/reading.ogg', 'source':'human',
                        'human_provenance':'reading.json'}
        source=self.evidence/'source.wav'; source.write_bytes(b'source recording fixture')
        permission=self.evidence/'permission.md'; permission.write_text('Test fixture only: permit fixture use.')
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.provenance = {'performer':'Fixture performer', 'recorded_on':'2026-01-01',
            'source_recording':{'path':'source.wav','sha256':digest(source)},
            'permission':{'path':'permission.md','sha256':digest(permission),'scope':'Test fixture use only'},
            'review':{'reviewer':'Fixture reviewer','date':'2026-01-02','verdict':'pass',
                      'notes':'Fixture transcript/pronunciation/recording quality check.',
                      'recording_sha256':digest(self.clip),
                      'transcript_sha256':hashlib.sha256(self.segment['transcript'].encode()).hexdigest()}}

    def audit(self, provenance=True):
        self.manifest.write_text(json.dumps([self.segment]))
        if provenance:self.record.write_text(json.dumps(self.provenance))
        # Codec verification is independent; this fixture targets the genuine
        # evidence contract, while production D6 still decodes every clip.
        with patch.object(gate,'AudioFile',return_value=SimpleNamespace(info=SimpleNamespace(length=1,channels=1,bitrate=24000))):
            return gate.audit(self.repo,self.evidence)[0]

    def test_bare_human_label_cannot_bypass_evidence(self):
        del self.segment['human_provenance']
        self.assertTrue(any('human provenance' in e for e in self.audit(False)))

    def test_complete_bound_fixture_and_external_private_evidence_pass(self):
        self.assertEqual(self.audit(),[])

    def test_changed_transcript_or_audio_requires_new_review(self):
        for field in ['transcript','clip']:
            with self.subTest(field=field):
                if field=='transcript':self.segment['transcript']+=' Changed.'
                else:self.clip.write_bytes(b'changed delivery')
                self.assertTrue(any('does not match' in e for e in self.audit()))

    def test_missing_changed_or_escaping_permission_is_rejected(self):
        for path in ['missing.md','../private-evidence/permission.md']:
            self.provenance['permission']['path']=path
            self.assertTrue(self.audit())
        self.provenance['permission']['path']='permission.md'
        (self.evidence/'permission.md').write_text('Different document')
        self.assertTrue(any('SHA-256 mismatch' in e for e in self.audit()))

    def test_pending_or_future_review_is_not_an_approval(self):
        for key,value in [('reviewer','pending'),('verdict','hold'),('date','2999-01-01')]:
            with self.subTest(key=key):
                original=copy.deepcopy(self.provenance)
                self.provenance['review'][key]=value
                self.assertTrue(self.audit())
                self.provenance=original
