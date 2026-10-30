from pathlib import Path
import importlib.util
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audition', KIT / 'audio/audition.py')
audition = importlib.util.module_from_spec(spec); spec.loader.exec_module(audition)

class Auditions(unittest.TestCase):
    def test_unlicensed_model_is_rejected_before_network_or_synthesis(self):
        with patch.object(audition, 'rows', return_value={'bad': {'licence': 'Unknown'}}), patch.object(audition, 'generate') as generate:
            self.assertEqual(audition.main(['--code', 'bad']), 1)
            generate.assert_not_called()

    def test_missing_checksum_cannot_be_reported_as_verified(self):
        with patch.object(audition, 'samples_for', return_value={}), tempfile.TemporaryDirectory() as td:
            row = {'url': 'https://example.org/resolve/' + 'a'*40 + '/voice.onnx'}
            with self.assertRaisesRegex(ValueError, 'checksum required'):
                audition.generate('test', row, Path(td), Path(td), 0)

    def test_cached_corrupt_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'voice.onnx'; p.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'), patch.object(audition.urllib.request, 'urlopen') as network:
                audition.fetch('https://example.org/voice.onnx', p, '0'*32)
            network.assert_not_called()
            self.assertEqual(p.read_bytes(), b'corrupt')

    def test_pronunciation_probes_are_required(self):
        with self.assertRaisesRegex(ValueError, 'omit required'):
            audition.samples_for('efl', {'must_render': ['不存在']})


class ApprovalEvidence(unittest.TestCase):
    def test_a_review_for_a_different_speaker_does_not_approve_recordings(self):
        import sys
        sys.path.insert(0, str(KIT / 'scripts'))
        from verify_audio_manifests import audition_errors
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'review.md'
            p.write_text('voice: example\nmodel_sha256: '+ 'a'*64 +'\nconfig_sha256: '+ 'b'*64 +'\nspeaker_id: 0\nlistener: Test Listener\ndate: 2026-01-01\nverdict: pass\n')
            identity = ('example', 'a'*64, 'b'*64, 1)
            self.assertIn('recording voice/model/config/speaker differs from the passed audition', audition_errors(p, 'example', {identity}))

class SpeechInput(unittest.TestCase):
    def test_ukrainian_character_model_keeps_the_transcript_but_can_read_its_input(self):
        from normalise_model import prepare_model_text
        transcript = 'Ґанок. Пʼять. Україна.'
        spoken = prepare_model_text(transcript, {'phoneme_type': 'text', 'language': {'family': 'uk'}})
        self.assertEqual(spoken, "ґанок. п'ять. україна.")
        self.assertEqual(transcript, 'Ґанок. Пʼять. Україна.')
        self.assertEqual(prepare_model_text(transcript, {'phoneme_type': 'espeak'}), transcript)

if __name__ == '__main__': unittest.main()
