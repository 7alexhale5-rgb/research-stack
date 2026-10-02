# Scripts room: the validator, the focus linter and the gatherer

One job: keep the scripts the skill and its consumers run correct, read-only and
dependency-free. Paths relative to the repo root.

## Inputs

- `scripts/validate_report.py`: `structure`, `focus`, `citations`, `sources`, `all` checks on a
  report. Read-only; it is the recorded verifier for development-protocol's research row.
- `scripts/focus_check.py`: `lint`, `suggest`, `plan`, `probe`, `table`, `docs` over
  `focus/tags.json`, `focus/<tag>.md` and `references/tool-registry.json`.
- `scripts/gather.py`: `rubric`, `prompt`, `score --scorer jev`, `merge`, `check`, `route`,
  `agree`, `eval` over a brief and hunter evidence cards (hunter/gatherer mode,
  `references/hunter-gatherer.md`). Its rubric follows `references/jev-question-design.md`;
  change a wording only with an `eval` run against labels.
- Consumers: `SKILL.md` Steps 0.4, 1, 3H and 8.5; development-protocol's port (same files under
  `skills/research-stack/scripts/`); CI.
- Missing input: a check with no test in `tests/` is not shipped.

## Process

1. Python 3.9+ standard library only. No network except `validate_report.py citations`, which
   keeps its SSRF guard and DNS pinning, and `gather.py score --scorer jev`, which posts only to
   the official TypeSafe or Cloudflare endpoint and never sends a card marked internal.
2. Never write to the report, the cards or the registry; never print a key's value (`probe` reports "key
   set" or "missing" only).
3. Both scripts must find the manifest in either layout: `focus/` (standalone) or
   `references/focus/` (ported). Keep that search order.
4. Add or change a test in `tests/`, then run `python3 -m unittest discover tests` and
   `python3 scripts/focus_check.py lint`.
5. A behaviour change here is a change for the port: note it so development-protocol re-ports.

## Outputs

- Edited `scripts/*.py` with matching tests.

## Human check

Alex runs the fixture pair and one real report through `validate_report.py all`. Pass: good and
focus-good exit 0, bad and focus-bad exit 1, the real report's verdict matches a read of it. Fail:
fix before release.
