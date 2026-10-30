#!/usr/bin/env python3
"""Build the shared teaching examples with the current kit checkout."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
from new_course import scaffold

KIT=Path(__file__).resolve().parents[1]
def main():
    root=KIT/'build/example'
    scaffold('daf',root)
    shutil.copytree(KIT/'example',root/'content',dirs_exist_ok=True)
    # Exercise the current module, not the last published release.
    (root/'go.work').write_text('go 1.26.1\nuse '+str(KIT)+'\n')
    env={**os.environ,'HUGO_MODULE_WORKSPACE':str(root/'go.work')}
    subprocess.run([sys.executable,str(KIT/'bin/kit'),'build',str(root)],env=env,check=True)
    subprocess.run([sys.executable,str(KIT/'scripts/verify_eqs.py'),str(root/'public')],env=env,check=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
