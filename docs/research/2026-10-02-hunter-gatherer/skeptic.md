## Finding 1 (severe): "Cloudflare zero data retention" is a catalog field, not evidence of ZDR at TypeSafe

**Source Concern:** Q5-03 is the only card for "Zero data retention: Yes", and the hunter's own note says the page "doesn't say how ZDR is enforced upstream at TypeSafe." Four other cards point the other way:
- Q5-04: Cloudflare treats third-party models as Third-Party Services under the provider's terms.
- Q5-02: TypeSafe offers ZDR to enterprise customers only, through sales.
- Q5-06: inference runs on Modal and live request data sits on AWS.
- Q5-07: MCA section 4.3 "Telemetry" (logs, hashes, classifications, learnings) may be processed "without restriction". This is secondhand; the MCA 404'd for the hunter.

The Cloudflare page lists a 32k context window, against 64k direct. That suggests a pass-through to TypeSafe-run inference, not Cloudflare-hosted weights. Nothing in the cards rules that out.

**Challenge:** The working answer offers the Cloudflare route as an equal alternative to the official API. That implies it solves the retention problem. The cards support "Cloudflare does not train on your content" and nothing more. Even with true ZDR, the typed sub-question text and the claim text for "supported" and "injection" are still sent upstream, and those can carry client context.

**Recommendation:** State "retention upstream of Cloudflare: unverified" in the answer. Before any non-public text goes to Jev, either get written ZDR from sales@typesafe.ai or ask Cloudflare in writing how the Jev ZDR flag is enforced. Until then, restrict Jev to text that is already public web content with the query terms stripped of client names. Keep Claude as the default and the only path for anything sensitive.

## Finding 2: "Pinned to jev-1.13.0" cannot be shown to hold on the Cloudflare route, and the calibration targets differ across routes

**Source Concern:**
- Q1-11 lists the Cloudflare model only as `typesafe/jev`, with no version selector. Only an example response shows jev-1.13.0.
- Q1-09 and Q4-11 pinning advice applies to TypeSafe's `model` field.
- Q1-10 is a single third-party test: `jev-1.13` returns 400, and the real ceiling is about 32k tokens.
- Q2-04 tested a dated snapshot (`jev-1.13-20260917`), not `jev-1.13.0`. The evidence base therefore mixes builds.

**Challenge:** The recalibration plan assumes a stable scorer. On the Cloudflare route it may silently change underneath the thresholds. The two routes also differ in context (32k vs 64k), price and possibly rate limits (Q1-04 vs Q1-05). A 200-label calibration done on one route does not transfer to the other.

**Recommendation:** Support one route in v1, the official API with `jev-1.13.0`. Treat Cloudflare as unpinnable until Cloudflare documents version control. Run the calibration against the exact route and model ID that will ship. Add a canary set to every run that fails closed to the Claude scorer if agreement drops.

## Finding 3: Injection evidence is decisive in direction but rests on single-card preprints, and it undermines the 0.8 gate itself

**Source Concern:** Three post-2026-09-15 arXiv papers sit under Q5 and Q2, and each is cited by exactly one evidence line.
- 2609.31142 (Q5-10) is the only source for the 12.1% flip rate and the 38% drop below 0.8.
- 2609.28613 (Q5-12) is the only source for the 1.8% to 3.5% hijack rate.
- 2609.26550 appears in Q2-02 and Q2-03, which is one paper counted twice. Q2-03's numbers came through a WebFetch summarizer and the card says "verify".

None has been seen by a second source. They are also 1 to 2 weeks old, so there has been no replication or critique. Only the direction is corroborated, by Check Point (Q5-11) and the vendor's own jaggedness doc (Q5-09).

