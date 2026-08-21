# Font attribution

Every font file shipped in this repository, its upstream release, and the
licence text bundled with it. Gate A4 fails if a `.woff2`, `.otf` or `.ttf`
exists here with no row below.

This file is not a formality. Seven `.woff2` files shipped in the previous
template with the OFL URL in their own name table and **no licence text
anywhere in the repository** — an open compliance gap, since OFL §5 requires
the licence to travel with the font. And a single `OFL.txt` would have been
the wrong fix: Permanent Marker is Apache-2.0, not OFL, so each family
carries its own upstream licence file with its own copyright notice.

## Families

| Family | Version | Release | Upstream | Licence | Licence file | Tiers |
|---|---|---|---|---|---|---|
| source-sans-3 | 3.052 | `3.052R` | <https://github.com/adobe-fonts/source-sans> | OFL 1.1 | [`LICENSES/OFL-1.1-SourceSans3.txt`](LICENSES/OFL-1.1-SourceSans3.txt) | core, cyrillic, greek, latin-ext |
| jetbrains-mono | 2.304 | `v2.304` | <https://github.com/JetBrains/JetBrainsMono> | OFL 1.1 | [`LICENSES/OFL-1.1-JetBrainsMono.txt`](LICENSES/OFL-1.1-JetBrainsMono.txt) | core, cyrillic, greek, latin-ext |
| noto-sans | 2.015 | `NotoSans-v2.015` | <https://github.com/notofonts/latin-greek-cyrillic> | OFL 1.1 | [`LICENSES/OFL-1.1-NotoSans.txt`](LICENSES/OFL-1.1-NotoSans.txt) | latin-ext |
| permanent-marker | 1.001 | `—` | <https://www.fontdiner.com> | Apache-2.0 | [`LICENSES/Apache-2.0-PermanentMarker.txt`](LICENSES/Apache-2.0-PermanentMarker.txt) | core |

## Subsetting

Web faces are cut from the upstream release by `design/build_fonts.py`:

```
pyftsubset <src> --flavor=woff2 --with-zopfli --no-hinting --desubroutinize --unicodes=<tier ranges> --layout-features=<computed retention set>
```

Ranges are declared by codepoint in `design/fonts.yaml`, never by Google
range name — Google's `cyrillic` stops at U+045F and Ukrainian ґ is U+0490,
so a name-based subset drops a letter that is present in the face.

Print faces are **not** subset. XeLaTeX has no `unicode-range`, and a deck
needing one Greek word in an otherwise Latin course must still find the glyph.

## Shipped files (33 web, 34 print)

### Web — `static/fonts/`

```
jetbrains-mono-400.core.woff2
jetbrains-mono-400.cyrillic.woff2
jetbrains-mono-400.greek.woff2
jetbrains-mono-400.latin-ext.woff2
jetbrains-mono-700.core.woff2
jetbrains-mono-700.cyrillic.woff2
jetbrains-mono-700.greek.woff2
jetbrains-mono-700.latin-ext.woff2
noto-sans-400.latin-ext.woff2
source-sans-3-400.core.woff2
source-sans-3-400.cyrillic.woff2
source-sans-3-400.greek.woff2
source-sans-3-400.latin-ext.woff2
source-sans-3-400i.core.woff2
source-sans-3-400i.cyrillic.woff2
source-sans-3-400i.greek.woff2
source-sans-3-400i.latin-ext.woff2
source-sans-3-600.core.woff2
source-sans-3-600.cyrillic.woff2
source-sans-3-600.greek.woff2
source-sans-3-600.latin-ext.woff2
source-sans-3-600i.core.woff2
source-sans-3-600i.cyrillic.woff2
source-sans-3-600i.greek.woff2
source-sans-3-600i.latin-ext.woff2
source-sans-3-700.core.woff2
source-sans-3-700.cyrillic.woff2
source-sans-3-700.greek.woff2
source-sans-3-700.latin-ext.woff2
source-sans-3-700i.core.woff2
source-sans-3-700i.cyrillic.woff2
source-sans-3-700i.greek.woff2
source-sans-3-700i.latin-ext.woff2
```

