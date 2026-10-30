#!/usr/bin/env python3
"""Validate catalogue sources and the committed discovery data they produce."""
from pathlib import Path
import subprocess
import sys
import yaml

def main():
    repo=Path(sys.argv[1]).resolve()
    cfg=yaml.safe_load((repo/'boulingua.yml').read_text()) or {}
    if cfg.get('kind')!='catalogue':
        print('A22 n/a: not a resource catalogue');return 0
    checks=[['validate_sources.py'],['check_commercial.py'],['build_overview.py','--check'],['validate_network_data.py']]
    bad=0
    for script,*args in checks:
        path=repo/'_scripts'/script
        if not path.is_file():print(f'::error::missing catalogue check {script}');bad+=1;continue
        result=subprocess.run([sys.executable,str(path),*args],cwd=repo)
        bad+=int(result.returncode!=0)
    return int(bool(bad))
if __name__=='__main__':raise SystemExit(main())
