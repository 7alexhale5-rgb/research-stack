# Research Stack v2: Multi-Source Research Pipeline

Execute a multi-phase research pipeline combining parallel data sources, Groq-based compression, and corroboration-tagged synthesis.

---

## Step 0: Parse Intent

Extract from user input:

- **TOPIC**: Subject to research
- **DEPTH**: Auto-shallow (skill-detected), default (balanced), `--deep` (comprehensive)
- **QUERY_TYPE**: `RECOMMENDATIONS` | `NEWS` | `HOW-TO` | `GENERAL`
- **FLAGS**:

| Flag | Purpose |
|------|---------|
| `--deep` | Full Firecrawl suite, perplexity_research, 3 NB queries, extended Round 3 |
| `--vault` | Structured notes (source notes, MOC updates, NB ingestion) |
| `--notebook <name>` | Explicit NotebookLM notebook target |
| `--content <type>` | Generate NB content (audio\|slides\|mind-map\|infographic) |
| `--gemini-pro` | Use gemini-2.5-pro instead of Flash |
| `--groq-model <model>` | Override compression model (default: llama-3.3-70b-versatile) |

**Auto-shallow detection:** Evaluate whether the query is a simple factual question answerable by WebSearch + Perplexity in one round. If yes, run only Round 1 + compress + synthesize + deliver. No user flag needed.

### Auto-Notebook Routing (when `--vault` set, `--notebook` NOT set)

Read routing table from `references/notebook-routing.md`. Lowercase TOPIC, tokenize, count keyword matches per notebook, select highest match. Inform user: `Auto-routed to notebook: "{NAME}" [ID: {ID}] (matched: {keywords})`.

### NO_MATCH Flow

If zero keyword matches across all notebooks:
1. Suggest a category name based on topic analysis
2. Prompt user with options: (a) create suggested notebook, (b) pick existing, (c) skip NB
3. If (a): run `notebooklm create "{NAME}"`, remind user to update routing table

If `--notebook` is explicitly set, skip auto-routing entirely.

---

## Step 1: Startup Health Probes

Fire ALL probes in ONE parallel block. Cache results as availability flags.

| Probe | Method | Timeout |
|-------|--------|---------|
| Perplexity | `mcp__perplexity__perplexity_search` with query "test", limit 1 | 10s |
| Firecrawl | `mcp__firecrawl__firecrawl_search` with query "test", limit 1 | 10s |
| Hacker News | `mcp__hacker-news__search_hn` with query "test" | 10s |
| Gemini | `gemini -m gemini-2.5-flash -p "ping" 2>&1` (check for 429) | 10s |
| Groq (compression) | `eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null); curl -s -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models \| jq -e '.data' > /dev/null 2>&1` (exits 0 only if valid response with model data) | 5s |
| Groq (research) | `eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null); curl -s -w '\n%{http_code}' https://api.groq.com/openai/v1/chat/completions -H "Authorization: Bearer $GROQ_API_KEY" -H "Content-Type: application/json" -d '{"model":"groq/compound-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' 2>&1` (check for 200; 429 = rate limited, set `HAS_GROQ_RESEARCH` false but note "rate limited" not "unavailable") | 10s |
| NotebookLM | `notebooklm list 2>&1` | 15s |

Display availability summary to user. Set flags: `HAS_PERPLEXITY`, `HAS_FIRECRAWL`, `HAS_HN`, `HAS_GEMINI`, `HAS_GROQ`, `HAS_GROQ_RESEARCH`, `HAS_NOTEBOOKLM`.

---

## Step 2: Research Plan Gate

**HARD GATE — always pause before executing.**

Present to user:

```
Research Plan: {TOPIC}
├─ Depth: {auto-shallow | default | deep}
├─ Queries: {list planned queries}
├─ Available tools: {list from health probes}
├─ Estimated scrapes: {N pages}
├─ Estimated cost: ${X.XX}
├─ Notebook routing: {notebook name or "none"}
└─ Rounds: {1 only (shallow) | 1-2 (default) | 1-3 (deep)}

Proceed? (yes / edit / adjust depth)
```

