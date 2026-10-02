Deep multi-source research with optional focus lenses. Free tools by default (web search, page fetch, Hacker News, arXiv, OSV, PageSpeed and more); paid APIs and MCPs only when configured. Every claim carries a source tag and a specific. Portable across Claude Code and OpenClaw.

## Usage

- `/research-stack <topic>`: balanced run. Sub-questions, Rounds 1 and 2, gap check, 3 to 5 pages read, skeptic and cross-source passes.
- `/research-stack <topic> --deep`: comprehensive. More pages, synthesis assist, all three perspectives, YouTube, automatic validation.
- `/research-stack <topic> --focus seo,security`: add focus lenses. Each lens adds sub-questions, its own tool round and a required report section.
- `/research-stack <topic> #ui-ux #a11y`: the same, with tag shorthand anywhere in the prompt.
- `/research-stack <topic> --focus seo --target https://example.com`: also audit your own asset live (read-only).

A simple factual question runs auto-shallow (one round) with no flag.

## Focus tags

| Tag          | Adds                                              | Report section                |
| ------------ | ------------------------------------------------- | ----------------------------- |
| `seo`        | DataForSEO, SpyFu, Semrush, Ahrefs, GSC, PageSpeed, CrUX, schema, HubSpot AEO | SEO scorecard |
| `content`    | Foreplay, Meta Ad Library, SpyFu ads, Higgsfield, HubSpot, YouTube | Content and creative angles |
| `market`     | NinjaPear, Crunchbase, Exa, Parallel, Product Hunt, G2, VIKTOR | Vendor and competitor matrix |
| `ui-ux`      | Mobbin, Refero, Figma, shadcn, Playwright, NN/g, Baymard | Pattern references |
| `a11y`       | axe-core, Lighthouse, Playwright, W3C WAI         | Accessibility checklist       |
| `perf`       | CrUX, PageSpeed, Lighthouse, Chrome DevTools, Bundlephobia | Performance budget |
| `security`   | OSV, GitHub Advisories, CISA KEV, NVD, Socket, Semgrep, Snyk, OWASP | Threat and advisory table |
| `devtools`   | Context7, DeepWiki, grep.app, GitHub, deps.dev, npm stats | Library decision matrix |
| `ai-agents`  | Claude docs, arXiv, Semantic Scholar, Artificial Analysis, promptfoo | Model and eval evidence |
| `data-infra` | Vendor docs, Jepsen, DB-Engines, status pages, gcloud | Data and infra trade-offs |
| `comms`      | RingCentral, Twilio, Telnyx, Aircall, Dialpad, CallRail, FCC rules | Telephony and messaging plan |
| `legal`      | Legal Data Hunter, official statutes, regulators  | Legal authority table         |

Bundles: `#launch` (seo, perf, a11y, content), `#ship-audit` (security, perf, a11y), `#competitive` (market, seo, content), `#build-pick` (devtools, security). At most 4 tags per run. With no tag, the scope gate suggests matching tags; it never applies them on its own.

## Flags

- `--deep`: comprehensive run (see above). Paid deep-research calls only if configured and confirmed.
- `--free`: never call a paid provider, even when a key is set.
- `--focus <tags>` / `#tag`: focus lenses and bundles.
- `--target <url|repo|path>`: live, read-only audit by each active lens.
- `--no-ask`: no clarifying question; the scope gate becomes a one-line notice.
- `--validate`: run the validation gate (automatic on `--deep`).
- `--auto-refine`: loop until findings are stable (max 3 iterations).
- `--youtube`: read talk and tutorial transcripts.
- `--notes`: one note per source next to the cache file.
- Power tier (`references/power-tier.md`): `--vault`, `--notebook <name>`, `--content audio|slides|mind-map|infographic`, `--gemini-pro`, `--groq-model <model>`.

## Examples

- `/research-stack is Postgres row-level security enough for a multi-tenant SaaS #security #data-infra`
- `/research-stack which React form library for a 30-field onboarding flow #build-pick --focus ui-ux`
- `/research-stack launch readiness for our pricing page #launch --target https://example.com/pricing`
- `/research-stack AI meeting-notes tools for agencies #competitive --deep`
- `/research-stack WCAG 2.2 focus requirements for modal dialogs --focus a11y --free`
- `/research-stack eval harness for a research agent --focus ai-agents --vault --notebook "AI Agents & Orchestration"`

## Cost (dated 2026-10; check pricing pages)

| Run                             | Free-only | With paid providers          |
| ------------------------------- | --------- | ---------------------------- |
| auto-shallow                    | $0        | ~$0.01                       |
| default                         | $0        | ~$0.05, plus ~$0.10-0.50 per paid lens |
| `--deep`                        | $0        | ~$5-15 (deep-research calls) |

Budgets are capped per depth (`config/config.md`). Over the cap, lenses fall back to their free path.

## Execution

Follow the full research pipeline instructions in `~/.claude/skills/research-stack/SKILL.md`.

The topic to research is:

$ARGUMENTS
