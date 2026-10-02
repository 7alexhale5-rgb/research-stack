---
date: 2026-10-02
type: research
topic: "How to instruct and prompt Jev (TypeSafe System One) for research-card scoring"
depth: default
focus: [ai-agents]
target: none
sub_questions: 3
---

## Research: how to word Jev's questions for the gatherer

The second hunter/gatherer run. Three hunters (official guidance, how Jev reads state, measured
practitioner findings) wrote 48 cards; a fourth subagent distilled TypeSafe's docs into 90
quoted rules. A fresh Claude scorer graded the cards and the lead decided the 23 it escalated.
The findings were then turned into the rubric in `scripts/gather.py` and the guide
`references/jev-question-design.md`, and tested by re-scoring both runs and re-hunting one
sub-question under new card rules. Artifacts: `docs/research/2026-10-02-jev-prompting/`. Jev
itself was still not called (no key).

### Decision answer

- **Write the rubric the way Jev reads.** Jev judges each Score level alone, never sees question
  ids, reads instructions literally, and can be moved by opinions in its state. So: one short,
  positive judgment per question with the state keys named in backticks, situational Score
  levels, neutral option keys in a stable order with a none option, and only `claim` and
  `quote` in Jev's state. [FC:docs.typesafe.ai + ACAD:2609.31142 + ACAD:2609.26758]
- **Route on Jev's distributions, not its fractional scores,** and on its published confidence
  formulas, never on an LLM's self-reported confidence. [FC:docs.typesafe.ai + ACAD:2609.31142 +
  INT:dogfood]
- **The card is the prompt.** The literal `supported` question showed hunters' claims routinely
  reach past their quotes. New card rules lifted fully backed cards from 2 of 16 to 16 of 16 on
  the same sub-question. [INT:scores-v2-original-vs-strict]

### Sub-question answers

**Q1: TypeSafe's official guidance on writing questions**

- One snap judgment per question; "Ask the most explicit, narrow, specific, atomic questions you
  can" [FC:docs.typesafe.ai]. Question ids "are not sent to the model", so the full question goes
  in `instructions` [FC:docs.typesafe.ai].
- Score levels "describe concrete situations"; "The model doesn't see a level's number or its
  neighbours", and numeric-only levels gave confidence 0.33 against 1.0 described
  [FC:docs.typesafe.ai]. Level objects with the same fields (`what`, `examples`) separate
  neighbours; examples help only when they resemble real inputs (0.35 to 0.96 on a matching
  example) [FC:docs.typesafe.ai].
- Choice sends option names and descriptions; give the full list and a none option
  [FC:docs.typesafe.ai]. Noul: one condition, "high value means yes", no inversions, criteria only
  for subtle boundaries, and test with and without them [FC:docs.typesafe.ai].
- Batch all questions on one state: 13 questions batched matched separate calls at 12.2 times
  lower cost [FC:docs.typesafe.ai].

**Q2: How Jev processes state and produces outputs**

- State can be a string, object or array; an object with descriptive keys is recommended; send
  only the fields the question needs, because accuracy falls with irrelevant content
  [FC:docs.typesafe.ai].
- Counting, arithmetic, numeric precision and date comparison are unreliable; keep them in code
  [FC:docs.typesafe.ai].
- Choice confidence is (p_max - 1/n)/(1 - 1/n); Score uses a spread formula; Noul returns none
  (stand-in |2p-1|) [FC:docs.typesafe.ai]. The fractional score is a probability-weighted mean
  position, not a magnitude [FC:docs.typesafe.ai].
- Identical requests changed the Score value on 38.5% of Score questions while decisions flipped
  on 1.0%; one appended observer opinion flipped 12.1% of decisions [ACAD:2609.31142].
- Context: 64k per request, 32k for state plus the longest question [FC:docs.typesafe.ai];
  English is the primary language [FC:docs.typesafe.ai].

**Q3: Measured effects of question design**

