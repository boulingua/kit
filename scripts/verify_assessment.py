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
TOTAL = re.compile(r"\*\*(?:Total|Gesamt|Punkte)(?:[.:]?\*\*\s*|\s*[:.]\s*)(\d+)\s*(?:points?|Punkte|BE)", re.I)
# "~24 BE" and "ca. 24 BE" are how the Kursstufe papers write an approximate
# weighting, and a pattern demanding a bare digit read ten of them as carrying
# no points at all.
TASK = re.compile(r"^#{2,4}\s.*?\(\s*(?:~|ca\.?\s*|approx\.?\s*)?(\d+)\s*"
                  r"(?:BE|points?|Punkte)\)", re.M | re.I)
# The grade token, not just its digit. The Kursstufe grades on the 15-point
# scale written as 1+ / 1 / 1-, and capturing only the digit made three
# distinct bands look like the same grade repeated — reported as an error in
# 74 papers that were correct.
BAND = re.compile(r"(\d+)\s*[–—-]\s*(\d+)\s*\|\s*([1-6][+-]?)(?=[\t ]*(?:\||\r?\n|$))")
SCALE = re.compile(r"title=\"[^\"]*(?:Notenschl|grading scale)[^\"]*\"", re.I)


def rubric_checks(body: str):
    """Check an actual criterion table without inventing school-grade bands.

    A rubric is additive; a table mapping overall performance to a score is not.
    Ambiguous or unsupported forms remain unverified by the caller.
    """
    plain = re.sub(r'[*_]', '', body)
    tables = re.findall(r'(?m)(?:^\|[^\n]*\|\s*\n){2,}', plain + '\n')
    rubrics = []
    for table in tables:
        rows = [[c.strip() for c in line.strip().strip('|').split('|')]
                for line in table.strip().splitlines()]
        header = rows[0]
        if not header or header[0].lower() not in {'kriterium', 'bereich', 'aufgabe'}:
            continue
        columns = [i for i, text in enumerate(header) if text.lower() == 'punkte']
        if len(columns) != 1:
            continue
        index = columns[0]; values, totals, errors = [], [], []
        for cells in rows[2:]:
            if len(cells) != len(header):
                errors.append('rubric table has inconsistent columns'); continue
            score_cell = cells[index]
            if re.fullmatch(r'(?i)summe|gesamt', cells[0]):
                score_cell = score_cell.removeprefix('/').strip()
            score = re.fullmatch(r'(?:(\d+)\s*[–—-]\s*)?(\d+)', score_cell)
            if not score:
                errors.append(f'unsupported criterion score: {cells[index]!r}'); continue
            low, high = int(score[1] or 0), int(score[2])
            if low > high:
                errors.append(f'reversed criterion range: {cells[index]}')
            if re.fullmatch(r'(?i)summe|gesamt', cells[0]):
                totals.append(high)
            else:
                values.append(high)
        rubrics.append((values, totals, errors))
    if len(rubrics) != 1:
        return None
    values, totals, errors = rubrics[0]
    if not values:
        errors.append('criterion rubric contains no scored criteria')
    maximum = sum(values)
    # The maximum must be stated independently of the component cells.
    for line in plain.splitlines():
        if re.search(r'(?i)rubrik|bewertung|bewertungsraster', line):
            match = re.search(r'(?i)\(\s*(?:max\.?\s*)?(\d+)\s*Punkte', line)
            if not match:
                match = re.search(r'(?i)\(Punkte,?\s*max\.?\s*(\d+)\)', line)
            if match:
                totals.append(int(match[1]))
            elif re.search(r'(?i)bewertungskriterien', line):
                match = re.search(r'\(0\s*[–—-]\s*(\d+)\)', line)
                if match: totals.append(int(match[1]))
    if not totals:
        errors.append('criterion rubric has no independently stated maximum')
    for total in set(totals):
        if total != maximum:
            errors.append(f'criterion maxima sum to {maximum}, but the rubric states {total}')
    for match in re.finditer(r'(?i)(?:bestanden|bestehen|bestehensgrenze|schwelle)[^\n]{0,90}', plain):
        clause = match[0]
        passing = re.search(r'(?i)\bab\s*(\d+)|(?:[:≥]\s*)(\d+)\s*(?:/|von)', clause)
        if passing:
            threshold = int(passing[1] or passing[2])
            if not 0 <= threshold <= maximum:
                errors.append(f'passing threshold {threshold} is outside 0–{maximum}')
        denominator = re.search(r'(?:/|von)\s*(\d+)', clause)
        if denominator and int(denominator[1]) != maximum:
            errors.append(f'passing rule denominator {denominator[1]} differs from rubric maximum {maximum}')
    return maximum, errors


