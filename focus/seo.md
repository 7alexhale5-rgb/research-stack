# Focus lens: seo (SEO, GEO and AEO)

Use this lens when the work has to be found: by classic search, by AI overviews, or by answer
engines that quote sources. It adds ranking, visibility and technical-health questions to the run.
Measured data about the actual site and its competitors beats blog advice.

## Triggers

Suggested when the topic mentions SEO, SERP, keywords, rankings, backlinks, Search Console,
schema markup or structured data, rich results, GEO, AEO, AI overviews, LLM visibility or organic
traffic. Bundles: `#launch`, `#competitive`.

## Sub-question lens

Add these to the Step 0.5 spine, merged with the topic's own sub-questions:

1. **Demand and intent:** which queries (with volume and difficulty) does the target audience
   use, and what intent does each one serve?
2. **Competitive SERP:** who ranks or gets cited for those queries today, in the classic results
   and in AI answers, and why (content depth, links, schema, freshness)?
3. **Technical health:** what blocks indexing or ranking on the target: Core Web Vitals,
   crawlability, structured-data validity, internal linking?

## Tool stack

Fire in a dedicated Round 2F block. Go down the tiers: use connected MCPs first, then API keys,
then free fallbacks. Skip anything not relevant to the sub-questions.

| Tool                 | Tier            | Use it for                                                        | Skip when                                      |
| -------------------- | --------------- | ----------------------------------------------------------------- | ---------------------------------------------- |
| `dataforseo`         | paid (MCP)      | Keyword volume and difficulty, live SERPs, backlinks, LLM mentions | `--free`, or one-off curiosity questions       |
| `spyfu`              | paid (API)      | Competitor organic and paid keywords, years of ad history          | `--free`; no competitor named                  |
| `semrush`            | paid (MCP)      | Keyword gap and domain analytics, when the team has a plan         | not configured                                 |
| `ahrefs`             | paid (MCP)      | Backlink profile and Brand Radar AI visibility                     | not configured                                 |
| `gsc`                | free (your own) | Real clicks, impressions and queries for the target property      | the target is not your property                |
| `hubspot-aeo`        | internal        | Tracked answer-engine prompts and visibility for your brand       | the brand is not tracked in HubSpot            |
| `pagespeed`          | free            | Lab plus field performance for the target URL                     | no target URL                                  |
| `crux`               | free            | Field Core Web Vitals per origin and URL                           | low-traffic origin (no CrUX data)              |
| `schema-validator`   | free            | Structured-data validity and rich-result eligibility               | no target URL                                  |
| `firecrawl`          | freemium        | Map and crawl the target or a competitor for an on-page audit     | default depth with no target                   |

**Free-only path:** `pagespeed` + `crux` + `schema-validator` + web search scoped to the SERP
(`"{query}"`, then read the top results) + `site:` queries for indexed-page counts. Say in the
dashboard that volume and backlink numbers were unavailable rather than guessing them.

## Authorities

Rank Google Search Central (developers.google.com/search), Search Console help
(support.google.com/webmasters), schema.org, web.dev and Bing Webmaster docs above any SEO blog.
An SEO vendor's own study counts as one source, however often it is reposted.

## Freshness

- Cache TTL: 7 days for SERP and volume data, 30 days for guidance.
- Rankings and AI-answer citations move weekly. Date every number.
- Dated lesson (2026-10-01): keyless PageSpeed calls from a shared cloud IP hit the anonymous
  daily quota (429). Use a free API key, or run Lighthouse locally.
- Dated traps: Google retired FAQ rich results for most sites (2026-05). Always check rich-result
  eligibility against the current Search Central docs before recommending a schema type.

## Audit mode

With `--target <url>`:

1. Run `pagespeed` (mobile and desktop) and `crux` on the URL and its origin.
2. Fetch the page and validate its JSON-LD with `schema-validator`.
3. Check `robots.txt`, `sitemap.xml`, the canonical tag, meta robots, title and meta description
   length, and the H1.
4. With `firecrawl`, map up to 50 URLs and flag orphan or thin pages.
5. With `dataforseo` or `spyfu`, pull the target's ranking keywords and its top 3 organic
   competitors.

Tag live results `[AUDIT:psi]`, `[AUDIT:schema]` and so on.

## Report addendum

Add an **SEO scorecard** section after Coverage gaps:

```text
### SEO scorecard
| Area               | Finding (with number and date)               | Source        | Fix, ranked by impact |
| ------------------ | -------------------------------------------- | ------------- | --------------------- |
| Demand             | "{query}" 2.4k/mo, KD 38 (2026-10)            | [DFS]         | ...                   |
| SERP / AI answers  | cited: competitor-a.com, competitor-b.com     | [DFS + AEO]   | ...                   |
| Core Web Vitals    | LCP 3.1 s p75 mobile (fails 2.5 s)            | [CRUX]        | ...                   |
| Structured data    | Product schema valid, missing `offers`        | [SCHEMA]      | ...                   |
| Indexing           | ...                                           | [GSC]         | ...                   |
```

## Pathway mapping

- pathway-operating-layer: `design` (information architecture), `release` (launch checklist),
  `docs` (content).
- development-protocol rows: `research`, `spec` (acceptance criteria such as "LCP under 2.5 s"),
  `ship` (pre-launch check).
