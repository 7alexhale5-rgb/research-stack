# Focus lens: ai-agents (LLMs, agents and evals)

Use this lens when the work builds on models, agents, prompts, RAG, MCP or evals. Model facts
(ids, limits, prices, tool versions) change monthly. This lens reads them from the provider's
current docs and benchmarks and never from memory, and it insists on a measurable eval.

## Triggers

Suggested when the topic mentions LLMs, agents, agentic, prompts, RAG, evals, MCP, models,
fine-tuning, embeddings, Claude, GPT or Gemini.

## Sub-question lens

1. **Current facts:** which models, ids, context limits, tool versions and prices apply today,
   from the provider's own docs (with dates)?
2. **Evidence:** what do benchmarks and papers say about the approach for this task type, and what
   are their limits (contamination, task mismatch)?
3. **Eval plan:** how will we measure success? Name the golden set, the metrics (for example
   faithfulness and groundedness for research and RAG) and the harness that runs them in CI.

## Tool stack

| Tool                  | Tier       | Use it for                                                 | Skip when                     |
| --------------------- | ---------- | ---------------------------------------------------------- | ----------------------------- |
| `claude-docs`         | free       | Current Claude model ids, limits, tools, pricing           | never for a Claude claim      |
| `arxiv`               | free       | Papers and preprints                                       | pure product question         |
| `semantic-scholar`    | free       | Citation counts and influential follow-ups                 | brand-new preprint            |
| `paper-mcp`           | free (MCP) | De-duplicated search across arXiv, S2 and OpenAlex         | not installed (use arxiv)     |
| `artificial-analysis` | free       | Independent model, speed and price benchmarks              | non-benchmarkable question    |
| `promptfoo`           | free (CLI) | Eval and red-team harness docs and config examples         | no eval in scope              |

Also check the official docs of any other provider named in the topic (ai.google.dev,
platform.openai.com) and modelcontextprotocol.io for MCP spec questions.

## Authorities

The provider's own platform docs outrank everything for its models. Peer-reviewed or widely cited
papers outrank blog benchmarks. Leaderboards are evidence about the leaderboard's task only.

## Freshness

- Cache TTL: 7 days for model facts and pricing, 90 days for papers.
- Dated traps: model ids get retired, and tool versions are date-stamped. A dead model pin often
  looks like a rate-limit error. Re-read the docs before blaming a quota.

## Audit mode

With `--target <repo|path>`: find model ids, prompt files and eval configs in the code. Compare the
model ids against the provider's current model list and flag retired or deprecated ones. Report
whether an eval suite exists and runs in CI. Tag `[AUDIT:models]`.

## Report addendum

Add a **Model and eval evidence** section:

```text
### Model and eval evidence
| Claim / choice                    | Evidence (date)                          | Source        | Eval that would prove it         |
| --------------------------------- | ---------------------------------------- | ------------- | -------------------------------- |
| Use model X for compression       | $/M tokens and TPM limit (2026-10)       | [CLD]         | 20-page golden set, fact recall  |
```

## Pathway mapping

- pathway-operating-layer: `quality`, `security`, `observability`, plus the `llm-agent-eval`
  overlay.
- development-protocol rows: `research`, `spec` (the eval is an acceptance criterion), `verify`.