Wait for explicit approval. If user edits, adjust plan accordingly. If user declines, stop.

### Cost confirmation for --deep

> **Cost note:** `--deep` uses perplexity_research (~$5-10/query), full Firecrawl suite, and extended Round 3. Estimated total: ~$5-15. Proceed? (yes/no)

If declined, downgrade to default depth.

---

## Step 3: ROUND 1 — Reliable Sources

Fire ALL of these in ONE parallel tool call block. These never cascade-fail.

### WebSearch (2-3 queries based on QUERY_TYPE)

| QUERY_TYPE | Query 1 | Query 2 | Query 3 (--deep only) |
|------------|---------|---------|----------------------|
| RECOMMENDATIONS | `best {TOPIC} recommendations 2026` | `{TOPIC} comparison review` | `{TOPIC} expert analysis` |
| NEWS | `{TOPIC} news 2026` | `{TOPIC} announcement update latest` | `{TOPIC} expert analysis` |
| HOW-TO | `{TOPIC} tutorial guide 2026` | `{TOPIC} best practices examples` | `{TOPIC} expert analysis` |
| GENERAL | `{TOPIC} 2026` | `{TOPIC} community discussion` | `{TOPIC} expert analysis` |

### Perplexity (depth-mapped)

| Depth | Tool | Model |
|-------|------|-------|
| auto-shallow | `perplexity_search` | sonar |
| default | `perplexity_ask` | sonar-pro |
| --deep | `perplexity_reason` | sonar-reasoning-pro |
| --deep (comprehensive) | `perplexity_research` | sonar-deep-research |

Prompt: `"Research this topic thoroughly with citations: {TOPIC}. Latest developments, key players, best practices, community sentiment. Specific facts, dates, version numbers."`

### Memory Vault Cache Check

```
Grep: pattern "{TOPIC keywords}" path ~/Projects/research-vault/research/ glob "*.md"
Grep: pattern "{TOPIC keywords}" path ~/Projects/memory-vault/ glob "*.md"
```

#### Cache Freshness Rules

Parse `date:` from YAML frontmatter or filename `YYYY-MM-DD-slug.md`:

| Cache Age | Action |
|-----------|--------|
| < 24 hours | Fresh hit. Show cached findings, ask "use cached or refresh?" |
| 1-7 days | Stale. Show with age note, ask "refresh or use cached?" |
| > 7 days | Expired. Proceed with fresh research, note outdated cache exists |

---

## Step 4: ROUND 2 — Extended Sources

**SEPARATE parallel tool call block from Round 1.** This is critical: Claude Code cancels ALL sibling parallel calls when one errors. Tiered rounds prevent cascading.

Fire all available tools in this block:

### Gemini CLI (if `HAS_GEMINI`)

```bash
# timeout: 120s
gemini -m gemini-2.5-flash -p "Research this topic thoroughly with citations and URLs: {TOPIC}. Latest developments, key players, best practices, community sentiment. Specific facts, dates, version numbers." 2>&1
```

For `--deep`: run directly (NOT background). Add "Be exhaustive. Cover all angles, competitors, alternatives, edge cases." For `--gemini-pro`: use `gemini-2.5-pro`.

**Quota handling:** If output contains research content followed by 429 error, use partial output + note "Gemini: partial (quota exhausted)" in report.

### Groq Research (if `HAS_GROQ_RESEARCH`)

**Always fires in Round 2 when available** — provides an independent LLM perspective with built-in web search, complementing Perplexity. Runs via `curl` in the same parallel block as HN/Firecrawl/last30days.

```bash
eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null)
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg topic "{TOPIC}" '{
    model: "groq/compound-mini",
    messages: [{role: "user", content: ("Research this topic with web search. Provide key findings, recent developments, community sentiment, and specific facts with URLs: " + $topic)}],
    temperature: 0.3,
    max_tokens: 2000
  }')" \
  | jq -r '.choices[0].message.content'
```

Tag output with `[GQ]`. compound-mini has built-in web search so it discovers sources independently. Timeout: 30s.

