---
date: 2026-10-02
type: research
topic: "Hunter/gatherer split for research-stack v3, with Jev (TypeSafe) as the gatherer's optional scorer"
depth: default
focus: [ai-agents]
target: none
sub_questions: 5
---

## Research: hunter/gatherer mode and Jev as the gatherer's scorer

Research Stack run on itself, in the mode it was designing (Step 3H). Five hunter subagents ran in
parallel, one per sub-question, and wrote 70 evidence cards plus raw notes. Two fresh-context
Claude scorers (a small model and a mid-size model) scored every card against the brief's rubric
with `scripts/gather.py`. The lead decided the 32 cards the two did not both keep. A skeptic
subagent then reviewed the 60 kept cards, and the report was written from the kept cards only.
Every artifact is in `docs/research/2026-10-02-hunter-gatherer/`. Jev itself was **not** called:
no TypeSafe key was available in this environment (`api.typesafe.ai` returned 403 "Must supply an
API key").

### Decision answer

- **Ship hunter/gatherer mode with the free Claude-subagent scorer as the default.** It worked
  end to end on its first run. Five hunters returned 70 well-formed cards in 3 min 53 s. The
  gatherer cut what the lead had to read by hand to 32 cards, built a coverage map with no gaps,
  and caught the run's main sourcing error once the skeptic added a `source_note`.
  [INT:dogfood ledger + INT:labels]
- **Add Jev only behind shadow mode.** It is cheap and fast: $0.042 per million input tokens,
  0.35 s against 8.83 s for Fable 5.1 [FC:typesafe.ai + FC:every.to]. Its confident band holds up
  on classification tasks [FC:amankumar.ai + FC:lindfors.no + FC:jevainews.com]. But no test
  covers judging research cards, and it is weak exactly where curation is hard: derivations,
  nuance and adversarial text [ACAD + FC:jevbench.xyz + FC:blog.checkpoint.com]. Route
  on it only after it matches Claude's agreement with lead labels on about 200 in-domain cards,
  and then only for the typed labels and the drop side. [perspective:skeptic]
- **Never let Jev screen for injection, never send it internal cards, and treat upstream
  retention as unverified** on both the direct and Cloudflare routes. [FC:docs.typesafe.ai +
  FC:developers.cloudflare.com + perspective:skeptic]

### Sub-question answers

**Q1: Jev API contract**

- One endpoint, `POST https://api.typesafe.ai/v1/systemone`, with three typed question kinds:
  choice (up to 255 options), score (2 to 10 levels) and noul (a yes/no probability)
  [FC:docs.typesafe.ai + FC:developers.cloudflare.com].
- Limits for jev-1.13.0: 64k tokens per request, of which 32k for the state plus the longest
  question, and 100K tokens/s and 40 requests/s, "adjusting dynamically" [FC:docs.typesafe.ai].
  Third-party guides still quote 1,200 rpm and 250k tok/s [FC:jevaiguide.com]; see
  Contradictions.
- Price: "Input tokens: $0.042 / MTok … Output tokens: FREE". TypeSafe adds: "We can't prove it
  isn't subsidized" [FC:typesafe.ai]. Attribution re-checked on 2026-10-02.
- Versioning: `jev-latest` and `jev-preview` both point to `jev-1.13.0`. TypeSafe advises pinning
  the versioned id once confidence thresholds are tuned [FC:docs.typesafe.ai]. `jev-1.13` returns
  HTTP 400 "Unknown model" [FC:jevaiguide.com, third-party, one source].
- Access: TypeSafe's homepage still shows early access with a waitlist on 2026-10-02
  [FC:typesafe.ai].
- Hosts: Cloudflare Workers AI `typesafe/jev` has a 32k context, $0.042/M and no version selector
  [FC:developers.cloudflare.com]. jevtypesafeai.com is run by CODEFASHION TECH LTD, "not
  affiliated with TypeSafe AI", and resells access at $0.25 to $0.42/M [FC:jevtypesafeai.com].
  Official SDKs: PyPI `typesafe-sdk` 0.7.2 and npm `@typesafe-ai/sdk` 0.6.0 [FC:pypi.org].

**Q2: Independent evidence of Jev's accuracy and calibration**

- **Strong on short typed labels:**
  - MLflow: 30/30 agreement with human labels on 30 QA items, at 369 ms median
    [FC:mlflow.org].
  - Bryo: 96.4% on 1,565 supplier emails across 10 categories, against 97.5% for Gemini 3.5
    Flash-Lite, with zero errors in Jev's most confident 85.5% [FC:jevainews.com, aggregator of
    an X thread, unverified].
  - Kumar: as a "page useful?" reject filter, 97.8% agreement on 1,005 pages, and 100% correct on
    the 63% of pages where it was confident [FC:amankumar.ai].
