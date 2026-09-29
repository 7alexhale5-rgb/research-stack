# Docs room: how the pipeline works

One job: keep architecture and tool-reference docs true to the shipped pipeline. Paths relative
to the repo root.

## Inputs

- The merged pipeline change.
- Current docs: `docs/architecture.md`, `docs/tools-reference.md`.
- Missing input: a source or stage with no doc entry is not considered documented.

## Process

1. Find every doc line the change makes false: `grep -rn "<old value>" docs`.
2. Rewrite those lines to match the shipped pipeline stages and sources.

## Outputs

- Edited `docs/*.md`.

## Human check

Alex spot-checks `docs/tools-reference.md` against the live source list. Pass: every listed
source is actually fired by the pipeline. Fail: correct before release.
