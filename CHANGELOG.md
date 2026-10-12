# Changelog

## [Unreleased]

### Fixed

- Focus checks no longer vanish on `focus:` spellings the parser cannot read. A flow list that
  wraps, or a value that starts or continues on a later line, used to return no tags and skip every
  focus check; `validate_report.py` now fails them and asks for `focus: [a, b]` on one line or a
  block list. CRLF front matter is read correctly. Unquoted `- #tag` block items are rejected as
  ambiguous because YAML reads them as comments; write `- tag` or quote the tag. Mixed root
  indentation fails before granting lens authority. Long quote/comma headers are scanned once,
  and failed `all` checks still print `Verdict: FAIL`. Found by outside reviews of the 3.3.0 follow-up commits.

## [3.3.0] - 2026-10-02

### Added

- **Local add-on.** An optional `local/OVERLAY.md` in the installed skill folder holds one machine's
  private sources, scripts and model pins. SKILL.md reads it in Step 0 after the config, and it wins
  where the two disagree. The installer never writes to `local/`, `evals/` or `config/config.md`,
  and lists files an older install left behind instead of deleting them.
- `commands/research-stack.md` has front matter so the slash menu shows a description.
- `tests/test_install.py`: installs into a temp HOME and checks the machine-owned files survive.

## [3.2.1] - 2026-10-02

### Fixed (from the companion-repo reviews)

- Source quality: lens authorities rank official only for the report's declared focus. Before, every
  lens's domains (youtube.com, g2.com, vercel.com and others) counted as official in every report.
- `focus: none`, `null` or `~` means no focus instead of failing on an unknown tag.
- Lint follows the fallback chain: a paid tool must reach a non-paid tool, not just name a fallback.
- `focus_check.py plan` reads lens files from `--root`, matching the manifest it loads.
- The perf template keeps dates outside the source-tag brackets, so its citations are counted.
- `[GQ]` documented; `[LDH]` versus `[LEX]` wording aligned; "Round 2F" renamed to Step 4F everywhere.
- Removed an unverified study citation (CITE-AI) from the attribution spot-check; the rule stays.
- The ICM layout test skips folders git ignores; `.claude/` is ignored.

## [3.2.0] - 2026-10-02

### Added

- **Hunter/gatherer mode** (SKILL.md Step 3H, `references/hunter-gatherer.md`). It turns on for
  `--deep` and for runs with 4+ sub-questions; `--hunt` and `--no-hunt` override. Read-only hunter
  subagents, one per sub-question, write evidence cards (claim, quote, URL, date, the hunter's
  reasoning) and raw notes to files. A fresh-context gatherer scores every card against a rubric
  built from the brief, then routes it to keep, drop, escalate or flagged, and lists coverage gaps
  for a re-hunt. The writer reads only the kept cards.
- `scripts/gather.py`: `rubric`, `prompt` (free Claude-subagent scorer), `score --scorer jev`
  (TypeSafe direct with `jev-1.13.0` pinned, or `--host cloudflare`; cards marked internal are
  never sent, and Jev never answers the injection screen), `merge`, `check`, `route` (fails
  closed on scores with no injection answer) and `agree` (Cohen's kappa between two scorers).
  Jev runs in shadow mode until it is calibrated on about 200 in-domain labels. Stdlib only,
  with tests and fixtures.
- Registry: `jev` (paid; falls back to `claude-subagent`) and `claude-subagent` (builtin). 94 tools.
- Dashboard line `Gatherer:`.
- Dogfood dossier `docs/research/2026-10-02-hunter-gatherer-jev-dossier.md` with every artifact
  from the run (brief, 70 cards, raw notes, two scorers' scores, ledgers, 70 labels) in
  `docs/research/2026-10-02-hunter-gatherer/`.

### Changed after the second dogfood run (Jev prompting)

- The rubric follows TypeSafe's rules for Jev (`references/jev-question-design.md`): six
  questions (`subq`, `specific`, `impact`, `supported`, `authority`, `injection`), each one short,
  literal and positive, with backticked state keys, situational Score levels as `what` plus
  `examples` objects, and neutral sub-question keys in a stable order. `--variant plain` is for
  A/B tests.
- Jev's state is `claim` plus `quote`. Authority is set in code from the source type and
  `source_notes`, which can now carry a number.
- Routing reads Score probability mass, uses |2p-1| for Noul confidence, gates on confidence only
  for Jev, and sends unsupported cards back as `requote` rather than dropping them.
- `gather.py eval` measures keep and drop precision against the lead's labels per threshold.
- Hunter briefs carry strict card rules. On the same sub-question, fully backed cards rose from
  2/16 to 16/16. Dossier: `docs/research/2026-10-02-jev-prompting-dossier.md`.

### Found by the dogfood run

- An LLM scorer's self-reported confidence can be a constant (70 of 70 usefulness confidences
  were 0.60). `route` now detects this and routes on scores alone (`--confidence auto`).
- Scoring one card at a time cannot see what another card revealed: an unaffiliated reseller's
  pages scored as vendor docs. Briefs now carry `source_notes`, which ride along with each card.

## [3.1.0] - 2026-10-01

### Added

- `comms` focus lens (voice, SMS, dialers; CPaaS vs UCaaS) with RingCentral, Twilio, Telnyx,
  Aircall, Dialpad, CallRail and FCC/eCFR/CTIA rules in the registry (92 tools). Addendum:
  "Telephony and messaging plan". Found by the first live v3 run (a RingCentral dialer for a
  custom CRM): no lens fired on the topic, and vendor developer docs scored as unknown sources.

### Changed

- `validate_report.py` has a `process` check, run by `structure` and `all` on `--deep` reports.
  It warns when the dashboard has no perspectives line with counts, no `Attribution: N/N` line,
  or no internal-round line. Found on the same live run: the first pass skipped the internal round,
  the perspective subagents and the attribution spot-check, and its dashboard overstated the
  perspectives without any check noticing.
- `data-infra` authorities now include vercel.com, supabase.com and opentelemetry.io.
- `devtools` triggers also match api, sdk, integration and webhook.

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