def feedback_checks(body: str):
    """Verify exhaustive qualitative score bands without treating them as grades."""
    plain = re.sub(r'[*_]', '', body)
    for table in re.findall(r'(?m)(?:^\|[^\n]*\|\s*\n){2,}', plain + '\n'):
        rows = [[cell.strip() for cell in line.strip().strip('|').split('|')]
                for line in table.strip().splitlines()]
        if rows[0][0].lower() not in {'punkte', 'richtige antworten'}:
            continue
        bands = []
        for row in rows[2:]:
            match = re.fullmatch(r'(\d+)(?:\s*[–—-]\s*(\d+))?', row[0])
            if not match:
                return None
            bands.append((int(match[1]), int(match[2] or match[1])))
        if not bands:
            return None
        # Repeated single values can instead describe additive criteria in a
        # points-first table. That shape needs its own explicit classification.
        if len(set(bands)) != len(bands) and all(lo == hi for lo, hi in bands):
            return None
        claimed = []
        for line in plain.splitlines():
            if re.search(r'(?i)rubrik|bewertung', line):
                match = re.search(r'(?i)\(\s*(?:max\.?\s*)?(\d+)\s*Punkte', line)
                if match: claimed.append(int(match[1]))
            if re.search(r'(?i)bestanden|bestehen', line):
                match = re.search(r'(?i)\bvon\s+(\d+)\s+Punkten', line)
                if match: claimed.append(int(match[1]))
        if not claimed:
            return None
        maximum = claimed[0]; errors = []
        if len(set(claimed)) != 1:
            errors.append(f'feedback table has contradictory maximum claims: {sorted(set(claimed))}')
        counts = {score: 0 for score in range(maximum + 1)}
        for low, high in bands:
            if not 0 <= low <= high <= maximum:
                errors.append(f'feedback band {low}–{high} is outside 0–{maximum}'); continue
            for score in range(low, high + 1): counts[score] += 1
        gaps = [score for score, count in counts.items() if count == 0]
        overlaps = [score for score, count in counts.items() if count > 1]
        if gaps: errors.append(f'feedback table has no band for scores {gaps}')
        if overlaps: errors.append(f'feedback bands overlap at scores {overlaps}')
        return maximum, errors
    return None


def learner_scoring_text(body):
    from build_materials_latex import strip_callouts
    return re.sub(r'[*_]', '', strip_callouts(body)).split('\n## Quellen',1)[0]


def item_numbers(body):
    """Count visible answer slots, never numbering in hidden solution scripts."""
    from build_materials_latex import strip_callouts
    visible = strip_callouts(body)
    visible = re.sub(r'(?m)^\s*>\s?', '', visible)
    numbered = [int(n) for n in re.findall(r'(?m)^\s*(\d+)\.\s+', visible)]
    cells=[]
    for table in re.findall(r'(?m)(?:^\|[^\n]*\|\s*\n){2,}',visible+'\n'):
        rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in table.strip().splitlines()]
        if rows[0][0].casefold() not in {'','nr','nr.','aussage'}:continue
        for row in rows[2:]:
            match=re.match(r'^(\d+)(?:\.\s|$)',row[0])
            if match:cells.append(int(match[1]))
    gaps = [int(n) for n in re.findall(r'__\((\d+)\)__', visible)]
    choices = [ids for ids in [numbered,cells,gaps] if ids]
    if len(choices)!=1:
        return None
    ids=choices[0]
    return len(ids) if ids==list(range(1,len(ids)+1)) else None


