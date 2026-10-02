# Tests room: the regression suite and fixtures

One job: prove the validator, the focus linter and the lens/registry contract still hold.
Paths relative to the repo root.

## Inputs

- `tests/test_validate_report.py`: structure, sources, SSRF guard, DNS pinning, citations, CLI.
- `tests/test_focus.py`: focus parsing, bundles, addenda, lens authorities, lint, suggest, plan,
  probe (no key values), docs table sync.
- `tests/test_gather.py`: card and score checks, rubric, routing (including constant-confidence
  detection), coverage and re-hunt, Cohen's kappa, Jev transport through a fake poster (internal
  cards held, key never printed, Cloudflare unwrap, one failed call isolated), scorer prompt.
- `tests/test_icm.py`: the ICM layout. The router's rooms exist and each has Inputs, Process,
  Outputs and Human check; the system map lists exactly the router's rooms; every top-level
  folder is a room; `AGENTS.md` mirrors `CLAUDE.md`.
- `tests/fixtures/research-report-{good,bad,focus-good,focus-bad}.md`, and
  `tests/fixtures/gather-{brief.json,cards.jsonl,scores.jsonl}`.
- Missing input: a script behaviour with no test is untested, not passing.

## Process

1. Run `python3 -m unittest discover tests` from the repo root. Tests must not need the network
   (citation tests use a fake fetcher).
2. Keep each fixture pair's contract: the good fixture passes `structure`, the bad one fails it.
   When a required section or addendum name changes, update the fixtures in the same change.
3. CI (`.github/workflows/ci.yml`) runs the suite on Python 3.9 and 3.12, the lint, the docs
   sync, the fixture pair and an install into a temp `HOME`.

## Outputs

- A green run before every commit that touches `scripts/`, `focus/` or `references/`.

## Human check

Alex reads CI on the exact pull-request commit. Pass: green on both Python versions. Fail: fix
before merge; never skip or delete a test to go green.
