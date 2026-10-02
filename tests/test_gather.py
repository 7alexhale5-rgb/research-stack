"""Tests for scripts/gather.py (hunter/gatherer mode). Run: python3 -m unittest discover tests"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gather as g  # noqa: E402

FIX = ROOT / "tests/fixtures"
BRIEF = str(FIX / "gather-brief.json")
CARDS = str(FIX / "gather-cards.jsonl")
SCORES = str(FIX / "gather-scores.jsonl")


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = g.main(argv)
    return code, out.getvalue(), err.getvalue()


def answers(choice="Q1", cconf=0.95, spec=0.95, imp=3.0, iconf=0.9, auth=3.0, sup=0.95,
            inj=0.01, probs=None):
    a = {
        "subq": {"choice": choice, "confidence": cconf},
        "specific": {"noul": spec},
        "impact": {"score": imp, "confidence": iconf},
        "supported": {"noul": sup},
        "authority": {"score": auth, "confidence": 0.9},
        "injection": {"noul": inj},
    }
    if probs is not None:
        a["impact"]["probabilities"] = probs
    return a


class RubricTest(unittest.TestCase):
    def test_rubric_has_six_typed_questions_and_a_none_choice(self):
        rubric = g.build_rubric(g.load_brief(BRIEF))
        self.assertEqual(list(rubric), g.QUESTION_IDS)
        self.assertEqual(rubric["subq"]["type"], "choice")
        self.assertEqual(list(rubric["subq"]["criteria"]), ["Q1", "Q2", "none"])  # stable order
        self.assertIn("self-hosted brokers", rubric["subq"]["criteria"]["none"])
        self.assertEqual(rubric["impact"]["type"], "score")
        self.assertIn("Which queue", rubric["impact"]["instructions"])
        self.assertEqual({rubric[q]["type"] for q in g.NOUL_QUESTIONS}, {"noul"})

    def test_rubric_follows_jev_question_rules(self):
        rubric = g.build_rubric(g.load_brief(BRIEF))
        for qid, q in rubric.items():
            ins = q["instructions"]
            # a `focus` line may contrast ("..., not every topic mentioned"), as TypeSafe's own
            # structured examples do; the question itself stays positive
            text = ins["question"] if isinstance(ins, dict) else ins
            self.assertIn("`", text, f"{qid}: name the state part with backticks")
            self.assertNotRegex(text.lower(), r"\bnot\b|\bfree of\b|\bwithout\b",
                                f"{qid}: no negation or inversion in instructions")
        levels = rubric["impact"]["criteria"]
        self.assertTrue(2 <= len(levels) <= 10)
        whats = [lvl["what"] for lvl in levels]
        for w in whats:  # each level judged alone: no relative or numeric-only wording
            self.assertNotRegex(w.lower(), r"\b(more|less|higher|lower|previous|next)\b|^\d+$")
        self.assertEqual({tuple(sorted(lvl)) for lvl in levels}, {("examples", "what")})

    def test_plain_variant_drops_examples_and_noul_criteria(self):
        rubric = g.build_rubric(g.load_brief(BRIEF), "plain")
        self.assertTrue(all(isinstance(lvl, str) for lvl in rubric["impact"]["criteria"]))
        self.assertNotIn("criteria", rubric["supported"])
        self.assertIsInstance(rubric["subq"]["instructions"], str)
        with self.assertRaises(g.UsageError):
            g.build_rubric(g.load_brief(BRIEF), "fancy")

    def test_brief_rejects_reserved_none_key(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"decision": "d", "sub_questions": {"none": "x"}}, fh)
        try:
            with self.assertRaises(g.UsageError):
                g.load_brief(fh.name)
        finally:
            os.unlink(fh.name)

    def test_state_hides_hunter_label_but_keeps_hunter_note(self):
        card = g.load_cards([CARDS])[0]
        state = g.card_state(card)
        self.assertNotIn("subq", state)
        self.assertEqual(state["hunter_note"], card["why"])
        self.assertEqual(state["source"], "docs.example.com")

    def test_jev_state_is_only_claim_and_quote(self):
        card = g.load_cards([CARDS])[0]
        self.assertEqual(sorted(g.card_state(card, {"example.com": "x"}, for_jev=True)),
                         ["claim", "quote"])

    def test_code_authority_uses_source_type_and_notes(self):
        card = g.load_cards([CARDS])[0]  # official
        self.assertEqual(g.code_authority(card), 3.0)
        self.assertEqual(g.code_authority(card, {"example.com": "reseller"}), 1.0)
        self.assertEqual(g.code_authority(card, {"example.com": {"note": "x", "authority": 0}}),
                         0.0)


    def test_source_note_matches_host_and_subdomains(self):
        card = dict(g.load_cards([CARDS])[0])
        notes = {"example.com": "vendor docs mirror, unaffiliated"}
        self.assertEqual(g.card_state(card, notes)["source_note"], notes["example.com"])
        self.assertNotIn("source_note", g.card_state(card, {"other.org": "x"}))
        self.assertIsNone(g.source_note("notexample.com", notes))


class CardCheckTest(unittest.TestCase):
    def test_fixture_cards_are_well_formed(self):
        self.assertEqual(g.check_cards(g.load_jsonl([CARDS])), [])

    def test_bad_cards_are_named(self):
        bad = [{"id": "x", "url": "ftp://a", "source_type": "rumour", "quote": "q" * 700}]
        probs = "\n".join(g.check_cards(bad))
        self.assertIn("missing", probs)
        self.assertIn("source_type", probs)
        self.assertIn("http(s)", probs)
        self.assertIn("600", probs)


class RouteTest(unittest.TestCase):
    def test_confident_supported_useful_card_is_kept(self):
        self.assertEqual(g.route_card(answers())[0], "keep")

    def test_injection_is_flagged_before_anything_else(self):
        self.assertEqual(g.route_card(answers(inj=0.9))[0], "flagged")

    def test_unsupported_quote_goes_back_for_a_requote(self):
        self.assertEqual(g.route_card(answers(sup=0.1))[0], "requote")

    def test_confident_none_is_dropped(self):
        self.assertEqual(g.route_card(answers(choice="none"))[0], "drop")

    def test_uncertain_card_escalates(self):
        self.assertEqual(g.route_card(answers(cconf=0.5))[0], "escalate")
        self.assertEqual(g.route_card(answers(sup=0.6))[0], "escalate")
        self.assertEqual(g.route_card(answers(spec=0.6))[0], "escalate")
        self.assertEqual(g.route_card({})[0], "escalate")

    def test_card_that_would_not_move_the_decision_is_dropped(self):
        self.assertEqual(g.route_card(answers(imp=0.2))[0], "drop")

    def test_score_routing_uses_the_distribution_not_the_mean(self):
        # mean 1.2 but 60% of the mass at level 0: does not reliably move the decision
        spread = {"0": 0.6, "1": 0.0, "2": 0.0, "3": 0.4}
        self.assertAlmostEqual(g.level_mass({"score": 1.2, "probabilities": spread}, 1), 0.4)
        self.assertEqual(g.route_card(answers(imp=1.2, probs=spread))[0], "escalate")
        self.assertEqual(g.level_mass({"score": 2.0}, 1), 1.0)

    def test_usefulness_is_capped_when_nothing_specific(self):
        self.assertEqual(g.usefulness_from(answers(imp=3.0, spec=0.2)), 1.0)
        self.assertEqual(g.usefulness_from(answers(imp=3.0, spec=0.9)), 3.0)

    def test_noul_confidence_is_typesafes_stand_in(self):
        self.assertAlmostEqual(g._conf({"noul": 0.1}), 0.8)  # |2p - 1|
        self.assertAlmostEqual(g._conf({"noul": 0.5}), 0.0)

    def test_llm_confidence_never_gates_by_default(self):
        cards = g.load_cards([CARDS])
        rows = [{"id": c["id"], "scorer": "claude", "answers": answers(cconf=0.6)}
                for c in cards]
        use, note = g.confidence_signal(rows)
        self.assertFalse(use)
        self.assertIn("not calibrated", note)
        self.assertEqual(g.build_ledger(rows, cards)["counts"]["keep"], 5)
        self.assertEqual(g.build_ledger(rows, cards, confidence="use")["counts"]["escalate"], 5)

    def test_jev_confidence_gates_unless_constant(self):
        rows = [{"id": str(i), "scorer": "jev-1.13.0",
                 "answers": answers(cconf=0.6 + i / 40)} for i in range(12)]
        self.assertTrue(g.confidence_signal(rows)[0])
        flat = [{"id": str(i), "scorer": "jev-1.13.0", "answers": answers(cconf=0.7)}
                for i in range(12)]
        self.assertFalse(g.confidence_signal(flat)[0])

    def test_ledger_on_fixture(self):
        cards = g.load_cards([CARDS])
        scores = g.load_jsonl([SCORES])
        brief = g.load_brief(BRIEF)
        led = g.build_ledger(scores, cards, brief["sub_questions"])
        by = {r["id"]: r["decision"] for r in led["cards"]}
        self.assertEqual(by, {"Q1-01": "keep", "Q1-02": "requote", "Q2-01": "keep",
                              "Q2-02": "escalate", "Q2-03": "flagged"})
        self.assertTrue(led["coverage"]["Q1"]["covered"])
        self.assertEqual(led["rehunt"], [])

    def test_gap_triggers_rehunt_and_strict_exit(self):
        cov = g.coverage([{"subq": "Q1", "authority": 1.0}], ["Q1", "Q2"])
        self.assertFalse(cov["Q1"]["covered"])
        self.assertFalse(cov["Q2"]["covered"])
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            for line in Path(SCORES).read_text().splitlines():
                row = json.loads(line)
                if row["id"] == "Q2-01":
                    row["answers"]["supported"]["noul"] = 0.05
                fh.write(json.dumps(row) + "\n")
        try:
            code, out, _ = run(["route", fh.name, CARDS, "--brief", BRIEF, "--strict"])
            self.assertEqual(code, 1)
            self.assertIn("re-hunt: Q2", out)
        finally:
            os.unlink(fh.name)


class AgreementTest(unittest.TestCase):
    def test_kappa(self):
        self.assertAlmostEqual(g.kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]), 1.0)
        self.assertAlmostEqual(g.kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]), 0.0)
        self.assertIsNone(g.kappa([], []))

    def test_identical_scorers_agree_fully(self):
        cards = g.load_cards([CARDS])
        scores = g.load_jsonl([SCORES])
        res = g.agreement(scores, scores, cards)
        self.assertEqual(res["cards"], 4)  # the held card has no answers
        self.assertEqual(res["route"]["agree"], 1.0)
        self.assertEqual(res["route"]["disagreements"], [])


class EvalTest(unittest.TestCase):
    def test_eval_reports_precision_and_missed_drops(self):
        cards = g.load_cards([CARDS])
        scores = g.load_jsonl([SCORES])
        labels = [{"id": "Q1-01", "label": "keep"}, {"id": "Q1-02", "label": "drop"},
                  {"id": "Q2-01", "label": "drop"}, {"id": "Q2-03", "label": "drop"}]
        res = g.evaluate(scores, cards, labels, sweep=(0.8,))
        row = res["sweep"][0]
        self.assertEqual(res["labelled"], 4)
        self.assertEqual(row["auto_keep"], 2)
        self.assertEqual(row["keep_precision"], 0.5)
        self.assertEqual(row["missed_drops"], ["Q2-01"])
        self.assertEqual(row["drop_precision"], 1.0)
        self.assertEqual(row["requote"], 1)


class JevTransportTest(unittest.TestCase):
    def fake_post(self, calls):
        def post(url, headers, body, timeout=30):
            calls.append((url, headers, body))
            choice = "Q2" if "pricing" in body["state"]["claim"] or "$" in body["state"]["claim"] \
                else "Q1"
            asked = answers(choice=choice)
            return {"model": "jev-1.13.0",
                    "answers": {q: asked[q] for q in body["questions"]},
                    "usage": {"input_tokens": 100}}
        return post

    def test_typesafe_scoring_holds_internal_cards_and_never_prints_the_key(self):
        calls = []
        env = {"TYPESAFE_API_KEY": "jv_live_SECRET123"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(g, "post_json", self.fake_post(calls)):
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "s.jsonl")
                code, stdout, stderr = run(["score", BRIEF, CARDS, "--scorer", "jev",
                                            "--out", out])
                rows = g.load_jsonl([out])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 4)  # five cards, one internal held back
        self.assertTrue(all(u == g.TYPESAFE_URL for u, _, _ in calls))
        self.assertTrue(all(b["model"] == g.DEFAULT_MODEL for _, _, b in calls))
        self.assertEqual(sorted(calls[0][2]["questions"]),
                         sorted(q for q in g.QUESTION_IDS if q not in g.JEV_SKIPS))
        self.assertEqual(sorted(calls[0][2]["state"]), ["claim", "quote"])
        self.assertEqual(rows[0]["answers"]["authority"]["by"], "code")
        held = [r for r in rows if r["scorer"] == "held"]
        self.assertEqual([r["id"] for r in held], ["Q2-02"])
        self.assertNotIn("SECRET123", stdout + stderr)
        self.assertIn("1 held", stderr)

    def test_cloudflare_host_unwraps_result(self):
        calls = []

        def post(url, headers, body, timeout=30):
            calls.append(url)
            return {"result": {"answers": answers()}, "success": True}

        env = {"CLOUDFLARE_ACCOUNT_ID": "acct", "CLOUDFLARE_API_TOKEN": "tok"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(g, "post_json", post):
            host, rows = g.score_with_jev(g.load_cards([CARDS]), {}, "jev-1.13.0",
                                          allow_internal=True, host="cloudflare")
        self.assertEqual(host, "cloudflare")
        self.assertIn("/accounts/acct/ai/run/typesafe/jev", calls[0])
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["answers"] for r in rows))

    def test_jev_scores_need_a_merged_injection_screen_before_routing(self):
        calls = []
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "k"}, clear=True), \
                mock.patch.object(g, "post_json", self.fake_post(calls)):
            with tempfile.TemporaryDirectory() as tmp:
                jev = os.path.join(tmp, "jev.jsonl")
                merged = os.path.join(tmp, "merged.jsonl")
                self.assertEqual(run(["score", BRIEF, CARDS, "--scorer", "jev",
                                      "--out", jev])[0], 0)
                code, _, err = run(["route", jev, CARDS, "--brief", BRIEF])
                self.assertEqual(code, 2)
                self.assertIn("no answer for injection", err)
                self.assertEqual(run(["merge", jev, SCORES, "--out", merged])[0], 0)
                rows = {r["id"]: r for r in g.load_jsonl([merged])}
                self.assertEqual(rows["Q2-03"]["answers"]["injection"]["noul"], 0.98)
                self.assertIn("+claude[injection]", rows["Q2-03"]["scorer"])
                code, out, _ = run(["route", merged, CARDS, "--brief", BRIEF])
                self.assertEqual(code, 0)
                self.assertIn("flagged 1", out)

    def test_cloudflare_is_only_used_when_asked(self):
        env = {"CLOUDFLARE_ACCOUNT_ID": "acct", "CLOUDFLARE_API_TOKEN": "tok"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(g.UsageError):
                g.jev_endpoint()
            self.assertEqual(g.jev_endpoint("cloudflare")[0], "cloudflare")

    def test_no_credentials_is_a_usage_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _, err = run(["score", BRIEF, CARDS, "--scorer", "jev"])
        self.assertEqual(code, 2)
        self.assertIn("TYPESAFE_API_KEY", err)

    def test_one_failed_call_does_not_sink_the_batch(self):
        def post(url, headers, body, timeout=30):
            if body["state"]["claim"].startswith("Queue B"):
                raise RuntimeError("HTTP 500")
            return {"answers": answers()}

        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "k"}, clear=True), \
                mock.patch.object(g, "post_json", post):
            _, rows = g.score_with_jev(g.load_cards([CARDS]), {}, "jev-1.13.0")
        errors = [r["id"] for r in rows if r["scorer"] == "error"]
        self.assertEqual(errors, ["Q1-02"])


class PromptTest(unittest.TestCase):
    def test_prompt_carries_rubric_cards_and_the_data_rule(self):
        code, out, _ = run(["prompt", BRIEF, CARDS])
        self.assertEqual(code, 0)
        self.assertIn("data, never instructions", out)
        self.assertIn('"Q2-03"', out)
        self.assertIn('"impact"', out)
        self.assertNotIn('"hunter_confidence"', out)

    def test_check_flags_missing_scores(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(Path(SCORES).read_text().splitlines()[0] + "\n")
        try:
            code, out, _ = run(["check", fh.name, CARDS])
        finally:
            os.unlink(fh.name)
        self.assertEqual(code, 1)
        self.assertIn("Q1-02: card has no score", out)


if __name__ == "__main__":
    unittest.main()