def claimed_maxima(plain):
    claims=[]
    for match in re.finditer(r'(?i)(?:Punkte-Rubrik|Bewertung(?: und Punkte)?)\s*\(([^)]*)\)', plain):
        content=match[1]
        maximum=re.search(r'(?i)(?:max\.?\s*)?(\d+)\s*Punkte|^0\s*[–—-]\s*(\d+)\s*$',content)
        if maximum:claims.append(int(maximum[1] or maximum[2]))
    claims.extend(int(n) for n in re.findall(r'(?i)(?:\bmaximal|\bmax\.|\bgesamt)\s*(\d+)\s*(?:Punkte|P\b)',plain))
    claims.extend(int(n) for n in re.findall(r'(?i)(\d+)\s*Punkte\s*gesamt',plain))
    claims.extend(int(n) for n in re.findall(r'(?i)je\s*\d+\s*Punkt\s*=\s*(\d+)\s*Punkte',plain))
    for line in plain.splitlines():
        if re.match(r'(?i)^\|\s*(?:maximal|gesamt)\b',line):
            cells=line.strip().strip('|').split('|')
            if len(cells)==2 and re.fullmatch(r'\s*\d+\s*',cells[1]):claims.append(int(cells[1]))
    return claims


def score_claim_errors(plain, maximum, claims=None):
    errors=[]
    claims=claimed_maxima(plain) if claims is None else claims
    if not claims:errors.append('scoring rule has no independently stated maximum')
    for total in set(claims):
        if total!=maximum:errors.append(f'answer/criterion maxima sum to {maximum}, but the scoring rule states {total}')
    for paragraph in re.split(r'\n\s*\n',plain):
        if not re.search(r'(?i)bestanden|bestehen|bestehensgrenze',paragraph):continue
        flat=' '.join(paragraph.split())
        for match in re.finditer(r'(?i)\bab\s*(\d+)|Bestehensgrenze[^:]*:\s*(\d+)',flat):
            threshold=int(match[1] or match[2])
            if not 0<=threshold<=maximum:errors.append(f'passing threshold {threshold} is outside 0–{maximum}')
        for match in re.finditer(r'(?:\bvon\s+|/)(\d+)\s*Punkte',flat):
            if int(match[1])!=maximum:errors.append(f'passing denominator {match[1]} differs from maximum {maximum}')
    return errors


def exhaustive_bands(bands, maximum):
    counts={score:0 for score in range(maximum+1)};errors=[]
    for low,high in bands:
        if not 0<=low<=high<=maximum:
            errors.append(f'feedback band {low}–{high} is outside 0–{maximum}');continue
        for score in range(low,high+1):counts[score]+=1
    gaps=[n for n,c in counts.items() if c==0];overlaps=[n for n,c in counts.items() if c>1]
    if gaps:errors.append(f'feedback table has no band for scores {gaps}')
    if overlaps:errors.append(f'feedback bands overlap at scores {overlaps}')
    return errors


def inline_feedback(plain, maximum):
    # Only explicit qualitative clauses with =/: are bands. Numerals in prose
    # and statements about errors cannot become school grades accidentally.
    chunks=[]
    for paragraph in re.split(r'\n\s*\n',plain):
        if re.search(r'(?i)rubrik|auswertung',paragraph) or re.search(r'\d+\s*[:=]\s*(?:sehr gut|gut|befriedigend|ausreichend)',paragraph):chunks.append(paragraph)
    bands=[]
    for m in re.finditer(r'(?<![\w\d])([≤<]?)\s*(\d+)(?:\s*[–—-]\s*(\d+))?\s*(?:P(?:unkte)?\.?)?\s*[:=]\s*([^·\n]+)', '\n'.join(chunks)):
        # Arithmetic statements (1 Punkt = 5 Punkte) are not feedback labels.
        if re.match(r'\d+\s*Punkte',m[4]):continue
        low,high=int(m[2]),int(m[3] or m[2])
        if m[1]:low,high=0,high-(m[1]=='<')
        bands.append((low,high))
    return exhaustive_bands(bands,maximum) if bands else []


