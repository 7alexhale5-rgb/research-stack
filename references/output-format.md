# Output templates

Templates for Step 9 (deliver) and Step 10 (cache and notes).

## Contents

- Report
- Source-stats dashboard
- Cache file
- Source notes (`--notes`)

---

## Report (Step 9)

Lead with the **Decision answer**, then answer each sub-question in order, then the cross-cutting
sections. The sub-question sections are the structure that keeps the report from going generic:
every answer carries a specific.

```text
---
date: {YYYY-MM-DD}
type: research
topic: "{TOPIC}"
depth: {auto-shallow|default|deep}
focus: [{tags, or leave the list empty}]
target: {URL / repo / path, or none}
---

## Research: {TOPIC}

### Decision answer

- {1-3 lines: what the research means for the decision the scope named. The takeaway, not a summary.}

### Sub-question answers

**Q1: {sub-question}**

- {direct answer with a specific: name, version, date, number or quote} [PX + FC:docs.example.com]

**Q2: {sub-question}**

- {direct answer with a specific} [WS][HN:42]
  - {if under-covered, say so: "only 1 source, verify independently"}

### Contradictions

- Source A says X [PX], source B says Y [RD:r/sub(120)]. {which to trust and why}

### Patterns (cross-cutting, 2+ sources)

- {pattern} [PX + FC:example.org + HN:88]

### Coverage gaps

- {each sub-question left under-covered and why}, or "none: every sub-question met the 2-source or
  1-authoritative bar"

### {Focus addendum, one per active tag, e.g. "SEO scorecard" or "Threat and advisory table"}

{the table from focus/<tag>.md "Report addendum": every row has a specific and a source tag;
an unavailable tool is named in its row, never filled with a guess}

### Sources

- {every URL fetched, one per line}
```

---

## Source-stats dashboard (Step 9)

Real numbers only. Write "skipped (reason)" or "unavailable" rather than dropping a line.

```text
---
Research Stack report
|- Scope: {N} sub-questions, {N} fully covered, {N} thin
|- Web search: {n} queries, {n} results, top domains {list}
|- Page fetch / scraper: {n} fetched | {tool} | {n} failed
|- Answer engine: {model} | {n} calls | ~${cost} | or "not configured" / "skipped (--free)"
|- Hacker News: {n} stories, {sum} points
|- Community: {n} threads
|- Academic: {n} papers ({sources})
|- Index search: {service} {n} calls | or "not configured"
|- YouTube: {n} transcripts | or "skipped (not --deep/--youtube)"
|- Internal round: {sources} | or "unavailable (headless)" / "not relevant"
|- Focus: {tags} | per tag: {tools used} / {tools missing -> fallback} | audit: {target or "none"}
|- Compression: {n} pages | {self | subagent | hosted model name}
|- Synthesis assist: {model or subagent} | "skipped (not --deep)" | "unavailable"
|- Perspectives: {N} run | {N} with findings | {N} escalated
|  |- skeptic: {N} findings
|  `- {name}: {N} findings | "clean (verified 2x)" | "failed" | "skipped"
|- Validation: {PASS | WARN | FAIL | skipped}
|- Cache: {path to the cache file}
|- Est. total cost: ${X.XX} ($0.00 on a free-only run)
`- Sources: {list of domains}

Ask me anything about {TOPIC}. I will answer from this research.
```

---

## Cache file (Step 10)

Path: `$CACHE_DIR/{YYYY-MM-DD}-{topic-slug}.md` (see SKILL.md Step 10 for the default). Keep it compact: it exists so the next
run can decide "use cached or refresh" in seconds.

```text
---
date: {YYYY-MM-DD}
type: research
topic: "{TOPIC}"
depth: {depth}
focus: [{tags}]
target: {target or none}
sub_questions: {N}
sources_count: {N}
---

# Research cache: {TOPIC}

## Decision answer

{1-3 lines}

## Key findings

{5-7 bullets, each with its source tags and a specific}

## Coverage gaps

{under-covered sub-questions, or "none"}

## Sources

{list of URLs used}

## Patterns

{2-3 cross-source patterns}
```

When the development protocol called this skill, the full report is also the evidence file
`.devproto/evidence/research.md`. The cache file is the short copy for reuse.

---

## Source notes (`--notes`)

One file per scraped source (top 3 by default, all on `--deep`), at
`$CACHE_DIR/sources/{source-slug}.md`:

```text
---
date: {YYYY-MM-DD}
type: source
url: {URL}
tag: "[FC:{domain}]"
research: ../{YYYY-MM-DD}-{topic-slug}.md
---

# {Source title}

## Key takeaways

- {3-5 bullets with specifics}

## Used for

- {which sub-questions this source answered}

## Reliability

- {official | peer-reviewed | engineering blog | forum | other}, {any caveat from the perspectives}
```

In the research note, link each source note with a normal relative markdown link.
