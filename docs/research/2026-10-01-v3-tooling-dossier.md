---
date: 2026-10-01
type: research
topic: "Best-in-class research tooling per focus area, and research-agent practice, for Research Stack v3"
depth: deep
focus: [ai-agents, devtools]
target: none
sub_questions: 8
---

## Research: best-in-class research tooling for Research Stack v3

Research Stack run on itself. Method: v3 scope (8 sub-questions), Round 1 web search and Exa
search per sub-question, Round 2 vendor docs and changelogs fetched directly, GitHub for MCP server
repos, a skeptic pass over every vendor-sourced claim, and a second, independent verification
pass on items the first pass marked uncertain. Every tool claim below was read on the vendor's
own docs or changelog unless marked otherwise. The registry entries in
`references/tool-registry.json` cite this file.

### Decision answer

- Ship v3 as **free-first with targeted paid lenses**. Every focus area has a credible free
  stack: OSV, KEV, PageSpeed, CrUX, axe-core, Playwright, DeepWiki, grep.app and deps.dev
  [FC:osv.dev + FC:developer.chrome.com + FC:docs.deps.dev]. Paid tools add measured domain data
  that no free source has:
  - keyword volume and LLM mentions (DataForSEO)
  - competitor ad and keyword history (SpyFu, Foreplay)
  - real app flows (Mobbin)
  
  [FC:dataforseo.com + FC:docs.mobbin.com + FC:foreplay.co].
- **Drop or demote four v2 sources.** Reddit and X need site-scoped search or a paid path,
  Firecrawl deep-research is deprecated, and Groq is no longer a research source
  [FC:support.reddithelp.com + FC:docs.x.com + FC:firecrawl.dev + CACHE].
- **Run each focus tag in its own parallel block** and require a per-tag report section. This is
  the orchestrator-plus-workers shape that Anthropic's research system reported a 90% gain from,
  at about 15x the tokens [WS + FC:anthropic.com].

### Sub-question answers

**Q1 [devtools]: Which general search and fetch providers are current, and which have hosted MCPs?**

- Exa hosts an MCP at `mcp.exa.ai/mcp`. Its default tools are `web_search_exa` and
  `web_fetch_exa`, with `agent_run` behind `?tools=`. The older crawling and deep-researcher
  tools are deprecated [EXA + FC:exa.ai].
- Firecrawl hosts its MCP at `mcp.firecrawl.dev/v2/mcp`, and it works keyless at daily limits.
  `/v1/deep-research` has been unmaintained since 2025-06-30 and returns deprecation headers
  pointing at `/v2/search` [FC:firecrawl.dev].
- Perplexity hosts `api.perplexity.ai/mcp` with `perplexity_search`, `perplexity_ask`,
  `perplexity_reason` and `perplexity_research`. There is no free API tier [FC:docs.perplexity.ai].
- Parallel's Search MCP (`search.parallel.ai/mcp`) is free and anonymous at rate limits. Task
  MCP is billed per processor tier [FC:docs.parallel.ai].
- Brave has charged $5 per 1,000 requests, with a $5 monthly credit, since 2026-02-12 [FC:brave.com].
- Kagi hosts `mcp.kagi.com/mcp` at $12 per 1,000 searches [FC:kagi.com].
- Tavily keeps 1,000 free credits a month [FC:docs.tavily.com].

**Q2 [devtools]: Which code and library sources beat model memory?**

- Context7's hosted MCP (`mcp.context7.com/mcp`) gives 1,000 free calls a month, then throttles.
  Pro is $10 per seat [C7 + FC:context7.com].
- DeepWiki (`mcp.deepwiki.com/mcp`) is free with no auth and offers `ask_question` over any
  indexed public repo [DW + FC:docs.devin.ai].
- grep.app (`mcp.grep.app`) searches about 1M public repos [GREP + FC:vercel.com].
- deps.dev v3 gives dependency graphs, licences, advisories and OpenSSF Scorecard data with no
  key [DEPS + FC:docs.deps.dev].
- The npm downloads API is keyless [NPM + FC:github.com].
- Bundlephobia's API is undocumented and often rate-limited, so treat it as best effort
  [BP + FC:github.com].

**Q3 [seo]: Which SEO, GEO and AEO tools are agent-ready?**

