# Focus lens: market (market and competitive intelligence)

Use this lens for "who else does this", "what does it cost", "who funds them", "is there room"
questions, and before any build-versus-buy call. It looks at company data, funding and real
pricing pages, and it brings in the team's own pipeline when that matters.

## Triggers

Suggested when the topic mentions market, competitors, competitive, pricing, TAM, vendors,
landscape, funding, positioning or alternatives. Bundle: `#competitive`.

## Sub-question lens

1. **Landscape:** who are the 5 to 10 real players (with funding stage, headcount and launch
   year), and which segment does each own?
2. **Pricing and packaging:** what does each charge today (copied from the pricing page, with the
   date), and where are the jumps between tiers?
3. **Momentum:** who is growing or shrinking (funding, hiring, launches, review velocity), and what
   do customers complain about?

## Tool stack

| Tool              | Tier             | Use it for                                                     | Skip when                         |
| ----------------- | ---------------- | -------------------------------------------------------------- | --------------------------------- |
| `ninjapear`       | paid (connector) | Company profile, competitor list, funding, headcount, products | `--free`; check per-call cost     |
| `crunchbase`      | paid (MCP)       | Funding rounds, acquisitions, investors                        | `--free`; not configured          |
| `exa`             | freemium (MCP)   | Company-category search and `agent_run` list-building          | quota exhausted                   |
| `parallel`        | freemium (MCP)   | Cost-tiered enrichment of a list of companies                  | fewer than 5 companies            |
| `producthunt`     | free             | Launch reception and maker replies                             | B2B enterprise niche              |
| `g2`              | free             | Review volume, ratings and complaint themes                    | consumer niche                    |
| `spyfu`           | paid (API)       | Competitor search spend and keywords                           | `--free`                          |
| `foreplay`        | paid (API)       | Competitor creative and positioning                            | `--free`                          |
| `meta-ad-library` | free             | Who is buying ads, since when                                  | no paid-social market             |
| `hubspot`         | internal         | Intent signals and deals already touching these companies      | no HubSpot portal                 |
| `viktor`          | internal         | Your own leads and pipeline in this segment                    | no pipeline data                  |

**Free-only path:** web search plus page fetch of every competitor's pricing page, `producthunt`,
`g2` site search, HN for launch threads, `meta-ad-library`, and public funding announcements.

## Authorities

The company's own pricing page and filings (sec.gov, Companies House) outrank aggregators.
Crunchbase and NinjaPear are good for structure, but treat their numbers as estimates with a date.
Reviews count by volume and recency, not by the score alone.

## Freshness

- Cache TTL: 7 days for pricing, 30 days for funding, 90 days for landscape.
- Copy prices verbatim with the date seen. Pricing pages change without notice.
- Dated trap: "contact sales" is a data point. Record it, do not guess a number.

## Audit mode

With `--target <company domain>`: profile the company (`ninjapear` or `exa`), list its competitors,
fetch its pricing page and each competitor's, and pull review themes. Tag `[AUDIT:market]`.

## Report addendum

Add a **Vendor and competitor matrix** section:

```text
### Vendor and competitor matrix
| Company       | Segment     | Price (seen 2026-10-01)  | Funding / size     | Strength           | Complaint theme     | Source       |
| ------------- | ----------- | ------------------------ | ------------------ | ------------------ | ------------------- | ------------ |
| vendor-a.com  | SMB         | $49/seat/mo, annual only | Series B, ~120 ppl | integrations       | support response    | [NP + G2]    |
```

## Pathway mapping

- pathway-operating-layer: `research`, `govern` (build versus buy, scope).
- development-protocol rows: `research`, `brainstorm` (options), `spec` (positioning).
