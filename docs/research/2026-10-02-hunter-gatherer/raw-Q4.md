# Q4 raw notes (hunter)

## Queries run
- arXiv API: ti:FrugalGPT, ti:RouteLLM, "LLM cascade" AND confidence, "conformal" AND "LLM judge", ti:"Trust or Escalate"; full abstracts for 2305.05176, 2406.18665, 2605.18796.
- Exa: TypeSafe Jev confidence threshold docs; label count for LLM judge calibration and Cohen's kappa; conformal calibration set size (Angelopoulos & Bates); RouteLLM LMSYS blog numbers.
- Exa fetch: docs.typesafe.ai/concepts/confidence (CRAWL_NOT_FOUND, so it is a guessed URL and may not exist); jevwiki.ai confidence page (fetched).

## Findings not carded / extra
- Conformal LLM-judge papers in 2026: CS-WCP (2609.27955, robust to traffic shift), multi-expert CRC for pairwise judging (2608.26529), Robust Conformal Consensus (2609.06367), SummEval conformal sets with width as a reliability indicator (2604.15302, N=1918). These are relevant if the gatherer wants conformal over 2 judges; not carded to stay inside the card limit.
- P3Defer (2410.08014): privacy-aware cascade deferral. Possible overlap with Q5.
- AWS sample-GEDD claims 15-20 labels per criterion are enough for kappa. That is much more optimistic than the other sources and I treat it as doubtful (not carded).
- Genalphai (2026-06) cites kappa >0.6 as the production floor and 100-300 labels, using SE ~ (1-kappa)/sqrt(n). Secondary aggregator, not carded.
- ai-tldr: 50-200 labels to start calibration; weighted kappa or Spearman for ordinal 1-5 scores.

## Source-trust flags
- I could not reach an official typesafe.ai docs page. The Jev pages I found are on jevtypesafeai.com, jevwiki.ai, mrjev.com, learnjev.com, docs.rs and openrouter.ai. The jev-as-a-judge page names "the official ... typesafe.ai/v1" endpoint, which suggests jevtypesafeai.com is not first-party. Cross-check with Q1.
- On jevtypesafeai.com, the judge-page code (options/levels/verdict.key) does not match the docs page schema (criteria/choice). This looks like inconsistency or marketing copy.
- No injection attempts seen.

## Gaps
- No independent measurement of Jev confidence calibration (for example, a reliability diagram) was found here. That belongs to Q2.
- No cascade paper specific to relevance or curation filtering of research evidence. The closest are Cascaded Selective Evaluation and UCCI (NER).
- FrugalGPT's numbers come from 2023 APIs and benchmarks; there is no fresh replication on 2026 model prices.