- DataForSEO publishes an MCP, plus an AI Optimization API (LLM Mentions at about $0.10 per
  request plus $0.001 per row). Monthly minimums were removed on 2026-07-01. Its docs show three
  endpoint paths (`/v3/mcp`, `/mcp`, `/http`), so verify with a handshake
  [DFS + FC:dataforseo.com].
- Semrush hosts `mcp.semrush.com/v2/mcp` on paid plans [FC:developer.semrush.com].
- Ahrefs is remote-only at `api.ahrefs.com/mcp/mcp` on Lite and above. The local `@ahrefs/mcp`
  is deprecated [FC:docs.ahrefs.com].
- SpyFu has a REST API, but no official MCP was confirmed, and its auth docs disagree between
  Bearer and Basic [SPY + FC:developer.spyfu.com].
- Google ships no Search Console MCP, only community servers [FC:developers.google.com].
- PageSpeed v5 is free (keyless at low volume). The CrUX API is free with a key
  [FC:developers.google.com + FC:developer.chrome.com].
- Neither the Rich Results Test nor validator.schema.org has a public API.
- FAQ rich results stopped showing on 2026-05-07 [FC:developers.google.com].

**Q4 [content and market]: What covers ads, creative and competitors?**

- Foreplay hosts an MCP at `public.api.foreplay.co/mcp`, covering 200M+ ads across Meta, TikTok,
  YouTube and LinkedIn [FP + FC:foreplay.co].
- The Meta Ad Library API needs ID verification. Commercial ads are fully searchable via the
  API only in the EU [ADL + FC:facebook.com].
- TikTok's Creative Center has no public API. The nearest is the Commercial Content API, which
  needs approval [FC:developers.tiktok.com].
- Crunchbase has a first-party MCP (`mcp.crunchbase.com`), sold as per-user seats [CB + FC:data.crunchbase.com].
- Product Hunt's GraphQL v2 is non-commercial by default [PH + FC:api.producthunt.com].
- NinjaPear, HubSpot (AEO metrics, intent signals, content analytics), Higgsfield (virality
  prediction) and VIKTOR are already connected in this environment [INT:session-tools].

**Q5 [ui-ux and a11y]: What gives real-product evidence for UI decisions?**

- Mobbin's MCP (`api.mobbin.com/mcp`) launched in beta at the end of April 2026, with 621k+
  screens, on paid plans with OAuth [MOB + FC:docs.mobbin.com].
- Refero hosts `api.refero.design/mcp`, with 142k screens and 12k flows [REF + FC:doc.refero.design].
- Figma's remote MCP is at `mcp.figma.com/mcp` [FIG + FC:developers.figma.com].
- shadcn runs locally (`npx shadcn@latest mcp`) [SHAD + FC:ui.shadcn.com].
- Baymard and NN/g have no API; use site search [WS].
- Deque's official axe MCP server needs a paid Axe DevTools subscription, so the free path is
  axe-core inside Playwright [AXE + FC:deque.com].

**Q6 [security]: Which vulnerability sources are primary, and what changed?**

- OSV.dev (`POST api.osv.dev/v1/query` and `/v1/querybatch`) is free and keyless
  [OSV + FC:google.github.io].
- The CISA KEV JSON feed is free [KEV + FC:cisa.gov].
- Since 2026-04-15, NVD prioritises enrichment only for KEV, federal-use and EO 14028 software,
  so a missing CVSS score means unknown, not low [NVD + FC:nvd.nist.gov].
- Socket's hosted MCP (`mcp.socket.dev`) is free with OAuth [SOCK + FC:docs.socket.dev].
- Semgrep's MCP now ships inside the CLI (`semgrep mcp`) [SG + FC:github.com].
- Snyk's MCP is now Snyk Studio, in Early Access [SNYK + FC:github.com].
- OWASP Top 10:2025 adds A03 Software Supply Chain Failures and A10 Mishandling of Exceptional
  Conditions [OWASP + FC:owasp.org].
- The LLM Top 10 2026 was published on 2026-08-04 [FC:genai.owasp.org].
- The Agentic Top 10 (ASI01-ASI10) was published in December 2025 [FC:genai.owasp.org].

