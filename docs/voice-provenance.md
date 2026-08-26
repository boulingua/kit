# The lessac provenance problem

**Every voice this organisation has shipped audio with descends from a
research-only, non-commercial base model.** efl, fle and daf have 323 audio
manifests between them, all published under CC BY-SA 4.0, which grants every
downstream recipient the right to use the work commercially. boulingua cannot
pass on rights it does not hold.

## The chain, from primary sources

1. **The Blizzard 2013 Lessac corpus is non-commercial only.**
   <https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/> —
   "This data is released under a license for non-commercial use only." The
   licence agreement grants a non-transferable licence without the right to
   sub-licence, and explicitly excludes "the development, marketing,
   commercialisation, sale or licencing of voice synthesis … products".

2. **`en_US-lessac-medium` is trained from scratch on that corpus.** Its model
   card names the CSTR dataset and states "Trained from scratch."

3. **Our voices are fine-tuned from it.** Verified individually, model card by
   model card, not inferred:

   | course | voice | Training line |
   |---|---|---|
   | `efl` | `en_GB-alba-medium` | "Finetuned from U.S. English lessac voice (medium quality)." |
   | `fle` | `fr_FR-siwis-medium` | "Finetuned from U.S. English lessac voice (medium quality)" |
   | `daf` | `de_DE-thorsten-medium` | refined from a U.S. English lessac voice, medium quality |
   | `nsf` | `no_NO-talesyntese-medium` | "Fine-tuned from U.S. English lessac voice (medium quality)." |
   | `nvt` | `nl_NL-ronnie-medium` | "Finetuned from U.S. English lessac voice (medium quality)" |

4. **Upstream reaches the same conclusion.** `ku_TR-berfin_renas-medium`, same
   provenance, declares **CC BY-NC 4.0** — "free for non-commercial use with
   attribution; commercial use restricted due to Blizzard 2013 base model" —
   and names `en_US-lessac-medium` as the cause. This is not our reading of
   someone else's licence; it is the maintainers' own.

## Why the registry did not catch it

Every one of those five voices advertises an allowlist-clean **dataset**
licence — CC0, CC BY 4.0. The encumbrance is in the **Training** line, and
`voices.yml` had no field for provenance at all. A check reading only the
dataset licence passes all of them, and a sweep of the upstream catalogue found
**76 of 175 voices declare a lessac fine-tune** while advertising a clean
dataset licence. The registry was asking the wrong question, carefully.

## What is not yet decided

This is a derived-weights argument. Whether a fine-tuned model's weights are a
derivative work of the base model's training corpus is a question a lawyer
should answer, not a build gate — and the conservative reading is not the only
reading. What is not in doubt is that the question exists, that it was never
asked, and that 323 audio files are already published.

**The conservative position, pending advice: treat lessac-derived voices as
NonCommercial and therefore incompatible with CC BY-SA 4.0.**

## What is available instead

`no_NO-nvcc-medium` — the alternative already listed on nsf's own row — states
"Trained from scratch." on a live CC0 dataset from the National Library of
Norway. It is clean, and it is the model for what a replacement looks like:
trained from scratch, not warm-started from lessac.

Finding equivalents for German, French and English is the substantive work,
and it is the difference between removing 323 audio files and regenerating
them.

---

## Resolved — 2026-08-26

All five voices are replaced with from-scratch models, each verified at its
model card AND at its dataset's own page:

| course | was | now | training | dataset licence | speakers |
|---|---|---|---|---|---|
| `efl` | `en_GB-alba-medium` | `en_GB-cori-medium` | from scratch | public domain (LibriVox) | 1 |
| `fle` | `fr_FR-siwis-medium` | `fr_FR-mls-medium` | from scratch | CC BY 4.0 (MLS) | 125 |
| `daf` | `de_DE-thorsten-medium` | `de_DE-mls-medium` | from scratch | CC BY 4.0 (MLS) | 236 |
| `nsf` | `no_NO-talesyntese-medium` | `no_NO-nvcc-medium` | from scratch | CC0 (Nasjonalbiblioteket) | 10 |
| `nvt` | `nl_NL-ronnie-medium` | `nl_NL-mls-medium` | from scratch | CC BY 4.0 (MLS) | 52 |

Multilingual LibriSpeech solved three of the five at once, and it is CC BY 4.0
— so attribution is now an OBLIGATION, carried in each course's NOTICE.md and
checked by gate A4 rather than left to good intentions.

Every voice returns to `status: candidate`. A changed voice needs a fresh
audition, and the new corpora make that more than a formality: MLS and LibriVox
are read audiobook speech, so these voices are fluent and literary where the
old ones were conversational. For a course teaching everyday dialogue that is a
real pedagogical difference, and it is exactly what an audition is for.

The 1,220 already-published clips were generated with the blocked voices and
are withheld — `file` moved to `file_withheld`, transcripts still rendering,
recordings still on disk. Every clip has a transcript, verified, so this costs
the audio and no teaching content. Restoring is one command once the clips are
regenerated.