- **Calibration holds in the confident band.** Lindfors found answers at 0.7 to 1.0 confidence
  right 97-98% of the time, but the 0.3 to 0.7 band right only 34% [FC:lindfors.no]. OpenRouter
  measured a Brier score of 0.043 against 0.054 for gpt-5.6-luna on 88 HaluEval items
  [FC:openrouter.ai].
- **Weak where curation is hard:**
  - CMU: 14.6 points behind GPT-6 on JudgeBench (78.6 vs 93.1); "Larger gaps arise when judgments
    require checking a derivation or resisting an elaborately written wrong answer" [FC:arxiv.org
    2609.26550].
  - Every: caught 6 of 7 planted writing defects, where Fable 5.1 caught 7 [FC:every.to].
  - JevBench: 62.6% against Claude Haiku 4.5's 81.3% on phishing, and its relevance-ranking probe
    failed 4 of 6 checks [FC:jevbench.xyz, anonymous, unverified].
  - Kumar: on a value-extraction gate, "its probability swung by 0.5 between runs on the same
    page" [FC:amankumar.ai].
- **Vendor claims:** 67.8% against Claude Opus 5's 73.1% on TypeSafe's four-workflow benchmark,
  scored against a GPT-6/Fable reference [FC:typesafe.ai]. The RLCD training method behind the
  calibration claim is undisclosed.

**Q3: What a hunter should hand to the curator**

- Each subagent brief gives an objective, an output format, tool and source guidance, and task
  boundaries [FC:anthropic.com]. Subagents write to a store and return "lightweight
  references", which avoids a "game of telephone" [FC:anthropic.com]. Results come back as
  condensed summaries of "often 1,000-2,000 tokens" [FC:anthropic.com 2025-09-29].
- A subagent's only channel back is its final message [CLD]. File handoff is
  therefore the way to keep raw material out of the lead's context.
- open_deep_research returns both `compressed_research` and `raw_notes` per researcher
  [FC:github.com/langchain-ai]. Anthropic's research subagent prompt passes unresolved conflicts
  up to the lead rather than resolving them [FC:github.com/anthropics].
- The `supported` check is necessary because cited is not verified. Deep-research agents'
  citation accuracy ranges from 40% to 80% (DeepTRACE) [ACAD:2509.04499]. Links are valid
  over 94% of the time, but fact checks pass only 39% to 77%, and accuracy falls about 42% as
  tool calls grow from 2 to 150 [ACAD].
- There is no published card schema for a hunter-to-curator handoff. The schema in
  `references/hunter-gatherer.md` is this run's own, tested once.

**Q4: Confidence-based routing**

- Cascades pay off. FrugalGPT matched GPT-4 with up to 98% lower cost [ACAD:2305.05176].
  RouteLLM cut cost by over 85% on MT Bench while keeping 95% of GPT-4's quality
  [FC:lmsys.org]. Cascaded Selective Evaluation kept above 80% human agreement at about 80%
  coverage using cheap judges first [ACAD:2407.18370].
- Thresholds need in-domain labels. RouteLLM's routers were near-random out of domain until about
  1,500 in-domain labels were added [FC:lmsys.org]. CMU's frozen cascade kept 99% of the
  comparator's accuracy at 56.8% of the cost, but its thresholds did not transfer across tasks
  [ACAD:2609.26550].
- Label budget: about 200 paired labels give a ±0.05 interval on kappa around 0.6 (a 95% CI
  width of 0.10) [FC:hashnode.dev]. A rare class under 10% needs more [FC:hashnode.dev].
  Conformal guarantees want about 1,000 points [ACAD:2107.07511]. Compare
  judge-to-human kappa against human-to-human kappa, not against a fixed cutoff [FC:potatoannotator.com].