**Q7 [ai-agents]: What does current practice say about research-agent architecture?**

- Orchestrator plus parallel workers, each with an objective, an output format, tool guidance
  and boundaries, then a citation pass at the end. Anthropic reported a 90% gain over a single
  agent at about 15x the tokens [WS + FC:anthropic.com].
- Benchmarks of deep-research agents show faithfulness of about 0.80 to 0.86 but groundedness of
  only 0.31 to 0.59, so uncited claims are the main weakness. That supports a "specifics or cut
  it" rule plus an attribution spot-check [ACAD:arxiv].
- Citation existence is not attribution: one 2026 study measured existence F1 at 0.81 against
  attributable F1 at 0.62 [ACAD:arxiv + CACHE].

**Q8 [devtools]: What broke in the v2 source list?**

- Reddit closed self-service API keys on 2025-11-11 [FC:support.reddithelp.com].
- X moved to pay-per-use on 2026-02-06, at about $0.005 per post read [FC:docs.x.com].
- xAI `x_search` costs $5 per 1,000 calls plus tokens [XS + FC:docs.x.ai].
- Groq's `compound-mini` returned 429s naming a retired model (measured 2026-08-17) [CACHE].
- Bluesky's unauthenticated `searchPosts` is increasingly 403 [FC:docs.bsky.app].

### Contradictions

- **DataForSEO's MCP path** is `/v3/mcp` on the MCP page, `/mcp` in the OAuth help, and `/http`
  in an older guide [DFS + FC:dataforseo.com]. The registry records `/v3/mcp` and says to verify
  with a handshake.
- **SpyFu auth** is Bearer on `api.spyfu.com/v1` but Basic on the legacy endpoints. One
  directory lists an MCP at `developer.spyfu.com/mcp` that SpyFu itself does not document
  [SPY + WS]. The registry calls the REST API and notes the conflict.
- **Snyk** status reads "Early Access" on one page and is implied GA on others [SNYK + WS]. The
  registry says Early Access.

### Patterns (cross-cutting, 2+ sources)

- Vendors moved from local npm servers to **hosted remote MCPs with OAuth**: Ahrefs, Mobbin,
  Foreplay, Refero, Crunchbase, Socket, Kagi, Firecrawl and Perplexity
  [FC:docs.ahrefs.com + FC:docs.mobbin.com + FC:docs.socket.dev + FC:kagi.com]. The registry
  stores an `endpoint` per tool, and detection matches MCP prefixes rather than only API keys.
- **Free tiers shrank** in 2026: Brave removed its free tier, Context7 cut to 1,000 calls, X and
  Reddit closed theirs [FC:brave.com + FC:context7.com + FC:docs.x.com]. Every paid registry
  entry therefore names a free fallback, and the linter enforces it.
- **Primary data got less complete**: NVD enrichment triage, and Rich Results and FAQ
  deprecations [FC:nvd.nist.gov + FC:developers.google.com]. Each lens carries "dated traps"
  in its Freshness section.

### Coverage gaps

- Pricing for Foreplay, Refero and Figma API usage was not confirmed. The registry marks them
  paid with free fallbacks.
- Community Search Console and a11y MCP servers were not evaluated for maintenance.
- Rate limits for X, Meta Ad Library and Product Hunt come from secondary sources only.

### Model and eval evidence

| Claim / choice                                  | Evidence (date)                                         | Source                     | Eval that would prove it                              |
| ----------------------------------------------- | ------------------------------------------------------- | -------------------------- | ----------------------------------------------------- |
| One parallel block per focus tag                | Orchestrator-worker gain, about 15x tokens (2025-06)     | [WS + FC:anthropic.com]    | promptfoo goldens per tag in gravity-stack            |
| Require a per-tag report addendum               | Groundedness 0.31-0.59 in deep-research benchmarks (2026) | [ACAD:arxiv]             | `validate_report.py` focus check; fixture pair        |
| Attribution spot-check, not liveness only       | Existence F1 0.81 vs attributable F1 0.62 (2026)        | [ACAD:arxiv + CACHE]       | Step 8.5 spot-check rate on 5 claims per report       |

### Library decision matrix

