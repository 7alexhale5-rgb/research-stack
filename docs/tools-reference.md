# Tools reference

Every tool and connector Research Stack v3 can use, what it is best at, how the skill finds it,
and what it falls back to. The table between the markers is generated from
`references/tool-registry.json` by `python3 scripts/focus_check.py table`; do not edit it by hand.
`python3 scripts/focus_check.py docs` fails when it is stale.

## How tools are chosen

1. **Base sources** (`focus: base`) serve every run: web search and page fetch (built in),
   Hacker News, arXiv and Crossref (keyless), the research cache, and optional paid search
   (Perplexity, Exa, Firecrawl, Tavily, Parallel, Brave, Kagi). Internal connectors (Slack,
   Atlassian, Fireflies, Microsoft 365, Superhuman, Wispr Flow) run in Round 1.5 when the topic
   touches the team's own work.
2. **Focus tools** fire only when their tag is active, in that tag's own Round 2F block, in the
   tier order given in `focus/<tag>.md`: connected MCP or connector, then API key, then the free
   fallback.
3. **Source discipline still applies.** A configured tool that is irrelevant to the run's
   sub-questions is skipped. Skipping is discipline, not degradation.
4. **Paid tools never run on `--free`,** never run above the depth's budget cap, and always have
   a free fallback, which the linter enforces.

## Detection

`python3 scripts/focus_check.py probe <tags>` checks environment variables and CLIs, printing
"key set" or "missing", never a value. MCP and connector tools cannot be seen from a script, so
the probe prints their tool-name prefixes (for example `mcp__Exa__`, `mcp__dataforseo__`,
`mcp__HubSpot__get_aeo_metrics`) and the agent matches them against its own tool list. Hosted MCP
endpoints, where the vendor publishes one, are in each registry entry's `endpoint` field.

## Dated changes that shaped the registry (2025-2026)

- Reddit closed self-service API keys (2025-11-11); unauthenticated JSON returns 403. Community
  search is site-scoped web search, with `last30days` as a power-tier option.
- X moved to pay-per-use (2026-02-06). Optional `xai-x-search` is cheaper for agents.
- Firecrawl deprecated `/v1/deep-research` and `/extract`; use `/v2/search`. Its hosted MCP works
  keyless at daily limits.
- Brave removed its free API tier (2026-02-12).
- NVD enriches only priority CVEs since 2026-04-15, so a missing CVSS score means unknown.
- Google retired FAQ rich results (2026-05-07).
- New official MCPs: Mobbin (beta, 2026-04), Foreplay, Refero, Crunchbase, Socket, Kagi;
  Semgrep's MCP moved into its CLI; Snyk's became Snyk Studio (Early Access).
- Groq's `compound-mini` research endpoint failed on a retired upstream model (2026-08-17), so
  Groq is used for compression only.

Evidence for each line: `docs/research/2026-10-01-v3-tooling-dossier.md`.

## Registry