- **Measured in this run: self-reported LLM confidence is not usable as a gate.** The mid-size
  scorer returned 0.60 for every usefulness confidence on all 70 cards. The small scorer's
  confidences varied (0.75 to 0.95) but ran high: it auto-kept 59 cards, 6 of which the lead
  dropped, against 2 of 42 for the mid-size scorer. [INT:dogfood ledgers + INT:labels]

**Q5: Data and injection risk**

- **Training and retention:** TypeSafe commits not to train on customer input but sets no
  retention period [FC:typesafe.ai privacy policy 2025-11-19]. Zero data retention is "for
  enterprise customers" only [FC:docs.typesafe.ai] (attribution re-checked). Cloudflare lists
  `typesafe/jev` as "Third-party" with "Zero data retention", but treats third-party models as
  services under the provider's own terms [FC:developers.cloudflare.com]. Nothing published says
  that flag binds TypeSafe upstream. [perspective:skeptic]
- **Subprocessors and telemetry:** TypeSafe's DPA (2026-04-24) authorises subprocessors listed
  only on its trust site [FC:typesafe.ai]. An independent EU reading says MCA §4.3 lets TypeSafe
  process "Telemetry" (logs, hashes, classifications, learnings) "without restriction"
  [FC:wunderlandmedia.com, unverified: the MCA would not load].
- **Injection:**
  - TypeSafe's own jev-1.13 notes list adversarial content as a known failure mode: injected text
    "can move the answer" [FC:docs.typesafe.ai].
  - JevAdvBench: "one unverified opinion appended to the state flips 12.1% of decisions" and
    "pushes 38% of confident answers below the 0.8 confidence threshold" [FC:arxiv.org
    2609.31142] (attribution re-checked).
  - Check Point broke every Jev configuration it tested at about $0.54 per break, and labelling
    the content untrusted did not help [FC:blog.checkpoint.com].
  - OWASP: "it is unclear if there are fool-proof methods of prevention" [FC:owasp.org].

### Contradictions

- **Injection rate:** JevAdvBench found 12.1% of decisions flipped by one appended opinion
  [ACAD:2609.31142]. The Decision Hijacking study found the attacker's target selected in
  only 1.8% of cases, rising to 3.5% with optimisation [ACAD:2609.28613]. The attacks
  differ (an opinion nudging a verdict versus naming a target), so no single rate applies to
  research cards. Both are preprints about a week old with no replication. [perspective:skeptic]
- **Rate limits:** official docs give 40 req/s and 100K tok/s; third-party guides give 1,200 rpm
  and 250k tok/s. Trust the official docs; the guides likely describe an earlier limit.
  [FC:docs.typesafe.ai + FC:jevaiguide.com]
- **Variance:** LangChain reports Jev's score variance 92 to 913 times lower than LLM judges
  [FC:langchain.com], while Kumar saw probabilities swing by 0.5 between runs on the same page
  [FC:amankumar.ai]. These are different tasks, and pinning plus a canary set is how to tell
  them apart.
- **Access:** TypeSafe's homepage still shows a waitlist, while a model directory says general
  availability came on 2026-09-20 [FC:typesafe.ai + FC:directory, dropped as unverified].

### Patterns (cross-cutting, 2+ sources)

- **Typed labels are easy and graded judgments are hard, for every scorer.** In this run the two
  Claude scorers agreed perfectly on sub-question, supported and injection (kappa 1.0), but
  barely on usefulness (kappa 0.12) [INT:agree-haiku-sonnet]. Jev's external record has the
  same shape: strong at classification, weaker at nuance [FC:mlflow.org + ACAD +
  FC:every.to]. Put cheap scorers on labels and spend the strong model on graded calls.
- **Calibrate per task, on labels.** RouteLLM, CMU and TypeSafe's own docs all say a threshold
  is only good for the task and build it was tuned on [FC:lmsys.org + ACAD +
  FC:docs.typesafe.ai].
- **A judge can be moved by what it judges.** This holds for Jev [FC:docs.typesafe.ai +
  FC:arxiv.org + FC:blog.checkpoint.com] and for LLM judges in general (RobustJudge, 13 models)
  [ACAD:2506.09443].

### Coverage gaps

