# Q2 raw notes (hunter)

## Queries / calls (~13 tool calls)
- Exa: "TypeSafe Jev judge model accuracy test review" -> MLflow, LangChain, CMU arXiv 2609.26550, Aman Kumar, Arize, OpenRouter, calibrateddecisions.com, DecisionEval, wrangleai, jev-aita.
- HN Algolia stories + comments "TypeSafe Jev": mostly Show HN wrappers (jevpipe, jevmem, jev-cli, mini-jev, credence). Notable stories: backnotprop poker test, lindfors.no test, mikulskibartosz "can't see" test (not fetched), OpenAI Decision API (Luna) competitor story 2026-09-29. Jevmem claims held-out check on 66 messages (23 Sep) - not fetched.
- Exa fetch: arXiv, amankumar, OpenRouter, MLflow; WebFetch arXiv results section (numbers via summarizer - verify against paper tables).
- Exa: Every vibe check (got full highlights incl. Shipper 6/7 test).
- Exa: TypeSafe launch post + 67.8/73.1 table (typesafe.ai blog; table via width.ai / dev.to / LinkedIn digests).
- Exa fetch: lindfors, jev-aita, backnotprop poker. WebFetch lindfors summary.
- Exa: jevainews 1,500/1,565 emails -> Bryo (Mudholkar) 1,565 table; Ryan Vogel 1,500 clip has no accuracy.
- Exa fetch: jevbench.xyz, LangChain, Arize.

## Dropped to stay <=14 cards (gatherer may want)
- backnotprop poker: Jev matched solver top action 63% of 30 spots; with straight vs known flush bet all-in 5/5 runs; value-laden verbs pushed bigger bets. https://backnotprop.com/blog/jev-poker/ (2026-09-17)
- jevainews claims TypeSafe Master Customer Agreement s2.3(f) forbids publishing benchmarks -> chills independent tests (unverified against MCA). https://jevainews.com/news/aman-kumar-filter/ (also Q1/Q5)

## Other leads not carded
- DecisionEval: Jev 1.13.0 on LocalLLaMA/typed-decisions 400 cases: acc 0.740, Brier 0.148, ECE 0.045 (10 bins). https://decisioneval.dev/models/typesafe-jev/ (unknown date, unknown authorship)
- wrangleai review: 100% baseline/contested, 94% policy gates vs 77-88% small model (vendor-adjacent orchestration platform).
- Arize: NearHere listing moderation 96% vs Gemini Flash-Lite 86%; zero-shot 18,514 spam emails statistical tie vs trained classifier (original sources not found).
- Charly Poly Banking77: beat open encoders on macro-F1, lost on ECE (via jevainews; not fetched).
- mlllm.io: notes calibration only confirmed by vendor internal benchmark; workflow benchmark is agreement with GPT-6 Astra/Fable 5.1, not ground truth.
- Third-party hosts (jevtypesafeai.com /api/v1/decide with jv_live_ keys) republish vendor claims -> Q1/Q5 concern, not official.

## Gaps
- No X/Twitter originals fetched (Mudholkar thread, Vogel clip, Shipper tweet) - only aggregator summaries.
- No test specifically of Jev as a *research-evidence relevance scorer* (closest: Kumar "is this page useful" filter, JevBench ESCI ranking FAIL, CMU reference-free prose near chance).
- No adversarial/prompt-injection test of Jev as judge found (RM-Bench style-adversarial is the nearest).
- arXiv numbers beyond abstract came through a summarizer; recheck tables.
- No injection attempts observed in fetched pages.
