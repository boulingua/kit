from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import tempfile
import sys

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audio_content', KIT / 'audio/build_audio.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)
FIXTURES = Path(__file__).parent / 'fixtures/lessons'


class SpeechContent(unittest.TestCase):
    def segments(self, name):
        return audio.extract_segments((FIXTURES / (name+'.md')).read_text().split('---', 2)[-1])

    def test_weather_dialogue_preserves_all_three_speakers(self):
        dialogue = next(s for s in self.segments('weather') if s[0] == 'dialogue')
        for turn in ['La radio :', 'Maman, il pleut à Strasbourg', 'Ce soir seulement, ma chérie']:
            self.assertIn(turn, dialogue[1])
            self.assertIn(turn, dialogue[2])

    def test_opening_letter_turn_is_spoken_as_well_as_transcribed(self):
        dialogue = next(s for s in self.segments('letter') if s[0] == 'dialogue')
        self.assertTrue(dialogue[2].startswith("Léa : J'ai écrit"))
        self.assertIn('Répondez vite !', dialogue[2])
        self.assertEqual(' '.join(dialogue[1].split()), ' '.join(dialogue[2].split()))

    def test_emphasis_is_not_a_stage_direction(self):
        text='> **Ana:** *This is an italic spoken sentence.*\n> *(The door opens.)*\n> **Ben:** **This is bold speech.**'
        segment=audio.extract_segments(text)[0]
        self.assertIn('italic spoken sentence', segment[2])
        self.assertIn('bold speech', segment[2])
        self.assertNotIn('The door opens', segment[2])
        self.assertIn('The door opens', segment[1])

    def test_english_story_and_vocabulary_are_selected_without_keys_or_rubrics(self):
        story='Mia arrives at her new school. She meets Theo at the classroom door and asks him his name. They sit together and look at the map on the wall.'
        body='## Lead-in story\n'+story+'\n## 2. Input {#input}\n### Vocabulary\n*hello, good morning, goodbye, thank you*\n'
        body+='{{< details title="Answer key" >}}\n> '+('SECRET '*20)+'\n{{< /details >}}\n'
        body+='## 4. Produce {#apply}\n| Criterion | Score |\n| --- | --- |\n| First | 1 |\n| Second | 1 |\n| Third | 1 |\n| Fourth | 1 |\n'
        segments=audio.extract_segments(body,'en')
        self.assertEqual([s[0] for s in segments],['texte','vocab'])
        self.assertEqual(segments[0][1],story)
        self.assertNotIn('SECRET',str(segments))
        self.assertNotIn('Criterion',str(segments))

    def test_foreign_mediation_source_and_grammar_tables_are_not_voiced_as_target_vocabulary(self):
        body='## Input {#input}\n### German source\n> '+('German source text. '*20)+'\n### Grammar\n| Person | Verb |\n| --- | --- |\n| I | am |\n| you | are |\n| he | is |\n| we | are |\n'
        self.assertEqual(audio.extract_segments(body,'en'),[])

    def test_teacher_and_exam_quotes_are_not_spoken(self):
        body='## Teacher notes {#teacher-notes}\n> '+('SECRET TEACHER TEXT '*20)+'\n## Exam {#exam}\n> '+('ASSESSMENT TEXT '*20)
        self.assertEqual(audio.extract_segments(body,'en'),[])

    def test_plain_intro_and_following_dialogue_keep_their_source_order(self):
        story='A new student walks through the door of the classroom and looks for a free seat. Her friend is already waiting by the window with two books.'
        body='## Lead-in story\n'+story+'\n\n> **Ana:** Hello, this is my first day at school.\n> **Ben:** Welcome, please sit here.'
        segments=audio.extract_segments(body,'en')
        self.assertEqual([s[0] for s in segments],['texte','dialogue'])
        self.assertEqual(segments[0][1],story)

    def test_persistent_synthesis_rejects_missing_phonemes_before_writing_audio(self):
        calls=[]
        model=SimpleNamespace(phonemize=lambda text:[['a','MISSING']],
                              config=SimpleNamespace(phoneme_id_map={'a':[1]}),
                              synthesize_wav=lambda *args:calls.append(args))
        modules={'onnxruntime':SimpleNamespace(), 'piper':SimpleNamespace(PiperVoice=object),
                 'piper.config':SimpleNamespace(PiperConfig=object,SynthesisConfig=object)}
        with tempfile.TemporaryDirectory() as td, patch.dict(audio._PIPER_VOICES,{'test-model':model}), patch.dict(sys.modules,modules):
            wav=Path(td)/'output.wav';wav.write_bytes(b'old output')
            with self.assertRaisesRegex(RuntimeError,'Missing phoneme'):
                audio.synth_persistent('A text',wav,'test-model')
            self.assertFalse(wav.exists());self.assertEqual(calls,[])

    def test_cache_fingerprint_binds_the_synthesis_backend(self):
        self.assertNotEqual(audio.synthesis_fingerprint('Text','model','config',0,'piper-cli'),
                            audio.synthesis_fingerprint('Text','model','config',0,'piper-python/1thread'))

    def test_vocabulary_uses_terms_instead_of_ratings_or_foreign_source_column(self):
        body='## Input {#input}\n### Vocabulaire\n| Force | Verbe | Exemple |\n| --- | --- | --- |\n'
        body+='\n'.join('| ★ | '+t+' | exemple |' for t in ["J’adore", "J’aime", "Je n’aime pas", "Je déteste"])
        segment=audio.extract_segments(body,'fr')[0]
        self.assertIn('Je déteste',segment[2]);self.assertNotIn('★',segment[2]);self.assertNotIn('exemple',segment[2])
        body=body[:body.index('| Force')]+ '| Allemand (source) | Français (cible) | Emploi |\n| --- | --- | --- |\n'
        body+='\n'.join('| SOURCE | '+t+' | contexte |' for t in ['bonjour','salut','merci','pardon'])
        self.assertEqual(audio.extract_segments(body,'fr')[0][1],'bonjour · salut · merci · pardon')

    def test_parallel_target_vocabulary_columns_are_all_retained_in_row_order(self):
        body='## Input {#input}\n### Vocabulaire\n| Les fruits | Les légumes | Au marché |\n| --- | --- | --- |\n| pomme | carotte | kilo |\n| poire | salade | prix |'
        self.assertEqual(audio.extract_segments(body,'fr')[0][1],'pomme · carotte · kilo · poire · salade · prix')

    def test_grammar_table_nested_under_vocabulary_is_not_spoken(self):
        body='## Input {#input}\n### Vocabulaire\n| Personne | *aimer* |\n| --- | --- |\n| je | aime |\n| tu | aimes |\n| il | aime |\n| nous | aimons |'
        self.assertEqual(audio.extract_segments(body,'fr'),[])

    def test_vocabulary_list_keeps_long_cells_and_omits_intro_label(self):
        body='## Input {#input}\n### Vocabulaire\n**Quelques thèmes utiles :** *le sport, la musique, les maths, le français.*\n'
        self.assertEqual(audio.extract_segments(body,'fr')[0][1],'le sport · la musique · les maths · le français')
        self.assertEqual(audio.extract_blocks('*premise, claim, essayist’s *I*, address.*',inline_vocab=True)[0][1], 'premise · claim · essayist’s I · address')
        long='le gigot d’agneau, le poulet rôti, le poisson, les pâtes, les haricots verts'
        table='| Catégorie | Aliments et mots utiles |\n| --- | --- |\n'+ '\n'.join('| plat | '+x+' |' for x in [long,'la soupe','la salade','le pain'])
        self.assertIn(long,audio.extract_blocks(table,lang='fr')[0][1])

    def test_explicit_iso_source_labels_and_mixed_openings_are_withheld(self):
        body='## Situation de départ (français / allemand)\n> **Frau Weber:** Entschuldigung, was hat er gesagt?\n> **Léo:** Il a annoncé une activité.\n'
        body+='## Input {#input}\n### Texte à médier (original, DE)\n> '+('Liebe Camille, gestern war der Europatag. '*10)+'\n'
        body+='### Texte de Camille\n> '+('Camille présente sa classe et ses activités préférées. '*6)
        segments=audio.extract_segments(body,'fr')
        self.assertEqual(len(segments),1);self.assertNotIn('Entschuldigung',str(segments));self.assertNotIn('Europatag',str(segments))
        self.assertEqual(len(audio.withheld_foreign_sections(body,'fr')),2)
        self.assertFalse(audio.foreign_heading('Le texte de Camille','fr'))
