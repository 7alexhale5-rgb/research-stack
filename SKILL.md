<!-- CONFIGURATION: Customize these values for your setup -->
<!-- VAULT_PATH: Path to your Obsidian/markdown research vault (default: ~/research-vault/) -->
<!-- NOTEBOOK_IDS: Run `notebooklm list` to get your notebook IDs, then update references/notebook-routing.md -->

# Research Stack: Hybrid Multi-Source Research Pipeline

You are executing a multi-phase research pipeline that combines multiple data sources in parallel, compresses scraped content locally via Ollama, and synthesizes everything into actionable insights. This pipeline is portable across Claude Code and OpenClaw/MikeLawdbot.

---

## Step 0: Parse Intent

From the user's input, extract:

- **TOPIC**: The subject to research (everything except flags)
- **DEPTH**: `--shallow` (fastest, no scraping), `--quick` (fewer sources), default (balanced), `--deep` (comprehensive)
- **QUERY_TYPE**: Classify as one of:
  - **RECOMMENDATIONS** — "best X", "top X", "what X should I use"
  - **NEWS** — "what's happening with X", "X news", "latest on X"
  - **HOW-TO** — "how to X", "X tutorial", "X guide"
  - **GENERAL** — anything else
- **FLAGS**: Check for optional override flags:
  - `--perplexity` — use Perplexity MCP instead of Gemini CLI for the AI research source
  - `--no-compress` — skip Ollama compression, send raw scraped content to Claude
  - `--gemini-pro` — use Gemini 2.5 Pro instead of Flash (higher quality, lower rate limits)
  - `--vault` — write structured output to Obsidian research vault (`~/research-vault/`)
  - `--notebook <name>` — specify NotebookLM notebook to query/ingest (requires notebooklm-py CLI)
  - `--content <type>` — generate content via NotebookLM (audio|slides|mind-map|infographic), requires `--notebook`

### Auto-Notebook Routing (when `--vault` is set but `--notebook` is NOT)

When `--vault` is set, automatically resolve the best notebook using keyword routing. Read the routing table from `references/notebook-routing.md` and apply this algorithm:

1. Lowercase the TOPIC, tokenize into words (split on spaces, hyphens, slashes)
2. For each notebook in the routing table, count keyword matches against the topic tokens
3. Select the notebook with the highest match count (tie-breaker: first in table)
4. If a match is found: set `NOTEBOOK_NAME` and `NOTEBOOK_ID` from the routing table and inform the user:
   `Auto-routed to notebook: "{NOTEBOOK_NAME}" [ID: {NOTEBOOK_ID}] (matched: {keywords})`
5. If NO keywords match any notebook (zero matches across all): trigger NO_MATCH flow

### NO_MATCH Flow

When auto-routing finds no matching notebook:

1. Analyze the topic to suggest a category name
2. Prompt the user:
   ```
   No existing notebook matches "{TOPIC}".
   Suggested notebook: "{SUGGESTED_NAME}"

   Options:
   a) Create "{SUGGESTED_NAME}" and route research there
   b) Route to an existing notebook: [show list]
   c) Skip NotebookLM for this run (--vault only)
   ```
3. If (a): run `notebooklm create "{SUGGESTED_NAME}"`, use it, and remind user to update routing table
4. If (b): use the selected notebook
5. If (c): clear `--notebook`, skip NB steps, vault-only mode

### Explicit `--notebook` Override

If the user explicitly passes `--notebook "Name"`, skip auto-routing entirely and use their specified notebook. Auto-routing only activates when `--vault` is set WITHOUT `--notebook`.

Store these for use throughout the pipeline.

---

## Step 0.25: Cost Confirmation for --deep

If DEPTH is `--deep`, pause and inform the user before proceeding:

> **Cost note:** `--deep` runs extra search queries, scrapes 5-7 pages, and uses Gemini for extended research. Estimated cost: ~$0.10-0.20 (vs ~$0.05 for default).
> If `--perplexity` flag is also set, `--deep` will use `sonar-deep-research` (~$5-10 per query) — confirm before proceeding.
> Proceed with --deep? (yes/no)

- If `--deep` WITHOUT `--perplexity`: proceed without cost gate (Gemini is free)
- If `--deep` WITH `--perplexity`: cost gate is mandatory (sonar-deep-research is expensive)
- If user declines: downgrade to default depth and proceed.

---

## Step 0.5: Check Memory Cache

Before doing ANY research, check if we have recent findings on this topic:

```
mcp__memory-layer__search_memories:
  query: "{TOPIC}"
  collection: "research-cache"
  limit: 3
```

