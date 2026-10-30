#!/usr/bin/env python3
"""Run representative built-site accessibility and interaction journeys."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
KIT=Path(__file__).resolve().parents[1]
def main():
    repo=Path(sys.argv[1]).resolve()
    if not shutil.which('node'):
        print('::error::Node 22 is required for browser verification');return 1
    if not (KIT/'node_modules/@playwright/test').is_dir():
        print('::error::Run npm ci in kit and npx playwright install chromium first');return 1
    env={**os.environ,'BROWSER_ARTIFACTS':str(repo/'build/browser')}
    return subprocess.run(['node',str(KIT/'tests/site-browser.cjs'),str(repo)],cwd=KIT,env=env).returncode
if __name__=='__main__':raise SystemExit(main())
