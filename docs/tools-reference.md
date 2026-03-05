# Tools Reference

Every tool in the Research Stack pipeline, how to install it, and what happens without it.

---

## 1. Gemini CLI

**Role in pipeline:** Default AI research engine. Generates a comprehensive research summary with citations and source URLs for any topic. Used in the SCATTER step as the primary AI source (unless `--perplexity` overrides it).

**Install:**

```bash
npm install -g @google/gemini-cli
gemini  # First run: interactive auth flow
```

Or set up `~/.gemini/.env` manually:

```
GEMINI_API_KEY=your_key_here
```

The CLI auto-loads `~/.gemini/.env`. No environment variable export needed.

**Cost:** Free. Flash model allows ~20 requests/day. Pro model has lower limits.

**Verify:**

```bash
gemini -m gemini-2.5-flash -p "What is Claude Code?"
```

Should return a research-style answer within 60-120 seconds.

**If missing:** The skill adds 2-3 extra WebSearch queries to compensate. Research quality decreases since WebSearch returns snippets, not synthesized analysis. Noted as "Gemini: unavailable" in the source stats.

**Configuration:**
- Default model: `gemini-2.5-flash` (free, fast)
- `--gemini-pro` flag switches to `gemini-2.5-pro` (higher quality, lower rate limits)
- Auth: either `~/.gemini/.env` file or `$GEMINI_API_KEY` environment variable
- The `settings.json` `apiKey` field is NOT used by the CLI for auth

**Gotchas:**
- Quota exhaustion (HTTP 429) can happen mid-request, producing partial output. The skill uses whatever content was generated before the error.
- Responses take 60-120 seconds for thorough research queries. The skill sets appropriate timeouts.
- Free tier resets daily.

---

## 2. Ollama + qwen3:8b

**Role in pipeline:** Local compression engine. Each scraped page (5,000-20,000 tokens) is piped through Ollama to extract key facts into concise bullet points (500-1,000 tokens). Saves 60-80% of Claude's input token budget during synthesis.

**Install:**

```bash
brew install ollama
ollama serve        # Start the background server
ollama pull qwen3:8b  # Download the model (~5GB)
```

On Linux:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen3:8b
```

**Cost:** Free. Runs entirely on your local machine.

**Verify:**

```bash
echo "The quick brown fox jumps over the lazy dog." | ollama run qwen3:8b "Summarize this in one word."
```

Should return a single word within a few seconds.

**If missing:** Compression step is skipped entirely. Raw scraped content goes directly to Claude for synthesis. Works fine but uses more input tokens (and therefore more of Claude's context window). The skill notes "Compression: unavailable" in the source stats.

**Configuration:**
- Model: `qwen3:8b` is the default. Any Ollama model works, but qwen3:8b balances speed and extraction quality.
- The `/no_think` prefix is prepended to prompts to skip the model's reasoning phase.
- ANSI escape codes and spinner characters are stripped from output automatically.
- 60-second timeout per page. Falls back to raw content on timeout.

**Gotchas:**
- First run downloads the model, which can take several minutes depending on connection speed.
- `ollama serve` must be running. If you get connection errors, start it first.
- Ollama can occasionally hang on malformed input. The 60-second timeout handles this.

---

## 3. Firecrawl MCP

**Role in pipeline:** Combined search and scrape engine. In the SCATTER step, runs a search query to discover URLs. In the DEEP DIVE step, scrapes individual pages for full markdown content.

**Install:**

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "your_key_here"
      }
    }
  }
}
```