### Gemini Fallback (if NOT `HAS_GEMINI` AND NOT `HAS_GROQ_RESEARCH`)

When BOTH Gemini and Groq Research are unavailable, fire these in the Round 2 parallel block instead:

1. **Perplexity targeted follow-up** — analyze Round 1 findings, identify 1-2 specific gaps or single-source claims, run a second `perplexity_ask` with a narrow, refined query targeting those gaps. Use a different query angle than Round 1 (e.g., if Round 1 asked about features, follow-up asks about limitations/alternatives/pricing).

2. **2 extra WebSearch queries** — targeted at gaps identified from Round 1. These feed into Round 3's scrape pipeline for URL discovery.

This replaces the "second LLM perspective" with citation-backed gap-filling at ~$0.02 extra cost. Note in report: `Gemini + Groq Research: unavailable — used Perplexity follow-up + extra WebSearch`.

### Hacker News (if `HAS_HN`)

```
mcp__hacker-news__search_hn: query "{TOPIC}", limit 10
```

For high-scoring results, fetch details with comments.

### Firecrawl Search (if `HAS_FIRECRAWL`)

| Depth | Tools | Limit |
|-------|-------|-------|
| auto-shallow | none | -- |
| default | search + scrape (3-5 pages) | 10 |
| --deep | search + scrape (5-7) + map (docs sites) + extract (structured data) | 15 |
| --deep + agent | above + `firecrawl_agent` (URL-scoped only) | 15 |

**Firecrawl Agent (`--deep` only):** The agent is powerful but costs are dynamic and unpredictable (typically 15-500 credits per run). Only use when:
- Depth is `--deep`
- You have specific URLs discovered in Rounds 1-2 to scope the agent to
- The prompt targets a specific data extraction goal (e.g., "Compare pricing tiers from these pages")

Always pass discovered URLs via the `urls` parameter — never run the agent open-ended. The MCP tool does NOT expose `maxCredits`, so keep prompts narrow. If the agent returns no data (credit limit hit), fall back to `firecrawl_scrape` on those URLs.

```
mcp__firecrawl__firecrawl_agent: prompt "{specific extraction goal}", urls ["{URL1}", "{URL2}"]
```

```
mcp__firecrawl__firecrawl_search: query "{TOPIC}", limit {N}, lang "en"
```

**Note:** `formats` param must be a JSON array `["markdown"]`, not a string.

### last30days Script (background)

```bash
python3 ~/.claude/skills/last30days/scripts/last30days.py "{TOPIC}" --emit=compact 2>&1
```

### NotebookLM (if `HAS_NOTEBOOKLM`)

Auto-route via `references/notebook-routing.md` and query best-match notebook. ALWAYS query if available — no `--notebook` flag needed for READ. Only gate WRITE/ingest behind `--notebook`.

```bash
notebooklm use {NOTEBOOK_ID} && notebooklm ask "What are the key findings, themes, and evidence about {TOPIC}? Include specific citations." 2>&1
```

For `--deep`, add 2 follow-ups:
```bash
notebooklm ask "What contradictions, gaps, or disagreements exist across sources about {TOPIC}?" 2>&1
notebooklm ask "What specific data points, statistics, or quantitative evidence about {TOPIC}?" 2>&1
```

Timeout: 60s per query. Skip silently on error.

---

## Step 5: GAP CHECK + ROUND 3

After Rounds 1+2 complete, collect all background task outputs. Then:

1. **Review all gathered data** from both rounds
2. **Auto-identify 1-3 gaps** — missing perspectives, unanswered sub-questions, single-source claims needing verification
3. **Fire targeted queries:**
   - Specific WebSearch queries to fill gaps
   - Firecrawl scrape of discovered URLs from Rounds 1-2
   - For `--deep`: `firecrawl_map` on docs sites, `firecrawl_extract` for structured data
4. **Scrape top URLs** from search results:

**URL priority:** Official docs/changelogs > blog posts/tutorials > GitHub repos > news articles > forum threads.