If results exist and are relevant (same topic), apply TTL-based validation:

### Cache Freshness Rules

Parse the `Date:` field from the cached result content to determine age.

| Cache Age | Action |
|-----------|--------|
| **< 24 hours** | **Fresh hit.** Show cached findings with note: "Found cached research from [date] (less than 24h old). Showing previous results." Enter Expert Mode with cached data. Skip to Step 7. |
| **1-7 days old** | **Stale but usable.** Show cached findings with note: "Found cached research from [date] ([N] days ago)." Ask: "Want me to refresh this research or use the cached version?" If user says refresh, proceed to Step 1. Otherwise, enter Expert Mode with cached data. |
| **> 7 days old** | **Expired.** Treat as a cache miss. Note: "Found outdated research from [date] (over 7 days old) — running fresh research." Proceed to Step 1. |

If no cache hit, results are irrelevant, or the date cannot be parsed, proceed to Step 0.75.

---

## Step 0.75: NotebookLM Prior Knowledge Check

**Only when `--notebook` flag is set AND `HAS_NOTEBOOKLM` is true.**

Before running the full pipeline, check if NotebookLM already has knowledge on this topic:

```bash
notebooklm use {NOTEBOOK_ID} && notebooklm ask "What do you know about {TOPIC}? Summarize key findings with citations." 2>&1
```

- Timeout: 60 seconds. If it times out, skip and proceed.
- Store the response as `NOTEBOOKLM_PRIOR` for use in Step 5 (SYNTHESIZE).
- This supplements (does NOT replace) the memory-layer cache check.
- If NotebookLM returns an error (auth expired, notebook not found), set `HAS_NOTEBOOKLM=false` and note "NotebookLM: unavailable ({error})" for the report.

---

## Step 1: Detect Runtime & Available Tools

Detect which tools are available in the current runtime. This makes the skill portable across Claude Code (full MCP stack) and OpenClaw/Mike (shell + Brave).

### 1a: Probe Available MCP Tools

Try to load these tools (fire all in a single message). Note which succeed and which fail:

1. Firecrawl: Check if `mcp__firecrawl__firecrawl_search` is callable
2. Perplexity: Check if `mcp__perplexity__perplexity_ask` is callable (only if `--perplexity` flag set)
3. Reddit MCP: Check if `mcp__reddit__get_subreddit_hot_posts` is callable
4. Hacker News: Check if `mcp__hacker-news__search_hn` is callable

### 1b: Probe Shell Tools

Test availability of CLI tools via Bash:

```bash
which gemini >/dev/null 2>&1 && echo "GEMINI_OK" || echo "GEMINI_MISSING"
which ollama >/dev/null 2>&1 && echo "OLLAMA_OK" || echo "OLLAMA_MISSING"
which notebooklm >/dev/null 2>&1 && echo "NOTEBOOKLM_OK" || echo "NOTEBOOKLM_MISSING"
```

### 1c: Set Runtime Flags

Based on probes, set these flags for the pipeline:

| Flag | How to Set |
|------|-----------|
| `HAS_FIRECRAWL` | Firecrawl MCP tools loaded successfully |
| `HAS_PERPLEXITY` | Perplexity MCP tools loaded AND `--perplexity` flag set |
| `HAS_REDDIT` | Reddit MCP tools loaded successfully |
| `HAS_HN` | Hacker News MCP tools loaded successfully |
| `HAS_GEMINI` | `which gemini` succeeded AND auth is available. Check with: `([ -n "$GEMINI_API_KEY" ] || [ -f ~/.gemini/.env ]) && echo "GEMINI_OK" || echo "GEMINI_NO_AUTH"`. Either env var OR `~/.gemini/.env` file is sufficient — the CLI auto-loads `~/.gemini/.env`. Note: `settings.json` `apiKey` field is NOT used for auth by the CLI. |
| `HAS_OLLAMA` | `which ollama` succeeded |
| `USE_WEBSEARCH` | Always true in Claude Code (built-in). In OpenClaw, check for `web_search` tool. |
| `USE_WEBFETCH` | Always true in Claude Code (built-in). In OpenClaw, check for `web_fetch` tool. |
| `HAS_NOTEBOOKLM` | `which notebooklm` succeeded. If `--notebook` flag set, verify auth with `notebooklm list` (timeout 30s). |
| `HAS_OBSIDIAN_VAULT` | `--vault` flag set AND `~/research-vault/CLAUDE.md` exists. |

### 1d: Select Research Engine

The primary AI research source is chosen in this priority:

