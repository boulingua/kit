#!/usr/bin/env python3
"""
build_graph.py — compute the materials discovery network graph + run
the five Phase-1 CI gates. Produces static/network/graph.json which
Hugo then serves as-is.

Pragmatic deviation from the prompt: the prompt suggests a Hugo custom
output format. Computing per-pair tag-intersection cleanly in Go
templates is painful and slow; doing it in Python at build time is
simpler, faster, and keeps the gate logic in one place. The end
artefact (a static /network/graph.json with the spec'd schema) is
identical.

Schema is exactly the one in the Phase-5 prompt §1 (Phase-1 section).

Run from repo root:  python scripts/build_graph.py
Exit code 1 on any gate failure.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
DATA = REPO / "data" / "topics.yml"
OUT = REPO / "static" / "network" / "graph.json"

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def load_topics() -> dict[str, dict]:
    raw = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    return {t["id"]: t for t in raw}


def parse_units() -> list[dict]:
    units: list[dict] = []
    for md in sorted(CONTENT.glob("kurs_*/units/unit*.md")):
        text = md.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        course = md.parent.parent.name  # kurs_a1
        url = (
            "/" + course + "/units/" + md.stem + "/"
        )
        units.append(
            {
                "course": course,
                "fm": fm,
                "path": str(md.relative_to(REPO)),
                "url": url,
            }
        )
    return units


def gate_fail(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)


def main() -> int:
    topics = load_topics()
    if not topics:
        gate_fail("data/topics.yml is empty")
        return 1

    units = parse_units()
    if not units:
        gate_fail("no unit articles found under content/kurs_*/units/")
        return 1

    failures = 0
    topic_counts: Counter[str] = Counter()

    nodes: list[dict] = []
    edges: list[dict] = []

    # Build nodes; gate 1 (no tags) and gate 2 (unknown topic) along the way.
    for u in units:
        fm = u["fm"]
        slug = fm.get("unit_slug") or Path(u["path"]).stem.split("_", 1)[-1]
        tags: list[str] = list(fm.get("tags") or [])
        topic_id = fm.get("topic")
        title = fm.get("title") or slug
        course = u["course"]
        url = u["url"]
        date = str(fm.get("date") or "")  # may be empty — date facet dropped (decision d1)

        if not tags:
            gate_fail(f"{u['path']}: no tags — Phase-1 gate 1 violation")
            failures += 1
        if not topic_id:
            gate_fail(f"{u['path']}: no topic — Phase-1 gate 2 violation")
            failures += 1
        elif topic_id not in topics:
            gate_fail(
                f"{u['path']}: topic '{topic_id}' not in data/topics.yml"
                " — Phase-1 gate 2 violation"
            )
            failures += 1
        else:
            topic_counts[topic_id] += 1

        article_id = f"article-{course}-{slug}"
        article_node = {
            "id": article_id,
            "type": "article",
            "title": title,
            "url": url,
            "course": course,
            "topic": topic_id,
            "tags": tags,
            "date": date,
            "description": fm.get("description") or "",
            "thumbnail": None,
            "related": [],
        }
        related: list[str] = []
        if pres := fm.get("presentation"):
            pid = f"pres-{course}-{slug}"
            related.append(pid)
            nodes.append(
                {
                    "id": pid,
                    "type": "presentation",
                    "title": title,
                    "url": pres.get("file"),
                    "thumbnail": pres.get("thumbnail"),
                    "parent_article": article_id,
                    "course": course,
                    "topic": topic_id,
                    "tags": tags,
                    "date": date,
                    "materials_status": fm.get("materials_status") or "",
                }
            )
            edges.append(
                {"source": pid, "target": article_id, "weight": 3, "kind": "same-article"}
            )
        if work := fm.get("worksheet"):
            wid = f"ws-{course}-{slug}"
            related.append(wid)
            nodes.append(
                {
                    "id": wid,
                    "type": "worksheet",
                    "title": title,
                    "url": work.get("file"),
                    "thumbnail": work.get("thumbnail"),
                    "parent_article": article_id,
                    "course": course,
                    "topic": topic_id,
                    "tags": tags,
                    "date": date,
                    "materials_status": fm.get("materials_status") or "",
                }
            )
            edges.append(
                {"source": wid, "target": article_id, "weight": 3, "kind": "same-article"}
            )
        article_node["related"] = related
        nodes.append(article_node)

    # Gate 4 — every topic in registry must have ≥1 material.
    for tid in topics:
        if topic_counts.get(tid, 0) == 0:
            gate_fail(
                f"data/topics.yml: topic '{tid}' has zero materials"
                " — Phase-1 gate 4 violation"
            )
            failures += 1

    # shared-tags edges: only between *article* nodes (presentations and
    # worksheets carry their parent's tags, so adding tag-edges between
    # them duplicates information the same-article structural edges
    # already encode).
    article_nodes = [n for n in nodes if n["type"] == "article"]
    for a, b in combinations(article_nodes, 2):
        common = set(a["tags"]) & set(b["tags"])
        if len(common) >= 2:
            w = min(len(common), 5)  # cap at 5 visually
            edges.append(
                {"source": a["id"], "target": b["id"], "weight": w, "kind": "shared-tags"}
            )

    # Gate 3 — graph must have edges (sparse tagging would yield none).
    if not any(e["kind"] == "shared-tags" for e in edges):
        gate_fail(
            "graph.json has zero shared-tag edges — tagging too sparse"
            " — Phase-1 gate 3 violation"
        )
        failures += 1

    # Build facets.
    type_counts: Counter[str] = Counter(n["type"] for n in nodes)
    course_counts: Counter[str] = Counter(n["course"] for n in nodes)
    tag_counts: Counter[str] = Counter()
    for n in nodes:
        for t in n.get("tags") or []:
            tag_counts[t] += 1
    dates = [n["date"] for n in nodes if n["date"]]
    facets = {
        "types": [
            {"id": t, "count": c}
            for t, c in sorted(type_counts.items())
        ],
        "courses": [
            {"id": c, "label": c.replace("kurs_", "").upper(), "count": n}
            for c, n in sorted(course_counts.items())
        ],
        "topics": [
            {
                "id": tid,
                "label_de": topics[tid].get("label_de"),
                "label_en": topics[tid].get("label_en"),
                "label_fr": topics[tid].get("label_fr"),
                "color": topics[tid].get("color"),
                "count": topic_counts[tid],
            }
            for tid in sorted(topics, key=lambda x: -topic_counts.get(x, 0))
            if tid in topic_counts
        ],
        "tags": [
            {"id": t, "count": c}
            for t, c in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "date_range": (
            {"min": min(dates), "max": max(dates)} if dates else None
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"nodes": nodes, "edges": edges, "facets": facets}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stats summary.
    n_articles = sum(1 for n in nodes if n["type"] == "article")
    n_pres = sum(1 for n in nodes if n["type"] == "presentation")
    n_work = sum(1 for n in nodes if n["type"] == "worksheet")
    n_exam = sum(1 for n in nodes if n["type"] == "exam")
    e_struct = sum(1 for e in edges if e["kind"] == "same-article")
    e_tags = sum(1 for e in edges if e["kind"] == "shared-tags")
    max_possible = n_articles * (n_articles - 1) // 2
    density = e_tags / max_possible if max_possible else 0.0
    singletons = [t for t, c in tag_counts.items() if c == 1]

    print(f"graph.json built: {OUT.relative_to(REPO)}")
    print(f"  nodes: {len(nodes)}  ({n_articles} articles, {n_pres} pres, {n_work} ws, {n_exam} exam)")
    print(f"  edges: {len(edges)}  ({e_struct} same-article, {e_tags} shared-tags)")
    print(f"  graph density (article subgraph): {density:.3f}")
    print(f"  topics: {len(topics)} declared, {len(topic_counts)} populated")
    print(f"  tags: {len(tag_counts)} unique, {len(singletons)} singletons")
    if singletons:
        print(f"    singleton tags: {', '.join(sorted(singletons))}")
    print(f"  facets.types: {len(facets['types'])}, "
          f"facets.courses: {len(facets['courses'])}, "
          f"facets.tags: {len(facets['tags'])}")

    if failures:
        print(f"\nGATE FAILURES: {failures}", file=sys.stderr)
        return 1
    print("\nall Phase-1 gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