<!-- registry:begin -->
| Tool | Kind | Cost | Tag | Focus | Best at | Fallback |
| ---- | ---- | ---- | --- | ----- | ------- | -------- |
| [axe-core](https://github.com/dequelabs/axe-core) `axe` | cli | free | `[AXE]` | a11y | Automated WCAG 2.2 A/AA rule checks with selectors and fixes | - |
| [Lighthouse](https://developer.chrome.com/docs/lighthouse) `lighthouse` | cli | free | `[LH]` | a11y, perf | Accessibility, performance, SEO and best-practice audits | - |
| [W3C WAI (WCAG 2.2, ARIA APG)](https://www.w3.org/WAI/standards-guidelines/wcag/) `w3c-wai` | builtin | free | `[WAI]` | a11y | Normative success criteria and authoring patterns | - |
| [Artificial Analysis](https://artificialanalysis.ai) `artificial-analysis` | builtin | free | `[AA]` | ai-agents | Independent model and search-API benchmarks | - |
| [Claude platform docs](https://platform.claude.com/docs) `claude-docs` | builtin | free | `[CLD]` | ai-agents | Current model ids, limits, tool versions and pricing | - |
| [Paper search MCP (arXiv, S2, OpenAlex)](https://github.com/openags/paper-search-mcp) `paper-mcp` | mcp | free | `[PAPER]` | ai-agents | De-duplicated multi-index paper search | - |
| [promptfoo](https://www.promptfoo.dev/docs/intro/) `promptfoo` | cli | free | `[PF]` | ai-agents | Eval and red-team configs you can run in CI | - |
| [Semantic Scholar](https://api.semanticscholar.org) `semantic-scholar` | api | free | `[S2]` | ai-agents | Citation graph and influential-paper ranking | - |
| [arXiv and Crossref](https://info.arxiv.org/help/api/index.html) `arxiv` | api | free | `[ACAD]` | base, ai-agents | Papers and preprints, keyless | - |
| [Atlassian (Jira, Confluence)](https://modelcontextprotocol.io) `atlassian` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [Brave Search API](https://brave.com/search/api/) `brave` | api | paid | `[BR]` | base | Independent index for corroboration | `websearch` |
| [Research cache](https://github.com/7alexhale5-rgb/research-stack) `cache` | builtin | free | `[CACHE]` | base | Prior runs on the same topic | - |
| [Exa](https://exa.ai/docs/reference/exa-mcp) `exa` | mcp | freemium | `[EXA]` | base, market | Semantic search, company and people categories, agent_run for list-building | `websearch` |
| [Firecrawl v2](https://docs.firecrawl.dev) `firecrawl` | mcp | freemium | `[FC]` | base, seo | Search plus full page content in one call; map and crawl for site audits | `webfetch` |
| [Fireflies meeting notes](https://modelcontextprotocol.io) `fireflies` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) `gemini-cli` | cli | freemium | `[GM]` | base | Second model family with Google Search grounding | `websearch` |
| [Groq API](https://console.groq.com/docs) `groq` | api | freemium | `[GQ]` | base | Cheap batch compression and synthesis assist | - |
| [Hacker News (Algolia)](https://hn.algolia.com/api) `hn` | api | free | `[HN]` | base, devtools | Practitioner sentiment, launch reactions, engagement counts | - |
| [Kagi Search API](https://kagi.com/api/docs) `kagi` | mcp | paid | `[KAGI]` | base | High-quality, ad-free results for corroboration | `websearch` |
| [last30days script](https://github.com/7alexhale5-rgb/research-stack) `last30days` | cli | freemium | `[L30]` | base | Reddit and X sweep for the last 30 days | `reddit-search` |
| [Microsoft 365](https://modelcontextprotocol.io) `m365` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [NotebookLM (notebooklm-py)](https://github.com/teng-lin/notebooklm-py) `notebooklm` | cli | free | `[NB]` | base | Grounded Q&A over your own curated notebooks | - |
| [Parallel Search and Task](https://docs.parallel.ai) `parallel` | mcp | freemium | `[PAR]` | base, market | Cost-tiered deep research and enrichment (Task processors Lite to Ultra) | `exa` |
| [Perplexity Sonar](https://docs.perplexity.ai) `perplexity` | mcp | paid | `[PX]` | base | Citation-backed answers; Deep Research for long-form synthesis | `websearch` |
| [Reddit via site-scoped search](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) `reddit-search` | builtin | free | `[RD]` | base | Lived experience threads (site:reddit.com) | - |
| [Slack](https://modelcontextprotocol.io) `slack` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [Superhuman Mail](https://modelcontextprotocol.io) `superhuman` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [Tavily](https://docs.tavily.com) `tavily` | api | freemium | `[TV]` | base | Simple /search and /research endpoints with a monthly free allowance | `websearch` |
| [Page fetch (agent built-in)](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool) `webfetch` | builtin | free | `[FC]` | base | Reading one known URL with an extraction prompt | - |
| [Web search (agent built-in)](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool) `websearch` | builtin | free | `[WS]` | base | Broad discovery, recency queries, site: scoping | - |
| [Wispr Flow notes](https://modelcontextprotocol.io) `wispr` | connector | internal | `[INT]` | base | What the team already knows, decided or promised | - |
| [xAI x_search](https://docs.x.ai) `xai-x-search` | api | paid | `[XS]` | base | Recent X posts with engagement, cheaper than the X API for agents | `websearch` |
| [YouTube transcripts (yt-dlp)](https://github.com/yt-dlp/yt-dlp) `youtube` | cli | free | `[YT]` | base, content | Talks, tutorials and teardown videos as primary content | - |
| [Aircall](https://developer.aircall.io) `aircall` | api | paid | `[AIR]` | comms | Buy-not-build power dialer, voicemail drop and AI notes with a public API | `fcc-telecom` |
| [CallRail](https://apidocs.callrail.com) `callrail` | api | paid | `[CR]` | comms | Call tracking numbers (DNI) and session attribution; official RingCentral integration | `fcc-telecom` |
| [Dialpad](https://developers.dialpad.com) `dialpad` | api | paid | `[DP]` | comms | UCaaS with built-in AI recaps; Sell tier for sales dialing | `fcc-telecom` |
| [FCC, eCFR and CTIA telecom rules](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-64/subpart-L/section-64.1200) `fcc-telecom` | builtin | free | `[FCC]` | comms | TCPA, consent revocation, calling hours, 10DLC and STIR/SHAKEN primary text | - |
| [RingCentral developer platform (RingEX, RingCX, ACE)](https://developers.ringcentral.com) `ringcentral` | api | paid | `[RC]` | comms | UCaaS phone system plus REST, WebPhone 2.x and Embeddable; RingCX for campaign dialing | `fcc-telecom` |
| [Telnyx Voice API and Messaging](https://developers.telnyx.com) `telnyx` | api | paid | `[TNX]` | comms | Lowest per-minute CPaaS cost, WebRTC SDK | `fcc-telecom` |
| [Twilio Voice, Messaging and Conversational Intelligence](https://www.twilio.com/docs) `twilio` | api | paid | `[TW]` | comms | Fully programmable voice and SMS, AMD, number pools; best fit for a custom-built dialer | `fcc-telecom` |
| [Foreplay](https://www.foreplay.co) `foreplay` | mcp | paid | `[FP]` | content, market, ui-ux | Ad library, swipe files and brand spy across Meta, TikTok and LinkedIn creative | `meta-ad-library` |
| [Higgsfield](https://higgsfield.ai) `higgsfield` | connector | internal | `[HF]` | content | Virality prediction and video analysis for short-form creative | - |
| [HubSpot marketing and CRM](https://developers.hubspot.com) `hubspot` | connector | internal | `[HS]` | content, market | Content analytics, campaign attribution, intent signals | - |
| [Meta Ad Library](https://www.facebook.com/ads/library/api) `meta-ad-library` | api | free | `[ADL]` | content, market | Live and historical ads per advertiser; political ads with spend | - |
| [DB-Engines](https://db-engines.com) `db-engines` | builtin | free | `[DBE]` | data-infra | Database popularity and system properties | - |
| [Google Cloud CLIs and managed MCPs](https://cloud.google.com/sdk/docs) `gcloud` | cli | free | `[GCP]` | data-infra | Live quotas, regions and service status on your own project | - |
| [Jepsen analyses](https://jepsen.io/analyses) `jepsen` | builtin | free | `[JEP]` | data-infra | Independent consistency and failure-mode testing | - |
| [Provider status and incident history](https://www.githubstatus.com) `status-pages` | builtin | free | `[STATUS]` | data-infra | Reliability track record | - |
| [Vendor docs and changelogs](https://www.postgresql.org/docs/) `vendor-docs` | builtin | free | `[DOCS]` | data-infra | Limits, pricing, deprecations straight from the source | - |
| [Context7](https://context7.com) `context7` | mcp | freemium | `[C7]` | devtools | Version-specific library docs | `deepwiki` |
| [DeepWiki](https://docs.devin.ai/work-with-devin/deepwiki-mcp) `deepwiki` | mcp | free | `[DW]` | devtools | Questions answered from a public GitHub repo's code | - |
| [deps.dev](https://docs.deps.dev/api/) `deps-dev` | api | free | `[DEPS]` | devtools | Dependency graph, licences, advisories, OpenSSF Scorecard | - |
| [GitHub code, releases and issues](https://github.com/github/github-mcp-server) `github-code` | mcp | free | `[GH]` | devtools | Release notes, open issues, maintenance signal | - |
| [grep.app](https://grep.app) `grep-app` | mcp | free | `[GREP]` | devtools | How public repos actually use an API | - |
| [npm downloads API](https://github.com/npm/registry/blob/main/docs/download-counts.md) `npm-stats` | api | free | `[NPM]` | devtools | Adoption trend per package | - |
| [Legal Data Hunter](https://legaldatahunter.com) `legal-data-hunter` | mcp | freemium | `[LDH]` | legal | Statutes and case law across 230+ jurisdictions with citations | `official-statutes` |
| [Official statute sites (EUR-Lex, eCFR, legislation.gov.uk)](https://eur-lex.europa.eu) `official-statutes` | builtin | free | `[STAT]` | legal | The text of the law itself | - |
| [Regulator guidance (EDPB, ICO, FTC)](https://www.edpb.europa.eu) `regulators` | builtin | free | `[REG]` | legal | How the law is enforced and interpreted | - |
| [Crunchbase](https://about.crunchbase.com) `crunchbase` | mcp | paid | `[CB]` | market | Private-market funding rounds, acquisitions, investors | `websearch` |
| [G2 reviews (site search)](https://www.g2.com) `g2` | builtin | free | `[G2]` | market | Buyer reviews and category grids | - |
| [NinjaPear](https://nubela.co) `ninjapear` | connector | paid | `[NP]` | market | Company details, competitors, funding, headcount, products | `exa` |
| [Product Hunt API v2](https://api.producthunt.com/v2/docs) `producthunt` | api | free | `[PH]` | market | Launch reception, upvotes and maker comments | - |
| [VIKTOR pipeline](https://modelcontextprotocol.io) `viktor` | connector | internal | `[VK]` | market | Your own leads, pipeline and deliverables | - |
| [Bundlephobia](https://bundlephobia.com) `bundlephobia` | api | free | `[BP]` | perf, devtools | Minified and gzipped cost of an npm package | - |
| [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) `chrome-devtools` | mcp | free | `[CDT]` | perf | Performance traces with Core Web Vitals and network waterfalls | - |
| [HTTP Archive and Web Almanac](https://httparchive.org) `httparchive` | builtin | free | `[HA]` | perf | Population-level web performance baselines | - |
| [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) `cisa-kev` | api | free | `[KEV]` | security | Exploited-in-the-wild signal | - |
| [GitHub Advisory Database](https://github.com/advisories) `ghsa` | mcp | free | `[GHSA]` | security | Reviewed advisories with affected ranges and patches | - |
| [NVD CVE API](https://nvd.nist.gov/developers/vulnerabilities) `nvd` | api | free | `[NVD]` | security | CVE records and CVSS where enriched | - |
| [OSV.dev](https://google.github.io/osv.dev/api/) `osv` | api | free | `[OSV]` | security | Known vulnerabilities by package and version across ecosystems | - |
| [OWASP Top 10:2025, LLM Top 10, Agentic Top 10](https://owasp.org/Top10/2025/) `owasp` | builtin | free | `[OWASP]` | security | Risk categories to map findings against | - |
| [Secret scanning (gitleaks, trufflehog, GitHub)](https://github.com/gitleaks/gitleaks) `secret-scan` | cli | free | `[SECRET]` | security | Leaked credentials in a repo or history | - |
| [Semgrep](https://github.com/semgrep/mcp) `semgrep` | mcp | free | `[SG]` | security | Static analysis of your own code against community and OWASP rules | - |
| [Snyk Studio (MCP)](https://github.com/snyk/studio-mcp) `snyk` | mcp | freemium | `[SNYK]` | security | SCA, code, IaC, container and secret scans with fix advice | `osv` |
| [Socket](https://docs.socket.dev) `socket` | mcp | free | `[SOCK]` | security, devtools | Supply-chain risk score per package (malware, install scripts, typosquats) | `osv` |
| [Ahrefs](https://docs.ahrefs.com) `ahrefs` | mcp | paid | `[AHR]` | seo | Backlink index, Site Explorer, Brand Radar AI visibility | `websearch` |
| [Chrome UX Report API](https://developer.chrome.com/docs/crux/api) `crux` | api | free | `[CRUX]` | seo, perf | Field Core Web Vitals (LCP, INP, CLS) at origin or URL level | `pagespeed` |
| [DataForSEO](https://dataforseo.com/model-context-protocol) `dataforseo` | mcp | paid | `[DFS]` | seo, content | SERP, keyword volume, backlinks, on-page, AI Optimization (LLM mentions and responses) | `pagespeed` |
| [Google Search Console](https://developers.google.com/webmaster-tools) `gsc` | mcp | free | `[GSC]` | seo | Real clicks, impressions, queries and index coverage for a property you own | - |
| [HubSpot AEO](https://developers.hubspot.com) `hubspot-aeo` | connector | internal | `[AEO]` | seo | Answer-engine visibility metrics, tracked prompts and recommendations | - |
| [PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started) `pagespeed` | api | free | `[PSI]` | seo, perf | Lab Lighthouse plus field CrUX data for one URL | `lighthouse` |
| [Schema.org validator and Rich Results Test](https://validator.schema.org) `schema-validator` | builtin | free | `[SCHEMA]` | seo | Structured data validity and rich-result eligibility | - |
| [Semrush](https://www.semrush.com/kb/1618-mcp) `semrush` | mcp | paid | `[SEM]` | seo | Keyword gap, domain analytics, position tracking | `websearch` |
| [SpyFu](https://developer.spyfu.com) `spyfu` | api | paid | `[SPY]` | seo, content, market | Competitor organic and PPC keywords, ad copy history, domain overlap | `websearch` |
| [Awwwards and Dribbble (site search)](https://www.awwwards.com) `awwwards` | builtin | free | `[AWW]` | ui-ux | Visual direction and interaction inspiration | - |
| [Baymard Institute](https://baymard.com) `baymard` | builtin | freemium | `[BAY]` | ui-ux | E-commerce UX benchmarks and checkout research | - |
| [Figma MCP](https://help.figma.com/hc/en-us/articles/32132100833559) `figma` | mcp | freemium | `[FIG]` | ui-ux | Component tree, variables and Code Connect from your own files | - |
| [Mobbin](https://mobbin.com) `mobbin` | mcp | paid | `[MOB]` | ui-ux | Real app screens and flows by pattern (onboarding, paywall, checkout) | `refero` |
| [Nielsen Norman Group (site search)](https://www.nngroup.com) `nngroup` | builtin | free | `[NNG]` | ui-ux | Evidence-based usability guidance | - |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) `playwright` | mcp | free | `[PW]` | ui-ux, a11y | Drive and screenshot real flows; run axe in the page | - |
| [Refero](https://refero.design) `refero` | mcp | paid | `[REF]` | ui-ux | Web and marketing-site screens and flows | `awwwards` |
| [shadcn registry MCP](https://ui.shadcn.com/docs/mcp) `shadcn` | mcp | free | `[SHAD]` | ui-ux | Accurate component APIs and registry blocks | - |
<!-- registry:end -->

## Source tags

Base tags are listed in `references/providers.md` (Source tags). Each focus tag's tags are in
`focus/tags.json` (`source_tags`). The validator loads both, so a bracket tag that appears in
neither does not count as a source.