1. If `--perplexity` flag AND `HAS_PERPLEXITY` → use Perplexity MCP
2. If `HAS_GEMINI` → use Gemini CLI (default)
3. Fallback → extra WebSearch queries to compensate

### 1e: Select Scrape Engine

1. If `HAS_FIRECRAWL` → use Firecrawl for search + scrape
2. Fallback → WebSearch for URL discovery + WebFetch for scraping

### 1f: Select Compression Engine

1. If `HAS_OLLAMA` AND NOT `--no-compress` → compress scraped content via Ollama
2. Fallback → pass raw content to Claude (original behavior)

---

## Step 1.5: SHALLOW PATH (--shallow only)

If depth is `--shallow`, skip the full pipeline. Do only:

### 1.5a: AI Research Query

**If using Gemini CLI (default):**

**Pre-check:** Verify Gemini auth is available: `([ -n "$GEMINI_API_KEY" ] || [ -f ~/.gemini/.env ]) && echo "GEMINI_AUTH_OK" || echo "GEMINI_NO_AUTH"`. The CLI auto-loads `~/.gemini/.env` — the `$GEMINI_API_KEY` env var is NOT required if the `.env` file exists. If GEMINI_NO_AUTH, skip Gemini and add 2 extra WebSearch queries as compensation. Log "Gemini: skipped (no auth)" in the report.

```bash
# timeout: 120000 (Gemini can take 60-120s for research queries)
gemini -m gemini-2.5-flash -p "Research this topic with citations and source URLs: {TOPIC}. Key developments, players, best practices. Be concise, use bullet points." 2>&1
```

If `--gemini-pro` flag: replace `gemini-2.5-flash` with `gemini-2.5-pro`.

Log cost:
```
mcp__memory-layer__add_memory:
  collection: "api-cost-log"
  content: "Gemini CLI | model: gemini-2.5-flash | depth: shallow | topic: {TOPIC} | date: {current_date}"
  metadata: {"service": "gemini-cli", "model": "gemini-2.5-flash", "depth": "shallow", "estimated_cost": 0.00, "date": "{current_date}"}
```

**If using Perplexity (--perplexity flag):**
```
mcp__perplexity__perplexity_ask:
  messages: [{"role": "user", "content": "Research this topic with citations: {TOPIC}. Key developments, players, best practices."}]
```

Log cost with `estimated_cost: 0.02` and `service: perplexity`.

### 1.5b: WebSearch (1-2 queries)
- `{TOPIC} 2026`
- One QUERY_TYPE-specific query

### 1.5c: Synthesize and Deliver
Synthesize from just these two sources and deliver. Cache results (Step 6.5). Skip to Step 6 (DELIVER).

This path costs ~$0.00-0.02 depending on research engine.

---

## Step 2: SCATTER — Fire All Sources in Parallel

In a SINGLE message, fire ALL applicable tool calls simultaneously:

### Source 1: last30days Script (Background)
```
Bash (run_in_background: true):
python3 ~/.claude/skills/last30days/scripts/last30days.py "{TOPIC}" --emit=compact 2>&1
```
If the script doesn't exist, this will error — that's fine, skip it.

### Source 2: URL Discovery (Firecrawl or WebSearch)

**If `HAS_FIRECRAWL`:**
```
mcp__firecrawl__firecrawl_search:
  query: "{TOPIC}"
  limit: 10 (--quick: 5, --deep: 15)
  lang: "en"
```

**Else (WebSearch fallback):**
Use WebSearch with 2-3 targeted queries (see Source 4 below) — these results double as both search snippets AND URL sources for scraping.

### Source 3: AI Research (Gemini CLI or Perplexity)

**If using Gemini CLI (default):**

**Pre-check:** Verify Gemini auth: `([ -n "$GEMINI_API_KEY" ] || [ -f ~/.gemini/.env ]) && echo "GEMINI_AUTH_OK" || echo "GEMINI_NO_AUTH"`. The CLI auto-loads `~/.gemini/.env` — the `$GEMINI_API_KEY` env var is NOT required if the `.env` file exists. If GEMINI_NO_AUTH, skip Gemini, add 2 extra WebSearch queries as compensation, and note "Gemini: skipped (no auth)" in the report.

For default/quick depths (fire-and-forget, supplements other sources):
```
Bash (run_in_background: true, timeout: 120000):
gemini -m gemini-2.5-flash -p "Research this topic thoroughly with citations and URLs: {TOPIC}. Focus on the latest developments, key players, best practices, and community sentiment. Include specific facts, dates, version numbers, and names." 2>&1
```

