Deep multi-source research using a hybrid pipeline: Gemini CLI (free) + Ollama compression + optional Firecrawl/Perplexity. Portable across Claude Code and OpenClaw.

## Usage
- `/research-stack [topic]` (balanced — Gemini + all sources, 3-5 scrapes, Ollama compression)
- `/research-stack [topic] --shallow` (fast — Gemini + WebSearch only, no scraping)
- `/research-stack [topic] --quick` (fewer sources, 2-3 scrapes)
- `/research-stack [topic] --deep` (comprehensive — all sources, 5-7 scrapes, extra queries)

## Flags
- `--perplexity` — use Perplexity MCP instead of Gemini CLI (costs $0.02-10/call)
- `--no-compress` — skip Ollama compression, send raw scraped content to Claude
- `--gemini-pro` — use Gemini 2.5 Pro instead of Flash (higher quality, lower rate limits)
- `--vault` — write structured output to Obsidian research vault + auto-route to best NotebookLM notebook via keyword matching
- `--notebook <name>` — explicitly specify NotebookLM notebook (overrides auto-routing)
- `--content <type>` — generate content via NotebookLM: audio, slides, mind-map, infographic (requires `--notebook`)

## Examples
- `/research-stack Firecrawl MCP latest features 2026`
- `/research-stack AI code editors market landscape`
- `/research-stack Claude Code skills best practices --deep`
- `/research-stack professional services automation trends --perplexity --deep`
- `/research-stack MCP protocol overview --vault` (auto-routes to "AI Agents & Orchestration" notebook + writes vault)
- `/research-stack AI agents 2026 --vault --notebook "AI Agents & Orchestration"` (explicit notebook + writes vault)
- `/research-stack contract AI --vault --content audio` (auto-routes notebook + audio generation)
- `/research-stack pricing strategy for agencies --vault` (auto-routes to "Business Strategy" notebook)

## Cost Comparison
| Depth | Old Cost | New Cost | Savings |
|-------|----------|----------|---------|
| --shallow | ~$0.05 | ~$0.00 | 100% |
| default | ~$0.25 | ~$0.05 | 80% |
| --deep | ~$5-10 | ~$0.10 | 98% |
| --deep --perplexity | N/A | ~$5-10 | (same as old --deep) |

## Execution

Follow the full research pipeline instructions in `~/.claude/skills/research-stack/SKILL.md`.

The topic to research is:

$ARGUMENTS
