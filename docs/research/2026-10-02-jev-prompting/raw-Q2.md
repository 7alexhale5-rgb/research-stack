# Q2 raw notes (hunter)
Sources fetched: docs.typesafe.ai api.md, models, jaggedness jev-1.13, concepts/state, confidence, primitives/score+noul, advanced, cookbooks/parallel_questions, fan-out; typesafe.ai launch blog; arXiv 2609.26550 (CMU), 2609.31142 (JevAdvBench); amankumar.ai; lindfors.no; HN algolia; docs.rs typesafe-jev (third-party Rust client).
Raw page dumps stayed in the session scratchpad (not published).
Key findings:
- State: string|object|array of text; object recommended w/ descriptive names. Backtick field refs in instructions. Question map keys NOT sent to model. Out-of-schema request keys never billed/seen (JevAdvBench).
- Caps: 64k/request total; 32k state+longest question. Norwegian ~2.06 chars/token (Lindfors); JevAdvBench: ~5 chars/token billed (English).
- Irrelevant state hurts (context rot, jaggedness #5). Aman: long whole-doc reads degrade.
- Confidence: Choice (pmax-1/n)/(1-1/n) == clamp((n*pmax-1)/(n-1)) CONFIRMED. Score: max(0, 1 - sum p_i|i-m| / MAD_unif). Noul: none returned; suggest |2p-1|. Score value = prob-weighted mean of level indices; don't interpolate magnitudes.
- Determinism: TypeSafe cookbook mostly identical repeats, some noul noise; JevAdvBench 38.5% of Score values change on identical rerun (decision flip floor 1.0%); CMU 0/96 decision changes on repeats; Aman ~0.01 on easy, 0.5 swings on hard mention-vs-value. No caching documented.
- Independence: questions evaluated independently/in parallel, batching no effect.
- Limits: counting, arithmetic, dates, numeric reps, indirection/multi-hop, literal reading, adversarial/argued state (12.1% flips from an appended opinion), generation. Niche world knowledge limited (HN quote of TypeSafe).
- Languages: English best; others/CJK lower.
- Instructions vs criteria weight: NOT FOUND explicitly; only "align them, contradictions confuse" (jaggedness #7). Position (start vs end of state) effects: NOT FOUND officially; only CMU candidate-order reversal (~5% of pairs flip) and Lindfors anecdote of finding content at end of 12 pages.
- Launch: new architecture, parallel sampler; >some cardinality Choices use 2-stage scoring.
- Not reached: OpenRouter Jev blog, Every.to, Cloudflare model page.