For `--deep` depth (Gemini output is critical — run directly, NOT in background):
```
Bash (timeout: 120000):
gemini -m gemini-2.5-flash -p "Research this topic thoroughly with citations and URLs: {TOPIC}. Focus on the latest developments, key players, best practices, and community sentiment. Include specific facts, dates, version numbers, and names. Be exhaustive. Cover all angles, competitors, alternatives, and edge cases." 2>&1
```

**Background task reliability note:** Background task IDs can be unreliable across tool calls (`TaskOutput` returns "No task found with ID"). For `--deep` where Gemini output is critical, always run directly. Only use `run_in_background: true` for default/quick depths where Gemini output supplements other sources.

For `--gemini-pro`: use `gemini-2.5-pro` model.

**Important:** Gemini CLI can take 60-120 seconds for thorough research queries. For background tasks, collect output via `TaskOutput` with `timeout: 120000` before synthesis. If Gemini output hasn't arrived by synthesis time, proceed without it and note "Gemini: pending" in the report.

**Quota handling:** Gemini free tier has a daily limit (20 requests/day for Flash, fewer for Pro). The CLI may produce partial output before hitting the quota (HTTP 429). If the output contains research content followed by a quota error:
- **Use the partial output** — it often contains the core research before web search augmentation failed
- Note "Gemini: partial (quota exhausted)" in the report
- Add 1-2 extra WebSearch queries to compensate for the missing web search augmentation
- Do NOT treat partial output as a full failure — extract what's there

Log cost after completion:
```
mcp__memory-layer__add_memory:
  collection: "api-cost-log"
  content: "Gemini CLI | model: {model} | depth: {DEPTH} | topic: {TOPIC} | date: {current_date}"
  metadata: {"service": "gemini-cli", "model": "{model}", "depth": "{DEPTH}", "estimated_cost": 0.00, "date": "{current_date}"}
```

**If using Perplexity (`--perplexity` flag):**

For `--deep` depth — use `perplexity_research` (sonar-deep-research, ~$5-10/call):
```
mcp__perplexity__perplexity_research:
  messages: [{"role": "user", "content": "Research this topic thoroughly with citations: {TOPIC}. Focus on the latest developments, key players, best practices, and community sentiment. Include specific facts, dates, version numbers, and names."}]
```

For all other depths — use `perplexity_ask` (sonar-pro, ~$0.02/call):
```
mcp__perplexity__perplexity_ask:
  messages: [{"role": "user", "content": "Research this topic thoroughly with citations: {TOPIC}. Focus on the latest developments, key players, best practices, and community sentiment. Include specific facts, dates, version numbers, and names."}]
```

Log cost with appropriate `estimated_cost` and `service: perplexity`.

> **Cost guard:** `perplexity_research` uses `sonar-deep-research` which generates millions of reasoning tokens. Only use it for `--deep --perplexity`. Gemini CLI is free and the default for all depths.

### Source 4: WebSearch (2-3 queries based on QUERY_TYPE)

**If RECOMMENDATIONS:**
- `best {TOPIC} recommendations 2026`
- `{TOPIC} comparison review`

**If NEWS:**
- `{TOPIC} news 2026`
- `{TOPIC} announcement update latest`

**If HOW-TO:**
- `{TOPIC} tutorial guide 2026`
- `{TOPIC} best practices examples`

**If GENERAL:**
- `{TOPIC} 2026`
- `{TOPIC} community discussion`

For `--deep`, add a third query:
- `{TOPIC} expert analysis`

### Source 5: Reddit MCP (if `HAS_REDDIT`)

Identify 1-3 relevant subreddits for the TOPIC, then fire in parallel:
```
mcp__reddit__get_subreddit_hot_posts:
  subreddit_name: "{relevant_subreddit}"
  limit: 10 (--quick: 5, --deep: 15)
```

Subreddit selection heuristic:
- Tech/AI topics → "artificial", "MachineLearning", "LocalLLaMA", "ClaudeAI"
- Web dev → "webdev", "javascript", "reactjs", "nextjs"
- General tech → "technology", "programming"
- Business/SaaS → "SaaS", "startups", "Entrepreneur"
- Specific tools → subreddit named after the tool if it exists

For high-scoring posts (score > 50), also fetch comments:
```
mcp__reddit__get_post_comments:
  post_id: "{post_id}"
  limit: 5
```

### Source 6: Hacker News MCP (if `HAS_HN`)

Search HN for relevant stories:
```
mcp__hacker-news__search_hn:
  query: "{TOPIC}"
  limit: 10
```

