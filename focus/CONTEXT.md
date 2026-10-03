# Focus room: lenses and the tag manifest

One job: keep each focus lens a sharp, sourced, tool-true contract for its area, and keep the tag
manifest in step with the lenses, the tool registry and the repos that mirror it. Paths relative
to the repo root.

## Inputs

- `focus/tags.json`: the canonical manifest (tags, addendum names, source tags, authorities,
  pathway and overlay mapping, development-protocol rows, bundles, limits).
- `focus/<tag>.md`: one lens per tag, with the eight required `##` sections: Triggers,
  Sub-question lens, Tool stack, Authorities, Freshness, Audit mode, Report addendum, Pathway
  mapping.
- `references/tool-registry.json`: every tool a lens names, by id.
- Evidence for any tool claim: a dated source, normally the latest dossier in `docs/research/`.
- Missing input: a tool with no registry entry, or a claim with no source, is not added.

## Process

1. Change `tags.json` first, then the lens, then the registry.
2. In a lens `Tool stack` table the first column is the registry id in backticks. Every id must
   exist in the registry and list this tag in its `focus`, and every registry entry that claims
   the tag must appear in the lens. Every paid tool needs a free `fallback`.
3. Run `python3 scripts/focus_check.py lint`, then `python3 scripts/focus_check.py table` and
   paste the output between the registry markers in `docs/tools-reference.md`, then
   `python3 -m unittest discover tests`.
4. A new tag or renamed addendum is a contract change for the mirrors. Update
   pathway-operating-layer `RESEARCH_FOCUS_MAP`, development-protocol
   `skills/research-stack/references/focus/` and its `FOCUS_HINTS`, and gravity-stack's promptfoo
   goldens in the same change set.

## Outputs

- Edited `focus/*.md`, `focus/tags.json`, `references/tool-registry.json`,
  `docs/tools-reference.md`.

## Human check

The maintainer runs one real `/research-stack ... --focus <tag>` on a live topic and reads the addendum.
Pass: every row has a specific and a source tag, the tools the lens named actually fired or are
named as unavailable, and `validate_report.py structure` passes. Fail: fix the lens or registry
before release.