def supplemental_scoring_checks(body):
    """Validate bounded authored formats using actual learner answer slots.

    No source is exempted: unsupported forms return None; recognizable but
    contradictory rules return errors instead of acquiring a synthetic rubric.
    """
    plain=learner_scoring_text(body);flat=' '.join(plain.split());count=item_numbers(body)
    tables=[]
    for table in re.findall(r'(?m)(?:^\|[^\n]*\|\s*\n){2,}',plain+'\n'):
        tables.append([[c.strip() for c in line.strip().strip('|').split('|')] for line in table.strip().splitlines()])
    for rows in tables:
        header=rows[0]
        # Three distinct additive criteria, plus an explicit zero-performance
        # row, differ from a table mapping a total to qualitative feedback.
        if header==['Punkte','Beschreibung'] and len(rows)>3:
            scores=[int(r[0]) for r in rows[2:] if re.fullmatch(r'\d+',r[0])]
            if len(scores)==len(rows)-2 and len(set(scores))<len(scores):
                if any(s==0 and not r[1].casefold().startswith('keine') for s,r in zip(scores,rows[2:])):return None
                maximum=sum(scores);return maximum,score_claim_errors(plain,maximum)
        # A horizontal points row is additive, not a grading scale.
        if header and header[0]=='Aufgabe' and header[-1]=='Gesamt':
            errors=[]
            if len(rows)!=3 or rows[2][0]!='Punkte' or len(rows[2])!=len(header):
                return 0,['malformed horizontal criterion table']
            if header[1:-1]!=[str(n) for n in range(1,len(header)-1)]:errors.append('horizontal table task identifiers are not consecutive')
            if not all(re.fullmatch(r'\d+',v) for v in rows[2][1:]):return 0,['unsupported horizontal criterion score']
            maximum=sum(int(v) for v in rows[2][1:-1])
            if count!=len(header)-2:errors.append('horizontal table does not match actual answer slots')
            errors+=score_claim_errors(plain,maximum,claimed_maxima(plain)+[int(rows[2][-1])])
            return maximum,errors
    # Penalty rubrics explicitly award only non-distractor assignments. Bind
    # their possible maximum to the actual key, not seven questions times two.
    if re.search(r'(?i)abgezogen|falsche Zuordnung[^\n]*[−-]\s*\d+\s*Punkte',plain):
        claims=claimed_maxima(plain);maximum=claims[0] if claims else 0;errors=[]
        from build_materials_latex import callout_tree, unwrap_callouts
        key_blocks=[]
        def collect(nodes):
            for node in nodes:
                if isinstance(node,str):continue
                if node['answer']:
                    candidate=unwrap_callouts(node['children'])
                    # The explicit key contract is language-independent.
                    # Bind mappings and distractor labels within the same key;
                    # an unrelated teacher transcript cannot repair its IDs.
                    if re.search(r'(?i)Distraktoren',candidate):key_blocks.append(candidate)
                else:collect(node['children'])
        collect(callout_tree(body))
        if len(key_blocks)!=1:return 0,['penalty rule requires one explicit key containing scored mappings and distractor declarations']
        keys=re.sub(r'[*_]', '', '\n\n'.join(key_blocks))
        mapped=[(int(n),v) for n,v in re.findall(r'(?<!\d)(\d+)\s*(?:→|=)\s*([A-Z])(?![A-Za-z])',keys)]
        correct=re.search(r'(?i)(?:richtig[^.\n]{0,100}?:|zugeordneten Aussagen gibt es)\s*(\d+)\s*Punkte',flat)
        penalty=re.search(r'(?i)falsche Zuordnung.{0,100}?(?:[−-]\s*)?(\d+)\s*Punkte',flat)
        if not correct or not penalty or not count or not mapped:return 0,['penalty rule cannot be bound to actual answer slots and key']
        reward=int(correct[1]);deduction=int(penalty[1]);identifiers=[n for n,_ in mapped]
        if len(set(identifiers))!=len(identifiers) or any(not 1<=n<=count for n in identifiers):errors.append('penalty key has duplicate/out-of-range scored answers')
        if len(mapped)>=count:errors.append('penalty rule declares distractors but no unscored answer slots remain')
        distractor_ids=[]
        for declaration in re.finditer(r'(?i)Distraktoren(?:\s*\([^)]*\))?\s*:\s*(.*?)(?=\n\s*\n|\Z)',keys,re.S):
            labels=declaration[1]
            while re.search(r'\([^()]*\)',labels):labels=re.sub(r'\([^()]*\)','',labels)
            if '(' in labels or ')' in labels:errors.append('unbalanced distractor explanation')
            distractor_ids.extend(int(n) for n in re.findall(r'\b\d+\b',labels))
        if (len(set(distractor_ids))!=len(distractor_ids) or set(identifiers)&set(distractor_ids)
                or set(identifiers)|set(distractor_ids)!=set(range(1,count+1))):
            errors.append('scored answers and distractors must be disjoint and cover every actual answer slot exactly once')
        maximum=len(mapped)*reward;errors+=score_claim_errors(plain,maximum,claims)
        bound=re.search(r'(?i)zwischen\s*0\s*und\s*(\d+)|mindestens\s*0,?\s*höchstens\s*(\d+)',flat)
        if not bound or int(bound[1] or bound[2])!=maximum:errors.append('penalty rule lacks matching explicit lower/upper bounds')
        if not re.search(r'(?i)negative Summen werden auf 0 gesetzt',flat):errors.append('penalty rule does not explicitly clamp negative sums to zero')
        if not re.search(r'(?i)fehlende (?:Zuordnung|Antwort).{0,20}0 Punkte',flat):errors.append('penalty rule lacks explicit omission score')
        if reward<=0 or deduction<=0:errors.append('penalty reward and deduction must be positive')
        return maximum,errors
    # Two independently scored decisions for each visible item (voice + T/P).
    components=re.findall(r'(?i)Je korrekte[^\n]*:\s*(\d+)\s*P\s*\(max\.\s*(\d+)\s*P\)',plain)
    if components:
        claims=claimed_maxima(re.split(r'(?mi)^\s*-\s*Je korrekte',plain,1)[0]);maximum=sum(int(cap) for _,cap in components);errors=[]
        if not count:errors.append('component scoring cannot be bound to actual answer slots')
        elif any(int(rate)*count!=int(cap) for rate,cap in components):errors.append('component score maximum differs from rate times actual answer slots')
        errors+=score_claim_errors(plain,maximum,claims);errors+=inline_feedback(plain,maximum)
        return maximum,errors
    # Explicit per-answer rates, including equivalent table forms. The table
    # maximum is evidence only after matching the actual learner item count.
    rate=None
    patterns=[r'(?i)(\d+)\s*Punkt(?:e)?\s*pro\s*richtige[rn]?\s*(?:Antwort|Zuordnung|Entscheidung)',
              r'(?i)(?:pro|je)\s*richtige[rn]?\s*(?:Antwort|Zuordnung|Entscheidung)\s*(\d+)\s*Punkt',
              r'(?i)(?:für\s*)?jede Aussage erhalten Sie\s*(\d+)\s*Punkt',
              r'(?i)\d+\s*Aufgaben,\s*je\s*(\d+)\s*Punkt']
    for pattern in patterns:
        match=re.search(pattern,flat)
        if match:rate=int(match[1]);break
    for rows in tables:
        if rows[0]!=['Leistung','Punkte']:continue
        for row in rows[2:]:
            if re.match(r'(?i)(?:pro|jede)\s+(?:richtige|korrekte)[rn]?\s+Zuordnung',row[0]):
                match=re.fullmatch(r'(?:je\s*)?(\d+)',row[1])
                if match:rate=int(match[1])
    if rate is not None:
        if not count:return 0,['per-answer scoring cannot be bound to consecutive actual answer slots']
        maximum=count*rate;errors=score_claim_errors(plain,maximum);errors+=inline_feedback(plain,maximum)
        for rows in tables:
            if rows[0][0]=='Punkte':
                bands=[]
                for row in rows[2:]:
                    m=re.fullmatch(r'(\d+)(?:\s*[–—-]\s*(\d+))?',row[0])
                    if not m:errors.append('unsupported feedback score');continue
                    bands.append((int(m[1]),int(m[2] or m[1])))
                errors+=exhaustive_bands(bands,maximum)
            if rows[0]!=['Leistung','Punkte']:continue
            bands=[]
            for row in rows[2:]:
                match=re.fullmatch(r'(?i)(unter\s+)?(\d+)\s+richtig',row[0])
                if match:
                    n=int(match[2]);bands.append((0,n-1) if match[1] else (n,n))
                    score=re.match(r'(\d+)',row[1])
                    if score and int(score[1])!=n*rate:errors.append('feedback row score differs from correct answers times rate')
            if bands:errors+=exhaustive_bands(bands,count)
        return maximum,errors
    # Pure inline feedback still needs an independent stated maximum.
    claims=claimed_maxima(plain)
    if claims and re.search(r'\d+\s*(?:P\.?\s*)?=\s*(?:ausgezeichnet|sehr gut|gut)',flat):
        maximum=claims[0];return maximum,score_claim_errors(plain,maximum)+inline_feedback(plain,maximum)
    return None