| Depth | Scrapes |
|-------|---------|
| auto-shallow | 0 |
| default | 3-5 |
| --deep | 5-7 |

If `HAS_FIRECRAWL`:
```
mcp__firecrawl__firecrawl_scrape: url "{URL}", formats ["markdown"], onlyMainContent true
```

Else: use WebFetch with extraction prompt.

5. **Present findings summary** and ask: "Want me to dig deeper into anything before I synthesize?"

---

## Step 6: COMPRESS via Groq API

Two modes based on page count. ~$0.001 total for batch, ~$0.0004 per page for individual.

### Batch Mode (3+ pages scraped) — kimi-k2

Concatenate all scraped pages into a single temp file with delimiters, then send to kimi-k2 (262K context) in one call:

```bash
# Write all pages into single file with delimiters
for i in /tmp/research-compress-*.txt; do
  echo "---PAGE BREAK--- $(basename $i)"
  cat "$i"
done > /tmp/research-compress-batch.txt

eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null)
cat /tmp/research-compress-batch.txt | curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat)" --arg topic "{TOPIC}" '{
    model: "moonshotai/kimi-k2-instruct-0905",
    messages: [{role: "user", content: ("You are compressing research pages about " + $topic + ". For EACH page (separated by ---PAGE BREAK---), extract ONLY key facts, data points, names, versions, dates, and actionable insights. Group your output by page. Concise bullets. No preamble.\n\n" + $content)}],
    temperature: 0.1,
    max_tokens: 3000
  }')" \
  | jq -r '.choices[0].message.content'
```

**Batch fallback:** If kimi-k2 errors (model unavailable, context overflow, timeout >60s), fall back to per-page mode with llama-3.3-70b.

### Per-Page Mode (1-2 pages scraped) — llama-3.3-70b

Write scraped content to temp file first, then pipe:

```bash
eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null)
cat /tmp/research-compress-{N}.txt | curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat)" --arg topic "{TOPIC}" '{
    model: "llama-3.3-70b-versatile",
    messages: [{role: "user", content: ("Extract ONLY key facts, data points, names, versions, dates, and actionable insights about " + $topic + ". Concise bullets. No preamble.\n\n" + $content)}],
    temperature: 0.1,
    max_tokens: 1000
  }')" \
  | jq -r '.choices[0].message.content'
```

### Shared Rules

If `--groq-model` flag set, use that model for BOTH modes (overrides kimi-k2 and llama-3.3-70b). Clean up temp files after: `rm -f /tmp/research-compress-*.txt /tmp/research-compress-batch.txt`.

**If Groq unavailable** (`HAS_GROQ` false): pass raw content to Claude for synthesis. Note "Groq: unavailable, using raw content" in report.

---

## Step 6.5: SYNTHESIS ASSIST via Groq (`--deep` only)

**Only fires when:** depth is `--deep` AND `HAS_GROQ` is true.

After compression, send all compressed findings (with source tags preserved) to qwen3-32b for a structured pre-synthesis draft. This offloads pattern detection to a fast model so Claude can focus on editorial judgment.

```bash
# Collect all compressed output into a single payload
eval $(grep '^export GROQ_API_KEY' ~/.zshrc 2>/dev/null)
cat /tmp/research-compressed-all.txt | curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg content "$(cat)" --arg topic "{TOPIC}" '{
    model: "qwen/qwen3-32b",
    messages: [{role: "user", content: ("You are a research analyst. Given compressed findings about " + $topic + ", produce a structured draft with these sections:\n\n1. **Key Findings** (ranked by source count, preserve [TAG] source markers)\n2. **Contradictions** (where sources disagree)\n3. **Patterns** (themes appearing in 2+ sources)\n4. **Gaps** (what the research does NOT cover)\n\nBe precise. Preserve all source tags. No preamble. /no_think\n\n" + $content)}],
    temperature: 0.2,
    max_tokens: 2000
  }')" \
  | jq -r '.choices[0].message.content' \
  | perl -0777 -pe 's/<think>.*?<\/think>\s*//gs'
```