Get a free API key at [firecrawl.dev](https://firecrawl.dev).

Restart Claude Code after adding the config.

**Cost:** Free tier available (limited requests). Paid plans for higher volume.

**Verify:** After restarting Claude Code, the skill's runtime detection will probe for `mcp__firecrawl__firecrawl_search`. You can also test manually in a Claude Code conversation by asking it to search for something.

**If missing:** WebSearch handles URL discovery. WebFetch handles scraping. The fallback works well but Firecrawl returns cleaner markdown and more consistent results.

**Configuration:**
- `formats` must be a JSON array: `["markdown"]`, not a string `"markdown"`
- `onlyMainContent: true` strips navigation, headers, footers
- `limit`: 5 (quick), 10 (default), 15 (deep)

**Gotchas:**
- The `formats` parameter type is the most common configuration error. It must be an array.
- Free tier rate limits are generous for research use (a few hundred requests/month).

---

## 4. Perplexity MCP

**Role in pipeline:** Optional AI research engine, activated with the `--perplexity` flag. Uses Perplexity's sonar models for citation-heavy research. For `--deep --perplexity`, uses sonar-deep-research which generates exhaustive, multi-source analysis.

**Install:**

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@anthropic/perplexity-mcp"],
      "env": {
        "PERPLEXITY_API_KEY": "your_key_here"
      }
    }
  }
}
```

Restart Claude Code after adding the config.

**Cost:**
- `sonar-pro` (default/quick/standard): ~$0.02 per query
- `sonar-deep-research` (`--deep --perplexity`): ~$5-10 per query (generates millions of reasoning tokens)

**Verify:** After restarting Claude Code, the skill probes for `mcp__perplexity__perplexity_ask` during runtime detection.

**If missing:** Gemini CLI is the default engine. Perplexity is only used when explicitly requested with `--perplexity`. No degradation occurs if Perplexity is not configured and the flag is not set.

**Configuration:**
- Only activated with `--perplexity` flag — never used by default
- `--deep --perplexity` triggers a cost confirmation gate before proceeding
- Two MCP tools: `perplexity_ask` (sonar-pro) and `perplexity_research` (sonar-deep-research)

**Gotchas:**
- sonar-deep-research is expensive. The skill enforces a confirmation gate for `--deep --perplexity`.
- Without `--perplexity`, the Perplexity MCP is never called even if configured.

---

## 5. Hacker News MCP

**Role in pipeline:** Tech community sentiment and discussion. Searches HN for stories related to the topic, returns titles, points, and comment counts. High-scoring stories indicate strong community interest.

**Install:**

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "hacker-news": {
      "command": "npx",
      "args": ["-y", "@anthropic/hacker-news-mcp"]
    }
  }
}
```

No API key needed. Restart Claude Code after adding the config.

**Cost:** Free.

**Verify:** After restarting Claude Code, the skill probes for `mcp__hacker-news__search_hn` during runtime detection.

**If missing:** HN data is skipped. Noted as "Hacker News: unavailable" in the source stats. For tech topics, this means less community sentiment data, but Reddit MCP and other sources partially compensate.

**Configuration:**
- `limit`: 10 results by default
- High-scoring results (many points) get additional detail fetching

---

## 6. NotebookLM CLI

**Role in pipeline:** Grounded RAG from curated notebooks. When `--notebook` is specified, the skill queries NotebookLM for citation-backed answers from your own uploaded sources. This provides zero-hallucination responses grounded in your corpus. Also used to ingest new URLs as sources after research completes.

**Install:**

```bash
pipx install notebooklm-py --python python3.12
notebooklm login
```

Requires Python 3.10 or higher. The `--python python3.12` flag ensures compatibility.