### Print — `fonts/<tier>/`

```
core/JetBrainsMono-Bold.ttf
core/JetBrainsMono-Regular.ttf
core/PermanentMarker-Regular.ttf
core/SourceSans3-Bold.otf
core/SourceSans3-BoldIt.otf
core/SourceSans3-It.otf
core/SourceSans3-Regular.otf
core/SourceSans3-Semibold.otf
core/SourceSans3-SemiboldIt.otf
cyrillic/JetBrainsMono-Bold.ttf
cyrillic/JetBrainsMono-Regular.ttf
cyrillic/SourceSans3-Bold.otf
cyrillic/SourceSans3-BoldIt.otf
cyrillic/SourceSans3-It.otf
cyrillic/SourceSans3-Regular.otf
cyrillic/SourceSans3-Semibold.otf
cyrillic/SourceSans3-SemiboldIt.otf
greek/JetBrainsMono-Bold.ttf
greek/JetBrainsMono-Regular.ttf
greek/SourceSans3-Bold.otf
greek/SourceSans3-BoldIt.otf
greek/SourceSans3-It.otf
greek/SourceSans3-Regular.otf
greek/SourceSans3-Semibold.otf
greek/SourceSans3-SemiboldIt.otf
latin-ext/JetBrainsMono-Bold.ttf
latin-ext/JetBrainsMono-Regular.ttf
latin-ext/NotoSans-Regular.ttf
latin-ext/SourceSans3-Bold.otf
latin-ext/SourceSans3-BoldIt.otf
latin-ext/SourceSans3-It.otf
latin-ext/SourceSans3-Regular.otf
latin-ext/SourceSans3-Semibold.otf
latin-ext/SourceSans3-SemiboldIt.otf
```
## Upstream sources — `design/fonts/src/`

Only the faces `fonts.yaml` actually names are kept. The full releases run to
339 MB between them — the Noto archive alone is 113 MB because it ships every
format — and committing that into a repository to use 3 MB of it would be a
poor trade. Each file below is the unmodified upstream artefact, so the build
is reproducible offline and the subsetter's input is auditable.

| File | Size | SHA-256 (first 16) | Upstream release |
|---|---|---|---|
| `JetBrainsMono-Bold.ttf` | 271 KB | `5590990c82e09739` | [JetBrains/JetBrainsMono v2.304](https://github.com/JetBrains/JetBrainsMono/releases/tag/v2.304) `fonts/ttf/` |
| `JetBrainsMono-Regular.ttf` | 267 KB | `a0bf60ef0f83c5ed` | [JetBrains/JetBrainsMono v2.304](https://github.com/JetBrains/JetBrainsMono/releases/tag/v2.304) `fonts/ttf/` |
| `NotoSans-Regular.ttf` | 806 KB | `f5f552c8c5edb61f` | [notofonts/latin-greek-cyrillic NotoSans-v2.015](https://github.com/notofonts/latin-greek-cyrillic/releases/tag/NotoSans-v2.015) `NotoSans/full/ttf/` |
| `SourceSans3-Bold.otf` | 335 KB | `7776ddb9f3eb5868` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
| `SourceSans3-BoldIt.otf` | 237 KB | `05e97d9adc010596` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
| `SourceSans3-It.otf` | 233 KB | `430b9f0eb1170be0` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
| `SourceSans3-Regular.otf` | 327 KB | `08df266400933d31` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
| `SourceSans3-Semibold.otf` | 331 KB | `36f1cd2c344aa310` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
| `SourceSans3-SemiboldIt.otf` | 234 KB | `81204ed282543df2` | [adobe-fonts/source-sans 3.052R](https://github.com/adobe-fonts/source-sans/releases/tag/3.052R) `OTF/` |
