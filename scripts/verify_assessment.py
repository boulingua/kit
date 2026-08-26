#!/usr/bin/env python3
"""Gate A13 — an exam's arithmetic adds up and its grading scale partitions it.

    verify_assessment.py REPO

Three things, and every one of them is a mistake a careful author still makes,
because none of it is visible when you read the page.

  Σ task points == the stated total. A paper whose tasks sum to 47 under a
  heading saying 45 marks two classes differently depending on which number the
  teacher trusts.

  The Notenschlüssel partitions 0…total exactly. Every score falls in one band,
  no score falls in two. A gap means a pupil with that mark has no grade; an
  overlap means they have two.

  The top band reaches the total and the bottom reaches zero. A scale topping
  out at 44 of 45 makes a perfect paper ungradeable.

WHERE THE DATA IS. Not in front matter — no exam page in this organisation
carries total_points or notenschluessel, and a gate written against those
fields would have examined nothing on 336 exams and reported success. It is in
the body, where the author actually wrote it: a "**Total.** N points." line,
per-task "(N BE)" headings, and a grading-scale callout of range/grade pairs.
Reading what is there beat requiring what is not.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TOTAL = re.compile(r"\*\*(?:Total|Gesamt|Punkte)\.?\*\*\s*(\d+)\s*(?:points?|Punkte|BE)", re.I)
# "~24 BE" and "ca. 24 BE" are how the Kursstufe papers write an approximate
# weighting, and a pattern demanding a bare digit read ten of them as carrying
# no points at all.
TASK = re.compile(r"^#{2,4}\s.*?\(\s*(?:~|ca\.?\s*|approx\.?\s*)?(\d+)\s*"
                  r"(?:BE|points?|Punkte)\)", re.M | re.I)
# The grade token, not just its digit. The Kursstufe grades on the 15-point
# scale written as 1+ / 1 / 1-, and capturing only the digit made three
# distinct bands look like the same grade repeated — reported as an error in
# 74 papers that were correct.
BAND = re.compile(r"(\d+)\s*[–—-]\s*(\d+)\s*\|\s*([1-6][+-]?)")
SCALE = re.compile(r"title=\"[^\"]*(?:Notenschl|grading scale)[^\"]*\"", re.I)


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    bad, checked, no_data, rehearsals = [], 0, [], 0

    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        if fm.get("page_type") != "exam":
            continue
        # A rehearsal drills one section of a larger paper and states no total
        # of its own. Ten of efl's Kl 13 exams are Kommunikationsprüfung
        # rehearsals, and requiring a full paper's arithmetic of them reported
        # twenty errors against pages that are correct. The distinction is
        # declared in front matter, not inferred from prose — inferring it
        # would let a genuinely incomplete paper hide behind a keyword.
        if fm.get("exam_scope") == "rehearsal":
            rehearsals += 1
            continue
        rel = md.relative_to(repo).as_posix()
        body = raw[m.end():]

        mt = TOTAL.search(body)
        tasks = [int(x) for x in TASK.findall(body)]
        bands = [(int(a), int(b), g) for a, b, g in BAND.findall(body)]
        if not mt and not tasks and not bands:
            no_data.append(rel)
            continue
        checked += 1

        if mt and tasks:
            total, s = int(mt.group(1)), sum(tasks)
            if s != total:
                bad.append(f"{rel}: tasks sum to {s} but the paper states {total}. "
                           f"Which number a teacher trusts changes the grade.")
        if not mt:
            bad.append(f"{rel}: no stated total")
        if not tasks:
            bad.append(f"{rel}: no task carries a point value")

        if bands:
            total = int(mt.group(1)) if mt else max(b for _, b, _ in bands)
            covered = sorted((lo, hi) for lo, hi, _ in bands)
            if covered[0][0] != 0:
                bad.append(f"{rel}: the grading scale starts at {covered[0][0]}, "
                           f"not 0 — a pupil below that has no grade")
            if covered[-1][1] != total:
                bad.append(f"{rel}: the grading scale tops out at {covered[-1][1]} "
                           f"of {total} — a perfect paper is ungradeable")
            for (l1, h1), (l2, h2) in zip(covered, covered[1:]):
                if l2 == h1 + 1:
                    continue
                if l2 <= h1:
                    bad.append(f"{rel}: bands {l1}–{h1} and {l2}–{h2} overlap — a "
                               f"score in the overlap has two grades")
                else:
                    bad.append(f"{rel}: gap between {h1} and {l2} — a score there "
                               f"has no grade")
            gs = [g for _, _, g in bands]
            if len(set(gs)) != len(gs):
                bad.append(f"{rel}: a grade appears in more than one band")
        elif mt:
            bad.append(f"{rel}: states a total but carries no grading scale")

    for b in bad[:20]:
        print(f"::error::{b}")
    if len(bad) > 20:
        print(f"::error::… and {len(bad) - 20} more")
    if no_data:
        print(f"::warning::{len(no_data)} exam page(s) carry no assessment data at "
              f"all — no total, no task points, no grading scale. Nothing here can "
              f"check a marking scheme that exists only in the author's head.")
        for x in no_data[:5]:
            print(f"::warning::    {x}")
    if not checked and not no_data:
        print("A13 n/a — this repo has no exam pages")
        return 0
    if bad:
        print(f"\nA13 FAIL — {len(bad)} problem(s) across {checked} exam(s)",
              file=sys.stderr)
        return 1
    if rehearsals:
        print(f"  {rehearsals} rehearsal paper(s) skipped — they drill a section "
              f"of a larger Klausur and state no total of their own")
    print(f"A13 OK — {checked} exam(s): tasks sum to the stated total, and the "
          f"grading scale partitions it with no gap and no overlap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