Save the draft output. Claude uses this as a **synthesis starting point** in Step 7 — not as final output. Claude still applies editorial judgment, resolves ambiguities, and restructures for the user.

**If qwen3 errors:** Skip silently. Claude synthesizes from compressed findings directly (standard path). Note "Synthesis assist: unavailable" in report dashboard.

---

## Step 7: SYNTHESIZE

Weight sources by reliability:

| Source | Weight |
|--------|--------|
| NotebookLM (grounded RAG) | Highest |
| Perplexity (citation-backed) | Highest |
| Reddit/X (via last30days) | High |
| Hacker News MCP | High |
| Gemini CLI | High |
| Groq Research (compound-mini) | High |
| Scraped content (compressed) | Medium |
| WebSearch snippets | Lower |

### Synthesis Rules
1. **Patterns**: Themes in 2+ sources = strongest signals
2. **Contradictions**: Flag where sources disagree
3. **Specifics**: Extract exact names, versions, dates, numbers
4. **Ground in research**: Report what sources say, not pre-existing knowledge
5. **Engagement signals**: Note upvote counts, comment counts, sentiment as confidence indicators

### Source Tags

Tag every finding with its sources:

| Tag | Source |
|-----|--------|
| `[PX]` | Perplexity |
| `[GM]` | Gemini |
| `[RD:r/sub(score)]` | Reddit (subreddit + score) |
| `[X:likes]` | Twitter/X |
| `[HN:pts]` | Hacker News (points) |
| `[FC:domain]` | Firecrawl scrape |
| `[WS]` | WebSearch |
| `[NB]` | NotebookLM |
| `[GQ]` | Groq Research (compound-mini) |
| `[L30]` | last30days |

---

## Step 8: USER STEERING

Before final delivery, present brief summary:

> I've covered [list of topics/angles]. Key themes: [themes]. Anything else to dig into before I finalize?

If user says no or wants results, proceed to deliver.

---

## Step 9: DELIVER

### Output Format

```
## Research: {TOPIC}

### Key Findings
- [5/8 sources] Finding — detail [PX + RD:r/sub(69) + HN:42 + GM + FC:docs.example.com]
- [3/8 sources] Finding — detail [PX + WS + FC:blog.example.com]
- [1/8 sources] Finding — detail [RD:r/sub(120)] — single-source, verify independently

### Contradictions
- Source A says X [PX], Source B says Y [RD] — analysis

### Patterns (2+ sources)
- Pattern [PX + GM + HN]

### Notable Details
- Specific fact, version, date [FC:docs.example.com]
- Data point or quote [HN:342]
```

### Source Stats Dashboard

```
---
Research Stack v2 Report
├─ Perplexity: {tool used} ({model}) | ${cost}
├─ Gemini: {model} | {status}
├─ Groq Research: compound-mini | {status}
├─ Groq Compression: {n} pages | {batch|per-page} mode | ~${cost} | {model}
├─ Groq Synthesis Assist: {qwen3-32b | skipped (not --deep) | unavailable}
├─ Hacker News: {n} stories | {sum} points
├─ Firecrawl: {n} searched | {n} scraped | {tools used}
├─ WebSearch: {n} results from {top domains}
├─ last30days: {n} items | {engagement}
├─ NotebookLM: {n} queries | notebook: "{name}" | {n} citations
├─ Vault: cached to ~/Projects/research-vault/research/{slug}.md
├─ Est. total cost: ${X.XX}
└─ Sources: {list of domains}

Ask me anything about {TOPIC} — I'm now an expert.
```

Use real numbers. If a source was unavailable, say so.

---

## Step 10: AUTO-CACHE to Vault

**Always runs. No flag needed.** Write compact summary for future cache hits:

```
Write:
  file_path: ~/Projects/research-vault/research/{date}-{topic-slug}.md
  content: |
    ---
    date: {YYYY-MM-DD}
    type: research
    topic: "{TOPIC}"
    depth: {depth}
    tags: [research, {topic-slug}]
    sources_count: {N}
    ---

    # Research Cache — {TOPIC}

    ## Key Findings
    {5-7 bullet points with source tags}

    ## Sources
    {list of URLs used}

    ## Patterns
    {2-3 cross-source patterns}
```

