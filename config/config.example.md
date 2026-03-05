# Research Stack Configuration

Copy this file to `config/config.md` and customize for your setup.
This file is gitignored — your personal config stays local.

## Vault Path (optional)

Set this if you use `--vault` flag. Default: `~/research-vault/`

```
VAULT_PATH=~/research-vault/
```

## NotebookLM Notebook IDs (optional)

Run `notebooklm list` to get your notebook IDs.
Update `references/notebook-routing.md` with your actual IDs.

Example output from `notebooklm list`:
```
abc12345  AI Agents & Orchestration
def67890  AI Automation & LLMs
...
```

## Preferred Research Engine

Default: Gemini CLI (free). Override per-run with `--perplexity`.

## Preferred Compression Model

Default: `qwen3:8b` via Ollama. Change in SKILL.md Step 4a if you prefer a different model.
Alternatives: `llama3.2:3b` (faster, less accurate), `qwen3:14b` (slower, more accurate).
