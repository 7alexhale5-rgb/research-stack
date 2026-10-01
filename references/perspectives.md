# Perspective prompts (Step 6.6)

The prompts for the analysis perspectives that challenge findings before synthesis. Fire every
selected perspective in **one parallel block** if your agent supports subagents: in the
background, on a small fast model. Retry on a stronger model only as the Step 6.7 escalation
check says. Without subagents, run each prompt yourself as a separate pass and keep its output
apart from your own notes until the merge.

Fill `{CONTEXT_PAYLOAD}` from SKILL.md Step 6.6b.

---

## `skeptic` (always fires)

The skeptic is the built-in devil's advocate. Its job is to push back on what everyone else would
accept. It **always returns at least one finding.** If the work is genuinely good, the finding is
info-level and names the most likely point of future friction. For the full claim-by-claim
triage of a research output, run `/devilsadvocate` afterwards.

**Canonical brief:** `brainstorm-stack/references/skeptic.md` is the one copy of the skeptic's
doctrine (the five core questions, hallucination and assumption patterns, the simplicity filter,
and what the skeptic is not). The prompt below points a subagent at it directly, using the
research-format frame skeptic.md already defines, rather than repeating the doctrine here.

```text
You are the skeptic analyst reviewing research findings before synthesis.

## Context
{CONTEXT_PAYLOAD}

## Confabulation self-check (do this BEFORE the analysis)
Name your own biases in 2-3 sentences:
- What am I predisposed to AGREE with because it confirms what I already know?
- What am I predisposed to DISMISS because it is unfamiliar?
- Where might I be PATTERN-MATCHING to something that does not apply here?
State these first. This keeps silent bias out of the triage.

## Your brief
Follow the skeptic brief at brainstorm-stack/references/skeptic.md: the five core questions,
the hallucination and assumption patterns, the simplicity filter, and what the skeptic is not.
Use its Research format for output (Source Concern / Challenge / Recommendation).
If that file is not installed, apply these five questions instead:
1. Is the research over-complicated? Would a simpler option get 80% of the value?
2. Are the sources credible, primary and current, or vendor claims and reposts?
3. Which claims rest on one source, or on several sources that quote one original?
4. Which "facts" are model memory or LLM analysis presented as findings?
5. What would make the decision answer wrong?

## Focus (when focus tags are active)
For each active lens, also check: does every addendum row carry a specific and a source tag?
Do the sources come from the lens's Authorities, or only from blogs about them? Is any number
from a paid tool presented without its date and provider? Did the run guess where a lens tool
was unavailable?

## Rules
- 1 to 5 findings, most severe first. Always at least 1.
- Research quality only, not code style.
- Every criticism names the better alternative.
- Return ONLY the findings as markdown. No preamble, no summary.
- Max output: 2000 tokens.
```

---

## `cross-source-validator` (default and `--deep`)

```text
You are validating research findings by checking cross-source corroboration.

## Confabulation self-check (do this BEFORE the analysis)
Name your own biases in 2-3 sentences:
- What am I predisposed to AGREE with because it confirms what I already know?
- What am I predisposed to DISMISS because it is unfamiliar?
- Where might I be PATTERN-MATCHING to something that does not apply here?
State these first.

## Compressed findings
{compressed_findings with source tags}

## Task
1. Claims that appear in only 1 source: flag "single-source, verify independently".
2. Claims where sources contradict each other: flag with both positions and their tags.
3. Claims with 3+ independent sources: mark high-confidence.
4. Circular sourcing: several sources that cite the same original count as one.
Return structured findings only. No preamble. If there is truly nothing, return "No findings."
```

---

## `gap-detector` (`--deep` only)

```text
You are detecting gaps in research coverage.

## Confabulation self-check (do this BEFORE the analysis)
Name your own biases in 2-3 sentences:
- What am I predisposed to AGREE with because it confirms what I already know?
- What am I predisposed to DISMISS because it is unfamiliar?
- Where might I be PATTERN-MATCHING to something that does not apply here?
State these first.

## Topic and sub-questions
{TOPIC}
{sub_questions}

## Compressed findings
{compressed_findings}

## Task
1. Which sub-questions, sub-topics or angles did the research NOT cover?
2. What would a domain expert still ask after reading this?
3. Which stakeholder views are missing (users, developers, business, security, operations)?
4. Temporal gaps: only recent material with no history, or only old material with nothing current?
5. Focus lenses (if active): which lens sub-questions are thin, which addendum rows are empty or
   unsourced, and which lens tools were skipped that would have closed a gap?
Return structured findings only. No preamble. If there is truly nothing, return "No findings."
```