- **Jev on research cards: unmeasured.** No key was available. The run is set up to measure it:
  `gather.py score … --scorer jev`, then `merge` the injection screen and `agree` against
  `scores-sonnet.jsonl` and the lead's `labels.jsonl`.
- **The label set is too small to set thresholds.** It has 70 labels, but only 34 come from the
  lead (32 escalated plus 2 skeptic overrides); the other 36 were "both scorers kept". About 200
  lead labels across 3 or 4 runs are needed.
- **The hunters did not test the drop path.** They were told not to over-filter, yet both scorers
  dropped 0 of 70 automatically, and the lead's 12 drops were background cards rather than wrong
  ones. A future run should seed known-bad cards to test the drop path.
- **Publishing Jev numbers may be restricted.** A raw note (Q2) says TypeSafe's Master Customer
  Agreement §2.3(f) restricts publishing benchmarks. This is unverified; check it before putting
  Jev results in this public repo. [INT:raw-Q2.md]
- Upstream retention behind Cloudflare's zero-data-retention flag: unverified (Q5).

### Run measurements (dogfood)

| Stage                     | Measured                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------- |
| Hunt (5 parallel)         | 3 min 53 s wall clock; 70 cards, 0 malformed; about 620k tokens inside the hunters        |
| Handoff                   | 54 KB of cards (about 13.5k tokens) plus 15 KB of raw notes reached the gatherer          |
| Score (2 scorers)         | about 1 min each; small model 68k tokens, mid-size model 81k tokens                       |
| Route (mid-size)          | 42 keep / 0 drop / 28 escalate (constant confidence detected, routed on scores)           |
| Route (small)             | 59 keep / 0 drop / 11 escalate (6 of the 59 the lead later dropped)                       |
| Cascade to lead           | 32 of 70 cards (46%) read by the lead; 22 kept, 10 dropped                                |
| Skeptic on kept set       | 5 findings; 2 reseller cards overturned and 3 design changes adopted                      |
| Coverage                  | 5 of 5 sub-questions covered; no re-hunt needed                                           |

The code changes this run caused: constant-confidence detection, `source_notes`, `merge`, Jev's
exclusion from the injection screen, TypeSafe-direct as the default host, and shadow mode.

### Model and eval evidence

Focus tools: CLD (Claude docs) and ACAD (arXiv) were used. S2, AA, PF and PAPER were not needed
for these sub-questions, and promptfoo was not run.

| Claim / choice                                   | Evidence (date)                                                                                   | Source                          | Eval that would prove it                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| Hunters as parallel subagents with file handoff  | 5 hunters, 70 cards, 3 min 53 s, 0 malformed (2026-10-02); the only channel back is the final message | [INT:dogfood] + [CLD]           | Same 5 sub-questions single-context against hunter mode, scored by `validate_report all`   |
| Small Claude model as the default card scorer    | Agreed with the lead on 23 of 32 hard cards; 6 of its 59 keeps overturned (2026-10-02)              | [INT:labels]                    | 200 lead labels; precision of auto-keep at least 0.95                                       |
| Do not gate on LLM self-confidence               | Mid-size scorer: 70 of 70 usefulness confidences were 0.60 (2026-10-02)                             | [INT:scores-sonnet]             | `confidence_signal` on every run; alert when constant                                       |
| Jev for typed labels in shadow mode              | Confident band reliable on classification; JudgeBench 78.6 vs 93.1 (2026-09-21)                     | [ACAD:2609.26550] + [FC:amankumar.ai] | Jev and Claude scored against the same 200 lead labels; kappa per question                  |
| Jev never screens for injection                  | One appended opinion flips 12.1% of decisions (2026-09-25)                                         | [ACAD:2609.31142]               | Seed 10 injected cards; count how many are flagged by the Claude screen versus by Jev       |
| Thresholds 0.8 / 0.2 are placeholders            | Thresholds did not transfer across tasks (CMU); about 200 labels for kappa ±0.05 around 0.6 (CI width 0.10) | [ACAD:2609.26550] + [FC:hashnode.dev] | Sweep keep/drop on the label set; pick the cutoff at the target precision            |

### Sources

Every URL behind a kept card (all cards, kept or not, are in the run folder):

