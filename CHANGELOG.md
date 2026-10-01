# Changelog

## [3.0.0] - 2026-10-01

### Added

- **Focus lenses.** `--focus <tags>` or `#tag` shorthand, with 11 tags: seo, content, market,
  ui-ux, a11y, perf, security, devtools, ai-agents, data-infra, legal. Bundles: `#launch`,
  `#ship-audit`, `#competitive`, `#build-pick`. Each lens adds sub-questions, its own tool round
  (Step 4F), authorities, freshness rules, an audit mode and a required report section.
- `--target <url|repo|path>`: a read-only live audit by each active lens.
- `references/tool-registry.json`: 85 tools and connectors with detection, cost class, best use,
  source tag and free fallback. New domain tools include DataForSEO, SpyFu, Semrush, Ahrefs,
  Search Console, PageSpeed, CrUX, Foreplay, Meta Ad Library, Mobbin, Refero, Figma, shadcn,
  Playwright, axe-core, Chrome DevTools, OSV, GitHub Advisories, CISA KEV, Socket, Semgrep, Snyk,
  Context7, DeepWiki, grep.app, deps.dev, Crunchbase, NinjaPear and Legal Data Hunter, plus team
  connectors (HubSpot, Slack, Atlassian, Fireflies and others).
- `scripts/focus_check.py`: `lint`, `suggest`, `plan`, `probe`, `table`, `docs`.
- `scripts/validate_report.py` (from the development-protocol port), extended with a focus check
  and lens authority scoring. Tests and fixtures under `tests/`; CI workflow.
- SKILL.md front matter, sub-question decomposition, source discipline, coverage-based stop
  conditions, skeptic, cross-source and gap perspectives, validation gate (the v3 method, merged
  from the development-protocol port).
- `references/power-tier.md`: Gemini CLI, Groq compression, NotebookLM, last30days, vault notes,
  MCP gateway names.
- `config/config.example.md` now lists only keys the skill reads.
- `docs/research/2026-10-01-v3-tooling-dossier.md`: the self-research behind these changes.

### Changed

- Groq is compression and synthesis assist only. Its research endpoint was dropped after it
  failed on a retired upstream model (2026-08-17).
- Reddit and X go through site-scoped search by default (Reddit API closed 2025-11-11; X
  pay-per-use since 2026-02-06), with optional xAI `x_search`.
- Firecrawl discovery uses `/v2/search` (`/deep-research` deprecated).
- `install.sh` ships focus lenses, registry, scripts and config example, runs from any directory
  and lints the install.
- README, command, architecture and tools-reference docs rewritten for v3. The Ollama, Reddit MCP
  and Twitter MCP descriptions were out of date and are removed.

### Fixed

- The duplicated Perplexity tool name in the probe table.
- The dead `docs/alternatives.md` link in the README.
- The vault path mismatch between config and the skill.

## [2.0.0] - 2026-03-12

- v2 pipeline: tiered rounds, Groq compression, corroboration tags, NotebookLM routing.