**Challenge:** Q5-10 and Q5-12 disagree (12.1% vs 1.8%). That is explained by attack type, but it means no injection rate for research cards is established. The 0.8 placeholder is also the exact gate JevAdvBench shows being pushed under by a single unverified opinion. Check Point shows that labelling content "untrusted" does not help. A scorer fed raw fetched web text is the attack surface, and a Jev "supported" or "injection" verdict can be steered by the text it is judging. The answer already says "never the only gate", but "injection" is on the Jev list, which asks the weakest component to detect attacks against itself.

**Recommendation:** Drop `injection` from the Jev question set and use a Claude pass on the quote-only snippet. Use Jev only for label questions where an adversarial page gains little. Run Jev on the verbatim quote field (short), never the full page. Treat the arXiv numbers as "reported, unreplicated" in the synthesis.

## Finding 4: Threshold and confidence guidance is sourced from an unaffiliated reseller and anonymous or aggregator sites

**Source Concern:**
- Q4-12 (0.85 cutoff, "0.9 holds nine times in ten") and Q4-11 are on jevtypesafeai.com. Q1-12 shows that domain is CODEFASHION TECH LTD, "not affiliated with TypeSafe AI", reselling at 6-10x list. Q4-11's "Direct TypeSafe-side guidance" label in the why field is wrong. Its pinning advice survives because the official docs in Q1-09 corroborate it.
- Q4-13 (confidence formula) is a reverse-engineered third-party wiki (jevwiki.ai) citing a demo. The no-confidence-field-on-Noul detail drives the whole keep/drop design and needs an official source.
- Q2-13 (jevbench.xyz) is anonymous and was classed as independent-test, though the hunter itself rated it low. Q2-12 is an aggregator (jevainews.com) relaying an X thread nobody fetched. Q1-05 (jevaiguide.com) conflicts with the official limits and should not be used.

Provenance of 0.8/0.2: 0.8 matches the JevAdvBench gate and 0.85 matches reseller marketing. No card supports 0.2.

**Challenge:** Calling them "placeholders" is honest, but the design (including the two-cutoff Noul rule) is built on unofficial descriptions of how confidence works.

**Recommendation:** Confirm the confidence and Noul semantics against docs.typesafe.ai or one live call before building on them. Drop jevtypesafeai.com cards from the evidence base. Mark Q2-12 and Q2-13 as unverified in the report. Treat 0.8/0.2 as an untested starting point, not a derived number.

## Finding 5: The accuracy evidence is for classifiers, not for research-card relevance or support, and the positive tests come from commercial partners

**Source Concern:**
- Positive evidence is from parties with a stake: Every (pre-launch access, Q2-01), OpenRouter (resells, Q2-04), LangChain (partner, Q2-08), MLflow (n=30 with a ceiling effect, Q2-07), TypeSafe (Q2-09, graded against LLM outputs).
- Independent and negative evidence is sharper on the exact use here. Kumar (Q2-05, Q2-06) shows a relevance filter works only on the confident 63%, and a value-extraction gate falls to 68.6% with probabilities swinging 0.5 between runs. This contradicts LangChain's 92-913x variance claim (Q2-08). CMU (Q2-02, Q2-03) shows near-chance reference-free prose judging at 0.90 confidence and thresholds not transferring across tasks.
- No card tests Jev on "sub-question", "supported" or injection labels on research snippets.

**Challenge:** The working answer extrapolates from classification and HaluEval to research curation. The simplicity filter says the free Claude subagent scorer already gets most of the value. The measured saving for Jev is cost and latency on a task where the whole pipeline's cost is dominated elsewhere. Meanwhile the integration adds a waitlist dependency (Q1-07: still early access), a second vendor, a second data-handling regime, and an attack surface.

**Recommendation:** Ship the Claude-subagent scorer alone as v3. Put Jev behind a flag after it passes a shadow run: score ~200 in-domain cards (more if the rare class is under 10%, per Q4-10) with both scorers, and report Jev-vs-human agreement against Claude-vs-human agreement (Q4-09). Only enable Jev if it matches Claude's agreement at the confident band, and only for sub-question tagging and the drop side of the keep/drop rule.
