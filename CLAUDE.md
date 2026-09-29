# Research Stack

> Status: active | Type: infra (public Claude Code skill)

Multi-source research pipeline: fires 8 parallel sources (Gemini CLI, Firecrawl, Perplexity,
Reddit, Hacker News, Twitter, NotebookLM, WebSearch), compresses locally via Ollama, synthesizes
with full source attribution. Public repo: `github.com/7alexhale5-rgb/research-stack`.

## Where to go

This repo follows ICM (Jake Van Clief's folder method): this file routes, each room's
`CONTEXT.md` holds its contract.

| Task                                                 | Go to         | Read                                           | Skills |
| ---------------------------------------------------- | ------------- | ---------------------------------------------- | ------ |
| Change the skill's invocation or its command surface | `commands/`   | none                                           | none   |
| Change a default or example config                   | `config/`     | [config/CONTEXT.md](config/CONTEXT.md)         | none   |
| Update architecture or tools-reference docs          | `docs/`       | [docs/CONTEXT.md](docs/CONTEXT.md)             | none   |
| Update setup or routing reference material           | `references/` | [references/CONTEXT.md](references/CONTEXT.md) | none   |

Root files stay where their tools expect them: `SKILL.md` (skill manifest), `install.sh`,
`README.md`, `LICENSE`.

## Naming

Kebab-case `.md` throughout.
