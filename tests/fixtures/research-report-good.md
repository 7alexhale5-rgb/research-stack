# Research: fixture (known-good)

This fixture is a minimal report that satisfies `validate_report.py structure`: every required
section is present, at least two source-tag types appear, and the body clears the length floor.
Used by `tests/test_validate_report.py` and by the research-stack regression check in
`SKILL.md`. Keep it in sync with the sections `check_structure` requires if
that script's required-section list ever changes.

## Decision answer

- Use the keyless API; it needs no setup [HN:91][WS].

## Sub-question answers

**Q1: Does the API need a key?**

- No key needed as of 2026-09 [PX + FC:docs.example.com].

## Contradictions

- Source A ranks results by points, source B by date [PX][WS].

## Patterns

- Compress before hand-off appears in 2 or more sources [PX + FC:example.org].

## Coverage gaps

- none

Padding to clear the report's minimum length floor so the structure check does not flag it as
suspiciously short: word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word
word word word word word word word word word word word word word word word word word word word

## Sources

- https://arxiv.org/abs/2506.18096
- https://docs.python.org/3/library/urllib.html
- https://github.com/example/repo