- Over-decomposing a holistic verdict hurts: 53.0% asked directly against 41.5-51.5% split into
  eight yes/no facts, and Brier 0.515 against 0.369 [FC:github.com/dchristopoulos]; poker 57-59%
  split against 63% direct [FC:backnotprop.com].
- Splitting a question that really mixes two concepts helps: a merged question gave 0.47, split it
  gave 0.04 and 0.96 [FC:dev.to].
- Longer "careful" wording raised calibration error from 0.040 to 0.116 [FC:lindfors.no].
- Option names bound to definitions flipped 32.5% of decisions; neutral names about 2%
  [ACAD:2609.26758]. Reordering options changed 10.3% of picks against 2.7% on a rerun
  [FC:jevals.com].
- Choice probabilities were less well calibrated than Noul and Score on the same items (OVL
  0.764 against 0.918 and 0.886) [ACAD:2609.35342]; Nouls for X and not-X miss summing to 1 by
  0.064 on average [ACAD:2609.33209].
- Closed rubrics suit Jev; open rubrics do not (SummEval Spearman 0.47 against 0.72 for an LLM
  judge) [FC:openrouter.ai].

### Contradictions

- **Decompose or not.** TypeSafe advises atomic questions combined in code [FC:docs.typesafe.ai];
  AITA and poker show decomposition hurting [FC:github.com/dchristopoulos + FC:backnotprop.com];
  the shell-risk benchmark shows splitting helping [FC:dev.to]. Reading: split where one question
  measures two things, never split a single holistic judgment into proxy facts. The rubric splits
  only `usefulness` (specific vs impact), which measured two things.
- **Run-to-run stability.** TypeSafe's cookbook saw identical answers on most repeats
  [FC:docs.typesafe.ai]; Kumar saw 0.5 swings on mention-vs-value questions [FC:amankumar.ai];
  JevAdvBench saw Score values move on 38.5% of reruns [ACAD:2609.31142]. Decisions are stable,
  fractional values are not, so route on distributions.

### Patterns (cross-cutting, 2+ sources)

- **Literal in, literal out.** Jev answers the words, so wording errors become answer errors
  [FC:docs.typesafe.ai + FC:lindfors.no + ACAD:2609.26758].
- **Code owns what code can compute:** dates, counts, thresholds, authority lookups
  [FC:docs.typesafe.ai + FC:amankumar.ai].
- **Opinions in the state move the answer** [ACAD:2609.31142 + FC:docs.typesafe.ai].

### Model and eval evidence

Focus tools used: ACAD (arXiv) and the vendor docs; CLD not needed; promptfoo not run.

| Claim / choice                                    | Evidence (date)                                                                           | Source                        | Eval that would prove it                                                   |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------- |
| Strict card rules make cards scoreable            | Same rubric and scorer: supported >= 0.8 on 2/16 original cards, 16/16 strict (2026-10-02) | [INT:scores-v2-original-vs-strict] | Repeat on all sub-questions of the next run                           |
| v2 rubric tuned for Jev, not for an LLM scorer    | Claude scorer under v2: auto-keep precision 0.80-0.83 against 0.95-1.00 under v1 (2026-10-02) | [INT:eval]                 | Same cards scored by Jev with both variants, `gather.py eval` per variant |
| Route on distributions                            | Score value moved on 38.5% of identical requests, decisions 1.0% (2026-09-25)             | [ACAD:2609.31142]             | Rerun 50 cards 3 times; compare decision stability                          |
| Keep Jev's state to claim + quote                 | One appended opinion flips 12.1% of decisions (2026-09-25)                                 | [ACAD:2609.31142]             | Jev with and without `hunter_note` in state, against labels               |

### Coverage gaps

- **Jev was not run.** Every wording choice is sourced, not measured on Jev for research cards.
  The A/B is ready: `score --variant structured` and `--variant plain`, then `eval` against
  `labels.jsonl`.
- **The v2 rubric scored worse than v1 with a Claude scorer** on both runs. Most of the gap is the
  stricter attribution check meeting loose cards (run 1: supported >= 0.8 on 17 of 70), and the
  strict re-hunt closed it for one sub-question. The rest is untested.