For high-scoring results, fetch details with comments.

### Source 7: Twitter MCP (if configured)

Only if Twitter MCP tools loaded successfully:
```
mcp__twitter__search_tweets:
  query: "{TOPIC}"
  count: 20 (--quick: 10, --deep: 50)
```

If Twitter returns auth errors, skip silently.

### Source 8: NotebookLM Grounded RAG (if `HAS_NOTEBOOKLM` AND `--notebook`)

Query NotebookLM for grounded, citation-backed answers from the user's curated corpus:

```bash
notebooklm use {NOTEBOOK_ID} && notebooklm ask "What are the key findings, themes, and evidence about {TOPIC}? Include specific citations." 2>&1
```

For `--deep`, add 2 follow-up queries:
```bash
notebooklm ask "What contradictions, gaps, or disagreements exist across sources about {TOPIC}?" 2>&1
notebooklm ask "What specific data points, statistics, or quantitative evidence about {TOPIC}?" 2>&1
```

- Timeout: 60 seconds per query. Skip silently on error.
- Preserve all citations — they become `[[wikilinks]]` in vault notes.
- If `NOTEBOOKLM_PRIOR` was already collected in Step 0.75, do NOT re-ask the primary question — only run the `--deep` follow-ups.

### Fallback Rules
- If ANY source returns an error, note which source failed and continue with the others
- Do NOT retry failed sources — move forward with what you have
- Track which sources succeeded for the final report

---

## Step 3: DEEP DIVE — Scrape Top Results

After ALL Step 2 results return:

### 3a: Identify Top URLs
From search results (Firecrawl or WebSearch), pick the top 3-5 URLs to scrape.

**Priority order:**
1. Official documentation / changelogs
2. Detailed blog posts / tutorials
3. GitHub repos / READMEs
4. News articles
5. Forum threads (if no better sources)

For `--quick`: scrape top 2-3 only.
For `--deep`: scrape top 5-7.

### 3b: Scrape Pages

**If `HAS_FIRECRAWL`:**
Fire all scrape calls in parallel:
```
mcp__firecrawl__firecrawl_scrape:
  url: "{URL}"
  formats: ["markdown"]
  onlyMainContent: true
```

**Else (WebFetch fallback):**
```
WebFetch:
  url: "{URL}"
  prompt: "Extract the main content about {TOPIC}. Focus on key facts, dates, features, and insights."
```

**Note:** Firecrawl MCP params must be proper JSON types. `formats` must be an actual array `["markdown"]`, not a string.

If any scrape fails, fall back to WebFetch for that URL.

### 3c: Collect Script Output
Use `TaskOutput` to collect the last30days background script results (if it was running).

### 3d: Collect Gemini CLI Output
Use `TaskOutput` to collect the Gemini CLI background results (if it was running in background).

### 3e: Compensate for Missing Sources
- If Gemini CLI fully failed AND Perplexity unavailable: add 2-3 extra WebSearch queries
- If Gemini CLI returned partial output (quota 429 mid-request): use partial output + add 1-2 extra WebSearch queries
- If Firecrawl search failed: use WebSearch results as the URL source for scraping
- If last30days failed: Reddit MCP is the primary fallback (already queried in Step 2)
- If Reddit MCP failed: last30days script is the fallback
- If both Reddit sources failed: note "Reddit data unavailable" in report

---

## Step 4: COMPRESS — Local Content Reduction via Ollama

**Skip this step if `--no-compress` flag is set OR `HAS_OLLAMA` is false.**

This step reduces scraped content from ~5,000-20,000 tokens per page down to ~500-1,000 tokens per page, saving 60-80% of Claude input tokens on synthesis.

### 4a: Compress Each Scraped Page

For each scraped page, fire a parallel Bash call:

**Do NOT use heredocs** to pipe content — apostrophes and quotes in scraped text will break them. Instead, write each page's content to a temp file first, then pipe:

```bash
# Step 1: Write content to temp file (use the Write tool, NOT echo/heredoc)
# Write scraped content to /tmp/research-compress-{N}.txt

# Step 2: Pipe temp file to Ollama with ANSI stripping
cat /tmp/research-compress-{N}.txt | ollama run qwen3:8b "/no_think Extract ONLY the key facts, data points, specific names, version numbers, dates, quotes, and actionable insights about {TOPIC} from this content. Output concise bullet points. No preamble." 2>&1 | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | sed 's/[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]//g' | sed '/^Thinking/,/done thinking/d' | grep -v '^$'
```

