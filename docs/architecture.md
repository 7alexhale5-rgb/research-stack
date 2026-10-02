# Architecture (v3)

Research Stack v3 is a phased pipeline driven by **sub-questions**, with optional **focus lenses**
that each add a tool stack, extra sub-questions and a required report section. The method follows
production deep-research systems: scope first, fan out only to relevant sources, check coverage
per sub-question, challenge findings, and ground every claim in a source you can point to.

## Step map

| Step | Name                  | What happens                                                                                   |
| ---- | --------------------- | ---------------------------------------------------------------------------------------------- |
| 0    | Parse intent          | Topic, depth, query type, flags, config (`config/config.md`).                                   |
| 0.4  | Resolve focus         | `--focus` / `#tag` / bundles / `DEFAULT_FOCUS`; unknown tag stops; max 4; suggest from triggers. |
| 0.5  | Adaptive scope        | 3-6 sub-questions plus each lens's 2-3 (max 8); ask only when a wrong fork is expensive.        |
| 1    | Probes                | Keys, CLIs and keyless APIs; `focus_check.py probe` over the registry; MCP prefixes matched.    |
| 2    | Scope gate            | Decision, sub-questions, focus, target, tools per tag, cost; pauses only when worth it.         |
| 3H   | Hunter/gatherer       | `--deep` or 4+ sub-questions: hunters per sub-question write cards; `gather.py` scores and routes; writer reads kept cards only. |
| 3    | Round 1               | Web search per sub-question, answer engine, research cache (focus-aware TTL).                   |
| 3.5  | Round 1.5             | Internal connectors when the topic touches the team's own work.                                 |
| 4    | Round 2               | HN, community, academic, scraper, index search, code docs, legal, notebooks (power tier).       |
| 4F   | Focus rounds          | One parallel block per tag: the lens's tool stack in tier order; `--target` audit mode.          |
| 4.5  | YouTube               | Transcripts (`--youtube` or `--deep`).                                                          |
| 5    | Gap check, Round 3    | Coverage per sub-question (lens authorities count as authoritative); targeted fetches.          |
| 6    | Compress              | Self or subagent by default; Groq batch on the power tier.                                      |
| 6.5  | Synthesis assist      | `--deep` only.                                                                                  |
| 6.6  | Perspectives          | Skeptic always; cross-source on default; gap-detector on `--deep`. Lens-aware.                  |
| 7    | Synthesize            | Answer sub-questions in order, specifics or cut, focus addenda filled.                          |
| 7.8  | Auto-refine           | `--auto-refine` only, max 3 iterations.                                                         |
| 8    | Steering              | The single mid-run question, only when something is thin.                                       |
| 8.5  | Validation            | `validate_report.py all`: structure, focus, citations, source quality; attribution spot-check.  |
| 9    | Deliver               | Decision answer, sub-questions, contradictions, patterns, gaps, addenda, dashboard.             |
| 10   | Cache                 | Always; `focus:` and `target:` in front matter. `--vault` notes on the power tier.              |
| 11   | Expert mode           | Follow-ups answered from the gathered research.                                                 |

## Data flow

```text
topic + flags
   |
   v
[0 parse] -> [0.4 focus: tags.json, focus/<tag>.md] -> [0.5 sub-questions (+lens questions)]
   |
   v
[1 probes: tool-registry.json] -> [2 scope gate]
   |
   v
Round 1 (parallel) ---- Round 1.5 internal ---- Round 2 (parallel) ---- Step 4F: one block per tag
   |                                                                       (|- audit --target)
   v
[5 coverage per sub-question] -> Round 3 targeted fetches
   |
   v
[6 compress] -> [6.6 perspectives] -> [7 synthesize + addenda] -> [8.5 validate] -> [9 deliver] -> [10 cache]
```

In hunter/gatherer mode (Step 3H) the rounds above run inside one hunter per sub-question:

```text
brief.json -> hunters (parallel, read-only) -> cards-Qn.jsonl + raw-Qn.md
           -> gather.py prompt|score -> scores.jsonl -> gather.py route -> ledger.json
                (keep / drop / escalate to lead / flagged; coverage -> re-hunt gaps once)
           -> [6.6 perspectives on kept cards] -> [7 synthesize from kept cards] -> ...
```

Rounds are separate parallel blocks because, in Claude Code, one failing call cancels its
siblings in the same block. Each focus tag gets its own block for the same reason: a flaky paid
connector in one lens cannot wipe out another lens's results.

## Focus lenses

A lens (`focus/<tag>.md`) is a contract with eight sections: Triggers, Sub-question lens, Tool
stack, Authorities, Freshness, Audit mode, Report addendum, Pathway mapping. The machine-readable
parts live in `focus/tags.json`: addendum name, source tags, authority domains, trigger regex,
pathway and overlay mapping, and development-protocol rows. `scripts/focus_check.py lint` keeps
lens, manifest and registry consistent. `scripts/validate_report.py` enforces the addendum for
every tag a report declares.

Lenses are opt-in. With no tag, the scope gate suggests matching lenses but never applies one
silently.

## Degradation

The minimum viable pipeline is web search plus page fetch. Every lens has a free-only path, and
every paid tool in the registry names a free fallback (the linter enforces it). A lens whose paid
tools are missing still runs and says what it could not measure. Per-source failures and
fallbacks are in `references/providers.md` and `references/power-tier.md`.

## Token and cost economics

- Free-only runs cost $0. Paid runs are estimated in Step 2 from current pricing pages and capped
  per depth (`BUDGET_*`), domain APIs included.
- Pages are compressed before synthesis; raw pages never reach the synthesis pass.
- Lens files are loaded only for active tags, so a general run carries none of their text.

## Downstream contracts

| Consumer                | Reads                                     | Contract                                                                     |
| ----------------------- | ----------------------------------------- | ---------------------------------------------------------------------------- |
| development-protocol    | the report at `.devproto/evidence/research.md` | research row verified by `validate_report.py structure`; focus hints from the goal |
| pathway-operating-layer | dossier front matter `focus:`              | research verifier requires each tag's addendum; tags derived from overlays    |
| gravity-stack           | report sections                           | promptfoo goldens check v3 headings and focus addenda                        |
| 1pct-moves-only         | `/research-stack --no-ask --focus <tag>`  | external unknowns go to research instead of stopping to ask                  |
