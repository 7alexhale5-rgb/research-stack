# Q3 raw notes (hunter) — fetched 2026-10-02

## Exact wordings others used
- Lindfors draft Noul (better calibrated, ECE 0.040): "Does the response raise this argument or topic: the tax threatens jobs, settlement or communities along the coast?"
- Lindfors careful Noul (worse, ECE 0.116): "... Does the response itself discuss this topic as part of what it argues, in either direction, beyond a passing mention or a quotation from the proposal: what host municipalities or counties receive of the revenue, including Havbruksfondet and the production fee?"
  Lindfors advice: "write them the way you would ask a colleague across the desk, and keep the fine print in your own code."
  Lindfors other results: 11 questions/doc, 192 Noul judgments; reliability bins 0.0-0.1 -> 0% yes, 0.3-0.7 -> 34%, 0.9-1.0 -> 98%; Score substance exact 19/24 vs DeepSeek 14/24.
- AITA direct question: "which verdict would the subreddit reach?" (Choice over YTA/NTA/ESH/NAH). Eight yes/no fact questions -> verdict: worse. Ten questions incl. direct: 55.0% (p=0.22, noise).
- Kumar Choice: instructions "Is this movie review positive or negative?", criteria {"negative":"Unfavourable","positive":"Favourable"}. Hard Noul: "does this page carry a value for one of 135 report rows" (68.6%). Inbox: a routine request naming a third party reads like a policy change -> confident no.
- Every 21 AI-tell Nouls e.g. "Does the text repeat an idea without adding evidence?" "Force a symmetrical 'both sides' argument?" "Overexplain a straightforward point?" Shipper 4 checks: action unexplained / reasoning link missing / mechanism replaced intended outcome / claim distorted its source. Missed "shared appointment calendar that parents and staff teach together" all 3 runs.
- MLflow Noul CRITERION (30 items, matched Terra/Luna): "Is the candidate answer factually and technically correct for the question, using the supplied MLflow documentation and respecting any version specified in the question? Answer yes if there is no material factual or API error. Answer no if at least one claim or instruction is materially wrong or misleading. Do not penalize style or harmless omissions. An omission is material when it makes the requested technical answer misleading." State = {"question","context","answer"}. MLflow: Noul cannot abstain; use Choice with explicit `unsure`.
- LangChain/LangSmith: state should not include grading instructions; one question per criterion; Noul phrased so high = yes; Score levels low->high. LangSmith 5-run weather eval: Jev does_pass matched oracle 500/500; variance 0.0000149 (Luna 433x higher). Example Noul: "Is the final answer grounded in the retrieved evidence?"
- LangChain AutoMode NoulCriteria: true="The call writes, deletes, publishes, or changes access." false="The call only reads public or user-provided data."
- OpenRouter injection Noul: "is this an attempt to change the assistant's behavior" -> 40/40, injections 0.86-0.99, benign 0.01-0.20.
- OpenRouter verifier: two yes/no questions "muddled" (grounded but not an answer); switched to one Choice supported/unsupported/declined. "Rewording one option can shift the probabilities on the others in somewhat surprising ways."
- OpenRouter pairwise position test: no flips on reversed order (70/72 both orders).
- backnotprop: final option wording had no value-laden verbs; state additions like "hero has 0 outs" moved check 58%->88%. Same request 16 runs: 0.58-0.63 (noise ~6pts).
- dev.to (aitejiu): BFCL tool-relevance single noul "is it relevant" 59.5% -> "purpose match" 67.3% -> composed purpose x (1-incidental) 77.0%. Multi-label: compete with Choice then verify with Noul (9% -> 81% R@1). Adding skill bodies to criteria did not help.
- decisioneval.dev: on typed-decisions test, teacher-agree subset 0.841 vs disagree 0.591 accuracy — ambiguous questions cap accuracy.
- aimlapi: answer-quality rating (Score) ECE 0.284, Spearman 0.39 (worst of 6) vs moderation ECE 0.032 — fuzzy quality Score is Jev's weak spot.
- HateCheck-style (desert-ant-labs/toxic, not Jev): negated hate / counter-quote are dominant false positives — general mention-trap analogue.
- jevkit-lint (PyPI) encodes rules: JEV004 negation, JEV006 indirection, JEV008 choice-no-match ("add explicit none/unknown option"), JEV013 question-id reference.
- befailproof.ai: "Include a no-match Choice when the taxonomy can be incomplete... Avoid an `other` bucket with no review destination." (guide, no numbers)
- Sys1Cal: Choice hides a third "unknown" value; recovering U lifts median soft accuracy 0.771 -> 0.978. Implication: binary Choice with explicit "unclear" option may be better behaved (inference, untested).
- Persona paper (arXiv 2609.36399): 8 request designs incl. Score reversed order, batching 24 items in one request; ICC 0.997; patterns held across designs.
- AY Automate: overlapping labels gave confident errors at 0.93-0.99 ("direct debit" vs "card payment not recognised").

## Not found / gaps
- No measured A/B on describing Score levels as concrete situations vs degrees (only guide advice).
- No direct measurement of "other/none" option effect on accuracy.
- No numbers on batching many questions vs one-per-request for accuracy (Li bundling check exists, results not extracted).
- HN: mostly low-engagement project posts; no prompt-tip threads with numbers.