**Important notes:**
- **Write temp files first** using the Write tool — never use heredocs or echo for scraped content (quotes/apostrophes break shell escaping)
- The `/no_think` prefix tells qwen3 to skip reasoning (may still output thinking text)
- The first `sed` strips ALL ANSI escape codes including CSI sequences with `?` (e.g., `[?25l`, `[?2026h`)
- The second `sed` strips Ollama's Unicode spinner characters (braille dots: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏)
- The third `sed` strips any `Thinking...` / `...done thinking.` blocks
- Set a **60-second timeout** per compression call. If Ollama hangs, use raw content for that page.
- Fire ALL compression calls in parallel — they're independent
- Clean up temp files after synthesis: `rm -f /tmp/research-compress-*.txt`

### 4b: Handle Compression Failures

If Ollama returns an error or times out for any page:
- Use the raw scraped content for that page (original behavior)
- Note "compression skipped" for that source in the report
- Do NOT retry — proceed with what you have

### 4c: Assemble Compressed Context

After all compression calls complete, you now have:
- Gemini CLI research output (already concise)
- Compressed scrape summaries from Ollama (~500-1000 tokens each)
- WebSearch snippets (already small)
- Reddit/HN/Twitter data (already structured)

This compressed context is what Claude will synthesize in Step 5.

---

## Step 5: SYNTHESIZE — Cross-Reference All Sources

Weight sources by reliability:

| Source | Weight | Why |
|--------|--------|-----|
| NotebookLM (grounded RAG) | Highest | Zero-hallucination, citation-backed answers from curated corpus |
| Reddit MCP (direct) | Highest | Real-time posts with scores, comments, engagement |
| Reddit/X (via last30days) | Highest | Engagement signals (upvotes, likes, comments) |
| Hacker News MCP | High | Tech community sentiment, high signal-to-noise |
| Twitter MCP | High | Real-time pulse, influencer takes |
| Gemini CLI / Perplexity | High | Grounded search with citations, recent data |
| Scraped content (compressed) | Medium | Key facts extracted from authoritative sources |
| WebSearch snippets | Lower | Snippet-only, no engagement data |

### Synthesis Rules
1. **Patterns**: Identify themes appearing in 2+ sources — these are the strongest signals
2. **Contradictions**: Note where sources disagree — flag for the user
3. **Specifics**: Extract exact names, versions, dates, numbers — not vague claims
4. **Ground in research**: Use what the sources ACTUALLY say, not your pre-existing knowledge. If the research says X, report X — even if you "know" differently
5. **Actionable insights**: Every finding should help the user DO something or DECIDE something
6. **Engagement signals**: When Reddit/HN/Twitter data is available, note upvote counts, comment counts, and sentiment as confidence indicators

---

## Step 6: DELIVER — Present Findings

### Output Format

```
## Research: {TOPIC}

### Key Findings
- [Insight 1 — grounded in specific source evidence]
- [Insight 2 — with specific names/versions/dates]
- [Insight 3 — actionable recommendation]
- [Insight 4 — if applicable]
- [Insight 5 — if applicable]

### Patterns Across Sources
- [Theme that appeared in 2+ sources, with which sources]
- [Another recurring theme]

### Notable Details
- [Specific fact, version, date from scrapes]
- [Specific quote or data point]
- [Anything surprising or contradictory]
```

### Source Stats Dashboard

After the findings, show the availability report:

```
---
Research Stack Report (Hybrid Pipeline)
├─ 🤖 Research Engine: Gemini Flash (free) | Gemini Pro (free) | Perplexity sonar-pro ($0.02) | Perplexity deep ($X.XX)
├─ 🗜️ Compression: Ollama qwen3:8b ([n] pages compressed, ~[X]% token reduction) | "skipped (--no-compress)" | "unavailable"
├─ 🟠 Reddit MCP: [n] posts | [sum] score | top: r/{sub1}, r/{sub2} OR "unavailable"
├─ 🟠 Reddit/X (last30days): [n] items | [engagement] OR "unavailable"
├─ 🟡 Hacker News: [n] stories | [sum] points OR "unavailable"
├─ 🔵 Twitter: [n] tweets | [engagement] OR "unavailable"
├─ 🔥 Firecrawl: [n] searched | [n] scraped OR "unavailable (using WebFetch)"
├─ 🌐 WebSearch: [n] results from [top domains]
├─ 📓 NotebookLM: [n] queries | notebook: "<name>" | [n] citations OR "not used"
├─ 🗃️ Vault: written to ~/research-vault/research/<slug>.md OR "not used"
├─ 💰 Est. cost: $[X.XX] (research: $[X.XX] + scraping: $[X.XX])
└─ Sources: [list of domains scraped]

Ask me anything about {TOPIC} — I'm now an expert.
```