def scored_task_headings(plain):
    headings=[]
    for line in re.finditer(r'(?m)^.*$',plain):
        heading=re.match(r'(?i)^\s*(?:(?:#{2,4}|-)\s+)?(Tâche|Partie|Phase)\s*(unique|[A-Z]|\d+)\b(.*)',line[0])
        if not heading:continue
        score=re.search(r'(?:\(\s*|[,·–—-]\s*|/\s*)(\d+)\s*(?:points?|pts?|P\.)(?:\s*\))?',heading[3],re.I)
        if score:headings.append((heading[1].casefold(),heading[2],int(score[1]),heading[3],line.start()))
    return headings


def points_only_checks(body):
    """Check explicitly declared practice totals without inventing grades."""
    plain=learner_scoring_text(body);errors=[]
    if SCALE.search(body) or BAND.search(body) or re.search(r'(?i)Notenschlüssel|Barème de notes',plain):errors.append('points-only assessment still carries a school-grade conversion')
    headings=scored_task_headings(plain)
    ids=[h[1] for h in headings];values=[h[2] for h in headings]
    expected=(['unique'] if ids==['unique'] else [str(n) for n in range(1,len(ids)+1)] if ids and ids[0].isdigit() else [chr(65+n) for n in range(len(ids))])
    if not ids or ids!=expected or len({h[0] for h in headings})!=1:errors.append('points-only tasks must have consecutive, unique, explicitly scored headings')
    if any(value<=0 for value in values):errors.append('points-only task maximum must be positive')
    # A separately scored global oral criterion is independent of both phases.
    global_scores=[int(n) for n in re.findall(r"(?mi)^\s*-\s*Impression d'ensemble[^\n]*?/\s*(\d+)\s*P\.",plain)]
    if len(global_scores)>1:errors.append('duplicate overall oral criterion')
    maximum=sum(values)+sum(global_scores)
    claims=[int(n) for n in re.findall(r"(?i)\b(?:Barème\s+)?Total(?: de l'épreuve)?\s*[:.]\s*(\d+)\s*(?:points?\b|P\.)",plain)]
    claims.extend(int(n) for n in re.findall(r'(?i)Barème\s*\((\d+)\s*points\s+au total\)',plain))
    for table in re.finditer(r'(?m)(?:^\|[^\n]*\|\s*\n){2,}',plain+'\n'):
        rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in table[0].strip().splitlines()]
        header=rows[0]
        if not header or header[-1].casefold()!='points':continue
        parts=[];totals=[];groups={};labels=[]
        for row in rows[2:]:
            score=re.fullmatch(r'(\d+)(?:\s*(?:P\.|points?))?',row[-1],re.I)
            if len(row)!=len(header) or not score:
                errors.append('unsupported points-only criterion/summary row');continue
            value=int(score[1])
            if row[0].casefold()=='total':totals.append(value);continue
            parts.append(value);labels.append(row[0])
            group=re.match(r'^([A-Z]|\d+)\b',row[0]) if len(header)==3 else re.search(r'\(([A-Z])\)\s*$',row[0])
            if group:groups[group[1]]=groups.get(group[1],0)+value
            elif len(header)==3 and header[0].casefold() in {'tâche','partie'}:
                errors.append('each grouped criterion row must identify a declared task/partie')
        claims+=totals
        kind=header[0].casefold()
        if kind in {'tâche','niveau','partie'} and len(header)==2:
            if parts!=values:errors.append('points-only summary rows differ from actual task maxima/order')
            if len(labels)!=len(headings):errors.append('summary table does not cover every actual task once')
            for label,heading in zip(labels,headings):
                identifier=re.match(r'(?i)^(?:(?:Tâche|Partie)\s*)?([A-Z]|\d+)\b',label)
                if identifier:
                    if identifier[1]!=heading[1]:errors.append('summary task identifiers differ from actual task order')
                elif kind!='niveau' or label.casefold() not in heading[3].casefold():
                    errors.append('summary row label does not identify its actual task')
        elif kind in {'critère','domaine'} or (kind in {'partie','tâche'} and len(header)==3):
            if sum(parts)!=maximum:errors.append('criterion maxima differ from complete paper maximum')
            if groups and groups!={identifier:value for identifier,value in zip(ids,values)}:errors.append('grouped criterion maxima differ from corresponding task maxima')
        elif kind.startswith(('barème','critère (')) or kind=='sous-critère':
            # An explicitly scoped detailed table belongs to one named part.
            part=re.search(r'(?i)(?:Partie|Tâche|Phase)\s+([A-Z]|\d+)\b',header[0])
            if part:matches=[h for h in headings if h[1]==part[1]]
            elif kind=='sous-critère':matches=[h for h in headings if h[4]<table.start()][-1:]
            else:
                label=re.search(r'\(([^)]+)\)',header[0])
                matches=[h for h in headings if label and label[1].casefold() in h[3].casefold()]
            if len(matches)!=1:errors.append('detailed rubric is not bound to exactly one declared task')
            elif sum(parts)!=matches[0][2]:errors.append('detailed rubric maxima differ from named task maximum')
        else:errors.append('unsupported points-only scoring table')
    if not claims:errors.append('points-only assessment lacks an independent stated total')
    if any(total!=maximum for total in claims):errors.append(f'points-only tasks sum to {maximum}, inconsistent with declared totals {sorted(set(claims))}')
    return maximum,errors


