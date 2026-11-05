#!/usr/bin/env python3
"""Build the shared teaching examples with the current kit checkout."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
from new_course import scaffold
from html_tree import parse

KIT=Path(__file__).resolve().parents[1]
def main():
    root=KIT/'build/example'
    scaffold('daf',root)
    shutil.copytree(KIT/'example',root/'content',dirs_exist_ok=True)
    # Match the development workspace's module identity across major releases.
    module=(KIT/'go.mod').read_text().splitlines()[0].split()[1]
    major=module.rsplit('/v',1)[1] if '/v' in module else '1'
    for name in ['go.mod','hugo.toml']:
        path=root/name
        text=re.sub(r'github\.com/boulingua/kit(?:/v[0-9]+)?',module,path.read_text())
        if name=='go.mod':text=re.sub(re.escape(module)+r' v[^\s]+',module+' v'+major+'.0.0',text)
        path.write_text(text)
    # Exercise the current module, not the last published release.
    (root/'go.work').write_text('go 1.26.1\nuse '+str(KIT)+'\n')
    env={**os.environ,'HUGO_MODULE_WORKSPACE':str(root/'go.work')}
    subprocess.run([sys.executable,str(KIT/'bin/kit'),'build',str(root)],env=env,check=True)
    subprocess.run([sys.executable,str(KIT/'scripts/verify_eqs.py'),str(root/'public')],env=env,check=True)
    page=parse((root/'public/appendices/rendering-contract/index.html').read_text())
    for anchor in ['activate','previous-activation-heading']:
        matches=[n for n in page.walk() if n.attrs.get('id')==anchor]
        if len(matches)!=1: raise RuntimeError(f'heading contract lost or duplicated {anchor}')
    keys=[n for n in page.walk() if n.tag=='details' and n.attrs.get('data-role')=='key']
    if len(keys)!=3 or any('open' in n.attrs for n in keys):
        raise RuntimeError('the three answer forms must render as closed, marked keys')
    summaries=[n.text for key in keys for n in key.walk() if n.tag=='summary']
    if not all(summaries) or 'Solutions' not in summaries:
        raise RuntimeError('the summary parameter or translated answer label was lost')
    return 0
if __name__=='__main__':raise SystemExit(main())
