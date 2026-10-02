# Research Stack configuration

Copy this file to `config/config.md` in the installed skill folder
(`~/.claude/skills/research-stack/config/config.md`) and edit the values. `config/config.md` is
gitignored. SKILL.md Step 0 reads it if it exists; command-line flags override it. Every key
below is read by the skill. Delete a line to use its default.

```text
# Where the always-on cache file is written (Step 10).
# Default: .devproto/research/ in a development-protocol project, else
# ~/Projects/research-vault/research/ if it exists, else ./research/
CACHE_DIR=~/Projects/research-vault/research/

# Vault root for --vault notes, MOC links and NotebookLM content (references/power-tier.md).
VAULT_PATH=~/Projects/research-vault/

# Focus tags applied when the prompt names none. Empty = general run with suggestions.
# Example: DEFAULT_FOCUS=devtools,security
DEFAULT_FOCUS=

# Per-run spend caps in USD, paid lens tools included (Step 2).
BUDGET_SHALLOW=0.05
BUDGET_DEFAULT=0.50
BUDGET_DEEP=15

# Registry ids to never call, comma-separated (see references/tool-registry.json).
# Example: DISABLED_TOOLS=ahrefs,crunchbase
DISABLED_TOOLS=

# Power tier: Gemini CLI model and Groq compression models (references/power-tier.md).
# Read the current ids from `gemini --help` and Groq's /models endpoint; names change.
GEMINI_MODEL=
COMPRESS_BATCH_MODEL=
COMPRESS_PAGE_MODEL=
SYNTH_MODEL=
```

## Notebook routing

NotebookLM notebook ids and keywords live in `references/notebook-routing.md`, not here. Get ids
with `notebooklm list`.

## Keys

Keys are read from the environment, never from this file. The registry lists each tool's
variable names (for example `DATAFORSEO_USERNAME`, `SPYFU_API_KEY`, `EXA_API_KEY`,
`SNYK_TOKEN`). Check what is set with `python3 scripts/focus_check.py probe <tags>`, which prints
"key set" or "missing", never a value.