| Candidate (tool)  | Fit for need                     | Status (2026-10)                 | Cost                 | Risk                         | Source                    |
| ----------------- | -------------------------------- | -------------------------------- | -------------------- | ---------------------------- | ------------------------- |
| Exa MCP           | semantic search, list-building   | hosted, tools consolidated       | $10/mo free credit   | deprecated tool names        | [EXA + FC:exa.ai]         |
| Firecrawl v2      | search with full content, crawl  | hosted keyless at daily limits   | 1,000 credits/mo free | `/extract` deprecated       | [FC:firecrawl.dev]        |
| Context7          | version-specific docs            | hosted, 1,000 calls/mo free      | $10/seat Pro         | free-tier cut                | [C7 + FC:context7.com]    |
| DeepWiki          | repo Q&A                         | hosted, no auth                  | free                 | throttles heavy use          | [DW + FC:docs.devin.ai]   |
| Socket            | supply-chain score               | hosted, OAuth                    | free                 | none noted                   | [SOCK + FC:docs.socket.dev] |
| Semgrep           | SAST of own code                 | MCP inside the CLI               | free rules           | hosted endpoint unverified   | [SG + FC:github.com]      |

### Sources

- https://exa.ai/docs/reference/exa-mcp
- https://docs.firecrawl.dev
- https://www.firecrawl.dev/blog/deep-research-api
- https://docs.perplexity.ai
- https://docs.parallel.ai/integrations/mcp/search-mcp
- https://brave.com/search/api/
- https://kagi.com/api/docs
- https://docs.tavily.com/documentation/mcp
- https://context7.com
- https://docs.devin.ai/work-with-devin/deepwiki-mcp
- https://vercel.com/blog/grep-a-million-github-repositories-via-mcp
- https://docs.deps.dev/api/v3/
- https://github.com/npm/registry/blob/main/docs/download-counts.md
- https://dataforseo.com/model-context-protocol
- https://developer.semrush.com/api/introduction/semrush-mcp/
- https://docs.ahrefs.com/en/mcp/docs/introduction
- https://developer.spyfu.com
- https://developers.google.com/speed/docs/insights/v5/get-started
- https://developer.chrome.com/docs/crux/guides/crux-api
- https://developers.google.com/search/updates
- https://www.foreplay.co
- https://www.facebook.com/ads/library/api/
- https://data.crunchbase.com/docs/mcp-overview
- https://api.producthunt.com/v2/docs
- https://docs.mobbin.com/mcp/introduction
- https://doc.refero.design/mcp/getting-started
- https://developers.figma.com/docs/figma-mcp-server/
- https://ui.shadcn.com/docs/mcp
- https://www.deque.com/axe/mcp-server/
- https://google.github.io/osv.dev/post-v1-query/
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- https://nvd.nist.gov/developers/vulnerabilities
- https://docs.socket.dev/docs/guide-to-socket-mcp
- https://github.com/semgrep/semgrep
- https://github.com/snyk/studio-mcp
- https://owasp.org/Top10/2025/
- https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://arxiv.org/abs/2506.11763
- https://arxiv.org/abs/2607.20891
- https://arxiv.org/abs/2604.03173
- https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy
- https://docs.x.com/x-api/getting-started/pricing
- https://docs.x.ai/developers/tools/x-search
- https://docs.bsky.app/docs/api/app-bsky-feed-search-posts

---
Research Stack report
|- Scope: 8 sub-questions, 8 covered, 3 gaps named (pricing, community MCP quality, secondary rate limits)
|- Web search: about 60 queries across two passes (built-in search and Exa)
|- Page fetch: about 70 vendor pages and changelogs read directly
|- Answer engine: not used (not configured in this environment)
|- Hacker News / community: skipped for vendor-fact sub-questions (discipline)
|- Academic: 3 papers (arXiv)
|- Internal round: session tool list (connected MCP servers) for Q4
|- Perspectives: skeptic (vendor self-claims flagged, Parallel benchmark pages discounted), cross-source (second verification pass)
|- Focus: ai-agents, devtools | seo, content, market, ui-ux, a11y and security questions folded into Q3-Q6
|- Validation: PASS. Structure 10/10, focus PASS, citations 43 live / 0 dead / 3 unverified (bot walls), checked 2026-10-01
`- Est. total cost: $0.00 (free tools and included connector quota)