Use real numbers from the actual results. If a source was unavailable, say so honestly.

---

## Step 6.5: Cache Results to Memory

After delivering findings, store a compact summary for future cache hits:

```
mcp__memory-layer__add_memory:
  collection: "research-cache"
  content: "Research: {TOPIC}\nDate: {current_date}\nDepth: {DEPTH}\nEngine: {gemini-cli|perplexity}\nCompressed: {yes|no}\nKey findings: {3-5 bullet points}\nSources used: {list}\nTop URLs: {scraped URLs}"
```

This enables the Step 0.5 cache check in future sessions.

---

## Step 6.75: Write to Obsidian Research Vault

**Gated on `--vault` AND `HAS_OBSIDIAN_VAULT`.** Skip entirely if neither condition is met.

### 6.75a: Create Research Note

Write to `~/research-vault/research/Research - {TOPIC_SLUG}.md` where `{TOPIC_SLUG}` is the topic in title case.

Use Obsidian CLI if available (`obsidian create vault="research-vault" ...`), otherwise write directly via filesystem.

```markdown
---
title: "Research - {TOPIC}"
date: {YYYY-MM-DD}
status: draft
type: research-note
tags: [research, {domain-tags}]
notebook: "{NOTEBOOK_NAME or empty}"
sources_count: {N}
depth: {DEPTH}
pipeline: research-stack
---

# {TOPIC} — Research Findings

## Executive Summary
{2-3 sentence synthesis from Step 5}

## Key Findings
### Finding 1: {Theme}
{Content synthesized from research}
- Source: [[Source - {Title}]] — {citation}

### Finding 2: {Theme}
{Content}
- Source: [[Source - {Title}]]

## Patterns Across Sources
{Themes from 2+ sources with attribution}

## Notable Details
{Specific facts, data points, contradictions}

## Sources
| Source | Type | Key Contribution |
|--------|------|-----------------|
| [[Source - {Title 1}]] | {type} | {contribution} |
| [[Source - {Title 2}]] | {type} | {contribution} |
```

### 6.75b: Create Source Notes

For each scraped URL (top 3 for default depth, all for `--deep`), write to `~/research-vault/sources/Source - {TITLE_SLUG}.md`:

```markdown
---
title: "Source - {Title}"
date: {YYYY-MM-DD}
type: source
source_type: {article|youtube|pdf|doc|website}
url: "{original URL}"
tags: [source, {domain-tags}]
cited_in: ["Research - {TOPIC}"]
---

# {Source Title}

## Key Takeaways
- {Point 1}
- {Point 2}
- {Point 3}

## Citations Used In
- [[Research - {TOPIC}]]
```

### 6.75c: Update MOC

Search `~/research-vault/moc/` for a MOC matching the research domain. If found, append a link to the new research note. Do NOT auto-create new MOCs — only update existing ones.

### 6.75d: Ingest Sources into NotebookLM

**Only if `HAS_NOTEBOOKLM` AND `--notebook` flag is set.**

Add scraped URLs as sources to the notebook for future grounded queries:

```bash
notebooklm use {NOTEBOOK_ID} && notebooklm source add "{URL}" 2>&1
```