- Nobody has measured where in the state content should sit, or whether instructions or criteria
  carry more weight.

### Run measurements

| Stage                        | Measured                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------- |
| Hunt (3 parallel)            | 48 cards, 0 malformed, about 3 min                                           |
| Rulebook distiller           | 90 quoted rules from 12 official pages                                       |
| Score + route (v1 rubric)    | confidence-gated: 2 keep / 46 escalate; on answers only: 25 keep / 23 escalate |
| Lead adjudication            | 23 escalated: 17 kept, 6 dropped (third-party, background or anecdote)       |
| v2 re-score, run 2 (48)      | at 0.8: 5 auto-keep (precision 0.80), 4 requote, 36 escalate                 |
| v2 re-score, run 1 (70)      | at 0.8: 12 auto-keep (precision 0.83), 1 requote, 57 escalate                |
| Strict re-hunt Q2 (16 cards) | supported >= 0.8: 16/16 (original 2/16); 7 auto-keep (original 0)            |

### Sources

- https://docs.typesafe.ai/primitives/score
- https://docs.typesafe.ai/primitives/choice
- https://docs.typesafe.ai/primitives
- https://docs.typesafe.ai/primitives/noul
- https://docs.typesafe.ai/model-jaggedness/jev-1.13
- https://docs.typesafe.ai/cookbooks/parallel_questions
- https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md
- https://docs.typesafe.ai/concepts/state
- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/confidence
- https://arxiv.org/abs/2609.31142
- https://arxiv.org/abs/2609.26550
- https://amankumar.ai/blogs/jev-measured
- https://docs.typesafe.ai/api.md
- https://github.com/dchristopoulos/jev-aita
- https://lindfors.no/blog/a-first-look-at-typesafes-jev/
- https://jevbench.xyz/
- https://arxiv.org/abs/2609.26758
- https://arxiv.org/html/2609.33209v1
- https://arxiv.org/html/2609.35342v1
- https://backnotprop.com/blog/jev-poker/
- https://dev.to/aitejiu/benchmarking-jev-what-a-decision-model-can-and-cant-do-in-an-agent-harness-20po
- https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/
- https://openrouter.ai/blog/insights/jev-vs-claude-opus-5-classification/
- https://jevals.com/choice/
- https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-classification
- https://docs.typesafe.ai/concepts/state.md
- https://docs.typesafe.ai/models.md
- https://docs.typesafe.ai/model-jaggedness/jev-1.13.md
- https://docs.typesafe.ai/confidence.md
- https://docs.typesafe.ai/primitives/score.md
- https://docs.typesafe.ai/cookbooks/parallel_questions.md

---
Research Stack report
|- Scope: 3 sub-questions, 3 covered, 3 gaps named (Jev unmeasured, v2-vs-v1 on Claude, state position)
|- Web search: about 70 searches and fetches across 4 hunters (Exa, built-in search, page fetch, HN Algolia, arXiv)
|- Page fetch / scraper: 12 official doc pages read in full by the distiller
|- Answer engine: not configured
|- Hacker News: queried by the Q2 and Q3 hunters
|- Academic: 6 arXiv preprints
|- Internal round: first-run artifacts and labels (read-only)
|- Gatherer: claude-sonnet | 48 cards | keep 25 / drop 0 / requote 0 / escalate 23 / flagged 0 | re-hunt none
|- Perspectives: 0 run (findings tested by re-scoring and a re-hunt instead)
|- Attribution: 16/16 strict cards supported (scorer check); 15/15 escalated quotes read by the lead
|- Validation: WARN. Structure 10/10, focus PASS, citations 30 live / 0 dead, source quality 5.1/10 (vendor docs domain unscored), checked 2026-10-02
|- Cache: this file
|- Est. total cost: $0.00 in API fees
`- Sources: docs.typesafe.ai, arxiv.org, github.com, lindfors.no, amankumar.ai, openrouter.ai, jevals.com, dev.to, backnotprop.com