def threshold_grade_bands(body, total):
    """Validate an explicitly ordered 1≥x … 6<x grade cutoff convention."""
    plain=learner_scoring_text(body)
    paragraphs=[p for p in re.split(r'\n\s*\n',plain) if 'Notenschlüssel' in p]
    cutoffs=[]
    for paragraph in paragraphs:cutoffs+=re.findall(r'(?<!\d)([1-6])\s*(≥|<)\s*(\d+)',paragraph)
    if not cutoffs:return None
    errors=[]
    if ([g for g,_,_ in cutoffs]!=list('123456') or [op for _,op,_ in cutoffs]!=['≥']*5+['<']):
        return [],['grade cutoffs must declare grades1–6 once in order with five lower bounds and a final upper bound']
    values=[int(value) for _,_,value in cutoffs]
    if not (0<values[4]<values[3]<values[2]<values[1]<values[0]<=total) or values[5]!=values[4]:
        return [],['grade cutoffs are not strictly ordered within the paper total or disagree at the lowest-grade boundary']
    bands=[]
    for index,(grade,_,_) in enumerate(cutoffs[:5]):bands.append((values[index],total if index==0 else values[index-1]-1,grade))
    bands.append((0,values[5]-1,'6'))
    return bands,errors


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    bad, checked, no_data, rehearsals, rubrics = [], 0, [], 0, 0

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

        if fm.get('assessment_scoring')=='points-only':
            result=points_only_checks(body)
            rubrics+=1
            bad.extend(f'{rel}: {problem}' for problem in result[1])
            continue
        if fm.get('assessment_scoring') not in (None,'grade-scale'):
            bad.append(f'{rel}: unsupported assessment_scoring declaration')
            continue

        mt = TOTAL.search(body)
        tasks = [int(x) for x in TASK.findall(body)]
        if not tasks:tasks=[h[2] for h in scored_task_headings(learner_scoring_text(body))]
        bands = [(int(a), int(b), g) for a, b, g in BAND.findall(body)]
        if mt and not bands:
            threshold=threshold_grade_bands(body,int(mt[1]))
            if threshold is not None:
                bands=threshold[0];bad.extend(f'{rel}: {problem}' for problem in threshold[1])
        if not mt and not tasks and not bands:
            rubric = rubric_checks(body)
            if rubric is None:
                rubric = feedback_checks(body)
            if rubric is None:
                rubric = supplemental_scoring_checks(body)
            if rubric is not None:
                rubrics += 1
                bad.extend(f'{rel}: {problem}' for problem in rubric[1])
                continue
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
            if any(lo > hi or lo < 0 or hi > total for lo, hi in covered):
                bad.append(f"{rel}: grading band is reversed or outside 0–{total}")
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
        print(f"::warning::{len(no_data)} exam page(s) have no recognized assessment "
              f"data in the supported total/task/grade formats. Inspect the source: "
              f"this may be missing data or an unsupported rubric format.")
        for x in no_data[:5]:
            print(f"::warning::    {x}")
    if not checked and not no_data and not rubrics:
        print("A13 n/a — this repo has no exam pages")
        return 0
    if bad:
        print(f"\nA13 FAIL — {len(bad)} problem(s) across {checked} exam(s)",
              file=sys.stderr)
        return 1
    # Having no exams and having 156 that carry no marking scheme are not the
    # same state, and this gate reported the second as "A13 OK — 0 exam(s)".
    # That is fle: every one of its exam pages states a task list and no total,
    # no task points and no grading scale, so the arithmetic gate had nothing to
    # add up and said so in a warning while returning OK. A blocking gate that
    # passes on zero is the failure mode this whole battery was built to remove;
    # it does not get an exception for being the one counting marks.
    if no_data:
        print(f"\nA13 FAIL — {len(no_data)} exam page(s) could not be verified. "
              f"Resolve missing scoring data or support the actual source format; "
              f"an unrecognized rubric is not proof that the source has none.", file=sys.stderr)
        return 1
    if rehearsals:
        print(f"  {rehearsals} rehearsal paper(s) skipped — they drill a section "
              f"of a larger Klausur and state no total of their own")
    if rubrics:
        print(f'  {rubrics} authored scoring format(s): criterion/per-answer totals or exhaustive feedback bands checked; no school-grade scale inferred')
    print(f"A13 OK — {checked} grade-scaled exam(s) and {rubrics} authored scoring format(s) verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
