# Course-owned data files

These are copied into a course by `kit new`. They are **not** shipped in the
kit's own `data/` directory, and that distinction is the whole point of this
folder.

Hugo merges module data with project data and emits a warning when a project
file shadows a module file of the same name. Under `--panicOnWarning` — which
every course build uses — that warning is a hard failure. So a template the kit
ships in `data/` does not scaffold a course; it breaks it, on the day the course
adopts the module, with an error that names data precedence rather than the
empty placeholder that caused it.

`data/accents.yaml` stays in the kit's `data/`, because it is the opposite kind
of file: one registry, owned by the platform, that no course may hold its own
copy of. The website carried a copy and that is exactly the failure this folder
prevents in the other direction.

Rule of thumb: if every course has its own version, it belongs here. If there is
one version for the whole organisation, it belongs in `data/`.
