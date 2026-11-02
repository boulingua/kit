# Authored lesson fixtures

These unchanged lesson snapshots retain real path conventions, stimuli, tasks
and answer keys needed to reproduce generator defects. `SOURCES.json` records
the exact source repository, commit and original path. EFL, FLE and DaF carry
the same S. Le Boulanger MIT notice, retained here as `LICENSE`. Source-specific
author and attribution text remains in each snapshot.

The path fixture command is self-contained. Use
`python scripts/test_blg_paths.py --org-root .. efl fle daf` to additionally
compare live course URLs and presentation filenames with their preserved locks.
The live check is separate evidence and is not implied by a fixture-only pass.