**Cost:** Free (uses your Google account's NotebookLM quota).

**Verify:**

```bash
notebooklm list
```

Should display your notebooks with IDs.

**If missing:** NotebookLM steps are skipped entirely. The pipeline runs without grounded RAG. Noted as "NotebookLM: unavailable" in the source stats.

**Configuration:**
- Activated with `--notebook <name>` or auto-routed via `--vault` (keyword matching against a routing table)
- `--content <type>` generates audio, slides, mind-maps, or infographics from notebooks
- Notebook IDs are used internally (names can contain special characters that break shell parsing)
- 60-second timeout per query

**Gotchas:**
- `notebooklm use "Name With & Symbol"` fails. Always use notebook IDs: `notebooklm use abc123`.
- Auth tokens expire. If queries fail, run `notebooklm login` again.
- The CLI is community-maintained (v0.3.x). Occasional breaking changes between versions.

---

## 7. Obsidian Vault

**Role in pipeline:** Persistent research storage. When `--vault` is set, the skill writes structured markdown notes to a vault directory: one research note per topic and one source note per scraped URL, all with YAML frontmatter, `[[wikilinks]]`, and cross-references. Obsidian's graph view shows how research topics connect over time.

**Install:**

Download Obsidian from [obsidian.md](https://obsidian.md) and open your research vault as a vault.

The skill writes plain markdown files. Obsidian is the recommended viewer but not required.

**Cost:** Free (Obsidian is free for personal use).

**Verify:** Check that your vault directory exists and contains a `CLAUDE.md` file:

```bash
ls ~/Projects/research-vault/CLAUDE.md
```

**If missing:** Vault write steps are skipped. Research is still delivered in the conversation and cached to memory-layer. The skill warns: "Use --vault after setting up a vault directory."

**Configuration:**
- Vault path: configurable (default: `~/Projects/research-vault/`)
- Directory structure: `research/` for research notes, `sources/` for source notes, `moc/` for maps of content, `assets/` for generated content
- Frontmatter fields: `title`, `date`, `status`, `type`, `tags`, `notebook`, `sources_count`, `depth`, `pipeline`
- Dataview-compatible: a `_Dashboard.md` with Dataview queries auto-displays recent research

**Gotchas:**
- The vault directory must exist before using `--vault`. The skill does not create it.
- Obsidian must have the vault directory registered as a vault for graph view to work.

---

## 8. WebSearch + WebFetch

**Role in pipeline:** Built-in fallback for everything. WebSearch runs targeted queries (2-3 per run, tailored by query type). WebFetch scrapes individual URLs when Firecrawl is unavailable. These are always available in Claude Code with zero configuration.

**Install:** Nothing. Built into Claude Code.

**Cost:** Included in Claude Code usage.

**Verify:** These are always available. No verification needed.

**If missing:** These tools are built into Claude Code and cannot be missing. If WebSearch returns an error, Firecrawl search results are used as the sole URL source.

**Configuration:**
- WebSearch queries are generated based on query type (recommendations, news, how-to, general)
- `--deep` adds an extra query
- WebFetch uses a prompt parameter to focus extraction on the research topic

**Notes:**
- WebSearch returns snippets, not full page content. For full content, the skill scrapes URLs via Firecrawl or WebFetch.
- WebFetch can handle most public URLs but may fail on JavaScript-heavy sites. Firecrawl handles these better.

---

## Tool Detection Summary

The skill detects all tools automatically at the start of each run. No manual configuration is needed beyond installing the tools you want.

| Tool | Detection Method | Runtime Flag |
|------|-----------------|-------------|
| Gemini CLI | `which gemini` + auth check | `HAS_GEMINI` |
| Ollama | `which ollama` | `HAS_OLLAMA` |
| Firecrawl MCP | MCP tool probe | `HAS_FIRECRAWL` |
| Perplexity MCP | MCP tool probe + `--perplexity` flag | `HAS_PERPLEXITY` |
| Reddit MCP | MCP tool probe | `HAS_REDDIT` |
| Hacker News MCP | MCP tool probe | `HAS_HN` |
| Twitter MCP | MCP tool probe | `HAS_TWITTER` |
| NotebookLM CLI | `which notebooklm` + `notebooklm list` | `HAS_NOTEBOOKLM` |
| Obsidian vault | `--vault` flag + directory check | `HAS_OBSIDIAN_VAULT` |
| WebSearch | Always available in Claude Code | `USE_WEBSEARCH` |
| WebFetch | Always available in Claude Code | `USE_WEBFETCH` |

Tools are checked once per run. If a tool fails during the run (timeout, auth error, rate limit), the skill falls back gracefully and notes it in the source stats dashboard.
