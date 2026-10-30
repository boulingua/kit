"""Build an offline listening page from completed audition receipts."""
from html import escape
import json
from pathlib import Path


def build_index(output):
    sections=[]
    for path in sorted(Path(output).glob('*.json')):
        receipt=json.loads(path.read_text())
        if not {'code','voice','samples'} <= receipt.keys():continue
        code=receipt['code'];cards=[]
        for name,sample in receipt['samples'].items():
            cards.append(f'''<div class="sample"><h3>{escape(name.title())}</h3>
<audio controls preload="none" aria-label="{escape(code+' '+name)}" src="{escape(sample['file'],quote=True)}"></audio>
<details><summary>Transcript</summary><p lang="{escape(receipt['voice'].split('-')[0].replace('_','-'))}">{escape(sample['transcript'])}</p></details>
<p class="meta">{sample['seconds']} seconds · {sample['sample_rate']} Hz · mono</p></div>''')
        sections.append(f'''<section id="{escape(code)}"><h2>{escape(code.upper())}</h2>
<p>{escape(receipt['voice'])} · speaker {receipt['speaker_id']} · listening review pending</p>
<div class="samples">{''.join(cards)}</div>
<p><a href="{escape(code)}-listening.md">Listening sheet</a> · <a href="{escape(code)}.json">Generation receipt</a> · <a href="{escape(code)}-MODEL_CARD.txt">Upstream model card</a></p></section>''')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boulingua voice previews</title><style>
body{font:17px/1.6 system-ui,sans-serif;color:#172435;background:#f4f6f8;margin:0}main{max-width:1120px;margin:auto;padding:28px}
h1{font-size:2rem}section{background:white;border:1px solid #cbd3de;border-radius:10px;padding:20px;margin:24px 0}h2{margin:0}
.samples{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:24px}audio{width:100%}
a{color:#16569c}summary{cursor:pointer;text-decoration:underline}summary:focus-visible,a:focus-visible{outline:3px solid #16569c;outline-offset:3px}
.meta{font-size:.85rem;color:#465568}details p{white-space:normal}footer{padding:20px 0}</style>
<main><h1>Boulingua voice previews</h1><p>Local samples for pronunciation review. Listen to the dialogue, vocabulary and continuous reading alongside their transcripts. Texts are review drafts.</p>
<p>Audio generation and technical checks are complete for the samples shown. A competent listener still needs to assess pronunciation, stress, intonation and teaching suitability. No voice has been automatically approved.</p>
'''+''.join(sections)+'''<footer>No selected synthesis model: Arabic, Japanese, Latin and Turkish. Human recordings with documented permission or transcripts remain available paths. This page uses no external services.</footer></main></html>'''
    (Path(output)/'index.html').write_text(html,encoding='utf-8')
    return len(sections)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',type=Path);a=ap.parse_args()
    print(f'{build_index(a.output)} voice sets indexed')