- https://docs.typesafe.ai/models
- https://docs.typesafe.ai/api.md
- https://jevaiguide.com/jev-api/
- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://developers.cloudflare.com/ai/models/typesafe/jev/
- https://jevtypesafeai.com/terms
- https://pypi.org/pypi/typesafe-sdk/json
- https://every.to/vibe-check/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds
- https://arxiv.org/html/2609.26550v1
- https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/
- https://amankumar.ai/blogs/jev-measured
- https://mlflow.org/blog/jev-llm-judge/
- https://www.langchain.com/blog/jev-agent-evals-langsmith
- https://dev.to/gabrielanhaia/jev-beat-gpt-luna-by-1-point-gpt-6-and-claude-wrote-the-answer-key-314k
- https://lindfors.no/blog/a-first-look-at-typesafes-jev/
- https://jevainews.com/news/
- https://jevbench.xyz/
- https://github.com/dchristopoulos/jev-aita
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/prompts/research_subagent.md
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://code.claude.com/docs/en/agent-sdk/subagents
- https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py
- https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/prompts.py
- https://arxiv.org/abs/2603.04384
- https://arxiv.org/abs/2509.04499
- https://arxiv.org/html/2605.06635
- https://arxiv.org/abs/2305.05176
- https://www.lmsys.org/blog/2024-07-01-routellm/
- https://arxiv.org/abs/2407.18370
- https://arxiv.org/abs/2605.18796
- https://arxiv.org/abs/2107.07511
- https://llmasajudge.hashnode.dev/your-llm-as-judge-eval-set-is-too-small-here-is-the-math
- https://www.potatoannotator.com/docs/guides/llm-judge-human-agreement
- https://llmasajudge.hashnode.dev/calibration-set-size-for-llm-as-judge-when-50-traces-is-enough-and-when-200-is-mandatory
- https://jevwiki.ai/wiki/concepts/confidence.md
- https://typesafe.ai/legal/privacy-policy
- https://docs.typesafe.ai/legal
- https://developers.cloudflare.com/workers-ai/platform/privacy/
- https://typesafe.ai/legal/data-processing
- https://wunderlandmedia.com/typesafe-ai-jev-terms-of-service-gdpr
- https://docs.typesafe.ai/model-jaggedness/jev-1.13.md
- https://arxiv.org/abs/2609.31142
- https://blog.checkpoint.com/ai-security/jev-is-not-a-language-model-but-it-breaks-like-one-prompt-injection-against-a-typed-decision-model/
- https://arxiv.org/abs/2609.28613
- https://arxiv.org/abs/2506.09443
- https://genai.owasp.org/llmrisk/llm01-prompt-injection/

---
Research Stack report
|- Scope: 5 sub-questions, 5 covered, 5 gaps named (Jev on research cards, label count, drop path, benchmark clause, upstream retention)
|- Web search: about 70 searches and fetches across 5 hunters (Exa, built-in search, page fetch, HN Algolia, arXiv API)
|- Page fetch / scraper: hunters' fetches, plus 4 attribution re-fetches by the lead
|- Answer engine: not configured
|- Hacker News: queried by the Q2 hunter (mostly Show HN wrappers; none carded)
|- Academic: 14 papers (arXiv, ACL, NAACL)
|- Internal round: the research-stack v3 branch and the development-protocol port (read-only); no team connectors relevant
|- Gatherer: claude-sonnet (routing) + claude-haiku (comparison) | 70 cards | keep 42 / drop 0 / escalate 28 / flagged 0 | re-hunt none
|- Perspectives: 1 run | 1 with findings | 0 escalated
|  `- skeptic: 5 findings (subagent, fresh context)
|- Attribution: 4/4 spot-checked claims supported
|- Validation: WARN. Structure 10/10, focus PASS, citations 26 live / 0 dead / 4 unverified (GitHub 503, API 405), source quality 6.0/10 (most Jev evidence is on new third-party sites), checked 2026-10-02
|- Cache: this file
|- Est. total cost: $0.00 in API fees (Claude subagents and included search quota)
`- Sources: docs.typesafe.ai, typesafe.ai, developers.cloudflare.com, arxiv.org, anthropic.com, github.com, lmsys.org, every.to, amankumar.ai, mlflow.org, openrouter.ai, langchain.com, blog.checkpoint.com
