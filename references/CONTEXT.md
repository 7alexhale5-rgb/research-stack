# References room: setup and routing guidance

One job: keep install and notebook-routing guidance workable for a fresh install. Paths
relative to the repo root.

## Inputs

- `install.sh`'s actual steps.
- Current references: `references/notebook-routing.md`, `references/setup-alternatives.md`,
  `references/setup-notebooklm-obsidian.md`, `references/providers.md`,
  `references/perspectives.md`, `references/output-format.md`, `references/hunter-gatherer.md`, `references/jev-question-design.md`, `references/power-tier.md`,
  `references/tool-registry.json` (changed through the focus room).
- Missing input: a setup step with no matching `install.sh` line is flagged, not assumed.

## Process

1. Walk `install.sh` end to end; confirm every reference doc matches its actual steps.
2. Update the doc, not `install.sh`, unless the install process itself changed.

## Outputs

- Edited `references/*.md`.

## Human check

Alex runs `install.sh` on a clean checkout and follows one reference doc. Pass: setup succeeds
as documented. Fail: correct the doc.
