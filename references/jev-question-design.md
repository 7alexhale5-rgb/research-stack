# Writing questions for Jev

How to write requests to Jev (TypeSafe's System One model) so its typed answers and
confidences come out right. The rules follow from how Jev reads its input and forms its output.
`scripts/gather.py` applies every rule below. This page says why, so the next change to the
rubric keeps them.

Sources: TypeSafe's docs (primitives, Choice, Score, Noul, advanced structure, confidence,
how-to-build, the jev-1.13 jaggedness notes and the cookbooks), read 2026-10-02, and the
measured studies in `docs/research/2026-10-02-jev-prompting-dossier.md`. Unless marked
otherwise, the quotes are TypeSafe's.

## 1. How Jev reads a request

| Fact                                                                                       | Consequence for the question writer                                                       |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| It returns a probability distribution over the options you define, "never a value outside them" | You design the answer space. A missing "none" option forces a wrong answer.              |
| "Question IDs are for your code. They are not sent to the model."                          | Write the whole question in `instructions`. An id like `is_relevant` says nothing to Jev.  |
| Option names **and** descriptions are sent; "The model sees the names along with the values" | Keys are signal. Keep them neutral (`Q1`, `Q2`). Swapping which definition a meaningful yes/no name carries flipped 32.5% of decisions; neutral names flipped about 2% (arXiv 2609.26758). |
| A Score level "is judged on its own"; the model "doesn't see a level's number or its neighbours" | Each level must describe a whole situation. "Worse than the previous level" and bare numbers mean nothing to it; numeric-only levels gave confidence 0.33 where described levels gave 1.0. |
| "Every question in a request sees the same state", and "One question's answer is not hidden context for another" | Batch every question about one card into one request (12.2 times cheaper in TypeSafe's test, with the same answers). Never chain questions inside a request. |
| "`jev-1.13` answers the question you wrote, not the one you meant"                          | Be literal. Scoping words, negations and implied conditions are read at face value.       |
| "Jev suffers from context rot, so unrelated material in the `state` costs you accuracy"     | Send only the fields the questions need.                                                  |
| State "is not treated as hostile by default"; "text that argues for its own classification can move the answer" | Keep opinions out of the state. One appended observer opinion flipped 12.1% of decisions (JevAdvBench, arXiv 2609.31142). |
| It "reads dates as text", "does not count reliably", and its score levels are "weak in numerical calibration" | Dates, counts, arithmetic and thresholds belong in code.                                 |
| English is the primary training language                                                   | Keep cards in English.                                                                     |

## 2. How Jev reports certainty

- **Choice:** `confidence = (p_max - 1/n) / (1 - 1/n)`. Only the top probability counts, so a
  0.6/0.3/0.1 split and a 0.6/0.2/0.2 split both give 0.4. Low confidence means no option clearly
  wins, or the card fits two options; a runner-up above about 0.25 is worth recording.
- **Score:** confidence falls with the spread of probability around the top level, and a
  neighbouring level costs less than a distant one. The fractional `score` is a
  probability-weighted mean position, **not a magnitude**. Identical requests moved it on 38.5%
  of Score questions while the decision flipped on 1.0% (JevAdvBench). **Route on the
  distribution** (`gather.py level_mass`), never on the fractional value.
- **Noul:** a single probability and no confidence field. TypeSafe's stand-in is `|2p - 1|`.
  Nouls are not coherent with each other: "refund" at 0.72 plus "not_refund" at 0.47 sums to
  1.19, so ask each decision one way and derive the opposite in code.
- **Calibration** is per question type and per build. "Don't carry a threshold tuned on a Noul
  over to a Choice". Pin `jev-1.13.0`, and record the build each response reports. In one study
  Choice probabilities were less well calibrated than Noul or Score on the same items (Sys1Cal,
  arXiv 2609.35342).

## 3. Rules for each question type

**All types**

1. **One snap judgment per question:** "a judgment a knowledgeable person makes in a second".
   Several judgments hidden in one question blur the answer; a merged "pressure or legitimate
   escalation" question gave 0.47, and split it gave 0.04 and 0.96 (dev.to benchmark).
2. **Short, plain and positive.** Write for an average reader. Longer "careful" wording with
   qualifiers raised calibration error from 0.040 to 0.116 and pushed answers toward 0.5
   (Lindfors). Avoid negations, double negatives and multi-hop indirection.
3. **Name the state part in backticks,** for example "Does the text in `quote` …". Paths use
   dots and indexes: `ticket.messages[0].text`.
4. **Criteria extend the instruction and never contradict it.** A Noul whose `true` means no
   performs worse.
5. **A `focus` line may contrast** ("the question it answers most directly, not every topic it
   mentions"), as TypeSafe's structured examples do. Keep the question itself positive.
6. **Don't over-decompose a holistic call.** Splitting one verdict into eight yes/no facts
   scored 41.5% to 51.5% against 53.0% asked directly, with worse calibration (AITA benchmark).
   The poker study saw the same pattern (57-59% against 63%). Split only where one question
   really measures two things.

**Choice**

7. Give the full option list in a **stable order** (reordering changed 10.3% of picks against
   2.7% for a plain rerun; Jevals), plus an `other` / `none` option.
8. When options blur, use objects with the same fields on every option: `what`, `not_for`,
   `examples`. Write descriptions that separate the options. A brief's sub-questions may be
   objects for this reason.

**Score**

9. Use 2 to 10 levels, ordered low to high, each describing **a concrete situation**:
   "Broken or degraded feature, but workaround exists" works, and "Moderately severe" doesn't.
10. One dimension per Score. Give a rare extreme its own level. If nothing lies in between, use
    a Choice or Nouls.
11. If neighbouring levels keep splitting, use level objects (`what` plus `examples`). Examples
    help only when they look like the real inputs (Safari report: confidence went from 0.35 to
    0.96 with a matching example and stayed at 0.35 with a mismatched one).

**Noul**

12. One condition, phrased so that **high means yes**. "Is it free of X" inverts the meaning.
    Make the boundary sharp: "any" leaves no middle ground.
13. Add `{true, false}` criteria only when the boundary is subtle. Test with and without them on
    your own cards.

## 4. What gather.py sends, and why

| Question    | Type   | Jev asked? | The rule behind it                                                                                  |
| ----------- | ------ | ---------- | --------------------------------------------------------------------------------------------------- |
| `subq`      | choice | yes        | Neutral keys in brief order, a `none` option, and a `focus` line (rules 5 and 7)                    |
| `specific`  | noul   | yes        | One condition, positive, an "any"-style list ("a specific number, version, date, name…")           |
| `impact`    | score  | yes        | Four situational levels with `what` plus `examples`, one dimension: how far the evidence moves the decision |
| `supported` | noul   | yes        | Literal attribution: "states or directly implies everything said in `claim`", with aligned criteria |
| `authority` | score  | **no**     | Needs knowledge of the source that the state does not carry. Code sets it from the source type and `source_notes`. |
| `injection` | noul   | **no**     | A judge asked whether a text attacks it can be steered by that text. A Claude pass answers this one. |

- The **state** for Jev is `{claim, quote}` only. The host, the date, the hunter's source type
  and the hunter's "why" stay out: they are irrelevant to the four questions (context rot), and
  the "why" is an opinion (JevAdvBench).
- The old single `usefulness` scale mixed two judgments and was split into `specific` and
  `impact`. Code recombines them: `usefulness_from` holds impact at background when nothing
  specific is stated.
- **Routing** reads the probability mass at or above a level (`level_mass`), uses `|2p - 1|`
  for Noul confidence, and gates on confidence only for Jev, never on an LLM's self-report.
- **`requote`:** a card whose quote does not back the whole claim goes back to its hunter instead
  of being dropped.

## 5. Write the cards for the scorer

Jev judges the state literally, so the card is the prompt. In the dogfood runs the strict
`supported` check found that hunters routinely wrote claims that reach past their quotes: only
17 of 70 run-1 cards were fully backed. The hunter rules in `references/hunter-gatherer.md`
section 2 therefore say:

- The quote is the evidence: verbatim, up to 300 characters, containing every fact in the claim.
- The claim restates only what the quote says, as one sentence with its specific. A second
  passage means a second card.
- Interpretation goes in `why`, which the Jev scorer never sees.

## 6. A/B and calibrate before trusting a change

1. Score the same cards with both variants: `gather.py score … --scorer jev --variant
   structured` and `--variant plain` (the plain variant drops the level examples and the Noul
   criteria).
2. Merge in the Claude injection screen, then run `gather.py eval scores.jsonl labels.jsonl
   cards…` for each. It reports keep precision, drop precision, requotes and escalations at keep
   thresholds from 0.5 to 0.95.
3. Keep the variant with the higher precision at the escalation rate you can afford. Change one
   wording at a time ("Two wordings of the same scale can behave differently on your data").
4. Set thresholds only after about 200 lead labels on this kind of research. A higher
   confidence alone does not show that a wording is better.
