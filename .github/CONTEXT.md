# CI room: the GitHub Actions workflow

One job: run the repo's own checks on every push and pull request. Paths relative to the repo
root.

## Inputs

- `.github/workflows/ci.yml`.
- The commands it mirrors: `CLAUDE.md` (Verify) and `tests/CONTEXT.md`.
- Missing input: a check that runs locally but not in CI is listed in the pull request, not
  assumed covered.

## Process

1. Keep CI equal to the local Verify list: unit tests (Python 3.9 and 3.12), `focus_check.py
   lint`, `focus_check.py docs`, the four fixtures, and `install.sh` into a temp `HOME`.
2. Expected failures are tested with an explicit `if ...; then exit 1; fi`. `! cmd` does not
   trip `set -e`.
3. No secrets: the suite and the lint need no keys.

## Outputs

- Edited `.github/workflows/ci.yml`.

## Human check

The maintainer reads the Actions run on the pull request. Pass: every step green on the exact commit.
Fail: fix the code or the workflow before merge.