### Structured Vault Output (gated on `--vault`)

Only when `--vault` AND `~/Projects/research-vault/CLAUDE.md` exists:

**Research note:** Write to `~/Projects/research-vault/research/Research - {TOPIC_SLUG}.md` with full frontmatter, executive summary, findings with `[[Source - {Title}]]` wikilinks, patterns, and source table.

**Source notes:** For each scraped URL (top 3 default, all for `--deep`), write to `~/Projects/research-vault/sources/Source - {TITLE_SLUG}.md` with key takeaways and backlinks.

**MOC update:** Search `~/Projects/research-vault/moc/` for matching MOC. If found, append link. Do NOT create new MOCs.

**NotebookLM ingestion** (requires `--notebook`):
```bash
notebooklm use {NOTEBOOK_ID} && notebooklm source add "{URL}" 2>&1
```
Up to 5 URLs default, 10 for `--deep`. Skip failures silently.

**Content generation** (requires `--content` + `--notebook`):
```bash
notebooklm generate {TYPE} "Create an overview of {TOPIC}" --wait 2>&1
notebooklm download {TYPE} ~/Projects/research-vault/assets/{TYPE}/{SLUG}.{ext} 2>&1
```
Type mapping: audio=`.mp3`, slides=`.pdf`, mind-map=`.json`, infographic=`.png`.

---

## Step 11: Expert Mode

After delivering results, you are an expert on {TOPIC} for the rest of this conversation.

- Answer follow-ups from gathered research — do NOT run new searches
- Only run NEW research if asked about a clearly different topic
- If asked "what sources?" — list specific URLs scraped

---

## Depth Tier Summary

| Tier | Perplexity | Gemini | Scrapes | Firecrawl | NB Queries | Groq | Rounds | Est. Cost |
|------|-----------|--------|---------|-----------|------------|------|--------|-----------|
| auto-shallow | search (sonar) | Flash | 0 | none | 1 (if avail) | compress only (per-page) | 1 | ~$0.01 |
| default | ask (sonar-pro) | Flash | 3-5 | search + scrape | 1 (if avail) | compound-mini + compress (batch if 3+) | 1-2 | ~$0.05 |
| --deep | reason + research | Flash/Pro | 5-7 | full suite | 3 (if avail) | compound-mini + batch compress + qwen3 synthesis | 1-3 | ~$5-15 |

---

## Graceful Degradation

| Source | If It Fails | Fallback |
|--------|-------------|----------|
| Perplexity | API error / timeout | Extra WebSearch queries (2-3) |
| Gemini CLI (full) | Auth / timeout / not installed | Perplexity targeted follow-up (gap query) + 2 extra WebSearch |
| Gemini CLI (429) | Quota exhausted mid-request | Use partial output + Perplexity follow-up + 1-2 extra WebSearch |
| Firecrawl agent | Credit limit hit / no data returned | `firecrawl_scrape` on same URLs |
| Firecrawl search | API error | WebSearch for URL discovery |
| Firecrawl scrape | Error on URL | WebFetch for that URL |
| Groq Research | API error / rate limit | Skip, note in report (Gemini or Perplexity follow-up covers gap) |
| Groq compression (kimi-k2 batch) | Model error / context overflow / timeout | Fall back to per-page llama-3.3-70b |
| Groq compression (per-page) | Unavailable / error | Pass raw content to Claude |
| Groq synthesis assist (qwen3) | Model error / timeout | Skip, Claude synthesizes directly |
| Hacker News | Server error | Skip, note in report |
| last30days | Script missing / error | Skip, note in report |
| NotebookLM | Auth expired / timeout | Skip, note in report |
| Research vault | Directory missing | Skip cache, warn user |

**Minimum viable pipeline:** WebSearch + Perplexity.

**Complete failure:** If ALL sources fail, report what happened and suggest checking MCP configurations.