- Up to 5 URLs for default depth, 10 for `--deep`.
- Skip URLs that fail to add (don't retry).
- This builds the notebook's corpus for future research sessions.

### 6.75e: Content Generation

**Only if `--content` flag is set AND `HAS_NOTEBOOKLM` AND `--notebook`.**

Generate the requested content type from the notebook:

```bash
notebooklm generate {CONTENT_TYPE} "Create an overview of {TOPIC}" --wait 2>&1
notebooklm download {CONTENT_TYPE} ~/research-vault/assets/{CONTENT_TYPE}/{TOPIC_SLUG}.{ext} 2>&1
```

Content type mapping: `audio` → `.mp3`, `slides` → `.pdf`, `mind-map` → `.json`, `infographic` → `.png`.

After download, add an asset link to the research note.

### 6.75f: Dashboard

Dataview in `_Dashboard.md` auto-updates from frontmatter queries. No action needed unless `_Dashboard.md` doesn't exist yet — in that case, create it (see vault setup).

---

## Step 7: Expert Mode — Handle Follow-ups

After delivering results, you are now an expert on {TOPIC} for the rest of this conversation.

**Rules:**
- Answer follow-up questions from the research you gathered — do NOT run new searches
- If asked to write a prompt, summary, or analysis — use your gathered data
- If asked to compare or evaluate — reference specific findings from your research
- Only run NEW research if the user asks about a CLEARLY DIFFERENT topic
- If asked "what sources did you use?" — list the specific URLs you scraped

---

## Graceful Degradation

This pipeline works even when sources are unavailable. The hybrid design means it runs on both Claude Code (full MCP stack) and OpenClaw/Mike (shell + Brave only).

| Source | If It Fails | Fallback |
|--------|-------------|----------|
| Gemini CLI (full failure) | Auth missing / timeout / CLI not installed | Extra WebSearch queries (2-3 additional) |
| Gemini CLI (quota 429) | Daily quota exhausted mid-request (partial output) | Use partial output + 1-2 extra WebSearch queries |
| Perplexity API | 401 / timeout / not configured | Gemini CLI (default engine) |
| Firecrawl search | API error / not configured | WebSearch as URL discovery source |
| Firecrawl scrape | Error on URL / not configured | WebFetch for that URL |
| Ollama compression | Not installed / timeout / error | Pass raw content to Claude (original behavior) |
| Reddit MCP | Server not loaded / error | last30days script for Reddit data |
| last30days script | Missing / script error | Reddit MCP for Reddit data |
| Hacker News MCP | Server not loaded / error | Skip, note in report |
| Twitter MCP | Auth error / not configured | Skip, note in report |
| NotebookLM CLI | Not installed / auth expired / timeout | Skip as source, note "NotebookLM: unavailable" in report |
| Obsidian CLI | Not running / not installed | Write vault notes via filesystem (direct file write) |
| Research vault | `~/research-vault/` doesn't exist | Skip vault output, warn user: "Use --vault after running vault setup" |
| WebSearch | Error | Firecrawl search results only |

### Minimum Viable Pipelines

**Claude Code minimum**: WebSearch + Firecrawl + Gemini CLI
**OpenClaw/Mike minimum**: WebSearch (Brave) + WebFetch + Gemini CLI

**Complete failure**: If ALL sources fail, report what happened and suggest checking MCP server configurations and CLI tool installations.

---

## Runtime Compatibility

| Feature | Claude Code | OpenClaw / Mike |
|---------|------------|-----------------|
| Gemini CLI | Yes (shell) | Yes (shell) |
| Ollama compression | Yes (shell) | Yes (shell) |
| Firecrawl MCP | Yes | No → WebFetch fallback |
| Perplexity MCP | Yes (opt-in) | No → Gemini default |
| Reddit MCP | Yes | No → last30days fallback |
| HN MCP | Yes | No → skip |
| WebSearch | Built-in | Brave Search tool |
| WebFetch | Built-in | web_fetch tool |
| Memory cache | memory-layer MCP | memory-layer MCP (if loaded) |
| NotebookLM CLI | Yes (shell, opt-in `--notebook`) | Yes (shell, opt-in `--notebook`) |
| Obsidian vault | Yes (opt-in `--vault`) | No (filesystem write only, no Obsidian CLI) |

The skill auto-detects the runtime in Step 1 and routes accordingly. No manual configuration needed.

---

## Depth Tier Summary

| Tier | Sources | Research Engine | Scrapes | Compression | Vault | NotebookLM | Est. Cost | Use When |
|------|---------|----------------|---------|-------------|-------|------------|-----------|----------|
| `--shallow` | Gemini + WebSearch | Gemini Flash | 0 | No | if `--vault` | 1 query if `--notebook` | ~$0.00 | Quick fact check, simple question |
| `--quick` | All available | Gemini Flash | 2-3 | Yes (if avail) | if `--vault` | 1 query if `--notebook` | ~$0.02 | Time-sensitive, good enough answer |
| default | All available | Gemini Flash | 3-5 | Yes (if avail) | if `--vault` (3 sources) | 1 query if `--notebook` | ~$0.05 | Standard research task |
| `--deep` | All + extra queries | Gemini Flash | 5-7 | Yes (if avail) | if `--vault` (all sources) | 3 queries if `--notebook` | ~$0.10 | Comprehensive analysis |
| `--deep --perplexity` | All + extra queries | sonar-deep-research | 5-7 | Yes (if avail) | if `--vault` (all sources) | 3 queries if `--notebook` | ~$5-10 | Exhaustive, citation-heavy research |

> **Cost comparison:** Default research now costs ~$0.05 (was ~$0.25). The combination of Gemini free tier + Ollama local compression reduces costs by ~80%. The `--perplexity` flag is available for when you need Perplexity's specific capabilities, but Gemini is the default.
